# Regime Diagnosis and Confirmation Report

## Executive conclusion

The original result is not evidence of a stable general mean-reversion edge. BASE returned -11.13% in 2016–2022 across 7 trades, then gained 101.95% in 2023–2026 across 52 trades. The change coincides with a different stock mix and speculative-theme cycle, not a parameter-stable effect. The confirmation variant with the best multi-metric balance is **positive_5d_momentum**, but its status is judged from development performance, drawdown, Sharpe, count, concentration, the limited neighborhood, and random control—not CAGR alone.

Final decision: **MODIFY AND RETEST**.

## Period diagnosis — BASE

| period    |   number_of_signals |   number_of_trades |    cagr |   total_return |   sharpe |   sortino |   maximum_drawdown |   win_rate |   average_trade_return |   median_trade_return |   profit_factor |   average_mae |   average_mfe |   average_holding_period |   average_beta_at_entry |   average_range_position |   exposure |
|:----------|--------------------:|-------------------:|--------:|---------------:|---------:|----------:|-------------------:|-----------:|-----------------------:|----------------------:|----------------:|--------------:|--------------:|-------------------------:|------------------------:|-------------------------:|-----------:|
| 2016-2019 |                   0 |                  0 |  0.0000 |         0.0000 | nan      |  nan      |             0.0000 |   nan      |               nan      |              nan      |        nan      |      nan      |      nan      |                 nan      |                nan      |                 nan      |     0.0000 |
| 2020-2022 |                 154 |                  7 | -0.0387 |        -0.1113 |  -0.5994 |   -0.8404 |            -0.1203 |     0.4286 |                -0.1606 |               -0.1594 |          0.2517 |       -0.3217 |        0.2814 |                  30.0000 |                  2.5054 |                   0.1203 |     0.0250 |
| 2023-2026 |                 845 |                 52 |  0.2149 |         1.0195 |   0.6015 |    1.2371 |            -0.4258 |     0.6154 |                 0.1486 |                0.0682 |          2.8513 |       -0.1528 |        0.3425 |                  28.5000 |                  2.5737 |                   0.1632 |     0.1633 |
| 2016-2022 |                 154 |                  7 | -0.0167 |        -0.1113 |  -0.3924 |   -0.5395 |            -0.1203 |     0.4286 |                -0.1606 |               -0.1594 |          0.2517 |       -0.3217 |        0.2814 |                  30.0000 |                  2.5054 |                   0.1203 |     0.0107 |
| combined  |                 999 |                 59 |  0.0567 |         0.7948 |   0.3130 |    0.6338 |            -0.4258 |     0.5932 |                 0.1119 |                0.0407 |          2.2455 |       -0.1728 |        0.3353 |                  28.6780 |                  2.5656 |                   0.1581 |     0.0626 |

## Confirmation comparison

All variants retain the original universe, eligibility, 30-session hold, costs, ranking, sizing, and next-open execution.

| variant                | period    |   total_return |    cagr |   sharpe |   sortino |   maximum_drawdown |   calmar |   number_of_trades |   win_rate |   average_trade_return |   median_trade_return |   profit_factor |   average_mae |   median_mae |   average_mfe |   average_holding_period |   exposure |
|:-----------------------|:----------|---------------:|--------:|---------:|----------:|-------------------:|---------:|-------------------:|-----------:|-----------------------:|----------------------:|----------------:|--------------:|-------------:|--------------:|-------------------------:|-----------:|
| base                   | 2023-2026 |         1.0195 |  0.2149 |   0.6015 |    1.2371 |            -0.4258 |   0.5046 |                 52 |     0.6154 |                 0.1486 |                0.0682 |          2.8513 |       -0.1528 |      -0.1276 |        0.3425 |                  28.5000 |     0.1633 |
| base                   | 2016-2022 |        -0.1113 | -0.0167 |  -0.3924 |   -0.5395 |            -0.1203 |  -0.1392 |                  7 |     0.4286 |                -0.1606 |               -0.1594 |          0.2517 |       -0.3217 |      -0.3098 |        0.2814 |                  30.0000 |     0.0107 |
| base                   | combined  |         0.7948 |  0.0567 |   0.3130 |    0.6338 |            -0.4258 |   0.1331 |                 59 |     0.5932 |                 0.1119 |                0.0407 |          2.2455 |       -0.1728 |      -0.1403 |        0.3353 |                  28.6780 |     0.0626 |
| sma100_trend           | 2023-2026 |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |
| sma100_trend           | 2016-2022 |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |
| sma100_trend           | combined  |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |
| sma20_recovery         | 2023-2026 |         0.1471 |  0.0387 |   0.3714 |    0.6075 |            -0.1855 |   0.2089 |                 20 |     0.5000 |                 0.0725 |                0.0031 |          2.0029 |       -0.1365 |      -0.1230 |        0.2890 |                  27.3000 |     0.0616 |
| sma20_recovery         | 2016-2022 |        -0.0286 | -0.0041 |  -0.1323 |   -0.1842 |            -0.0573 |  -0.0724 |                  3 |     0.3333 |                -0.0947 |               -0.0598 |          0.2275 |       -0.2580 |      -0.2085 |        0.3202 |                  30.0000 |     0.0048 |
| sma20_recovery         | combined  |         0.1143 |  0.0103 |   0.1731 |    0.2748 |            -0.1855 |   0.0553 |                 23 |     0.4783 |                 0.0507 |               -0.0279 |          1.6364 |       -0.1524 |      -0.1294 |        0.2931 |                  27.6522 |     0.0241 |
| positive_5d_momentum   | 2023-2026 |         0.6422 |  0.1472 |   0.8297 |    1.4512 |            -0.1410 |   1.0443 |                 37 |     0.5676 |                 0.1450 |                0.1122 |          3.1492 |       -0.1495 |      -0.1049 |        0.3291 |                  26.9459 |     0.1105 |
| positive_5d_momentum   | 2016-2022 |        -0.0689 | -0.0102 |  -0.2839 |   -0.3960 |            -0.0729 |  -0.1394 |                  5 |     0.4000 |                -0.1342 |               -0.2736 |          0.4235 |       -0.3554 |      -0.3975 |        0.1658 |                  30.0000 |     0.0069 |
| positive_5d_momentum   | combined  |         0.5291 |  0.0408 |   0.4121 |    0.6961 |            -0.1410 |   0.2897 |                 42 |     0.5476 |                 0.1117 |                0.0541 |          2.3306 |       -0.1740 |      -0.1293 |        0.3097 |                  27.3095 |     0.0422 |
| sma100_and_positive_5d | 2023-2026 |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |
| sma100_and_positive_5d | 2016-2022 |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |
| sma100_and_positive_5d | combined  |         0.0000 |  0.0000 | nan      |  nan      |             0.0000 | nan      |                  0 |   nan      |               nan      |              nan      |        nan      |      nan      |     nan      |      nan      |                 nan      |     0.0000 |

## Explicit answers

1. **Why did the strategy lose money in 2016–2022?** There were no qualifying signals in 2016–2019. The seven executable 2020–2022 trades were only five COIN and two APP trades, with average return -16.06%, win rate 42.86%, and average MAE -32.17%. At entry, median SPY/QQQ distance from SMA200 was negative and median stock drawdown from its 100-day high was about 58%. The result is a sparse two-stock falling-market sample, not a diversified development test.
2. **Why did it perform better after 2023?** Trade count rose to 52 across all eight stocks, average trade return to 14.86%, MAE improved to -15.28%, and MFE rose to 34.25%. SPY/QQQ 60-day trends and distance from SMA200 were materially stronger than in development, while individual stocks still entered after sharp selloffs. This looks like broader speculative rebound participation inside a healthier medium-term market, not proof of a timeless edge.
3. **Is post-2023 performance driven by a few stocks?** **Partly, but not solely.** The leading stock contributes 19.11% of net P&L and the top three contribute 49.21%. Removal sensitivities are reported below.
4. **Is it driven by speculative themes?** **Not by one theme alone.** The leading theme contributes 25.54% of net P&L; space, fintech, crypto-linked, consumer, AI/software, and quantum all contribute positively. The mapping is manual and not historical sector data.
5. **Does it mainly work in bullish SPY/QQQ trends?** **Only in a nuanced sense.** Returns are not better merely when price is above SMA200: 9.84% above versus 15.15% below SPY SMA200, and 9.76% above versus 15.04% below QQQ SMA200. However, trades with SPY SMA50 above SMA200 average 13.94% versus −6.34% when below, and negative prior-20-day SPY returns outperform positive ones. The evidence fits “buy high-beta dips during an established rising trend after a short market pullback” better than either general mean reversion or a simple above-SMA200 rule.
6. **Are losers primarily falling knives?** **No cleanly.** Both winners and losers enter with sharply negative momentum and below declining SMAs. Losers had median prior-5-day return -8.47% and SMA20 slope -2.13%, while winners were actually -10.80% and -3.35%. Losers do show more consecutive down days and much worse realized MAE, but falling-knife indicators do not separate outcomes consistently.
7. **Does short-term momentum differentiate winners and losers?** **Not monotonically in the raw BASE trades.** Winner median prior-5-day return is -2.33% lower than loser median. The positive-five-day filter improves portfolio drawdown and Sharpe by excluding many entries, but that does not establish a continuous winner/loser momentum relationship.
8. **Does being above SMA100 help?** See `sma100_trend`: development return 0.00%, combined trades 0. A tiny sample is not evidence.
9. **Does crossing above SMA20 help?** Development return -2.86%, combined Sharpe 0.173, and drawdown -18.55%.
10. **Does positive 5-day momentum help?** Development return -6.89%, combined Sharpe 0.412, drawdown -14.10%, and 42 trades.
11. **Does the combined filter help?** Development return 0.00%; combined trade count 0. It is rejected if it achieves apparent safety by eliminating nearly all observations.
12. **Best return/drawdown/Sharpe/robustness/simplicity balance?** **positive_5d_momentum** ranks best under the predeclared multi-metric rule. Its combined return is 52.91%, drawdown -14.10%, Sharpe 0.412, with 42 trades. Its top three stocks contribute 78.03% of variant P&L, so concentration remains material.
13. **Does a revised rule show a development-period edge?** Best-variant development return is -6.89% versus BASE -11.13%. Only 0/3 nearby development specifications are positive.
14. **Statistically meaningful versus random?** The selected variant reached the 86.9th percentile of 1,000 matched simulations.
15. **Research recommendation?** **MODIFY AND RETEST**. Recent-period strength alone is insufficient for live deployment.

## Post-2023 ticker concentration

| ticker   |   number_of_trades |   total_pnl_contribution |   average_trade_return |   median_return |   win_rate |     mae |    mfe |
|:---------|-------------------:|-------------------------:|-----------------------:|----------------:|-----------:|--------:|-------:|
| HOOD     |                  7 |               17318.5784 |                 0.1908 |          0.1263 |     0.7143 | -0.1389 | 0.3272 |
| COIN     |                 12 |               13781.3314 |                 0.1342 |          0.0127 |     0.5000 | -0.1523 | 0.3719 |
| CVNA     |                  6 |               13490.0351 |                 0.1512 |          0.1124 |     0.8333 | -0.1035 | 0.2731 |
| APP      |                  6 |               12732.0286 |                 0.2018 |          0.1310 |     0.5000 | -0.1776 | 0.3240 |
| ASTS     |                  4 |               11851.7566 |                 0.2224 |          0.1291 |     0.7500 | -0.1392 | 0.4942 |
| RKLB     |                  2 |               11286.4617 |                 0.4007 |          0.4007 |     1.0000 | -0.1885 | 0.4904 |
| IONQ     |                  5 |                8577.6386 |                 0.1136 |          0.0507 |     0.6000 | -0.1704 | 0.3626 |
| MSTR     |                 10 |                1568.5834 |                 0.0402 |          0.0109 |     0.5000 | -0.1671 | 0.2704 |

## Post-2023 removal sensitivity

| sensitivity             |   total_return |   cagr |   sharpe |   maximum_drawdown |   number_of_trades |
|:------------------------|---------------:|-------:|---------:|-------------------:|-------------------:|
| base                    |         1.0195 | 0.2149 |   0.6015 |            -0.4258 |                 52 |
| remove_best_trade       |         0.8534 | 0.1863 |   0.5547 |            -0.4258 |                 51 |
| remove_best_5_trades    |         0.4039 | 0.0985 |   0.4019 |            -0.4264 |                 47 |
| remove_top_10pct_trades |         0.3251 | 0.0811 |   0.3694 |            -0.4640 |                 46 |
| remove_best_stock       |         0.7970 | 0.1762 |   0.5971 |            -0.3426 |                 45 |
| remove_best_3_stocks    |         0.4291 | 0.1039 |   0.5125 |            -0.2388 |                 27 |

## Best-confirmation ticker concentration — combined

| ticker   |   number_of_trades |   total_pnl_contribution |   average_trade_return |   median_return |   win_rate |     mae |    mfe |
|:---------|-------------------:|-------------------------:|-----------------------:|----------------:|-----------:|--------:|-------:|
| RKLB     |                  2 |               16221.9825 |                 0.6278 |          0.6278 |     1.0000 | -0.0943 | 0.7185 |
| HOOD     |                  4 |               15567.3133 |                 0.3049 |          0.3102 |     0.7500 | -0.0570 | 0.4452 |
| CVNA     |                  3 |                9499.7576 |                 0.2540 |          0.2230 |     1.0000 | -0.1330 | 0.2719 |
| IONQ     |                  4 |                4383.2625 |                 0.0785 |          0.1065 |     0.7500 | -0.2132 | 0.2059 |
| MSTR     |                  7 |                3854.0813 |                 0.0679 |         -0.0096 |     0.4286 | -0.1322 | 0.2610 |
| APP      |                  5 |                2465.7082 |                 0.0678 |          0.0407 |     0.6000 | -0.1950 | 0.2288 |
| COIN     |                 15 |                 841.6502 |                 0.0213 |         -0.0447 |     0.3333 | -0.2202 | 0.2877 |
| ASTS     |                  2 |                  80.2867 |                 0.0040 |          0.0040 |     0.5000 | -0.2177 | 0.4311 |

## Theme contribution

Manual mapping: APP = AI/software; COIN and MSTR = crypto-linked; ASTS and RKLB = space; IONQ = quantum; HOOD = fintech; CVNA = consumer/other.

| theme                  |   number_of_trades |   total_pnl_contribution |   average_trade_return |   win_rate |
|:-----------------------|-------------------:|-------------------------:|-----------------------:|-----------:|
| space                  |                  6 |               23138.2183 |                 0.2818 |     0.8333 |
| fintech                |                  7 |               17318.5784 |                 0.1908 |     0.7143 |
| crypto / crypto-linked |                 22 |               15349.9147 |                 0.0915 |     0.5000 |
| consumer / other       |                  6 |               13490.0351 |                 0.1512 |     0.8333 |
| AI / software          |                  6 |               12732.0286 |                 0.2018 |     0.5000 |
| quantum                |                  5 |                8577.6386 |                 0.1136 |     0.6000 |

## Market regimes

`trade_return_sharpe` annualizes the dispersion of 30-day trade returns and is descriptive; it is not a portfolio Sharpe.

| regime                  | state    |   number_of_trades |   average_return |   median_return |   win_rate |     mae |    mfe |   trade_return_sharpe |
|:------------------------|:---------|-------------------:|-----------------:|----------------:|-----------:|--------:|-------:|----------------------:|
| SPY vs SMA200           | below    |                 15 |           0.1515 |          0.0918 |     0.7333 | -0.1960 | 0.4720 |                1.0808 |
| SPY vs SMA200           | above    |                 44 |           0.0984 |          0.0301 |     0.5455 | -0.1649 | 0.2886 |                0.9176 |
| QQQ vs SMA200           | below    |                 16 |           0.1504 |          0.1124 |     0.7500 | -0.1965 | 0.4575 |                1.1102 |
| QQQ vs SMA200           | above    |                 43 |           0.0976 |          0.0261 |     0.5349 | -0.1640 | 0.2898 |                0.9002 |
| SPY SMA50 vs SMA200     | below    |                  8 |          -0.0634 |         -0.0630 |     0.5000 | -0.2815 | 0.4113 |               -0.4592 |
| SPY SMA50 vs SMA200     | above    |                 51 |           0.1394 |          0.0661 |     0.6078 | -0.1558 | 0.3233 |                1.2678 |
| Previous SPY 20D return | negative |                 28 |           0.2186 |          0.1368 |     0.7143 | -0.1401 | 0.4314 |                1.8625 |
| Previous SPY 20D return | positive |                 31 |           0.0155 |         -0.0044 |     0.4839 | -0.2023 | 0.2484 |                0.1474 |

## Signal quality inside the bottom quartile

| range_bucket   |   number_of_trades |   average_return |   median_return |   win_rate |     mae |    mfe |   trade_return_sharpe |
|:---------------|-------------------:|-----------------:|----------------:|-----------:|--------:|-------:|----------------------:|
| 0-5%           |                  8 |           0.0034 |          0.0109 |     0.5000 | -0.2702 | 0.3443 |                0.0239 |
| 5-10%          |                  5 |           0.0818 |          0.0661 |     0.6000 | -0.1901 | 0.2988 |                0.9242 |
| 10-15%         |                  9 |           0.3694 |          0.3110 |     0.8889 | -0.0425 | 0.5616 |                4.0273 |
| 15-20%         |                 17 |           0.0236 |          0.0334 |     0.5294 | -0.1752 | 0.2600 |                0.2371 |
| 20-25%         |                 20 |           0.1219 |          0.0268 |     0.5500 | -0.1861 | 0.3028 |                1.0064 |

## Winner/loser and period condition distributions

| grouping     | group     | variable                |   observations |    mean |   median |     p25 |     p75 |
|:-------------|:----------|:------------------------|---------------:|--------:|---------:|--------:|--------:|
| outcome      | loser     | spy_20d_return          |             24 |  0.0115 |   0.0064 | -0.0017 |  0.0273 |
| outcome      | loser     | spy_60d_return          |             24 |  0.0325 |   0.0398 |  0.0169 |  0.0584 |
| outcome      | loser     | qqq_20d_return          |             24 |  0.0047 |   0.0027 | -0.0366 |  0.0364 |
| outcome      | loser     | qqq_60d_return          |             24 |  0.0392 |   0.0357 |  0.0072 |  0.0803 |
| outcome      | loser     | spy_distance_sma200     |             24 |  0.0576 |   0.0789 |  0.0437 |  0.0983 |
| outcome      | loser     | qqq_distance_sma200     |             24 |  0.0630 |   0.0873 |  0.0307 |  0.1178 |
| outcome      | loser     | vix_level               |             24 | 19.4458 |  18.6800 | 16.3150 | 20.8675 |
| outcome      | loser     | previous_20d_return     |             24 | -0.1458 |  -0.1301 | -0.2492 | -0.0528 |
| outcome      | loser     | previous_60d_return     |             24 | -0.2346 |  -0.1995 | -0.3347 | -0.0971 |
| outcome      | loser     | drawdown_from_100d_high |             24 | -0.3998 |  -0.3825 | -0.4352 | -0.3025 |
| outcome      | winner    | spy_20d_return          |             35 | -0.0056 |  -0.0167 | -0.0423 |  0.0177 |
| outcome      | winner    | spy_60d_return          |             35 |  0.0040 |   0.0267 | -0.0504 |  0.0526 |
| outcome      | winner    | qqq_20d_return          |             35 | -0.0089 |  -0.0283 | -0.0427 |  0.0080 |
| outcome      | winner    | qqq_60d_return          |             35 |  0.0067 |  -0.0018 | -0.0617 |  0.0700 |
| outcome      | winner    | spy_distance_sma200     |             35 |  0.0326 |   0.0662 | -0.0123 |  0.0840 |
| outcome      | winner    | qqq_distance_sma200     |             35 |  0.0343 |   0.0473 | -0.0229 |  0.1036 |
| outcome      | winner    | vix_level               |             35 | 23.1080 |  21.9700 | 17.4900 | 27.0700 |
| outcome      | winner    | previous_20d_return     |             35 | -0.1490 |  -0.1728 | -0.2701 | -0.0466 |
| outcome      | winner    | previous_60d_return     |             35 | -0.1980 |  -0.2041 | -0.3471 | -0.0635 |
| outcome      | winner    | drawdown_from_100d_high |             35 | -0.4390 |  -0.4469 | -0.5075 | -0.3633 |
| period_group | 2016-2022 | spy_20d_return          |              7 |  0.0089 |  -0.0059 | -0.0360 |  0.0383 |
| period_group | 2016-2022 | spy_60d_return          |              7 | -0.0606 |  -0.0730 | -0.1163 | -0.0046 |
| period_group | 2016-2022 | qqq_20d_return          |              7 |  0.0009 |  -0.0245 | -0.0508 |  0.0413 |
| period_group | 2016-2022 | qqq_60d_return          |              7 | -0.0922 |  -0.1460 | -0.1731 | -0.0121 |
| period_group | 2016-2022 | spy_distance_sma200     |              7 | -0.0741 |  -0.0865 | -0.1083 | -0.0286 |
| period_group | 2016-2022 | qqq_distance_sma200     |              7 | -0.1343 |  -0.1643 | -0.1820 | -0.0768 |
| period_group | 2016-2022 | vix_level               |              7 | 25.4700 |  25.3000 | 24.0300 | 27.2700 |
| period_group | 2016-2022 | previous_20d_return     |              7 | -0.1188 |  -0.1247 | -0.2000 |  0.0132 |
| period_group | 2016-2022 | previous_60d_return     |              7 | -0.3476 |  -0.3652 | -0.5239 | -0.2132 |
| period_group | 2016-2022 | drawdown_from_100d_high |              7 | -0.5758 |  -0.5494 | -0.6845 | -0.4833 |
| period_group | 2023-2026 | spy_20d_return          |             52 |  0.0003 |   0.0039 | -0.0286 |  0.0183 |
| period_group | 2023-2026 | spy_60d_return          |             52 |  0.0258 |   0.0311 |  0.0054 |  0.0584 |
| period_group | 2023-2026 | qqq_20d_return          |             52 | -0.0039 |  -0.0209 | -0.0398 |  0.0165 |
| period_group | 2023-2026 | qqq_60d_return          |             52 |  0.0350 |   0.0244 | -0.0115 |  0.0784 |
| period_group | 2023-2026 | spy_distance_sma200     |             52 |  0.0585 |   0.0731 |  0.0377 |  0.0940 |
| period_group | 2023-2026 | qqq_distance_sma200     |             52 |  0.0703 |   0.0869 |  0.0190 |  0.1178 |
| period_group | 2023-2026 | vix_level               |             52 | 21.0998 |  18.7700 | 16.6200 | 24.9800 |
| period_group | 2023-2026 | previous_20d_return     |             52 | -0.1516 |  -0.1737 | -0.2690 | -0.0540 |
| period_group | 2023-2026 | previous_60d_return     |             52 | -0.1948 |  -0.1928 | -0.3140 | -0.0937 |
| period_group | 2023-2026 | drawdown_from_100d_high |             52 | -0.4025 |  -0.3882 | -0.4840 | -0.3096 |

## Falling-knife diagnostics

SMA slopes are five-session percentage changes in SMA20/SMA50. Consecutive down days are consecutive negative closes through the signal date.

| grouping   | group   | variable              |   observations |    mean |   median |     p25 |     p75 |
|:-----------|:--------|:----------------------|---------------:|--------:|---------:|--------:|--------:|
| outcome    | loser   | previous_5d_return    |             24 | -0.0835 |  -0.0847 | -0.1259 | -0.0435 |
| outcome    | loser   | previous_10d_return   |             24 | -0.1051 |  -0.1119 | -0.1963 | -0.0501 |
| outcome    | loser   | previous_20d_return   |             24 | -0.1458 |  -0.1301 | -0.2492 | -0.0528 |
| outcome    | loser   | distance_sma20        |             24 | -0.1113 |  -0.1227 | -0.1736 | -0.0633 |
| outcome    | loser   | distance_sma50        |             24 | -0.1616 |  -0.1576 | -0.1851 | -0.1083 |
| outcome    | loser   | distance_sma100       |             24 | -0.2041 |  -0.1564 | -0.2188 | -0.1368 |
| outcome    | loser   | sma20_slope           |             24 | -0.0290 |  -0.0213 | -0.0433 | -0.0064 |
| outcome    | loser   | sma50_slope           |             24 | -0.0219 |  -0.0167 | -0.0368 | -0.0088 |
| outcome    | loser   | consecutive_down_days |             24 |  2.2917 |   2.0000 |  1.0000 |  3.0000 |
| outcome    | winner  | previous_5d_return    |             35 | -0.0722 |  -0.1080 | -0.1596 |  0.0318 |
| outcome    | winner  | previous_10d_return   |             35 | -0.1201 |  -0.1459 | -0.2084 | -0.0666 |
| outcome    | winner  | previous_20d_return   |             35 | -0.1490 |  -0.1728 | -0.2701 | -0.0466 |
| outcome    | winner  | distance_sma20        |             35 | -0.1094 |  -0.1072 | -0.1898 | -0.0375 |
| outcome    | winner  | distance_sma50        |             35 | -0.1687 |  -0.1929 | -0.2287 | -0.1037 |
| outcome    | winner  | distance_sma100       |             35 | -0.2093 |  -0.1825 | -0.2429 | -0.1352 |
| outcome    | winner  | sma20_slope           |             35 | -0.0350 |  -0.0335 | -0.0596 | -0.0171 |
| outcome    | winner  | sma50_slope           |             35 | -0.0203 |  -0.0161 | -0.0341 | -0.0010 |
| outcome    | winner  | consecutive_down_days |             35 |  1.7714 |   1.0000 |  0.0000 |  2.0000 |

## Limited neighborhood for positive_5d_momentum

| family            |   window | period    |   total_return |    cagr |   sharpe |   maximum_drawdown |   number_of_trades |   win_rate |
|:------------------|---------:|:----------|---------------:|--------:|---------:|-------------------:|-------------------:|-----------:|
| positive_momentum |        3 | 2016-2022 |        -0.1164 | -0.0176 |  -0.4386 |            -0.1207 |                  7 |     0.2857 |
| positive_momentum |        3 | 2023-2026 |         0.4021 |  0.0981 |   0.4949 |            -0.2285 |                 38 |     0.6053 |
| positive_momentum |        3 | combined  |         0.2389 |  0.0204 |   0.2074 |            -0.2285 |                 45 |     0.5556 |
| positive_momentum |        5 | 2016-2022 |        -0.0689 | -0.0102 |  -0.2839 |            -0.0729 |                  5 |     0.4000 |
| positive_momentum |        5 | 2023-2026 |         0.6422 |  0.1472 |   0.8297 |            -0.1410 |                 37 |     0.5676 |
| positive_momentum |        5 | combined  |         0.5291 |  0.0408 |   0.4121 |            -0.1410 |                 42 |     0.5476 |
| positive_momentum |       10 | 2016-2022 |        -0.0274 | -0.0040 |  -0.0927 |            -0.1001 |                  5 |     0.2000 |
| positive_momentum |       10 | 2023-2026 |         0.5427 |  0.1276 |   0.4625 |            -0.4031 |                 32 |     0.5000 |
| positive_momentum |       10 | combined  |         0.4577 |  0.0362 |   0.2493 |            -0.4031 |                 36 |     0.4722 |

## Research limitations

- This is the same eight-stock current-survivor watchlist; theme and stock-mix conclusions are highly selection-biased.
- Yahoo historical market cap remains sparse/revised and is not institutional point-in-time data.
- The 2016–2022 sample has very few executable trades because several watchlist companies were not public or eligible.
- Confirmation rules were predeclared and the limited neighborhood changes one lookback dimension only.
- No RSI, MACD, machine learning, alternative exit, or OOS-driven threshold search was introduced.
