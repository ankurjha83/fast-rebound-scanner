"""Refresh data and write the current watchlist screener."""

import argparse

from config import CONFIG
from data.provider import CacheMode, YFinanceProvider
from src.research import prepare_panel
from src.screener import current_screener

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-mode", choices=[m.value for m in CacheMode], default="refresh_recent")
    args = parser.parse_args()
    panel, _ = prepare_panel(YFinanceProvider(), CONFIG, CacheMode(args.cache_mode))
    stocks = panel.loc[panel.index.get_level_values("ticker").isin(CONFIG.tickers)]
    result = current_screener(stocks)
    path = CONFIG.outputs_dir / "current_screener.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    print(result.to_string(index=False))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
