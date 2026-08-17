from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.capital_allocation_research import AllocationArchitecture, run_allocation_portfolio
from src.theme_concentration_diagnostic import audited_theme_mapping, basket_analysis


def test_audited_mapping_separates_residual_other_artifact():
    mapping=audited_theme_mapping(["AVGO","WDC","STX"]).set_index("ticker")
    assert mapping.loc["AVGO","audited_theme"]=="AI / semiconductors"
    assert mapping.loc["WDC","audited_theme"]=="data infrastructure"
    assert mapping.loc["STX","audited_theme"]=="data infrastructure"


def test_theme_limit_skips_conflict_and_admits_next_candidate():
    dates=pd.to_datetime(["2024-01-02","2024-01-03","2024-01-04"])
    index=pd.MultiIndex.from_product([dates,["AAA","BBB","CCC"]],names=["date","ticker"])
    panel=pd.DataFrame({"adj_open":100.,"adj_high":101.,"adj_low":99.,"adj_close":100.},index=index)
    signals=pd.DataFrame([
        {"date":dates[0],"ticker":"AAA","daily_rank":1,"beta252":2.2,"estimated_probability":.70,"fast_rebound_score":70.},
        {"date":dates[0],"ticker":"BBB","daily_rank":2,"beta252":2.1,"estimated_probability":.69,"fast_rebound_score":69.},
        {"date":dates[0],"ticker":"CCC","daily_rank":3,"beta252":2.0,"estimated_probability":.68,"fast_rebound_score":68.},
    ])
    result,ignored=run_allocation_portfolio(panel,signals,AllocationArchitecture("theme",3,1/3,999),theme_map_override={"AAA":"x","BBB":"x","CCC":"y"},max_per_theme=1)
    assert set(result.trades.ticker)=={"AAA","CCC"}
    assert ignored.loc[ignored.ticker.eq("BBB"),"reason"].iloc[0]=="theme_limit"


def test_single_day_basket_includes_that_days_return():
    dates=pd.to_datetime(["2024-01-02","2024-01-03"])
    equity=pd.DataFrame({"equity":[100.,95.],"position_tickers":["","AAA|BBB"],"position_weights":["","AAA:0.5|BBB:0.5"],"exposure":[0.,1.]},index=dates)
    index=pd.MultiIndex.from_product([dates,["AAA","BBB"]],names=["date","ticker"])
    panel=pd.DataFrame({"adj_close":[100.,100.,95.,95.]},index=index)
    trades=pd.DataFrame({"ticker":["AAA","BBB"],"entry_date":[dates[1]]*2,"exit_date":[dates[1]]*2,"daily_rank":[1,2],"fast_rebound_score":[70.,69.],"exit_reason":["hold10","hold10"],"mae":[-.05,-.05],"mfe":[0.,0.],"holding_days":[1,1]})
    baskets=basket_analysis(SimpleNamespace(equity=equity),trades,panel,{"AAA":"x","BBB":"x"})
    assert len(baskets)==1
    assert baskets.iloc[0].basket_return==pytest.approx(-.05)
    assert baskets.iloc[0].positions==2
