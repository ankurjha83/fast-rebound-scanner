"""Portfolio and trade performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def performance_metrics(equity: pd.DataFrame, trades: pd.DataFrame, risk_free_rate: float = 0.0) -> dict[str, float]:
    if equity.empty:
        return {"total_return": np.nan, "number_of_trades": 0}
    values = equity["equity"].astype(float)
    returns = values.pct_change(fill_method=None).dropna()
    years = max((values.index[-1] - values.index[0]).days / 365.25, 1 / 252)
    total_return = values.iloc[-1] / values.iloc[0] - 1.0
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1.0
    volatility = returns.std(ddof=1) * np.sqrt(252) if len(returns) > 1 else np.nan
    excess = returns - risk_free_rate / 252
    sharpe = excess.mean() / returns.std(ddof=1) * np.sqrt(252) if returns.std(ddof=1) else np.nan
    downside = returns.clip(upper=0)
    sortino = excess.mean() / downside.std(ddof=1) * np.sqrt(252) if downside.std(ddof=1) else np.nan
    drawdown = values / values.cummax() - 1.0
    max_drawdown = drawdown.min()
    calmar = cagr / abs(max_drawdown) if max_drawdown else np.nan
    trade_returns = trades.get("net_return", pd.Series(dtype=float)).dropna()
    winners = trade_returns[trade_returns > 0]
    losers = trade_returns[trade_returns < 0]
    gross_profit = trades.loc[trades.get("net_pnl", pd.Series(index=trades.index, dtype=float)) > 0, "net_pnl"].sum() if not trades.empty else 0
    gross_loss = -trades.loc[trades.get("net_pnl", pd.Series(index=trades.index, dtype=float)) < 0, "net_pnl"].sum() if not trades.empty else 0
    turnover = (
        (trades.get("gross_pnl", pd.Series(dtype=float)).abs().sum() + trades.get("net_pnl", pd.Series(dtype=float)).abs().sum())
        / values.mean()
        if not trades.empty else 0.0
    )
    result = {
        "total_return": total_return,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "maximum_drawdown": max_drawdown,
        "calmar": calmar,
        "number_of_trades": int(len(trades)),
        "win_rate": (trade_returns > 0).mean() if len(trade_returns) else np.nan,
        "average_trade_return": trade_returns.mean(),
        "median_trade_return": trade_returns.median(),
        "average_winner": winners.mean(),
        "average_loser": losers.mean(),
        "profit_factor": gross_profit / gross_loss if gross_loss else np.nan,
        "average_holding_period": trades.get("holding_days", pd.Series(dtype=float)).mean(),
        "best_trade": trade_returns.max(),
        "worst_trade": trade_returns.min(),
        "exposure": equity.get("exposure", pd.Series(dtype=float)).mean(),
        "turnover": turnover,
    }
    if "gross_equity" in equity:
        gross = equity["gross_equity"].astype(float)
        gross_returns = gross.pct_change(fill_method=None).dropna()
        result["gross_total_return"] = gross.iloc[-1] / gross.iloc[0] - 1.0
        result["gross_cagr"] = (gross.iloc[-1] / gross.iloc[0]) ** (1 / years) - 1.0
        result["gross_sharpe"] = (
            gross_returns.mean() / gross_returns.std(ddof=1) * np.sqrt(252)
            if gross_returns.std(ddof=1) else np.nan
        )
        result["total_costs"] = equity["cumulative_costs"].iloc[-1]
    return result


def benchmark_equity(close: pd.Series, initial_capital: float = 100_000.0) -> pd.Series:
    clean = close.dropna()
    return clean / clean.iloc[0] * initial_capital
