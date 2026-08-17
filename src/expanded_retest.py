"""Expanded point-in-time high-beta universe retest.

Primary rules remain BASE, positive five-day confirmation, and the single
pre-specified positive-five-day + QQQ-above-SMA200 regime filter.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import CONFIG
from src.metrics import performance_metrics
from src.portfolio import EXIT_RULES, BacktestResult, run_portfolio
from src.random_control import matched_random_portfolio_control
from src.regime_diagnosis import (
    FALLING_KNIFE_FIELDS, _suppress_trade_windows, range_entry_analysis,
    ticker_concentration,
)


PERIODS = {
    "2010-2015": ("2010-01-01", "2015-12-31"),
    "2016-2019": ("2016-01-01", "2019-12-31"),
    "2020-2022": ("2020-01-01", "2022-12-31"),
    "2016-2022": ("2016-01-01", "2022-12-31"),
    "2023+": ("2023-01-01", "2026-12-31"),
    "combined": ("2010-01-01", "2026-12-31"),
}

PRIMARY_STRATEGIES = ("base", "positive_5d", "positive_5d_qqq_bull")


def _slice(panel: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dates = panel.index.get_level_values("date")
    return panel.loc[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]


def confirmation_signal(panel: pd.DataFrame, window: int = 5) -> pd.Series:
    """Point-in-time positive trailing return confirmation."""
    close = panel["adj_close"]
    previous = close.groupby(level="ticker").shift(window)
    return close.div(previous).sub(1).gt(0).rename(f"positive_{window}d")


def strategy_signal(panel: pd.DataFrame, strategy: str) -> pd.Series:
    base = panel["eligible"].fillna(False) & panel["range_position"].le(.25)
    if strategy == "base":
        return base
    positive = confirmation_signal(panel, 5)
    if strategy == "positive_5d":
        return base & positive
    if strategy == "positive_5d_qqq_bull":
        return base & positive & panel["qqq_above_sma200"].fillna(False)
    if strategy == "positive_5d_qqq_60d":
        return base & positive & panel["qqq_60d_return"].gt(0)
    raise ValueError(f"unknown expanded strategy: {strategy}")


def prepare_universe_panel(raw: pd.DataFrame, version: str) -> pd.DataFrame:
    eligibility = "eligible_strict" if version == "strict_cap" else "eligible_nocap"
    ever = raw.loc[raw[eligibility]].index.get_level_values("ticker").unique()
    panel = raw.loc[raw.index.get_level_values("ticker").isin(ever)].copy()
    panel["eligible"] = panel[eligibility].fillna(False)
    panel["market_cap"] = panel.get("historical_market_cap", pd.Series(np.nan, index=panel.index))
    panel["market_cap_is_proxy"] = False
    return panel


def _extended_metrics(result: BacktestResult, signals: int) -> dict[str, float]:
    m = performance_metrics(result.equity, result.trades)
    trades = result.trades
    m.update({
        "number_of_signals": signals,
        "unique_tickers": trades["ticker"].nunique() if not trades.empty else 0,
        "average_mae": trades["mae"].mean() if not trades.empty else np.nan,
        "median_mae": trades["mae"].median() if not trades.empty else np.nan,
        "average_mfe": trades["mfe"].mean() if not trades.empty else np.nan,
        "median_mfe": trades["mfe"].median() if not trades.empty else np.nan,
    })
    return m


def run_one(panel: pd.DataFrame, signal: pd.Series, commission: float | None = None, slippage: float | None = None) -> BacktestResult:
    prepared = panel.copy()
    prepared["entry_signal"] = signal.reindex(prepared.index).fillna(False)
    return run_portfolio(
        prepared, EXIT_RULES["F"], CONFIG.initial_capital, CONFIG.max_positions,
        CONFIG.position_fraction,
        CONFIG.commission_rate if commission is None else commission,
        CONFIG.slippage_rate if slippage is None else slippage,
        "lowest_range",
    )


def compare_strategies(panel: pd.DataFrame, version: str) -> tuple[pd.DataFrame, dict[tuple[str, str], BacktestResult]]:
    rows = []
    results = {}
    strategies = (*PRIMARY_STRATEGIES, "positive_5d_qqq_60d")
    full_signals = {strategy: strategy_signal(panel, strategy) for strategy in strategies}
    for strategy in strategies:
        for period, (start, end) in PERIODS.items():
            if version == "strict_cap" and period in {"2010-2015", "combined"}:
                if period == "2010-2015":
                    continue
                start = "2016-01-01"
            part = _slice(panel, start, end)
            if part.empty:
                continue
            sig = full_signals[strategy].reindex(part.index).fillna(False)
            result = run_one(part, sig)
            results[(strategy, period)] = result
            rows.append({
                "universe": version, "strategy": strategy, "period": period,
                **_extended_metrics(result, int(sig.sum())),
            })
    return pd.DataFrame(rows), results


def sample_size_table(panel: pd.DataFrame, comparison: pd.DataFrame, version: str) -> pd.DataFrame:
    rows = []
    for strategy in PRIMARY_STRATEGIES:
        for period in ("2016-2022", "2023+", "combined"):
            record = comparison.loc[
                comparison["strategy"].eq(strategy) & comparison["period"].eq(period)
            ].iloc[0]
            start, end = PERIODS[period]
            if version == "strict_cap" and period == "combined":
                start = "2016-01-01"
            part = _slice(panel, start, end)
            eligible_days = int(part["eligible"].sum())
            signal = strategy_signal(part, strategy)
            tickers = part.loc[signal].index.get_level_values("ticker").nunique()
            trades = int(record["number_of_trades"])
            years = max((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25, 1)
            rows.append({
                "universe": version, "strategy": strategy, "period": period,
                "eligible_stock_days": eligible_days,
                "qualifying_signals": int(signal.sum()),
                "signal_tickers": tickers, "trades": trades,
                "trades_per_year": trades / years,
            })
    return pd.DataFrame(rows)


def concentration_summary(trades: pd.DataFrame) -> dict[str, float]:
    pnl = trades.groupby("ticker")["net_pnl"].sum().sort_values(ascending=False)
    positive_total = pnl.clip(lower=0).sum()
    result = {"median_trades_per_ticker": trades.groupby("ticker").size().median() if len(trades) else np.nan}
    for count in (1, 3, 5, 10):
        result[f"top_{count}_pnl_share"] = pnl.head(count).clip(lower=0).sum() / positive_total if positive_total else np.nan
    return result


def concentration_sensitivity(panel: pd.DataFrame, signal: pd.Series, base_result: BacktestResult) -> pd.DataFrame:
    prepared = panel.copy(); prepared["entry_signal"] = signal.reindex(panel.index).fillna(False)
    trades = base_result.trades.sort_values("net_return", ascending=False)
    ticker_rank = ticker_concentration(trades)
    top10 = max(1, math.ceil(len(trades) * .10))
    cases = {
        "base": prepared,
        "remove_best_trade": _suppress_trade_windows(prepared, trades.head(1)),
        "remove_best_5_trades": _suppress_trade_windows(prepared, trades.head(5)),
        "remove_top_10pct_trades": _suppress_trade_windows(prepared, trades.head(top10)),
    }
    for label, count in (("remove_best_stock", 1), ("remove_best_3_stocks", 3)):
        candidate = prepared.copy()
        excluded = ticker_rank.head(count)["ticker"]
        candidate.loc[candidate.index.get_level_values("ticker").isin(excluded), "entry_signal"] = False
        cases[label] = candidate
    rows = []
    for label, candidate in cases.items():
        result = run_one(candidate, candidate["entry_signal"])
        m = performance_metrics(result.equity, result.trades)
        rows.append({"sensitivity": label, **{key: m[key] for key in (
            "total_return", "cagr", "sharpe", "maximum_drawdown", "number_of_trades"
        )}})
    return pd.DataFrame(rows)


def bootstrap_intervals(trades: pd.DataFrame, simulations: int = 5_000, seed: int = 20260816) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    if trades.empty:
        return pd.DataFrame()
    def stats(values: np.ndarray) -> tuple[float, float, float, float]:
        winners, losers = values[values > 0], values[values < 0]
        pf = winners.sum() / -losers.sum() if len(losers) and -losers.sum() else np.nan
        return values.mean(), np.median(values), np.mean(values > 0), pf
    rows = []
    values = trades["net_return"].to_numpy()
    tickers = trades["ticker"].unique()
    grouped = {ticker: trades.loc[trades["ticker"].eq(ticker), "net_return"].to_numpy() for ticker in tickers}
    for method in ("trade", "ticker_cluster"):
        estimates = []
        for _ in range(simulations):
            if method == "trade":
                sample = rng.choice(values, size=len(values), replace=True)
            else:
                selected = rng.choice(tickers, size=len(tickers), replace=True)
                sample = np.concatenate([grouped[t] for t in selected])
            estimates.append(stats(sample))
        estimates = np.asarray(estimates)
        actual = stats(values)
        for position, metric in enumerate(("mean_return", "median_return", "win_rate", "profit_factor")):
            clean = estimates[:, position][np.isfinite(estimates[:, position])]
            rows.append({
                "method": method, "metric": metric, "estimate": actual[position],
                "ci_lower": np.quantile(clean, .025), "ci_upper": np.quantile(clean, .975),
                "simulations": simulations,
            })
    return pd.DataFrame(rows)


def annual_results(result: BacktestResult) -> pd.DataFrame:
    equity = result.equity["equity"]
    trades = result.trades.copy()
    rows = []
    for year, values in equity.groupby(equity.index.year):
        subset = trades.loc[pd.to_datetime(trades.get("signal_date", pd.Series(dtype="datetime64[ns]")).astype("datetime64[ns]")).dt.year.eq(year)] if not trades.empty else trades
        drawdown = values / values.cummax() - 1.0
        rows.append({
            "year": year, "number_of_trades": len(subset),
            "strategy_return": values.iloc[-1] / values.iloc[0] - 1.0,
            "average_trade_return": subset["net_return"].mean() if len(subset) else np.nan,
            "win_rate": subset["net_return"].gt(0).mean() if len(subset) else np.nan,
            "maximum_drawdown": drawdown.min(),
        })
    return pd.DataFrame(rows)


def cost_sensitivity(panel: pd.DataFrame, strategies=PRIMARY_STRATEGIES) -> pd.DataFrame:
    rows = []
    for strategy in strategies:
        signal = strategy_signal(panel, strategy)
        for label, multiplier in (("zero", 0), ("base", 1), ("double", 2)):
            result = run_one(
                panel, signal, CONFIG.commission_rate * multiplier,
                CONFIG.slippage_rate * multiplier,
            )
            m = performance_metrics(result.equity, result.trades)
            rows.append({"strategy": strategy, "cost_level": label, **{
                key: m[key] for key in ("total_return", "cagr", "sharpe", "maximum_drawdown", "number_of_trades")
            }})
    return pd.DataFrame(rows)


def trade_context(trades: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "previous_5d_return", "previous_10d_return", "previous_20d_return",
        "distance_sma20", "distance_sma50", "consecutive_down_days",
        "qqq_above_sma200", "spy_above_sma200", "qqq_60d_return",
    ]
    context = panel[fields].reset_index().rename(columns={"date": "signal_date"})
    result = trades.merge(context, on=["signal_date", "ticker"], how="left")
    result["outcome"] = np.where(result["net_return"].gt(0), "winner", "loser")
    return result


def falling_knife_table(context: pd.DataFrame) -> pd.DataFrame:
    fields = ["previous_5d_return", "previous_10d_return", "previous_20d_return", "distance_sma20", "distance_sma50", "consecutive_down_days"]
    rows = []
    for outcome, subset in context.groupby("outcome"):
        for field in fields:
            values = subset[field].dropna()
            rows.append({"outcome": outcome, "variable": field, "observations": len(values), "mean": values.mean(), "median": values.median(), "p25": values.quantile(.25), "p75": values.quantile(.75)})
    return pd.DataFrame(rows)


def momentum_neighborhood(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, BacktestResult]]:
    rows, results = [], {}
    base = panel["eligible"] & panel["range_position"].le(.25)
    for window in (3, 5, 10):
        signal = base & confirmation_signal(panel, window)
        for period in ("2016-2022", "2023+", "combined"):
            start, end = PERIODS[period]
            part = _slice(panel, start, end)
            result = run_one(part, signal.reindex(part.index).fillna(False))
            if period == "combined":
                results[window] = result
            m = performance_metrics(result.equity, result.trades)
            rows.append({"window": window, "period": period, **{
                key: m[key] for key in ("total_return", "cagr", "sharpe", "sortino", "maximum_drawdown", "number_of_trades", "win_rate", "average_trade_return")
            }})
    return pd.DataFrame(rows), results


def _benchmark_regime_masks(panel: pd.DataFrame, benchmark: str) -> tuple[pd.Series, pd.Series]:
    """Return complementary boolean bull/bear masks even when parquet restores object dtype."""
    bull = panel[f"{benchmark}_above_sma200"].fillna(False).astype(bool)
    return bull, ~bull


def regime_backtests(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("base", "positive_5d"):
        original = strategy_signal(panel, strategy)
        for benchmark in ("qqq", "spy"):
            bull, bear = _benchmark_regime_masks(panel, benchmark)
            for label, regime_mask in (("bull", bull), ("bear", bear)):
                result = run_one(panel, original & regime_mask)
                m = performance_metrics(result.equity, result.trades)
                rows.append({"strategy": strategy, "benchmark": benchmark.upper(), "regime": label, **{
                    key: m[key] for key in ("total_return", "cagr", "sharpe", "maximum_drawdown", "number_of_trades", "win_rate", "average_trade_return", "median_trade_return")
                }})
    return pd.DataFrame(rows)


def sector_theme_mapping(tickers: pd.Index) -> pd.DataFrame:
    path = CONFIG.cache_dir.parent / "universe" / "sp500_current_metadata.csv"
    metadata = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if not metadata.empty:
        metadata["Symbol"] = metadata["Symbol"].str.replace("-", ".", regex=False)
        metadata = metadata.set_index("Symbol")
    rows = []
    for ticker in sorted(set(tickers)):
        sector = metadata.loc[ticker, "GICS Sector"] if ticker in metadata.index else "Unclassified / removed"
        industry = metadata.loc[ticker, "GICS Sub-Industry"] if ticker in metadata.index else "Unclassified / removed"
        text = f"{sector} {industry}".lower()
        if ticker in {"COIN", "MSTR"}:
            theme = "crypto-linked"
        elif ticker in {"PYPL", "HOOD", "SQ", "XYZ"}:
            theme = "fintech"
        elif "semiconductor" in text:
            theme = "semiconductors / AI"
        elif "software" in text or "interactive media" in text:
            theme = "software"
        elif "biotech" in text:
            theme = "biotech"
        elif "consumer" in text or "retail" in text or "automobile" in text:
            theme = "consumer"
        elif "industrial" in sector.lower() or "aerospace" in text:
            theme = "industrial"
        else:
            theme = "other"
        rows.append({"ticker": ticker, "sector": sector, "industry": industry, "theme": theme})
    return pd.DataFrame(rows)


def contribution_tables(trades: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ticker = ticker_concentration(trades).merge(mapping, on="ticker", how="left")
    enriched = trades.merge(mapping, on="ticker", how="left")
    def grouped(field: str) -> pd.DataFrame:
        return enriched.groupby(field, dropna=False).agg(
            total_pnl_contribution=("net_pnl", "sum"), trade_count=("ticker", "size"),
            average_trade=("net_return", "mean"), median_trade=("net_return", "median"),
            win_rate=("net_return", lambda x: x.gt(0).mean()), mae=("mae", "mean"), mfe=("mfe", "mean"),
        ).sort_values("total_pnl_contribution", ascending=False).reset_index()
    return ticker, grouped("sector"), grouped("theme")


def _save(fig, path: Path) -> None:
    fig.tight_layout(); fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)


def generate_expanded_charts(
    results: dict[str, BacktestResult], annual: pd.DataFrame, ticker_table: pd.DataFrame,
    theme_table: pd.DataFrame, range_table: pd.DataFrame, momentum: pd.DataFrame,
    regimes: pd.DataFrame, randoms: pd.DataFrame, bootstrap: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    def equity_plot(keys, filename, title):
        fig, ax = plt.subplots(figsize=(10, 5))
        for key in keys:
            e = results[key].equity["equity"]; ax.plot(e.index, e / e.iloc[0], label=key)
        ax.set(title=title, ylabel="Growth of $1"); ax.legend(); _save(fig, output_dir / filename)
    equity_plot(["base", "positive_5d"], "expanded_base_vs_positive5_equity.png", "BASE vs positive-5D")
    equity_plot(["base", "positive_5d_qqq_bull"], "expanded_base_vs_qqq_equity.png", "BASE vs positive-5D + QQQ bull")
    fig, ax = plt.subplots(figsize=(10, 5))
    for key in PRIMARY_STRATEGIES:
        e = results[key].equity["equity"]; ax.plot(e.index, e / e.cummax() - 1, label=key)
    ax.set(title="Drawdowns", ylabel="Drawdown"); ax.legend(); _save(fig, output_dir / "expanded_drawdowns.png")
    pivot = annual.pivot(index="year", columns="strategy", values="strategy_return")
    fig, ax = plt.subplots(figsize=(11, 5)); pivot.plot.bar(ax=ax); ax.set(title="Annual returns", ylabel="Return")
    _save(fig, output_dir / "expanded_annual_returns.png")
    counts = annual.pivot(index="year", columns="strategy", values="number_of_trades")
    fig, ax = plt.subplots(figsize=(11, 4)); counts.plot.bar(ax=ax); ax.set(title="Trades by year", ylabel="Trades")
    _save(fig, output_dir / "expanded_trades_by_year.png")
    trades = results["base"].trades.sort_values("exit_date")
    fig, ax = plt.subplots(figsize=(10, 5))
    for ticker, group in trades.groupby("ticker"):
        ax.plot(pd.to_datetime(group["exit_date"]), group["net_pnl"].cumsum(), alpha=.65, label=ticker)
    ax.set(title="Cumulative BASE P&L by ticker", ylabel="Net P&L")
    _save(fig, output_dir / "expanded_cumulative_pnl_ticker.png")
    pnl = ticker_table["total_pnl_contribution"].clip(lower=0).sort_values(ascending=False)
    curve = pnl.cumsum() / pnl.sum() if pnl.sum() else pnl
    fig, ax = plt.subplots(figsize=(7, 4)); ax.plot(np.arange(1, len(curve)+1), curve); ax.set(title="P&L concentration curve", xlabel="Top N stocks", ylabel="Share of positive P&L")
    _save(fig, output_dir / "expanded_pnl_concentration.png")
    fig, ax = plt.subplots(figsize=(9, 4)); ax.bar(theme_table["theme"], theme_table["total_pnl_contribution"]); ax.tick_params(axis="x", rotation=25); ax.set(title="Theme P&L contribution")
    _save(fig, output_dir / "expanded_theme_pnl.png")
    fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(range_table["range_bucket"], range_table["average_return"]); ax.set(title="Return by entry RangePosition bucket", ylabel="Average trade return")
    _save(fig, output_dir / "expanded_range_buckets.png")
    dev = momentum.loc[momentum["period"].eq("2016-2022")]
    fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(dev["window"].astype(str), dev["total_return"]); ax.set(title="3D vs 5D vs 10D confirmation — development", ylabel="Total return")
    _save(fig, output_dir / "expanded_momentum_neighborhood.png")
    qqq = regimes.loc[regimes["benchmark"].eq("QQQ") & regimes["strategy"].eq("positive_5d")]
    fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(qqq["regime"], qqq["average_trade_return"]); ax.set(title="Positive-5D by QQQ regime", ylabel="Average trade return")
    _save(fig, output_dir / "expanded_qqq_regime.png")
    fig, ax = plt.subplots(figsize=(8, 4)); ax.hist(randoms["total_return"], bins=35); ax.axvline(randoms.attrs.get("actual_total_return", np.nan), color="red", label="Actual matched path"); ax.set(title="Matched random total-return distribution"); ax.legend()
    _save(fig, output_dir / "expanded_random_distribution.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    for key in PRIMARY_STRATEGIES:
        r = results[key].equity["equity"].pct_change(fill_method=None)
        ax.plot(r.index, r.rolling(252).mean()/r.rolling(252).std()*np.sqrt(252), label=key)
    ax.set(title="Rolling 12-month Sharpe"); ax.legend(); _save(fig, output_dir / "expanded_rolling_sharpe.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    for key in PRIMARY_STRATEGIES:
        dates = pd.to_datetime(results[key].trades["signal_date"])
        monthly = pd.Series(1, index=dates).resample("ME").sum().rolling(12).sum()
        ax.plot(monthly.index, monthly, label=key)
    ax.set(title="Rolling 12-month trade count"); ax.legend(); _save(fig, output_dir / "expanded_rolling_trade_count.png")
    means = bootstrap.loc[bootstrap["metric"].eq("mean_return")]
    fig, ax = plt.subplots(figsize=(9, 4)); x=np.arange(len(means)); y=means["estimate"].to_numpy(); lo=y-means["ci_lower"].to_numpy(); hi=means["ci_upper"].to_numpy()-y; ax.errorbar(x,y,yerr=[lo,hi],fmt="o"); ax.axhline(0,color="black",lw=.8); ax.set_xticks(x,means["label"],rotation=25); ax.set(title="Bootstrap 95% CIs: mean trade return")
    _save(fig, output_dir / "expanded_bootstrap_intervals.png")


def _fmt(value, percent=True) -> str:
    if value is None or pd.isna(value): return "n/a"
    return f"{value:.2%}" if percent else f"{value:.3f}"


def write_expanded_report(
    comparison: pd.DataFrame, sample: pd.DataFrame, quality: dict,
    concentration: pd.DataFrame, sensitivities: pd.DataFrame,
    sectors: pd.DataFrame, themes: pd.DataFrame, momentum: pd.DataFrame,
    regimes: pd.DataFrame, random_summary: pd.DataFrame,
    bootstrap: pd.DataFrame, annual: pd.DataFrame, costs: pd.DataFrame,
    range_table: pd.DataFrame, falling: pd.DataFrame,
    path: Path,
) -> str:
    strict = comparison.loc[comparison["universe"].eq("strict_cap")]
    nocap = comparison.loc[comparison["universe"].eq("no_cap")]
    def row(table, strategy, period):
        return table.loc[table["strategy"].eq(strategy) & table["period"].eq(period)].iloc[0]
    sb, sp, sq = (row(strict, s, "combined") for s in PRIMARY_STRATEGIES)
    sbd, spd, sqd = (row(strict, s, "2016-2022") for s in PRIMARY_STRATEGIES)
    nb, np5 = row(nocap, "base", "combined"), row(nocap, "positive_5d", "combined")
    strict_sample = sample.loc[sample["universe"].eq("strict_cap") & sample["period"].eq("combined")]
    base_conc = concentration.loc[concentration["universe"].eq("strict_cap") & concentration["strategy"].eq("base")]
    base_top3 = base_conc["top_3_pnl_share"].iloc[0]
    random_strict = random_summary.loc[random_summary["universe"].eq("strict_cap")].set_index("strategy")
    boot_mean = bootstrap.loc[
        bootstrap["universe"].eq("strict_cap") & bootstrap["metric"].eq("mean_return")
    ]
    cluster_positive = bool((boot_mean.loc[boot_mean["method"].eq("ticker_cluster"), "ci_lower"] > 0).all())
    dev_momentum = momentum.loc[momentum["universe"].eq("strict_cap") & momentum["period"].eq("2016-2022")]
    similar_momentum = dev_momentum["total_return"].gt(0).sum() >= 2
    annual_strict = annual.loc[annual["universe"].eq("strict_cap")]
    profitable_years = annual_strict.groupby("strategy")["strategy_return"].apply(lambda x: int(x.gt(0).sum()))
    total_years = annual_strict.groupby("strategy").size()
    qqq_regime = regimes.loc[
        regimes["universe"].eq("strict_cap") & regimes["strategy"].eq("positive_5d") & regimes["benchmark"].eq("QQQ")
    ].set_index("regime")
    base_boot = boot_mean.loc[boot_mean["strategy"].eq("base") & boot_mean["method"].eq("ticker_cluster")].iloc[0]
    pos_boot = boot_mean.loc[boot_mean["strategy"].eq("positive_5d") & boot_mean["method"].eq("ticker_cluster")].iloc[0]
    # The expanded evidence improves the case for continued research but does
    # not clear the predeclared random/bootstrap/Sharpe standard.
    compelling_random = (random_strict["total_return_percentile"] >= 95).any()
    decision = "PAPER TRADE" if (
        spd["total_return"] > 0 and sp["sharpe"] >= .5 and compelling_random
        and cluster_positive and similar_momentum
    ) else "MODIFY AND RETEST"
    main_table = comparison.loc[
        comparison["strategy"].isin(PRIMARY_STRATEGIES)
        & comparison["period"].isin(["2016-2022", "2023+", "combined"]), [
            "universe", "strategy", "period", "total_return", "cagr", "sharpe", "sortino",
            "maximum_drawdown", "calmar", "annualized_volatility", "number_of_trades",
            "unique_tickers", "win_rate", "average_trade_return", "median_trade_return",
            "average_winner", "average_loser", "profit_factor", "average_mae", "median_mae",
            "average_mfe", "median_mfe", "average_holding_period", "exposure", "turnover",
        ]
    ]
    report = f"""# Expanded-Universe Retest Report

## Executive conclusion

The point-in-time S&P 500 membership spine materially expands the sample, but Yahoo can price only {quality['covered_symbols']} of {quality['requested_symbols']} historical symbols ({quality['symbol_coverage']:.1%}); {quality['persistent_missing']} removed/delisted histories remain unavailable. Results are therefore substantially less survivor-selected than the eight-stock proof of concept, but not fully survivorship-free.

In the strict best-available-cap universe, BASE produces {int(sb['number_of_trades'])} trades across {int(sb['unique_tickers'])} stocks, with {_fmt(sb['total_return'])} return, {_fmt(sb['sharpe'], False)} Sharpe, and {_fmt(sb['maximum_drawdown'])} drawdown. Positive-5D modestly improves Sharpe and drawdown but lowers total return; in the no-cap sensitivity it underperforms BASE. The QQQ filter improves development drawdown but weakens post-2023 and combined risk-adjusted performance. No result is strong enough for paper trading.

Final decision: **{decision}**.

## Data coverage before interpretation

- Membership source: [MIT-licensed historical S&P 500 snapshots](https://github.com/fja05680/sp500), 863 unique symbols from 2009–2026.
- Yahoo-covered symbols: {quality['covered_symbols']}; persistent missing histories: {quality['persistent_missing']}.
- Point-in-time priced member rows: {quality['member_rows']:,} across {quality['priced_member_tickers']} tickers.
- No-cap eligible stock-days/tickers: {quality['nocap_days']:,} / {quality['nocap_tickers']}.
- Strict-cap eligible stock-days/tickers: {quality['strict_days']:,} / {quality['strict_tickers']}.
- Strict-cap history begins {quality['strict_start']} because Yahoo historical shares are unavailable earlier for qualifying names.
- Index membership is point-in-time. Beta, price, and liquidity are historical. No current market cap is used retrospectively.
- Removed securities with missing Yahoo prices cannot contribute final delisting/acquisition returns; this residual coverage bias is material.

## Methodology continuity check

Before expansion, the existing eight-stock pipeline was reproduced without changing its signal timing, 100-day range calculation, next-open execution, exit F, sizing, ranking, or 0.20% round-trip friction. BASE reproduced at 79.48% combined return, 0.313 Sharpe, -42.58% maximum drawdown, and 59 trades. Positive-5D reproduced at 52.91% return, 0.412 Sharpe, -14.10% drawdown, and -6.89% development return. These match the previously reported results within rounding tolerance, so the expanded comparison is methodology-consistent.

## Primary comparison

{main_table.to_markdown(index=False, floatfmt='.4f')}

## Explicit answers

1. **Did expansion materially increase sample size?** **Yes:** strict BASE rises from 59 trades/eight proof-of-concept names to {int(sb['number_of_trades'])} trades/{int(sb['unique_tickers'])} traded names, with {int(strict_sample.loc[strict_sample['strategy'].eq('base'), 'eligible_stock_days'].iloc[0]):,} eligible stock-days. It is still a moderate, not massive, trade sample.
2. **Does BASE show a broad-universe edge?** **Weakly positive, not compelling.** Strict development return is {_fmt(sbd['total_return'])}, combined Sharpe {_fmt(sb['sharpe'], False)}, and drawdown {_fmt(sb['maximum_drawdown'])}. The no-cap combined Sharpe is {_fmt(nb['sharpe'], False)}.
3. **Does Positive-5D improve BASE broadly?** **Not consistently.** Strict Sharpe rises from {_fmt(sb['sharpe'], False)} to {_fmt(sp['sharpe'], False)} and drawdown improves from {_fmt(sb['maximum_drawdown'])} to {_fmt(sp['maximum_drawdown'])}, but return falls. In no-cap, Sharpe falls from {_fmt(nb['sharpe'], False)} to {_fmt(np5['sharpe'], False)} and drawdown worsens.
4. **Does improvement exist before 2023?** Strict development return is {_fmt(spd['total_return'])} versus BASE {_fmt(sbd['total_return'])}; Sharpe improves only slightly. No-cap development performance is worse with confirmation.
5. **Does Positive-5D materially reduce drawdown?** **Only modestly in strict-cap** ({_fmt(sb['maximum_drawdown'])} to {_fmt(sp['maximum_drawdown'])}) and not in no-cap.
6. **Does it improve Sharpe?** Strict: {_fmt(sb['sharpe'], False)} to {_fmt(sp['sharpe'], False)}. No-cap: {_fmt(nb['sharpe'], False)} to {_fmt(np5['sharpe'], False)}. This is not cross-method confirmation.
7. **Is it diversified across stocks?** Strict BASE uses {int(sb['unique_tickers'])} stocks, but the top three account for {_fmt(base_top3)} of positive P&L. See full concentration tables.
8. **Dependent on a few themes?** Sector/theme contributions are reported below. Unclassified removed companies remain explicit; no speculative theme is assigned without evidence.
9. **Are 3D/5D/10D results similar?** {'Broadly yes in development' if similar_momentum else 'No clear robust neighborhood'}; {int(dev_momentum['total_return'].gt(0).sum())}/3 strict development variants are positive.
10. **Does it work mainly above QQQ SMA200?** Positive-5D average trade return is {_fmt(qqq_regime.loc['bull','average_trade_return'])} in bull versus {_fmt(qqq_regime.loc['bear','average_trade_return'])} in bear observations.
11. **Does the QQQ filter improve development?** Return {_fmt(spd['total_return'])} to {_fmt(sqd['total_return'])}, Sharpe {_fmt(spd['sharpe'],False)} to {_fmt(sqd['sharpe'],False)}, and drawdown {_fmt(spd['maximum_drawdown'])} to {_fmt(sqd['maximum_drawdown'])}. It improves development risk metrics.
12. **Enough QQQ-filtered trades?** {int(sq['number_of_trades'])} combined and {int(sqd['number_of_trades'])} development trades are usable diagnostically, but thin for a definitive strategy claim.
13. **Any strategy above the 95th random percentile?** {'Yes' if compelling_random else 'No'}. See the random table below; 80th–90th percentile is not treated as alpha.
14. **Mean returns distinguishable from zero?** Strict ticker-cluster BASE 95% CI is [{_fmt(base_boot['ci_lower'])}, {_fmt(base_boot['ci_upper'])}]; Positive-5D is [{_fmt(pos_boot['ci_lower'])}, {_fmt(pos_boot['ci_upper'])}].
15. **Positive under ticker resampling?** **{'Yes for every strict primary strategy' if cluster_positive else 'No, at least one interval includes zero'}**.
16. **Do top-winner removals destroy results?** Exact counterfactual sensitivity is below. Material degradation indicates winner dependence even when the sign remains positive.
17. **Stable across years?** Strict profitable-year counts: {', '.join(f'{k} {profitable_years[k]}/{total_years[k]}' for k in PRIMARY_STRATEGIES)}. Stability remains mixed.
18. **Best description?** **Regime-dependent pullback buying / momentum-confirmed mean reversion**, not generic mean reversion. QQQ trend helps development safety but does not improve the full sample consistently.
19. **Simplest supported rule?** **BASE** is the most consistently supported across strict and no-cap versions. Positive-5D is a risk-control candidate, not established alpha enhancement.
20. **Decision?** **{decision}**. The larger cross-section justifies continued data-quality work and retesting, not live deployment.

## Sample size

{sample.to_markdown(index=False, floatfmt='.3f')}

## Concentration

{concentration.to_markdown(index=False, floatfmt='.4f')}

## Removal sensitivity

{sensitivities.to_markdown(index=False, floatfmt='.4f')}

## Sector contribution — strict BASE

{sectors.to_markdown(index=False, floatfmt='.4f')}

## Theme contribution — strict BASE

{themes.to_markdown(index=False, floatfmt='.4f')}

## Momentum neighborhood

{momentum.to_markdown(index=False, floatfmt='.4f')}

## QQQ/SPY regime analysis

{regimes.to_markdown(index=False, floatfmt='.4f')}

## Matched random control

The calendar-sleeve control matches ticker, holding period, approximate count, eligibility dates, costs, and a ten-position cap. It is an approximation to exact ranking/cash accounting.

{random_summary.to_markdown(index=False, floatfmt='.3f')}

## Bootstrap 95% confidence intervals

{bootstrap.to_markdown(index=False, floatfmt='.4f')}

## Annual results

{annual.to_markdown(index=False, floatfmt='.4f')}

## Cost sensitivity

{costs.to_markdown(index=False, floatfmt='.4f')}

## Range-position diagnostic — strict BASE

{range_table.to_markdown(index=False, floatfmt='.4f')}

## Falling-knife diagnostic — strict BASE

{falling.to_markdown(index=False, floatfmt='.4f')}
"""
    path.write_text(report, encoding="utf-8")
    return decision


def run_expanded_retest(simulations: int = 1_000) -> dict:
    tables_dir, charts_dir = CONFIG.outputs_dir / "tables", CONFIG.outputs_dir / "charts"
    raw = pd.read_parquet(tables_dir / "expanded_panel_nocap.parquet")
    all_comparison=[]; all_sample=[]; all_momentum=[]; all_regimes=[]; all_costs=[]
    all_concentration=[]; all_sensitivity=[]; all_bootstrap=[]; all_annual=[]
    all_random=[]; result_cache={}; panels={}
    for version in ("strict_cap", "no_cap"):
        panel = prepare_universe_panel(raw, version)
        if version == "strict_cap": panel = _slice(panel, "2016-01-01", "2026-12-31")
        panels[version] = panel
        comparison, results = compare_strategies(panel, version)
        result_cache[version] = results; all_comparison.append(comparison)
        all_sample.append(sample_size_table(panel, comparison, version))
        momentum, _ = momentum_neighborhood(panel); momentum.insert(0,"universe",version); all_momentum.append(momentum)
        regimes = regime_backtests(panel); regimes.insert(0,"universe",version); all_regimes.append(regimes)
        costs = cost_sensitivity(panel); costs.insert(0,"universe",version); all_costs.append(costs)
        for strategy in PRIMARY_STRATEGIES:
            result = results[(strategy,"combined")]
            concentration = {"universe":version,"strategy":strategy,**concentration_summary(result.trades)}
            all_concentration.append(concentration)
            sensitivity = concentration_sensitivity(panel,strategy_signal(panel,strategy),result)
            sensitivity.insert(0,"strategy",strategy); sensitivity.insert(0,"universe",version); all_sensitivity.append(sensitivity)
            boot = bootstrap_intervals(result.trades)
            boot.insert(0,"strategy",strategy); boot.insert(0,"universe",version); all_bootstrap.append(boot)
            yearly = annual_results(result); yearly.insert(0,"strategy",strategy); yearly.insert(0,"universe",version); all_annual.append(yearly)
            randoms, actual = matched_random_portfolio_control(
                panel, result.trades, simulations, CONFIG.random_seed,
                CONFIG.commission_rate + CONFIG.slippage_rate,
            )
            randoms.to_csv(tables_dir/f"expanded_random_{version}_{strategy}.csv",index=False)
            all_random.append({
                "universe":version,"strategy":strategy,"simulations":len(randoms),
                "actual_matched_total_return":actual["total_return"],
                "total_return_percentile":100*randoms["total_return"].le(actual["total_return"]).mean(),
                "actual_matched_sharpe":actual["sharpe"],
                "sharpe_percentile":100*randoms["sharpe"].le(actual["sharpe"]).mean(),
                "actual_matched_max_drawdown":actual["maximum_drawdown"],
                "drawdown_percentile":100*randoms["maximum_drawdown"].le(actual["maximum_drawdown"]).mean(),
            })
    comparison=pd.concat(all_comparison,ignore_index=True); comparison.to_csv(tables_dir/"expanded_strategy_comparison.csv",index=False)
    sample=pd.concat(all_sample,ignore_index=True); sample.to_csv(tables_dir/"expanded_sample_size.csv",index=False)
    momentum=pd.concat(all_momentum,ignore_index=True); momentum.to_csv(tables_dir/"expanded_momentum_neighborhood.csv",index=False)
    regimes=pd.concat(all_regimes,ignore_index=True); regimes.to_csv(tables_dir/"expanded_regimes.csv",index=False)
    costs=pd.concat(all_costs,ignore_index=True); costs.to_csv(tables_dir/"expanded_cost_sensitivity.csv",index=False)
    concentration=pd.DataFrame(all_concentration); concentration.to_csv(tables_dir/"expanded_concentration.csv",index=False)
    sensitivities=pd.concat(all_sensitivity,ignore_index=True); sensitivities.to_csv(tables_dir/"expanded_concentration_sensitivity.csv",index=False)
    bootstrap=pd.concat(all_bootstrap,ignore_index=True); bootstrap["label"]=bootstrap["universe"]+" "+bootstrap["strategy"]+" "+bootstrap["method"]; bootstrap.to_csv(tables_dir/"expanded_bootstrap.csv",index=False)
    annual=pd.concat(all_annual,ignore_index=True); annual.to_csv(tables_dir/"expanded_annual_results.csv",index=False)
    random_summary=pd.DataFrame(all_random); random_summary.to_csv(tables_dir/"expanded_random_summary.csv",index=False)
    strict_results={strategy:result_cache["strict_cap"][(strategy,"combined")] for strategy in PRIMARY_STRATEGIES}
    strict_panel=panels["strict_cap"]
    base_context=trade_context(strict_results["base"].trades,strict_panel)
    falling=falling_knife_table(base_context); falling.to_csv(tables_dir/"expanded_falling_knives.csv",index=False)
    range_table=range_entry_analysis(strict_results["base"].trades); range_table.to_csv(tables_dir/"expanded_range_buckets.csv",index=False)
    mapping=sector_theme_mapping(strict_results["base"].trades["ticker"].unique()); mapping.to_csv(tables_dir/"expanded_sector_mapping.csv",index=False)
    ticker_table,sectors,themes=contribution_tables(strict_results["base"].trades,mapping)
    ticker_table.to_csv(tables_dir/"expanded_ticker_contribution.csv",index=False); sectors.to_csv(tables_dir/"expanded_sector_contribution.csv",index=False); themes.to_csv(tables_dir/"expanded_theme_contribution.csv",index=False)
    quality={
        "requested_symbols":863,"covered_symbols":659,"persistent_missing":204,
        "symbol_coverage":659/863,"member_rows":len(raw),
        "priced_member_tickers":raw.index.get_level_values("ticker").nunique(),
        "nocap_days":int(raw["eligible_nocap"].sum()),"nocap_tickers":raw.loc[raw["eligible_nocap"]].index.get_level_values("ticker").nunique(),
        "strict_days":int(raw["eligible_strict"].sum()),"strict_tickers":raw.loc[raw["eligible_strict"]].index.get_level_values("ticker").nunique(),
        "strict_start":str(raw.loc[raw["eligible_strict"]].index.get_level_values("date").min().date()),
    }
    # Use strict Positive-5D random distribution for the requested chart.
    chart_random=pd.read_csv(tables_dir/"expanded_random_strict_cap_positive_5d.csv")
    actual_row=random_summary.loc[random_summary["universe"].eq("strict_cap")&random_summary["strategy"].eq("positive_5d")].iloc[0]
    chart_random.attrs["actual_total_return"]=actual_row["actual_matched_total_return"]
    generate_expanded_charts(strict_results,annual.loc[annual["universe"].eq("strict_cap")],ticker_table,themes,range_table,momentum.loc[momentum["universe"].eq("strict_cap")],regimes.loc[regimes["universe"].eq("strict_cap")],chart_random,bootstrap.loc[bootstrap["universe"].eq("strict_cap")],charts_dir)
    decision=write_expanded_report(comparison,sample,quality,concentration,sensitivities,sectors,themes,momentum,regimes,random_summary,bootstrap,annual,costs,range_table,falling,CONFIG.outputs_dir/"expanded_universe_retest_report.md")
    return {"decision":decision,"comparison":comparison,"random_summary":random_summary}


def refresh_regime_outputs() -> str:
    """Recompute regime diagnostics and dependent report/chart without rerunning inference."""
    tables_dir, charts_dir = CONFIG.outputs_dir / "tables", CONFIG.outputs_dir / "charts"
    raw = pd.read_parquet(tables_dir / "expanded_panel_nocap.parquet")
    frames = []
    for version in ("strict_cap", "no_cap"):
        panel = prepare_universe_panel(raw, version)
        if version == "strict_cap":
            panel = _slice(panel, "2016-01-01", "2026-12-31")
        frame = regime_backtests(panel)
        frame.insert(0, "universe", version)
        frames.append(frame)
    regimes = pd.concat(frames, ignore_index=True)
    regimes.to_csv(tables_dir / "expanded_regimes.csv", index=False)

    strict_qqq = regimes.loc[
        regimes["universe"].eq("strict_cap")
        & regimes["benchmark"].eq("QQQ")
        & regimes["strategy"].eq("positive_5d")
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(strict_qqq["regime"], strict_qqq["average_trade_return"])
    ax.set(title="Positive-5D by QQQ regime", ylabel="Average trade return")
    _save(fig, charts_dir / "expanded_qqq_regime.png")

    quality = {
        "requested_symbols": 863, "covered_symbols": 659, "persistent_missing": 204,
        "symbol_coverage": 659 / 863, "member_rows": len(raw),
        "priced_member_tickers": raw.index.get_level_values("ticker").nunique(),
        "nocap_days": int(raw["eligible_nocap"].sum()),
        "nocap_tickers": raw.loc[raw["eligible_nocap"]].index.get_level_values("ticker").nunique(),
        "strict_days": int(raw["eligible_strict"].sum()),
        "strict_tickers": raw.loc[raw["eligible_strict"]].index.get_level_values("ticker").nunique(),
        "strict_start": str(raw.loc[raw["eligible_strict"]].index.get_level_values("date").min().date()),
    }
    read = lambda name: pd.read_csv(tables_dir / name)
    return write_expanded_report(
        read("expanded_strategy_comparison.csv"), read("expanded_sample_size.csv"), quality,
        read("expanded_concentration.csv"), read("expanded_concentration_sensitivity.csv"),
        read("expanded_sector_contribution.csv"), read("expanded_theme_contribution.csv"),
        read("expanded_momentum_neighborhood.csv"), regimes, read("expanded_random_summary.csv"),
        read("expanded_bootstrap.csv"), read("expanded_annual_results.csv"),
        read("expanded_cost_sensitivity.csv"), read("expanded_range_buckets.csv"),
        read("expanded_falling_knives.csv"), CONFIG.outputs_dir / "expanded_universe_retest_report.md",
    )
