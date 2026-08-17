"""Point-in-time historical S&P 500 universe construction.

The membership source is MIT-licensed fja05680/sp500. Yahoo price coverage for
removed/delisted members is incomplete, so coverage failures are measured and
reported rather than silently dropping them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config import CONFIG


MEMBERSHIP_SOURCE = "https://github.com/fja05680/sp500"
MEMBERSHIP_FILE = CONFIG.cache_dir.parent / "universe" / "sp500_historical.csv"


@dataclass
class HistoricalMembership:
    snapshots: pd.DataFrame
    symbols: tuple[str, ...]

    def mask(self, ticker: str, dates: pd.Index) -> np.ndarray:
        """Point-in-time membership for arbitrary trading dates."""
        snapshot_dates = self.snapshots.index.to_numpy(dtype="datetime64[ns]")
        positions = np.searchsorted(snapshot_dates, pd.DatetimeIndex(dates).to_numpy(), side="right") - 1
        valid = positions >= 0
        output = np.zeros(len(dates), dtype=bool)
        if valid.any():
            values = self.snapshots["members"].to_numpy(dtype=object)
            output[valid] = [ticker in values[position] for position in positions[valid]]
        return output


def load_historical_membership(
    path: str | Path = MEMBERSHIP_FILE,
    start: str = "2009-01-01",
) -> HistoricalMembership:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame.loc[frame["date"].ge(pd.Timestamp(start))].copy()
    if frame.empty:
        raise ValueError("historical membership file has no rows in the requested range")
    frame["members"] = frame["tickers"].str.split(",").map(frozenset)
    frame = frame.set_index("date").sort_index()
    symbols = tuple(sorted(set().union(*frame["members"])))
    return HistoricalMembership(frame[["members"]], symbols)


def attach_point_in_time_membership(panel: pd.DataFrame, membership: HistoricalMembership) -> pd.DataFrame:
    result = panel.copy()
    result["point_in_time_member"] = False
    for ticker, frame in result.groupby(level="ticker", sort=False):
        dates = frame.index.get_level_values("date")
        result.loc[frame.index, "point_in_time_member"] = membership.mask(ticker, dates)
    return result


def broad_eligibility(
    frame: pd.DataFrame,
    require_market_cap: bool,
    min_beta: float = 2.0,
    min_price: float = 10.0,
    min_dollar_volume: float = 100_000_000.0,
    min_market_cap: float = 10_000_000_000.0,
) -> pd.Series:
    """Historical eligibility with an explicit strict/no-cap switch."""
    required = {"point_in_time_member", "beta252", "adj_close", "average_dollar_volume", "history_days"}
    if missing := required - set(frame.columns):
        raise ValueError(f"broad eligibility columns missing: {sorted(missing)}")
    eligible = (
        frame["point_in_time_member"].fillna(False)
        & frame["beta252"].ge(min_beta)
        & frame["adj_close"].ge(min_price)
        & frame["average_dollar_volume"].ge(min_dollar_volume)
        & frame["history_days"].ge(252)
    )
    if require_market_cap:
        if "historical_market_cap" not in frame:
            return pd.Series(False, index=frame.index, name="eligible")
        eligible &= frame["historical_market_cap"].notna() & frame["historical_market_cap"].ge(min_market_cap)
    return eligible.rename("eligible")
