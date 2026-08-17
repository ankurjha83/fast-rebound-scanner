import pandas as pd

from src.expanded_universe import HistoricalMembership, attach_point_in_time_membership, broad_eligibility
from src.expanded_retest import _benchmark_regime_masks, confirmation_signal, strategy_signal


def test_universe_membership_changes_through_time():
    snapshots = pd.DataFrame(
        {"members": [frozenset({"OLD"}), frozenset({"NEW"})]},
        index=pd.to_datetime(["2020-01-01", "2020-02-01"]),
    )
    membership = HistoricalMembership(snapshots, ("NEW", "OLD"))
    dates = pd.to_datetime(["2020-01-15", "2020-02-15"])
    index = pd.MultiIndex.from_product([dates, ["OLD", "NEW"]], names=["date", "ticker"])
    result = attach_point_in_time_membership(pd.DataFrame(index=index), membership)
    assert result.loc[(dates[0], "OLD"), "point_in_time_member"]
    assert not result.loc[(dates[1], "OLD"), "point_in_time_member"]
    assert not result.loc[(dates[0], "NEW"), "point_in_time_member"]
    assert result.loc[(dates[1], "NEW"), "point_in_time_member"]


def test_historical_beta_liquidity_and_market_cap_eligibility():
    frame = pd.DataFrame({
        "point_in_time_member": [True, True, True, True],
        "beta252": [2.1, 1.9, 2.1, 2.1],
        "adj_close": [20.0, 20.0, 20.0, 20.0],
        "average_dollar_volume": [200e6, 200e6, 50e6, 200e6],
        "history_days": [300, 300, 300, 300],
        "historical_market_cap": [12e9, 12e9, 12e9, float("nan")],
    })
    assert broad_eligibility(frame, False).tolist() == [True, False, False, True]
    assert broad_eligibility(frame, True).tolist() == [True, False, False, False]


def test_three_five_ten_day_momentum_has_no_lookahead():
    dates = pd.date_range("2024-01-01", periods=12)
    index = pd.MultiIndex.from_product([dates, ["TEST"]], names=["date", "ticker"])
    frame = pd.DataFrame({"adj_close": range(10, 22)}, index=index)
    for window in (3, 5, 10):
        signal = confirmation_signal(frame, window)
        assert not signal.iloc[:window].any()
        assert signal.iloc[window]
    changed = frame.copy(); changed.iloc[-1, 0] = 999
    pd.testing.assert_series_equal(
        confirmation_signal(frame, 5).iloc[:-1], confirmation_signal(changed, 5).iloc[:-1]
    )


def test_qqq_sma200_regime_is_applied_on_signal_date():
    dates = pd.date_range("2024-01-01", periods=7)
    index = pd.MultiIndex.from_product([dates, ["TEST"]], names=["date", "ticker"])
    frame = pd.DataFrame({
        "adj_close": [10, 9, 8, 7, 6, 11, 12], "eligible": True,
        "range_position": .20, "qqq_above_sma200": [False]*5+[True,False],
        "qqq_60d_return": .01,
    }, index=index)
    signal = strategy_signal(frame, "positive_5d_qqq_bull")
    assert signal.iloc[5]
    assert not signal.iloc[6]


def test_benchmark_bull_and_bear_masks_are_complements_for_object_dtype():
    frame = pd.DataFrame({"qqq_above_sma200": pd.Series([True, False, None], dtype=object)})
    bull, bear = _benchmark_regime_masks(frame, "qqq")
    assert bull.tolist() == [True, False, False]
    assert bear.tolist() == [False, True, True]
    assert not (bull & bear).any()
    assert (bull | bear).all()
