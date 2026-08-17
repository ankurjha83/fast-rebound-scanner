import numpy as np
import pandas as pd
import pytest

from src.fast_rebound_research import (
    FEATURES, analyze_forward_path, barrier_first, fit_chronological_model, rank_recommendations,
    run_fast_portfolio, simulate_trade_path,
)


def test_barrier_detection_at_1_3_5_10_days():
    opens=np.full(10,100.0); highs=np.array([101,102,106,103,104,105,106,107,108,109.]); lows=np.full(10,99.0); closes=np.full(10,100.0)
    out=analyze_forward_path(100,opens,highs,lows,closes)
    assert not out["hit_plus_5_within_1d"]
    assert out["hit_plus_5_within_3d"]
    assert out["hit_plus_5_within_5d"]
    assert out["hit_plus_5_within_10d"]
    assert out["days_to_plus_5pct"]==3


def test_barrier_first_same_bar_is_conservative():
    result=barrier_first(100,np.array([100.]),np.array([106.]),np.array([94.]),.05,.05)
    assert result[0]=="stop"


def test_barrier_first_gap_through_stop():
    result=barrier_first(100,np.array([90.]),np.array([92.]),np.array([88.]),.05,.05)
    assert result==( "stop_gap",1,90.0)


def test_mae_before_plus5_and_mfe_after_plus5():
    out=analyze_forward_path(100,np.full(3,100.),np.array([102.,106.,112.]),np.array([98.,96.,104.]),np.array([101.,105.,110.]))
    assert out["mae_before_plus5"]==pytest.approx(-.04)
    assert out["mfe_after_plus5"]==pytest.approx(.12)


def test_trailing_stop_activates_only_after_plus5_and_uses_high_water():
    result=simulate_trade_path(100,np.array([100.,100.,104.]),np.array([104.,108.,106.]),np.array([96.,103.,102.]),np.array([102.,106.,103.]),.10,"trail_5")
    assert result.exit_reason=="trailing_stop"
    assert result.exit_price==pytest.approx(108*.95)


def test_partial_exit_realizes_half_at_plus5():
    result=simulate_trade_path(100,np.array([100.]),np.array([106.]),np.array([100.]),np.array([105.]),.10,"partial_5_trail_5")
    assert result.partial_day==1
    assert result.gross_return==pytest.approx(.025+.5*(106*.95/100-1))


def test_ten_day_maximum_hold():
    result=simulate_trade_path(100,np.full(12,100.),np.full(12,102.),np.full(12,99.),np.full(12,101.),.10,"fixed_5")
    assert result.exit_day==10
    assert result.exit_reason=="hold10"


def test_stop_executes_at_level_without_gap():
    result=simulate_trade_path(100,np.array([100.]),np.array([101.]),np.array([89.]),np.array([90.]),.10,"fixed_5")
    assert result.exit_price==90
    assert result.exit_reason=="stop"


class _ProbabilityModel:
    def predict_proba(self, frame):
        p=frame[FEATURES[0]].to_numpy(float)
        return np.column_stack([1-p,p])


def _ranking_frame():
    rows=[]
    for date,values in (("2023-01-03",(.9,.8,.7,.6)),("2023-01-04",(.4,.3))):
        for i,value in enumerate(values):
            row={field:0. for field in FEATURES}; row.update({"date":pd.Timestamp(date),"ticker":f"T{i}","complete_10d_path":True,FEATURES[0]:value})
            rows.append(row)
    return pd.DataFrame(rows)


def test_daily_ranking_maximum_three_and_no_forcing():
    _,recommendations,distribution=rank_recommendations(_ranking_frame(),_ProbabilityModel(),.5)
    assert recommendations.groupby("date").size().max()==3
    assert pd.Timestamp("2023-01-04") not in set(recommendations.date)
    assert distribution.set_index("recommendations").loc[0,"days"]>=1


def test_next_day_open_entry_and_entry_day_stop():
    dates=pd.to_datetime(["2023-01-03","2023-01-04"])
    index=pd.MultiIndex.from_product([dates,["AAA"]],names=["date","ticker"])
    panel=pd.DataFrame({"adj_open":[100.,100.],"adj_high":[101.,101.],"adj_low":[99.,90.],"adj_close":[100.,91.]},index=index)
    rec=pd.DataFrame([{"date":dates[0],"ticker":"AAA","daily_rank":1,"beta252":2.5,"range_position_100d":.3,"estimated_probability":.8,"fast_rebound_score":80.}])
    result=run_fast_portfolio(panel,rec,.075,"fixed_5")
    assert result.trades.iloc[0].entry_date==dates[1]
    assert result.trades.iloc[0].exit_date==dates[1]
    assert result.trades.iloc[0].exit_reason=="stop"


def test_feature_inputs_are_signal_date_values_not_forward_outcomes():
    assert not any(name.startswith(("hit_","days_to_","mae_","mfe_","close_return_")) for name in FEATURES)


def test_chronological_training_excludes_primary_period():
    rows=[]
    for i,date in enumerate(pd.to_datetime(["2021-01-04","2021-01-05","2022-01-04","2022-01-05","2023-01-04","2024-01-04"])):
        row={field:float(i) for field in FEATURES}; row.update({"date":date,"complete_10d_path":True,"plus5_before_stop_7_5":bool(i%2)})
        rows.append(row)
    _,_,coefficients=fit_chronological_model(pd.DataFrame(rows),.075)
    assert coefficients.development_observations.iloc[0]==4
