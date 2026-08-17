# Data Quality Report

- yfinance version: 1.2.2
- Price coverage: 2016-01-04 through 2026-08-14
- Adjusted prices: Yahoo `Adj Close`; adjusted OHLC reconstructed with `Adj Close / Close`.
- Corporate actions: dividends and splits cached when Yahoo supplies them.
- Rolling beta: trailing 252 daily adjusted-close returns versus SPY; full 252 observations required.
- Historical market cap: raw close × Yahoo historical shares where available. Current market cap is used only as an explicitly flagged V1 proxy when shares history is unavailable.
- Market-cap proxy share of stock rows: 5.9%.
- Survivorship bias: severe. The supplied current watchlist excludes delisted historical securities and was selected with present knowledge.
- Delisted stocks: not represented by the proof-of-concept watchlist.
- Look-ahead controls: rolling windows are trailing; signals use close T; entries use open T+1.
- Download errors: `{}`
- Metadata errors: `{}`
- Historical-shares errors: `{}`

## Coverage

| ticker   | min                 | max                 |   count |
|:---------|:--------------------|:--------------------|--------:|
| APP      | 2021-04-15 00:00:00 | 2026-08-14 00:00:00 |    1340 |
| ASTS     | 2019-11-01 00:00:00 | 2026-08-14 00:00:00 |    1704 |
| COIN     | 2021-04-14 00:00:00 | 2026-08-14 00:00:00 |    1341 |
| CVNA     | 2017-04-28 00:00:00 | 2026-08-14 00:00:00 |    2337 |
| HOOD     | 2021-07-29 00:00:00 | 2026-08-14 00:00:00 |    1267 |
| IONQ     | 2021-01-04 00:00:00 | 2026-08-14 00:00:00 |    1410 |
| MSTR     | 2016-01-04 00:00:00 | 2026-08-14 00:00:00 |    2669 |
| QQQ      | 2016-01-04 00:00:00 | 2026-08-14 00:00:00 |    2669 |
| RKLB     | 2020-11-24 00:00:00 | 2026-08-14 00:00:00 |    1436 |
| SPY      | 2016-01-04 00:00:00 | 2026-08-14 00:00:00 |    2669 |
| ^VIX     | 2016-01-04 00:00:00 | 2026-08-14 00:00:00 |    2670 |

## Missing core fields

| ticker   |   adj_close |   volume |
|:---------|------------:|---------:|
| APP      |           0 |        0 |
| ASTS     |           0 |        0 |
| COIN     |           0 |        0 |
| CVNA     |           0 |        0 |
| HOOD     |           0 |        0 |
| IONQ     |           0 |        0 |
| MSTR     |           0 |        0 |
| QQQ      |           0 |        0 |
| RKLB     |           0 |        0 |
| SPY      |           0 |        0 |
| ^VIX     |           0 |        0 |

## Reliability assessment

Price-based calculations, execution timing, and rolling beta are suitable for prototype evidence checks subject to Yahoo corrections. Historical universe membership, security type, market capitalization, and the hand-picked surviving watchlist are not point-in-time reliable. Conclusions involving the $10B filter or claims about the broader U.S. high-beta universe are therefore provisional and must be retested with institutional point-in-time fundamentals and a survivorship-free universe.
