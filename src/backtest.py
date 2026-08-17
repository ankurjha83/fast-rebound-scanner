"""Orchestration helpers for the three entry and eight exit strategies."""

from __future__ import annotations

import pandas as pd

from config import CONFIG, ResearchConfig
from src.portfolio import EXIT_RULES, BacktestResult, run_portfolio
from src.signals import EntryStrategy, generate_entry_signals


def run_strategy_grid(
    panel: pd.DataFrame,
    config: ResearchConfig = CONFIG,
    rankings: tuple[str, ...] = ("lowest_range",),
) -> dict[str, BacktestResult]:
    results: dict[str, BacktestResult] = {}
    for entry in EntryStrategy:
        prepared = panel.copy()
        prepared["entry_signal"] = generate_entry_signals(prepared, entry, config.max_range_position)
        for exit_code, exit_rule in EXIT_RULES.items():
            for ranking in rankings:
                key = f"{entry.value}__{exit_code}_{exit_rule.name}__{ranking}"
                results[key] = run_portfolio(
                    prepared,
                    exit_rule,
                    config.initial_capital,
                    config.max_positions,
                    config.position_fraction,
                    config.commission_rate,
                    config.slippage_rate,
                    ranking,
                )
    return results
