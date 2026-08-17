"""Point-in-time eligibility rules for the research universe."""

from __future__ import annotations

import pandas as pd


def attach_market_cap(
    frame: pd.DataFrame,
    historical_market_caps: dict[str, pd.Series] | None = None,
    current_market_caps: dict[str, float] | None = None,
    allow_current_proxy: bool = True,
) -> pd.DataFrame:
    """Attach market cap, explicitly flagging any current-snapshot proxy."""
    result = frame.copy()
    result["market_cap"] = pd.NA
    result["market_cap_is_proxy"] = False
    historical_market_caps = historical_market_caps or {}
    current_market_caps = current_market_caps or {}
    for ticker in result.index.get_level_values("ticker").unique():
        mask = result.index.get_level_values("ticker") == ticker
        dates = result.index.get_level_values("date")[mask]
        history = historical_market_caps.get(ticker)
        if history is not None and not history.empty:
            values = history.sort_index().reindex(dates, method="ffill")
            result.loc[mask, "market_cap"] = values.to_numpy()
        missing = mask & result["market_cap"].isna().to_numpy()
        if allow_current_proxy and ticker in current_market_caps and missing.any():
            result.loc[missing, "market_cap"] = float(current_market_caps[ticker])
            result.loc[missing, "market_cap_is_proxy"] = True
    result["market_cap"] = pd.to_numeric(result["market_cap"], errors="coerce")
    return result


def eligible_observations(
    frame: pd.DataFrame,
    min_beta: float = 2.0,
    min_market_cap: float = 10_000_000_000,
    min_price: float = 10.0,
    min_average_dollar_volume: float = 100_000_000,
    min_history_days: int = 252,
) -> pd.Series:
    required = ["beta252", "market_cap", "adj_close", "average_dollar_volume", "history_days"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"eligibility columns missing: {sorted(missing)}")
    return (
        frame[required].notna().all(axis=1)
        & frame["beta252"].ge(min_beta)
        & frame["market_cap"].ge(min_market_cap)
        & frame["adj_close"].ge(min_price)
        & frame["average_dollar_volume"].ge(min_average_dollar_volume)
        & frame["history_days"].ge(min_history_days)
    ).rename("eligible")
