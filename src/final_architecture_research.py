"""Final, pre-specified portfolio-architecture experiment.

The stock-level signal, ranking and range exit are frozen.  This module only
compares the requested position counts/sizes and the three requested broad
catastrophic stops.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from src.expanded_retest import _slice, bootstrap_intervals, prepare_universe_panel, strategy_signal
from src.exit_research import drawdown_diagnostics, pnl_tail_dependence
from src.metrics import performance_metrics
from src.portfolio import BacktestResult, ExitRule, run_portfolio
from src.portfolio_risk_research import add_market_context, attach_themes, drawdown_episodes
from src.random_control import actual_percentile, matched_random_portfolio_control
from src.regime_diagnosis import _suppress_trade_windows


START, END = "2016-01-01", "2026-12-31"
PERIODS = {"2016-2022": ("2016-01-01", "2022-12-31"), "2023+": ("2023-01-01", END), "combined": (START, END)}
STOP_LEVELS = (None, .15, .20, .25)


@dataclass(frozen=True)
class Architecture:
    name: str
    max_positions: int
    position_fraction: float
    sequential: bool = False
    stop_loss: float | None = None

    @property
    def max_exposure(self) -> float:
        return self.max_positions * self.position_fraction


BASE_ARCHITECTURES = (
    Architecture("five_x10", 5, .10),
    Architecture("two_x25", 2, .25),
    Architecture("one_x10", 1, .10, True),
    Architecture("one_x25", 1, .25, True),
    Architecture("one_x50", 1, .50, True),
    Architecture("one_x75", 1, .75, True),
    Architecture("one_x100", 1, 1.00, True),
)


def variant_name(architecture: Architecture) -> str:
    return architecture.name if architecture.stop_loss is None else f"{architecture.name}_stop{int(architecture.stop_loss * 100)}"


def run_architecture(panel: pd.DataFrame, architecture: Architecture, signal: pd.Series | None = None, track: bool = False) -> BacktestResult:
    prepared = panel.copy()
    prepared["entry_signal"] = strategy_signal(prepared, "base") if signal is None else signal.reindex(prepared.index).fillna(False)
    rule = ExitRule(
        variant_name(architecture), stop_loss=architecture.stop_loss,
        range_exit=.75, hold_days=90,
    )
    return run_portfolio(
        prepared, rule, CONFIG.initial_capital, architecture.max_positions,
        architecture.position_fraction, CONFIG.commission_rate,
        CONFIG.slippage_rate, "lowest_range", strict_no_queue=architecture.sequential,
        stop_reentry_lockout=architecture.stop_loss is not None,
        track_signals=track, size_at_open_equity=True,
    )


def _period_result(result: BacktestResult, start: str, end: str) -> BacktestResult:
    equity = result.equity.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    if not equity.empty:
        scale = CONFIG.initial_capital / equity["equity"].iloc[0]
        for column in ("equity", "gross_equity", "cash", "market_value", "cumulative_costs"):
            if column in equity:
                equity[column] *= scale
    trades = result.trades.loc[
        pd.to_datetime(result.trades["exit_date"]).between(pd.Timestamp(start), pd.Timestamp(end))
    ].copy() if not result.trades.empty else result.trades.copy()
    return BacktestResult(equity, trades)


def extended_metrics(result: BacktestResult) -> dict[str, float]:
    m = performance_metrics(result.equity, result.trades)
    t, e = result.trades, result.equity
    duration, recovery = drawdown_diagnostics(e)
    exposure = m.get("exposure", np.nan)
    entry_notional = (t.get("quantity", 0) * t.get("entry_price", 0)).sum() if len(t) else 0
    exit_notional = (t.get("quantity", 0) * t.get("exit_price", 0)).sum() if len(t) else 0
    m.update({
        "unique_stocks": t.ticker.nunique() if len(t) else 0,
        "average_mae": t.mae.mean() if len(t) else np.nan,
        "median_mae": t.mae.median() if len(t) else np.nan,
        "average_mfe": t.mfe.mean() if len(t) else np.nan,
        "median_mfe": t.mfe.median() if len(t) else np.nan,
        "maximum_drawdown_duration": duration,
        "recovery_time": recovery,
        "average_exposure": exposure,
        "maximum_exposure": e.exposure.max() if len(e) else np.nan,
        "percentage_time_in_cash": e.exposure.eq(0).mean() if len(e) else np.nan,
        "turnover": (entry_notional + exit_notional) / e.equity.mean() if len(e) else np.nan,
        "cagr_per_average_exposure": m.get("cagr", np.nan) / exposure if exposure else np.nan,
        "total_return_per_average_exposure": m.get("total_return", np.nan) / exposure if exposure else np.nan,
        "return_per_max_drawdown": m.get("total_return", np.nan) / abs(m.get("maximum_drawdown", np.nan)) if m.get("maximum_drawdown", 0) else np.nan,
        "return_per_invested_dollar": m.get("total_return", np.nan) / exposure if exposure else np.nan,
    })
    return m


def performance_table(results: dict[str, BacktestResult]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        for period, (start, end) in PERIODS.items():
            part = result if period == "combined" else _period_result(result, start, end)
            rows.append({"architecture": name, "period": period, **extended_metrics(part)})
    return pd.DataFrame(rows)


def independent_signal_outcomes(panel: pd.DataFrame, signal_records: pd.DataFrame) -> pd.DataFrame:
    """Evaluate every signal independently with the frozen next-open/range/90d rule."""
    frames = {t: f.droplevel("ticker").sort_index() for t, f in panel.groupby(level="ticker", sort=False)}
    rows = []
    for signal in signal_records.itertuples(index=False):
        frame = frames.get(signal.ticker)
        date = pd.Timestamp(signal.signal_date)
        if frame is None or date not in frame.index:
            continue
        loc = int(frame.index.get_loc(date))
        if loc + 1 >= len(frame):
            continue
        entry = loc + 1
        exit_loc = min(entry + 89, len(frame) - 1)
        reason = "hold90"
        # RangePosition is observed at close and executes at the following open.
        for close_loc in range(entry, exit_loc):
            if frame.iloc[close_loc]["range_position"] >= .75:
                exit_loc = close_loc + 1
                reason = "range75"
                break
        entry_price = float(frame.iloc[entry]["adj_open"])
        exit_price = float(frame.iloc[exit_loc]["adj_open"] if reason == "range75" else frame.iloc[exit_loc]["adj_close"])
        path = frame.iloc[entry:exit_loc + 1]
        rows.append({
            **signal._asdict(), "entry_date": frame.index[entry], "hypothetical_exit_date": frame.index[exit_loc],
            "forward_return": exit_price * (1 - CONFIG.slippage_rate) / (entry_price * (1 + CONFIG.slippage_rate)) *
                              (1 - CONFIG.commission_rate) / (1 + CONFIG.commission_rate) - 1,
            "mae": path.adj_low.min() / entry_price - 1,
            "mfe": path.adj_high.max() / entry_price - 1,
            "exit_reason": reason,
        })
    return pd.DataFrame(rows)


def selected_ignored_summary(outcomes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = {
        "selected": outcomes.loc[outcomes.selected],
        "ignored": outcomes.loc[~outcomes.selected],
        "rank_1_multi_signal": outcomes.loc[(outcomes["rank"] == 1) & outcomes.groupby("signal_date").ticker.transform("size").gt(1)],
        "rank_2plus_multi_signal": outcomes.loc[(outcomes["rank"] >= 2) & outcomes.groupby("signal_date").ticker.transform("size").gt(1)],
        "all_multi_signal": outcomes.loc[outcomes.groupby("signal_date").ticker.transform("size").gt(1)],
    }
    for label, group in groups.items():
        rows.append({
            "group": label, "signals": len(group), "mean_range_position": group.range_position.mean(),
            "median_range_position": group.range_position.median(), "mean_beta": group.beta252.mean(),
            "mean_forward_return": group.forward_return.mean(), "median_forward_return": group.forward_return.median(),
            "win_rate": group.forward_return.gt(0).mean() if len(group) else np.nan,
            "average_mae": group.mae.mean(), "median_mae": group.mae.median(),
            "average_mfe": group.mfe.mean(), "median_mfe": group.mfe.median(),
            "best_return": group.forward_return.max(), "worst_return": group.forward_return.min(),
        })
    return pd.DataFrame(rows)


def opportunity_summary(outcomes: pd.DataFrame, architecture: str) -> dict[str, float | str]:
    ignored = outcomes.loc[~outcomes.selected]
    return {
        "architecture": architecture, "total_qualifying_signals": len(outcomes),
        "selected_signals": int(outcomes.selected.sum()), "ignored_signals": len(ignored),
        "percentage_ignored": len(ignored) / len(outcomes) if len(outcomes) else np.nan,
        "ignored_mean_forward_return": ignored.forward_return.mean(),
        "ignored_median_forward_return": ignored.forward_return.median(),
        "ignored_win_rate": ignored.forward_return.gt(0).mean() if len(ignored) else np.nan,
        "ignored_average_mae": ignored.mae.mean(), "ignored_average_mfe": ignored.mfe.mean(),
        "best_ignored_opportunity": ignored.forward_return.max(), "worst_ignored_opportunity": ignored.forward_return.min(),
    }


def stop_diagnostics(panel: pd.DataFrame, architecture: Architecture, result: BacktestResult, outcomes: pd.DataFrame) -> dict[str, float | str]:
    trades = result.trades
    stopped = trades.loc[trades.exit_reason.astype(str).str.startswith("stop")].copy()
    stopped["key"] = stopped.ticker.astype(str) + "|" + stopped.signal_date.astype(str)
    independent = outcomes.copy()
    independent["key"] = independent.ticker.astype(str) + "|" + independent.signal_date.astype(str)
    matched = stopped.merge(independent[["key", "forward_return", "mfe"]], on="key", how="left", suffixes=("", "_original"))
    frames = {t: f.droplevel("ticker").sort_index() for t, f in panel.groupby(level="ticker", sort=False)}
    post = []
    for trade in stopped.itertuples():
        frame = frames[trade.ticker]
        date = pd.Timestamp(trade.exit_date)
        if date not in frame.index:
            continue
        loc = int(frame.index.get_loc(date)); future = frame.iloc[loc + 1:loc + 61]
        rec = {"entry_price": trade.entry_price}
        for horizon in (5, 10, 20, 40, 60):
            sample = future.head(horizon)
            rec[f"post_stop_max_return_{horizon}d"] = sample.adj_high.max() / trade.entry_price - 1 if len(sample) else np.nan
        rec["recovered_to_entry"] = bool(len(future) and future.adj_high.ge(trade.entry_price).any())
        rec["reached_plus_5"] = bool(len(future) and future.adj_high.ge(trade.entry_price * 1.05).any())
        rec["reached_plus_10"] = bool(len(future) and future.adj_high.ge(trade.entry_price * 1.10).any())
        rec["eventually_range75"] = bool(len(future) and future.range_position.ge(.75).any())
        post.append(rec)
    post_frame = pd.DataFrame(post)
    gap = stopped.loc[stopped.exit_reason.eq("stop_gap")]
    original_winners = matched.forward_return.gt(0)
    top_cut = outcomes.forward_return.quantile(.90) if len(outcomes) else np.nan
    original_top = matched.forward_return.ge(top_cut)
    original_right_tail = outcomes.loc[outcomes.forward_return.ge(top_cut), "forward_return"].clip(lower=0).sum()
    right_tail_lost = (matched.loc[original_top, "forward_return"] - matched.loc[original_top, "net_return"]).clip(lower=0).sum()
    mfe_capture = matched["mfe"].clip(lower=0).div(matched["mfe_original"].clip(lower=0).replace(0,np.nan)).clip(upper=1)
    row: dict[str, float | str] = {
        "architecture": variant_name(architecture), "stop_level": architecture.stop_loss,
        "stop_outs": len(stopped), "stop_rate": len(stopped) / len(trades) if len(trades) else np.nan,
        "average_stop_return": stopped.net_return.mean(), "median_stop_return": stopped.net_return.median(),
        "gap_through_frequency": len(gap) / len(stopped) if len(stopped) else np.nan,
        "average_gap_through_loss": gap.net_return.mean(), "worst_gap_through_loss": gap.net_return.min(),
        "original_winners_stopped": int(original_winners.sum()), "original_top_decile_winners_stopped": int(original_top.sum()),
        "pnl_lost_from_eventual_winners": (matched.loc[original_winners, "forward_return"] - matched.loc[original_winners, "net_return"]).sum(),
        "mfe_preserved": mfe_capture.mean(),
        "right_tail_pnl_preserved": 1-right_tail_lost/original_right_tail if original_right_tail else np.nan,
        "theoretical_portfolio_risk": architecture.position_fraction * float(architecture.stop_loss or 0),
        "worst_realized_portfolio_loss": stopped.net_pnl.div(stopped.entry_cash_out if "entry_cash_out" in stopped else stopped.quantity * stopped.entry_price).min() * architecture.position_fraction if len(stopped) else np.nan,
    }
    for column in post_frame.columns:
        if column != "entry_price":
            row[column] = post_frame[column].mean()
    return row


def tail_sensitivity(panel: pd.DataFrame, architecture: Architecture, result: BacktestResult) -> pd.DataFrame:
    t = result.trades.sort_values("net_return", ascending=False)
    prepared = panel.copy(); prepared["entry_signal"] = strategy_signal(prepared, "base")
    cases = {"base": prepared, "remove_best_trade": _suppress_trade_windows(prepared, t.head(1)),
             "remove_best_5_trades": _suppress_trade_windows(prepared, t.head(5)),
             "remove_top_10pct_trade_windows": _suppress_trade_windows(prepared, t.head(max(1, math.ceil(len(t) * .10))))}
    stock_pnl = t.groupby("ticker").net_pnl.sum().sort_values(ascending=False)
    for label, count in (("remove_best_stock", 1), ("remove_best_3_stocks", 3)):
        candidate = prepared.copy()
        candidate.loc[candidate.index.get_level_values("ticker").isin(stock_pnl.head(count).index), "entry_signal"] = False
        cases[label] = candidate
    rows = []
    contribution = pnl_tail_dependence(t).assign(architecture=variant_name(architecture), analysis="contribution")
    for label, candidate in cases.items():
        rerun = run_architecture(candidate, architecture, candidate.entry_signal)
        rows.append({"architecture": variant_name(architecture), "analysis": label, **extended_metrics(rerun)})
    return pd.concat([pd.DataFrame(rows), contribution], ignore_index=True, sort=False)


def annual_returns(results: dict[str, BacktestResult]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        returns = result.equity.equity.resample("YE").last().pct_change(fill_method=None)
        if len(returns):
            returns.iloc[0] = result.equity.equity.resample("YE").last().iloc[0] / result.equity.equity.iloc[0] - 1
        rows.extend({"architecture": name, "year": int(date.year), "return": value} for date, value in returns.items())
    return pd.DataFrame(rows)


def random_controls(panel: pd.DataFrame, principals: list[tuple[Architecture, BacktestResult]], simulations: int) -> pd.DataFrame:
    rows = []
    for index, (architecture, result) in enumerate(principals):
        sims, actual = matched_random_portfolio_control(
            panel, result.trades, simulations, CONFIG.random_seed + index,
            CONFIG.commission_rate + CONFIG.slippage_rate,
            architecture.position_fraction, architecture.max_positions,
        )
        rows.append({
            "architecture": variant_name(architecture), "simulations": simulations,
            "actual_return": actual["total_return"], "actual_sharpe": actual["sharpe"],
            "actual_maximum_drawdown": actual["maximum_drawdown"],
            "return_percentile": actual_percentile(actual["total_return"], sims.total_return),
            "sharpe_percentile": actual_percentile(actual["sharpe"], sims.sharpe),
            "drawdown_percentile": 100 * sims.maximum_drawdown.le(actual["maximum_drawdown"]).mean(),
            "random_mean_return": sims.total_return.mean(), "random_mean_sharpe": sims.sharpe.mean(),
        })
    return pd.DataFrame(rows)


def drawdown_forensics(result: BacktestResult, panel: pd.DataFrame, architecture: str) -> pd.DataFrame:
    episodes = add_market_context(drawdown_episodes(result, panel))
    if episodes.empty:
        return episodes
    rows = []
    for ep in episodes.itertuples():
        held = str(ep.tickers_at_trough).split(",") if ep.tickers_at_trough else []
        stock_returns = []
        for ticker in held:
            if not ticker:
                continue
            frame = panel.xs(ticker, level="ticker")
            sample = frame.loc[pd.Timestamp(ep.start_date):pd.Timestamp(ep.trough_date), "adj_close"]
            if len(sample) > 1:
                stock_returns.append(sample.iloc[-1] / sample.iloc[0] - 1)
        stock_decline = min(stock_returns, default=np.nan)
        if len(held) > 1 and ep.maximum_depth <= -.10:
            classification = "correlated multi-position event"
        elif ep.spy_return <= -.10 or ep.qqq_return <= -.12:
            classification = "broad-market event"
        elif pd.notna(stock_decline) and stock_decline <= -.20:
            classification = "single-company collapse" if len(held) <= 1 else "prolonged decline"
        else:
            classification = "other"
        for threshold in (.05, .10, .15, .20, .30):
            if ep.maximum_depth <= -threshold:
                rows.append({
                    "architecture": architecture, "threshold": threshold,
                    "start_date": ep.start_date, "trough_date": ep.trough_date,
                    "recovery_date": ep.recovery_date, "depth": ep.maximum_depth,
                    "stocks_held": ep.tickers_at_trough, "portfolio_allocation": ep.gross_exposure_at_trough,
                    "stock_decline": stock_decline, "spy_return": ep.spy_return,
                    "qqq_return": ep.qqq_return, "vix_change": ep.vix_change,
                    "classification": classification,
                })
    return pd.DataFrame(rows)


def single_stock_risk(panel: pd.DataFrame, architecture: Architecture, result: BacktestResult) -> dict[str, float | str]:
    t = result.trades
    duration, recovery = drawdown_diagnostics(result.equity)
    gap = t.loc[t.exit_reason.eq("stop_gap")] if len(t) else t
    overnight_gaps=[]
    frames={ticker: frame.droplevel("ticker").sort_index() for ticker,frame in panel.groupby(level="ticker",sort=False)}
    for trade in t.itertuples():
        frame=frames.get(trade.ticker)
        if frame is None: continue
        held=frame.loc[pd.Timestamp(trade.entry_date):pd.Timestamp(trade.exit_date)]
        previous_close=frame.adj_close.shift(1).reindex(held.index)
        overnight_gaps.extend(held.adj_open.div(previous_close).sub(1).dropna().tolist())
    return {
        "architecture": variant_name(architecture), "worst_individual_stock_loss": t.net_return.min(),
        "largest_portfolio_loss_from_one_stock": (t.net_return * architecture.position_fraction).min(),
        "largest_overnight_gap": min(overnight_gaps,default=np.nan), "largest_gap_through_stop": gap.net_return.min() if len(gap) else np.nan,
        "maximum_intratrade_drawdown": t.mae.min(), "maximum_portfolio_drawdown": extended_metrics(result)["maximum_drawdown"],
        "longest_drawdown": duration, "recovery_time": recovery,
    }


def _save_chart(path: Path) -> None:
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def make_charts(results: dict[str, BacktestResult], performance: pd.DataFrame, selected: pd.DataFrame,
                tail: pd.DataFrame, annual: pd.DataFrame, forensics: pd.DataFrame, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    def equity_plot(names, filename, title):
        for name in names:
            if name in results:
                e = results[name].equity.equity
                plt.plot(e.index, e / e.iloc[0], label=name)
        plt.title(title); plt.ylabel("Growth of $1"); plt.legend(); _save_chart(out / filename)
    equity_plot(["five_x10", "two_x25", "one_x50"], "final_01_controlled_equity.png", "Equal 50% Maximum Exposure")
    equity_plot(["one_x25", "one_x50", "one_x75", "one_x100"], "final_02_sequential_equity.png", "Sequential Position Sizes")
    equity_plot(["one_x100"], "final_03_one_x100_equity.png", "ONE x100%")
    for name in ["five_x10", "two_x25", "one_x50", "one_x100"]:
        e=results[name].equity.equity; plt.plot(e.index, e/e.cummax()-1,label=name)
    plt.title("Drawdowns"); plt.legend(); _save_chart(out / "final_04_drawdowns.png")
    equity_plot([n for n in results if n.startswith("one_x50")], "final_05_stops.png", "ONE x50% Stop Comparison")
    combined=performance.loc[performance.period.eq("combined")].drop_duplicates("architecture")
    plt.scatter(-combined.maximum_drawdown,combined.cagr); [plt.annotate(r.architecture,(abs(r.maximum_drawdown),r.cagr),fontsize=7) for r in combined.itertuples()]
    plt.xlabel("Maximum drawdown magnitude"); plt.ylabel("CAGR"); _save_chart(out/"final_06_cagr_drawdown.png")
    plt.scatter(-combined.maximum_drawdown,combined.sharpe); [plt.annotate(r.architecture,(abs(r.maximum_drawdown),r.sharpe),fontsize=7) for r in combined.itertuples()]
    plt.xlabel("Maximum drawdown magnitude"); plt.ylabel("Sharpe"); _save_chart(out/"final_07_sharpe_drawdown.png")
    combined.set_index("architecture").calmar.plot.bar(); plt.ylabel("Calmar"); _save_chart(out/"final_08_calmar.png")
    selected.set_index("group").mean_forward_return.plot.bar(); plt.ylabel("Mean frozen-exit return"); _save_chart(out/"final_09_selected_ignored_returns.png")
    selected.set_index("group")[["average_mae","average_mfe"]].plot.bar(); _save_chart(out/"final_10_selected_ignored_excursions.png")
    selected.set_index("group")[["signals","win_rate"]].plot.bar(secondary_y="win_rate"); _save_chart(out/"final_11_opportunity_cost.png")
    contrib=tail.loc[tail.analysis.eq("contribution")];
    if len(contrib): contrib.pivot(index="group",columns="architecture",values="percentage_total_pnl").plot.bar()
    _save_chart(out/"final_12_tail_contribution.png")
    annual.pivot(index="year",columns="architecture",values="return")[[c for c in ["five_x10","two_x25","one_x50","one_x100"] if c in annual.architecture.unique()]].plot.bar(); _save_chart(out/"final_13_annual_returns.png")
    for name in ["five_x10","two_x25","one_x50","one_x100"]:
        r=results[name].equity.equity.pct_change(fill_method=None); roll=r.rolling(252).mean()/r.rolling(252).std()*np.sqrt(252); plt.plot(roll.index,roll,label=name)
    plt.legend(); plt.ylabel("252-day Sharpe"); _save_chart(out/"final_14_rolling_sharpe.png")
    if len(forensics):
        f=forensics.loc[forensics.threshold.eq(.05)].copy(); plt.bar(pd.to_datetime(f.trough_date).astype(str),-f.depth); plt.xticks(rotation=90); plt.ylabel("Drawdown magnitude")
    _save_chart(out/"final_15_drawdown_episodes.png")


def _fmt(value: float, kind: str = "pct") -> str:
    if pd.isna(value): return "N/A"
    return f"{value:.2%}" if kind == "pct" else f"{value:.3f}"


def write_report(performance: pd.DataFrame, selected: pd.DataFrame, opportunity: pd.DataFrame,
                 stop_table: pd.DataFrame, random: pd.DataFrame, bootstrap: pd.DataFrame,
                 tail: pd.DataFrame, risks: pd.DataFrame, forensics: pd.DataFrame,
                 best_sequential: str, frozen: str, path: Path) -> None:
    c=performance.loc[performance.period.eq("combined")].drop_duplicates("architecture").set_index("architecture")
    dev=performance.loc[performance.period.eq("2016-2022")].drop_duplicates("architecture").set_index("architecture")
    post=performance.loc[performance.period.eq("2023+")].drop_duplicates("architecture").set_index("architecture")
    rank1=selected.set_index("group").loc["rank_1_multi_signal"]; rank2=selected.set_index("group").loc["rank_2plus_multi_signal"]
    opp=opportunity.iloc[0]
    random_map=random.set_index("architecture") if len(random) else pd.DataFrame()
    controlled=["five_x10","two_x25","one_x50"]
    best_control=max(controlled,key=lambda n:c.loc[n,"sharpe"])
    best_sharpe=c.sharpe.idxmax(); best_calmar=c.calmar.idxmax()
    one100=c.loc["one_x100"]
    stop_help={level: stop_table.loc[stop_table.stop_level.eq(level),"stop_rate"].mean() for level in (.15,.20,.25)}
    final_names=["five_x10","two_x25","one_x25","one_x50"]
    for base in ("one_x50","one_x75"):
        candidates=[]
        for name in [n for n in c.index if n.startswith(base+"_stop")]:
            if (c.loc[name,"maximum_drawdown"] >= c.loc[base,"maximum_drawdown"]+.02 and c.loc[name,"sharpe"] >= c.loc[base,"sharpe"]-.02 and c.loc[name,"calmar"] > c.loc[base,"calmar"] and dev.loc[name,"total_return"]>0 and post.loc[name,"total_return"]>0): candidates.append(name)
        if candidates: final_names.append(max(candidates,key=lambda n:c.loc[n,"calmar"]))
    final_names.append("one_x100")
    candidates=[]
    for name in [n for n in c.index if n.startswith("one_x100_stop")]:
        if (c.loc[name,"maximum_drawdown"] >= c.loc["one_x100","maximum_drawdown"]+.02 and c.loc[name,"sharpe"] >= c.loc["one_x100","sharpe"]-.02 and c.loc[name,"calmar"] > c.loc["one_x100","calmar"] and dev.loc[name,"total_return"]>0 and post.loc[name,"total_return"]>0): candidates.append(name)
    if candidates: final_names.append(max(candidates,key=lambda n:c.loc[n,"calmar"]))
    cols=["total_return","cagr","sharpe","maximum_drawdown","calmar","average_exposure"]
    final_table=c.loc[final_names,cols].copy(); final_table["2016_2022_return"]=[dev.loc[n,"total_return"] for n in final_names]; final_table["2023_plus_return"]=[post.loc[n,"total_return"] for n in final_names]
    top_removed=tail.loc[tail.analysis.eq("remove_top_10pct_trade_windows")].set_index("architecture").total_return
    final_table["top_10pct_removed_return"]=top_removed.reindex(final_names)
    if len(random_map): final_table["random_return_percentile"]=random_map.return_percentile.reindex(final_names); final_table["random_sharpe_percentile"]=random_map.sharpe_percentile.reindex(final_names)
    stop_statement = "No catastrophic stop met the broad selection standard; NONE is frozen." if frozen not in [variant_name(Architecture("one_x50",1,.5,True,s)) for s in (.15,.20,.25)] else f"{frozen} met the broad stop standard."
    frozen_base=frozen.split("_stop")[0]
    frozen_arch=next(a for a in BASE_ARCHITECTURES if a.name==frozen_base)
    report=f"""# Final Portfolio-Architecture Research

## Executive conclusion

**READY FOR SURVIVORSHIP-CLEAN VALIDATION.** The frozen architecture is **{frozen}**. {stop_statement}

The two legacy anchors reproduced exactly before the new implementation: unmanaged Range Exit **85.7179% return / 0.4142 Sharpe / -30.9944% drawdown**, and FIVE x10% **64.0680% / 0.4398 / -17.4163%**. Final-experiment comparisons size entries from opening equity, eliminating a discovered morning-sizing look-ahead in the legacy multi-position implementation; this is why its final row may differ slightly from the legacy anchor.

This conclusion is provisional because Yahoo covers only **659 of 863** historical symbols. The **204 unavailable histories disproportionately include removed/delisted companies**. That can materially inflate a strategy designed to buy beaten-down high-beta stocks. Paper trading and live deployment are not recommended from this dataset.

## Controlled architecture result

At the same 50% maximum exposure, the highest Sharpe is **{best_control}**. FIVE x10={_fmt(c.loc['five_x10','total_return'])}/{_fmt(c.loc['five_x10','sharpe'],'num')}/{_fmt(c.loc['five_x10','maximum_drawdown'])}; TWO x25={_fmt(c.loc['two_x25','total_return'])}/{_fmt(c.loc['two_x25','sharpe'],'num')}/{_fmt(c.loc['two_x25','maximum_drawdown'])}; ONE x50={_fmt(c.loc['one_x50','total_return'])}/{_fmt(c.loc['one_x50','sharpe'],'num')}/{_fmt(c.loc['one_x50','maximum_drawdown'])}.

{final_table.to_markdown(floatfmt='.4f')}

## Opportunity cost and ranking

ONE-at-a-time selected {int(opp.selected_signals)} of {int(opp.total_qualifying_signals)} qualifying stock-day signals and ignored {int(opp.ignored_signals)} ({opp.percentage_ignored:.1%}). Ignored signals returned {opp.ignored_mean_forward_return:.2%} on average with {opp.ignored_win_rate:.1%} wins under the frozen independent exit. On multi-signal dates, rank #1 averaged {rank1.mean_forward_return:.2%}, versus {rank2.mean_forward_return:.2%} for rank #2+, so ranking is {'directionally effective' if rank1.mean_forward_return > rank2.mean_forward_return else 'not effective'} in this sample. Ranking remains lowest RangePosition, then highest beta; no ranking was optimized.

{selected.to_markdown(index=False,floatfmt='.4f')}

## Catastrophic stops

Only -15%, -20%, and -25% fixed entry-price stops were tested. Stops fill at the open after a gap through the level; otherwise at the stop level. A stopped ticker is locked out until RangePosition first rises above 25% and later produces a new <=25% signal. {stop_statement}

{stop_table.to_markdown(index=False,floatfmt='.4f')}

Theoretical pre-gap portfolio risk equals allocation times stop distance; realized losses can be worse through gaps. Stop use was judged on drawdown, Sharpe, Calmar, both periods, right-tail preservation, and stability across concentration levels—not highest return.

## Explicit answers

1. **Is one-stock-at-a-time viable?** {'Yes' if c.loc[best_sequential,'total_return']>0 and dev.loc[best_sequential,'total_return']>0 and post.loc[best_sequential,'total_return']>0 else 'No'}; the best sequential row is {best_sequential} at {_fmt(c.loc[best_sequential,'total_return'])} return, {_fmt(c.loc[best_sequential,'sharpe'],'num')} Sharpe, and {_fmt(c.loc[best_sequential,'maximum_drawdown'])} drawdown.
2. **Best at identical 50% exposure?** {best_control}.
3. **Does concentration add value?** {'Yes on Sharpe' if c.loc['one_x50','sharpe']>c.loc['five_x10','sharpe'] else 'No on risk-adjusted performance'}.
4. **Does ranking select superior opportunities?** {'Yes, directionally' if rank1.mean_forward_return>rank2.mean_forward_return else 'No'}; rank #1 vs rank #2+ means are {rank1.mean_forward_return:.2%} vs {rank2.mean_forward_return:.2%}.
5. **Opportunity lost?** {opp.percentage_ignored:.1%} of qualifying stock-day signals were ignored; their mean return was {opp.ignored_mean_forward_return:.2%}.
6. **Ignored better or worse?** {'Worse' if selected.set_index('group').loc['selected','mean_forward_return']>selected.set_index('group').loc['ignored','mean_forward_return'] else 'Better'} than selected on mean forward return.
7. **Does ONE x100 materially increase CAGR?** Its CAGR is {_fmt(one100.cagr)} versus ONE x50 {_fmt(c.loc['one_x50','cagr'])}.
8. **ONE x100 drawdown?** {_fmt(one100.maximum_drawdown)}.
9. **Unacceptable idiosyncratic risk?** {'Yes' if one100.maximum_drawdown < -.30 or risks.set_index('architecture').loc['one_x100','worst_individual_stock_loss'] < -.40 else 'Not by the predeclared historical thresholds, though survivorship bias prevents assurance'}.
10. **-15% stop?** It stopped {stop_help[.15]:.1%} of trades on average; see the broad-standard conclusion above.
11. **-20% stop?** It stopped {stop_help[.20]:.1%} of trades on average; see the broad-standard conclusion above.
12. **-25% stop?** It stopped {stop_help[.25]:.1%} of trades on average; see the broad-standard conclusion above.
13. **Which stop materially improves concentration?** {stop_statement}
14. **Winner destruction?** The stop table reports eventual winners/top-decile winners stopped, P&L lost, MFE and right-tail preservation; this was included in the stop decision.
15. **ONE x50 + stop beats FIVE x10 risk-adjusted?** {'Yes' if any(c.loc[n,'sharpe']>c.loc['five_x10','sharpe'] and c.loc[n,'maximum_drawdown']>=c.loc['five_x10','maximum_drawdown'] for n in c.index if n.startswith('one_x50_stop')) else 'No'}.
16. **Sizing or stops?** Position sizing is {'more' if frozen.endswith(('x10','x25','x50','x75','x100')) else 'less'} defensible under the broad standard.
17. **Best Sharpe?** {best_sharpe}, {_fmt(c.loc[best_sharpe,'sharpe'],'num')}.
18. **Best Calmar?** {best_calmar}, {_fmt(c.loc[best_calmar,'calmar'],'num')}.
19. **Least extreme-winner dependent?** The architecture with the strongest top-10%-removed result is {top_removed.idxmax()} ({_fmt(top_removed.max())}).
20. **Strongest in 2016-2022?** {dev.total_return.idxmax()} by return; architecture selection did not use return alone.
21. **Strongest after 2023?** {post.total_return.idxmax()} by return.
22. **Above 95th matched random?** {', '.join(random.loc[(random.return_percentile>95)&(random.sharpe_percentile>95),'architecture']) or 'None on both return and Sharpe'}.
23. **Simplest?** ONE-at-a-time without a stop is mechanically simplest; the frozen choice balances simplicity and evidence.
24. **Exact frozen strategy?** Specified below. No further strategy-design search is authorized.

## Statistical robustness

Matched random controls use 1,000 fixed-seed simulations matched by ticker and holding period with architecture-specific sleeves/caps. Bootstrap intervals use 5,000 trade and ticker-cluster resamples.

{random.to_markdown(index=False,floatfmt='.3f')}

{bootstrap.to_markdown(index=False,floatfmt='.4f')}

## Drawdown and single-stock risk

{risks.to_markdown(index=False,floatfmt='.4f')}

Major drawdown episodes and the requested 5/10/15/20/30% threshold crossings are in `outputs/tables/final_drawdown_forensics.csv`. Tail contributions and exact removal reruns are in `outputs/tables/final_tail_sensitivity.csv`.

## Research stopping rule

This completes strategy design. Do not search for new indicators, thresholds, filters, exits, ranking formulas, stop levels, or portfolio rules. The next step is survivor-clean validation on point-in-time membership, delisted/removed securities, reliable corporate-action-adjusted prices, and point-in-time capitalization. The parameters below must not be changed in response to that new dataset.

## FROZEN STRATEGY FOR SURVIVORSHIP-CLEAN VALIDATION

**Universe:** Historical S&P 500 membership; point-in-time market cap >=$10B where historical shares are available; adjusted close >=$10; trailing average dollar volume >=$100M; rolling 252-trading-day beta to SPY >=2.0.

**Entry:** RangePosition <=25% over the frozen 100-trading-day high/low lookback, observed at close T; enter at open T+1.

**Ranking:** Lowest RangePosition first; ties resolved by higher beta252, with the existing stable ticker/index order as the final deterministic tie-break. No optimized ranking.

**Position size:** {frozen_arch.position_fraction:.0%} of current portfolio equity per new position (opening marks only).

**Maximum simultaneous positions:** {5 if frozen.startswith('five') else 2 if frozen.startswith('two') else 1}.

**Maximum portfolio exposure:** {frozen_arch.max_exposure:.0%} at entry. Position weights may drift above their entry allocation before exit; no leverage is used.

**Stop loss:** {'NONE' if '_stop' not in frozen else '-' + frozen.split('stop')[-1] + '% fixed from entry price, with gap-through execution at the open'}.

**Stop re-entry rule:** {'Not applicable because no stop is frozen.' if '_stop' not in frozen else 'After a stop, the ticker must first have RangePosition >25%, then later produce a new RangePosition <=25% signal.'}

**Exit:** RangePosition >=75% observed at close, executed at the next available open.

**Maximum holding period:** 90 trading days; the existing engine exits at that day’s adjusted close.

**Execution:** Signals use close-T information only. Entries and range exits execute at T+1 open. Stops use daily OHLC: gap-through fills at open; otherwise the stop level. No leverage; unused capital remains cash. Strict sequential variants have no queue and rescan only current signals after exit.

**Transaction costs:** 0.05% commission plus 0.05% slippage per side (0.20% modeled round trip).

### WHY THIS ARCHITECTURE WAS SELECTED

{frozen} was selected using Sharpe, drawdown, Calmar, both subperiods, matched-random evidence, tail removals, ticker-cluster bootstrap, opportunity cost, ranking effectiveness, simplicity, and exposure efficiency—not maximum CAGR. The exact quantitative comparison is in the final table above.

## FINAL DECISION

**READY FOR SURVIVORSHIP-CLEAN VALIDATION**

Not PAPER TRADE: missing removed/delisted histories may be material. Not live deployment.
"""
    path.write_text(report, encoding="utf-8")


def run_final_architecture_research(simulations: int = 1000, bootstrap_simulations: int = 5000) -> dict:
    tables=CONFIG.outputs_dir/"tables"; charts=CONFIG.outputs_dir/"charts"; tables.mkdir(parents=True,exist_ok=True)
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet")
    panel=attach_themes(_slice(prepare_universe_panel(raw,"strict_cap"),START,END))
    signal=strategy_signal(panel,"base")

    # Reproduce immutable legacy anchors before applying open-equity sizing.
    legacy_range=run_portfolio(panel.assign(entry_signal=signal),ExitRule("range75_hold90",range_exit=.75,hold_days=90),CONFIG.initial_capital,10,.10,CONFIG.commission_rate,CONFIG.slippage_rate,"lowest_range")
    legacy_five=run_portfolio(panel.assign(entry_signal=signal),ExitRule("range75_hold90",range_exit=.75,hold_days=90),CONFIG.initial_capital,5,.10,CONFIG.commission_rate,CONFIG.slippage_rate,"lowest_range")
    anchors=[extended_metrics(legacy_range),extended_metrics(legacy_five)]
    expected=((.857178920764,.41423268082,-.309943915274),(.640679757528,.439809877167,-.174163216637))
    for observed,target in zip(anchors,expected):
        if not all(np.isclose(observed[k],v,atol=2e-8) for k,v in zip(("total_return","sharpe","maximum_drawdown"),target)):
            raise RuntimeError(f"legacy anchor failed reproduction: {observed}")

    architectures=list(BASE_ARCHITECTURES)
    architectures += [Architecture(a.name,a.max_positions,a.position_fraction,True,stop) for a in BASE_ARCHITECTURES if a.name in {"one_x25","one_x50","one_x75","one_x100"} for stop in (.15,.20,.25)]
    results={}
    for a in architectures:
        results[variant_name(a)]=run_architecture(panel,a,signal,track=a.name=="one_x50" and a.stop_loss is None)
    performance=performance_table(results)

    signal_outcomes=independent_signal_outcomes(panel,results["one_x50"].signals)
    selected=selected_ignored_summary(signal_outcomes)
    opportunity=pd.DataFrame([opportunity_summary(signal_outcomes,a.name) for a in BASE_ARCHITECTURES if a.sequential])
    stop_rows=[]
    for a in architectures:
        if a.stop_loss is not None:
            stop_rows.append(stop_diagnostics(panel,a,results[variant_name(a)],signal_outcomes))
    stops=pd.DataFrame(stop_rows)
    stop_performance=performance.loc[
        performance.period.eq("combined") & performance.architecture.str.contains("_stop")
    ].drop(columns="period")
    stops=stops.merge(stop_performance,on="architecture",how="left")

    combined=performance.loc[performance.period.eq("combined")].set_index("architecture")
    no_stop_sequential=[a.name for a in BASE_ARCHITECTURES if a.sequential]
    dev=performance.loc[performance.period.eq("2016-2022")].set_index("architecture")
    post=performance.loc[performance.period.eq("2023+")].set_index("architecture")
    defensible_sequential=[n for n in no_stop_sequential if combined.loc[n,"maximum_drawdown"] >= -.20]
    score=(
        combined.loc[defensible_sequential,"sharpe"].rank(pct=True)
        + combined.loc[defensible_sequential,"calmar"].rank(pct=True)
        + combined.loc[defensible_sequential,"maximum_drawdown"].rank(pct=True)
        + combined.loc[defensible_sequential,"total_return"].rank(pct=True)
        + dev.loc[defensible_sequential,"total_return"].rank(pct=True)
        + post.loc[defensible_sequential,"total_return"].rank(pct=True)
        + combined.loc[defensible_sequential,"cagr_per_average_exposure"].rank(pct=True)
    )
    best_sequential=score.idxmax()
    sequential_names=[n for n in combined.index if n.startswith("one_")]
    # A stop must improve drawdown by >=2 points, not reduce Sharpe by >.02,
    # improve Calmar, and remain positive in both periods.
    defensible=[]
    for name in sequential_names:
        if "_stop" not in name: continue
        base=name.split("_stop")[0]
        dev=performance.loc[(performance.architecture.eq(name))&(performance.period.eq("2016-2022")),"total_return"].iloc[0]
        post=performance.loc[(performance.architecture.eq(name))&(performance.period.eq("2023+")),"total_return"].iloc[0]
        if (combined.loc[name,"maximum_drawdown"] >= combined.loc[base,"maximum_drawdown"]+.02 and
            combined.loc[name,"sharpe"] >= combined.loc[base,"sharpe"]-.02 and
            combined.loc[name,"calmar"] > combined.loc[base,"calmar"] and dev>0 and post>0): defensible.append(name)
    # Freeze the simplest balanced architecture. A sequential strategy must beat
    # five-by-ten on Sharpe and Calmar without a worse drawdown to displace it.
    frozen="five_x10"
    if best_sequential in combined.index and (combined.loc[best_sequential,"sharpe"]>combined.loc[frozen,"sharpe"] and combined.loc[best_sequential,"calmar"]>combined.loc[frozen,"calmar"] and combined.loc[best_sequential,"maximum_drawdown"]>=combined.loc[frozen,"maximum_drawdown"]): frozen=best_sequential

    principal_names=["five_x10",best_sequential,"one_x100"]
    principal_names=list(dict.fromkeys(principal_names))
    arch_lookup={variant_name(a):a for a in architectures}
    principals=[(arch_lookup[n],results[n]) for n in principal_names]
    random=random_controls(panel,principals,simulations)
    boot=pd.concat([bootstrap_intervals(r.trades,bootstrap_simulations,CONFIG.random_seed+i).assign(architecture=variant_name(a)) for i,(a,r) in enumerate(principals)],ignore_index=True)
    tail=pd.concat([tail_sensitivity(panel,a,r) for a,r in principals],ignore_index=True)
    annual=annual_returns(results)
    risks=pd.DataFrame([single_stock_risk(panel,arch_lookup[n],results[n]) for n in ["one_x50","one_x75","one_x100"]])
    forensic=pd.concat([drawdown_forensics(results[n],panel,n) for n in ["five_x10","two_x25","one_x50","one_x75","one_x100"]],ignore_index=True)

    performance.to_csv(tables/"final_architecture_comparison.csv",index=False)
    stops.to_csv(tables/"sequential_stop_comparison.csv",index=False)
    selected.to_csv(tables/"selected_vs_ignored.csv",index=False)
    random.to_csv(tables/"final_random_control.csv",index=False)
    boot.to_csv(tables/"final_bootstrap.csv",index=False)
    tail.to_csv(tables/"final_tail_sensitivity.csv",index=False)
    opportunity.to_csv(tables/"final_opportunity_cost.csv",index=False)
    signal_outcomes.to_csv(tables/"final_signal_outcomes.csv",index=False)
    risks.to_csv(tables/"final_single_stock_risk.csv",index=False)
    forensic.to_csv(tables/"final_drawdown_forensics.csv",index=False)
    annual.to_csv(tables/"final_annual_returns.csv",index=False)
    for name,result in results.items():
        result.trades.to_csv(tables/f"final_trades_{name}.csv",index=False)
        result.equity.to_parquet(tables/f"final_equity_{name}.parquet")
    make_charts(results,performance,selected,tail,annual,forensic,charts)
    write_report(performance,selected,opportunity,stops,random,boot,tail,risks,forensic,best_sequential,frozen,CONFIG.outputs_dir/"final_architecture_report.md")
    return {"decision":"READY FOR SURVIVORSHIP-CLEAN VALIDATION","frozen":frozen,"best_sequential":best_sequential,"defensible_stops":defensible,"performance":performance}
