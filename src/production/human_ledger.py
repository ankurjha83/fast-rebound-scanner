"""Human decisions are intentionally isolated from the model portfolio."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.production.audit_log import append_csv


FIELDS=["recorded_at_utc","run_id","recommendation_date","ticker","decision","reason","intended_allocation","order_type","actual_entry_price","actual_exit_price","broker_notes"]


def record_decision(path: str | Path, **values) -> dict:
    decision=str(values.get("decision","")).upper()
    if decision not in {"TRADE","SKIP"}: raise ValueError("decision must be TRADE or SKIP")
    row={field:values.get(field,"") for field in FIELDS}; row["decision"]=decision; row["ticker"]=str(row["ticker"]).upper(); row["recorded_at_utc"]=datetime.now(timezone.utc).isoformat(); append_csv(path,[row],FIELDS); return row
