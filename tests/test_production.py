from copy import deepcopy
from datetime import datetime, timezone
import json

import numpy as np
import pandas as pd
import pytest

from data.provider import CacheMode
from src.production import scanner
from src.production.audit_log import write_immutable_json
from src.production.frozen_config import FEATURES, MODEL_VERSION, assert_frozen_integrity
from src.production.human_ledger import record_decision
from src.production.market_data import load_market_data
from src.production.paper_portfolio import enqueue_recommendations, initial_state, load_state, save_state, update_for_session
from src.production.telegram_notifier import TelegramError, format_daily_message, send_message
from src.production.trading_calendar import is_session, next_session


def _qualifying(count=4):
    return pd.DataFrame([{"ticker":f"T{i}","daily_rank":i,"fast_rebound_score":80-i,"estimated_probability":.8-i/100,"previous_close":100.} for i in range(1,count+1)])


def _pending_state(signal="2026-07-01"):
    state=initial_state(); accepted,_=enqueue_recommendations(state,_qualifying(1),"run",datetime.now(timezone.utc).isoformat(),pd.Timestamp(signal)); assert len(accepted)==1; return state


def _panel(date,open_=100.,high=101.,low=99.,close=100.,split=0.):
    index=pd.MultiIndex.from_tuples([(pd.Timestamp(date),"T1")],names=["date","ticker"])
    return pd.DataFrame({"adj_open":[open_],"adj_high":[high],"adj_low":[low],"adj_close":[close],"stock_splits":[split]},index=index)


def test_frozen_config_integrity_and_version():
    assert_frozen_integrity(); assert MODEL_VERSION=="fast-rebound-v1-frozen"; assert len(FEATURES)==13


def test_ranking_max_three_and_no_forced_recommendations(monkeypatch):
    features=pd.DataFrame({"ticker":["A","B","C","D"],"eligible":[True]*4,**{x:[0.]*4 for x in FEATURES}})
    monkeypatch.setattr(scanner,"frozen_probabilities",lambda frame:np.array([.9,.8,.7,.5]))
    _,qualified=scanner.rank_recommendations(features); assert list(qualified.ticker)==["A","B","C"]
    monkeypatch.setattr(scanner,"frozen_probabilities",lambda frame:np.array([.5,.4,.3,.2]))
    _,qualified=scanner.rank_recommendations(features); assert qualified.empty


def test_portfolio_max_three_and_no_ignored_queue():
    state=initial_state(); accepted,events=enqueue_recommendations(state,_qualifying(),"run","now",pd.Timestamp("2026-07-01")); assert len(accepted)==len(events)==len(state["pending"])==3


def test_pending_waits_for_actual_next_open_and_sizes_one_third():
    state=_pending_state(); events,_=update_for_session(state,_panel("2026-07-02"),pd.Timestamp("2026-07-02")); entry=[x for x in events if x["event_type"]=="ENTRY"][0]
    assert entry["entry_price"]==100.; assert state["positions"][0]["entry_cash_out"]==pytest.approx(100000/3); assert state["positions"][0]["holding_days"]==1


def test_entry_day_stop_wins_when_both_barriers_hit():
    state=_pending_state(); events,_=update_for_session(state,_panel("2026-07-02",high=106,low=92),pd.Timestamp("2026-07-02")); exit_event=[x for x in events if x["event_type"]=="EXIT"][0]; assert exit_event["exit_reason"]=="stop"; assert exit_event["exit_price"]==92.5


def test_entry_day_target():
    state=_pending_state(); events,_=update_for_session(state,_panel("2026-07-02",high=106,low=99),pd.Timestamp("2026-07-02")); assert [x for x in events if x["event_type"]=="EXIT"][0]["exit_reason"]=="target"


def test_gap_through_stop_uses_open():
    state=_pending_state(); update_for_session(state,_panel("2026-07-02"),pd.Timestamp("2026-07-02")); events,_=update_for_session(state,_panel("2026-07-06",open_=90,high=91,low=89,close=90),pd.Timestamp("2026-07-06")); event=[x for x in events if x["event_type"]=="EXIT"][0]; assert event["exit_reason"]=="stop_gap"; assert event["exit_price"]==90


def test_ten_trading_day_timeout_and_idempotent_session():
    state=_pending_state(); sessions=[next_session("2026-07-01")]
    for _ in range(9): sessions.append(next_session(sessions[-1]))
    exits=[]
    for date in sessions:
        events,_=update_for_session(state,_panel(date),date); exits.extend(x for x in events if x["event_type"]=="EXIT")
    assert exits[0]["exit_reason"]=="hold10"; assert exits[0]["holding_days"]==10
    events,_=update_for_session(state,_panel(sessions[-1]),sessions[-1]); assert events==[]


def test_missing_due_open_is_never_substituted():
    state=_pending_state(); empty=_panel("2026-07-02").iloc[0:0]; _,notices=update_for_session(state,empty,pd.Timestamp("2026-07-02")); assert state["pending"][0]["status"]=="ENTRY_DATA_MISSING"; assert notices[0]["type"]=="ENTRY_DATA_MISSING"


def test_state_round_trip_and_corruption_detection(tmp_path):
    path=tmp_path/"state.json"; state=initial_state(); save_state(path,state); assert load_state(path)["model_version"]==MODEL_VERSION; path.write_text("bad");
    with pytest.raises(RuntimeError): load_state(path)


def test_immutable_snapshot_refuses_overwrite(tmp_path):
    path=tmp_path/"one.json"; write_immutable_json(path,{"a":1})
    with pytest.raises(FileExistsError): write_immutable_json(path,{"a":2})


def test_market_holiday_and_next_session():
    assert not is_session("2026-07-03"); assert next_session("2026-07-02")==pd.Timestamp("2026-07-06")


def test_telegram_message_and_failure_do_not_expose_token(monkeypatch):
    text=format_daily_message("2026-07-01",_qualifying(1),_qualifying(1),initial_state(),[]); assert "PENDING NEXT OPEN" in text and "33.33%" in text
    def broken(*args,**kwargs): raise __import__('requests').Timeout("secret-token")
    monkeypatch.setattr("requests.post",broken)
    with pytest.raises(TelegramError) as error: send_message("x",token="secret-token",chat_id="1")
    assert "secret-token" not in str(error.value)


def test_human_decision_isolation(tmp_path):
    state=initial_state(); before=deepcopy(state); row=record_decision(tmp_path/"human.csv",run_id="r",recommendation_date="2026-07-01",ticker="t1",decision="SKIP",reason="valuation"); assert row["decision"]=="SKIP"; assert state==before


def test_frozen_inference_matches_research_scanner_historical_date():
    bundle=load_market_data("2026-07-31",CacheMode.CACHED); features=scanner.build_signal_features(bundle.panel,"2026-07-31"); _,actual=scanner.rank_recommendations(features)
    assert list(actual.sort_values("daily_rank").ticker)==["SMCI","KLAC","SNDK"]
    assert actual.estimated_probability.to_numpy()==pytest.approx([.7009296456858085,.6561636454478402,.6404593007383491])


def test_feature_builder_uses_only_data_through_session():
    bundle=load_market_data("2026-07-31",CacheMode.CACHED); base=scanner.build_signal_features(bundle.panel,"2026-07-31").set_index("ticker")
    truncated=bundle.panel.loc[bundle.panel.index.get_level_values("date")<=pd.Timestamp("2026-07-31")]; again=scanner.build_signal_features(truncated,"2026-07-31").set_index("ticker")
    pd.testing.assert_series_equal(base.loc["SMCI",list(FEATURES)],again.loc["SMCI",list(FEATURES)])
