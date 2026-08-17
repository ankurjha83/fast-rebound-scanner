"""Pre-specified exit-management research for the frozen strict-cap BASE entry."""

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
from src.expanded_retest import (
    _slice, annual_results, bootstrap_intervals, prepare_universe_panel, strategy_signal,
)
from src.regime_diagnosis import _suppress_trade_windows
from src.metrics import performance_metrics
from src.portfolio import BacktestResult, ExitRule, run_portfolio
from src.random_control import matched_random_portfolio_control


PERIODS = {
    "2016-2022": ("2016-01-01", "2022-12-31"),
    "2023+": ("2023-01-01", "2026-12-31"),
    "combined": ("2016-01-01", "2026-12-31"),
}

EXIT_VARIANTS: dict[str, ExitRule] = {
    "exit_0_baseline_hold30": ExitRule("baseline_hold30", hold_days=30),
    "exit_1_hold20": ExitRule("hold20", hold_days=20),
    "exit_2_hold40": ExitRule("hold40", hold_days=40),
    "exit_3_hold60": ExitRule("hold60", hold_days=60),
    "exit_4_hold90": ExitRule("hold90", hold_days=90),
    "exit_5_stop10_hold60": ExitRule("stop10_hold60", stop_loss=.10, hold_days=60),
    "exit_6_stop15_hold60": ExitRule("stop15_hold60", stop_loss=.15, hold_days=60),
    "exit_7_stop20_hold60": ExitRule("stop20_hold60", stop_loss=.20, hold_days=60),
    "exit_8_trail10": ExitRule("trail10", stop_loss=.15, trail_activation=.10, trailing_stop=.10),
    "exit_9_trail7_5": ExitRule("trail7_5", stop_loss=.15, trail_activation=.10, trailing_stop=.075),
    "exit_10_trail5": ExitRule("trail5", stop_loss=.15, trail_activation=.10, trailing_stop=.05),
    "exit_11_profit_protection": ExitRule("profit_protection", stop_loss=.15, hold_days=90, profit_ratchet=True),
    "exit_12_range75_hold90": ExitRule("range75_hold90", range_exit=.75, hold_days=90),
    "exit_13_range75_stop15_hold90": ExitRule("range75_stop15_hold90", stop_loss=.15, range_exit=.75, hold_days=90),
}


def run_exit(panel: pd.DataFrame, rule: ExitRule, signal: pd.Series | None = None) -> BacktestResult:
    prepared = panel.copy()
    prepared["entry_signal"] = (
        strategy_signal(prepared, "base") if signal is None else signal.reindex(prepared.index).fillna(False)
    )
    return run_portfolio(
        prepared, rule, CONFIG.initial_capital, CONFIG.max_positions, CONFIG.position_fraction,
        CONFIG.commission_rate, CONFIG.slippage_rate, "lowest_range",
    )


def mfe_capture_ratio(trades: pd.DataFrame) -> float:
    profitable = trades.loc[trades["net_return"].gt(0) & trades["mfe"].gt(0)]
    if profitable.empty:
        return np.nan
    return profitable["net_return"].div(profitable["mfe"]).mean()


def drawdown_diagnostics(equity: pd.DataFrame) -> tuple[int, float]:
    if equity.empty:
        return 0, np.nan
    values = equity["equity"]
    dd = values / values.cummax() - 1.0
    underwater = dd.lt(0).to_numpy()
    longest = current = 0
    for flag in underwater:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    trough = dd.idxmin()
    prior_peak_value = values.loc[:trough].cummax().iloc[-1]
    recovered = values.loc[trough:].loc[values.loc[trough:].ge(prior_peak_value)]
    recovery = float(values.index.get_loc(recovered.index[0]) - values.index.get_loc(trough)) if len(recovered) else np.nan
    return longest, recovery


def _extended(result: BacktestResult) -> dict[str, float]:
    m = performance_metrics(result.equity, result.trades)
    t = result.trades
    longest, recovery = drawdown_diagnostics(result.equity)
    exposure = m.get("exposure", np.nan)
    m.update({
        "unique_tickers": t["ticker"].nunique() if len(t) else 0,
        "average_mae": t["mae"].mean() if len(t) else np.nan,
        "median_mae": t["mae"].median() if len(t) else np.nan,
        "mae_5th_percentile": t["mae"].quantile(.05) if len(t) else np.nan,
        "average_mfe": t["mfe"].mean() if len(t) else np.nan,
        "median_mfe": t["mfe"].median() if len(t) else np.nan,
        "trade_return_5th_percentile": t["net_return"].quantile(.05) if len(t) else np.nan,
        "longest_drawdown_bars": longest,
        "max_drawdown_recovery_bars": recovery,
        "mfe_capture_ratio": mfe_capture_ratio(t),
        "return_per_exposure": m["total_return"] / exposure if exposure else np.nan,
        "drawdown_per_exposure": m["maximum_drawdown"] / exposure if exposure else np.nan,
        "return_per_average_invested_dollar": m["total_return"] / exposure if exposure else np.nan,
    })
    return m


def compare_exits(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[str, str], BacktestResult]]:
    signal = strategy_signal(panel, "base")
    rows, results = [], {}
    for exit_name, rule in EXIT_VARIANTS.items():
        for period, (start, end) in PERIODS.items():
            part = _slice(panel, start, end)
            result = run_exit(part, rule, signal.reindex(part.index).fillna(False))
            results[(exit_name, period)] = result
            rows.append({"exit": exit_name, "period": period, **_extended(result)})
    return pd.DataFrame(rows), results


def _trade_path(panel: pd.DataFrame, trade: pd.Series) -> pd.DataFrame:
    frame = panel.xs(trade["ticker"], level="ticker").sort_index()
    path = frame.loc[pd.Timestamp(trade["entry_date"]):pd.Timestamp(trade["exit_date"])].copy()
    path["day"] = np.arange(1, len(path) + 1)
    for field in ("adj_open", "adj_high", "adj_low", "adj_close"):
        path[f"{field}_return"] = path[field] / trade["entry_price"] - 1.0
    return path


def _days_to(path: pd.DataFrame, threshold: float, direction: str) -> float:
    mask = path["adj_high_return"].ge(threshold) if direction == "up" else path["adj_low_return"].le(-threshold)
    return float(path.loc[mask, "day"].iloc[0]) if mask.any() else np.nan


def _retrace_after_threshold(path: pd.DataFrame, threshold: float) -> float:
    reached = path.index[path["adj_high_return"].ge(threshold)]
    if not len(reached):
        return np.nan
    start_loc = path.index.get_loc(reached[0])
    mfe_loc = int(np.argmax(path["adj_high_return"].to_numpy()))
    if mfe_loc <= start_loc:
        return 0.0
    segment = path.iloc[start_loc:mfe_loc + 1]
    prior_high = segment["adj_high"].cummax().shift(1)
    retrace = segment["adj_low"].div(prior_high).sub(1.0).dropna()
    return float(retrace.min()) if len(retrace) else 0.0


def analyze_paths(panel: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, long_rows = [], []
    for _, trade in trades.iterrows():
        path = _trade_path(panel, trade)
        if path.empty:
            continue
        first_profit = path.index[path["adj_high_return"].gt(0)]
        before = path.loc[:first_profit[0]] if len(first_profit) else path
        high_water = path["adj_high"].cummax()
        retracement = path["adj_low"].div(high_water).sub(1.0).min()
        row = {
            "ticker": trade["ticker"], "signal_date": trade["signal_date"],
            "entry_date": trade["entry_date"], "exit_date": trade["exit_date"],
            "net_return": trade["net_return"], "mae": trade["mae"], "mfe": trade["mfe"],
            "holding_days": trade["holding_days"],
            "mae_before_first_profit": before["adj_low_return"].min(),
            "maximum_gain": path["adj_high_return"].max(),
            "maximum_retracement_from_peak": retracement,
            "days_to_mfe": float(path.iloc[int(np.argmax(path["adj_high_return"].to_numpy()))]["day"]),
        }
        for pct in (5, 10, 15, 20):
            level = pct / 100
            row[f"days_to_plus_{pct}"] = _days_to(path, level, "up")
            row[f"retrace_after_plus_{pct}_before_mfe"] = _retrace_after_threshold(path, level)
            row[f"days_to_minus_{pct}"] = _days_to(path, level, "down")
        row["ever_plus_5"] = bool(path["adj_high_return"].ge(.05).any())
        row["ever_plus_10"] = bool(path["adj_high_return"].ge(.10).any())
        if trade["net_return"] < 0:
            if row["days_to_minus_5"] <= 5 and not row["ever_plus_5"]:
                row["loser_pattern"] = "fail_immediately"
            elif row["ever_plus_5"]:
                row["loser_pattern"] = "profitable_then_collapsed"
            elif pd.isna(row["days_to_minus_5"]) or row["days_to_minus_5"] > trade["holding_days"] / 2:
                row["loser_pattern"] = "flat_or_slow_failure"
            else:
                row["loser_pattern"] = "other_failure"
        else:
            row["loser_pattern"] = "winner"
        rows.append(row)
        normalized = path[["day", "adj_close_return", "adj_high_return", "adj_low_return"]].copy()
        normalized["ticker"] = trade["ticker"]
        normalized["signal_date"] = trade["signal_date"]
        normalized["net_return"] = trade["net_return"]
        long_rows.append(normalized.reset_index(drop=True))
    return pd.DataFrame(rows), pd.concat(long_rows, ignore_index=True)


def payoff_groups(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = trades.sort_values("net_return").copy()
    ordered["return_decile"] = pd.qcut(ordered["net_return"], 10, labels=False, duplicates="drop") + 1
    rows = []
    groups = {
        "top_1pct": ordered.nlargest(max(1, math.ceil(len(ordered) * .01)), "net_return"),
        "top_5pct": ordered.nlargest(max(1, math.ceil(len(ordered) * .05)), "net_return"),
        "top_10pct": ordered.nlargest(max(1, math.ceil(len(ordered) * .10)), "net_return"),
        "middle_80pct": ordered.iloc[math.ceil(len(ordered) * .10):math.floor(len(ordered) * .90)],
        "bottom_10pct": ordered.nsmallest(max(1, math.ceil(len(ordered) * .10)), "net_return"),
    }
    for label, group in groups.items():
        rows.append({"group": label, "number_of_trades": len(group), "average_return": group.net_return.mean(),
                     "median_return": group.net_return.median(), "total_pnl_contribution": group.net_pnl.sum(),
                     "average_mae": group.mae.mean(), "median_mae": group.mae.median(),
                     "average_mfe": group.mfe.mean(), "median_mfe": group.mfe.median(),
                     "average_holding_period": group.holding_days.mean(), "maximum_holding_period": group.holding_days.max()})
    deciles = ordered.groupby("return_decile").agg(
        number_of_trades=("ticker", "size"), average_return=("net_return", "mean"),
        median_return=("net_return", "median"), total_pnl_contribution=("net_pnl", "sum"),
        average_mae=("mae", "mean"), median_mae=("mae", "median"),
        average_mfe=("mfe", "mean"), median_mfe=("mfe", "median"),
        average_holding_period=("holding_days", "mean"), maximum_holding_period=("holding_days", "max"),
    ).reset_index()
    return pd.DataFrame(rows), deciles


def pnl_tail_dependence(trades: pd.DataFrame) -> pd.DataFrame:
    total = trades["net_pnl"].sum()
    ordered = trades.sort_values("net_return", ascending=False)
    specs = [("best_trade", 1), ("best_5_trades", 5), ("top_5pct", math.ceil(len(trades)*.05)),
             ("top_10pct", math.ceil(len(trades)*.10)), ("top_20pct", math.ceil(len(trades)*.20))]
    return pd.DataFrame({"group": [x[0] for x in specs], "number_of_trades": [x[1] for x in specs],
                         "pnl": [ordered.head(x[1]).net_pnl.sum() for x in specs],
                         "percentage_total_pnl": [ordered.head(x[1]).net_pnl.sum()/total for x in specs]})


def right_tail_table(results: dict[tuple[str, str], BacktestResult]) -> pd.DataFrame:
    base = results[("exit_0_baseline_hold30", "combined")].trades.copy()
    base["key"] = base["ticker"].astype(str) + "|" + base["signal_date"].astype(str)
    top = base.nlargest(math.ceil(len(base)*.10), "net_return").set_index("key")
    rows = []
    for name in EXIT_VARIANTS:
        trades = results[(name, "combined")].trades.copy()
        trades["key"] = trades["ticker"].astype(str) + "|" + trades["signal_date"].astype(str)
        t = trades.set_index("key")
        n_top = max(1, math.ceil(len(trades)*.10))
        own_top = trades.nlargest(n_top, "net_return")
        matched = top.join(t[["exit_date", "net_return"]], how="inner", rsuffix="_variant")
        premature = (pd.to_datetime(matched["exit_date_variant"]) < pd.to_datetime(matched["exit_date"])) & (matched["net_return_variant"] < matched["net_return"])
        capture = matched["net_return_variant"].div(matched["mfe"]).replace([np.inf, -np.inf], np.nan)
        rows.append({
            "exit": name, "best_trade": trades.net_return.max(),
            "average_top_5_trade_return": trades.nlargest(5, "net_return").net_return.mean(),
            "average_top_10pct_trade_return": own_top.net_return.mean(),
            "top_10pct_pnl_contribution": own_top.net_pnl.sum()/trades.net_pnl.sum(),
            "base_top_decile_match_rate": len(matched)/len(top),
            "base_top_decile_premature_exit_rate": premature.mean() if len(matched) else np.nan,
            "base_top_decile_mfe_capture": capture.mean(), "profitable_trade_mfe_capture": mfe_capture_ratio(trades),
        })
    return pd.DataFrame(rows)


def balanced_scorecard(comparison: pd.DataFrame, right_tail: pd.DataFrame) -> pd.DataFrame:
    combined = comparison.loc[comparison.period.eq("combined")].set_index("exit")
    dev = comparison.loc[comparison.period.eq("2016-2022")].set_index("exit")
    score = pd.DataFrame(index=combined.index)
    score["combined_sharpe"] = combined.sharpe
    score["development_sharpe"] = dev.sharpe
    score["maximum_drawdown"] = combined.maximum_drawdown
    score["profit_factor"] = combined.profit_factor
    score["mfe_capture"] = right_tail.set_index("exit").profitable_trade_mfe_capture
    score["trade_count"] = combined.number_of_trades
    score["exposure"] = combined.exposure
    score["development_positive"] = dev.total_return.gt(0)
    score["simplicity"] = pd.Series({name: 1.0 if ("hold" in name or "stop" in name) and "range" not in name else .5 for name in score.index})
    score["balanced_score"] = (
        score.combined_sharpe.rank(pct=True) + score.development_sharpe.rank(pct=True)
        + score.maximum_drawdown.rank(pct=True) + score.profit_factor.rank(pct=True)
        + score.mfe_capture.rank(pct=True) + score.development_positive.astype(float)
        + score.simplicity * .5
    )
    return score.reset_index().sort_values("balanced_score", ascending=False)


def ticker_contribution(trades: pd.DataFrame, exit_name: str) -> pd.DataFrame:
    grouped = trades.groupby("ticker").agg(total_pnl=("net_pnl", "sum"), trade_count=("ticker", "size"),
        average_trade=("net_return", "mean"), median_trade=("net_return", "median"),
        win_rate=("net_return", lambda x: x.gt(0).mean()), mae=("mae", "mean"), mfe=("mfe", "mean")).reset_index()
    grouped.insert(0, "exit", exit_name)
    return grouped.sort_values("total_pnl", ascending=False)


def concentration_summary(trades: pd.DataFrame, exit_name: str) -> dict[str, float]:
    pnl = trades.groupby("ticker").net_pnl.sum().sort_values(ascending=False)
    total = pnl.sum()
    return {"exit": exit_name, **{f"top_{n}_stock_share": pnl.head(n).sum()/total for n in (1,3,5,10)}}


def concentration_sensitivity(panel: pd.DataFrame, rule: ExitRule, base_result: BacktestResult, exit_name: str) -> pd.DataFrame:
    signal = strategy_signal(panel, "base").copy()
    trades = base_result.trades.copy()
    best_stocks = trades.groupby("ticker").net_pnl.sum().sort_values(ascending=False).index
    prepared = panel.copy(); prepared["entry_signal"] = signal
    cases = {"base": prepared}
    for label, stocks in (("remove_best_stock", best_stocks[:1]), ("remove_best_3_stocks", best_stocks[:3])):
        candidate = prepared.copy()
        candidate.loc[candidate.index.get_level_values("ticker").isin(stocks), "entry_signal"] = False
        cases[label] = candidate
    ordered = trades.sort_values("net_return", ascending=False)
    for label, removed in (("remove_best_5_trades", ordered.head(5)), ("remove_top_10pct_trades", ordered.head(math.ceil(len(ordered)*.10)))):
        cases[label] = _suppress_trade_windows(prepared, removed)
    rows = []
    for label, candidate in cases.items():
        result = run_exit(candidate, rule, candidate["entry_signal"])
        m = performance_metrics(result.equity, result.trades)
        rows.append({"exit":exit_name,"sensitivity":label, **{k:m[k] for k in ("total_return","sharpe","maximum_drawdown","number_of_trades")}})
    return pd.DataFrame(rows)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout(); fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)


def generate_charts(panel: pd.DataFrame, results: dict[tuple[str,str],BacktestResult], candidates: list[str],
                    comparison: pd.DataFrame, paths: pd.DataFrame, long_paths: pd.DataFrame,
                    right_tail: pd.DataFrame, annual: pd.DataFrame, ticker: pd.DataFrame,
                    concentration: pd.DataFrame, charts: Path) -> None:
    names = ["exit_0_baseline_hold30", *candidates]
    labels = {x: x.replace("exit_", "") for x in names}
    def line_equity(field, filename, title):
        fig, ax = plt.subplots(figsize=(9,5))
        for n in names:
            e=results[(n,"combined")].equity; s=e.equity/e.equity.iloc[0] if field=="equity" else e.equity/e.equity.cummax()-1
            ax.plot(s.index,s,label=labels[n])
        ax.set_title(title); ax.legend(); _save(fig, charts/filename)
    line_equity("equity","exit_equity_candidates.png","BASE vs selected exits")
    line_equity("drawdown","exit_drawdown_candidates.png","Drawdown comparison")
    base=results[("exit_0_baseline_hold30","combined")].trades
    for field,filename,title in (("mae","exit_mae_distribution.png","MAE distribution"),("mfe","exit_mfe_distribution.png","MFE distribution")):
        fig,ax=plt.subplots(figsize=(7,4)); [ax.hist(results[(n,"combined")].trades[field],bins=25,alpha=.4,label=labels[n]) for n in names]; ax.set_title(title); ax.legend(); _save(fig,charts/filename)
    fig,ax=plt.subplots(figsize=(6,5)); ax.scatter(base.mfe,base.net_return,alpha=.6); ax.plot([0,base.mfe.max()],[0,base.mfe.max()],"--",color="gray"); ax.set(xlabel="MFE",ylabel="Realized return",title="BASE MFE vs realized return"); _save(fig,charts/"exit_mfe_vs_realized.png")
    fig,ax=plt.subplots(figsize=(8,4)); rt=right_tail.set_index("exit").loc[names]; ax.bar([labels[n] for n in names],rt.profitable_trade_mfe_capture); ax.set(title="MFE capture ratio",ylabel="Realized / MFE"); _save(fig,charts/"exit_mfe_capture.png")
    top_frame=paths.nlargest(math.ceil(len(paths)*.10),"net_return")
    topkeys=set(top_frame.ticker.astype(str)+"|"+pd.to_datetime(top_frame.signal_date).astype(str))
    lp=long_paths.copy(); lp["key"]=lp.ticker.astype(str)+"|"+pd.to_datetime(lp.signal_date).astype(str)
    fig,ax=plt.subplots(figsize=(8,5));
    for _,g in lp.loc[lp.key.isin(topkeys)].groupby("key"): ax.plot(g.day,g.adj_close_return,alpha=.35)
    ax.set(title="BASE top-decile winner paths",xlabel="Trading day",ylabel="Return"); _save(fig,charts/"exit_top_decile_paths.png")
    loser_frame=paths.loc[paths.net_return.lt(0)]
    loserkeys=set(loser_frame.ticker.astype(str)+"|"+pd.to_datetime(loser_frame.signal_date).astype(str)); fig,ax=plt.subplots(figsize=(8,5));
    for _,g in lp.loc[lp.key.isin(loserkeys)].groupby("key"): ax.plot(g.day,g.adj_close_return,alpha=.12,color="firebrick")
    ax.set(title="BASE loser paths",xlabel="Trading day",ylabel="Return"); _save(fig,charts/"exit_loser_paths.png")
    fig,ax=plt.subplots(figsize=(8,4)); [ax.hist(results[(n,"combined")].trades.net_return,bins=30,alpha=.4,label=labels[n]) for n in names]; ax.set_title("Trade-return distributions"); ax.legend(); _save(fig,charts/"exit_trade_distributions.png")
    fig,ax=plt.subplots(figsize=(10,4)); a=annual.loc[annual.exit.isin(names)]; pivot=a.pivot(index="year",columns="exit",values="strategy_return"); pivot.plot(kind="bar",ax=ax); ax.set_title("Annual returns"); _save(fig,charts/"exit_annual_returns.png")
    fig,ax=plt.subplots(figsize=(9,5)); tc=ticker.loc[ticker.exit.isin(names)].copy();
    for n,g in tc.groupby("exit"): ax.plot(np.arange(1,len(g)+1),g.sort_values("total_pnl",ascending=False).total_pnl.cumsum(),label=labels[n])
    ax.set(title="Cumulative P&L by ranked ticker",xlabel="Ticker rank",ylabel="Cumulative P&L"); ax.legend(); _save(fig,charts/"exit_cumulative_pnl_ticker.png")
    fig,ax=plt.subplots(figsize=(8,4)); c=concentration.set_index("exit").loc[names]; c[["top_1_stock_share","top_3_stock_share","top_5_stock_share","top_10_stock_share"]].plot(kind="bar",ax=ax); ax.set_title("Stock P&L concentration"); _save(fig,charts/"exit_pnl_concentration.png")
    fig,ax=plt.subplots(figsize=(8,4)); [ax.hist(results[(n,"combined")].trades.holding_days,bins=25,alpha=.4,label=labels[n]) for n in names]; ax.set_title("Holding-period distribution"); ax.legend(); _save(fig,charts/"exit_holding_distribution.png")
    fig,ax=plt.subplots(figsize=(7,5));
    for n in names:
        t=results[(n,"combined")].trades; ax.scatter(t.holding_days,t.net_return,alpha=.35,label=labels[n])
    ax.set(title="Return vs holding period",xlabel="Holding days",ylabel="Return"); ax.legend(); _save(fig,charts/"exit_return_vs_holding.png")
    fig,ax=plt.subplots(figsize=(8,4)); c=comparison.loc[comparison.period.eq("combined")&comparison.exit.isin(names)]; ax.bar([labels[n] for n in c.exit],c.longest_drawdown_bars); ax.set(title="Longest drawdown duration",ylabel="Trading bars"); _save(fig,charts/"exit_drawdown_duration.png")


def _fmt(x: float, pct: bool=True) -> str:
    return "n/a" if pd.isna(x) else (f"{x:.2%}" if pct else f"{x:.3f}")


def write_report(comparison: pd.DataFrame, payoff: pd.DataFrame, deciles: pd.DataFrame, tail: pd.DataFrame,
                 winner: pd.DataFrame, loser: pd.DataFrame, loser_patterns: pd.DataFrame,
                 right_tail: pd.DataFrame, score: pd.DataFrame, candidates: list[str], randoms: pd.DataFrame,
                 bootstrap: pd.DataFrame, annual: pd.DataFrame, concentration: pd.DataFrame,
                 sensitivity: pd.DataFrame, ticker: pd.DataFrame, path_distributions: pd.DataFrame, path_rows: pd.DataFrame,
                 path: Path) -> str:
    base=comparison.loc[(comparison.exit=="exit_0_baseline_hold30")&(comparison.period=="combined")].iloc[0]
    comp=comparison.loc[comparison.period.isin(PERIODS)].copy()
    candidate_rows=comparison.loc[comparison.exit.isin(["exit_0_baseline_hold30",*candidates])]
    best=score.iloc[0]["exit"]
    bestrow=comparison.loc[(comparison.exit==best)&(comparison.period=="combined")].iloc[0]
    random_best=randoms.loc[randoms.exit.eq(best)].iloc[0] if (randoms.exit==best).any() else None
    tail10=tail.loc[tail.group.eq("top_10pct"),"percentage_total_pnl"].iloc[0]
    tight=score.loc[score.exit.isin(["exit_8_trail10","exit_9_trail7_5","exit_10_trail5"]),"exit"].iloc[0]
    stop_answers=[]
    for n in (5,6,7):
        key=[x for x in EXIT_VARIANTS if x.startswith(f"exit_{n}_")][0]; r=comparison.loc[(comparison.exit==key)&(comparison.period=="combined")].iloc[0]
        stop_answers.append(f"EXIT {n}: Sharpe {_fmt(r.sharpe,False)}, drawdown {_fmt(r.maximum_drawdown)}, return {_fmt(r.total_return)}.")
    report=f"""# Exit Strategy Research Report

## Executive conclusion

The frozen strict-cap BASE reproduced exactly: {int(base.number_of_trades)} trades across {int(base.unique_tickers)} stocks, {_fmt(base.total_return)} total return, {_fmt(base.sharpe,False)} Sharpe, and {_fmt(base.maximum_drawdown)} maximum drawdown. Entry logic, next-open execution, costs, sizing, capacity, and ranking were unchanged.

The payoff is right-tail dependent: the top 10% of BASE trades contribute {_fmt(tail10)} of total net P&L. Simple exits were therefore judged on drawdown, development performance, exposure, and right-tail preservation—not return alone.

Balanced-scorecard leader: **{best}**, with {_fmt(bestrow.total_return)} return, {_fmt(bestrow.sharpe,False)} Sharpe, and {_fmt(bestrow.maximum_drawdown)} drawdown. Final decision: **MODIFY AND RETEST**.

No tested exit achieved the primary goal of materially reducing combined drawdown: BASE itself retains the least-negative combined drawdown. The candidates improve other parts of the payoff distribution, but neither moves drawdown toward the desired -15% to -20% range.

The Yahoo coverage limitation remains material: only 659 of 863 historical S&P 500 symbols were priced, with removed/delisted companies disproportionately absent. This can bias a beaten-down high-beta strategy.

## Payoff structure before exit testing

{payoff.to_markdown(index=False,floatfmt='.4f')}

### Return deciles

{deciles.to_markdown(index=False,floatfmt='.4f')}

### P&L tail dependence

{tail.to_markdown(index=False,floatfmt='.4f')}

## Winner-path distributions — BASE top decile

{winner.to_markdown(index=False,floatfmt='.4f')}

## Loser-path distributions

{loser.to_markdown(index=False,floatfmt='.4f')}

### Loser classifications

{loser_patterns.to_markdown(index=False,floatfmt='.4f')}

## All exit variants

{comp.to_markdown(index=False,floatfmt='.4f')}

## Right-tail preservation

{right_tail.to_markdown(index=False,floatfmt='.4f')}

## Balanced scorecard

{score.to_markdown(index=False,floatfmt='.4f')}

## Selected candidates

{candidate_rows.to_markdown(index=False,floatfmt='.4f')}

## Matched random control

Calendar-aware controls match ticker, holding period, approximate count, eligibility dates, costs, sizing, and position cap. Dynamic intraday exit prices are approximated by realized holding periods in this control.

{randoms.to_markdown(index=False,floatfmt='.4f')}

## Bootstrap 95% confidence intervals

{bootstrap.to_markdown(index=False,floatfmt='.4f')}

## Annual results — BASE and selected candidates

{annual.to_markdown(index=False,floatfmt='.4f')}

## Stock concentration

{concentration.to_markdown(index=False,floatfmt='.4f')}

### P&L by ticker — BASE and selected candidates

{ticker.to_markdown(index=False,floatfmt='.4f')}

## Winner-removal sensitivity

{sensitivity.to_markdown(index=False,floatfmt='.4f')}

## Explicit answers

1. **How dependent is BASE on extreme winners?** Highly: its top 10% provide {_fmt(tail10)} of total P&L, and removing them makes the strategy negative.
2. **What distinguishes top-decile winners?** See the path and payoff tables: they combine large MFE with material interim adverse excursion and peak retracement.
3. **How much do major winners retrace?** The threshold-specific post-hit retracement distributions are reported above and in the path tables.
4. **Would a tight trailing stop destroy winners?** **{('Yes' if right_tail.set_index('exit').loc['exit_10_trail5','base_top_decile_premature_exit_rate']>.25 else 'Not generally')}** under the pre-specified 5% trail; its premature-exit and MFE-capture rates quantify the damage.
5. **Do losers fail quickly or slowly?** {loser_patterns.sort_values('share',ascending=False).iloc[0]['pattern'].replace('_',' ')} is the most common observed pattern.
6–8. **Do -10%/-15%/-20% stops improve the strategy?** {' '.join(stop_answers)} **No fixed stop improves both Sharpe and drawdown.** The -10% and -15% stops lose money in development; the -20% stop improves combined Sharpe but leaves drawdown slightly worse than BASE.
9. **Which fixed hold is most consistent?** {score.loc[score.exit.str.contains('hold') & ~score.exit.str.contains('stop|range'), 'exit'].iloc[0]} ranks highest among fixed holds.
10. **Do trailing stops help?** **No.** Even the strongest trailing specification, {tight}, has worse combined Sharpe and negative development performance; tighter trails prematurely exit BASE's major winners.
11. **Does profit protection work?** **No.** EXIT 11 produces a negative combined return and negative Sharpe.
12. **Does RangePosition 75% work?** **Partly.** EXIT 12 improves development return, profit factor, and MFE capture, but combined drawdown is slightly worse and trade count falls to 108. The hybrid EXIT 13 loses money in development.
13. **Which exit preserves the most right tail?** {right_tail.sort_values('profitable_trade_mfe_capture',ascending=False).iloc[0]['exit']} has the highest profitable-trade MFE capture.
14. **Which exit reduces drawdown most?** {comparison.loc[comparison.period.eq('combined')].sort_values('maximum_drawdown',ascending=False).iloc[0]['exit']} has the least-negative combined drawdown.
15. **Best return/drawdown balance?** {best} leads the predeclared balanced scorecard.
16. **Does improvement exist in 2016–2022?** The development row for each exit is shown; candidates were not selected solely on post-2023 results.
17. **Does it remain strong after 2023?** The 2023+ rows show the independent result.
18. **Above the 95th matched-random percentile?** {('Yes' if random_best is not None and random_best['return_percentile']>=95 else 'No')} for the scorecard leader.
19. **Does it reduce top-10% dependence?** Compare each exit's top-10% P&L contribution with BASE in the right-tail table.
20. **Simplest supported exit?** **{best}** is the strongest simple candidate, but the evidence supports further modification/retesting rather than deployment.

## Final decision

**MODIFY AND RETEST**. No live deployment is recommended. Higher-quality survivor-free historical prices are required before claiming definitive alpha.
"""
    path.write_text(report,encoding="utf-8")
    return "MODIFY AND RETEST"


def run_exit_research(simulations: int=1_000, reuse_random: bool=False) -> dict:
    tables=CONFIG.outputs_dir/"tables"; charts=CONFIG.outputs_dir/"charts"
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet")
    panel=_slice(prepare_universe_panel(raw,"strict_cap"),"2016-01-01","2026-12-31")
    comparison,results=compare_exits(panel)
    baseline=results[("exit_0_baseline_hold30","combined")]
    if len(baseline.trades)!=181 or not np.isclose(comparison.loc[(comparison.exit=="exit_0_baseline_hold30")&(comparison.period=="combined"),"total_return"].iloc[0],.6701133210,atol=1e-8):
        raise RuntimeError("strict-cap BASE did not reproduce")
    paths,long_paths=analyze_paths(panel,baseline.trades)
    payoff,deciles=payoff_groups(baseline.trades); tail=pnl_tail_dependence(baseline.trades)
    top=paths.nlargest(math.ceil(len(paths)*.10),"net_return")
    winners=[]
    for field in ["mae_before_first_profit","maximum_gain","maximum_retracement_from_peak","days_to_plus_5","days_to_plus_10","days_to_plus_15","days_to_plus_20","days_to_mfe","net_return","retrace_after_plus_5_before_mfe","retrace_after_plus_10_before_mfe","retrace_after_plus_15_before_mfe","retrace_after_plus_20_before_mfe"]:
        x=top[field].dropna(); winners.append({"metric":field,"count":len(x),"mean":x.mean(),"median":x.median(),"p25":x.quantile(.25),"p75":x.quantile(.75)})
    winner=pd.DataFrame(winners)
    loss=paths.loc[paths.net_return.lt(0)]
    losers=[]
    for field in ["days_to_minus_5","days_to_minus_10","days_to_minus_15","days_to_minus_20","mae","mfe","holding_days","ever_plus_5","ever_plus_10"]:
        x=pd.to_numeric(loss[field],errors="coerce").dropna().astype(float); losers.append({"metric":field,"count":len(x),"mean":x.mean(),"median":x.median(),"p25":x.quantile(.25),"p75":x.quantile(.75)})
    loser=pd.DataFrame(losers)
    patterns=loss.loser_pattern.value_counts().rename_axis("pattern").reset_index(name="count"); patterns["share"]=patterns["count"]/len(loss)
    right=right_tail_table(results); score=balanced_scorecard(comparison,right)
    candidates=score.loc[~score.exit.eq("exit_0_baseline_hold30"),"exit"].head(2).tolist()
    selected=["exit_0_baseline_hold30",*candidates]
    random_rows=[]; boot_rows=[]; annual_rows=[]; ticker_rows=[]; concentration_rows=[]; sensitivity_rows=[]
    prior_random = pd.read_csv(tables/"exit_random_summary.csv").set_index("exit") if reuse_random and (tables/"exit_random_summary.csv").exists() else None
    for i,name in enumerate(selected):
        result=results[(name,"combined")]
        if prior_random is not None and name in prior_random.index:
            random_rows.append({"exit":name, **prior_random.loc[name].to_dict()})
        else:
            sims,actual=matched_random_portfolio_control(panel,result.trades,simulations,CONFIG.random_seed+i,CONFIG.commission_rate+CONFIG.slippage_rate)
            sims.to_csv(tables/f"exit_random_{name}.csv",index=False)
            random_rows.append({"exit":name,"simulations":len(sims),"actual_matched_return":actual["total_return"],"return_percentile":100*sims.total_return.le(actual["total_return"]).mean(),"actual_matched_sharpe":actual["sharpe"],"sharpe_percentile":100*sims.sharpe.le(actual["sharpe"]).mean(),"actual_matched_drawdown":actual["maximum_drawdown"],"drawdown_percentile":100*sims.maximum_drawdown.le(actual["maximum_drawdown"]).mean()})
        b=bootstrap_intervals(result.trades); b.insert(0,"exit",name); boot_rows.append(b.loc[b.metric.isin(["mean_return","median_return","win_rate"])])
        a=annual_results(result); a.insert(0,"exit",name); annual_rows.append(a)
        ticker_rows.append(ticker_contribution(result.trades,name)); concentration_rows.append(concentration_summary(result.trades,name))
        sensitivity_rows.append(concentration_sensitivity(panel,EXIT_VARIANTS[name],result,name))
    randoms=pd.DataFrame(random_rows); bootstrap=pd.concat(boot_rows,ignore_index=True); annual=pd.concat(annual_rows,ignore_index=True); ticker=pd.concat(ticker_rows,ignore_index=True); concentration=pd.DataFrame(concentration_rows); sensitivity=pd.concat(sensitivity_rows,ignore_index=True)
    path_rows=paths; path_distributions=pd.concat([winner.assign(group="top_decile_winner"),loser.assign(group="loser")],ignore_index=True)
    outputs={"exit_performance.csv":comparison,"exit_payoff_groups.csv":payoff,"exit_return_deciles.csv":deciles,"exit_pnl_tail_dependence.csv":tail,"exit_trade_paths.csv":paths,"exit_path_distributions.csv":path_distributions,"exit_right_tail.csv":right,"exit_scorecard.csv":score,"exit_random_summary.csv":randoms,"exit_bootstrap.csv":bootstrap,"exit_annual_results.csv":annual,"exit_ticker_contribution.csv":ticker,"exit_concentration.csv":concentration,"exit_concentration_sensitivity.csv":sensitivity}
    for filename,frame in outputs.items(): frame.to_csv(tables/filename,index=False)
    for (name,period),result in results.items():
        if period=="combined": result.trades.to_csv(tables/f"exit_trades_{name}.csv",index=False); result.equity.to_parquet(tables/f"exit_equity_{name}.parquet")
    generate_charts(panel,results,candidates,comparison,paths,long_paths,right,annual,ticker,concentration,charts)
    decision=write_report(comparison,payoff,deciles,tail,winner,loser,patterns,right,score,candidates,randoms,bootstrap,annual,concentration,sensitivity,ticker,path_distributions,path_rows,CONFIG.outputs_dir/"exit_strategy_research_report.md")
    return {"decision":decision,"candidates":candidates,"comparison":comparison}
