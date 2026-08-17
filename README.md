# High-Beta Mean-Reversion Research

This repository is a research prototype for testing whether large, liquid,
high-beta U.S. stocks outperform after falling into the bottom quartile of
their trailing price range. The implementation is deliberately modular so the
Yahoo Finance data source can later be replaced by point-in-time institutional
data.

## Implemented scope

The complete proof-of-concept pipeline is implemented:

- reproducible project structure and dependency declaration;
- daily Yahoo Finance OHLCV downloads with raw and adjusted prices;
- local Parquet/JSON caching with cached, recent-refresh, and full-refresh modes;
- current metadata and historical shares-outstanding retrieval;
- historical market-cap calculation when reported shares are available;
- graceful per-ticker download failures and machine-readable quality notes;
- point-in-time rolling beta/range/SMA/liquidity indicators and eligibility;
- three entry strategies, eight exit strategies, three ranking methods;
- next-open portfolio execution, gaps, conservative same-bar brackets, costs,
  one-position-per-stock enforcement, MAE/MFE, and full trade audit fields;
- development/OOS/combined metrics, SPY/QQQ comparisons, event studies,
  range/beta buckets, regimes, 1,000 matched random controls, and a 288-cell
  development-only robustness sweep;
- all requested report tables, 15 chart types, trade history, and screener.

The broad 288-cell robustness diagnostic
uses a vectorized fixed 10%-sleeve calculation with next-open entry, one active
position per ticker, fixed holding exits, and identical costs; the primary
strategy and all eight exit comparisons use the exact daily portfolio engine.

## Setup

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Data download and cache modes

The default cache is `data/cache/` and can be changed in `config.py` or when
constructing the provider.

```python
from data.provider import CacheMode, YFinanceProvider

provider = YFinanceProvider()
result = provider.get_prices(
    ["IONQ", "ASTS", "RKLB", "COIN", "HOOD", "CVNA", "MSTR", "APP", "SPY", "QQQ"],
    start="2015-01-01",  # warm-up before the 2016 research period
    mode=CacheMode.REFRESH_RECENT,
)
prices = result.data
print(result.errors)
```

Modes:

- `cached`: never uses the network; reads whatever requested coverage exists.
- `refresh_recent`: preserves history and redownloads an overlapping recent
  window (default 10 calendar days) to capture revisions.
- `full_refresh`: redownloads the complete requested interval and replaces the
  requested cache slice.

Price files contain Yahoo's raw `open`, `high`, `low`, `close`, `adj_close`,
and `volume`, plus split/dividend-adjusted `adj_open`, `adj_high`, `adj_low`, and
`adj_close`. Adjustment uses `adj_close / close`, which supports consistent
historical signal and execution calculations while retaining the raw fields
for audit.

## Market-cap limitation

Yahoo Finance supplies current market cap, but it is not point-in-time history.
This system never silently applies today's market cap to past dates.
`get_historical_market_cap()` attempts to retrieve Yahoo's historical shares
outstanding and computes raw close × contemporaneous shares outstanding. Yahoo coverage
can be sparse, revised, or unavailable and is not institutional-quality
point-in-time fundamental data. Rows lacking reported shares remain missing.
Any later V1 experiment that elects to use current market cap as a proxy must
label the resulting look-ahead/survivorship bias explicitly.

Other V1 limitations include watchlist survivorship bias, unreliable exchange
and security-type history, and missing delisted securities. These prevent the
prototype from supporting production-capital conclusions.

## Tests

Tests are offline and inject fake Yahoo responses:

```bash
python -m pytest
```

## Run the research

```bash
python run_backtest.py --cache-mode refresh_recent --random-simulations 1000
python run_screener.py --cache-mode refresh_recent
python run_regime_diagnosis.py
python run_expanded_retest.py --simulations 1000
python run_exit_research.py --simulations 1000
python run_portfolio_risk_research.py --simulations 1000
python run_final_architecture_research.py --simulations 1000 --bootstrap-simulations 5000
python run_fast_rebound_research.py --simulations 5000
python run_fast_rebound_2024_diagnosis.py --simulations 20000
python run_capital_allocation_research.py --random-simulations 5000 --bootstrap-simulations 5000
python run_theme_concentration_diagnostic.py --random-simulations 5000
```

After a completed inference run, `--reuse-random` regenerates exit tables,
charts, and the report without repeating the matched-random simulations.

Use `--cache-mode cached` for a fully offline repeat, `refresh_recent` for the
normal incremental workflow, or `full_refresh` to replace the requested cache
interval. `--skip-robustness` is available for quick development checks; it is
not appropriate for the final research report.

## Frozen Fast Rebound production scanner

The production layer is a prospective recommendation and paper-validation
system. It does not place brokerage orders. The frozen inference parameters
live in `src/production/frozen_config.py`; production never calls the research
training functions. The model remains `fast-rebound-v1-frozen`: three maximum
positions, one-third equity per position, +5% target, -7.5% stop, ten trading
sessions, next-open entry, existing costs, and no theme rule.

The daily sequence is:

1. Determine the latest fully completed NYSE session with the official market
   calendar, including holidays and early closes.
2. Refresh cached Yahoo daily data and current market-cap metadata. Missing
   tickers are logged; inadequate coverage fails closed.
3. Update pending and open mechanical model positions from completed bars.
4. Build close-T features and apply the frozen preprocessing, coefficients,
   threshold, and rank order. Zero to three candidates may qualify.
5. Store one immutable snapshot for that data session, enqueue accepted model
   candidates as `PENDING_NEXT_OPEN`, and send the Telegram summary.
6. Append model lifecycle events and an audit record. Human decisions are
   never read by the model portfolio.

### GitHub Actions schedule and persistence

`.github/workflows/fast_rebound_daily.yml` runs daily at `00:10 UTC`, which is
`09:10 Asia/Seoul` year-round. Running every calendar day is intentional: the
NYSE calendar turns weekends, holidays, and dates with no newly completed
session into an idempotent skip. `workflow_dispatch` supports manual runs, and
the concurrency group prevents overlapping state writers.

GitHub-hosted runners are ephemeral, so non-secret files in `state/`,
`outputs/daily/`, and `outputs/prospective/` are committed back to the checked
out default branch with `[skip ci]`. The workflow has no push trigger, avoiding
an execution loop. Repository Actions settings must grant workflow
`Read and write permissions`; branch protection must permit the GitHub Actions
bot to make this state commit. A 90-day Actions artifact is also uploaded for
operational recovery, but it is not the permanent ledger.

The persistence model is append-only where history matters:

- `state/recommendation_history/`: immutable recommendation JSON snapshots;
- `state/run_history/`: immutable audit JSON records;
- `state/prospective_ledger.csv`: append-only model recommendation, entry, and
  exit events;
- `state/model_portfolio.json`: atomic current-state checkpoint;
- `state/human_decisions.csv`: independent human TRADE/SKIP records.

The session date and deterministic run ID prevent duplicate recommendations.
Ledger event IDs prevent duplicate lifecycle events after a retry.

### Required GitHub secrets and Telegram setup

Create exactly these repository Actions secrets:

- `TELEGRAM_BOT_TOKEN`: token returned by Telegram's BotFather;
- `TELEGRAM_CHAT_ID`: destination user, group, or channel ID.

The short first-run checklist is also available in `PRODUCTION_SETUP.md`.

Never put either value in source, state, an issue, or an Actions command. Add
the bot to the destination and send it an initial message before testing. The
safe connectivity test does not run the strategy:

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
python run_daily_scan.py --telegram-test
```

### Local validation and manual operation

An offline dry run reads the existing cache, performs inference, formats the
Telegram text, and displays prospective state changes without sending or
persisting anything:

```bash
python run_daily_scan.py --dry-run --no-telegram --cache-mode cached
```

Normal production behavior is:

```bash
python run_daily_scan.py
```

The model-paper updater can be run independently without creating signals:

```bash
python run_paper_update.py --dry-run --cache-mode cached
```

Record an explicit human decision separately:

```bash
python record_human_decision.py \
  --run-id fr-20260814 --recommendation-date 2026-08-14 \
  --ticker IONQ --decision SKIP --reason "valuation"
```

Omitting a human decision never blocks the scanner. Human TRADE/SKIP records
cannot change model recommendations, pending entries, positions, or equity.

Generate the prospective report with:

```bash
python generate_prospective_report.py
```

The report labels prospective and historical statistics separately. Reviews
at 25, 50, 100, and 200 completed trades are informational checkpoints only;
they never retrain or modify the strategy.

### Inspection and recovery

Inspect the most recent files under `state/run_history/`,
`state/recommendation_history/`, and `outputs/daily/`. A failed data or state
read produces no recommendation or invented trade. A Telegram delivery failure
is recorded separately after state persistence.

To recover, correct or restore the affected non-secret state file from Git
history, document the correction in a new run/audit record, and manually
dispatch the workflow. Do not delete recommendation or ledger history. If an
entry-day open is missing or a corporate action is detected, the pending item
is held for explicit review; a later close or open is never silently
substituted for the required next regular-session open.
