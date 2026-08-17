"""Long-only portfolio accounting with next-open entry execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np
import pandas as pd

from src.signals import rank_signals


@dataclass(frozen=True)
class ExitRule:
    name: str
    take_profit: float | None = None
    stop_loss: float | None = None
    range_exit: float | None = None
    hold_days: int | None = None
    trail_activation: float | None = None
    trailing_stop: float | None = None
    profit_ratchet: bool = False


@dataclass(frozen=True)
class PortfolioRiskRule:
    """Optional new-entry constraints; existing positions are never force-liquidated."""
    gross_exposure_cap: float | None = None
    portfolio_beta_cap: float | None = None
    theme_cap: float | None = None
    correlation_threshold: float | None = None
    correlation_window: int = 60
    qqq_risk_off: bool = False
    circuit_breaker: bool = False


EXIT_RULES = {
    "A": ExitRule("tp10_sl10", 0.10, 0.10),
    "B": ExitRule("tp15_sl10", 0.15, 0.10),
    "C": ExitRule("tp20_sl10", 0.20, 0.10),
    "D": ExitRule("range75", range_exit=0.75),
    "E": ExitRule("hold20", hold_days=20),
    "F": ExitRule("hold30", hold_days=30),
    "G": ExitRule("hold60", hold_days=60),
    "H": ExitRule("hold90", hold_days=90),
}


@dataclass
class BacktestResult:
    equity: pd.DataFrame
    trades: pd.DataFrame
    signals: pd.DataFrame = field(default_factory=pd.DataFrame)


def _sell_value(quantity: float, raw_price: float, slippage: float, commission: float) -> tuple[float, float]:
    effective = raw_price * (1.0 - slippage)
    proceeds = quantity * effective
    fee = proceeds * commission
    return proceeds - fee, fee


def run_portfolio(
    panel: pd.DataFrame,
    exit_rule: ExitRule,
    initial_capital: float = 100_000.0,
    max_positions: int = 10,
    position_fraction: float = 0.10,
    commission: float = 0.0005,
    slippage: float = 0.0005,
    ranking: str = "lowest_range",
    risk_rule: PortfolioRiskRule | None = None,
    strict_no_queue: bool = False,
    stop_reentry_lockout: bool = False,
    track_signals: bool = False,
    size_at_open_equity: bool = False,
) -> BacktestResult:
    """Run one entry/exit combination.

    Signals recorded at close on T are considered only at T+1 open. Stops and
    targets use adjusted daily OHLC. A gap through a level fills at the open;
    if both levels occur in one candle, the stop is assumed first.
    """
    required = {
        "entry_signal", "adj_open", "adj_high", "adj_low", "adj_close",
        "range_position", "beta252", "market_cap", "low_range", "high_range",
        "sma_range", "distance_sma", "average_dollar_volume",
    }
    if missing := required - set(panel.columns):
        raise ValueError(f"backtest columns missing: {sorted(missing)}")
    data = panel.sort_index()
    daily_frames = {
        current_date: frame.droplevel("date")
        for current_date, frame in data.groupby(level="date", sort=True, observed=True)
    }
    dates = pd.Index(daily_frames.keys())
    ticker_frames = {ticker: frame.droplevel("ticker").sort_index() for ticker, frame in data.groupby(level="ticker", sort=False)}
    positions: dict[str, dict] = {}
    pending_range_exits: set[str] = set()
    cash = float(initial_capital)
    cumulative_costs = 0.0
    trades: list[dict] = []
    curve: list[dict] = []
    signal_records: list[dict] = []
    previous_date: pd.Timestamp | None = None
    entry_slots_at_previous_close = max_positions
    locked_tickers: dict[str, bool] = {}
    circuit_blocked = False
    rolling_peak = float(initial_capital)

    def trailing_correlation(candidate: str, held: list[str], asof: pd.Timestamp, window: int) -> list[float]:
        candidate_frame = ticker_frames.get(candidate)
        if candidate_frame is None:
            return []
        candidate_returns = candidate_frame.loc[:asof, "adj_close"].pct_change(fill_method=None).tail(window)
        values = []
        for ticker in held:
            held_frame = ticker_frames.get(ticker)
            if held_frame is None:
                continue
            held_returns = held_frame.loc[:asof, "adj_close"].pct_change(fill_method=None).tail(window)
            joined = pd.concat([candidate_returns, held_returns], axis=1).dropna()
            if len(joined) >= max(20, window // 2):
                values.append(float(joined.iloc[:, 0].corr(joined.iloc[:, 1])))
        return values

    def close_position(ticker: str, row: pd.Series, when: pd.Timestamp, raw_price: float, reason: str) -> None:
        nonlocal cash, cumulative_costs
        position = positions.pop(ticker)
        net_proceeds, exit_fee = _sell_value(position["quantity"], raw_price, slippage, commission)
        cash += net_proceeds
        cumulative_costs += position["quantity"] * raw_price - net_proceeds
        gross_return = raw_price / position["entry_price"] - 1.0
        net_return = net_proceeds / position["entry_cash_out"] - 1.0
        record = {k: v for k, v in position.items() if k != "entry_cash_out"}
        record.update(
            {
                "exit_date": when,
                "exit_price": raw_price,
                "exit_reason": reason,
                "gross_return": gross_return,
                "net_return": net_return,
                "holding_days": position["bars_held"],
                "mae": position["mae"],
                "mfe": position["mfe"],
                "exit_commission": exit_fee,
                "gross_pnl": position["quantity"] * (raw_price - position["entry_price"]),
                "net_pnl": net_proceeds - position["entry_cash_out"],
            }
        )
        trades.append(record)
        if stop_reentry_lockout and reason.startswith("stop"):
            locked_tickers[ticker] = False

    for current_date in dates:
        day = daily_frames[current_date]

        # Exit signals observed at yesterday's close execute at today's open.
        for ticker in list(pending_range_exits):
            if ticker in positions and ticker in day.index and pd.notna(day.loc[ticker, "adj_open"]):
                close_position(ticker, day.loc[ticker], current_date, day.loc[ticker, "adj_open"], "range75")
            pending_range_exits.discard(ticker)

        # Yesterday's entry signals execute at today's open, ranked as of signal date.
        slots_today = min(max_positions - len(positions), entry_slots_at_previous_close) if strict_no_queue else max_positions - len(positions)
        selected_today: set[str] = set()
        prior_all_signals = pd.DataFrame()
        if previous_date is not None:
            prior_all_signals = rank_signals(
                daily_frames[previous_date].loc[daily_frames[previous_date]["entry_signal"].fillna(False)], ranking
            )
        if previous_date is not None and slots_today > 0:
            prior = daily_frames[previous_date]
            candidates = prior.loc[prior["entry_signal"].fillna(False)]
            candidates = candidates.loc[~candidates.index.isin(positions)]
            candidates = rank_signals(candidates, ranking)
            if stop_reentry_lockout:
                candidates = candidates.loc[
                    [ticker not in locked_tickers or locked_tickers[ticker] for ticker in candidates.index]
                ]
            for ticker, signal_row in candidates.iterrows():
                if len(positions) >= max_positions or len(selected_today) >= slots_today:
                    break
                if ticker not in day.index:
                    continue
                entry_price = day.loc[ticker, "adj_open"]
                if not np.isfinite(entry_price) or entry_price <= 0:
                    continue
                mark_field = "adj_open" if size_at_open_equity else "adj_close"
                equity_now = cash + sum(
                    p["quantity"] * day.loc[t, mark_field]
                    for t, p in positions.items()
                    if t in day.index and pd.notna(day.loc[t, mark_field])
                )
                budget = min(equity_now * position_fraction, cash)
                risk_equity = cash + sum(
                    p["quantity"] * day.loc[t, "adj_open"]
                    for t, p in positions.items()
                    if t in day.index and pd.notna(day.loc[t, "adj_open"])
                )
                opening_value = sum(
                    p["quantity"] * day.loc[t, "adj_open"]
                    for t, p in positions.items()
                    if t in day.index and pd.notna(day.loc[t, "adj_open"])
                )
                effective_cap = risk_rule.gross_exposure_cap if risk_rule else None
                if risk_rule and risk_rule.qqq_risk_off and not bool(signal_row.get("qqq_above_sma200", False)):
                    effective_cap = min(effective_cap if effective_cap is not None else 1.0, .50)
                if risk_rule and risk_rule.circuit_breaker and circuit_blocked:
                    continue
                if effective_cap is not None and risk_equity > 0 and (opening_value + budget) / risk_equity > effective_cap + 1e-12:
                    continue
                if risk_rule and risk_rule.portfolio_beta_cap is not None and risk_equity > 0:
                    current_beta = 0.0
                    for held_ticker, held_position in positions.items():
                        if held_ticker not in day.index:
                            continue
                        held_value = held_position["quantity"] * day.loc[held_ticker, "adj_open"]
                        prior_beta = prior.loc[held_ticker, "beta252"] if held_ticker in prior.index else held_position["beta"]
                        current_beta += held_value / risk_equity * prior_beta
                    projected_beta = current_beta + budget / risk_equity * signal_row["beta252"]
                    if projected_beta > risk_rule.portfolio_beta_cap + 1e-12:
                        continue
                candidate_theme = str(signal_row.get("theme", "other"))
                if risk_rule and risk_rule.theme_cap is not None and risk_equity > 0:
                    theme_value = sum(
                        p["quantity"] * day.loc[t, "adj_open"] for t, p in positions.items()
                        if t in day.index and p.get("theme", "other") == candidate_theme
                    )
                    if (theme_value + budget) / risk_equity > risk_rule.theme_cap + 1e-12:
                        continue
                if risk_rule and risk_rule.correlation_threshold is not None and positions:
                    correlations = trailing_correlation(ticker, list(positions), previous_date, risk_rule.correlation_window)
                    required = math.ceil(len(correlations) / 2) if correlations else 0
                    if required and sum(value > risk_rule.correlation_threshold for value in correlations) >= required:
                        continue
                effective_entry = entry_price * (1.0 + slippage)
                quantity = budget / (effective_entry * (1.0 + commission))
                entry_notional = quantity * effective_entry
                entry_fee = entry_notional * commission
                entry_cash_out = entry_notional + entry_fee
                if quantity <= 0 or entry_cash_out > cash + 1e-8:
                    continue
                cash -= entry_cash_out
                cumulative_costs += entry_cash_out - quantity * entry_price
                positions[ticker] = {
                    "ticker": ticker,
                    "signal_date": previous_date,
                    "entry_date": current_date,
                    "entry_price": entry_price,
                    "beta": signal_row["beta252"],
                    "market_cap": signal_row["market_cap"],
                    "market_cap_is_proxy": bool(signal_row.get("market_cap_is_proxy", False)),
                    "low_range": signal_row["low_range"],
                    "high_range": signal_row["high_range"],
                    "range_position": signal_row["range_position"],
                    "sma100": signal_row["sma_range"],
                    "distance_sma100": signal_row["distance_sma"],
                    "average_dollar_volume": signal_row["average_dollar_volume"],
                    "theme": candidate_theme,
                    "quantity": quantity,
                    "entry_cash_out": entry_cash_out,
                    "entry_commission": entry_fee,
                    "bars_held": 0,
                    "mae": 0.0,
                    "mfe": 0.0,
                    "high_water": entry_price,
                }
                selected_today.add(ticker)
                locked_tickers.pop(ticker, None)

        if track_signals and previous_date is not None:
            held_at_signal_close = max_positions - entry_slots_at_previous_close
            for rank, (ticker, signal_row) in enumerate(prior_all_signals.iterrows(), 1):
                selected = ticker in selected_today
                if selected:
                    disposition = "selected"
                elif ticker in locked_tickers and not locked_tickers[ticker]:
                    disposition = "stop_lockout"
                elif strict_no_queue and entry_slots_at_previous_close == 0:
                    disposition = "ignored_while_full"
                elif ticker in positions:
                    disposition = "already_held"
                else:
                    disposition = "ranked_below_capacity"
                signal_records.append({
                    "signal_date": previous_date, "ticker": ticker, "rank": rank,
                    "selected": selected, "disposition": disposition,
                    "positions_at_signal_close": held_at_signal_close,
                    "range_position": signal_row["range_position"],
                    "beta252": signal_row["beta252"],
                })

        # Update excursions and apply same-day stop/target rules.
        for ticker in list(positions):
            if ticker not in day.index:
                continue
            row = day.loc[ticker]
            position = positions[ticker]
            position["bars_held"] += 1
            position["mae"] = min(position["mae"], row["adj_low"] / position["entry_price"] - 1.0)
            position["mfe"] = max(position["mfe"], row["adj_high"] / position["entry_price"] - 1.0)
            stop = position["entry_price"] * (1.0 - exit_rule.stop_loss) if exit_rule.stop_loss else None
            target = position["entry_price"] * (1.0 + exit_rule.take_profit) if exit_rule.take_profit else None
            reason = None
            raw_exit = None

            # Dynamic stops use only the prior high-water mark for the opening
            # gap check, then conservatively allow today's high to raise the
            # stop before testing today's low.
            prior_high = position["high_water"]
            dynamic_stop = stop
            if exit_rule.trailing_stop is not None and exit_rule.trail_activation is not None:
                if prior_high >= position["entry_price"] * (1.0 + exit_rule.trail_activation):
                    dynamic_stop = max(dynamic_stop or -np.inf, prior_high * (1.0 - exit_rule.trailing_stop))
            if exit_rule.profit_ratchet:
                gain = prior_high / position["entry_price"] - 1.0
                floor = None
                if gain >= .20:
                    floor = max(position["entry_price"] * 1.12, prior_high * .925)
                elif gain >= .15:
                    floor = position["entry_price"] * 1.07
                elif gain >= .10:
                    floor = position["entry_price"] * 1.03
                elif gain >= .05:
                    floor = position["entry_price"]
                if floor is not None:
                    dynamic_stop = max(dynamic_stop or -np.inf, floor)

            if dynamic_stop is not None and row["adj_open"] <= dynamic_stop:
                reason, raw_exit = "stop_gap", row["adj_open"]
            elif target is not None and row["adj_open"] >= target:
                reason, raw_exit = "target_gap", row["adj_open"]
            else:
                position["high_water"] = max(prior_high, row["adj_high"])
                if exit_rule.trailing_stop is not None and exit_rule.trail_activation is not None:
                    if position["high_water"] >= position["entry_price"] * (1.0 + exit_rule.trail_activation):
                        dynamic_stop = max(dynamic_stop or -np.inf, position["high_water"] * (1.0 - exit_rule.trailing_stop))
                if exit_rule.profit_ratchet:
                    gain = position["high_water"] / position["entry_price"] - 1.0
                    floor = None
                    if gain >= .20:
                        floor = max(position["entry_price"] * 1.12, position["high_water"] * .925)
                    elif gain >= .15:
                        floor = position["entry_price"] * 1.07
                    elif gain >= .10:
                        floor = position["entry_price"] * 1.03
                    elif gain >= .05:
                        floor = position["entry_price"]
                    if floor is not None:
                        dynamic_stop = max(dynamic_stop or -np.inf, floor)
                if dynamic_stop is not None and row["adj_low"] <= dynamic_stop and target is not None and row["adj_high"] >= target:
                    reason, raw_exit = "stop_same_bar_conservative", dynamic_stop
                elif dynamic_stop is not None and row["adj_low"] <= dynamic_stop:
                    reason = "ratchet_stop" if exit_rule.profit_ratchet else ("trailing_stop" if exit_rule.trailing_stop is not None else "stop")
                    raw_exit = dynamic_stop
                elif target is not None and row["adj_high"] >= target:
                    reason, raw_exit = "target", target
            if reason:
                close_position(ticker, row, current_date, raw_exit, reason)
            elif exit_rule.hold_days and position["bars_held"] >= exit_rule.hold_days:
                close_position(ticker, row, current_date, row["adj_close"], f"hold{exit_rule.hold_days}")

        if exit_rule.range_exit is not None:
            for ticker in positions:
                if ticker in day.index and day.loc[ticker, "range_position"] >= exit_rule.range_exit:
                    pending_range_exits.add(ticker)

        if stop_reentry_lockout:
            for ticker in list(locked_tickers):
                if ticker in day.index and day.loc[ticker, "range_position"] > .25:
                    locked_tickers[ticker] = True

        market_value = sum(
            p["quantity"] * day.loc[t, "adj_close"]
            for t, p in positions.items()
            if t in day.index and pd.notna(day.loc[t, "adj_close"])
        )
        equity = cash + market_value
        weights = {
            ticker: p["quantity"] * day.loc[ticker, "adj_close"] / equity
            for ticker, p in positions.items()
            if ticker in day.index and pd.notna(day.loc[ticker, "adj_close"]) and equity
        }
        theme_weights: dict[str, float] = {}
        portfolio_beta = 0.0
        for ticker, weight in weights.items():
            theme = positions[ticker].get("theme", "other")
            theme_weights[theme] = theme_weights.get(theme, 0.0) + weight
            current_beta = day.loc[ticker, "beta252"] if pd.notna(day.loc[ticker, "beta252"]) else positions[ticker]["beta"]
            portfolio_beta += weight * current_beta
        curve.append(
            {
                "date": current_date,
                "equity": equity,
                "gross_equity": equity + cumulative_costs,
                "cumulative_costs": cumulative_costs,
                "cash": cash,
                "market_value": market_value,
                "positions": len(positions),
                "exposure": market_value / equity if equity else 0.0,
                "portfolio_beta": portfolio_beta,
                "position_tickers": tuple(weights),
                "position_weights": weights,
                "theme_weights": theme_weights,
                "max_theme_exposure": max(theme_weights.values(), default=0.0),
                "circuit_blocked": circuit_blocked,
            }
        )
        rolling_peak = max(rolling_peak, equity)
        portfolio_drawdown = equity / rolling_peak - 1.0
        if risk_rule and risk_rule.circuit_breaker:
            if not circuit_blocked and portfolio_drawdown <= -.10:
                circuit_blocked = True
            elif circuit_blocked and portfolio_drawdown >= -.05:
                circuit_blocked = False
        previous_date = current_date
        entry_slots_at_previous_close = max_positions - len(positions)

    # Liquidate residual positions at the final available close for reporting.
    if len(dates):
        final_date = dates[-1]
        final_day = daily_frames[final_date]
        for ticker in list(positions):
            if ticker in final_day.index:
                close_position(ticker, final_day.loc[ticker], final_date, final_day.loc[ticker, "adj_close"], "end_of_test")
        if curve:
            curve[-1].update({"equity": cash, "gross_equity": cash + cumulative_costs, "cumulative_costs": cumulative_costs, "cash": cash, "market_value": 0.0, "positions": 0, "exposure": 0.0})

    equity_frame = pd.DataFrame(curve).set_index("date") if curve else pd.DataFrame()
    trades_frame = pd.DataFrame(trades)
    return BacktestResult(equity_frame, trades_frame, pd.DataFrame(signal_records))
