# Recent-Period Survivorship-Clean Validation

## Executive conclusion

The requested 2023-through-latest survivorship-clean validation **cannot yet be performed**. The frozen Yahoo reference was reproduced with a full 2022 warm-up and entries disabled before 2023, but no accessible dataset passes the clean-data gate.

I did not rerun Yahoo and label it clean. No strategy parameter was changed, no alternative was tested, and no post-result optimization was performed.

This report therefore makes a data-quality decision, not a strategy-performance decision.

## Frozen Yahoo reference with proper warm-up

- Data warm-up: 2022-01-03 through 2022-12-30.
- Entries enabled: 2023-01-01 onward.
- Evaluation: 2023-01-03 through the latest cached date, 2026-08-14.
- Frozen strategy: one position maximum, 25% current-equity allocation, no stop, no queue, lowest RangePosition then highest beta ranking, RangePosition >=75%/90-day exit, existing next-open execution and costs.

| Metric | Yahoo reference |
|---|---:|
| Total return | 41.02% |
| CAGR | 9.99% |
| Annualized volatility | 12.67% |
| Sharpe | 0.818 |
| Sortino | 1.357 |
| Maximum drawdown | -10.33% |
| Calmar | 0.967 |
| Trades / unique stocks | 12 / 9 |
| Win rate | 75.0% |
| Average / median trade | 12.27% / 17.89% |
| Profit factor | 3.16 |
| Average winner / loser | 23.13% / -20.32% |
| Best / worst trade | 64.68% / -22.54% |
| Average / median MAE | -16.15% / -10.88% |
| Average / median MFE | 19.86% / 18.62% |
| Average holding period | 53.3 trading days |
| Average exposure | 17.29% |
| Time fully in cash | 29.88% |
| Turnover | 6.38x average equity |

These figures are reference-only and remain exposed to the known Yahoo missing-security problem.

## Year-by-year Yahoo reference

Trades are attributed by exit year. Selected signals are attributed by signal year, so a year-end selection may exit in the following year.

| Period | Signal stock-days | Selected signals | Trades exited | Return | Win rate | Average trade | Sharpe | Maximum drawdown | Average exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 59 | 3 | 3 | 14.42% | 100.0% | 18.40% | 2.282 | -3.69% | 6.82% |
| 2024 | 736 | 4 | 3 | 5.25% | 66.7% | 8.61% | 0.481 | -8.64% | 22.93% |
| 2025 | 661 | 3 | 3 | 9.35% | 66.7% | 16.96% | 0.721 | -10.14% | 18.52% |
| 2026 YTD through Aug 14 | 520 | 2 | 3 | 5.75% | 66.7% | 5.10% | 0.594 | -10.20% | 23.03% |

The reference return is positive in every calendar segment, but annual Sharpes based on three exits are highly unstable.

## Sample-size assessment

- Qualifying signal stock-days: 1,978; 1,976 had a following execution day available.
- Selected signals/trades: 12.
- Unique stocks: 9.
- Evaluation trading days: 907.
- Days with a position: 636 (70.1%).
- Average capital exposure: 17.3%, reflecting the frozen 25% entry allocation and price drift.

Classification: **SMALL SAMPLE**. Twelve sequential trades are enough to expose implementation and large failures, but not enough for a strong alpha inference, stable annual estimates, or reliable ticker-cluster asymptotics. A clean result would need to be interpreted with wide bootstrap intervals even if its point estimates were high.

## Clean-data access audit

No CRSP/WRDS, Norgate, EODHD, Polygon, FMP, Tiingo, or Nasdaq Data Link credential or local dataset is present. The only complete local research panel remains Yahoo-derived.

The source findings from the full validation assessment remain applicable:

1. **CRSP/WRDS plus an audited opening-price source** is the strongest institutional solution. CRSP provides permanent IDs, share codes, historical shares/cap and explicit delisting fields, but the standard daily stock product does not clearly expose the required opening price. [CRSP data guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-data-descriptions-guide-crspaccess/), [WRDS CRSP fields](https://wrds-www.wharton.upenn.edu/demo/crsp/form/)
2. **Norgate US Platinum/Diamond** is the best turnkey OHLC/historical-membership candidate. It includes delisted securities and historical constituents, but requires Windows and its point-in-time market-cap/delisting-payment coverage must be confirmed. Platinum is USD 346.50/6 months or USD 630/12 months. [Norgate packages](https://norgatedata.com/stockmarketpackages.php), [Norgate accessibility](https://norgatedata.com/accessibility.php)
3. **EODHD** is the most practical recent-period API pilot. It documents post-2018 delisted EOD/fundamental/corporate-action coverage, historical index components and historical market cap. Its All-in-One plan is USD 99.99/month. It does not document a CRSP-style delisting-return field, so final consideration and identifier reuse require an audit. [EODHD delisted coverage](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), [EODHD fundamentals/pricing](https://eodhd.com/lp/fundamental-data-api)
4. **Tiingo or Polygon** may supply historical opening prices, but neither is sufficient alone without a clean eligibility/delisting spine. [Tiingo EOD](https://www.tiingo.com/products/end-of-day-stock-price-data), [Polygon stock plans](https://polygon.io/stocks)
5. **FMP** is not acceptable alone because it acknowledges incomplete delisted histories and historical S&P membership gaps. [FMP limitations](https://site.financialmodelingprep.com/contact)

No account was created and nothing was purchased.

## Exact data or credentials required

One of the following is needed before work can continue:

### Preferred institutional route

- WRDS credentials with licensed CRSP Daily US Stock access from at least 2022 through latest;
- an approved daily-open feed covering active and inactive US common stocks over identical dates;
- permission to join sources using permanent identifiers or a vendor-supplied dated mapping.

### Practical vendor route

- Norgate US Platinum/Diamond access on Windows or exported OHLC/membership/delisted files, plus a verified point-in-time market-cap source and documented final delisting proceeds; or
- an EODHD API key with EOD, fundamentals/historical market cap, historical components and delisted-symbol entitlements, after a coverage pilot confirms the required fields.

Before backtesting, the source must enumerate active, removed and delisted US common stocks; complete/partial OHLCV; missing opens; corporate actions; historical cap coverage; and actual/estimated/missing delisting proceeds. A held delisting must never disappear.

## Work correctly not performed

Because the clean audit failed at access, the following were not run:

- clean frozen strategy;
- identical-date clean-vs-Yahoo comparison;
- recovered/missing-stock effect;
- clean delisted-stock trade analysis;
- 5,000 clean-universe matched-random simulations;
- clean trade/ticker-cluster bootstrap;
- clean top-trade/top-stock removal reruns.

The corresponding CSVs carry `NOT_AVAILABLE` or `NOT_RUN` rather than invented values.

## Answers to the final questions

1. **Profitable on clean data from 2023 onward?** Unknown; no clean backtest exists.
2. **Clean CAGR?** Not available.
3. **Clean Sharpe?** Not available.
4. **Clean maximum drawdown?** Not available.
5. **Clean trade count?** Not available. Yahoo reference: 12.
6. **Large enough sample?** The Yahoo reference is a small sample; clean sample size is unknown.
7. **Yahoo versus clean?** Cannot be compared until identical-date clean data is acquired.
8. **Did missing stocks reduce performance?** Unknown.
9. **Did delisted stocks create losses?** Unknown.
10. **Does the strategy select eventual failures?** Unknown.
11. **Distributed across years?** Yahoo reference is positive across all four segments; clean distribution is unknown.
12. **Diversified across stocks?** Yahoo reference uses 9 stocks; clean diversification is unknown.
13. **Survives top-winner removal?** Not tested on clean data.
14. **Above 95th random-return percentile?** Not tested on the clean universe.
15. **Above 95th random-Sharpe percentile?** Not tested.
16. **Ticker-cluster support?** Not tested; 12 trades would imply wide uncertainty.
17. **Does the edge survive recent clean validation?** Not established.
18. **Enough evidence for prospective paper trading?** No.

## Recent-period interpretation limit

Even a future pass would support only the statement that the frozen strategy showed evidence in the 2023+ regime under clean data. It would not establish robustness across recessions, multiple decades, or all market cycles.

## FINAL DECISION

INCONCLUSIVE — DATA QUALITY INSUFFICIENT
