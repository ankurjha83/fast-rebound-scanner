"""Signal definitions; signals are observed at close and executed next open."""

from __future__ import annotations

from enum import Enum

import pandas as pd


class EntryStrategy(str, Enum):
    PURE = "pure"
    ABOVE_SMA = "above_100dma"
    NEAR_SMA = "near_100dma"


class ConfirmationVariant(str, Enum):
    BASE = "base"
    SMA100_TREND = "sma100_trend"
    SMA20_RECOVERY = "sma20_recovery"
    POSITIVE_5D = "positive_5d_momentum"
    COMBINED = "sma100_and_positive_5d"


def generate_entry_signals(
    frame: pd.DataFrame,
    strategy: EntryStrategy | str = EntryStrategy.PURE,
    threshold: float = 0.25,
    near_sma_tolerance: float = 0.05,
) -> pd.Series:
    selected = EntryStrategy(strategy)
    required = {"eligible", "range_position", "adj_close", "sma_range", "distance_sma"}
    if missing := required - set(frame.columns):
        raise ValueError(f"signal columns missing: {sorted(missing)}")
    signal = frame["eligible"].fillna(False) & frame["range_position"].le(threshold)
    if selected is EntryStrategy.ABOVE_SMA:
        signal &= frame["adj_close"].ge(frame["sma_range"])
    elif selected is EntryStrategy.NEAR_SMA:
        signal &= frame["distance_sma"].abs().le(near_sma_tolerance)
    return signal.rename("entry_signal")


def sma_cross_above(close: pd.Series, moving_average: pd.Series) -> pd.Series:
    """Strict close cross: prior close <= prior SMA and current close > current SMA."""
    return (
        close.shift(1).le(moving_average.shift(1))
        & close.gt(moving_average)
        & close.notna()
        & moving_average.notna()
    ).rename("sma_cross_above")


def generate_confirmation_signals(
    frame: pd.DataFrame,
    variant: ConfirmationVariant | str,
    threshold: float = 0.25,
) -> pd.Series:
    """Four predeclared confirmations layered on the unchanged base signal."""
    selected = ConfirmationVariant(variant)
    required = {"eligible", "range_position", "adj_close", "sma_range", "sma20", "previous_5d_return"}
    if missing := required - set(frame.columns):
        raise ValueError(f"confirmation columns missing: {sorted(missing)}")
    base = frame["eligible"].fillna(False) & frame["range_position"].le(threshold)
    if selected is ConfirmationVariant.BASE:
        return base.rename("entry_signal")
    if selected is ConfirmationVariant.SMA100_TREND:
        return (base & frame["adj_close"].ge(frame["sma_range"])).rename("entry_signal")
    if selected is ConfirmationVariant.SMA20_RECOVERY:
        grouped = frame.groupby(level="ticker", sort=False)
        prior_close = grouped["adj_close"].shift(1)
        prior_sma = grouped["sma20"].shift(1)
        crosses = prior_close.le(prior_sma) & frame["adj_close"].gt(frame["sma20"])
        return (base & crosses).rename("entry_signal")
    if selected is ConfirmationVariant.POSITIVE_5D:
        return (base & frame["previous_5d_return"].gt(0)).rename("entry_signal")
    return (
        base
        & frame["adj_close"].ge(frame["sma_range"])
        & frame["previous_5d_return"].gt(0)
    ).rename("entry_signal")


def rank_signals(frame: pd.DataFrame, method: str = "lowest_range") -> pd.DataFrame:
    if method == "lowest_range":
        return frame.sort_values(["range_position", "beta252"], ascending=[True, False])
    if method == "highest_beta":
        return frame.sort_values(["beta252", "range_position"], ascending=[False, True])
    if method == "largest_decline":
        decline = frame["adj_close"].div(frame["high_range"]) - 1.0
        return frame.assign(_decline=decline).sort_values("_decline").drop(columns="_decline")
    raise ValueError(f"unknown ranking method: {method}")
