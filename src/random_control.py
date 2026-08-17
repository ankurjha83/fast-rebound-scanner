"""Fixed-seed matched random-entry control."""

from __future__ import annotations

import numpy as np
import pandas as pd


def matched_random_control(
    panel: pd.DataFrame,
    actual_trades: pd.DataFrame,
    simulations: int = 1_000,
    seed: int = 20260816,
    round_trip_cost: float = 0.002,
) -> pd.DataFrame:
    """Match ticker and holding period for each trade, randomizing entry date."""
    if actual_trades.empty:
        return pd.DataFrame(columns=["simulation", "mean_return", "median_return", "win_rate"])
    by_ticker = {t: f.droplevel("ticker").sort_index() for t, f in panel.groupby(level="ticker")}
    eligible_dates = {
        t: f.index[f["eligible"].fillna(False)].to_numpy() for t, f in by_ticker.items()
    }
    rng = np.random.default_rng(seed)
    rows = []
    specs = actual_trades[["ticker", "holding_days"]].itertuples(index=False)
    specs = [(row.ticker, max(1, int(row.holding_days))) for row in specs]
    for simulation in range(simulations):
        returns = []
        for ticker, hold in specs:
            frame = by_ticker.get(ticker)
            candidates = eligible_dates.get(ticker, np.array([]))
            if frame is None or not len(candidates):
                continue
            valid = [d for d in candidates if frame.index.get_loc(d) + hold < len(frame)]
            if not valid:
                continue
            signal_date = valid[rng.integers(len(valid))]
            signal_location = frame.index.get_loc(signal_date)
            entry_location = signal_location + 1
            exit_location = min(entry_location + hold - 1, len(frame) - 1)
            gross = frame.iloc[exit_location]["adj_close"] / frame.iloc[entry_location]["adj_open"] - 1.0
            returns.append(gross - round_trip_cost)
        series = pd.Series(returns, dtype=float)
        rows.append({
            "simulation": simulation,
            "mean_return": series.mean(),
            "median_return": series.median(),
            "win_rate": series.gt(0).mean() if len(series) else np.nan,
            "trades": len(series),
        })
    return pd.DataFrame(rows)


def actual_percentile(actual_value: float, simulations: pd.Series) -> float:
    clean = simulations.dropna()
    return 100.0 * clean.le(actual_value).mean() if len(clean) else np.nan


def calendar_sleeve_metrics(
    panel: pd.DataFrame,
    trade_specs: list[tuple[str, int, int]],
    one_way_cost: float = 0.001,
    position_fraction: float = 0.10,
    max_positions: int = 10,
) -> dict[str, float]:
    """Fast calendar portfolio approximation for matched random controls.

    Each spec is ``(ticker, signal_row_position, holding_days)``. Positions use
    a fixed 10% sleeve, next-row open entry, and close exit. Daily exposure is
    scaled back if random overlap would exceed the ten-position cap.
    """
    dates = panel.index.get_level_values("date").unique().sort_values()
    date_positions = pd.Series(np.arange(len(dates)), index=dates)
    frames = {t: f.droplevel("ticker").sort_index() for t, f in panel.groupby(level="ticker", sort=False)}
    return _calendar_sleeve_metrics_precomputed(
        frames, dates, date_positions, trade_specs, one_way_cost,
        position_fraction, max_positions,
    )


def _calendar_sleeve_metrics_precomputed(
    frames: dict[str, pd.DataFrame],
    dates: pd.Index,
    date_positions: pd.Series,
    trade_specs: list[tuple[str, int, int]],
    one_way_cost: float,
    position_fraction: float = 0.10,
    max_positions: int = 10,
) -> dict[str, float]:
    contributions = np.zeros(len(dates), dtype=float)
    counts = np.zeros(len(dates), dtype=float)
    trade_returns = []
    for ticker, signal_position, hold in trade_specs:
        frame = frames.get(ticker)
        if frame is None:
            continue
        entry = signal_position + 1
        exit_at = entry + max(1, int(hold)) - 1
        if entry >= len(frame) or exit_at >= len(frame):
            continue
        held = frame.iloc[entry:exit_at + 1]
        returns = held["adj_close"].pct_change(fill_method=None).fillna(0.0).to_numpy(copy=True)
        returns[0] = held.iloc[0]["adj_close"] / held.iloc[0]["adj_open"] - 1.0 - one_way_cost
        returns[-1] -= one_way_cost
        locations = date_positions.reindex(held.index).dropna().astype(int).to_numpy()
        if len(locations) != len(returns):
            continue
        contributions[locations] += returns
        counts[locations] += 1
        trade_returns.append(held.iloc[-1]["adj_close"] / held.iloc[0]["adj_open"] - 1.0 - 2 * one_way_cost)
    scale = np.ones(len(dates))
    crowded = counts > max_positions
    scale[crowded] = max_positions / counts[crowded]
    daily = position_fraction * contributions * scale
    equity = pd.Series((1.0 + daily).cumprod(), index=dates)
    drawdown = equity / equity.cummax() - 1.0
    std = pd.Series(daily).std(ddof=1)
    return {
        "total_return": equity.iloc[-1] - 1.0 if len(equity) else np.nan,
        "sharpe": pd.Series(daily).mean() / std * np.sqrt(252) if std else np.nan,
        "maximum_drawdown": drawdown.min() if len(drawdown) else np.nan,
        "mean_trade_return": pd.Series(trade_returns).mean(),
        "trades": len(trade_returns),
    }


def matched_random_portfolio_control(
    panel: pd.DataFrame,
    actual_trades: pd.DataFrame,
    simulations: int = 1_000,
    seed: int = 20260816,
    one_way_cost: float = 0.001,
    position_fraction: float = 0.10,
    max_positions: int = 10,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Calendar-aware random control matching ticker, count, and holding period."""
    frames = {t: f.droplevel("ticker").sort_index() for t, f in panel.groupby(level="ticker", sort=False)}
    eligible_positions = {
        ticker: np.flatnonzero(frame["eligible"].fillna(False).to_numpy())
        for ticker, frame in frames.items()
    }
    actual_specs = []
    dates = panel.index.get_level_values("date").unique().sort_values()
    date_positions = pd.Series(np.arange(len(dates)), index=dates)
    for trade in actual_trades.itertuples():
        frame = frames.get(trade.ticker)
        if frame is None or pd.Timestamp(trade.signal_date) not in frame.index:
            continue
        actual_specs.append((trade.ticker, int(frame.index.get_loc(pd.Timestamp(trade.signal_date))), int(trade.holding_days)))
    actual_metrics = _calendar_sleeve_metrics_precomputed(
        frames, dates, date_positions, actual_specs, one_way_cost,
        position_fraction, max_positions,
    )
    rng = np.random.default_rng(seed)
    rows = []
    trade_template = [(row.ticker, int(row.holding_days)) for row in actual_trades.itertuples()]
    for simulation in range(simulations):
        specs = []
        occupied: dict[str, list[tuple[int, int]]] = {}
        for ticker, hold in trade_template:
            frame = frames.get(ticker)
            candidates = eligible_positions.get(ticker, np.array([], dtype=int))
            if frame is None or not len(candidates):
                continue
            valid = candidates[candidates + hold < len(frame)]
            if not len(valid):
                continue
            chosen = None
            for _ in range(50):
                candidate = int(valid[rng.integers(len(valid))])
                interval = (candidate + 1, candidate + hold)
                if all(interval[1] < old[0] or interval[0] > old[1] for old in occupied.get(ticker, [])):
                    chosen = candidate; occupied.setdefault(ticker, []).append(interval); break
            if chosen is not None:
                specs.append((ticker, chosen, hold))
        rows.append({"simulation": simulation, **_calendar_sleeve_metrics_precomputed(
            frames, dates, date_positions, specs, one_way_cost,
            position_fraction, max_positions,
        )})
    return pd.DataFrame(rows), actual_metrics
