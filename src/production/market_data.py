"""Prospective market-data refresh with explicit coverage and failure status."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

import numpy as np
import pandas as pd

from config import CONFIG
from data.provider import CacheMode, YFinanceProvider
from src.expanded_universe import load_historical_membership
from src.indicators import add_diagnostic_indicators, add_indicators
from src.production.frozen_config import (
    MIN_AVERAGE_DOLLAR_VOLUME, MIN_BETA, MIN_HISTORY_DAYS, MIN_MARKET_CAP, MIN_PRICE,
)


@dataclass
class MarketDataBundle:
    panel: pd.DataFrame
    session: pd.Timestamp
    universe_size: int
    covered_on_session: int
    errors: dict[str,str]
    status: str


def current_universe() -> tuple[str,...]:
    membership=load_historical_membership(start="2020-01-01")
    return tuple(sorted(membership.snapshots.iloc[-1].members))


def _cached_research_bundle(session: pd.Timestamp) -> MarketDataBundle | None:
    path=CONFIG.outputs_dir/"tables"/"expanded_panel_nocap.parquet"
    if not path.exists(): return None
    raw=pd.read_parquet(path); dates=raw.index.get_level_values("date")
    if session not in dates: return None
    panel=raw.loc[dates<=session].copy(); panel["eligible"]=panel["eligible_strict"].fillna(False); panel["market_cap"]=panel["historical_market_cap"]
    benchmark=YFinanceProvider(CONFIG.cache_dir).get_prices(("SPY","QQQ"),session-pd.Timedelta(days=550),session,CacheMode.CACHED)
    if benchmark.data.empty or "QQQ" not in benchmark.data.index.get_level_values("ticker"): return None
    bench=benchmark.data.copy(); bench["eligible"]=False; bench["market_cap"]=np.nan
    panel=pd.concat([panel,bench],sort=False).sort_index()
    symbols=current_universe(); covered=panel.xs(session,level="date").index.intersection(symbols).nunique()
    return MarketDataBundle(panel,session,len(symbols),covered,{},"OK_CACHED")


def load_market_data(session: str | pd.Timestamp, mode: CacheMode | str=CacheMode.REFRESH_RECENT, retries: int=3, provider: YFinanceProvider | None=None) -> MarketDataBundle:
    session=pd.Timestamp(session).normalize(); mode=CacheMode(mode)
    if mode is CacheMode.CACHED:
        cached=_cached_research_bundle(session)
        if cached is not None: return cached
    symbols=current_universe(); requested=(*symbols,"SPY","QQQ"); provider=provider or YFinanceProvider(CONFIG.cache_dir)
    start=session-pd.Timedelta(days=550); result=None; fatal=None
    for attempt in range(retries):
        try:
            result=provider.get_prices_batch(requested,start,session,mode=mode); break
        except Exception as exc:
            fatal=exc
            if attempt+1<retries: time.sleep(2**attempt)
    if result is None: raise RuntimeError(f"Market-data refresh failed after {retries} attempts: {type(fatal).__name__}")
    prices=result.data
    if prices.empty or any(x not in prices.index.get_level_values("ticker") for x in ("SPY","QQQ")):
        raise RuntimeError("Required SPY/QQQ market data unavailable")
    panel=add_diagnostic_indicators(add_indicators(prices))
    latest=panel.xs(session,level="date",drop_level=False) if session in panel.index.get_level_values("date") else panel.iloc[0:0]
    technical=latest.loc[latest.beta252.ge(MIN_BETA)&latest.adj_close.ge(MIN_PRICE)&latest.average_dollar_volume.ge(MIN_AVERAGE_DOLLAR_VOLUME)&latest.history_days.ge(MIN_HISTORY_DAYS)]
    candidates=technical.index.get_level_values("ticker").difference(["SPY","QQQ"])
    info=provider.get_current_info(candidates,mode=mode); caps=info.data.market_cap.to_dict() if not info.data.empty and "market_cap" in info.data else {}
    panel["market_cap"]=panel.index.get_level_values("ticker").map(caps)
    panel["eligible"]=(panel.beta252.ge(MIN_BETA)&panel.adj_close.ge(MIN_PRICE)&panel.average_dollar_volume.ge(MIN_AVERAGE_DOLLAR_VOLUME)&panel.history_days.ge(MIN_HISTORY_DAYS)&panel.market_cap.ge(MIN_MARKET_CAP))
    panel.loc[panel.index.get_level_values("ticker").isin(["SPY","QQQ"]),"eligible"]=False
    covered=latest.index.get_level_values("ticker").intersection(symbols).nunique(); ratio=covered/max(1,len(symbols)); status="OK" if ratio>=.95 else "DEGRADED" if ratio>=.90 else "FAILED"
    missing=sorted(set(symbols)-set(latest.index.get_level_values("ticker"))); session_errors={ticker:f"no completed bar for data session {session.date()}" for ticker in missing}; errors={**result.errors,**info.errors,**session_errors}
    return MarketDataBundle(panel,session,len(symbols),covered,errors,status)
