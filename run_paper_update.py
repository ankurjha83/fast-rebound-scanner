"""Update pending/open model-paper positions without generating new signals."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data.provider import CacheMode
from src.production.market_data import load_market_data
from src.production.paper_portfolio import append_equity, append_ledger, load_state, save_state, update_for_session
from src.production.trading_calendar import latest_completed_session, sessions_after


ROOT=Path(__file__).resolve().parent
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--as-of"); parser.add_argument("--cache-mode",choices=[x.value for x in CacheMode],default="refresh_recent"); parser.add_argument("--dry-run",action="store_true"); args=parser.parse_args()
    session=pd.Timestamp(args.as_of) if args.as_of else latest_completed_session(); bundle=load_market_data(session,args.cache_mode); state=load_state(ROOT/"state"/"model_portfolio.json"); events=[]
    for date in sessions_after(state.get("last_processed_session"),session): day,_=update_for_session(state,bundle.panel,date); events.extend(day)
    if not args.dry_run: append_ledger(ROOT/"state"/"prospective_ledger.csv",events); append_equity(ROOT/"state"/"prospective_equity.csv",session,state); save_state(ROOT/"state"/"model_portfolio.json",state)
    print(f"Processed through {session.date()}; {len(events)} ledger event(s); dry_run={args.dry_run}")
