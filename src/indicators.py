"""Point-in-time indicators calculated only from current and prior rows."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    lookback: int = 252,
    min_periods: int | None = None,
) -> pd.Series:
    """Rolling Cov(stock, market) / Var(market), aligned without future data."""
    minimum = lookback if min_periods is None else min_periods
    aligned_stock, aligned_market = stock_returns.align(market_returns, join="left")
    covariance = aligned_stock.rolling(lookback, min_periods=minimum).cov(aligned_market)
    variance = aligned_market.rolling(lookback, min_periods=minimum).var()
    return covariance.div(variance.replace(0, np.nan)).rename("beta252")


def range_position(price: pd.Series, low: pd.Series, high: pd.Series) -> pd.Series:
    width = high - low
    result = (price - low).div(width.replace(0, np.nan))
    return result.where(width.ne(0), 0.5).rename("range_position")


def add_indicators(
    prices: pd.DataFrame,
    market_ticker: str = "SPY",
    beta_lookback: int = 252,
    range_lookback: int = 100,
    dollar_volume_lookback: int = 20,
) -> pd.DataFrame:
    """Enrich a (date, ticker) price panel with all base indicators."""
    if not isinstance(prices.index, pd.MultiIndex) or prices.index.names != ["date", "ticker"]:
        raise ValueError("prices must use a (date, ticker) MultiIndex")
    result = prices.sort_index().copy()
    market = result.xs(market_ticker, level="ticker")["adj_close"].pct_change(fill_method=None)
    pieces: list[pd.DataFrame] = []
    for ticker, frame in result.groupby(level="ticker", sort=False):
        item = frame.droplevel("ticker").copy()
        item["return_1d"] = item["adj_close"].pct_change(fill_method=None)
        item["beta252"] = rolling_beta(item["return_1d"], market, beta_lookback)
        item["low_range"] = item["adj_close"].rolling(range_lookback, min_periods=range_lookback).min()
        item["high_range"] = item["adj_close"].rolling(range_lookback, min_periods=range_lookback).max()
        item["sma_range"] = item["adj_close"].rolling(range_lookback, min_periods=range_lookback).mean()
        item["range_position"] = range_position(item["adj_close"], item["low_range"], item["high_range"])
        item["distance_sma"] = item["adj_close"].div(item["sma_range"]) - 1.0
        item["dollar_volume"] = item["close"] * item["volume"]
        item["average_dollar_volume"] = item["dollar_volume"].rolling(
            dollar_volume_lookback, min_periods=dollar_volume_lookback
        ).mean()
        item["history_days"] = np.arange(1, len(item) + 1)
        item["ticker"] = ticker
        pieces.append(item.reset_index().set_index(["date", "ticker"]))
    return pd.concat(pieces).sort_index()


def consecutive_down_days(returns: pd.Series) -> pd.Series:
    """Count consecutive negative close-to-close returns through each date."""
    down = returns.lt(0) & returns.notna()
    groups = (~down).cumsum()
    return down.groupby(groups).cumsum().astype(int).rename("consecutive_down_days")


def add_diagnostic_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    """Add the small, predeclared diagnostic set without future leakage.

    SMA slopes are five-session percentage changes in the respective SMA.
    Every field uses prices available at or before the row's close.
    """
    result = panel.sort_index().copy()
    pieces = []
    for ticker, frame in result.groupby(level="ticker", sort=False):
        item = frame.droplevel("ticker").copy()
        close = item["adj_close"]
        for horizon in (5, 10, 20, 60):
            item[f"previous_{horizon}d_return"] = close.div(close.shift(horizon)) - 1.0
        item["sma20"] = close.rolling(20, min_periods=20).mean()
        item["sma50"] = close.rolling(50, min_periods=50).mean()
        if "sma_range" not in item or item["sma_range"].isna().all():
            item["sma_range"] = close.rolling(100, min_periods=100).mean()
        item["distance_sma20"] = close.div(item["sma20"]) - 1.0
        item["distance_sma50"] = close.div(item["sma50"]) - 1.0
        item["distance_sma100"] = close.div(item["sma_range"]) - 1.0
        item["sma20_slope"] = item["sma20"].div(item["sma20"].shift(5)) - 1.0
        item["sma50_slope"] = item["sma50"].div(item["sma50"].shift(5)) - 1.0
        item["consecutive_down_days"] = consecutive_down_days(close.pct_change(fill_method=None))
        item["drawdown_from_100d_high"] = close.div(item["high_range"]) - 1.0
        item["ticker"] = ticker
        pieces.append(item.reset_index().set_index(["date", "ticker"]))
    return pd.concat(pieces).sort_index()
