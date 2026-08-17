import json

import numpy as np
import pandas as pd

from data.provider import CacheMode, YFinanceProvider


def fake_prices(*args, **kwargs):
    index = pd.date_range("2024-01-02", periods=3, freq="B", name="Date")
    return pd.DataFrame(
        {
            "Open": [50.0, 51.0, 52.0],
            "High": [52.0, 53.0, 54.0],
            "Low": [49.0, 50.0, 51.0],
            "Close": [51.0, 52.0, 53.0],
            "Adj Close": [25.5, 26.0, 26.5],
            "Volume": [1_000, 2_000, 3_000],
        },
        index=index,
    )


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def get_info(self):
        return {
            "marketCap": 12_000_000_000,
            "exchange": "NMS",
            "quoteType": "EQUITY",
            "currency": "USD",
            "sharesOutstanding": 400_000_000,
            "longName": "Example Corp",
        }

    def get_shares_full(self, start, end):
        return pd.Series(
            [400_000_000, 410_000_000],
            index=pd.to_datetime(["2024-01-02", "2024-01-04"], utc=True),
        )


def test_download_normalizes_and_adjusts_ohlc(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices, ticker_factory=FakeTicker)
    result = provider.get_prices(["test"], "2024-01-01", "2024-01-10", CacheMode.FULL_REFRESH)
    rows = result.data.xs("TEST", level="ticker")
    assert not result.errors
    assert rows.loc["2024-01-02", "adj_open"] == 25.0
    assert rows.loc["2024-01-02", "adj_high"] == 26.0
    assert rows.loc["2024-01-02", "adj_low"] == 24.5
    assert rows.loc["2024-01-02", "volume"] == 1_000


def test_cached_mode_never_downloads(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices)
    provider.get_prices(["TEST"], "2024-01-01", "2024-01-10", CacheMode.FULL_REFRESH)

    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    cached_provider = YFinanceProvider(tmp_path, downloader=forbidden)
    result = cached_provider.get_prices(["TEST"], "2024-01-01", "2024-01-10", CacheMode.CACHED)
    assert len(result.data) == 3
    assert not result.errors


def test_download_failure_falls_back_to_cache(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices)
    provider.get_prices(["TEST"], "2024-01-01", "2024-01-10", CacheMode.FULL_REFRESH)

    def broken(*args, **kwargs):
        raise ConnectionError("offline")

    fallback = YFinanceProvider(tmp_path, downloader=broken)
    result = fallback.get_prices(["TEST"], "2024-01-01", "2024-01-10")
    assert len(result.data) == 3
    assert "download failed" in result.errors["TEST"]


def test_current_info_is_timestamped_snapshot(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices, ticker_factory=FakeTicker)
    result = provider.get_current_info(["TEST"], CacheMode.FULL_REFRESH)
    assert result.data.loc["TEST", "market_cap"] == 12_000_000_000
    assert "snapshot" in result.notes[0].lower()
    payload = json.loads((tmp_path / "info" / "TEST.json").read_text())
    assert payload["as_of"]


def test_historical_market_cap_uses_reported_shares_only(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices, ticker_factory=FakeTicker)
    prices = provider.get_prices(["TEST"], "2024-01-01", "2024-01-10", CacheMode.FULL_REFRESH).data
    result = provider.get_historical_market_cap(
        "TEST", prices, "2024-01-01", "2024-01-10", CacheMode.FULL_REFRESH
    )
    assert result.data.loc["2024-01-02", "historical_market_cap"] == 51.0 * 400_000_000
    assert result.data.loc["2024-01-04", "historical_market_cap"] == 53.0 * 410_000_000
    assert "not point-in-time reliable" in result.notes[0]


def test_invalid_ticker_and_date_range_are_safe(tmp_path):
    provider = YFinanceProvider(tmp_path, downloader=fake_prices)
    result = provider.get_prices(["bad ticker"], "2024-01-01", "2024-01-10")
    assert result.data.empty
    assert "Invalid ticker" in result.errors["bad ticker"]

    try:
        provider.get_prices(["TEST"], "2024-02-01", "2024-01-01")
    except ValueError as exc:
        assert "start" in str(exc)
    else:
        raise AssertionError("invalid range should fail")
