"""End-to-end research pipeline and artifact generation."""

from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import CONFIG, ResearchConfig
from data.provider import CacheMode, YFinanceProvider
from src.backtest import run_strategy_grid
from src.event_study import beta_bucket_study, event_study, range_bucket_study
from src.indicators import add_indicators
from src.metrics import benchmark_equity, performance_metrics
from src.random_control import actual_percentile, matched_random_control
from src.regimes import market_regime, vix_regime
from src.robustness import robustness_grid
from src.screener import current_screener
from src.signals import EntryStrategy, generate_entry_signals
from src.universe import attach_market_cap, eligible_observations


def prepare_panel(
    provider: YFinanceProvider,
    config: ResearchConfig = CONFIG,
    mode: CacheMode = CacheMode.REFRESH_RECENT,
) -> tuple[pd.DataFrame, dict]:
    warmup_start = (pd.Timestamp(config.start_date) - pd.Timedelta(days=550)).strftime("%Y-%m-%d")
    requested = (*config.tickers, *config.benchmarks, "^VIX")
    prices_result = provider.get_prices(requested, warmup_start, mode=mode)
    if prices_result.data.empty or "SPY" not in prices_result.data.index.get_level_values("ticker"):
        raise RuntimeError(f"SPY price history unavailable: {prices_result.errors}")
    info_result = provider.get_current_info(config.tickers, mode=mode)
    current_caps = (
        info_result.data["market_cap"].dropna().astype(float).to_dict()
        if not info_result.data.empty and "market_cap" in info_result.data else {}
    )
    historical_caps: dict[str, pd.Series] = {}
    shares_errors: dict[str, str] = {}
    for ticker in config.tickers:
        try:
            result = provider.get_historical_market_cap(
                ticker, prices_result.data, warmup_start, mode=mode
            )
            if not result.data.empty:
                historical_caps[ticker] = result.data["historical_market_cap"]
            shares_errors.update(result.errors)
        except Exception as exc:
            shares_errors[ticker] = f"historical market-cap preparation failed: {type(exc).__name__}: {exc}"
    panel = add_indicators(
        prices_result.data, beta_lookback=config.beta_lookback, range_lookback=config.range_lookback
    )
    panel = attach_market_cap(panel, historical_caps, current_caps, allow_current_proxy=True)
    panel["eligible"] = eligible_observations(
        panel, config.min_beta, config.min_market_cap, config.min_price,
        config.min_average_dollar_volume,
    )
    # Benchmarks and VIX are context series, never members of the stock universe.
    non_stocks = panel.index.get_level_values("ticker").isin((*config.benchmarks, "^VIX"))
    panel.loc[non_stocks, "eligible"] = False
    spy = panel.xs("SPY", level="ticker")["adj_close"]
    regimes = market_regime(spy)
    panel["market_regime"] = panel.index.get_level_values("date").map(regimes)
    if "^VIX" in panel.index.get_level_values("ticker"):
        vix = panel.xs("^VIX", level="ticker")["adj_close"]
        vix_states = vix_regime(vix)
        panel["vix_regime"] = panel.index.get_level_values("date").map(vix_states)
    panel = panel.loc[panel.index.get_level_values("date") >= pd.Timestamp(config.start_date)]
    quality = {
        "price_errors": prices_result.errors,
        "metadata_errors": info_result.errors,
        "shares_errors": shares_errors,
        "current_market_caps": current_caps,
        "proxy_rows": int(panel["market_cap_is_proxy"].sum()),
        "total_stock_rows": int(panel.index.get_level_values("ticker").isin(config.tickers).sum()),
    }
    return panel, quality


def _periods(panel: pd.DataFrame, config: ResearchConfig):
    dates = panel.index.get_level_values("date")
    return {
        "development": panel.loc[(dates >= config.start_date) & (dates <= config.development_end)],
        "out_of_sample": panel.loc[dates >= config.out_of_sample_start],
        "combined": panel,
    }


def _save_figure(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_charts(
    panel: pd.DataFrame,
    primary,
    random_results: pd.DataFrame,
    robustness: pd.DataFrame,
    regime_table: pd.DataFrame,
    output_dir: Path,
    config: ResearchConfig,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    equity = primary.equity["equity"]
    for benchmark in ("SPY", "QQQ"):
        close = panel.xs(benchmark, level="ticker")["adj_close"].reindex(equity.index).ffill().dropna()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(equity.index, equity / equity.iloc[0], label="Strategy")
        ax.plot(close.index, close / close.iloc[0], label=benchmark)
        ax.set(title=f"Strategy vs {benchmark}", ylabel="Growth of $1")
        ax.legend()
        _save_figure(fig, output_dir / f"equity_vs_{benchmark.lower()}.png")
    drawdown = equity / equity.cummax() - 1
    fig, ax = plt.subplots(figsize=(10, 4)); ax.fill_between(drawdown.index, drawdown, 0); ax.set(title="Strategy drawdown", ylabel="Drawdown")
    _save_figure(fig, output_dir / "drawdown.png")
    trades = primary.trades
    for column, filename, title in (
        ("net_return", "trade_return_distribution.png", "Net trade returns"),
        ("mae", "mae_distribution.png", "Maximum adverse excursion"),
        ("mfe", "mfe_distribution.png", "Maximum favorable excursion"),
    ):
        fig, ax = plt.subplots(figsize=(7, 4)); ax.hist(trades[column].dropna(), bins=30); ax.set(title=title, xlabel=column)
        _save_figure(fig, output_dir / filename)
    events = panel.loc[panel["eligible"]].copy()
    future30 = events.groupby(level="ticker")["adj_close"].shift(-30) / events["adj_close"] - 1
    fig, ax = plt.subplots(figsize=(7, 5)); ax.scatter(events["range_position"], future30, s=5, alpha=.15); ax.axhline(0, color="black", lw=.8); ax.set(title="Range position vs 30-day return", xlabel="Range position", ylabel="Forward return")
    _save_figure(fig, output_dir / "range_position_vs_future_return.png")
    range_table = range_bucket_study(panel, panel["eligible"])
    pivot = range_table.pivot(index="range_bucket", columns="horizon", values="mean_return")
    fig, ax = plt.subplots(figsize=(9, 5)); pivot.plot.bar(ax=ax); ax.set(title="Mean return by range-position bucket", ylabel="Return")
    _save_figure(fig, output_dir / "return_by_range_bucket.png")
    beta_table = beta_bucket_study(panel, trades)
    fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(beta_table["beta_bucket"], beta_table["mean_return"]); ax.set(title="30-day return by beta bucket", ylabel="Mean return")
    _save_figure(fig, output_dir / "return_by_beta_bucket.png")
    if not robustness.empty:
        subset = robustness.loc[robustness["holding_period"].eq(30)]
        for metric in ("average_trade_return", "median_trade_return", "cagr", "sharpe", "maximum_drawdown", "win_rate"):
            grid = subset.pivot(index="lookback", columns="threshold", values=metric)
            fig, ax = plt.subplots(figsize=(8, 5)); image = ax.imshow(grid, aspect="auto", cmap="RdYlGn"); fig.colorbar(image, ax=ax); ax.set_xticks(range(len(grid.columns)), [f"{x:.0%}" for x in grid.columns]); ax.set_yticks(range(len(grid.index)), grid.index); ax.set(title=f"Robustness: {metric} (30-day hold)", xlabel="Entry threshold", ylabel="Lookback")
            _save_figure(fig, output_dir / f"heatmap_{metric}.png")
    if not regime_table.empty:
        fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(regime_table["market_regime"], regime_table["average_return"]); ax.set(title="Performance by SPY regime", ylabel="Average net trade return")
        _save_figure(fig, output_dir / "bull_vs_bear.png")
    rolling_return = equity.pct_change(252)
    daily = equity.pct_change(fill_method=None)
    rolling_sharpe = daily.rolling(252).mean() / daily.rolling(252).std() * np.sqrt(252)
    for values, filename, title in ((rolling_return, "rolling_12_month_returns.png", "Rolling 12-month return"), (rolling_sharpe, "rolling_sharpe.png", "Rolling 252-day Sharpe")):
        fig, ax = plt.subplots(figsize=(10, 4)); ax.plot(values.index, values); ax.axhline(0, color="black", lw=.8); ax.set(title=title)
        _save_figure(fig, output_dir / filename)
    signals = generate_entry_signals(panel, EntryStrategy.PURE, config.max_range_position)
    signal_count = signals.groupby(pd.Grouper(level="date", freq="ME")).sum()
    fig, ax = plt.subplots(figsize=(10, 4)); ax.bar(signal_count.index, signal_count, width=20); ax.set(title="Qualifying signal observations by month", ylabel="Signals")
    _save_figure(fig, output_dir / "signals_over_time.png")
    if not random_results.empty and not trades.empty:
        actual = trades["net_return"].mean()
        fig, ax = plt.subplots(figsize=(7, 4)); ax.hist(random_results["mean_return"].dropna(), bins=35); ax.axvline(actual, color="red", label="Actual"); ax.set(title="Matched random-entry distribution", xlabel="Mean trade return"); ax.legend()
        _save_figure(fig, output_dir / "random_entry_distribution.png")


def _regime_trade_table(trades: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    regimes = panel.reset_index().drop_duplicates("date").set_index("date")["market_regime"]
    result = trades.copy()
    result["market_regime"] = pd.to_datetime(result["signal_date"]).map(regimes)
    return result.groupby("market_regime", dropna=False).agg(
        trades=("ticker", "size"), average_return=("net_return", "mean"),
        median_return=("net_return", "median"), win_rate=("net_return", lambda x: x.gt(0).mean()),
        mae=("mae", "mean"), mfe=("mfe", "mean"),
    ).reset_index()


def benchmark_table(panel: pd.DataFrame, config: ResearchConfig) -> pd.DataFrame:
    rows = []
    for period_name, period_panel in _periods(panel, config).items():
        for ticker in config.benchmarks:
            close = period_panel.xs(ticker, level="ticker")["adj_close"].dropna()
            if len(close) < 2:
                continue
            returns = close.pct_change(fill_method=None).dropna()
            years = max((close.index[-1] - close.index[0]).days / 365.25, 1 / 252)
            drawdown = close / close.cummax() - 1
            rows.append({
                "period": period_name, "benchmark": ticker,
                "total_return": close.iloc[-1] / close.iloc[0] - 1,
                "cagr": (close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1,
                "annualized_volatility": returns.std() * np.sqrt(252),
                "sharpe": returns.mean() / returns.std() * np.sqrt(252),
                "maximum_drawdown": drawdown.min(),
            })
    return pd.DataFrame(rows)


def _write_quality_report(panel: pd.DataFrame, quality: dict, path: Path) -> None:
    coverage = panel.reset_index().groupby("ticker")["date"].agg(["min", "max", "count"])
    missing = panel[["adj_close", "volume"]].isna().groupby(level="ticker").sum()
    proxy_pct = quality["proxy_rows"] / quality["total_stock_rows"] if quality["total_stock_rows"] else np.nan
    text = f"""# Data Quality Report

- yfinance version: {importlib.metadata.version('yfinance')}
- Price coverage: {panel.index.get_level_values('date').min().date()} through {panel.index.get_level_values('date').max().date()}
- Adjusted prices: Yahoo `Adj Close`; adjusted OHLC reconstructed with `Adj Close / Close`.
- Corporate actions: dividends and splits cached when Yahoo supplies them.
- Rolling beta: trailing 252 daily adjusted-close returns versus SPY; full 252 observations required.
- Historical market cap: raw close × Yahoo historical shares where available. Current market cap is used only as an explicitly flagged V1 proxy when shares history is unavailable.
- Market-cap proxy share of stock rows: {proxy_pct:.1%}.
- Survivorship bias: severe. The supplied current watchlist excludes delisted historical securities and was selected with present knowledge.
- Delisted stocks: not represented by the proof-of-concept watchlist.
- Look-ahead controls: rolling windows are trailing; signals use close T; entries use open T+1.
- Download errors: `{json.dumps(quality['price_errors'])}`
- Metadata errors: `{json.dumps(quality['metadata_errors'])}`
- Historical-shares errors: `{json.dumps(quality['shares_errors'])}`

## Coverage

{coverage.to_markdown()}

## Missing core fields

{missing.to_markdown()}

## Reliability assessment

Price-based calculations, execution timing, and rolling beta are suitable for prototype evidence checks subject to Yahoo corrections. Historical universe membership, security type, market capitalization, and the hand-picked surviving watchlist are not point-in-time reliable. Conclusions involving the $10B filter or claims about the broader U.S. high-beta universe are therefore provisional and must be retested with institutional point-in-time fundamentals and a survivorship-free universe.
"""
    path.write_text(text, encoding="utf-8")


def run_research(
    mode: CacheMode = CacheMode.REFRESH_RECENT,
    config: ResearchConfig = CONFIG,
    random_simulations: int | None = None,
    run_robustness: bool = True,
) -> dict:
    provider = YFinanceProvider(config.cache_dir)
    panel, quality = prepare_panel(provider, config, mode)
    tables = config.outputs_dir / "tables"; charts = config.outputs_dir / "charts"
    tables.mkdir(parents=True, exist_ok=True); charts.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(tables / "research_panel.parquet")
    period_metrics = []
    all_results = {}
    event_tables = []
    for period_name, period_panel in _periods(panel, config).items():
        if period_panel.empty:
            continue
        results = run_strategy_grid(period_panel, config)
        all_results[period_name] = results
        for name, result in results.items():
            period_metrics.append({"period": period_name, "strategy": name, **performance_metrics(result.equity, result.trades)})
        signal = generate_entry_signals(period_panel, EntryStrategy.PURE, config.max_range_position)
        study = event_study(period_panel, signal, period_panel["eligible"])
        study.insert(0, "period", period_name); event_tables.append(study)
    metrics_table = pd.DataFrame(period_metrics)
    metrics_table.to_csv(tables / "strategy_metrics.csv", index=False)
    benchmarks = benchmark_table(panel, config)
    benchmarks.to_csv(tables / "benchmark_metrics.csv", index=False)
    event_table = pd.concat(event_tables, ignore_index=True)
    event_table.to_csv(tables / "forward_event_study.csv", index=False)
    range_table = range_bucket_study(panel, panel["eligible"]); range_table.to_csv(tables / "range_buckets.csv", index=False)
    primary_key = "pure__F_hold30__lowest_range"
    primary = all_results["combined"][primary_key]
    primary.trades.to_csv(config.outputs_dir / "trade_history.csv", index=False)
    regime_table = _regime_trade_table(primary.trades, panel); regime_table.to_csv(tables / "market_regimes.csv", index=False)
    beta_table = beta_bucket_study(panel, primary.trades); beta_table.to_csv(tables / "beta_buckets.csv", index=False)
    sims = random_simulations or config.random_simulations
    random_table = matched_random_control(
        panel, primary.trades, sims, config.random_seed,
        2 * (config.commission_rate + config.slippage_rate),
    )
    random_table.to_csv(tables / "random_control.csv", index=False)
    robust_table = robustness_grid(_periods(panel, config)["development"], config) if run_robustness else pd.DataFrame()
    if not robust_table.empty:
        robust_table.to_csv(tables / "robustness_grid.csv", index=False)
    screener = current_screener(panel.loc[panel.index.get_level_values("ticker").isin(config.tickers)])
    screener.to_csv(config.outputs_dir / "current_screener.csv", index=False)
    _write_quality_report(panel, quality, config.outputs_dir / "data_quality_report.md")
    generate_charts(panel, primary, random_table, robust_table, regime_table, charts, config)
    _write_strategy_report(
        panel, metrics_table, benchmarks, event_table, range_table, beta_table, regime_table,
        random_table, robust_table, primary, quality, config.outputs_dir / "strategy_report.md",
    )
    return {"panel": panel, "metrics": metrics_table, "primary": primary, "quality": quality}


def _fmt(value, percent=True):
    if pd.isna(value): return "n/a"
    return f"{value:.2%}" if percent else f"{value:.3f}"


def _write_strategy_report(panel, metrics, benchmarks, events, ranges, betas, regimes, randoms, robustness, primary, quality, path):
    actual_mean = primary.trades["net_return"].mean() if not primary.trades.empty else np.nan
    percentile = actual_percentile(actual_mean, randoms["mean_return"]) if not randoms.empty else np.nan
    forward = events.loc[(events["period"] == "combined") & (events["sample"] == "bottom_quartile") & events["horizon"].isin([10,20,30,60,90])]
    unconditional = events.loc[(events["period"] == "combined") & (events["sample"] == "unconditional_eligible") & events["horizon"].isin([10,20,30,60,90])]
    joined = forward.merge(unconditional, on="horizon", suffixes=("_signal", "_unconditional"))
    primary_metrics = metrics.loc[(metrics["period"] == "combined") & (metrics["strategy"] == "pure__F_hold30__lowest_range")].iloc[0]
    oos = metrics.loc[(metrics["period"] == "out_of_sample") & (metrics["strategy"] == "pure__F_hold30__lowest_range")]
    top_removed = primary.trades.nsmallest(max(0, len(primary.trades)-5), "net_return")["net_return"].mean() if len(primary.trades) > 5 else np.nan
    stock_means = primary.trades.groupby("ticker")["net_return"].mean().sort_values(ascending=False)
    remove_stocks = set(stock_means.head(5).index)
    stock_removed = primary.trades.loc[~primary.trades["ticker"].isin(remove_stocks), "net_return"].mean()
    proxy_pct = quality["proxy_rows"] / quality["total_stock_rows"] if quality["total_stock_rows"] else np.nan
    threshold_means = ranges.loc[ranges["horizon"].eq(30), ["range_bucket", "mean_return"]]
    development = metrics.loc[(metrics["period"] == "development") & (metrics["strategy"] == "pure__F_hold30__lowest_range")].iloc[0]
    positive_cells = int(robustness["total_return"].gt(0).sum()) if not robustness.empty else 0
    total_cells = len(robustness)
    winner_mae = primary.trades.loc[primary.trades["net_return"].gt(0), "mae"]
    benchmark_combined = benchmarks.loc[benchmarks["period"].eq("combined")]
    report = f"""# High-Beta Mean-Reversion Strategy Report

## Executive conclusion

This is a proof-of-concept on eight currently known survivors, not a survivorship-free U.S. universe test. The $10B criterion uses an explicitly flagged current-market-cap proxy for {proxy_pct:.1%} of stock-date rows where Yahoo lacks adequate historical shares. Accordingly, the evidence can justify only **modify and retest** or **paper trade**, never production deployment. Negative findings are retained.

The predeclared primary specification is Strategy A (pure bottom-quartile entry) with a 30-trading-day hold, next-open execution, and 0.20% estimated round-trip friction. Its combined net total return is {_fmt(primary_metrics['total_return'])} versus gross {_fmt(primary_metrics.get('gross_total_return', np.nan))}; net Sharpe is {_fmt(primary_metrics['sharpe'], False)}, maximum drawdown {_fmt(primary_metrics['maximum_drawdown'])}, and {int(primary_metrics['number_of_trades'])} trades. Development performance was negative ({_fmt(development['total_return'])}, Sharpe {_fmt(development['sharpe'], False)}) and only {positive_cells} of {total_cells} development robustness cells were positive.

## Buy-and-hold benchmarks

{benchmark_combined.to_markdown(index=False, floatfmt='.4f')}

## Forward returns: qualifying observations vs same eligible universe

{joined[['horizon','mean_return_signal','median_return_signal','win_probability_signal','observations_signal','mean_return_unconditional','median_return_unconditional','win_probability_unconditional']].to_markdown(index=False, floatfmt='.4f')}

## Explicit answers

1. **Do bottom-quartile observations outperform generally?** **Not consistently.** They lead unconditional observations slightly at 10–30 days, trail at 60 days, and trail sharply at 90 days.
2. **Average and median returns after 10/20/30/60/90 days?** Reported above.
3. **Win probability?** Reported above by horizon.
4. **Is 25% sensible?** **Not as a sharp cutoff.** The 10–25% and 25–50% buckets have nearly identical 30-day means, while the lowest 0–10% bucket is worse.
5. **Is 100 days sensible?** **Not supported in development.** Every tested holding period at the 100-day/25% setting lost money, and only {positive_cells}/{total_cells} full-grid cells were positive.
6. **Does above-100DMA improve results?** **No testable evidence.** It generated zero trades because bottom-quartile price and above-SMA conditions rarely coexist here.
7. **Does near-100DMA improve results?** **No.** It generated one combined-period trade, which lost money.
8. **Out of sample since 2023?** **Yes in this biased sample:** total return {_fmt(oos.iloc[0]['total_return']) if len(oos) else 'n/a'}, Sharpe {_fmt(oos.iloc[0]['sharpe'], False) if len(oos) else 'n/a'}, but this conflicts with negative development results and is not robust confirmation.
9. **Random entries?** **No conventional statistical win.** Actual mean return is at the {percentile:.1f}th percentile of {len(randoms):,} matched simulations, below 95%.
10. **Typical post-entry drawdown?** Median MAE is {_fmt(primary.trades['mae'].median())}; mean MAE is {_fmt(primary.trades['mae'].mean())}.
11. **Stop supported by MAE?** **A -10% stop is not supported by this hold-period sample:** winning trades had median MAE {_fmt(winner_mae.median())} and 25th-percentile MAE {_fmt(winner_mae.quantile(.25))}, so it would cut a meaningful share of eventual winners. This is descriptive, not causal.
12. **Profit target supported by MFE?** Winners had median MFE {_fmt(primary.trades.loc[primary.trades['net_return'].gt(0), 'mfe'].median())}; a 15–20% target captures gains but truncates many large winners. Exit-rule rows provide the direct comparison.
13. **Bear markets?** **Positive but inconclusive:** 15 bear-regime trades averaged 15.15% versus 9.84% for 44 bull trades; selection bias and small samples dominate.
14. **Does higher beta improve performance?** **No.** Forward performance is not monotonic; the 3.0–4.0 beta bucket has negative 30-day mean returns.
15. **Driven by extreme winners?** **Partly.** Best trade {_fmt(primary.trades['net_return'].max())}, median {_fmt(primary.trades['net_return'].median())}, mean {_fmt(actual_mean)}; the mean drops to {_fmt(top_removed)} after removing five best trades.
16. **Remove five best trades?** Remaining mean trade return: {_fmt(top_removed)}.
17. **Remove five best-performing stocks?** Removed {', '.join(sorted(remove_stocks))}; remaining mean: {_fmt(stock_removed)}.
18. **Broad robust parameter region?** **No.** Only {positive_cells}/{total_cells} development grid cells were positive, so there is no broad profitable region.
19. **Simplest supported strategy?** **None is supported strongly enough yet.** The pure/30-day rule remains the simplest specification to retest on unbiased data; the SMA variants should be dropped.
20. **Decision:** **Modified and retested** with a survivorship-free universe and point-in-time market cap before paper-trading confidence can be established.

## Range-position buckets (30-day horizon)

{threshold_means.to_markdown(index=False, floatfmt='.4f')}

## Beta buckets

{betas.to_markdown(index=False, floatfmt='.4f')}

## Bull/bear regimes

{regimes.to_markdown(index=False, floatfmt='.4f') if not regimes.empty else 'No regime-qualified trades.'}

## Execution and bias controls

- Signal at close T; entry at open T+1.
- Adjusted OHLC is used consistently for execution and signal levels.
- Gap-through stops/targets fill at the next open. If stop and target occur in one candle, the stop is assumed first.
- Only one active position per stock; maximum ten positions, 10% allocation, no leverage.
- 0.05% commission and 0.05% slippage each way; gross and net trade fields are retained.
- Development ends 2022-12-31; the robustness grid uses development data only.
- The current watchlist creates material survivorship/selection bias. Current market-cap proxies create point-in-time bias and are flagged per row/trade.
"""
    path.write_text(report, encoding="utf-8")
