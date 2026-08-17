"""Broad, predeclared parameter-grid robustness analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import CONFIG, ResearchConfig
from src.indicators import range_position
from src.metrics import performance_metrics


def _fast_fixed_hold(prepared: pd.DataFrame, hold: int, config: ResearchConfig):
    """Vectorized fixed-fraction engine for broad-grid diagnostics.

    With eight stocks the 10-position cap cannot bind. Each ticker sleeve is
    flat until a signal, enters next open, and cannot re-enter until its fixed
    hold exits. Daily sleeve returns are aggregated with a 10% portfolio weight.
    """
    all_dates = prepared.index.get_level_values("date").unique().sort_values()
    contributions = pd.Series(0.0, index=all_dates)
    exposures = pd.Series(0.0, index=all_dates)
    trade_rows = []
    one_way_cost = config.commission_rate + config.slippage_rate
    for ticker, frame in prepared.groupby(level="ticker", sort=False):
        item = frame.droplevel("ticker").sort_index()
        signal_locations = np.flatnonzero(item["entry_signal"].fillna(False).to_numpy())
        next_available = 0
        close_returns = item["adj_close"].pct_change(fill_method=None).fillna(0.0)
        for signal_location in signal_locations:
            entry_location = signal_location + 1
            if entry_location >= len(item) or entry_location < next_available:
                continue
            exit_location = min(entry_location + hold - 1, len(item) - 1)
            entry_date, exit_date = item.index[entry_location], item.index[exit_location]
            entry_open = item.iloc[entry_location]["adj_open"]
            exit_close = item.iloc[exit_location]["adj_close"]
            if not np.isfinite(entry_open) or entry_open <= 0 or not np.isfinite(exit_close):
                continue
            held_dates = item.index[entry_location:exit_location + 1]
            sleeve = close_returns.loc[held_dates].copy()
            sleeve.iloc[0] = item.iloc[entry_location]["adj_close"] / entry_open - 1.0
            sleeve.iloc[0] -= one_way_cost
            sleeve.iloc[-1] -= one_way_cost
            contributions.loc[held_dates] += config.position_fraction * sleeve
            exposures.loc[held_dates] += config.position_fraction
            gross_return = exit_close / entry_open - 1.0
            trade_rows.append({
                "ticker": ticker, "signal_date": item.index[signal_location],
                "entry_date": entry_date, "exit_date": exit_date,
                "net_return": gross_return - 2 * one_way_cost,
                "holding_days": exit_location - entry_location + 1,
                "net_pnl": config.initial_capital * config.position_fraction * (gross_return - 2 * one_way_cost),
                "gross_pnl": config.initial_capital * config.position_fraction * gross_return,
            })
            next_available = exit_location + 1
    equity_values = config.initial_capital * (1.0 + contributions).cumprod()
    equity = pd.DataFrame({"equity": equity_values, "exposure": exposures.clip(upper=1.0)})
    return equity, pd.DataFrame(trade_rows)


def robustness_grid(
    panel: pd.DataFrame,
    config: ResearchConfig = CONFIG,
    lookbacks=(50, 75, 100, 125, 150, 200),
    thresholds=(.05, .10, .15, .20, .25, .30, .35, .40),
    holding_periods=(10, 20, 30, 45, 60, 90),
) -> pd.DataFrame:
    rows = []
    base = panel.copy()
    for lookback in lookbacks:
        prepared_parts = []
        for ticker, frame in base.groupby(level="ticker", sort=False):
            item = frame.droplevel("ticker").copy()
            item["low_range"] = item["adj_close"].rolling(lookback, min_periods=lookback).min()
            item["high_range"] = item["adj_close"].rolling(lookback, min_periods=lookback).max()
            item["sma_range"] = item["adj_close"].rolling(lookback, min_periods=lookback).mean()
            item["range_position"] = range_position(item["adj_close"], item["low_range"], item["high_range"])
            item["distance_sma"] = item["adj_close"] / item["sma_range"] - 1
            item["ticker"] = ticker
            prepared_parts.append(item.reset_index().set_index(["date", "ticker"]))
        prepared = pd.concat(prepared_parts).sort_index()
        for threshold in thresholds:
            candidate = prepared.copy()
            candidate["entry_signal"] = candidate["eligible"] & candidate["range_position"].le(threshold)
            for hold in holding_periods:
                equity, trades = _fast_fixed_hold(candidate, hold, config)
                metrics = performance_metrics(equity, trades)
                rows.append({"lookback": lookback, "threshold": threshold, "holding_period": hold, **metrics})
    return pd.DataFrame(rows)
