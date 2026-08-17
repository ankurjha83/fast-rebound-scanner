"""Current-market watchlist screener; labels are not trade recommendations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def classify_range(value: float) -> str:
    if pd.isna(value):
        return "UNAVAILABLE"
    if value <= .25:
        return "CANDIDATE"
    if value <= .40:
        return "WATCH"
    if value <= .75:
        return "NEUTRAL"
    return "EXTENDED"


def current_screener(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, frame in panel.groupby(level="ticker"):
        latest = frame.droplevel("ticker").dropna(subset=["adj_close"]).iloc[-1]
        rows.append({
            "Ticker": ticker,
            "Price": latest["adj_close"],
            "Market Cap": latest.get("market_cap", np.nan),
            "Market Cap Proxy": latest.get("market_cap_is_proxy", False),
            "Beta252": latest.get("beta252", np.nan),
            "100D Low": latest.get("low_range", np.nan),
            "100D High": latest.get("high_range", np.nan),
            "Range Position": latest.get("range_position", np.nan),
            "SMA100": latest.get("sma_range", np.nan),
            "% vs SMA100": latest.get("distance_sma", np.nan),
            "Average Dollar Volume": latest.get("average_dollar_volume", np.nan),
            "Eligible": bool(latest.get("eligible", False)),
            "Signal": classify_range(latest.get("range_position", np.nan)),
        })
    return pd.DataFrame(rows).sort_values(["Range Position", "Ticker"], na_position="last")
