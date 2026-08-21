"""Telegram formatting and safe Bot API delivery."""

from __future__ import annotations

import os
from datetime import datetime as _dt

import requests

from src.production.frozen_config import MAX_POSITIONS, POSITION_SIZE, STOP_LOSS, TAKE_PROFIT


class TelegramError(RuntimeError): pass


def format_daily_message(session, qualifying, accepted, state, notices: list[dict], data_status: str = "OK") -> str:
    try:
        day_str = _dt.strptime(session, "%Y-%m-%d").strftime("%a %Y-%m-%d")
    except Exception:
        day_str = str(session)

    lines = [f"📊 FAST REBOUND — {day_str}"]

    if data_status.startswith("DEGRADED"):
        lines.extend(["", "⚠️ DATA DEGRADED — some symbols missing, see logs."])

    # ── CLOSED TODAY ──────────────────────────────────────────────
    exits = [x for x in notices if x["type"] == "EXIT"]
    if exits:
        lines.extend(["", "CLOSED TODAY"])
        icon_map  = {"target": "✅", "target_gap": "✅", "stop": "❌", "stop_gap": "❌", "hold10": "⏱"}
        label_map = {"target": "TARGET HIT", "target_gap": "TARGET HIT (gap up)",
                     "stop": "STOP HIT", "stop_gap": "STOP HIT (gap down)", "hold10": "TIME EXIT"}
        for ev in exits:
            icon  = icon_map.get(ev["reason"], "◼")
            label = label_map.get(ev["reason"], "EXITED")
            pct   = ev["return_pct"]
            pnl   = ev.get("portfolio_pnl")
            dollar_str  = f"  (${pnl:+,.0f})" if pnl is not None else ""
            entry = ev.get("entry_price")
            price_line  = f"Entry ${entry:.2f} → Exit ${ev['price']:.2f}" if entry else f"Exit ${ev['price']:.2f}"
            days  = ev["holding_days"]
            lines += [
                "",
                f"{icon} {ev['ticker']}  {label}",
                f"   {price_line}",
                f"   Return: {pct:+.2%}{dollar_str}",
                f"   Held: {days} trading day{'s' if days != 1 else ''}",
            ]

    # ── OPEN POSITIONS ─────────────────────────────────────────────
    positions = state.get("positions", [])
    if positions:
        lines.extend(["", "OPEN POSITIONS"])
        for p in positions:
            unr_pct = p["last_close"] / p["entry_price"] - 1
            unr_usd = p["quantity"] * (p["last_close"] - p["entry_price"])
            lines += [
                "",
                f"📌 {p['ticker']}  Day {p['holding_days']}/10",
                f"   Entry ${p['entry_price']:.2f}  →  Last ${p['last_close']:.2f}",
                f"   Stop ${p['stop_price']:.2f}  |  Target ${p['target_price']:.2f}",
                f"   Unrealized: {unr_pct:+.2%}  (${unr_usd:+,.0f})",
            ]

    # ── NEW SIGNALS ────────────────────────────────────────────────
    equity = state.get("equity") or 100_000.0
    if len(accepted):
        lines.extend(["", f"NEW SIGNAL{'S' if len(accepted) > 1 else ''} — ENTERS TOMORROW OPEN"])
        for row in accepted.itertuples():
            alloc_usd = equity * POSITION_SIZE
            tgt = row.previous_close * (1 + TAKE_PROFIT)
            stp = row.previous_close * (1 + STOP_LOSS)
            lines += [
                "",
                f"🟡 {row.ticker}  Score {row.fast_rebound_score:.1f}",
                f"   Yesterday close: ${row.previous_close:.2f}",
                f"   Target ~${tgt:.2f} (+5%)  |  Stop ~${stp:.2f} (-7.5%)",
                f"   Allocation: 33.33% of equity (~${alloc_usd:,.0f})",
                f"   Status: PENDING NEXT OPEN",
                f"   Max hold: 10 trading days",
            ]
    elif len(qualifying):
        lines += [
            "",
            "NO NEW POSITION",
            f"{len(qualifying)} stock(s) qualified but all slots are filled.",
            "On watch: " + ", ".join(qualifying.ticker),
        ]
    else:
        lines += ["", "NO TRADE", "No stocks meet the frozen threshold today."]

    # ── PORTFOLIO SNAPSHOT ─────────────────────────────────────────
    open_count    = len(positions)
    pending       = state.get("pending", [])
    pending_count = len(pending)
    exposure      = (sum(p.get("quantity", 0) * p.get("last_close", p.get("entry_price", 0))
                        for p in positions) / equity) if equity else 0
    available     = max(0, MAX_POSITIONS - open_count - pending_count)
    lines += [
        "",
        "PORTFOLIO",
        f"Equity: ${equity:,.0f}",
        f"Slots:  {open_count} open  +  {pending_count} pending  +  {available} free  (of {MAX_POSITIONS})",
        f"Exposure: {exposure:.1%}  (excl. pending)",
    ]

    # ── ACTION TOMORROW MORNING ────────────────────────────────────
    actions = []
    for p in pending:
        actions.append(f"• {p['ticker']}  enters at open — note the fill price")
    for p in positions:
        actions.append(
            f"• {p['ticker']}  stop ${p['stop_price']:.2f}  |  target ${p['target_price']:.2f}"
            f"  (day {p['holding_days']}/10)"
        )
    if not actions:
        actions.append("• Nothing required — no open or pending positions")

    lines += ["", "⚡ ACTION TOMORROW MORNING"] + actions + ["", "Research before placing any real order."]
    return "\n".join(lines)


def no_new_session_message(session) -> str:
    return f"FAST REBOUND\n\nNO NEW U.S. SESSION — scanner skipped.\nLatest processed session: {session}"


def error_message(reason: str) -> str:
    return f"FAST REBOUND SCANNER ERROR\n\nNo recommendation generated.\n\nReason: {reason[:300]}"


def send_message(text: str, token: str | None = None, chat_id: str | None = None, timeout: int = 15) -> None:
    token   = token   or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise TelegramError("Telegram credentials are not configured")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=timeout,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise TelegramError("Telegram API returned an unsuccessful response")
    except requests.RequestException as exc:
        raise TelegramError(f"Telegram delivery failed: {type(exc).__name__}") from exc


def send_test_message() -> None:
    send_message("FAST REBOUND SCANNER\nTelegram integration test successful.")
