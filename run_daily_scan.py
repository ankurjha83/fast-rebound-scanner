"""Run one idempotent Fast Rebound production scan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

from data.provider import CacheMode
from src.production.audit_log import write_immutable_json
from src.production.frozen_config import MODEL_VERSION, assert_frozen_integrity
from src.production.market_data import load_market_data
from src.production.paper_portfolio import append_equity, append_ledger, clone_state, enqueue_recommendations, load_state, save_state
from src.production.recommendation_service import build_snapshot, git_sha, save_snapshot
from src.production.reporting import generate_report
from src.production.scanner import build_signal_features, rank_recommendations
from src.production.telegram_notifier import TelegramError, error_message, format_daily_message, no_new_session_message, send_message, send_test_message
from src.production.trade_monitor import process_through
from src.production.trading_calendar import latest_completed_session


ROOT=Path(__file__).resolve().parent
STATE_PATH=ROOT/"state"/"model_portfolio.json"
LEDGER_PATH=ROOT/"state"/"prospective_ledger.csv"


def _audit_path(run_id: str, utc: datetime) -> Path: return ROOT/"state"/"run_history"/f"{utc.strftime('%Y%m%dT%H%M%S%fZ')}_{run_id}.json"


def run(args) -> int:
    assert_frozen_integrity(); utc=datetime.now(timezone.utc); session=pd.Timestamp(args.as_of).normalize() if args.as_of else latest_completed_session(utc); run_id=f"fr-{session.strftime('%Y%m%d')}"; state=load_state(STATE_PATH); before=clone_state(state)
    if not args.dry_run and str(session.date()) in state["recommendation_sessions"]:
        retry=state.get("pending_notification"); message=retry["message"] if retry else no_new_session_message(session.date()); telegram_ok=None
        if not args.no_telegram:
            try:
                send_message(message); telegram_ok=True
                if retry: state["pending_notification"]=None; save_state(STATE_PATH,state)
            except TelegramError: telegram_ok=False
        audit={"run_id":run_id,"timestamp_utc":utc.isoformat(),"git_sha":git_sha(),"model_version":MODEL_VERSION,"data_session":str(session.date()),"status":"RETRIED_NOTIFICATION" if retry else "NO_NEW_SESSION","data_source_status":"NOT_REFRESHED","universe_size":None,"data_failures":{},"recommendations":[],"portfolio_state_before":before,"portfolio_state_after":state,"telegram_success":telegram_ok,"exceptions":[]}
        write_immutable_json(_audit_path(run_id,utc),audit); print(message); return 2 if telegram_ok is False else 0
    try:
        bundle=load_market_data(session,CacheMode(args.cache_mode))
        if bundle.status=="FAILED": raise RuntimeError(f"Market-data coverage insufficient: {bundle.covered_on_session}/{bundle.universe_size}")
        working=clone_state(state); portfolio_events,notices=process_through(working,bundle.panel,session)
        features=build_signal_features(bundle.panel,session); scored,qualifying=rank_recommendations(features)
        accepted,recommendation_events=enqueue_recommendations(working,qualifying,run_id,utc.isoformat(),session); all_events=portfolio_events+recommendation_events
        snapshot=build_snapshot(run_id,utc,session,bundle,scored,qualifying,accepted,working)
        message=format_daily_message(session.date(),qualifying,accepted,working,notices,bundle.status)
        if args.dry_run:
            print(message); print("\nDRY-RUN STATE CHANGES\n"+json.dumps({"events":all_events,"state_before":before,"state_after":working},indent=2,default=str)); return 0
        if not args.no_telegram: working["pending_notification"]={"session":str(session.date()),"message":message}
        save_snapshot(snapshot,ROOT/"state"/"recommendation_history"); append_ledger(LEDGER_PATH,all_events); append_equity(ROOT/"state"/"prospective_equity.csv",session,working); save_state(STATE_PATH,working)
        generate_report(LEDGER_PATH,ROOT/"outputs"/"prospective"/"fast_rebound_prospective_report.md",ROOT/"state"/"prospective_equity.csv")
        telegram_ok=None; telegram_error=None
        if not args.no_telegram:
            try: send_message(message); telegram_ok=True; working["pending_notification"]=None; save_state(STATE_PATH,working)
            except TelegramError as exc: telegram_ok=False; telegram_error=str(exc)
        audit={"run_id":run_id,"timestamp_utc":utc.isoformat(),"git_sha":git_sha(),"model_version":MODEL_VERSION,"data_session":str(session.date()),"status":"SUCCESS" if telegram_ok is not False else "SUCCESS_TELEGRAM_FAILED","data_source_status":bundle.status,"universe_size":bundle.universe_size,"covered_on_session":bundle.covered_on_session,"data_failures":bundle.errors,"recommendations":snapshot["candidates"],"portfolio_events":all_events,"portfolio_state_before":before,"portfolio_state_after":working,"telegram_success":telegram_ok,"telegram_error":telegram_error,"exceptions":[]}
        write_immutable_json(_audit_path(run_id,utc),audit); write_immutable_json(ROOT/"outputs"/"daily"/f"{utc.strftime('%Y%m%dT%H%M%S%fZ')}_{run_id}.json",audit); print(message)
        return 2 if telegram_ok is False else 0
    except Exception as exc:
        reason=f"{type(exc).__name__}: {exc}"; telegram_ok=None
        if not args.dry_run and not args.no_telegram:
            try: send_message(error_message(reason)); telegram_ok=True
            except Exception: telegram_ok=False
        audit={"run_id":run_id,"timestamp_utc":utc.isoformat(),"git_sha":git_sha(),"model_version":MODEL_VERSION,"data_session":str(session.date()),"status":"FAILED","data_source_status":"FAILED","universe_size":None,"data_failures":{},"recommendations":[],"portfolio_state_before":before,"portfolio_state_after":before,"telegram_success":telegram_ok,"exceptions":[reason]}
        if not args.dry_run: write_immutable_json(_audit_path(run_id,utc),audit)
        print(error_message(reason),file=sys.stderr); return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--no-telegram",action="store_true"); parser.add_argument("--telegram-test",action="store_true"); parser.add_argument("--cache-mode",choices=[x.value for x in CacheMode],default=CacheMode.REFRESH_RECENT.value); parser.add_argument("--as-of",help="Completed NYSE session YYYY-MM-DD")
    arguments=parser.parse_args()
    if arguments.telegram_test:
        try: send_test_message(); print("Telegram integration test sent."); raise SystemExit(0)
        except TelegramError as exc: print(str(exc),file=sys.stderr); raise SystemExit(1)
    raise SystemExit(run(arguments))
