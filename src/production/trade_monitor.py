"""Sequentially apply every unprocessed NYSE bar to the paper portfolio."""

from __future__ import annotations

import pandas as pd

from src.production.paper_portfolio import update_for_session
from src.production.trading_calendar import sessions_after


def process_through(state: dict, panel: pd.DataFrame, through: pd.Timestamp) -> tuple[list[dict],list[dict]]:
    events=[]; notices=[]
    for session in sessions_after(state.get("last_processed_session"),through):
        day_events,day_notices=update_for_session(state,panel,session); events.extend(day_events); notices.extend(day_notices)
    return events,notices
