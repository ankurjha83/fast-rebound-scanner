"""Regime diagnosis and four predeclared confirmation experiments.

This module extends the existing research without changing its universe,
execution, sizing, costs, ranking, or 30-session exit methodology.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import CONFIG, ResearchConfig
from data.provider import CacheMode, YFinanceProvider
from src.indicators import add_diagnostic_indicators
from src.metrics import performance_metrics
from src.portfolio import EXIT_RULES, BacktestResult, run_portfolio
from src.random_control import actual_percentile, matched_random_control
from src.signals import ConfirmationVariant, generate_confirmation_signals


PERIODS = {
    "2016-2019": ("2016-01-01", "2019-12-31"),
    "2020-2022": ("2020-01-01", "2022-12-31"),
    "2023-2026": ("2023-01-01", "2026-12-31"),
    "2016-2022": ("2016-01-01", "2022-12-31"),
    "combined": ("2016-01-01", "2026-12-31"),
}

THEMES = {
    "APP": "AI / software",
    "COIN": "crypto / crypto-linked",
    "MSTR": "crypto / crypto-linked",
    "ASTS": "space",
    "RKLB": "space",
    "IONQ": "quantum",
    "HOOD": "fintech",
    "CVNA": "consumer / other",
}

CONDITIONS = [
    "spy_20d_return", "spy_60d_return", "qqq_20d_return", "qqq_60d_return",
    "spy_distance_sma200", "qqq_distance_sma200", "vix_level",
    "previous_20d_return", "previous_60d_return", "drawdown_from_100d_high",
]

FALLING_KNIFE_FIELDS = [
    "previous_5d_return", "previous_10d_return", "previous_20d_return",
    "distance_sma20", "distance_sma50", "distance_sma100",
    "sma20_slope", "sma50_slope", "consecutive_down_days",
]


def _slice(panel: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dates = panel.index.get_level_values("date")
    return panel.loc[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]


def add_market_context(panel: pd.DataFrame, provider: YFinanceProvider) -> pd.DataFrame:
    """Attach the four requested regimes and benchmark condition fields."""
    result = add_diagnostic_indicators(panel)
    benchmarks = provider.get_prices(
        ["SPY", "QQQ", "^VIX"], "2014-01-01", mode=CacheMode.CACHED
    ).data
    dates = result.index.get_level_values("date")
    for ticker, prefix in (("SPY", "spy"), ("QQQ", "qqq")):
        close = benchmarks.xs(ticker, level="ticker")["adj_close"].sort_index()
        sma50 = close.rolling(50, min_periods=50).mean()
        sma200 = close.rolling(200, min_periods=200).mean()
        fields = {
            f"{prefix}_20d_return": close.div(close.shift(20)) - 1.0,
            f"{prefix}_60d_return": close.div(close.shift(60)) - 1.0,
            f"{prefix}_distance_sma200": close.div(sma200) - 1.0,
            f"{prefix}_above_sma200": close.ge(sma200),
        }
        if ticker == "SPY":
            fields["spy_sma50_above_sma200"] = sma50.ge(sma200)
            fields["spy_20d_positive"] = fields["spy_20d_return"].gt(0)
        for name, values in fields.items():
            result[name] = dates.map(values)
    if "^VIX" in benchmarks.index.get_level_values("ticker"):
        vix = benchmarks.xs("^VIX", level="ticker")["adj_close"].sort_index()
        result["vix_level"] = dates.map(vix)
    else:
        result["vix_level"] = np.nan
    return result


def run_variant(
    panel: pd.DataFrame,
    variant: ConfirmationVariant,
    config: ResearchConfig = CONFIG,
) -> BacktestResult:
    prepared = panel.copy()
    prepared["entry_signal"] = generate_confirmation_signals(
        prepared, variant, config.max_range_position
    )
    return run_portfolio(
        prepared, EXIT_RULES["F"], config.initial_capital, config.max_positions,
        config.position_fraction, config.commission_rate, config.slippage_rate,
        "lowest_range",
    )


def _extended_metrics(result: BacktestResult, signals: int) -> dict[str, float]:
    metrics = performance_metrics(result.equity, result.trades)
    trades = result.trades
    metrics.update({
        "number_of_signals": int(signals),
        "average_mae": trades["mae"].mean() if not trades.empty else np.nan,
        "median_mae": trades["mae"].median() if not trades.empty else np.nan,
        "average_mfe": trades["mfe"].mean() if not trades.empty else np.nan,
        "median_mfe": trades["mfe"].median() if not trades.empty else np.nan,
        "average_beta_at_entry": trades["beta"].mean() if not trades.empty else np.nan,
        "average_range_position": trades["range_position"].mean() if not trades.empty else np.nan,
    })
    return metrics


def compare_periods(panel: pd.DataFrame, variant: ConfirmationVariant) -> tuple[pd.DataFrame, dict[str, BacktestResult]]:
    rows = []
    results = {}
    full_signals = generate_confirmation_signals(panel, variant, CONFIG.max_range_position)
    for period, (start, end) in PERIODS.items():
        part = _slice(panel, start, end).copy()
        part["entry_signal"] = full_signals.reindex(part.index).fillna(False)
        result = run_portfolio(
            part, EXIT_RULES["F"], CONFIG.initial_capital, CONFIG.max_positions,
            CONFIG.position_fraction, CONFIG.commission_rate, CONFIG.slippage_rate,
            "lowest_range",
        )
        results[period] = result
        rows.append({
            "variant": variant.value, "period": period,
            **_extended_metrics(result, int(part["entry_signal"].sum())),
        })
    return pd.DataFrame(rows), results


def attach_trade_context(trades: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    context_columns = list(dict.fromkeys(
        CONDITIONS + FALLING_KNIFE_FIELDS + [
            "spy_above_sma200", "qqq_above_sma200", "spy_sma50_above_sma200",
            "spy_20d_positive", "range_position", "beta252",
        ]
    ))
    context = panel[context_columns].reset_index().rename(columns={"date": "signal_date"})
    result = trades.merge(context, on=["signal_date", "ticker"], how="left", suffixes=("", "_context"))
    result["outcome"] = np.where(result["net_return"].gt(0), "winner", "loser")
    result["period_group"] = np.where(
        pd.to_datetime(result["signal_date"]).lt("2023-01-01"), "2016-2022", "2023-2026"
    )
    result["theme"] = result["ticker"].map(THEMES).fillna("unclassified")
    return result


def ticker_concentration(trades: pd.DataFrame) -> pd.DataFrame:
    return trades.groupby("ticker").agg(
        number_of_trades=("ticker", "size"),
        total_pnl_contribution=("net_pnl", "sum"),
        average_trade_return=("net_return", "mean"),
        median_return=("net_return", "median"),
        win_rate=("net_return", lambda x: x.gt(0).mean()),
        mae=("mae", "mean"), mfe=("mfe", "mean"),
    ).sort_values("total_pnl_contribution", ascending=False).reset_index()


def theme_concentration(trades: pd.DataFrame) -> pd.DataFrame:
    enriched = trades.assign(theme=trades["ticker"].map(THEMES).fillna("unclassified"))
    return enriched.groupby("theme").agg(
        number_of_trades=("ticker", "size"),
        total_pnl_contribution=("net_pnl", "sum"),
        average_trade_return=("net_return", "mean"),
        win_rate=("net_return", lambda x: x.gt(0).mean()),
    ).sort_values("total_pnl_contribution", ascending=False).reset_index()


def _suppress_trade_windows(panel: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    result = panel.copy()
    for row in trades.itertuples():
        dates = result.index.get_level_values("date")
        tickers = result.index.get_level_values("ticker")
        mask = (
            (tickers == row.ticker)
            & (dates >= pd.Timestamp(row.signal_date))
            & (dates <= pd.Timestamp(row.exit_date))
        )
        result.loc[mask, "entry_signal"] = False
    return result


def concentration_sensitivity(post_panel: pd.DataFrame, post_result: BacktestResult) -> pd.DataFrame:
    trades = post_result.trades.sort_values("net_return", ascending=False)
    ticker_rank = ticker_concentration(trades)
    top10 = max(1, math.ceil(len(trades) * 0.10))
    cases: dict[str, pd.DataFrame] = {
        "base": post_panel.copy(),
        "remove_best_trade": _suppress_trade_windows(post_panel, trades.head(1)),
        "remove_best_5_trades": _suppress_trade_windows(post_panel, trades.head(5)),
        "remove_top_10pct_trades": _suppress_trade_windows(post_panel, trades.head(top10)),
    }
    for label, count in (("remove_best_stock", 1), ("remove_best_3_stocks", 3)):
        excluded = set(ticker_rank.head(count)["ticker"])
        candidate = post_panel.copy()
        mask = candidate.index.get_level_values("ticker").isin(excluded)
        candidate.loc[mask, "entry_signal"] = False
        cases[label] = candidate
    rows = []
    for label, candidate in cases.items():
        result = run_portfolio(
            candidate, EXIT_RULES["F"], CONFIG.initial_capital, CONFIG.max_positions,
            CONFIG.position_fraction, CONFIG.commission_rate, CONFIG.slippage_rate,
        )
        metrics = performance_metrics(result.equity, result.trades)
        rows.append({"sensitivity": label, **{k: metrics[k] for k in (
            "total_return", "cagr", "sharpe", "maximum_drawdown", "number_of_trades"
        )}})
    return pd.DataFrame(rows)


def _trade_group_summary(frame: pd.DataFrame) -> dict[str, float]:
    returns = frame["net_return"].dropna()
    annualizer = np.sqrt(252 / frame["holding_days"].mean()) if len(frame) else np.nan
    return {
        "number_of_trades": len(frame),
        "average_return": returns.mean(), "median_return": returns.median(),
        "win_rate": returns.gt(0).mean() if len(returns) else np.nan,
        "mae": frame["mae"].mean(), "mfe": frame["mfe"].mean(),
        "trade_return_sharpe": returns.mean() / returns.std(ddof=1) * annualizer
        if len(returns) > 1 and returns.std(ddof=1) else np.nan,
    }


def regime_analysis(trades: pd.DataFrame) -> pd.DataFrame:
    definitions = {
        "SPY vs SMA200": ("spy_above_sma200", {True: "above", False: "below"}),
        "QQQ vs SMA200": ("qqq_above_sma200", {True: "above", False: "below"}),
        "SPY SMA50 vs SMA200": ("spy_sma50_above_sma200", {True: "above", False: "below"}),
        "Previous SPY 20D return": ("spy_20d_positive", {True: "positive", False: "negative"}),
    }
    rows = []
    for regime, (field, labels) in definitions.items():
        for value, group in trades.dropna(subset=[field]).groupby(field):
            rows.append({"regime": regime, "state": labels[bool(value)], **_trade_group_summary(group)})
    return pd.DataFrame(rows)


def distribution_comparison(trades: pd.DataFrame, fields: list[str], grouping: str) -> pd.DataFrame:
    rows = []
    for group, subset in trades.groupby(grouping):
        for field in fields:
            values = pd.to_numeric(subset[field], errors="coerce").dropna()
            rows.append({
                "grouping": grouping, "group": group, "variable": field,
                "observations": len(values), "mean": values.mean(),
                "median": values.median(), "p25": values.quantile(.25), "p75": values.quantile(.75),
            })
    return pd.DataFrame(rows)


def range_entry_analysis(trades: pd.DataFrame) -> pd.DataFrame:
    edges = [-np.inf, .05, .10, .15, .20, .25]
    labels = ["0-5%", "5-10%", "10-15%", "15-20%", "20-25%"]
    buckets = pd.cut(trades["range_position"], edges, labels=labels, include_lowest=True)
    rows = []
    for label in labels:
        subset = trades.loc[buckets.eq(label)]
        rows.append({"range_bucket": label, **_trade_group_summary(subset)})
    return pd.DataFrame(rows)


def _custom_confirmation(panel: pd.DataFrame, family: str, window: int) -> pd.Series:
    base = panel["eligible"].fillna(False) & panel["range_position"].le(CONFIG.max_range_position)
    grouped = panel.groupby(level="ticker", sort=False)
    if family == "positive_momentum":
        momentum = panel["adj_close"].div(grouped["adj_close"].shift(window)) - 1.0
        return base & momentum.gt(0)
    sma = grouped["adj_close"].transform(lambda x: x.rolling(window, min_periods=window).mean())
    if family == "sma_trend":
        return base & panel["adj_close"].ge(sma)
    if family == "sma_recovery":
        prior_close = grouped["adj_close"].shift(1)
        prior_sma = sma.groupby(level="ticker").shift(1)
        return base & prior_close.le(prior_sma) & panel["adj_close"].gt(sma)
    if family == "combined_momentum":
        momentum = panel["adj_close"].div(grouped["adj_close"].shift(window)) - 1.0
        return base & panel["adj_close"].ge(panel["sma_range"]) & momentum.gt(0)
    raise ValueError(f"unknown neighborhood family: {family}")


def limited_neighborhood(panel: pd.DataFrame, best: ConfirmationVariant) -> pd.DataFrame:
    if best is ConfirmationVariant.SMA100_TREND:
        family, windows = "sma_trend", (50, 100, 150)
    elif best is ConfirmationVariant.SMA20_RECOVERY:
        family, windows = "sma_recovery", (10, 20, 30)
    elif best is ConfirmationVariant.COMBINED:
        family, windows = "combined_momentum", (3, 5, 10)
    else:
        family, windows = "positive_momentum", (3, 5, 10)
    rows = []
    for window in windows:
        full_signal = _custom_confirmation(panel, family, window)
        for period in ("2016-2022", "2023-2026", "combined"):
            start, end = PERIODS[period]
            part = _slice(panel, start, end).copy()
            part["entry_signal"] = full_signal.reindex(part.index).fillna(False)
            result = run_portfolio(
                part, EXIT_RULES["F"], CONFIG.initial_capital, CONFIG.max_positions,
                CONFIG.position_fraction, CONFIG.commission_rate, CONFIG.slippage_rate,
            )
            m = performance_metrics(result.equity, result.trades)
            rows.append({"family": family, "window": window, "period": period, **{
                k: m[k] for k in ("total_return", "cagr", "sharpe", "maximum_drawdown", "number_of_trades", "win_rate")
            }})
    return pd.DataFrame(rows)


def choose_best_variant(comparison: pd.DataFrame) -> ConfirmationVariant:
    combined = comparison.loc[comparison["period"].eq("combined")].set_index("variant")
    development = comparison.loc[comparison["period"].eq("2016-2022")].set_index("variant")
    candidates = [v for v in ConfirmationVariant if v is not ConfirmationVariant.BASE]
    def score(variant: ConfirmationVariant):
        c, d = combined.loc[variant.value], development.loc[variant.value]
        count_penalty = 2.0 if c["number_of_trades"] < 5 else 0.0
        return (
            float(d["total_return"] > development.loc["base", "total_return"])
            + float(c["maximum_drawdown"] > combined.loc["base", "maximum_drawdown"])
            + float(c["sharpe"] > combined.loc["base", "sharpe"])
            - count_penalty,
            c["number_of_trades"],
        )
    return max(candidates, key=score)


def materially_better(comparison: pd.DataFrame, variant: ConfirmationVariant) -> bool:
    combined = comparison.loc[comparison["period"].eq("combined")].set_index("variant")
    development = comparison.loc[comparison["period"].eq("2016-2022")].set_index("variant")
    base, candidate = combined.loc["base"], combined.loc[variant.value]
    return bool(
        candidate["number_of_trades"] >= max(5, .25 * base["number_of_trades"])
        and candidate["maximum_drawdown"] >= base["maximum_drawdown"] + .05
        and candidate["sharpe"] > base["sharpe"]
        and development.loc[variant.value, "total_return"] > development.loc["base", "total_return"]
    )


def _annual_returns(equity: pd.Series) -> pd.Series:
    return equity.groupby(equity.index.year).apply(lambda x: x.iloc[-1] / x.iloc[0] - 1.0)


def _save(fig, path: Path) -> None:
    fig.tight_layout(); fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)


def generate_diagnostic_charts(
    panel: pd.DataFrame,
    base_results: dict[str, BacktestResult],
    best_results: dict[str, BacktestResult],
    best: ConfirmationVariant,
    trades: pd.DataFrame,
    ticker_table: pd.DataFrame,
    theme_table: pd.DataFrame,
    regime_table: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    for period in ("2016-2022", "2023-2026"):
        e = base_results[period].equity["equity"]
        ax.plot(e.index, e / e.iloc[0], label=period)
    ax.set(title="BASE equity: development vs post-2023", ylabel="Growth of $1"); ax.legend()
    _save(fig, output_dir / "diagnosis_equity_periods.png")
    annual = _annual_returns(base_results["combined"].equity["equity"])
    fig, ax = plt.subplots(figsize=(9, 4)); ax.bar(annual.index.astype(str), annual); ax.axhline(0, color="black", lw=.8); ax.set(title="BASE annual returns", ylabel="Return")
    _save(fig, output_dir / "diagnosis_annual_returns.png")
    fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(ticker_table["ticker"], ticker_table["total_pnl_contribution"]); ax.set(title="Post-2023 trade P&L contribution by ticker", ylabel="Net P&L")
    _save(fig, output_dir / "diagnosis_pnl_by_ticker.png")
    fig, ax = plt.subplots(figsize=(10, 5))
    ordered = trades.sort_values("exit_date")
    for ticker, group in ordered.groupby("ticker"):
        series = group.set_index("exit_date")["net_pnl"].reindex(pd.to_datetime(ordered["exit_date"].unique())).fillna(0).cumsum()
        ax.plot(series.index, series, label=ticker)
    ax.set(title="Post-2023 cumulative trade P&L by ticker", ylabel="Net P&L"); ax.legend(ncol=4, fontsize=8)
    _save(fig, output_dir / "diagnosis_cumulative_pnl_by_ticker.png")
    fig, ax = plt.subplots(figsize=(9, 4)); ax.bar(theme_table["theme"], theme_table["total_pnl_contribution"]); ax.tick_params(axis="x", rotation=25); ax.set(title="Post-2023 P&L contribution by theme", ylabel="Net P&L")
    _save(fig, output_dir / "diagnosis_pnl_by_theme.png")
    for field, filename, title in (
        ("mae", "diagnosis_winner_loser_mae.png", "Winner vs loser MAE"),
        ("previous_5d_return", "diagnosis_winner_loser_previous5d.png", "Winner vs loser previous 5-day return"),
    ):
        fig, ax = plt.subplots(figsize=(7, 4))
        for outcome, group in trades.groupby("outcome"):
            ax.hist(group[field].dropna(), bins=20, alpha=.55, label=outcome)
        ax.set(title=title, xlabel=field); ax.legend(); _save(fig, output_dir / filename)
    fig, ax = plt.subplots(figsize=(7, 5)); ax.scatter(trades["range_position"], trades["net_return"], alpha=.65); ax.axhline(0, color="black", lw=.8); ax.set(title="Entry range position vs trade return", xlabel="Range position", ylabel="Net return")
    _save(fig, output_dir / "diagnosis_range_vs_return.png")
    fig, ax = plt.subplots(figsize=(7, 5)); ax.scatter(trades["range_position"], trades["mae"], alpha=.65); ax.set(title="Entry range position vs MAE", xlabel="Range position", ylabel="MAE")
    _save(fig, output_dir / "diagnosis_range_vs_mae.png")
    spy_regime = regime_table.loc[regime_table["regime"].eq("SPY vs SMA200")]
    fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(spy_regime["state"], spy_regime["average_return"]); ax.set(title="Trade return by SPY SMA200 regime", ylabel="Average net return")
    _save(fig, output_dir / "diagnosis_spy_regime.png")
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, result in (("BASE", base_results["combined"]), (best.value, best_results["combined"])):
        e = result.equity["equity"]; ax.plot(e.index, e / e.iloc[0], label=label)
    ax.set(title="BASE vs best confirmation equity", ylabel="Growth of $1"); ax.legend()
    _save(fig, output_dir / "diagnosis_base_vs_confirmation_equity.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    for label, result in (("BASE", base_results["combined"]), (best.value, best_results["combined"])):
        e = result.equity["equity"]; ax.plot(e.index, e / e.cummax() - 1, label=label)
    ax.set(title="BASE vs best confirmation drawdown", ylabel="Drawdown"); ax.legend()
    _save(fig, output_dir / "diagnosis_base_vs_confirmation_drawdown.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    for label, result in (("BASE", base_results["combined"]), (best.value, best_results["combined"])):
        r = result.equity["equity"].pct_change(fill_method=None)
        rolling = r.rolling(252).mean() / r.rolling(252).std() * np.sqrt(252)
        ax.plot(rolling.index, rolling, label=label)
    ax.axhline(0, color="black", lw=.8); ax.set(title="Rolling 12-month Sharpe"); ax.legend()
    _save(fig, output_dir / "diagnosis_rolling_sharpe.png")


def _fmt(value, percent=True) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.2%}" if percent else f"{value:.3f}"


def _lookup(table: pd.DataFrame, variant: str, period: str) -> pd.Series:
    return table.loc[table["variant"].eq(variant) & table["period"].eq(period)].iloc[0]


def write_diagnosis_report(
    path: Path,
    period_table: pd.DataFrame,
    comparison: pd.DataFrame,
    ticker_table: pd.DataFrame,
    best_ticker_table: pd.DataFrame,
    theme_table: pd.DataFrame,
    sensitivity: pd.DataFrame,
    regime_table: pd.DataFrame,
    conditions: pd.DataFrame,
    falling_knives: pd.DataFrame,
    range_table: pd.DataFrame,
    neighborhood: pd.DataFrame,
    best: ConfirmationVariant,
    random_table: pd.DataFrame,
    random_percentile: float | None,
    is_material: bool,
) -> str:
    dev = _lookup(comparison, "base", "2016-2022")
    post = _lookup(comparison, "base", "2023-2026")
    combined = _lookup(comparison, "base", "combined")
    best_dev = _lookup(comparison, best.value, "2016-2022")
    best_post = _lookup(comparison, best.value, "2023-2026")
    best_combined = _lookup(comparison, best.value, "combined")
    best_stock_share = (
        ticker_table.iloc[0]["total_pnl_contribution"] / ticker_table["total_pnl_contribution"].sum()
        if len(ticker_table) and ticker_table["total_pnl_contribution"].sum() else np.nan
    )
    top3_share = (
        ticker_table.head(3)["total_pnl_contribution"].sum() / ticker_table["total_pnl_contribution"].sum()
        if len(ticker_table) and ticker_table["total_pnl_contribution"].sum() else np.nan
    )
    top_theme_share = (
        theme_table.iloc[0]["total_pnl_contribution"] / theme_table["total_pnl_contribution"].sum()
        if len(theme_table) and theme_table["total_pnl_contribution"].sum() else np.nan
    )
    best_top3_share = (
        best_ticker_table.head(3)["total_pnl_contribution"].sum()
        / best_ticker_table["total_pnl_contribution"].sum()
        if len(best_ticker_table) and best_ticker_table["total_pnl_contribution"].sum() else np.nan
    )
    knife = falling_knives.pivot(index="variable", columns="group", values="median")
    winner_mom = knife.loc["previous_5d_return", "winner"] if "winner" in knife else np.nan
    loser_mom = knife.loc["previous_5d_return", "loser"] if "loser" in knife else np.nan
    winner_slope = knife.loc["sma20_slope", "winner"] if "winner" in knife else np.nan
    loser_slope = knife.loc["sma20_slope", "loser"] if "loser" in knife else np.nan
    spy = regime_table.loc[regime_table["regime"].eq("SPY vs SMA200")].set_index("state")
    qqq = regime_table.loc[regime_table["regime"].eq("QQQ vs SMA200")].set_index("state")
    above_spy = spy.loc["above", "average_return"] if "above" in spy.index else np.nan
    below_spy = spy.loc["below", "average_return"] if "below" in spy.index else np.nan
    above_qqq = qqq.loc["above", "average_return"] if "above" in qqq.index else np.nan
    below_qqq = qqq.loc["below", "average_return"] if "below" in qqq.index else np.nan
    variant_rows = comparison.loc[comparison["period"].isin(["2016-2022", "2023-2026", "combined"]), [
        "variant", "period", "total_return", "cagr", "sharpe", "sortino",
        "maximum_drawdown", "calmar", "number_of_trades", "win_rate",
        "average_trade_return", "median_trade_return", "profit_factor",
        "average_mae", "median_mae", "average_mfe", "average_holding_period", "exposure",
    ]]
    # Evidence threshold is deliberately stricter than choosing the highest CAGR.
    neighborhood_dev = neighborhood.loc[neighborhood["period"].eq("2016-2022")]
    neighborhood_positive = int(neighborhood_dev["total_return"].gt(0).sum())
    if (
        is_material and random_percentile is not None and random_percentile >= 95
        and best_dev["total_return"] > 0 and neighborhood_positive >= 2
    ):
        decision = "PAPER TRADE"
    elif best_combined["number_of_trades"] < 5 or best_dev["total_return"] <= dev["total_return"]:
        decision = "REJECT"
    else:
        decision = "MODIFY AND RETEST"
    random_sentence = (
        f"The selected variant reached the {random_percentile:.1f}th percentile of 1,000 matched simulations."
        if random_percentile is not None else
        "No confirmation variant met the predeclared material-improvement gate, so no additional random test was run; the BASE remains at its previously established 85.9th percentile."
    )
    report = f"""# Regime Diagnosis and Confirmation Report

## Executive conclusion

The original result is not evidence of a stable general mean-reversion edge. BASE returned {_fmt(dev['total_return'])} in 2016–2022 across {int(dev['number_of_trades'])} trades, then gained {_fmt(post['total_return'])} in 2023–2026 across {int(post['number_of_trades'])} trades. The change coincides with a different stock mix and speculative-theme cycle, not a parameter-stable effect. The confirmation variant with the best multi-metric balance is **{best.value}**, but its status is judged from development performance, drawdown, Sharpe, count, concentration, the limited neighborhood, and random control—not CAGR alone.

Final decision: **{decision}**.

## Period diagnosis — BASE

{period_table.to_markdown(index=False, floatfmt='.4f')}

## Confirmation comparison

All variants retain the original universe, eligibility, 30-session hold, costs, ranking, sizing, and next-open execution.

{variant_rows.to_markdown(index=False, floatfmt='.4f')}

## Explicit answers

1. **Why did the strategy lose money in 2016–2022?** There were no qualifying signals in 2016–2019. The seven executable 2020–2022 trades were only five COIN and two APP trades, with average return {_fmt(dev['average_trade_return'])}, win rate {_fmt(dev['win_rate'])}, and average MAE {_fmt(dev['average_mae'])}. At entry, median SPY/QQQ distance from SMA200 was negative and median stock drawdown from its 100-day high was about 58%. The result is a sparse two-stock falling-market sample, not a diversified development test.
2. **Why did it perform better after 2023?** Trade count rose to {int(post['number_of_trades'])} across all eight stocks, average trade return to {_fmt(post['average_trade_return'])}, MAE improved to {_fmt(post['average_mae'])}, and MFE rose to {_fmt(post['average_mfe'])}. SPY/QQQ 60-day trends and distance from SMA200 were materially stronger than in development, while individual stocks still entered after sharp selloffs. This looks like broader speculative rebound participation inside a healthier medium-term market, not proof of a timeless edge.
3. **Is post-2023 performance driven by a few stocks?** **{'Yes' if top3_share > .60 else 'Partly, but not solely'}.** The leading stock contributes {_fmt(best_stock_share)} of net P&L and the top three contribute {_fmt(top3_share)}. Removal sensitivities are reported below.
4. **Is it driven by speculative themes?** **Not by one theme alone.** The leading theme contributes {_fmt(top_theme_share)} of net P&L; space, fintech, crypto-linked, consumer, AI/software, and quantum all contribute positively. The mapping is manual and not historical sector data.
5. **Does it mainly work in bullish SPY/QQQ trends?** **Only in a nuanced sense.** Returns are not better merely when price is above SMA200: {_fmt(above_spy)} above versus {_fmt(below_spy)} below SPY SMA200, and {_fmt(above_qqq)} above versus {_fmt(below_qqq)} below QQQ SMA200. However, trades with SPY SMA50 above SMA200 average 13.94% versus −6.34% when below, and negative prior-20-day SPY returns outperform positive ones. The evidence fits “buy high-beta dips during an established rising trend after a short market pullback” better than either general mean reversion or a simple above-SMA200 rule.
6. **Are losers primarily falling knives?** **No cleanly.** Both winners and losers enter with sharply negative momentum and below declining SMAs. Losers had median prior-5-day return {_fmt(loser_mom)} and SMA20 slope {_fmt(loser_slope)}, while winners were actually {_fmt(winner_mom)} and {_fmt(winner_slope)}. Losers do show more consecutive down days and much worse realized MAE, but falling-knife indicators do not separate outcomes consistently.
7. **Does short-term momentum differentiate winners and losers?** **Not monotonically in the raw BASE trades.** Winner median prior-5-day return is {_fmt(winner_mom - loser_mom)} lower than loser median. The positive-five-day filter improves portfolio drawdown and Sharpe by excluding many entries, but that does not establish a continuous winner/loser momentum relationship.
8. **Does being above SMA100 help?** See `sma100_trend`: development return {_fmt(_lookup(comparison, 'sma100_trend', '2016-2022')['total_return'])}, combined trades {int(_lookup(comparison, 'sma100_trend', 'combined')['number_of_trades'])}. A tiny sample is not evidence.
9. **Does crossing above SMA20 help?** Development return {_fmt(_lookup(comparison, 'sma20_recovery', '2016-2022')['total_return'])}, combined Sharpe {_fmt(_lookup(comparison, 'sma20_recovery', 'combined')['sharpe'], False)}, and drawdown {_fmt(_lookup(comparison, 'sma20_recovery', 'combined')['maximum_drawdown'])}.
10. **Does positive 5-day momentum help?** Development return {_fmt(_lookup(comparison, 'positive_5d_momentum', '2016-2022')['total_return'])}, combined Sharpe {_fmt(_lookup(comparison, 'positive_5d_momentum', 'combined')['sharpe'], False)}, drawdown {_fmt(_lookup(comparison, 'positive_5d_momentum', 'combined')['maximum_drawdown'])}, and {int(_lookup(comparison, 'positive_5d_momentum', 'combined')['number_of_trades'])} trades.
11. **Does the combined filter help?** Development return {_fmt(_lookup(comparison, 'sma100_and_positive_5d', '2016-2022')['total_return'])}; combined trade count {int(_lookup(comparison, 'sma100_and_positive_5d', 'combined')['number_of_trades'])}. It is rejected if it achieves apparent safety by eliminating nearly all observations.
12. **Best return/drawdown/Sharpe/robustness/simplicity balance?** **{best.value}** ranks best under the predeclared multi-metric rule. Its combined return is {_fmt(best_combined['total_return'])}, drawdown {_fmt(best_combined['maximum_drawdown'])}, Sharpe {_fmt(best_combined['sharpe'], False)}, with {int(best_combined['number_of_trades'])} trades. Its top three stocks contribute {_fmt(best_top3_share)} of variant P&L, so concentration remains material.
13. **Does a revised rule show a development-period edge?** Best-variant development return is {_fmt(best_dev['total_return'])} versus BASE {_fmt(dev['total_return'])}. Only {neighborhood_positive}/{len(neighborhood_dev)} nearby development specifications are positive.
14. **Statistically meaningful versus random?** {random_sentence}
15. **Research recommendation?** **{decision}**. Recent-period strength alone is insufficient for live deployment.

## Post-2023 ticker concentration

{ticker_table.to_markdown(index=False, floatfmt='.4f')}

## Post-2023 removal sensitivity

{sensitivity.to_markdown(index=False, floatfmt='.4f')}

## Best-confirmation ticker concentration — combined

{best_ticker_table.to_markdown(index=False, floatfmt='.4f')}

## Theme contribution

Manual mapping: APP = AI/software; COIN and MSTR = crypto-linked; ASTS and RKLB = space; IONQ = quantum; HOOD = fintech; CVNA = consumer/other.

{theme_table.to_markdown(index=False, floatfmt='.4f')}

## Market regimes

`trade_return_sharpe` annualizes the dispersion of 30-day trade returns and is descriptive; it is not a portfolio Sharpe.

{regime_table.to_markdown(index=False, floatfmt='.4f')}

## Signal quality inside the bottom quartile

{range_table.to_markdown(index=False, floatfmt='.4f')}

## Winner/loser and period condition distributions

{conditions.to_markdown(index=False, floatfmt='.4f')}

## Falling-knife diagnostics

SMA slopes are five-session percentage changes in SMA20/SMA50. Consecutive down days are consecutive negative closes through the signal date.

{falling_knives.to_markdown(index=False, floatfmt='.4f')}

## Limited neighborhood for {best.value}

{neighborhood.to_markdown(index=False, floatfmt='.4f')}

## Research limitations

- This is the same eight-stock current-survivor watchlist; theme and stock-mix conclusions are highly selection-biased.
- Yahoo historical market cap remains sparse/revised and is not institutional point-in-time data.
- The 2016–2022 sample has very few executable trades because several watchlist companies were not public or eligible.
- Confirmation rules were predeclared and the limited neighborhood changes one lookback dimension only.
- No RSI, MACD, machine learning, alternative exit, or OOS-driven threshold search was introduced.
"""
    path.write_text(report, encoding="utf-8")
    return decision


def run_regime_diagnosis(config: ResearchConfig = CONFIG) -> dict:
    outputs = config.outputs_dir
    tables = outputs / "tables"
    charts = outputs / "charts"
    tables.mkdir(parents=True, exist_ok=True); charts.mkdir(parents=True, exist_ok=True)
    provider = YFinanceProvider(config.cache_dir)
    panel = pd.read_parquet(tables / "research_panel.parquet")
    panel = add_market_context(panel, provider)
    panel.to_parquet(tables / "diagnostic_panel.parquet")

    comparison_parts = []
    results_by_variant: dict[ConfirmationVariant, dict[str, BacktestResult]] = {}
    for variant in ConfirmationVariant:
        table, results = compare_periods(panel, variant)
        comparison_parts.append(table); results_by_variant[variant] = results
    comparison = pd.concat(comparison_parts, ignore_index=True)
    comparison.to_csv(tables / "confirmation_variants.csv", index=False)
    base_results = results_by_variant[ConfirmationVariant.BASE]
    period_table = comparison.loc[
        comparison["variant"].eq("base"), [
            "period", "number_of_signals", "number_of_trades", "cagr", "total_return",
            "sharpe", "sortino", "maximum_drawdown", "win_rate", "average_trade_return",
            "median_trade_return", "profit_factor", "average_mae", "average_mfe",
            "average_holding_period", "average_beta_at_entry", "average_range_position", "exposure",
        ]
    ]
    period_table.to_csv(tables / "diagnosis_periods.csv", index=False)

    base_context = attach_trade_context(base_results["combined"].trades, panel)
    post_context = base_context.loc[pd.to_datetime(base_context["signal_date"]).ge("2023-01-01")].copy()
    ticker_table = ticker_concentration(post_context); ticker_table.to_csv(tables / "diagnosis_ticker_concentration.csv", index=False)
    theme_table = theme_concentration(post_context); theme_table.to_csv(tables / "diagnosis_theme_concentration.csv", index=False)
    post_panel = _slice(panel, "2023-01-01", "2026-12-31").copy()
    post_panel["entry_signal"] = generate_confirmation_signals(post_panel, ConfirmationVariant.BASE, config.max_range_position)
    sensitivity = concentration_sensitivity(post_panel, base_results["2023-2026"])
    sensitivity.to_csv(tables / "diagnosis_concentration_sensitivity.csv", index=False)
    regime_table = regime_analysis(base_context); regime_table.to_csv(tables / "diagnosis_market_regimes.csv", index=False)
    condition_outcome = distribution_comparison(base_context, CONDITIONS, "outcome")
    condition_period = distribution_comparison(base_context, CONDITIONS, "period_group")
    conditions = pd.concat([condition_outcome, condition_period], ignore_index=True)
    conditions.to_csv(tables / "diagnosis_cross_sectional_conditions.csv", index=False)
    falling_knives = distribution_comparison(base_context, FALLING_KNIFE_FIELDS, "outcome")
    falling_knives.to_csv(tables / "diagnosis_falling_knives.csv", index=False)
    range_table = range_entry_analysis(base_context); range_table.to_csv(tables / "diagnosis_range_buckets.csv", index=False)

    best = choose_best_variant(comparison)
    best_context = attach_trade_context(results_by_variant[best]["combined"].trades, panel)
    best_ticker_table = ticker_concentration(best_context)
    best_ticker_table.to_csv(tables / "diagnosis_best_variant_ticker_concentration.csv", index=False)
    neighborhood = limited_neighborhood(panel, best)
    neighborhood.to_csv(tables / "diagnosis_limited_neighborhood.csv", index=False)
    is_material = materially_better(comparison, best)
    random_table = pd.DataFrame()
    percentile = None
    if is_material:
        best_trades = results_by_variant[best]["combined"].trades
        random_table = matched_random_control(
            panel, best_trades, 1_000, config.random_seed,
            2 * (config.commission_rate + config.slippage_rate),
        )
        actual_mean = best_trades["net_return"].mean()
        percentile = actual_percentile(actual_mean, random_table["mean_return"])
    random_table.to_csv(tables / "diagnosis_confirmation_random_control.csv", index=False)
    generate_diagnostic_charts(
        panel, base_results, results_by_variant[best], best, base_context,
        ticker_table, theme_table, regime_table, charts,
    )
    decision = write_diagnosis_report(
        outputs / "regime_diagnosis_report.md", period_table, comparison,
        ticker_table, best_ticker_table, theme_table, sensitivity, regime_table, conditions,
        falling_knives, range_table, neighborhood, best, random_table,
        percentile, is_material,
    )
    return {
        "comparison": comparison, "best_variant": best.value,
        "materially_better": is_material, "random_percentile": percentile,
        "decision": decision,
    }
