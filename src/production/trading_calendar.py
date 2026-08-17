"""NYSE session helpers; all scanner decisions are session-based, not date-based."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pandas_market_calendars as mcal


NYSE = mcal.get_calendar("NYSE")


def latest_completed_session(now_utc: datetime | None=None) -> pd.Timestamp:
    now=now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None: now=now.replace(tzinfo=timezone.utc)
    now_stamp=pd.Timestamp(now).tz_convert("UTC")
    schedule=NYSE.schedule(start_date=(now_stamp-pd.Timedelta(days=14)).date(),end_date=now_stamp.date())
    completed=schedule.loc[schedule.market_close.lt(now_stamp)]
    if completed.empty: raise RuntimeError("No completed NYSE session found")
    return pd.Timestamp(completed.index[-1]).tz_localize(None).normalize()


def next_session(session: str | pd.Timestamp) -> pd.Timestamp:
    value=pd.Timestamp(session).normalize()
    schedule=NYSE.schedule(start_date=(value+pd.Timedelta(days=1)).date(),end_date=(value+pd.Timedelta(days=10)).date())
    if schedule.empty: raise RuntimeError(f"No NYSE session found after {value.date()}")
    return pd.Timestamp(schedule.index[0]).tz_localize(None).normalize()


def is_session(value: str | pd.Timestamp) -> bool:
    date=pd.Timestamp(value).normalize()
    return not NYSE.schedule(start_date=date.date(),end_date=date.date()).empty


def sessions_after(last_session: str | pd.Timestamp | None, through: str | pd.Timestamp) -> list[pd.Timestamp]:
    end=pd.Timestamp(through).normalize()
    start=(pd.Timestamp(last_session).normalize()+pd.Timedelta(days=1)) if last_session else end
    schedule=NYSE.schedule(start_date=start.date(),end_date=end.date())
    return [pd.Timestamp(x).tz_localize(None).normalize() for x in schedule.index]
