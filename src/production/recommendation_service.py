"""Immutable recommendation snapshots and idempotent pending entries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pandas as pd

from src.production.audit_log import write_immutable_json
from src.production.frozen_config import MAX_HOLDING_DAYS, MAX_POSITIONS, MODEL_VERSION, POSITION_SIZE, STOP_LOSS, TAKE_PROFIT


def git_sha() -> str:
    try: return subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
    except Exception: return "unknown"


def candidate_record(row: pd.Series, available_slot: int | None=None) -> dict:
    fields=("atr_pct","realized_volatility_10d","absolute_move_3pct_frequency_60d","plus5_5d_frequency_60d","range_position_100d","drawdown_from_50d_high","distance_sma20","previous_5d_return","close_position_in_day_range","consecutive_down_days","sma20_slope","volume_relative_20d","qqq_20d_return")
    return {
        "rank":int(row.daily_rank),"ticker":str(row.ticker),"previous_close":float(row.previous_close),"market_cap":float(row.market_cap),"beta":float(row.beta252),
        "fast_rebound_score":float(row.fast_rebound_score),"estimated_probability":float(row.estimated_probability),
        **{field:(None if pd.isna(row.get(field)) else float(row.get(field))) for field in fields},
        "target_percentage":TAKE_PROFIT,"stop_percentage":STOP_LOSS,"maximum_hold":MAX_HOLDING_DAYS,
        "available_portfolio_slot":available_slot,"recommended_allocation":POSITION_SIZE,
    }


def build_snapshot(run_id: str, utc: datetime, session: pd.Timestamp, bundle, scored: pd.DataFrame, qualifying: pd.DataFrame, accepted: pd.DataFrame, state: dict) -> dict:
    open_positions=[{k:p.get(k) for k in ("ticker","entry_date","entry_price","quantity","holding_days","mae","mfe")} for p in state.get("positions",[])]
    slots=MAX_POSITIONS-len(open_positions)-len(state.get("pending",[]))
    accepted_tickers=set(accepted.ticker) if len(accepted) else set()
    candidates=[]
    for row in qualifying.itertuples(index=False):
        record=candidate_record(pd.Series(row._asdict()),max(0,slots)); record["portfolio_action"]="PENDING_NEXT_OPEN" if row.ticker in accepted_tickers else "WATCH_ONLY_NO_SLOT"; candidates.append(record)
    return {"run_id":run_id,"run_timestamp_utc":utc.isoformat(),"run_timestamp_kst":utc.astimezone(__import__('zoneinfo').ZoneInfo("Asia/Seoul")).isoformat(),"data_session_date":str(session.date()),"git_sha":git_sha(),"model_version":MODEL_VERSION,"universe_size":bundle.universe_size,"covered_on_session":bundle.covered_on_session,"data_source_status":bundle.status,"data_failures":bundle.errors,"eligible_count":int(scored.eligible.sum()) if len(scored) else 0,"qualifying_count":len(qualifying),"accepted_count":len(accepted),"candidates":candidates,"open_model_positions":open_positions,"pending_model_entries":state.get("pending",[])}


def save_snapshot(snapshot: dict, directory: str | Path) -> Path:
    name=f"{snapshot['data_session_date']}_{snapshot['run_id']}.json"
    target=Path(directory)/name
    try: return write_immutable_json(target,snapshot)
    except FileExistsError:
        existing=__import__('json').loads(target.read_text(encoding="utf-8"))
        if existing.get("model_version")!=snapshot.get("model_version") or existing.get("data_session_date")!=snapshot.get("data_session_date"): raise RuntimeError("Existing recommendation snapshot conflicts with this run")
        return target
