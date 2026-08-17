"""Forward-return event studies for conditional and unconditional samples."""

from __future__ import annotations

import numpy as np
import pandas as pd


FORWARD_HORIZONS = (5, 10, 20, 30, 60, 90, 120)
RANGE_BUCKETS = [-np.inf, 0.10, 0.25, 0.50, 0.75, 0.90, np.inf]
RANGE_LABELS = ["0-10%", "10-25%", "25-50%", "50-75%", "75-90%", "90-100%"]
BETA_BUCKETS = [2.0, 2.5, 3.0, 4.0, np.inf]
BETA_LABELS = ["2.0-2.5", "2.5-3.0", "3.0-4.0", ">4.0"]


def add_forward_returns(panel: pd.DataFrame, horizons=FORWARD_HORIZONS) -> pd.DataFrame:
    result = panel.sort_index().copy()
    for horizon in horizons:
        future = result.groupby(level="ticker")["adj_close"].shift(-horizon)
        result[f"forward_{horizon}d"] = future.div(result["adj_close"]) - 1.0
    return result


def _summary(values: pd.Series) -> dict[str, float]:
    clean = values.dropna()
    return {
        "mean_return": clean.mean(),
        "median_return": clean.median(),
        "win_probability": clean.gt(0).mean() if len(clean) else np.nan,
        "p25": clean.quantile(0.25),
        "p75": clean.quantile(0.75),
        "observations": len(clean),
    }


def event_study(
    panel: pd.DataFrame,
    signal_mask: pd.Series,
    eligible_mask: pd.Series,
    horizons=FORWARD_HORIZONS,
) -> pd.DataFrame:
    enriched = add_forward_returns(panel, horizons)
    rows = []
    for sample, mask in (("bottom_quartile", signal_mask), ("unconditional_eligible", eligible_mask)):
        for horizon in horizons:
            rows.append({"sample": sample, "horizon": horizon, **_summary(enriched.loc[mask, f"forward_{horizon}d"])})
    return pd.DataFrame(rows)


def range_bucket_study(panel: pd.DataFrame, eligible_mask: pd.Series, horizons=(10, 20, 30, 60, 90)) -> pd.DataFrame:
    enriched = add_forward_returns(panel, horizons)
    buckets = pd.cut(
        enriched["range_position"], RANGE_BUCKETS, labels=RANGE_LABELS,
        right=True, include_lowest=True,
    )
    rows = []
    for bucket in RANGE_LABELS:
        mask = eligible_mask & buckets.eq(bucket)
        for horizon in horizons:
            rows.append({"range_bucket": bucket, "horizon": horizon, **_summary(enriched.loc[mask, f"forward_{horizon}d"])})
    return pd.DataFrame(rows)


def beta_bucket_study(panel: pd.DataFrame, trades: pd.DataFrame | None = None, horizon: int = 30) -> pd.DataFrame:
    enriched = add_forward_returns(panel, [horizon])
    buckets = pd.cut(enriched["beta252"], BETA_BUCKETS, labels=BETA_LABELS, right=False)
    rows = []
    for bucket in BETA_LABELS:
        values = enriched.loc[enriched["eligible"] & buckets.eq(bucket), f"forward_{horizon}d"]
        row = {"beta_bucket": bucket, **_summary(values)}
        if trades is not None and not trades.empty:
            trade_buckets = pd.cut(trades["beta"], BETA_BUCKETS, labels=BETA_LABELS, right=False)
            subset = trades.loc[trade_buckets.eq(bucket)]
            row.update({
                "trade_win_rate": subset["net_return"].gt(0).mean() if len(subset) else np.nan,
                "mae": subset["mae"].mean(), "mfe": subset["mfe"].mean(),
                "worst_mae": subset["mae"].min(),
            })
        rows.append(row)
    return pd.DataFrame(rows)
