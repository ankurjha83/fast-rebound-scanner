# Expanded-Universe Retest Report

## Executive conclusion

The point-in-time S&P 500 membership spine materially expands the sample, but Yahoo can price only 659 of 863 historical symbols (76.4%); 204 removed/delisted histories remain unavailable. Results are therefore substantially less survivor-selected than the eight-stock proof of concept, but not fully survivorship-free.

In the strict best-available-cap universe, BASE produces 181 trades across 51 stocks, with 67.01% return, 0.372 Sharpe, and -29.93% drawdown. Positive-5D modestly improves Sharpe and drawdown but lowers total return; in the no-cap sensitivity it underperforms BASE. The QQQ filter improves development drawdown but weakens post-2023 and combined risk-adjusted performance. No result is strong enough for paper trading.

Final decision: **MODIFY AND RETEST**.

## Data coverage before interpretation

- Membership source: [MIT-licensed historical S&P 500 snapshots](https://github.com/fja05680/sp500), 863 unique symbols from 2009–2026.
- Yahoo-covered symbols: 659; persistent missing histories: 204.
- Point-in-time priced member rows: 1,792,648 across 651 tickers.
- No-cap eligible stock-days/tickers: 16,318 / 93.
- Strict-cap eligible stock-days/tickers: 14,342 / 85.
- Strict-cap history begins 2016-01-22 because Yahoo historical shares are unavailable earlier for qualifying names.
- Index membership is point-in-time. Beta, price, and liquidity are historical. No current market cap is used retrospectively.
- Removed securities with missing Yahoo prices cannot contribute final delisting/acquisition returns; this residual coverage bias is material.

## Methodology continuity check

Before expansion, the existing eight-stock pipeline was reproduced without changing its signal timing, 100-day range calculation, next-open execution, exit F, sizing, ranking, or 0.20% round-trip friction. BASE reproduced at 79.48% combined return, 0.313 Sharpe, -42.58% maximum drawdown, and 59 trades. Positive-5D reproduced at 52.91% return, 0.412 Sharpe, -14.10% drawdown, and -6.89% development return. These match the previously reported results within rounding tolerance, so the expanded comparison is methodology-consistent.

## Primary comparison

| universe   | strategy             | period    |   total_return |   cagr |   sharpe |   sortino |   maximum_drawdown |   calmar |   annualized_volatility |   number_of_trades |   unique_tickers |   win_rate |   average_trade_return |   median_trade_return |   average_winner |   average_loser |   profit_factor |   average_mae |   median_mae |   average_mfe |   median_mfe |   average_holding_period |   exposure |   turnover |
|:-----------|:---------------------|:----------|---------------:|-------:|---------:|----------:|-------------------:|---------:|------------------------:|-------------------:|-----------------:|-----------:|-----------------------:|----------------------:|-----------------:|----------------:|----------------:|--------------:|-------------:|--------------:|-------------:|-------------------------:|-----------:|-----------:|
| strict_cap | base                 | 2016-2022 |         0.0633 | 0.0088 |   0.1370 |    0.2087 |            -0.1901 |   0.0464 |                  0.1019 |                 63 |               28 |     0.4762 |                 0.0133 |               -0.0105 |           0.1692 |         -0.1284 |          1.1342 |       -0.1311 |      -0.0892 |        0.1525 |       0.1284 |                  29.2857 |     0.1012 |     1.8482 |
| strict_cap | base                 | 2023+     |         0.6214 | 0.1432 |   0.6591 |    1.1044 |            -0.2993 |   0.4784 |                  0.2511 |                120 |               34 |     0.5750 |                 0.0465 |                0.0250 |           0.1733 |         -0.1252 |          1.8185 |       -0.1338 |      -0.1180 |        0.1845 |       0.1356 |                  28.9250 |     0.3699 |     3.6360 |
| strict_cap | base                 | combined  |         0.6701 | 0.0495 |   0.3715 |    0.5959 |            -0.2993 |   0.1655 |                  0.1679 |                181 |               51 |     0.5414 |                 0.0336 |                0.0237 |           0.1702 |         -0.1277 |          1.5355 |       -0.1340 |      -0.1113 |        0.1732 |       0.1325 |                  29.2873 |     0.1919 |     5.6086 |
| strict_cap | positive_5d          | 2016-2022 |         0.0656 | 0.0091 |   0.1571 |    0.2447 |            -0.1575 |   0.0580 |                  0.0763 |                 42 |               20 |     0.5238 |                 0.0172 |                0.0097 |           0.1308 |         -0.1078 |          1.2870 |       -0.1349 |      -0.1213 |        0.1376 |       0.1024 |                  30.0000 |     0.0686 |     1.0122 |
| strict_cap | positive_5d          | 2023+     |         0.4778 | 0.1142 |   0.6671 |    1.0869 |            -0.2838 |   0.4025 |                  0.1896 |                 85 |               30 |     0.5294 |                 0.0510 |                0.0211 |           0.2095 |         -0.1273 |          1.8025 |       -0.1203 |      -0.0885 |        0.1935 |       0.1470 |                  28.1647 |     0.2605 |     2.8848 |
| strict_cap | positive_5d          | combined  |         0.5811 | 0.0441 |   0.4046 |    0.6412 |            -0.2838 |   0.1555 |                  0.1266 |                127 |               42 |     0.5276 |                 0.0402 |                0.0136 |           0.1843 |         -0.1208 |          1.6714 |       -0.1256 |      -0.0906 |        0.1744 |       0.1284 |                  28.7717 |     0.1337 |     4.1965 |
| strict_cap | positive_5d_qqq_bull | 2016-2022 |         0.0787 | 0.0109 |   0.3347 |    0.5166 |            -0.0425 |   0.2564 |                  0.0341 |                 22 |               16 |     0.6818 |                 0.0352 |                0.0272 |           0.1013 |         -0.1064 |          2.0362 |       -0.1027 |      -0.0562 |        0.1267 |       0.0724 |                  30.0000 |     0.0362 |     0.4471 |
| strict_cap | positive_5d_qqq_bull | 2023+     |         0.2312 | 0.0593 |   0.4564 |    0.7146 |            -0.2393 |   0.2477 |                  0.1521 |                 75 |               28 |     0.5333 |                 0.0312 |                0.0132 |           0.1752 |         -0.1333 |          1.4606 |       -0.1188 |      -0.0885 |        0.1747 |       0.1320 |                  27.9200 |     0.2270 |     2.3742 |
| strict_cap | positive_5d_qqq_bull | combined  |         0.3281 | 0.0271 |   0.3351 |    0.5068 |            -0.2393 |   0.1133 |                  0.0929 |                 97 |               38 |     0.5670 |                 0.0321 |                0.0154 |           0.1551 |         -0.1288 |          1.5314 |       -0.1152 |      -0.0877 |        0.1638 |       0.1195 |                  28.3918 |     0.1011 |     2.9375 |
| no_cap     | base                 | 2016-2022 |         0.2895 | 0.0371 |   0.3104 |    0.4794 |            -0.2234 |   0.1659 |                  0.1564 |                 86 |               35 |     0.5349 |                 0.0336 |                0.0295 |           0.1714 |         -0.1249 |          1.4718 |       -0.1414 |      -0.0932 |        0.1889 |       0.1403 |                  29.4767 |     0.1394 |     2.6354 |
| no_cap     | base                 | 2023+     |         0.4580 | 0.1101 |   0.5415 |    0.8683 |            -0.3224 |   0.3414 |                  0.2522 |                129 |               36 |     0.5736 |                 0.0428 |                0.0268 |           0.1681 |         -0.1257 |          1.7459 |       -0.1310 |      -0.1115 |        0.1750 |       0.1447 |                  29.1318 |     0.4048 |     3.7738 |
| no_cap     | base                 | combined  |         0.7806 | 0.0353 |   0.3015 |    0.4615 |            -0.3224 |   0.1096 |                  0.1551 |                214 |               58 |     0.5561 |                 0.0367 |                0.0278 |           0.1678 |         -0.1275 |          1.5907 |       -0.1366 |      -0.1084 |        0.1807 |       0.1432 |                  29.4766 |     0.1469 |     7.1113 |
| no_cap     | positive_5d          | 2016-2022 |         0.1581 | 0.0212 |   0.2561 |    0.4052 |            -0.1936 |   0.1097 |                  0.1024 |                 59 |               27 |     0.5254 |                 0.0277 |                0.0125 |           0.1554 |         -0.1137 |          1.4583 |       -0.1334 |      -0.1102 |        0.1586 |       0.1157 |                  30.0000 |     0.0970 |     1.6226 |
| no_cap     | positive_5d          | 2023+     |         0.3383 | 0.0840 |   0.5064 |    0.7802 |            -0.3340 |   0.2516 |                  0.1994 |                 94 |               33 |     0.5638 |                 0.0469 |                0.0317 |           0.1853 |         -0.1320 |          1.7965 |       -0.1201 |      -0.0900 |        0.1870 |       0.1471 |                  28.3404 |     0.2927 |     2.9835 |
| no_cap     | positive_5d          | combined  |         0.5214 | 0.0256 |   0.2786 |    0.4203 |            -0.3340 |   0.0766 |                  0.1143 |                154 |               48 |     0.5455 |                 0.0381 |                0.0198 |           0.1748 |         -0.1260 |          1.6480 |       -0.1264 |      -0.0927 |        0.1760 |       0.1338 |                  28.9870 |     0.1051 |     5.0556 |
| no_cap     | positive_5d_qqq_bull | 2016-2022 |         0.0738 | 0.0102 |   0.2260 |    0.3432 |            -0.0952 |   0.1077 |                  0.0508 |                 32 |               21 |     0.6250 |                 0.0230 |                0.0260 |           0.1112 |         -0.1240 |          1.4865 |       -0.1161 |      -0.1007 |        0.1360 |       0.0815 |                  30.0000 |     0.0526 |     0.7329 |
| no_cap     | positive_5d_qqq_bull | 2023+     |         0.1025 | 0.0274 |   0.2443 |    0.3593 |            -0.3126 |   0.0876 |                  0.1725 |                 85 |               31 |     0.5647 |                 0.0269 |                0.0185 |           0.1542 |         -0.1383 |          1.4275 |       -0.1213 |      -0.0905 |        0.1677 |       0.1320 |                  28.1647 |     0.2617 |     2.4943 |
| no_cap     | positive_5d_qqq_bull | combined  |         0.1839 | 0.0102 |   0.1610 |    0.2282 |            -0.3126 |   0.0327 |                  0.0868 |                117 |               44 |     0.5812 |                 0.0258 |                0.0185 |           0.1416 |         -0.1348 |          1.4407 |       -0.1198 |      -0.0905 |        0.1591 |       0.1195 |                  28.6667 |     0.0790 |     3.2593 |

## Explicit answers

1. **Did expansion materially increase sample size?** **Yes:** strict BASE rises from 59 trades/eight proof-of-concept names to 181 trades/51 traded names, with 14,342 eligible stock-days. It is still a moderate, not massive, trade sample.
2. **Does BASE show a broad-universe edge?** **Weakly positive, not compelling.** Strict development return is 6.33%, combined Sharpe 0.372, and drawdown -29.93%. The no-cap combined Sharpe is 0.302.
3. **Does Positive-5D improve BASE broadly?** **Not consistently.** Strict Sharpe rises from 0.372 to 0.405 and drawdown improves from -29.93% to -28.38%, but return falls. In no-cap, Sharpe falls from 0.302 to 0.279 and drawdown worsens.
4. **Does improvement exist before 2023?** Strict development return is 6.56% versus BASE 6.33%; Sharpe improves only slightly. No-cap development performance is worse with confirmation.
5. **Does Positive-5D materially reduce drawdown?** **Only modestly in strict-cap** (-29.93% to -28.38%) and not in no-cap.
6. **Does it improve Sharpe?** Strict: 0.372 to 0.405. No-cap: 0.302 to 0.279. This is not cross-method confirmation.
7. **Is it diversified across stocks?** Strict BASE uses 51 stocks, but the top three account for 25.97% of positive P&L. See full concentration tables.
8. **Dependent on a few themes?** Sector/theme contributions are reported below. Unclassified removed companies remain explicit; no speculative theme is assigned without evidence.
9. **Are 3D/5D/10D results similar?** Broadly yes in development; 3/3 strict development variants are positive.
10. **Does it work mainly above QQQ SMA200?** Positive-5D average trade return is 3.21% in bull versus 9.08% in bear observations.
11. **Does the QQQ filter improve development?** Return 6.56% to 7.87%, Sharpe 0.157 to 0.335, and drawdown -15.75% to -4.25%. It improves development risk metrics.
12. **Enough QQQ-filtered trades?** 97 combined and 22 development trades are usable diagnostically, but thin for a definitive strategy claim.
13. **Any strategy above the 95th random percentile?** Yes. See the random table below; 80th–90th percentile is not treated as alpha.
14. **Mean returns distinguishable from zero?** Strict ticker-cluster BASE 95% CI is [1.04%, 5.55%]; Positive-5D is [1.11%, 6.84%].
15. **Positive under ticker resampling?** **Yes for every strict primary strategy**.
16. **Do top-winner removals destroy results?** Exact counterfactual sensitivity is below. Material degradation indicates winner dependence even when the sign remains positive.
17. **Stable across years?** Strict profitable-year counts: base 8/11, positive_5d 8/11, positive_5d_qqq_bull 8/11. Stability remains mixed.
18. **Best description?** **Regime-dependent pullback buying / momentum-confirmed mean reversion**, not generic mean reversion. QQQ trend helps development safety but does not improve the full sample consistently.
19. **Simplest supported rule?** **BASE** is the most consistently supported across strict and no-cap versions. Positive-5D is a risk-control candidate, not established alpha enhancement.
20. **Decision?** **MODIFY AND RETEST**. The larger cross-section justifies continued data-quality work and retesting, not live deployment.

## Sample size

| universe   | strategy             | period    |   eligible_stock_days |   qualifying_signals |   signal_tickers |   trades |   trades_per_year |
|:-----------|:---------------------|:----------|----------------------:|---------------------:|-----------------:|---------:|------------------:|
| strict_cap | base                 | 2016-2022 |                  4660 |                  779 |               28 |       63 |             9.003 |
| strict_cap | base                 | 2023+     |                  9682 |                 1978 |               38 |      120 |            30.021 |
| strict_cap | base                 | combined  |                 14342 |                 2757 |               55 |      181 |            16.458 |
| strict_cap | positive_5d          | 2016-2022 |                  4660 |                  297 |               21 |       42 |             6.002 |
| strict_cap | positive_5d          | 2023+     |                  9682 |                  558 |               30 |       85 |            21.265 |
| strict_cap | positive_5d          | combined  |                 14342 |                  858 |               42 |      127 |            11.548 |
| strict_cap | positive_5d_qqq_bull | 2016-2022 |                  4660 |                  116 |               16 |       22 |             3.144 |
| strict_cap | positive_5d_qqq_bull | 2023+     |                  9682 |                  444 |               28 |       75 |            18.763 |
| strict_cap | positive_5d_qqq_bull | combined  |                 14342 |                  560 |               38 |       97 |             8.820 |
| no_cap     | base                 | 2016-2022 |                  5777 |                 1103 |               37 |       86 |            12.289 |
| no_cap     | base                 | 2023+     |                 10517 |                 2286 |               40 |      129 |            32.272 |
| no_cap     | base                 | combined  |                 16318 |                 3390 |               62 |      214 |            12.591 |
| no_cap     | positive_5d          | 2016-2022 |                  5777 |                  396 |               28 |       59 |             8.431 |
| no_cap     | positive_5d          | 2023+     |                 10517 |                  650 |               34 |       94 |            23.516 |
| no_cap     | positive_5d          | combined  |                 16318 |                 1050 |               48 |      154 |             9.061 |
| no_cap     | positive_5d_qqq_bull | 2016-2022 |                  5777 |                  170 |               21 |       32 |             4.573 |
| no_cap     | positive_5d_qqq_bull | 2023+     |                 10517 |                  536 |               32 |       85 |            21.265 |
| no_cap     | positive_5d_qqq_bull | combined  |                 16318 |                  706 |               44 |      117 |             6.884 |

## Concentration

| universe   | strategy             |   median_trades_per_ticker |   top_1_pnl_share |   top_3_pnl_share |   top_5_pnl_share |   top_10_pnl_share |
|:-----------|:---------------------|---------------------------:|------------------:|------------------:|------------------:|-------------------:|
| strict_cap | base                 |                     2.0000 |            0.1306 |            0.2597 |            0.3854 |             0.6556 |
| strict_cap | positive_5d          |                     2.0000 |            0.1190 |            0.3423 |            0.5230 |             0.8412 |
| strict_cap | positive_5d_qqq_bull |                     2.0000 |            0.1367 |            0.3721 |            0.5671 |             0.8498 |
| no_cap     | base                 |                     2.0000 |            0.1069 |            0.2585 |            0.3714 |             0.6001 |
| no_cap     | positive_5d          |                     2.0000 |            0.1237 |            0.3018 |            0.4545 |             0.7482 |
| no_cap     | positive_5d_qqq_bull |                     2.0000 |            0.1388 |            0.3570 |            0.5240 |             0.7836 |

## Removal sensitivity

| universe   | strategy             | sensitivity             |   total_return |    cagr |   sharpe |   maximum_drawdown |   number_of_trades |
|:-----------|:---------------------|:------------------------|---------------:|--------:|---------:|-------------------:|-------------------:|
| strict_cap | base                 | base                    |         0.6701 |  0.0495 |   0.3715 |            -0.2993 |                181 |
| strict_cap | base                 | remove_best_trade       |         0.6114 |  0.0460 |   0.3513 |            -0.3050 |                180 |
| strict_cap | base                 | remove_best_5_trades    |         0.3746 |  0.0304 |   0.2648 |            -0.3442 |                177 |
| strict_cap | base                 | remove_top_10pct_trades |        -0.1229 | -0.0123 |  -0.0031 |            -0.4293 |                166 |
| strict_cap | base                 | remove_best_stock       |         0.3981 |  0.0321 |   0.2781 |            -0.3075 |                161 |
| strict_cap | base                 | remove_best_3_stocks    |         0.3402 |  0.0280 |   0.2564 |            -0.2975 |                154 |
| strict_cap | positive_5d          | base                    |         0.5811 |  0.0441 |   0.4046 |            -0.2838 |                127 |
| strict_cap | positive_5d          | remove_best_trade       |         0.5034 |  0.0392 |   0.3676 |            -0.2838 |                126 |
| strict_cap | positive_5d          | remove_best_5_trades    |         0.2401 |  0.0205 |   0.2262 |            -0.2838 |                122 |
| strict_cap | positive_5d          | remove_top_10pct_trades |        -0.0390 | -0.0037 |   0.0276 |            -0.3224 |                115 |
| strict_cap | positive_5d          | remove_best_stock       |         0.4287 |  0.0342 |   0.3512 |            -0.2460 |                111 |
| strict_cap | positive_5d          | remove_best_3_stocks    |         0.2385 |  0.0204 |   0.2485 |            -0.1912 |                100 |
| strict_cap | positive_5d_qqq_bull | base                    |         0.3281 |  0.0271 |   0.3351 |            -0.2393 |                 97 |
| strict_cap | positive_5d_qqq_bull | remove_best_trade       |         0.2629 |  0.0222 |   0.2847 |            -0.2393 |                 96 |
| strict_cap | positive_5d_qqq_bull | remove_best_5_trades    |         0.0606 |  0.0056 |   0.1071 |            -0.2457 |                 92 |
| strict_cap | positive_5d_qqq_bull | remove_top_10pct_trades |        -0.0915 | -0.0090 |  -0.0654 |            -0.2632 |                 87 |
| strict_cap | positive_5d_qqq_bull | remove_best_stock       |         0.2451 |  0.0209 |   0.2719 |            -0.2393 |                 93 |
| strict_cap | positive_5d_qqq_bull | remove_best_3_stocks    |         0.1065 |  0.0096 |   0.1652 |            -0.1791 |                 76 |
| no_cap     | base                 | base                    |         0.7806 |  0.0353 |   0.3015 |            -0.3224 |                214 |
| no_cap     | base                 | remove_best_trade       |         0.7217 |  0.0333 |   0.2881 |            -0.3278 |                214 |
| no_cap     | base                 | remove_best_5_trades    |         0.4779 |  0.0238 |   0.2299 |            -0.3413 |                211 |
| no_cap     | base                 | remove_top_10pct_trades |        -0.0243 | -0.0015 |   0.0645 |            -0.4266 |                198 |
| no_cap     | base                 | remove_best_stock       |         0.5915 |  0.0284 |   0.2594 |            -0.3615 |                210 |
| no_cap     | base                 | remove_best_3_stocks    |         0.3109 |  0.0164 |   0.1875 |            -0.3622 |                182 |
| no_cap     | positive_5d          | base                    |         0.5214 |  0.0256 |   0.2786 |            -0.3340 |                154 |
| no_cap     | positive_5d          | remove_best_trade       |         0.4393 |  0.0222 |   0.2503 |            -0.3340 |                153 |
| no_cap     | positive_5d          | remove_best_5_trades    |         0.1814 |  0.0101 |   0.1461 |            -0.3360 |                149 |
| no_cap     | positive_5d          | remove_top_10pct_trades |        -0.1885 | -0.0125 |  -0.0644 |            -0.4226 |                139 |
| no_cap     | positive_5d          | remove_best_stock       |         0.4118 |  0.0210 |   0.2469 |            -0.3116 |                140 |
| no_cap     | positive_5d          | remove_best_3_stocks    |         0.2217 |  0.0121 |   0.1687 |            -0.3006 |                133 |
| no_cap     | positive_5d_qqq_bull | base                    |         0.1839 |  0.0102 |   0.1610 |            -0.3126 |                117 |
| no_cap     | positive_5d_qqq_bull | remove_best_trade       |         0.1246 |  0.0071 |   0.1255 |            -0.3146 |                116 |
| no_cap     | positive_5d_qqq_bull | remove_best_5_trades    |        -0.0548 | -0.0034 |   0.0015 |            -0.3204 |                112 |
| no_cap     | positive_5d_qqq_bull | remove_top_10pct_trades |        -0.2293 | -0.0156 |  -0.1568 |            -0.3395 |                105 |
| no_cap     | positive_5d_qqq_bull | remove_best_stock       |         0.1090 |  0.0062 |   0.1162 |            -0.3264 |                113 |
| no_cap     | positive_5d_qqq_bull | remove_best_3_stocks    |         0.0068 |  0.0004 |   0.0450 |            -0.3038 |                101 |

## Sector contribution — strict BASE

| sector                 |   total_pnl_contribution |   trade_count |   average_trade |   median_trade |   win_rate |     mae |    mfe |
|:-----------------------|-------------------------:|--------------:|----------------:|---------------:|-----------:|--------:|-------:|
| Information Technology |               34944.9446 |           103 |          0.0310 |        -0.0034 |     0.4951 | -0.1410 | 0.1750 |
| Industrials            |               13323.5737 |             8 |          0.1359 |         0.1536 |     0.8750 | -0.0493 | 0.2162 |
| Utilities              |                6897.9783 |             2 |          0.3599 |         0.3599 |     1.0000 | -0.0760 | 0.4114 |
| Unclassified / removed |                5404.9560 |            17 |          0.0327 |         0.0305 |     0.6471 | -0.1277 | 0.1790 |
| Consumer Discretionary |                4661.4879 |            23 |          0.0138 |         0.0268 |     0.6087 | -0.1330 | 0.1532 |
| Financials             |                3570.6293 |            15 |          0.0226 |         0.0661 |     0.6000 | -0.1294 | 0.1639 |
| Materials              |                1400.1337 |             7 |          0.0210 |        -0.0479 |     0.4286 | -0.1024 | 0.1634 |
| Energy                 |               -3192.3715 |             6 |         -0.0470 |        -0.0156 |     0.1667 | -0.2178 | 0.1012 |

## Theme contribution — strict BASE

| theme               |   total_pnl_contribution |   trade_count |   average_trade |   median_trade |   win_rate |     mae |    mfe |
|:--------------------|-------------------------:|--------------:|----------------:|---------------:|-----------:|--------:|-------:|
| semiconductors / AI |               26633.8647 |            79 |          0.0323 |        -0.0040 |     0.4937 | -0.1244 | 0.1622 |
| other               |               25215.0514 |            51 |          0.0453 |         0.0319 |     0.5882 | -0.1465 | 0.2053 |
| industrial          |               13323.5737 |             8 |          0.1359 |         0.1536 |     0.8750 | -0.0493 | 0.2162 |
| consumer            |                4661.4879 |            23 |          0.0138 |         0.0268 |     0.6087 | -0.1330 | 0.1532 |
| fintech             |                4472.3293 |             5 |          0.0608 |         0.0661 |     0.6000 | -0.1505 | 0.2330 |
| software            |               -3341.0500 |             9 |         -0.0249 |        -0.0291 |     0.3333 | -0.1845 | 0.0849 |
| crypto-linked       |               -3953.9250 |             6 |         -0.0440 |        -0.0541 |     0.3333 | -0.1827 | 0.1480 |

## Momentum neighborhood

| universe   |   window | period    |   total_return |   cagr |   sharpe |   sortino |   maximum_drawdown |   number_of_trades |   win_rate |   average_trade_return |
|:-----------|---------:|:----------|---------------:|-------:|---------:|----------:|-------------------:|-------------------:|-----------:|-----------------------:|
| strict_cap |        3 | 2016-2022 |         0.0192 | 0.0027 |   0.0740 |    0.1122 |            -0.2059 |                 48 |     0.5000 |                 0.0075 |
| strict_cap |        3 | 2023+     |         0.6384 | 0.1465 |   0.7490 |    1.2561 |            -0.2886 |                 96 |     0.5938 |                 0.0579 |
| strict_cap |        3 | combined  |         0.6522 | 0.0485 |   0.4080 |    0.6564 |            -0.2886 |                142 |     0.5634 |                 0.0409 |
| strict_cap |        5 | 2016-2022 |         0.0656 | 0.0091 |   0.1571 |    0.2447 |            -0.1575 |                 42 |     0.5238 |                 0.0172 |
| strict_cap |        5 | 2023+     |         0.4778 | 0.1142 |   0.6671 |    1.0869 |            -0.2838 |                 85 |     0.5294 |                 0.0510 |
| strict_cap |        5 | combined  |         0.5811 | 0.0441 |   0.4046 |    0.6412 |            -0.2838 |                127 |     0.5276 |                 0.0402 |
| strict_cap |       10 | 2016-2022 |         0.1308 | 0.0178 |   0.2742 |    0.4434 |            -0.1017 |                 37 |     0.6486 |                 0.0353 |
| strict_cap |       10 | 2023+     |         0.3840 | 0.0942 |   0.5992 |    0.9850 |            -0.2984 |                 77 |     0.5714 |                 0.0479 |
| strict_cap |       10 | combined  |         0.5651 | 0.0431 |   0.4139 |    0.6670 |            -0.2984 |                114 |     0.5965 |                 0.0438 |
| no_cap     |        3 | 2016-2022 |         0.0920 | 0.0127 |   0.1716 |    0.2634 |            -0.2394 |                 65 |     0.5231 |                 0.0172 |
| no_cap     |        3 | 2023+     |         0.6442 | 0.1476 |   0.7167 |    1.1636 |            -0.3030 |                104 |     0.6058 |                 0.0639 |
| no_cap     |        3 | combined  |         0.7368 | 0.0338 |   0.3250 |    0.5027 |            -0.3030 |                168 |     0.5714 |                 0.0442 |
| no_cap     |        5 | 2016-2022 |         0.1581 | 0.0212 |   0.2561 |    0.4052 |            -0.1936 |                 59 |     0.5254 |                 0.0277 |
| no_cap     |        5 | 2023+     |         0.3383 | 0.0840 |   0.5064 |    0.7802 |            -0.3340 |                 94 |     0.5638 |                 0.0469 |
| no_cap     |        5 | combined  |         0.5214 | 0.0256 |   0.2786 |    0.4203 |            -0.3340 |                154 |     0.5455 |                 0.0381 |
| no_cap     |       10 | 2016-2022 |         0.1326 | 0.0180 |   0.2353 |    0.3665 |            -0.1289 |                 49 |     0.6122 |                 0.0281 |
| no_cap     |       10 | 2023+     |         0.2444 | 0.0624 |   0.4202 |    0.6449 |            -0.3610 |                 84 |     0.5833 |                 0.0434 |
| no_cap     |       10 | combined  |         0.3779 | 0.0195 |   0.2350 |    0.3531 |            -0.3610 |                134 |     0.5896 |                 0.0358 |

## QQQ/SPY regime analysis

| universe   | strategy    | benchmark   | regime   |   total_return |   cagr |   sharpe |   maximum_drawdown |   number_of_trades |   win_rate |   average_trade_return |   median_trade_return |
|:-----------|:------------|:------------|:---------|---------------:|-------:|---------:|-------------------:|-------------------:|-----------:|-----------------------:|----------------------:|
| strict_cap | base        | QQQ         | bull     |         0.4168 | 0.0334 |   0.3118 |            -0.2973 |                146 |     0.5411 |                 0.0274 |                0.0210 |
| strict_cap | base        | QQQ         | bear     |         0.3981 | 0.0321 |   0.3084 |            -0.2654 |                 63 |     0.5079 |                 0.0701 |                0.0112 |
| strict_cap | base        | SPY         | bull     |         0.2727 | 0.0230 |   0.2329 |            -0.3057 |                149 |     0.5101 |                 0.0196 |                0.0033 |
| strict_cap | base        | SPY         | bear     |         0.6231 | 0.0467 |   0.4232 |            -0.2419 |                 67 |     0.5522 |                 0.0844 |                0.0389 |
| strict_cap | positive_5d | QQQ         | bull     |         0.3281 | 0.0271 |   0.3351 |            -0.2393 |                 97 |     0.5670 |                 0.0321 |                0.0154 |
| strict_cap | positive_5d | QQQ         | bear     |         0.4621 | 0.0365 |   0.3910 |            -0.2202 |                 47 |     0.5319 |                 0.0908 |                0.0459 |
| strict_cap | positive_5d | SPY         | bull     |         0.2525 | 0.0214 |   0.2617 |            -0.2830 |                100 |     0.5500 |                 0.0251 |                0.0145 |
| strict_cap | positive_5d | SPY         | bear     |         0.6154 | 0.0462 |   0.5026 |            -0.1892 |                 48 |     0.5625 |                 0.1090 |                0.0462 |
| no_cap     | base        | QQQ         | bull     |         0.4054 | 0.0207 |   0.2353 |            -0.3427 |                169 |     0.5562 |                 0.0292 |                0.0268 |
| no_cap     | base        | QQQ         | bear     |         0.5805 | 0.0279 |   0.2838 |            -0.2453 |                 75 |     0.5200 |                 0.0766 |                0.0112 |
| no_cap     | base        | SPY         | bull     |         0.2039 | 0.0112 |   0.1542 |            -0.3800 |                170 |     0.5353 |                 0.0199 |                0.0214 |
| no_cap     | base        | SPY         | bear     |         0.9132 | 0.0398 |   0.3783 |            -0.2419 |                 81 |     0.5679 |                 0.0926 |                0.0499 |
| no_cap     | positive_5d | QQQ         | bull     |         0.1839 | 0.0102 |   0.1610 |            -0.3126 |                117 |     0.5812 |                 0.0258 |                0.0185 |
| no_cap     | positive_5d | QQQ         | bear     |         0.5506 | 0.0268 |   0.3303 |            -0.2202 |                 56 |     0.5179 |                 0.0879 |                0.0414 |
| no_cap     | positive_5d | SPY         | bull     |         0.1177 | 0.0067 |   0.1191 |            -0.3522 |                120 |     0.5667 |                 0.0201 |                0.0176 |
| no_cap     | positive_5d | SPY         | bear     |         0.7082 | 0.0328 |   0.4130 |            -0.1900 |                 55 |     0.5455 |                 0.1063 |                0.0459 |

## Matched random control

The calendar-sleeve control matches ticker, holding period, approximate count, eligibility dates, costs, and a ten-position cap. It is an approximation to exact ranking/cash accounting.

| universe   | strategy             |   simulations |   actual_matched_total_return |   total_return_percentile |   actual_matched_sharpe |   sharpe_percentile |   actual_matched_max_drawdown |   drawdown_percentile |
|:-----------|:---------------------|--------------:|------------------------------:|--------------------------:|------------------------:|--------------------:|------------------------------:|----------------------:|
| strict_cap | base                 |          1000 |                         0.760 |                    98.800 |                   0.399 |              96.500 |                        -0.300 |                42.100 |
| strict_cap | positive_5d          |          1000 |                         0.624 |                    90.700 |                   0.421 |              82.000 |                        -0.289 |                10.500 |
| strict_cap | positive_5d_qqq_bull |          1000 |                         0.351 |                    84.100 |                   0.352 |              83.100 |                        -0.243 |                21.400 |
| no_cap     | base                 |          1000 |                         1.200 |                    99.800 |                   0.381 |              98.100 |                        -0.270 |                70.200 |
| no_cap     | positive_5d          |          1000 |                         0.756 |                    94.600 |                   0.362 |              87.600 |                        -0.260 |                26.800 |
| no_cap     | positive_5d_qqq_bull |          1000 |                         0.352 |                    87.200 |                   0.263 |              85.800 |                        -0.239 |                33.200 |

## Bootstrap 95% confidence intervals

| universe   | strategy             | method         | metric        |   estimate |   ci_lower |   ci_upper |   simulations | label                                          |
|:-----------|:---------------------|:---------------|:--------------|-----------:|-----------:|-----------:|--------------:|:-----------------------------------------------|
| strict_cap | base                 | trade          | mean_return   |     0.0336 |     0.0043 |     0.0624 |          5000 | strict_cap base trade                          |
| strict_cap | base                 | trade          | median_return |     0.0237 |    -0.0115 |     0.0414 |          5000 | strict_cap base trade                          |
| strict_cap | base                 | trade          | win_rate      |     0.5414 |     0.4696 |     0.6133 |          5000 | strict_cap base trade                          |
| strict_cap | base                 | trade          | profit_factor |     1.5736 |     1.0601 |     2.3157 |          5000 | strict_cap base trade                          |
| strict_cap | base                 | ticker_cluster | mean_return   |     0.0336 |     0.0104 |     0.0555 |          5000 | strict_cap base ticker_cluster                 |
| strict_cap | base                 | ticker_cluster | median_return |     0.0237 |    -0.0077 |     0.0407 |          5000 | strict_cap base ticker_cluster                 |
| strict_cap | base                 | ticker_cluster | win_rate      |     0.5414 |     0.4774 |     0.6062 |          5000 | strict_cap base ticker_cluster                 |
| strict_cap | base                 | ticker_cluster | profit_factor |     1.5736 |     1.1581 |     2.0837 |          5000 | strict_cap base ticker_cluster                 |
| strict_cap | positive_5d          | trade          | mean_return   |     0.0402 |     0.0063 |     0.0752 |          5000 | strict_cap positive_5d trade                   |
| strict_cap | positive_5d          | trade          | median_return |     0.0136 |    -0.0338 |     0.0662 |          5000 | strict_cap positive_5d trade                   |
| strict_cap | positive_5d          | trade          | win_rate      |     0.5276 |     0.4409 |     0.6142 |          5000 | strict_cap positive_5d trade                   |
| strict_cap | positive_5d          | trade          | profit_factor |     1.7039 |     1.0891 |     2.6717 |          5000 | strict_cap positive_5d trade                   |
| strict_cap | positive_5d          | ticker_cluster | mean_return   |     0.0402 |     0.0111 |     0.0684 |          5000 | strict_cap positive_5d ticker_cluster          |
| strict_cap | positive_5d          | ticker_cluster | median_return |     0.0136 |    -0.0338 |     0.0543 |          5000 | strict_cap positive_5d ticker_cluster          |
| strict_cap | positive_5d          | ticker_cluster | win_rate      |     0.5276 |     0.4386 |     0.6117 |          5000 | strict_cap positive_5d ticker_cluster          |
| strict_cap | positive_5d          | ticker_cluster | profit_factor |     1.7039 |     1.1760 |     2.3869 |          5000 | strict_cap positive_5d ticker_cluster          |
| strict_cap | positive_5d_qqq_bull | trade          | mean_return   |     0.0321 |    -0.0045 |     0.0694 |          5000 | strict_cap positive_5d_qqq_bull trade          |
| strict_cap | positive_5d_qqq_bull | trade          | median_return |     0.0154 |    -0.0338 |     0.0561 |          5000 | strict_cap positive_5d_qqq_bull trade          |
| strict_cap | positive_5d_qqq_bull | trade          | win_rate      |     0.5670 |     0.4742 |     0.6701 |          5000 | strict_cap positive_5d_qqq_bull trade          |
| strict_cap | positive_5d_qqq_bull | trade          | profit_factor |     1.5761 |     0.9361 |     2.6656 |          5000 | strict_cap positive_5d_qqq_bull trade          |
| strict_cap | positive_5d_qqq_bull | ticker_cluster | mean_return   |     0.0321 |     0.0000 |     0.0612 |          5000 | strict_cap positive_5d_qqq_bull ticker_cluster |
| strict_cap | positive_5d_qqq_bull | ticker_cluster | median_return |     0.0154 |    -0.0166 |     0.0518 |          5000 | strict_cap positive_5d_qqq_bull ticker_cluster |
| strict_cap | positive_5d_qqq_bull | ticker_cluster | win_rate      |     0.5670 |     0.4688 |     0.6591 |          5000 | strict_cap positive_5d_qqq_bull ticker_cluster |
| strict_cap | positive_5d_qqq_bull | ticker_cluster | profit_factor |     1.5761 |     1.0004 |     2.3300 |          5000 | strict_cap positive_5d_qqq_bull ticker_cluster |
| no_cap     | base                 | trade          | mean_return   |     0.0367 |     0.0109 |     0.0622 |          5000 | no_cap base trade                              |
| no_cap     | base                 | trade          | median_return |     0.0278 |    -0.0058 |     0.0572 |          5000 | no_cap base trade                              |
| no_cap     | base                 | trade          | win_rate      |     0.5561 |     0.4907 |     0.6215 |          5000 | no_cap base trade                              |
| no_cap     | base                 | trade          | profit_factor |     1.6487 |     1.1609 |     2.3344 |          5000 | no_cap base trade                              |
| no_cap     | base                 | ticker_cluster | mean_return   |     0.0367 |     0.0166 |     0.0559 |          5000 | no_cap base ticker_cluster                     |
| no_cap     | base                 | ticker_cluster | median_return |     0.0278 |    -0.0040 |     0.0524 |          5000 | no_cap base ticker_cluster                     |
| no_cap     | base                 | ticker_cluster | win_rate      |     0.5561 |     0.4942 |     0.6182 |          5000 | no_cap base ticker_cluster                     |
| no_cap     | base                 | ticker_cluster | profit_factor |     1.6487 |     1.2574 |     2.1708 |          5000 | no_cap base ticker_cluster                     |
| no_cap     | positive_5d          | trade          | mean_return   |     0.0381 |     0.0078 |     0.0685 |          5000 | no_cap positive_5d trade                       |
| no_cap     | positive_5d          | trade          | median_return |     0.0198 |    -0.0182 |     0.0538 |          5000 | no_cap positive_5d trade                       |
| no_cap     | positive_5d          | trade          | win_rate      |     0.5455 |     0.4675 |     0.6234 |          5000 | no_cap positive_5d trade                       |
| no_cap     | positive_5d          | trade          | profit_factor |     1.6647 |     1.1115 |     2.4977 |          5000 | no_cap positive_5d trade                       |
| no_cap     | positive_5d          | ticker_cluster | mean_return   |     0.0381 |     0.0116 |     0.0625 |          5000 | no_cap positive_5d ticker_cluster              |
| no_cap     | positive_5d          | ticker_cluster | median_return |     0.0198 |    -0.0182 |     0.0518 |          5000 | no_cap positive_5d ticker_cluster              |
| no_cap     | positive_5d          | ticker_cluster | win_rate      |     0.5455 |     0.4636 |     0.6164 |          5000 | no_cap positive_5d ticker_cluster              |
| no_cap     | positive_5d          | ticker_cluster | profit_factor |     1.6647 |     1.1779 |     2.2769 |          5000 | no_cap positive_5d ticker_cluster              |
| no_cap     | positive_5d_qqq_bull | trade          | mean_return   |     0.0258 |    -0.0065 |     0.0580 |          5000 | no_cap positive_5d_qqq_bull trade              |
| no_cap     | positive_5d_qqq_bull | trade          | median_return |     0.0185 |    -0.0143 |     0.0518 |          5000 | no_cap positive_5d_qqq_bull trade              |
| no_cap     | positive_5d_qqq_bull | trade          | win_rate      |     0.5812 |     0.4872 |     0.6667 |          5000 | no_cap positive_5d_qqq_bull trade              |
| no_cap     | positive_5d_qqq_bull | trade          | profit_factor |     1.4571 |     0.9085 |     2.3731 |          5000 | no_cap positive_5d_qqq_bull trade              |
| no_cap     | positive_5d_qqq_bull | ticker_cluster | mean_return   |     0.0258 |     0.0003 |     0.0501 |          5000 | no_cap positive_5d_qqq_bull ticker_cluster     |
| no_cap     | positive_5d_qqq_bull | ticker_cluster | median_return |     0.0185 |    -0.0096 |     0.0508 |          5000 | no_cap positive_5d_qqq_bull ticker_cluster     |
| no_cap     | positive_5d_qqq_bull | ticker_cluster | win_rate      |     0.5812 |     0.4954 |     0.6591 |          5000 | no_cap positive_5d_qqq_bull ticker_cluster     |
| no_cap     | positive_5d_qqq_bull | ticker_cluster | profit_factor |     1.4571 |     1.0050 |     2.0942 |          5000 | no_cap positive_5d_qqq_bull ticker_cluster     |

## Annual results

| universe   | strategy             |   year |   number_of_trades |   strategy_return |   average_trade_return |   win_rate |   maximum_drawdown |
|:-----------|:---------------------|-------:|-------------------:|------------------:|-----------------------:|-----------:|-------------------:|
| strict_cap | base                 |   2016 |                  2 |            0.0092 |                 0.0462 |     0.5000 |            -0.0476 |
| strict_cap | base                 |   2017 |                 20 |            0.0702 |                 0.0561 |     0.6500 |            -0.0402 |
| strict_cap | base                 |   2018 |                  0 |            0.0336 |               nan      |   nan      |            -0.0048 |
| strict_cap | base                 |   2019 |                  1 |            0.0431 |                 0.4308 |     1.0000 |            -0.0023 |
| strict_cap | base                 |   2020 |                  3 |           -0.0657 |                -0.2218 |     0.0000 |            -0.0933 |
| strict_cap | base                 |   2021 |                  5 |            0.0316 |                 0.0309 |     0.6000 |            -0.0237 |
| strict_cap | base                 |   2022 |                 32 |           -0.0612 |                 0.0060 |     0.4062 |            -0.1901 |
| strict_cap | base                 |   2023 |                  7 |            0.1281 |                 0.1024 |     0.8571 |            -0.0729 |
| strict_cap | base                 |   2024 |                 45 |           -0.0269 |                 0.0070 |     0.5333 |            -0.1772 |
| strict_cap | base                 |   2025 |                 32 |            0.0580 |                 0.0226 |     0.4375 |            -0.2990 |
| strict_cap | base                 |   2026 |                 34 |            0.3334 |                 0.0882 |     0.6765 |            -0.1385 |
| strict_cap | positive_5d          |   2016 |                  2 |            0.0092 |                 0.0462 |     0.5000 |            -0.0476 |
| strict_cap | positive_5d          |   2017 |                 14 |            0.0059 |                 0.0217 |     0.7143 |            -0.0425 |
| strict_cap | positive_5d          |   2018 |                  0 |            0.0150 |               nan      |   nan      |            -0.0194 |
| strict_cap | positive_5d          |   2019 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| strict_cap | positive_5d          |   2020 |                  1 |           -0.0109 |                -0.1091 |     0.0000 |            -0.0258 |
| strict_cap | positive_5d          |   2021 |                  3 |            0.0284 |                 0.0764 |     0.6667 |            -0.0097 |
| strict_cap | positive_5d          |   2022 |                 24 |            0.0071 |                 0.0396 |     0.4583 |            -0.1575 |
| strict_cap | positive_5d          |   2023 |                  3 |            0.2017 |                 0.3667 |     1.0000 |            -0.0149 |
| strict_cap | positive_5d          |   2024 |                 34 |           -0.1287 |                -0.0222 |     0.4706 |            -0.1801 |
| strict_cap | positive_5d          |   2025 |                 21 |            0.1493 |                 0.0597 |     0.4286 |            -0.2144 |
| strict_cap | positive_5d          |   2026 |                 25 |            0.2259 |                 0.0814 |     0.6000 |            -0.1080 |
| strict_cap | positive_5d_qqq_bull |   2016 |                  1 |            0.0102 |                 0.1024 |     1.0000 |            -0.0187 |
| strict_cap | positive_5d_qqq_bull |   2017 |                 14 |            0.0059 |                 0.0217 |     0.7143 |            -0.0425 |
| strict_cap | positive_5d_qqq_bull |   2018 |                  0 |            0.0150 |               nan      |   nan      |            -0.0194 |
| strict_cap | positive_5d_qqq_bull |   2019 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| strict_cap | positive_5d_qqq_bull |   2020 |                  1 |           -0.0109 |                -0.1091 |     0.0000 |            -0.0258 |
| strict_cap | positive_5d_qqq_bull |   2021 |                  3 |            0.0284 |                 0.0764 |     0.6667 |            -0.0097 |
| strict_cap | positive_5d_qqq_bull |   2022 |                  3 |            0.0185 |                 0.0829 |     0.6667 |            -0.0294 |
| strict_cap | positive_5d_qqq_bull |   2023 |                  3 |            0.1099 |                 0.3667 |     1.0000 |            -0.0149 |
| strict_cap | positive_5d_qqq_bull |   2024 |                 34 |           -0.1287 |                -0.0222 |     0.4706 |            -0.1801 |
| strict_cap | positive_5d_qqq_bull |   2025 |                 13 |            0.0355 |                 0.0094 |     0.4615 |            -0.1656 |
| strict_cap | positive_5d_qqq_bull |   2026 |                 25 |            0.2129 |                 0.0750 |     0.6000 |            -0.1034 |
| no_cap     | base                 |   2010 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | base                 |   2011 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | base                 |   2012 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | base                 |   2013 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | base                 |   2014 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | base                 |   2015 |                  1 |           -0.0223 |                -0.2234 |     0.0000 |            -0.0410 |
| no_cap     | base                 |   2016 |                  2 |            0.0092 |                 0.0462 |     0.5000 |            -0.0476 |
| no_cap     | base                 |   2017 |                 25 |            0.0938 |                 0.0499 |     0.6400 |            -0.0526 |
| no_cap     | base                 |   2018 |                  1 |            0.0462 |                 0.2404 |     1.0000 |            -0.0127 |
| no_cap     | base                 |   2019 |                  1 |            0.0431 |                 0.4308 |     1.0000 |            -0.0023 |
| no_cap     | base                 |   2020 |                 11 |            0.0020 |                 0.0047 |     0.5455 |            -0.2234 |
| no_cap     | base                 |   2021 |                  7 |            0.0559 |                 0.0531 |     0.7143 |            -0.0150 |
| no_cap     | base                 |   2022 |                 39 |            0.0047 |                 0.0241 |     0.4359 |            -0.1964 |
| no_cap     | base                 |   2023 |                 12 |            0.0417 |                 0.0751 |     0.8333 |            -0.1268 |
| no_cap     | base                 |   2024 |                 49 |           -0.0848 |                -0.0047 |     0.5306 |            -0.1716 |
| no_cap     | base                 |   2025 |                 32 |            0.1421 |                 0.0474 |     0.4375 |            -0.2718 |
| no_cap     | base                 |   2026 |                 34 |            0.2780 |                 0.0740 |     0.6471 |            -0.1385 |
| no_cap     | positive_5d          |   2010 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2011 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2012 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2013 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2014 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2015 |                  1 |           -0.0223 |                -0.2234 |     0.0000 |            -0.0410 |
| no_cap     | positive_5d          |   2016 |                  2 |            0.0092 |                 0.0462 |     0.5000 |            -0.0476 |
| no_cap     | positive_5d          |   2017 |                 18 |            0.0049 |                 0.0165 |     0.6667 |            -0.0627 |
| no_cap     | positive_5d          |   2018 |                  0 |            0.0150 |               nan      |   nan      |            -0.0194 |
| no_cap     | positive_5d          |   2019 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d          |   2020 |                  4 |            0.0192 |                 0.0496 |     0.5000 |            -0.0952 |
| no_cap     | positive_5d          |   2021 |                  6 |            0.0473 |                 0.0657 |     0.6667 |            -0.0182 |
| no_cap     | positive_5d          |   2022 |                 31 |            0.0468 |                 0.0450 |     0.4516 |            -0.1936 |
| no_cap     | positive_5d          |   2023 |                  8 |            0.1042 |                 0.1533 |     0.8750 |            -0.1169 |
| no_cap     | positive_5d          |   2024 |                 38 |           -0.1643 |                -0.0286 |     0.5000 |            -0.1777 |
| no_cap     | positive_5d          |   2025 |                 20 |            0.1616 |                 0.0693 |     0.4500 |            -0.1970 |
| no_cap     | positive_5d          |   2026 |                 26 |            0.2425 |                 0.0840 |     0.6154 |            -0.1080 |
| no_cap     | positive_5d_qqq_bull |   2010 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2011 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2012 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2013 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2014 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2015 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2016 |                  1 |            0.0102 |                 0.1024 |     1.0000 |            -0.0187 |
| no_cap     | positive_5d_qqq_bull |   2017 |                 18 |            0.0049 |                 0.0165 |     0.6667 |            -0.0627 |
| no_cap     | positive_5d_qqq_bull |   2018 |                  0 |            0.0150 |               nan      |   nan      |            -0.0194 |
| no_cap     | positive_5d_qqq_bull |   2019 |                  0 |            0.0000 |               nan      |   nan      |             0.0000 |
| no_cap     | positive_5d_qqq_bull |   2020 |                  3 |           -0.0169 |                -0.0560 |     0.3333 |            -0.0952 |
| no_cap     | positive_5d_qqq_bull |   2021 |                  6 |            0.0473 |                 0.0657 |     0.6667 |            -0.0182 |
| no_cap     | positive_5d_qqq_bull |   2022 |                  4 |            0.0051 |                 0.0276 |     0.5000 |            -0.0427 |
| no_cap     | positive_5d_qqq_bull |   2023 |                  8 |            0.0198 |                 0.1533 |     0.8750 |            -0.1169 |
| no_cap     | positive_5d_qqq_bull |   2024 |                 38 |           -0.1643 |                -0.0286 |     0.5000 |            -0.1777 |
| no_cap     | positive_5d_qqq_bull |   2025 |                 13 |            0.0349 |                 0.0094 |     0.4615 |            -0.1712 |
| no_cap     | positive_5d_qqq_bull |   2026 |                 26 |            0.2292 |                 0.0778 |     0.6154 |            -0.1034 |

## Cost sensitivity

| universe   | strategy             | cost_level   |   total_return |   cagr |   sharpe |   maximum_drawdown |   number_of_trades |
|:-----------|:---------------------|:-------------|---------------:|-------:|---------:|-------------------:|-------------------:|
| strict_cap | base                 | zero         |         0.7322 | 0.0531 |   0.3920 |            -0.2975 |                181 |
| strict_cap | base                 | base         |         0.6701 | 0.0495 |   0.3715 |            -0.2993 |                181 |
| strict_cap | base                 | double       |         0.6103 | 0.0459 |   0.3511 |            -0.3045 |                181 |
| strict_cap | positive_5d          | zero         |         0.6227 | 0.0467 |   0.4238 |            -0.2800 |                127 |
| strict_cap | positive_5d          | base         |         0.5811 | 0.0441 |   0.4046 |            -0.2838 |                127 |
| strict_cap | positive_5d          | double       |         0.5406 | 0.0416 |   0.3854 |            -0.2876 |                127 |
| strict_cap | positive_5d_qqq_bull | zero         |         0.3548 | 0.0290 |   0.3551 |            -0.2357 |                 97 |
| strict_cap | positive_5d_qqq_bull | base         |         0.3281 | 0.0271 |   0.3351 |            -0.2393 |                 97 |
| strict_cap | positive_5d_qqq_bull | double       |         0.3020 | 0.0252 |   0.3150 |            -0.2430 |                 97 |
| no_cap     | base                 | zero         |         0.8595 | 0.0381 |   0.3183 |            -0.3136 |                214 |
| no_cap     | base                 | base         |         0.7806 | 0.0353 |   0.3015 |            -0.3224 |                214 |
| no_cap     | base                 | double       |         0.7050 | 0.0327 |   0.2848 |            -0.3310 |                214 |
| no_cap     | positive_5d          | zero         |         0.5701 | 0.0275 |   0.2951 |            -0.3278 |                154 |
| no_cap     | positive_5d          | base         |         0.5214 | 0.0256 |   0.2786 |            -0.3340 |                154 |
| no_cap     | positive_5d          | double       |         0.4742 | 0.0236 |   0.2621 |            -0.3402 |                154 |
| no_cap     | positive_5d_qqq_bull | zero         |         0.2126 | 0.0117 |   0.1776 |            -0.3064 |                117 |
| no_cap     | positive_5d_qqq_bull | base         |         0.1839 | 0.0102 |   0.1610 |            -0.3126 |                117 |
| no_cap     | positive_5d_qqq_bull | double       |         0.1559 | 0.0088 |   0.1444 |            -0.3188 |                117 |

## Range-position diagnostic — strict BASE

| range_bucket   |   number_of_trades |   average_return |   median_return |   win_rate |     mae |    mfe |   trade_return_sharpe |
|:---------------|-------------------:|-----------------:|----------------:|-----------:|--------:|-------:|----------------------:|
| 0-5%           |                 30 |           0.0764 |          0.0389 |     0.6333 | -0.1463 | 0.2466 |                0.8521 |
| 5-10%          |                 21 |          -0.0213 |         -0.0497 |     0.4286 | -0.1390 | 0.1013 |               -0.3610 |
| 10-15%         |                 24 |           0.0698 |          0.0527 |     0.5833 | -0.1292 | 0.2030 |                0.9751 |
| 15-20%         |                 41 |           0.0326 |          0.0369 |     0.5366 | -0.1390 | 0.1795 |                0.4732 |
| 20-25%         |                 65 |           0.0188 |          0.0033 |     0.5231 | -0.1254 | 0.1477 |                0.3598 |

## Falling-knife diagnostic — strict BASE

| outcome   | variable              |   observations |    mean |   median |     p25 |     p75 |
|:----------|:----------------------|---------------:|--------:|---------:|--------:|--------:|
| loser     | previous_5d_return    |             83 | -0.0769 |  -0.0763 | -0.1222 | -0.0383 |
| loser     | previous_10d_return   |             83 | -0.0959 |  -0.0853 | -0.1585 | -0.0310 |
| loser     | previous_20d_return   |             83 | -0.1043 |  -0.0910 | -0.1531 | -0.0226 |
| loser     | distance_sma20        |             83 | -0.0876 |  -0.0747 | -0.1318 | -0.0327 |
| loser     | distance_sma50        |             83 | -0.1108 |  -0.0978 | -0.1598 | -0.0558 |
| loser     | consecutive_down_days |             83 |  1.7831 |   2.0000 |  1.0000 |  3.0000 |
| winner    | previous_5d_return    |             98 | -0.0504 |  -0.0462 | -0.1029 | -0.0172 |
| winner    | previous_10d_return   |             98 | -0.0728 |  -0.0628 | -0.1212 | -0.0247 |
| winner    | previous_20d_return   |             98 | -0.0978 |  -0.0845 | -0.1777 | -0.0301 |
| winner    | distance_sma20        |             98 | -0.0692 |  -0.0607 | -0.1018 | -0.0208 |
| winner    | distance_sma50        |             98 | -0.1186 |  -0.0994 | -0.1757 | -0.0502 |
| winner    | consecutive_down_days |             98 |  1.6633 |   1.0000 |  0.0000 |  2.0000 |
