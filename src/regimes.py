"""Market and optional VIX regime classification."""

import pandas as pd


def market_regime(spy_close: pd.Series, lookback: int = 200) -> pd.Series:
    sma = spy_close.rolling(lookback, min_periods=lookback).mean()
    return pd.Series(
        pd.NA, index=spy_close.index, dtype="object", name="market_regime"
    ).mask(spy_close.ge(sma), "bull").mask(spy_close.lt(sma), "bear")


def vix_regime(vix_close: pd.Series) -> pd.Series:
    result = pd.Series(pd.NA, index=vix_close.index, dtype="object", name="vix_regime")
    result = result.mask(vix_close.lt(20), "under_20")
    result = result.mask(vix_close.ge(20) & vix_close.le(30), "20_to_30")
    return result.mask(vix_close.gt(30), "over_30")
