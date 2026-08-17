import numpy as np
import pandas as pd
import pytest

from src.capital_allocation_research import AllocationArchitecture, run_allocation_portfolio, stress_test


def _panel():
    dates=pd.to_datetime(["2024-01-02","2024-01-03","2024-01-04"])
    index=pd.MultiIndex.from_product([dates,["AAA","BBB"]],names=["date","ticker"])
    return pd.DataFrame({"adj_open":[100.]*6,"adj_high":[101.]*6,"adj_low":[99.]*6,"adj_close":[100.]*6},index=index)


def _signals():
    return pd.DataFrame([
        {"date":pd.Timestamp("2024-01-02"),"ticker":"AAA","daily_rank":1,"beta252":2.2,"estimated_probability":.7,"fast_rebound_score":70.},
        {"date":pd.Timestamp("2024-01-02"),"ticker":"BBB","daily_rank":2,"beta252":2.1,"estimated_probability":.68,"fast_rebound_score":68.},
    ])


def test_fixed_architecture_allocates_entry_fraction_without_leverage():
    result,_=run_allocation_portfolio(_panel(),_signals(),AllocationArchitecture("two",2,.25,3))
    assert len(result.trades)==2
    assert np.allclose(result.trades.entry_weight,.25)
    assert result.equity.exposure.max()<=.51


def test_dynamic_full_splits_cash_across_same_day_candidates():
    result,_=run_allocation_portfolio(_panel(),_signals(),AllocationArchitecture("dynamic",4,None,4,True))
    assert len(result.trades)==2
    assert np.allclose(result.trades.entry_weight,.5)
    assert result.equity.exposure.max()>=.99


def test_rank_limit_does_not_admit_weaker_candidate():
    result,_=run_allocation_portfolio(_panel(),_signals(),AllocationArchitecture("one_rank",2,.25,1))
    assert set(result.trades.ticker)=={"AAA"}


def test_stress_scenarios_translate_weights_to_portfolio_impact():
    architectures=(AllocationArchitecture("three",3,1/3,3),)
    table=stress_test(architectures).set_index("scenario")
    assert table.loc["one position -15% gap","portfolio_impact"]==pytest.approx(-.05)
    assert table.loc["3 positions -15% gaps","portfolio_impact"]==pytest.approx(-.15)
