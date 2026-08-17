# Survivorship-Clean Validation Report

## Outcome

The frozen strategy has **not** yet received a survivorship-clean validation. The Yahoo regression reproduced, but no locally available or connected dataset satisfies the required combination of removed/delisted securities, historical OHLCV including the open, corporate actions, economically valid delisting treatment, permanent identifiers, point-in-time eligibility, and historical capitalization.

Per the validation protocol, I stopped before running or labeling another Yahoo backtest as clean. No strategy rule was changed and no alternative strategy was tested.

## Frozen strategy regression

The existing implementation was rerun on the frozen Yahoo panel on 2026-08-17:

| Metric | Reproduced | Reference |
|---|---:|---:|
| Total return | 71.6119% | 71.61% |
| Sharpe | 0.495847 | 0.496 |
| Maximum drawdown | -15.5175% | -15.52% |
| Trades | 24 | 24 |

This confirms code continuity only. It is not new validation evidence.

## Access audit

- No CRSP/WRDS, Norgate, Polygon, Nasdaq Data Link, FMP, Tiingo, or EODHD dataset or credential is present in the workspace/environment.
- The only full research panel remains Yahoo-derived.
- The current machine is macOS. Norgate's local updater and Python access require Windows, so using it here would require a Windows VM or exported files.
- No purchase or account creation was performed.

## Existing Yahoo universe audit

| Item | Existing Yahoo audit | Clean audit |
|---|---:|---:|
| Historical requested symbols (2009-2026) | 863 | unavailable |
| Symbols with usable Yahoo history | 659 (76.4%) | unavailable |
| Missing histories | 204 | unavailable |
| Point-in-time priced member rows | 1,792,648 across 651 tickers | unavailable |
| Strict-cap eligible stock-days/tickers | 14,342 / 85 | unavailable |
| Corporate actions | Yahoo adjustment factor; incomplete auditability | unavailable |
| Delisting returns/cash consideration | not available | unavailable |
| Point-in-time cap | best-available historical shares for a limited subset | unavailable |
| Point-in-time membership | existing historical S&P snapshot spine | unavailable |

The existing membership spine identifies removed constituents but does not reliably distinguish every acquisition, exchange transfer, bankruptcy, and delisting or provide final economic proceeds. Therefore active/removed/delisted and complete/partial clean-history counts cannot be produced honestly without the replacement source.

## Data-source assessment

### 1. CRSP — preferred research foundation

CRSP is the strongest source for this validation. Its US stock database contains permanent security/company identifiers, share codes, historical shares, daily capitalization, distributions, and explicit delisting codes, prices, amounts and returns. CRSP describes daily history back to 1925 and treats securities shown to be worthless as a -100% delisting return. Access is normally institutional/direct or through WRDS, with pricing by quote and a separate CRSP license. [CRSP data guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-data-descriptions-guide-crspaccess/), [WRDS CRSP variables](https://wrds-www.wharton.upenn.edu/demo/crsp/form/), [CRSP CIZ guide](https://www.crsp.org/wp-content/uploads/guides/CRSP_US_Stock_%26_Indexes_Database_Guide_Flat_File_Format_2.0.pdf)

Critical limitation: standard CRSP daily stock fields clearly provide close/price, high/ask, low/bid, volume, returns, shares, capitalization and delisting fields, but do not clearly expose the exchange opening price needed for the frozen T+1-open execution. The preferred institutional design is therefore **CRSP as the eligibility/delisting spine plus an audited historical-open feed joined by permanent identifier**. The open-price supplement must cover inactive securities and survive ticker reuse.

### 2. Norgate Data Platinum/Diamond — best turnkey backtesting candidate

Norgate explicitly includes delisted securities and historical index constituents. US Platinum provides daily history back to 1990 for USD 346.50/6 months or USD 630/12 months; Diamond goes back to 1950 for USD 433.13/6 months or USD 787.50/12 months. It supports Python on Windows and is marketed for survivorship-bias-free backtesting. [Packages and prices](https://norgatedata.com/stockmarketpackages.php), [content](https://norgatedata.com/data-content-tables.php), [accessibility](https://norgatedata.com/accessibility.php)

Limitations: Windows is required; the database is proprietary; historical index membership is strong, but historical market capitalization/shares and CRSP-style delisting proceeds are not clearly documented. These fields must be confirmed before purchase. A free trial exists, but none was started.

### 3. EODHD — best lower-cost API pilot

EODHD documents historical EOD data for delisted US names, dividends, splits, symbol changes, historical index components, and a historical-market-cap endpoint. It states pre-2018 delisted names generally have EOD only and advertises tens of thousands of delisted US symbols. The All-in-One plan is USD 99.99/month; fundamentals is USD 59.99/month, while extended bulk access is quote-based. [Delisted coverage](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), [fundamental/index coverage and pricing](https://eodhd.com/lp/fundamental-data-api)

Limitations: no CRSP-style delisting-return field is documented; last quoted prices cannot automatically substitute for final shareholder proceeds. Historical cap completeness, identifier reuse, common-stock classification, membership dates and delisting economics require a symbol-level audit before acceptance.

### 4. Tiingo — useful OHLC/corporate-action supplement

Tiingo provides raw and adjusted OHLCV, dividends and splits, broad US/OTC history from 1962, REST access, and stable `permaTicker` identifiers for delisted/recycled symbols. Individual pricing is free or USD 30/month; historical fundamentals are an add-on. [EOD product](https://www.tiingo.com/products/end-of-day-stock-price-data), [fundamentals/permaTicker](https://www.tiingo.com/documentation/fundamentals), [pricing](https://www.tiingo.com/about/pricing)

Limitations: point-in-time universe membership and explicit delisting returns/final consideration are not documented. Tiingo is more suitable as the opening-price supplement than as the sole clean spine.

### 5. Polygon — possible historical-open supplement

Polygon provides grouped daily OHLC, reference data and corporate actions. Individual stock plans range from free/2 years to USD 199/month/20+ years. [Stocks pricing](https://polygon.io/stocks), [grouped daily OHLC](https://ui-v3-pr-1103.staging.polygon.io/knowledge-base/article/how-can-i-get-the-daily-prices-for-all-stocks-using-polygons-market-data)

Limitations: explicit delisting proceeds/returns, stable inactive-security mapping, historical shares/cap and point-in-time universe membership are not established. It cannot be considered survivorship-clean alone.

### 6. Financial Modeling Prep — insufficient as sole source

FMP offers delisted-company, historical-price and historical-market-cap endpoints, with plans from free to USD 149/month billed annually. However, FMP explicitly says only selected US delisted histories are available and acknowledges gaps in historical S&P 500 membership. [FMP delisted coverage limitations](https://site.financialmodelingprep.com/contact), [pricing](https://site.financialmodelingprep.com/pricing-plans)

This fails the completeness requirement unless a detailed audit proves otherwise.

### 7. Nasdaq Data Link — product-specific, no qualifying bundle identified

Nasdaq Data Link is an API marketplace. A specific licensed product must be selected and audited; the workspace has no subscription. The currently identified documentation does not establish a single US product combining inactive OHLC, delisting returns, point-in-time membership and point-in-time cap. [API/product organization](https://docs.data.nasdaq.com/docs/data-organization)

## Recommended acquisition path

1. First check whether the user's university/employer already licenses **CRSP Daily through WRDS**. This is the preferred option and avoids an unnecessary purchase.
2. If CRSP is available, obtain 2009-present security-level daily data with permanent IDs, share codes, returns, volume, shares/cap, distributions, and all delisting fields. Pair it with an institutionally licensed opening-price source covering inactive securities. Audit at least the 204 Yahoo-missing names before backtesting.
3. If CRSP is unavailable, run a no-purchase pilot or vendor-confirmation exercise for **Norgate Platinum** and **EODHD**. Require the vendor to answer in writing: historical open coverage for delisted stocks; ticker-reuse identifiers; final delisting cash/return treatment; historical shares/cap coverage; and historical membership coverage.
4. Accept a source only after it produces the requested active/removed/delisted and complete/partial coverage audit and reconciles delisting economics. Then run the frozen strategy exactly once.

## Required ingestion contract

Any supplied clean dataset should expose, at minimum:

- permanent security and company identifiers;
- historical ticker/name/exchange/share-code intervals;
- date, raw and adjusted open/high/low/close, volume;
- split/dividend/capital-event factors and dates;
- historical shares outstanding or point-in-time market cap;
- membership start/end dates if an index spine is used;
- delisting date/code, last trade, final payment/price, payment date and delisting return;
- a flag distinguishing actual, estimated and missing delisting proceeds.

For missing delisting proceeds, the treatment must be frozen before seeing strategy results. No held position may disappear. A conservative fallback schedule should be documented by delisting reason and tested only as a data-quality sensitivity, not used to optimize the strategy.

## Validation work not performed

Because the required clean audit could not be passed, the following were correctly **not run**:

- clean primary backtest;
- missing-stock impact and qualifying delisted-stock analysis;
- clean-universe matched-random control;
- clean trade/ticker-cluster bootstrap;
- clean tail-removal reruns;
- clean-vs-Yahoo performance conclusion;
- decision on prospective paper trading.

The required CSV deliverables exist with `NOT_AVAILABLE`/`NOT_RUN` status rather than fabricated values.

## Answers to the final questions

1. **How much survivorship bias existed?** Unknown; potentially material. The 23.6% missing-symbol rate is exposure, not a measured return bias.
2. **Did delisted stocks reduce performance?** Not measurable without clean data.
3. **Did missing Yahoo stocks generate significant losses?** Not measurable.
4. **Does ONE x25% remain profitable on clean data?** Unknown.
5. **Profitable in 2016-2022?** Unknown on clean data.
6. **Profitable after 2023?** Unknown on clean data.
7. **Clean Sharpe?** Not available.
8. **Clean maximum drawdown?** Not available.
9. **Above the 95th matched-random return percentile?** Not tested.
10. **Sharpe above the 95th random percentile?** Not tested.
11. **Positive ticker-cluster evidence?** Not tested.
12. **Do top-winner removals destroy clean performance?** Not tested.
13. **Does the strategy frequently enter eventual delistings?** Unknown.
14. **Is the economic hypothesis still supported?** It remains a biased-data hypothesis, not cleanly validated evidence.
15. **Enough evidence for prospective paper trading?** No.

## FINAL VALIDATION DECISION

INCONCLUSIVE — DATA QUALITY STILL INSUFFICIENT
