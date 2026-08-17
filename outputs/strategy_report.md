# High-Beta Mean-Reversion Strategy Report

## Executive conclusion

This is a proof-of-concept on eight currently known survivors, not a survivorship-free U.S. universe test. The $10B criterion uses an explicitly flagged current-market-cap proxy for 5.9% of stock-date rows where Yahoo lacks adequate historical shares. Accordingly, the evidence can justify only **modify and retest** or **paper trade**, never production deployment. Negative findings are retained.

The predeclared primary specification is Strategy A (pure bottom-quartile entry) with a 30-trading-day hold, next-open execution, and 0.20% estimated round-trip friction. Its combined net total return is 79.48% versus gross 81.21%; net Sharpe is 0.313, maximum drawdown -42.58%, and 59 trades. Development performance was negative (-11.13%, Sharpe -0.392) and only 2 of 288 development robustness cells were positive.

## Buy-and-hold benchmarks

| period   | benchmark   |   total_return |   cagr |   annualized_volatility |   sharpe |   maximum_drawdown |
|:---------|:------------|---------------:|-------:|------------------------:|---------:|-------------------:|
| combined | SPY         |         3.5809 | 0.1543 |                  0.1779 |   0.8975 |            -0.3372 |
| combined | QQQ         |         6.1952 | 0.2044 |                  0.2230 |   0.9478 |            -0.3512 |

## Forward returns: qualifying observations vs same eligible universe

|   horizon |   mean_return_signal |   median_return_signal |   win_probability_signal |   observations_signal |   mean_return_unconditional |   median_return_unconditional |   win_probability_unconditional |
|----------:|---------------------:|-----------------------:|-------------------------:|----------------------:|----------------------------:|------------------------------:|--------------------------------:|
|   10.0000 |               0.0259 |                 0.0132 |                   0.5315 |              952.0000 |                      0.0238 |                        0.0070 |                          0.5190 |
|   20.0000 |               0.0541 |                 0.0122 |                   0.5151 |              893.0000 |                      0.0492 |                        0.0081 |                          0.5133 |
|   30.0000 |               0.0863 |                 0.0311 |                   0.5338 |              858.0000 |                      0.0793 |                        0.0078 |                          0.5112 |
|   60.0000 |               0.1425 |                 0.0818 |                   0.5658 |              806.0000 |                      0.1670 |                        0.0735 |                          0.5586 |
|   90.0000 |               0.1269 |                 0.0329 |                   0.5385 |              754.0000 |                      0.2568 |                        0.1328 |                          0.5986 |

## Explicit answers

1. **Do bottom-quartile observations outperform generally?** **Not consistently.** They lead unconditional observations slightly at 10–30 days, trail at 60 days, and trail sharply at 90 days.
2. **Average and median returns after 10/20/30/60/90 days?** Reported above.
3. **Win probability?** Reported above by horizon.
4. **Is 25% sensible?** **Not as a sharp cutoff.** The 10–25% and 25–50% buckets have nearly identical 30-day means, while the lowest 0–10% bucket is worse.
5. **Is 100 days sensible?** **Not supported in development.** Every tested holding period at the 100-day/25% setting lost money, and only 2/288 full-grid cells were positive.
6. **Does above-100DMA improve results?** **No testable evidence.** It generated zero trades because bottom-quartile price and above-SMA conditions rarely coexist here.
7. **Does near-100DMA improve results?** **No.** It generated one combined-period trade, which lost money.
8. **Out of sample since 2023?** **Yes in this biased sample:** total return 101.95%, Sharpe 0.601, but this conflicts with negative development results and is not robust confirmation.
9. **Random entries?** **No conventional statistical win.** Actual mean return is at the 85.9th percentile of 1,000 matched simulations, below 95%.
10. **Typical post-entry drawdown?** Median MAE is -14.03%; mean MAE is -17.28%.
11. **Stop supported by MAE?** **A -10% stop is not supported by this hold-period sample:** winning trades had median MAE -7.54% and 25th-percentile MAE -13.58%, so it would cut a meaningful share of eventual winners. This is descriptive, not causal.
12. **Profit target supported by MFE?** Winners had median MFE 38.97%; a 15–20% target captures gains but truncates many large winners. Exit-rule rows provide the direct comparison.
13. **Bear markets?** **Positive but inconclusive:** 15 bear-regime trades averaged 15.15% versus 9.84% for 44 bull trades; selection bias and small samples dominate.
14. **Does higher beta improve performance?** **No.** Forward performance is not monotonic; the 3.0–4.0 beta bucket has negative 30-day mean returns.
15. **Driven by extreme winners?** **Partly.** Best trade 89.64%, median 4.07%, mean 11.19%; the mean drops to 4.75% after removing five best trades.
16. **Remove five best trades?** Remaining mean trade return: 4.75%.
17. **Remove five best-performing stocks?** Removed ASTS, CVNA, HOOD, IONQ, RKLB; remaining mean: 6.00%.
18. **Broad robust parameter region?** **No.** Only 2/288 development grid cells were positive, so there is no broad profitable region.
19. **Simplest supported strategy?** **None is supported strongly enough yet.** The pure/30-day rule remains the simplest specification to retest on unbiased data; the SMA variants should be dropped.
20. **Decision:** **Modified and retested** with a survivorship-free universe and point-in-time market cap before paper-trading confidence can be established.

## Range-position buckets (30-day horizon)

| range_bucket   |   mean_return |
|:---------------|--------------:|
| 0-10%          |        0.0519 |
| 10-25%         |        0.1196 |
| 25-50%         |        0.1159 |
| 50-75%         |        0.0868 |
| 75-90%         |        0.0405 |
| 90-100%        |        0.0614 |

## Beta buckets

| beta_bucket   |   mean_return |   median_return |   win_probability |      p25 |      p75 |   observations |   trade_win_rate |      mae |      mfe |   worst_mae |
|:--------------|--------------:|----------------:|------------------:|---------:|---------:|---------------:|-----------------:|---------:|---------:|------------:|
| 2.0-2.5       |        0.0907 |          0.0287 |            0.5441 |  -0.1217 |   0.2546 |           2042 |           0.6207 |  -0.1804 |   0.3084 |     -0.7260 |
| 2.5-3.0       |        0.1176 |          0.0254 |            0.5250 |  -0.1408 |   0.3423 |           1299 |           0.5263 |  -0.1704 |   0.4119 |     -0.4253 |
| 3.0-4.0       |       -0.0671 |         -0.0771 |            0.3407 |  -0.2286 |   0.0515 |            499 |           0.6364 |  -0.1572 |   0.2737 |     -0.3372 |
| >4.0          |      nan      |        nan      |          nan      | nan      | nan      |              0 |         nan      | nan      | nan      |    nan      |

## Bull/bear regimes

| market_regime   |   trades |   average_return |   median_return |   win_rate |     mae |    mfe |
|:----------------|---------:|-----------------:|----------------:|-----------:|--------:|-------:|
| bear            |       15 |           0.1515 |          0.0918 |     0.7333 | -0.1960 | 0.4720 |
| bull            |       44 |           0.0984 |          0.0301 |     0.5455 | -0.1649 | 0.2886 |

## Execution and bias controls

- Signal at close T; entry at open T+1.
- Adjusted OHLC is used consistently for execution and signal levels.
- Gap-through stops/targets fill at the next open. If stop and target occur in one candle, the stop is assumed first.
- Only one active position per stock; maximum ten positions, 10% allocation, no leverage.
- 0.05% commission and 0.05% slippage each way; gross and net trade fields are retained.
- Development ends 2022-12-31; the robustness grid uses development data only.
- The current watchlist creates material survivorship/selection bias. Current market-cap proxies create point-in-time bias and are flagged per row/trade.
