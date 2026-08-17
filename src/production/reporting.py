"""Prospective-only metrics; historical results are labeled separately."""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


CHECKPOINTS=(25,50,100,200)
HISTORICAL_REFERENCE={"trades":226,"total_return":.7412725,"cagr":.1660,"sharpe":.8252,"maximum_drawdown":-.1764}


def prospective_metrics(ledger: pd.DataFrame, equity_history: pd.DataFrame | None=None) -> dict:
    exits=ledger.loc[ledger.event_type.eq("EXIT")].copy() if len(ledger) else pd.DataFrame()
    if exits.empty: return {"trade_count":0,"checkpoint":"Collecting prospective data; no performance claim."}
    returns=pd.to_numeric(exits.return_pct); pnl=pd.to_numeric(exits.portfolio_pnl); winners=pnl.clip(lower=0).sum(); losses=-pnl.clip(upper=0).sum(); equity=100_000+pnl.cumsum(); drawdown=equity/equity.cummax()-1
    count=len(exits); reached=max([x for x in CHECKPOINTS if count>=x],default=0); next_cp=min([x for x in CHECKPOINTS if count<x],default=None); cagr=None; sharpe=None
    if equity_history is not None and len(equity_history)>1:
        curve=pd.to_numeric(equity_history.equity); daily=curve.pct_change(fill_method=None).dropna(); drawdown=curve/curve.cummax()-1; span=(pd.to_datetime(equity_history.session).max()-pd.to_datetime(equity_history.session).min()).days/365.25
        if count>=25 and span>=.5: cagr=(curve.iloc[-1]/curve.iloc[0])**(1/span)-1; sharpe=daily.mean()/daily.std()*np.sqrt(252) if daily.std() else None
    return {"trade_count":count,"trades_per_month":count/max(1,(pd.to_datetime(exits.exit_date).max()-pd.to_datetime(exits.entry_date).min()).days/30.44),"target_rate":exits.exit_reason.astype(str).str.startswith("target").mean(),"stop_rate":exits.exit_reason.astype(str).str.startswith("stop").mean(),"timeout_rate":exits.exit_reason.eq("hold10").mean(),"average_return":returns.mean(),"median_return":returns.median(),"profit_factor":winners/losses if losses else None,"cumulative_return":equity.iloc[-1]/100_000-1,"cagr_when_meaningful":cagr,"sharpe_when_meaningful":sharpe,"maximum_drawdown":drawdown.min(),"average_mae":pd.to_numeric(exits.mae).mean(),"average_mfe":pd.to_numeric(exits.mfe).mean(),"average_holding_period":pd.to_numeric(exits.holding_days).mean(),"gap_through_losses":int(exits.gap_through_stop.astype(str).str.lower().eq("true").sum()),"checkpoint_reached":reached,"next_checkpoint":next_cp}


def generate_report(ledger_path: str | Path, output_path: str | Path, equity_path: str | Path | None=None) -> dict:
    path=Path(ledger_path); ledger=pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame(); epath=Path(equity_path) if equity_path else None; equity_history=pd.read_csv(epath) if epath and epath.exists() and epath.stat().st_size else None; metrics=prospective_metrics(ledger,equity_history)
    rank=pd.DataFrame()
    if len(ledger):
        exits=ledger.loc[ledger.event_type.eq("EXIT")].copy()
        if len(exits): rank=exits.assign(return_pct=pd.to_numeric(exits.return_pct)).groupby("rank").return_pct.agg(["count","mean","median"]).reset_index()
    text="# Fast Rebound Prospective Report\n\n## PROSPECTIVE\n\n```json\n"+json.dumps(metrics,indent=2,default=str)+"\n```\n\n## Performance by rank\n\n"+(rank.to_markdown(index=False) if len(rank) else "No completed prospective trades.")+"\n\n## HISTORICAL REFERENCE (not prospective)\n\n```json\n"+json.dumps(HISTORICAL_REFERENCE,indent=2)+"\n```\n\nCheckpoint reviews never modify the frozen strategy automatically.\n"
    target=Path(output_path); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text,encoding="utf-8"); return metrics


def human_vs_model(model_ledger: pd.DataFrame, human_decisions: pd.DataFrame) -> dict:
    """Return comparison-ready counts without claiming human performance."""
    if model_ledger.empty or human_decisions.empty: return {"status":"insufficient human data","model_completed":int(model_ledger.event_type.eq("EXIT").sum()) if len(model_ledger) else 0,"human_decisions":len(human_decisions)}
    exits=model_ledger.loc[model_ledger.event_type.eq("EXIT"),["run_id","ticker","return_pct"]].copy(); merged=human_decisions.merge(exits,on=["run_id","ticker"],how="left"); skipped=merged.loc[merged.decision.eq("SKIP")]
    return {"status":"descriptive only","model_completed":len(exits),"human_decisions":len(merged),"skipped_winners":int(pd.to_numeric(skipped.return_pct,errors="coerce").gt(0).sum()),"avoided_losers":int(pd.to_numeric(skipped.return_pct,errors="coerce").lt(0).sum())}
