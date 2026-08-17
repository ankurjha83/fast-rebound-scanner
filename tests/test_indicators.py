import numpy as np
import pandas as pd

from src.indicators import add_diagnostic_indicators, range_position, rolling_beta
from src.regimes import market_regime


def test_range_position_and_flat_range():
    price = pd.Series([10.0, 15.0, 20.0, 10.0])
    low = pd.Series([10.0, 10.0, 10.0, 10.0])
    high = pd.Series([20.0, 20.0, 20.0, 10.0])
    assert range_position(price, low, high).tolist() == [0.0, 0.5, 1.0, 0.5]


def test_rolling_beta_has_no_future_information():
    market = pd.Series([0.01, -0.02, 0.03, 0.01, -0.01])
    stock = market * 2
    beta = rolling_beta(stock, market, lookback=3)
    assert beta.iloc[:2].isna().all()
    np.testing.assert_allclose(beta.iloc[2:], 2.0)
    changed_future = stock.copy()
    changed_future.iloc[-1] = 99
    changed = rolling_beta(changed_future, market, lookback=3)
    pd.testing.assert_series_equal(beta.iloc[:4], changed.iloc[:4])


def test_market_regime_uses_trailing_sma_only():
    close = pd.Series([1.0, 2.0, 3.0, 1.0], index=pd.date_range("2024-01-01", periods=4))
    result = market_regime(close, lookback=3)
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == "bull"
    assert result.iloc[3] == "bear"


def test_previous_five_day_return_has_no_future_information():
    dates = pd.date_range("2024-01-01", periods=8)
    index = pd.MultiIndex.from_product([dates, ["TEST"]], names=["date", "ticker"])
    close = pd.Series([10, 11, 12, 13, 14, 15, 16, 99.0], index=index)
    frame = pd.DataFrame({"adj_close": close, "high_range": 100.0, "sma_range": 12.0})
    result = add_diagnostic_indicators(frame)
    assert result.loc[(dates[5], "TEST"), "previous_5d_return"] == 0.5
    changed = frame.copy(); changed.loc[(dates[-1], "TEST"), "adj_close"] = 1_000
    changed_result = add_diagnostic_indicators(changed)
    pd.testing.assert_series_equal(
        result.loc[(slice(None, dates[-2]), "TEST"), "previous_5d_return"],
        changed_result.loc[(slice(None, dates[-2]), "TEST"), "previous_5d_return"],
    )
