"""Yahoo Finance market-data adapter with an auditable local cache.

Yahoo is suitable for prototype research, not point-in-time production data.
The adapter isolates all provider-specific behavior behind ``PriceDataProvider``.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from config import CONFIG

LOGGER = logging.getLogger(__name__)
PRICE_COLUMNS = [
    "open", "high", "low", "close", "adj_close", "volume",
    "dividends", "stock_splits", "adj_open", "adj_high", "adj_low",
]


class CacheMode(str, Enum):
    CACHED = "cached"
    REFRESH_RECENT = "refresh_recent"
    FULL_REFRESH = "full_refresh"


@dataclass
class DataResult:
    """Data plus non-fatal provider errors and provenance notes."""

    data: pd.DataFrame
    errors: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


class PriceDataProvider(ABC):
    @abstractmethod
    def get_prices(
        self,
        tickers: Iterable[str],
        start: str | date | pd.Timestamp,
        end: str | date | pd.Timestamp | None = None,
        mode: CacheMode | str = CacheMode.REFRESH_RECENT,
    ) -> DataResult:
        """Return a MultiIndex (date, ticker) daily-price frame."""

    @abstractmethod
    def get_current_info(
        self, tickers: Iterable[str], mode: CacheMode | str = CacheMode.REFRESH_RECENT
    ) -> DataResult:
        """Return current metadata; never treat it as historical metadata."""


class YFinanceProvider(PriceDataProvider):
    """Cached Yahoo Finance implementation.

    Parameters allow dependency injection so tests remain deterministic and
    offline. Dates are normalized to timezone-naive trading-day timestamps.
    """

    def __init__(
        self,
        cache_dir: str | Path = CONFIG.cache_dir,
        refresh_overlap_days: int = 10,
        downloader: Callable[..., pd.DataFrame] | None = None,
        ticker_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.price_dir = self.cache_dir / "prices"
        self.info_dir = self.cache_dir / "info"
        self.shares_dir = self.cache_dir / "shares"
        for directory in (self.price_dir, self.info_dir, self.shares_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.refresh_overlap_days = refresh_overlap_days
        self._download = downloader or yf.download
        self._ticker = ticker_factory or yf.Ticker

    @staticmethod
    def _mode(mode: CacheMode | str) -> CacheMode:
        try:
            return CacheMode(mode)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in CacheMode)
            raise ValueError(f"Unknown cache mode {mode!r}; choose {allowed}") from exc

    @staticmethod
    def _ticker_symbol(ticker: str) -> str:
        symbol = str(ticker).strip().upper()
        if not symbol or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^" for c in symbol):
            raise ValueError(f"Invalid ticker symbol: {ticker!r}")
        return symbol

    @staticmethod
    def _timestamp(value: str | date | pd.Timestamp) -> pd.Timestamp:
        stamp = pd.Timestamp(value)
        if stamp.tz is not None:
            stamp = stamp.tz_convert(None)
        return stamp.normalize()

    @staticmethod
    def _clean_index(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        index = pd.to_datetime(result.index, errors="coerce", utc=True).tz_convert(None).normalize()
        result.index = index
        result.index.name = "date"
        return result.loc[~result.index.isna()].sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]

    @classmethod
    def _normalize_prices(cls, raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if raw is None or raw.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS, index=pd.DatetimeIndex([], name="date"))
        frame = raw.copy()
        if isinstance(frame.columns, pd.MultiIndex):
            levels = [set(map(str, frame.columns.get_level_values(i))) for i in range(frame.columns.nlevels)]
            selected = None
            for level, values in enumerate(levels):
                if ticker in values:
                    selected = frame.xs(ticker, axis=1, level=level, drop_level=True)
                    break
            frame = selected if selected is not None else frame.droplevel(-1, axis=1)
        frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
        frame = frame.rename(columns={"adjclose": "adj_close", "stock_splits": "stock_splits"})
        for column in ("open", "high", "low", "close", "adj_close", "volume"):
            if column not in frame:
                frame[column] = np.nan
        if frame["adj_close"].isna().all():
            frame["adj_close"] = frame["close"]
        for column in ("dividends", "stock_splits"):
            if column not in frame:
                frame[column] = 0.0
        factor = frame["adj_close"].div(frame["close"].replace(0, np.nan))
        for raw_column in ("open", "high", "low"):
            frame[f"adj_{raw_column}"] = frame[raw_column] * factor
        frame = cls._clean_index(frame)
        return frame.reindex(columns=PRICE_COLUMNS).apply(pd.to_numeric, errors="coerce")

    @staticmethod
    def _read_parquet(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(path)
        except Exception as exc:
            LOGGER.warning("Ignoring unreadable cache %s: %s", path, exc)
            return pd.DataFrame()

    @staticmethod
    def _merge(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        if old.empty:
            return new.sort_index()
        if new.empty:
            return old.sort_index()
        combined = pd.concat([old, new]).sort_index()
        return combined.loc[~combined.index.duplicated(keep="last")]

    def _download_one(self, ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        # Yahoo's end is exclusive, so add one day for an inclusive public API.
        raw = self._download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            auto_adjust=False,
            actions=True,
            progress=False,
            threads=False,
            timeout=20,
        )
        return self._normalize_prices(raw, ticker)

    def get_prices(
        self,
        tickers: Iterable[str],
        start: str | date | pd.Timestamp,
        end: str | date | pd.Timestamp | None = None,
        mode: CacheMode | str = CacheMode.REFRESH_RECENT,
    ) -> DataResult:
        selected_mode = self._mode(mode)
        start_at = self._timestamp(start)
        end_at = self._timestamp(end or pd.Timestamp.now(tz="UTC"))
        if start_at > end_at:
            raise ValueError("start must be on or before end")
        frames: list[pd.DataFrame] = []
        errors: dict[str, str] = {}
        notes: list[str] = []

        for requested in dict.fromkeys(tickers):
            try:
                ticker = self._ticker_symbol(requested)
            except ValueError as exc:
                errors[str(requested)] = str(exc)
                continue
            path = self.price_dir / f"{ticker}.parquet"
            cached = self._clean_index(self._read_parquet(path)) if path.exists() else pd.DataFrame()
            updated = cached
            if selected_mode is not CacheMode.CACHED:
                download_start = start_at
                if selected_mode is CacheMode.REFRESH_RECENT and not cached.empty:
                    overlap = cached.index.max() - pd.Timedelta(days=self.refresh_overlap_days)
                    download_start = max(start_at, overlap)
                try:
                    downloaded = self._download_one(ticker, download_start, end_at)
                    if downloaded.empty:
                        raise ValueError("Yahoo returned no rows")
                    if selected_mode is CacheMode.FULL_REFRESH:
                        outside = (
                            cached.loc[(cached.index < start_at) | (cached.index > end_at)]
                            if not cached.empty
                            else cached
                        )
                        updated = self._merge(outside, downloaded)
                    else:
                        updated = self._merge(cached, downloaded)
                    updated.to_parquet(path)
                except Exception as exc:
                    errors[ticker] = f"download failed: {type(exc).__name__}: {exc}"
                    LOGGER.warning("%s", errors[ticker])
                    updated = cached
            if updated.empty:
                if selected_mode is CacheMode.CACHED:
                    errors[ticker] = "no cached price data"
                continue
            sliced = updated.loc[(updated.index >= start_at) & (updated.index <= end_at)].copy()
            if sliced.empty:
                errors.setdefault(ticker, "cache has no rows in requested date range")
                continue
            sliced["ticker"] = ticker
            frames.append(sliced.reset_index().set_index(["date", "ticker"]))

        data = pd.concat(frames).sort_index() if frames else self._empty_price_result()
        if selected_mode is CacheMode.CACHED:
            notes.append("cached mode: no network requests were made")
        notes.append("Adjusted OHLC uses Yahoo Adj Close / raw Close; volume is unadjusted raw volume.")
        return DataResult(data=data, errors=errors, notes=notes)

    def get_prices_batch(
        self,
        tickers: Iterable[str],
        start: str | date | pd.Timestamp,
        end: str | date | pd.Timestamp | None = None,
        mode: CacheMode | str = CacheMode.REFRESH_RECENT,
        batch_size: int = 40,
    ) -> DataResult:
        """Batch variant for broad universes while retaining per-symbol caches.

        Dot-class tickers are translated to Yahoo's dash convention for the
        request, then restored to the point-in-time membership symbol.
        """
        selected_mode = self._mode(mode)
        start_at = self._timestamp(start)
        end_at = self._timestamp(end or pd.Timestamp.now(tz="UTC"))
        originals = [self._ticker_symbol(t) for t in dict.fromkeys(tickers)]
        errors: dict[str, str] = {}
        notes = ["Broad-universe downloads are batched; ticker-level Yahoo failures remain explicit."]
        to_download: list[str] = []
        if selected_mode is not CacheMode.CACHED:
            for ticker in originals:
                path = self.price_dir / f"{ticker}.parquet"
                cached = self._read_parquet(path)
                if selected_mode is CacheMode.FULL_REFRESH or cached.empty:
                    to_download.append(ticker)
                elif self._clean_index(cached).index.max() < end_at:
                    to_download.append(ticker)
        for offset in range(0, len(to_download), batch_size):
            batch = to_download[offset: offset + batch_size]
            yahoo_symbols = [ticker.replace(".", "-") for ticker in batch]
            batch_starts=[]
            for ticker in batch:
                cached=self._clean_index(self._read_parquet(self.price_dir/f"{ticker}.parquet"))
                batch_starts.append(max(start_at,cached.index.max()-pd.Timedelta(days=self.refresh_overlap_days)) if not cached.empty and selected_mode is CacheMode.REFRESH_RECENT else start_at)
            download_start=min(batch_starts,default=start_at)
            try:
                raw = self._download(
                    yahoo_symbols,
                    start=download_start.strftime("%Y-%m-%d"),
                    end=(end_at + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    auto_adjust=False,
                    actions=True,
                    progress=False,
                    threads=True,
                    group_by="ticker",
                    timeout=20,
                )
            except Exception as exc:
                for ticker in batch:
                    errors[ticker] = f"batch download failed: {type(exc).__name__}: {exc}"
                continue
            for ticker, yahoo_symbol in zip(batch, yahoo_symbols):
                try:
                    downloaded = self._normalize_prices(raw, yahoo_symbol)
                    if downloaded.empty or downloaded["adj_close"].notna().sum() == 0:
                        raise ValueError("Yahoo returned no usable rows")
                    path = self.price_dir / f"{ticker}.parquet"
                    cached = self._clean_index(self._read_parquet(path)) if path.exists() else pd.DataFrame()
                    if selected_mode is CacheMode.FULL_REFRESH:
                        outside = cached.loc[(cached.index < start_at) | (cached.index > end_at)] if not cached.empty else cached
                        updated = self._merge(outside, downloaded)
                    else:
                        updated = self._merge(cached, downloaded)
                    updated.to_parquet(path)
                except Exception as exc:
                    errors[ticker] = f"ticker extraction failed: {type(exc).__name__}: {exc}"
        # Reuse the cache-only reader so returned shape/provenance is identical.
        result = self.get_prices(originals, start_at, end_at, CacheMode.CACHED)
        result.errors = {**errors, **result.errors}
        result.notes.extend(notes)
        return result

    @staticmethod
    def _empty_price_result() -> pd.DataFrame:
        index = pd.MultiIndex.from_arrays(
            [pd.DatetimeIndex([], name="date"), pd.Index([], name="ticker")]
        )
        return pd.DataFrame(columns=PRICE_COLUMNS, index=index)

    def get_current_info(
        self, tickers: Iterable[str], mode: CacheMode | str = CacheMode.REFRESH_RECENT
    ) -> DataResult:
        selected_mode = self._mode(mode)
        rows: list[dict[str, Any]] = []
        errors: dict[str, str] = {}
        for requested in dict.fromkeys(tickers):
            try:
                ticker = self._ticker_symbol(requested)
            except ValueError as exc:
                errors[str(requested)] = str(exc)
                continue
            path = self.info_dir / f"{ticker}.json"
            payload: dict[str, Any] | None = None
            if selected_mode is CacheMode.CACHED and path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors[ticker] = f"metadata cache unreadable: {exc}"
            elif selected_mode is not CacheMode.CACHED:
                try:
                    info = self._ticker(ticker).get_info()
                    payload = {
                        "ticker": ticker,
                        "as_of": datetime.now(timezone.utc).isoformat(),
                        "market_cap": info.get("marketCap"),
                        "exchange": info.get("exchange"),
                        "quote_type": info.get("quoteType"),
                        "currency": info.get("currency"),
                        "shares_outstanding": info.get("sharesOutstanding"),
                        "long_name": info.get("longName"),
                    }
                    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                except Exception as exc:
                    errors[ticker] = f"metadata download failed: {type(exc).__name__}: {exc}"
                    if path.exists():
                        try:
                            payload = json.loads(path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            pass
            elif not path.exists():
                errors[ticker] = "no cached metadata"
            if payload:
                rows.append(payload)
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame = frame.set_index("ticker").sort_index()
        return DataResult(
            data=frame,
            errors=errors,
            notes=["Current metadata is snapshot data and must not be used as point-in-time history."],
        )

    def get_historical_shares(
        self,
        ticker: str,
        start: str | date | pd.Timestamp,
        end: str | date | pd.Timestamp | None = None,
        mode: CacheMode | str = CacheMode.REFRESH_RECENT,
    ) -> DataResult:
        symbol = self._ticker_symbol(ticker)
        selected_mode = self._mode(mode)
        start_at = self._timestamp(start)
        end_at = self._timestamp(end or pd.Timestamp.now(tz="UTC"))
        path = self.shares_dir / f"{symbol}.parquet"
        cached = self._clean_index(self._read_parquet(path)) if path.exists() else pd.DataFrame()
        errors: dict[str, str] = {}
        shares = cached
        if selected_mode is not CacheMode.CACHED:
            try:
                raw = self._ticker(symbol).get_shares_full(
                    start=start_at.strftime("%Y-%m-%d"),
                    end=(end_at + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                )
                if raw is None or len(raw) == 0:
                    raise ValueError("Yahoo returned no historical shares")
                downloaded = raw.to_frame("shares_outstanding") if isinstance(raw, pd.Series) else raw.copy()
                downloaded.columns = ["shares_outstanding"] if len(downloaded.columns) == 1 else downloaded.columns
                downloaded = self._clean_index(downloaded[["shares_outstanding"]])
                shares = self._merge(cached, downloaded)
                shares.to_parquet(path)
            except Exception as exc:
                errors[symbol] = f"historical shares download failed: {type(exc).__name__}: {exc}"
        if shares.empty and selected_mode is CacheMode.CACHED:
            errors[symbol] = "no cached historical shares"
        shares = shares.loc[(shares.index >= start_at) & (shares.index <= end_at)] if not shares.empty else shares
        return DataResult(
            data=shares,
            errors=errors,
            notes=[
                "Yahoo historical shares may be sparse, revised, incomplete, and not point-in-time reliable; missing values are not fabricated."
            ],
        )

    def get_historical_market_cap(
        self,
        ticker: str,
        prices: pd.DataFrame,
        start: str | date | pd.Timestamp,
        end: str | date | pd.Timestamp | None = None,
        mode: CacheMode | str = CacheMode.REFRESH_RECENT,
    ) -> DataResult:
        symbol = self._ticker_symbol(ticker)
        shares_result = self.get_historical_shares(symbol, start, end, mode)
        if prices.empty:
            return DataResult(pd.DataFrame(), shares_result.errors, shares_result.notes)
        frame = prices.copy()
        if isinstance(frame.index, pd.MultiIndex):
            frame = frame.xs(symbol, level="ticker")
        frame = self._clean_index(frame)
        shares = shares_result.data.reindex(frame.index, method="ffill")
        result = pd.DataFrame(index=frame.index)
        # Market capitalization is an as-traded-date value; raw close pairs
        # with the contemporaneous reported share count across stock splits.
        result["close"] = frame["close"]
        result["shares_outstanding"] = shares.get("shares_outstanding")
        result["historical_market_cap"] = result["close"] * result["shares_outstanding"]
        result["ticker"] = symbol
        return DataResult(result, shares_result.errors, shares_result.notes)
