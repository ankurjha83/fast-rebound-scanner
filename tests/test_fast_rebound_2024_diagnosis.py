import numpy as np
import pandas as pd

from src.fast_rebound_2024_diagnosis import barrier_analysis, pnl_concentration, variance_test


def test_pnl_concentration_uses_worst_trades():
    trades=pd.DataFrame({"net_pnl":[-100.,-50.,25.,25.]})
    out=pnl_concentration(trades).set_index("subset")
    assert out.loc["worst 1","pnl"]==-100
    assert out.loc["worst 3","pnl"]==-125


def test_barrier_year_probabilities_partition_paths():
    trades=pd.DataFrame({"year":[2024]*3,"plus5_before_stop_7_5":[True,False,False],
        "barrier_outcome_stop_7_5":["target","stop","none"],"hit_plus_5_within_1d":[False]*3,
        "hit_plus_5_within_3d":[True,False,False],"hit_plus_5_within_5d":[True,False,False],"hit_plus_5pct":[True,False,False]})
    row=barrier_analysis(trades).iloc[0]
    assert row.plus5_before_minus7_5==1/3
    assert row.minus7_5_before_plus5==1/3
    assert row.neither_within_10d==1/3


def test_cluster_variance_test_is_seeded_and_bounded():
    trades=pd.DataFrame({"year":[2023,2024,2024,2025,2025,2026],"ticker":["A","A","B","A","B","B"],"exit_date":pd.date_range("2023-01-01",periods=6),"net_return":[.05,-.08,.05,.05,-.08,.05]})
    first=variance_test(trades,-.02,-.04,200); second=variance_test(trades,-.02,-.04,200)
    assert np.allclose(first.probability,second.probability)
    assert first.probability.between(0,1).all()
