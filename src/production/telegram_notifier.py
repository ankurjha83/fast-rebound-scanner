"""Telegram formatting and safe Bot API delivery."""

from __future__ import annotations

import os

import requests

from src.production.frozen_config import MAX_POSITIONS


class TelegramError(RuntimeError): pass


def format_daily_message(session, qualifying, accepted, state, notices: list[dict], data_status: str="OK") -> str:
    lines=["FAST REBOUND",f"Data through: {session} U.S. close"]
    if data_status.startswith("DEGRADED"): lines.extend(["","⚠️ DATA DEGRADED — missing symbols were logged."])
    exits=[x for x in notices if x["type"]=="EXIT"]
    for event in exits:
        title={"target":"TARGET HIT","target_gap":"TARGET HIT","stop":"STOP HIT","stop_gap":"STOP HIT","hold10":"TIME EXIT"}.get(event["reason"],"POSITION EXIT")
        lines.extend(["",title,event["ticker"],f"Exit: ${event['price']:.2f}",f"Return: {event['return_pct']:+.2%}",f"Held: {event['holding_days']} trading days",f"Reason: {event['reason']}"])
    if len(accepted):
        lines.extend(["",f"{len(accepted)} NEW CANDIDATE{'S' if len(accepted)!=1 else ''}"])
        for row in accepted.itertuples(): lines.extend(["",f"#{int(row.daily_rank)} {row.ticker}",f"Score: {row.fast_rebound_score:.1f}",f"P(+5%): {row.estimated_probability:.1%}",f"Close: ${row.previous_close:.2f}","Target: +5%","Stop: -7.5%","Max hold: 10 trading days","Allocation: 33.33%","Status: PENDING NEXT OPEN"])
    elif len(qualifying):
        lines.extend(["","NO NEW POSITION",f"{len(qualifying)} qualifying stock(s), but no model slot is available.","Watch only: "+", ".join(qualifying.ticker)])
    else: lines.extend(["","NO TRADE","No stocks meet the frozen threshold."])
    open_count=len(state.get("positions",[])); pending=len(state.get("pending",[])); exposure=sum(p.get("quantity",0)*p.get("last_close",p.get("entry_price",0)) for p in state.get("positions",[]))/state.get("equity",1)
    lines.extend(["","MODEL PORTFOLIO",f"Open: {open_count}/{MAX_POSITIONS}",f"Pending next open: {pending}",f"Available slots: {max(0,MAX_POSITIONS-open_count-pending)}",f"Current exposure: {exposure:.2%}","","Research candidates before placing any real order."])
    return "\n".join(lines)


def no_new_session_message(session) -> str: return f"FAST REBOUND\n\nNO NEW U.S. SESSION — scanner skipped.\nLatest processed session: {session}"


def error_message(reason: str) -> str: return f"FAST REBOUND SCANNER ERROR\n\nNo recommendation generated.\n\nReason: {reason[:300]}"


def send_message(text: str, token: str | None=None, chat_id: str | None=None, timeout: int=15) -> None:
    token=token or os.environ.get("TELEGRAM_BOT_TOKEN"); chat_id=chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id: raise TelegramError("Telegram credentials are not configured")
    try:
        response=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat_id,"text":text,"disable_web_page_preview":True},timeout=timeout)
        response.raise_for_status()
        if not response.json().get("ok"): raise TelegramError("Telegram API returned an unsuccessful response")
    except requests.RequestException as exc: raise TelegramError(f"Telegram delivery failed: {type(exc).__name__}") from exc


def send_test_message() -> None: send_message("FAST REBOUND SCANNER\nTelegram integration test successful.")

