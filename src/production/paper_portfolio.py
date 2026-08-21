"""Event-driven prospective model portfolio; human actions never enter this module."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.production.audit_log import append_csv, atomic_json
from src.production.frozen_config import (
    COMMISSION_RATE, INITIAL_EQUITY, MAX_HOLDING_DAYS, MAX_POSITIONS, MODEL_VERSION,
    POSITION_SIZE, SLIPPAGE_RATE, STOP_LOSS, TAKE_PROFIT,
)
from src.production.trading_calendar import next_session


LEDGER_FIELDS=["event_id","event_type","model_version","recommendation_timestamp","run_id","signal_session","rank","ticker","score","predicted_probability","signal_close","entry_date","entry_price","allocation","target_price","stop_price","exit_date","exit_price","exit_reason","return_pct","portfolio_pnl","holding_days","mae","mfe","gap_through_stop","portfolio_equity_before","portfolio_equity_after","recorded_at_utc"]
EQUITY_FIELDS=["session","model_version","equity","cash","market_value","exposure","open_positions"]


def initial_state() -> dict:
    return {"schema_version":1,"model_version":MODEL_VERSION,"last_processed_session":None,"recommendation_sessions":[],"cash":INITIAL_EQUITY,"equity":INITIAL_EQUITY,"positions":[],"pending":[],"pending_notification":None,"updated_at_utc":None}


def load_state(path: str | Path) -> dict:
    target=Path(path)
    if not target.exists(): return initial_state()
    try: state=json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc: raise RuntimeError(f"Portfolio state is unreadable: {type(exc).__name__}") from exc
    if state.get("model_version")!=MODEL_VERSION or not isinstance(state.get("positions"),list) or not isinstance(state.get("pending"),list): raise RuntimeError("Portfolio state failed schema/model validation")
    return state


def save_state(path: str | Path, state: dict) -> None:
    state["updated_at_utc"]=datetime.now(timezone.utc).isoformat(); atomic_json(path,state)


def _event(kind: str, item: dict, **updates) -> dict:
    now=datetime.now(timezone.utc).isoformat(); base={field:"" for field in LEDGER_FIELDS}; base.update(item); base.update(updates); base.update({"event_id":f"{kind}:{item['run_id']}:{item['ticker']}:{updates.get('entry_date') or updates.get('exit_date') or item.get('signal_session')}","event_type":kind,"model_version":MODEL_VERSION,"recorded_at_utc":now}); return base


def enqueue_recommendations(state: dict, qualifying: pd.DataFrame, run_id: str, recommendation_timestamp: str, signal_session: pd.Timestamp) -> tuple[pd.DataFrame,list[dict]]:
    if str(signal_session.date()) in state["recommendation_sessions"]: return qualifying.iloc[0:0].copy(),[]
    held={p["ticker"] for p in state["positions"]}|{p["ticker"] for p in state["pending"]}; slots=max(0,MAX_POSITIONS-len(held)); accepted=qualifying.loc[~qualifying.ticker.isin(held)].head(slots).copy(); events=[]
    for row in accepted.itertuples():
        item={"run_id":run_id,"recommendation_timestamp":recommendation_timestamp,"signal_session":str(signal_session.date()),"entry_due_session":str(next_session(signal_session).date()),"rank":int(row.daily_rank),"ticker":row.ticker,"score":float(row.fast_rebound_score),"predicted_probability":float(row.estimated_probability),"signal_close":float(row.previous_close),"allocation":POSITION_SIZE,"status":"PENDING_NEXT_OPEN"}
        state["pending"].append(item); events.append(_event("RECOMMENDATION",item))
    state["recommendation_sessions"].append(str(signal_session.date()))
    return accepted,events


def _bar(panel: pd.DataFrame, session: pd.Timestamp, ticker: str) -> pd.Series | None:
    try: row=panel.loc[(session,ticker)]; return row if isinstance(row,pd.Series) else row.iloc[-1]
    except KeyError: return None


def update_for_session(state: dict, panel: pd.DataFrame, session: pd.Timestamp) -> tuple[list[dict],list[dict]]:
    """Apply exactly one completed session. Calling twice is a no-op."""
    session=pd.Timestamp(session).normalize(); last=state.get("last_processed_session")
    if last and session<=pd.Timestamp(last): return [],[]
    working_events=[]; notices=[]; positions=state["positions"]
    opening_equity=float(state["cash"])
    for p in positions:
        bar=_bar(panel,session,p["ticker"]); opening_equity+=p["quantity"]*float(bar.adj_open if bar is not None else p.get("last_close",p["entry_price"]))
    remaining=[]
    for item in state["pending"]:
        due=pd.Timestamp(item["entry_due_session"]); bar=_bar(panel,session,item["ticker"])
        if session<due: remaining.append(item); continue
        if session>due or bar is None or not np.isfinite(bar.adj_open) or bar.adj_open<=0:
            if item.get("status")!="ENTRY_DATA_MISSING": notices.append({"type":"ENTRY_DATA_MISSING","ticker":item["ticker"],"due_session":str(due.date())})
            item["status"]="ENTRY_DATA_MISSING"; remaining.append(item); continue
        if float(bar.get("stock_splits",0) or 0)!=0:
            item["status"]="CORPORATE_ACTION_REVIEW"; remaining.append(item); notices.append({"type":"CORPORATE_ACTION_REVIEW","ticker":item["ticker"]}); continue
        entry_equity=float(state["cash"])
        for held in positions:
            held_bar=_bar(panel,session,held["ticker"]); entry_equity+=held["quantity"]*float(held_bar.adj_open if held_bar is not None else held.get("last_close",held["entry_price"]))
        budget=min(entry_equity*POSITION_SIZE,float(state["cash"])); effective=float(bar.adj_open)*(1+SLIPPAGE_RATE); quantity=budget/(effective*(1+COMMISSION_RATE)); commission=quantity*effective*COMMISSION_RATE; out=quantity*effective+commission
        state["cash"]-=out
        position={**item,"status":"OPEN","entry_date":str(session.date()),"entry_price":float(bar.adj_open),"quantity":quantity,"entry_cash_out":out,"entry_commission":commission,"portfolio_equity_before":entry_equity,"target_price":float(bar.adj_open)*(1+TAKE_PROFIT),"stop_price":float(bar.adj_open)*(1+STOP_LOSS),"holding_days":0,"mae":0.,"mfe":0.,"last_close":float(bar.adj_open)}
        positions.append(position); working_events.append(_event("ENTRY",position,entry_date=position["entry_date"],entry_price=position["entry_price"],target_price=position["target_price"],stop_price=position["stop_price"],portfolio_equity_before=entry_equity)); notices.append({"type":"ENTRY","ticker":item["ticker"],"price":position["entry_price"]})
    state["pending"]=remaining
    still_open=[]
    for p in positions:
        bar=_bar(panel,session,p["ticker"])
        if bar is None: raise RuntimeError(f"Missing daily bar for open model position {p['ticker']} on {session.date()}")
        if pd.Timestamp(p["entry_date"])>session: still_open.append(p); continue
        p["holding_days"]+=1; p["mae"]=min(p["mae"],float(bar.adj_low)/p["entry_price"]-1); p["mfe"]=max(p["mfe"],float(bar.adj_high)/p["entry_price"]-1); p["last_close"]=float(bar.adj_close)
        raw_exit=None; reason=None
        if bar.adj_open<=p["stop_price"]: raw_exit=float(bar.adj_open); reason="stop_gap"
        elif bar.adj_open>=p["target_price"]: raw_exit=float(bar.adj_open); reason="target_gap"
        elif bar.adj_low<=p["stop_price"]: raw_exit=p["stop_price"]; reason="stop"
        elif bar.adj_high>=p["target_price"]: raw_exit=p["target_price"]; reason="target"
        elif p["holding_days"]>=MAX_HOLDING_DAYS: raw_exit=float(bar.adj_close); reason="hold10"
        if reason is None: still_open.append(p); continue
        effective=raw_exit*(1-SLIPPAGE_RATE); gross=p["quantity"]*effective; fee=gross*COMMISSION_RATE; proceeds=gross-fee; state["cash"]+=proceeds; pnl=proceeds-p["entry_cash_out"]; after=state["cash"]+sum(x["quantity"]*x["last_close"] for x in still_open)
        event=_event("EXIT",p,entry_date=p["entry_date"],entry_price=p["entry_price"],target_price=p["target_price"],stop_price=p["stop_price"],exit_date=str(session.date()),exit_price=raw_exit,exit_reason=reason,return_pct=proceeds/p["entry_cash_out"]-1,portfolio_pnl=pnl,holding_days=p["holding_days"],mae=p["mae"],mfe=p["mfe"],gap_through_stop=reason=="stop_gap",portfolio_equity_before=p["portfolio_equity_before"],portfolio_equity_after=after)
        working_events.append(event); notices.append({"type":"EXIT","ticker":p["ticker"],"price":raw_exit,"reason":reason,"return_pct":event["return_pct"],"holding_days":p["holding_days"],"entry_price":p["entry_price"],"portfolio_pnl":pnl})
    state["positions"]=still_open; state["equity"]=float(state["cash"])+sum(p["quantity"]*p["last_close"] for p in still_open); state["last_processed_session"]=str(session.date())
    for event in working_events:
        if event["event_type"]=="EXIT": event["portfolio_equity_after"]=state["equity"]
    return working_events,notices


def append_ledger(path: str | Path, events: list[dict]) -> None:
    target=Path(path); existing=set()
    if target.exists() and target.stat().st_size:
        try: existing=set(pd.read_csv(target,usecols=["event_id"]).event_id)
        except (ValueError,pd.errors.EmptyDataError): existing=set()
    append_csv(target,[event for event in events if event["event_id"] not in existing],LEDGER_FIELDS)


def append_equity(path: str | Path, session: pd.Timestamp, state: dict) -> None:
    target=Path(path); key=str(pd.Timestamp(session).date()); existing=set()
    if target.exists() and target.stat().st_size:
        try: existing=set(pd.read_csv(target,usecols=["session"]).session.astype(str))
        except (ValueError,pd.errors.EmptyDataError): existing=set()
    if key in existing: return
    market=sum(p["quantity"]*p.get("last_close",p["entry_price"]) for p in state["positions"]); equity=float(state["equity"])
    append_csv(target,[{"session":key,"model_version":MODEL_VERSION,"equity":equity,"cash":state["cash"],"market_value":market,"exposure":market/equity if equity else 0.,"open_positions":len(state["positions"])}],EQUITY_FIELDS)


def clone_state(state: dict) -> dict: return deepcopy(state)
