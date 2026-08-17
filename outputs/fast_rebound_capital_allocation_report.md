# Fast-Rebound Capital Allocation Report

**Final decision: MOVE TO 3 ×33.33%**

The alpha signal is unchanged. This experiment modifies only entry-time capital allocation. The frozen 3×25% baseline reproduced exactly: 226 trades, 53.32% total return, Sharpe 0.82, and -13.43% maximum drawdown.

## Executive conclusion

The strongest diversified full-deployment architecture is **3x33_33**. It returned 74.13%, compounded at 16.60%, had Sharpe 0.83, and drew down -17.64%. This compares with 53.32%, 12.56%, 0.82, and -13.43% for 3×25%. The 1×100% and true-dynamic variants expose the portfolio to single-name weights near 100% and historical drawdowns above 50%; that idiosyncratic gap risk is not justified.

## Most important comparison

| architecture   |   total_return |   cagr |   sharpe |   maximum_drawdown |   calmar |   worst_day |   worst_week |   average_exposure |   maximum_single_stock_exposure |   2024_return |   gap_risk |   random_return_percentile |   random_sharpe_percentile |   top_10pct_removed_return |
|:---------------|---------------:|-------:|---------:|-------------------:|---------:|------------:|-------------:|-------------------:|--------------------------------:|--------------:|-----------:|---------------------------:|---------------------------:|---------------------------:|
| 3x25           |         0.5332 | 0.1256 |   0.8156 |            -0.1343 |   0.9356 |     -0.0747 |      -0.0948 |             0.1076 |                          0.2696 |       -0.0474 |    -0.0665 |                     0.9928 |                     0.9924 |                     0.2729 |
| 4x25           |         0.4524 | 0.1089 |   0.6513 |            -0.1627 |   0.6693 |     -0.0768 |      -0.0948 |             0.1222 |                          0.2680 |       -0.0125 |    -0.0665 |                   nan      |                   nan      |                     0.0986 |
| 3x33_33        |         0.7413 | 0.1660 |   0.8252 |            -0.1764 |   0.9410 |     -0.0993 |      -0.1245 |             0.1431 |                          0.3652 |       -0.0673 |    -0.0887 |                     0.9932 |                     0.9924 |                     0.3350 |
| 2x50           |         0.8254 | 0.1813 |   0.7880 |            -0.2675 |   0.6779 |     -0.1481 |      -0.1563 |             0.1685 |                          0.5618 |       -0.2060 |    -0.1330 |                   nan      |                   nan      |                     0.3431 |
| 1x100          |         0.8180 | 0.1800 |   0.6256 |            -0.5257 |   0.3424 |     -0.2912 |      -0.3055 |             0.2194 |                          1.0000 |       -0.4498 |    -0.2661 |                   nan      |                   nan      |                     0.1687 |

## All deterministic architectures

| architecture   |   total_return |   cagr |   annualized_volatility |   sharpe |   sortino |   maximum_drawdown |   calmar |   maximum_drawdown_duration |   recovery_time |   number_of_trades |   trades_per_year |   win_rate |   average_trade_return |   median_trade_return |   profit_factor |   average_winner |   average_loser |   best_trade |   worst_trade |   average_mae |   average_mfe |   average_holding_period |   average_exposure |   maximum_exposure |   annual_turnover |   return_per_invested_day |   return_per_average_exposure |
|:---------------|---------------:|-------:|------------------------:|---------:|----------:|-------------------:|---------:|----------------------------:|----------------:|-------------------:|------------------:|-----------:|-----------------------:|----------------------:|----------------:|-----------------:|----------------:|-------------:|--------------:|--------------:|--------------:|-------------------------:|-------------------:|-------------------:|------------------:|--------------------------:|------------------------------:|
| 1x25           |         0.2227 | 0.0573 |                  0.0985 |   0.6172 |    0.8838 |            -0.1562 |   0.3666 |                         336 |             401 |                107 |           29.6298 |     0.6729 |                 0.0081 |                0.0479 |          1.2997 |           0.0531 |         -0.0844 |       0.1841 |       -0.2661 |       -0.0551 |        0.0618 |                   2.8598 |             0.0545 |             0.2586 |            7.3261 |                    0.0011 |                        4.0840 |
| 2x25           |         0.3966 | 0.0969 |                  0.1271 |   0.7947 |    1.1876 |            -0.1375 |   0.7047 |                         131 |             101 |                179 |           49.5677 |     0.6704 |                 0.0081 |                0.0479 |          1.2988 |           0.0522 |         -0.0814 |       0.1841 |       -0.2661 |       -0.0530 |        0.0619 |                   2.7207 |             0.0844 |             0.5102 |           12.6868 |                    0.0017 |                        4.7020 |
| 3x25           |         0.5332 | 0.1256 |                  0.1619 |   0.8156 |    1.2347 |            -0.1343 |   0.9356 |                          82 |              46 |                226 |           62.5826 |     0.6726 |                 0.0084 |                0.0479 |          1.2960 |           0.0521 |         -0.0813 |       0.1841 |       -0.2661 |       -0.0526 |        0.0633 |                   2.7389 |             0.1076 |             0.7587 |           16.4810 |                    0.0021 |                        4.9565 |
| 4x25           |         0.4524 | 0.1089 |                  0.1861 |   0.6513 |    0.9603 |            -0.1627 |   0.6693 |                          85 |              24 |                260 |           71.9977 |     0.6577 |                 0.0067 |                0.0479 |          1.2087 |           0.0522 |         -0.0808 |       0.1841 |       -0.2661 |       -0.0537 |        0.0622 |                   2.7231 |             0.1222 |             1.0000 |           18.8768 |                    0.0017 |                        3.7012 |
| 3x33_33        |         0.7413 | 0.1660 |                  0.2151 |   0.8252 |    1.2507 |            -0.1764 |   0.9410 |                          82 |              29 |                226 |           62.5826 |     0.6726 |                 0.0084 |                0.0479 |          1.2934 |           0.0521 |         -0.0813 |       0.1841 |       -0.2661 |       -0.0526 |        0.0633 |                   2.7389 |             0.1431 |             1.0000 |           22.2400 |                    0.0029 |                        5.1817 |
| 2x50           |         0.8254 | 0.1813 |                  0.2537 |   0.7880 |    1.1788 |            -0.2675 |   0.6779 |                         133 |             105 |                179 |           49.5677 |     0.6704 |                 0.0081 |                0.0479 |          1.2895 |           0.0522 |         -0.0814 |       0.1841 |       -0.2661 |       -0.0530 |        0.0619 |                   2.7207 |             0.1685 |             1.0000 |           25.6424 |                    0.0035 |                        4.8983 |
| 1x100          |         0.8180 | 0.1800 |                  0.3946 |   0.6256 |    0.9008 |            -0.5257 |   0.3424 |                         416 |             515 |                107 |           29.6298 |     0.6729 |                 0.0081 |                0.0479 |          1.2933 |           0.0531 |         -0.0844 |       0.1841 |       -0.2661 |       -0.0551 |        0.0618 |                   2.8598 |             0.2194 |             1.0000 |           27.4932 |                    0.0041 |                        3.7280 |
| dynamic_full   |         0.1755 | 0.0458 |                  0.3346 |   0.3106 |    0.4215 |            -0.5349 |   0.0856 |                         563 |             533 |                226 |           62.5826 |     0.6416 |                 0.0043 |                0.0479 |          1.0637 |           0.0520 |         -0.0811 |       0.1841 |       -0.2661 |       -0.0555 |        0.0604 |                   2.7035 |             0.2209 |             1.0000 |           25.9139 |                    0.0007 |                        0.7946 |

## Ranking and the fourth opportunity

| rank_group             |   trades |   plus5_hit_rate |   average_return |   median_return |   stop_rate |   average_mae |   average_mfe |   average_holding_period |   profit_factor |
|:-----------------------|---------:|-----------------:|-----------------:|----------------:|------------:|--------------:|--------------:|-------------------------:|----------------:|
| rank_1                 |      255 |           0.7608 |           0.0073 |          0.0480 |      0.3020 |       -0.1204 |        0.1443 |                   2.8157 |          1.2569 |
| rank_2                 |      131 |           0.7481 |           0.0024 |          0.0480 |      0.3740 |       -0.1025 |        0.1538 |                   2.7634 |          1.0796 |
| rank_3                 |       89 |           0.7640 |           0.0075 |          0.0480 |      0.3596 |       -0.1020 |        0.1382 |                   3.0337 |          1.2587 |
| rank_4                 |       63 |           0.7302 |          -0.0047 |          0.0480 |      0.4127 |       -0.1136 |        0.1201 |                   2.6667 |          0.8606 |
| rank_4_while_3x25_full |       18 |           0.7778 |           0.0067 |          0.0480 |      0.3333 |       -0.0969 |        0.1118 |                   3.0556 |          1.2532 |

Rank #4 uses the identical threshold and frozen model; no weaker signal was admitted. Its event outcomes explain why merely opening a fourth 25% slot did not add portfolio alpha.

The 18 Rank #4 events observed while 3×25% was already full were positive ex post (+0.67% average), but this is a small selected subset. Across all 63 threshold-qualified Rank #4 events, expectancy was -0.47% and profit factor 0.86. The actual 4×25% rerun therefore provides the more reliable answer: the extra slot reduced return and Sharpe. There is no robust evidence of unused fourth-slot alpha.

## Exposure and concentration

| architecture   |   average_exposure |   median_exposure |   pct_0 |   pct_0_25 |   pct_25_50 |   pct_50_75 |   pct_75_100 |   pct_100 |
|:---------------|-------------------:|------------------:|--------:|-----------:|------------:|------------:|-------------:|----------:|
| 1x25           |             0.0545 |            0.0000 |  0.7806 |     0.1246 |      0.0948 |      0.0000 |       0.0000 |    0.0000 |
| 2x25           |             0.0844 |            0.0000 |  0.7398 |     0.1147 |      0.1169 |      0.0287 |       0.0000 |    0.0000 |
| 3x25           |             0.1076 |            0.0000 |  0.7133 |     0.1058 |      0.1290 |      0.0430 |       0.0088 |    0.0000 |
| 4x25           |             0.1222 |            0.0000 |  0.7067 |     0.0959 |      0.1301 |      0.0474 |       0.0154 |    0.0044 |
| 3x33_33        |             0.1431 |            0.0000 |  0.7133 |     0.0000 |      0.1720 |      0.0827 |       0.0198 |    0.0121 |
| 2x50           |             0.1685 |            0.0000 |  0.7398 |     0.0000 |      0.1213 |      0.0595 |       0.0397 |    0.0397 |
| 1x100          |             0.2194 |            0.0000 |  0.7806 |     0.0000 |      0.0000 |      0.0000 |       0.0000 |    0.2194 |
| dynamic_full   |             0.2209 |            0.0000 |  0.7332 |     0.0077 |      0.0419 |      0.0408 |       0.0099 |    0.1665 |

| architecture   |   maximum_single_stock_exposure |   average_single_stock_allocation |   maximum_theme_exposure |   maximum_simultaneous_positions |   average_simultaneous_positions |   average_pairwise_correlation |   average_portfolio_beta |
|:---------------|--------------------------------:|----------------------------------:|-------------------------:|---------------------------------:|---------------------------------:|-------------------------------:|-------------------------:|
| 1x25           |                          0.2586 |                            0.2500 |                   0.2586 |                                1 |                           0.2194 |                       nan      |                   0.1276 |
| 2x25           |                          0.2617 |                            0.2500 |                   0.5058 |                                2 |                           0.3396 |                         0.3751 |                   0.1955 |
| 3x25           |                          0.2696 |                            0.2500 |                   0.7320 |                                3 |                           0.4333 |                         0.4101 |                   0.2491 |
| 4x25           |                          0.2680 |                            0.2494 |                   0.7530 |                                4 |                           0.4939 |                         0.4397 |                   0.2842 |
| 3x33_33        |                          0.3652 |                            0.3321 |                   0.9734 |                                3 |                           0.4333 |                         0.4101 |                   0.3314 |
| 2x50           |                          0.5618 |                            0.4983 |                   1.0000 |                                2 |                           0.3396 |                         0.3751 |                   0.3906 |
| 1x100          |                          1.0000 |                            1.0000 |                   1.0000 |                                1 |                           0.2194 |                       nan      |                   0.5133 |
| dynamic_full   |                          1.0000 |                            0.4647 |                   1.0000 |                                4 |                           0.4245 |                         0.4666 |                   0.5094 |

At 3×33.33%, maximum single-name exposure was 36.5%; average pairwise correlation was 0.41. Maximum same-theme exposure briefly reached 97.3%, an important concentration warning. The allocation remains preferable only as a deliberately high-alpha sleeve with this theme clustering understood; it is not equivalent to a diversified total portfolio.

True dynamic mechanics: at each next-open entry event, available cash is divided equally among that day's new qualifying candidates and existing positions are never resized. If one candidate appears while the portfolio is empty, it receives 100%; if two appear, each receives 50%, and so on. Freed cash waits for a new frozen-quality signal.

## Gap and simultaneous-loss risk

| architecture   |   gap_stops |   worst_gap_stock_loss |   average_gap_stock_loss |   largest_single_gap_portfolio_impact |   worst_portfolio_day |   worst_portfolio_week |   multi_stop_dates |   worst_multi_stop_pnl |
|:---------------|------------:|-----------------------:|-------------------------:|--------------------------------------:|----------------------:|-----------------------:|-------------------:|-----------------------:|
| 1x25           |           5 |                -0.2661 |                  -0.1427 |                               -0.0665 |               -0.0747 |                -0.0790 |                  0 |                 0.0000 |
| 2x25           |           8 |                -0.2661 |                  -0.1217 |                               -0.0665 |               -0.0747 |                -0.0790 |                  7 |                -0.0430 |
| 3x25           |          13 |                -0.2661 |                  -0.1088 |                               -0.0665 |               -0.0747 |                -0.0948 |                  9 |                -0.0629 |
| 4x25           |          15 |                -0.2661 |                  -0.1061 |                               -0.0665 |               -0.0768 |                -0.0948 |                 16 |                -0.0869 |
| 3x33_33        |          13 |                -0.2661 |                  -0.1088 |                               -0.0887 |               -0.0993 |                -0.1245 |                  9 |                -0.0839 |
| 2x50           |           8 |                -0.2661 |                  -0.1217 |                               -0.1330 |               -0.1481 |                -0.1563 |                  7 |                -0.0860 |
| 1x100          |           5 |                -0.2661 |                  -0.1427 |                               -0.2661 |               -0.2912 |                -0.3055 |                  0 |                 0.0000 |
| dynamic_full   |          13 |                -0.2661 |                  -0.1083 |                               -0.2661 |               -0.2912 |                -0.3055 |                 13 |                -0.0896 |

Actual gaps are translated using each trade's entry-time portfolio weight. The deterministic stress table is in `outputs/tables/capital_stress_test.csv`; these scenarios are risk illustrations, not forecasts.

For 3×33.33%, one -15% gap implies approximately -5% portfolio impact; two simultaneous -15% gaps imply -10%, and three imply -15%. The comparable 3×25% impacts are -3.75%, -7.5%, and -11.25%.

## Single-stock 100% architecture

The 1×100% architecture had 18.00% CAGR and 81.80% total return, but Sharpe fell to 0.63, maximum drawdown reached -52.57%, recovery took 515 calendar days, the worst overnight gap cost -26.61% of the portfolio, and the worst day was -29.12%. Its top 10% of trades supplied 29.0% of positive P&L. The return increment does not justify full single-name tail exposure.

## Fixed slots versus true dynamic deployment

The current 3×25% architecture beat 4×25% despite lower maximum deployment. True dynamic deployment was worse still: initial 100% allocations arising on one-signal days caused -53.49% drawdown and only 4.58% CAGR. Full deployment works best here through three capped sleeves, not by forcing all cash into however many positions happen to be open.

## Year-by-year evidence

| architecture   |   year |   return |   sharpe |   maximum_drawdown |   trades |   average_exposure |
|:---------------|-------:|---------:|---------:|-------------------:|---------:|-------------------:|
| 3x25           |   2023 |   0.0309 |   0.9975 |            -0.0172 |        5 |             0.0130 |
| 3x25           |   2024 |  -0.0474 |  -0.2690 |            -0.1297 |       40 |             0.1054 |
| 3x25           |   2025 |   0.1448 |   0.7647 |            -0.1343 |       95 |             0.1631 |
| 3x25           |   2026 |   0.3638 |   2.3754 |            -0.1021 |       86 |             0.1740 |
| 4x25           |   2023 |   0.0309 |   0.9975 |            -0.0172 |        5 |             0.0130 |
| 4x25           |   2024 |  -0.0125 |  -0.0053 |            -0.1297 |       43 |             0.1121 |
| 4x25           |   2025 |   0.1167 |   0.5834 |            -0.1627 |      113 |             0.1912 |
| 4x25           |   2026 |   0.2776 |   1.6421 |            -0.1384 |       99 |             0.2035 |
| 3x33_33        |   2023 |   0.0413 |   0.9991 |            -0.0230 |        5 |             0.0174 |
| 3x33_33        |   2024 |  -0.0673 |  -0.2701 |            -0.1717 |       40 |             0.1407 |
| 3x33_33        |   2025 |   0.1923 |   0.7863 |            -0.1721 |       95 |             0.2163 |
| 3x33_33        |   2026 |   0.5036 |   2.3842 |            -0.1340 |       86 |             0.2314 |
| 2x50           |   2023 |   0.0598 |   0.9797 |            -0.0344 |        5 |             0.0256 |
| 2x50           |   2024 |  -0.2060 |  -0.7593 |            -0.2538 |       36 |             0.1762 |
| 2x50           |   2025 |   0.2231 |   0.8404 |            -0.1839 |       68 |             0.2424 |
| 2x50           |   2026 |   0.7736 |   2.8547 |            -0.1099 |       70 |             0.2673 |
| 1x100          |   2023 |   0.0705 |   0.8389 |            -0.0711 |        4 |             0.0320 |
| 1x100          |   2024 |  -0.4498 |  -0.9974 |            -0.4855 |       28 |             0.2738 |
| 1x100          |   2025 |   0.4323 |   1.1051 |            -0.1875 |       41 |             0.2680 |
| 1x100          |   2026 |   1.1549 |   2.6693 |            -0.1910 |       34 |             0.3548 |

## Tail dependence

| architecture   | subset     |   trades |         pnl |   share_positive_pnl |
|:---------------|:-----------|---------:|------------:|---------------------:|
| 3x25           | best_trade |        1 |   6642.2361 |               0.0285 |
| 3x25           | best_5     |        5 |  20100.0276 |               0.0861 |
| 3x25           | top_5pct   |       12 |  37217.8167 |               0.1594 |
| 3x25           | top_10pct  |       23 |  57120.3566 |               0.2447 |
| 4x25           | best_trade |        1 |   6462.6532 |               0.0247 |
| 4x25           | best_5     |        5 |  20319.6788 |               0.0775 |
| 4x25           | top_5pct   |       13 |  39707.0877 |               0.1515 |
| 4x25           | top_10pct  |       26 |  62652.6593 |               0.2391 |
| 3x33_33        | best_trade |        1 |   9869.3802 |               0.0302 |
| 3x33_33        | best_5     |        5 |  29291.1910 |               0.0896 |
| 3x33_33        | top_5pct   |       12 |  53407.1323 |               0.1635 |
| 3x33_33        | top_10pct  |       23 |  82731.5919 |               0.2532 |
| 2x50           | best_trade |        1 |  14065.6382 |               0.0383 |
| 2x50           | best_5     |        5 |  41683.0283 |               0.1134 |
| 2x50           | top_5pct   |        9 |  60106.9628 |               0.1635 |
| 2x50           | top_10pct  |       18 |  94962.8678 |               0.2583 |
| 1x100          | best_trade |        1 |  23955.7436 |               0.0664 |
| 1x100          | best_5     |        5 |  66703.1573 |               0.1850 |
| 1x100          | top_5pct   |        6 |  74084.6547 |               0.2054 |
| 1x100          | top_10pct  |       11 | 104718.3995 |               0.2904 |

Exact reruns after removing leading trades/stocks are saved in `capital_tail_sensitivity.csv`.

## Matched-random and bootstrap evidence

| architecture   | metric           |   actual |   percentile |   random_p2_5 |   random_p50 |   random_p97_5 |
|:---------------|:-----------------|---------:|-------------:|--------------:|-------------:|---------------:|
| 3x25           | return           |   0.4775 |       0.9928 |       -0.3660 |      -0.0695 |         0.3577 |
| 3x25           | sharpe           |   1.0322 |       0.9924 |       -1.0244 |      -0.1190 |         0.8127 |
| 3x25           | maximum_drawdown |  -0.1325 |       0.9998 |       -0.4792 |      -0.3589 |        -0.2383 |
| 3x33_33        | return           |   0.6761 |       0.9932 |       -0.4572 |      -0.0958 |         0.4920 |
| 3x33_33        | sharpe           |   1.0481 |       0.9924 |       -1.0160 |      -0.1115 |         0.8234 |
| 3x33_33        | maximum_drawdown |  -0.1735 |       0.9998 |       -0.5815 |      -0.4466 |        -0.3042 |

| architecture   | bootstrap      | metric           |   ci_2_5 |   median |   ci_97_5 |
|:---------------|:---------------|:-----------------|---------:|---------:|----------:|
| 3x25           | trade          | total_return     |  -0.0406 |   0.5622 |    1.5351 |
| 3x25           | trade          | cagr             |  -0.0114 |   0.1315 |    0.2938 |
| 3x25           | trade          | maximum_drawdown |  -0.3005 |  -0.1508 |   -0.0842 |
| 3x25           | trade          | win_rate         |   0.6106 |   0.6726 |    0.7345 |
| 3x25           | ticker_cluster | total_return     |   0.1058 |   0.5328 |    1.1898 |
| 3x25           | ticker_cluster | cagr             |   0.0282 |   0.1256 |    0.2424 |
| 3x25           | ticker_cluster | maximum_drawdown |  -0.1770 |  -0.1040 |   -0.0701 |
| 3x25           | ticker_cluster | win_rate         |   0.6283 |   0.6726 |    0.7168 |
| 3x33_33        | trade          | total_return     |  -0.0579 |   0.7978 |    2.4151 |
| 3x33_33        | trade          | cagr             |  -0.0164 |   0.1764 |    0.4051 |
| 3x33_33        | trade          | maximum_drawdown |  -0.3818 |  -0.1961 |   -0.1109 |
| 3x33_33        | trade          | win_rate         |   0.6106 |   0.6726 |    0.7345 |
| 3x33_33        | ticker_cluster | total_return     |   0.1337 |   0.7523 |    1.8216 |
| 3x33_33        | ticker_cluster | cagr             |   0.0354 |   0.1680 |    0.3327 |
| 3x33_33        | ticker_cluster | maximum_drawdown |  -0.2305 |  -0.1358 |   -0.0932 |
| 3x33_33        | ticker_cluster | win_rate         |   0.6283 |   0.6726 |    0.7168 |

Random controls preserve actual entry dates, holding windows, and allocation weights while replacing selections from the same eligible universe. Bootstrap intervals include both independent trade resampling and ticker-cluster resampling.

## Explicit answers to the 20 questions

1. No. 4×25% changed total return by -8.08% and Sharpe from 0.82 to 0.65.
2. Rank #4 was not profitable: 63 qualified events, 73.0% +5% hits, and -0.47% average diagnostic return.
3. No; 4×25% returned 45.2% versus 53.3%, with a deeper -16.3% drawdown.
4. Full-deployment variants raised average exposure but magnified gaps; true dynamic deployment returned 17.6% with -53.5% drawdown.
5. 3×33.33% returned 74.1%, Sharpe 0.83, and drawdown -17.6%; it dominates 4×25% on this sample.
6. 2×50% produced 82.5%, but drawdown expanded to -26.7% and single-name exposure reached 56.2%.
7. No. 1×100% returned 81.8% but suffered -52.6% drawdown and a -26.6% single-gap portfolio hit.
8. 2x50 had the highest CAGR (18.1%).
9. 2x50 had the highest total return (82.5%).
10. 3x33_33 had the highest Sharpe (0.83).
11. 3x33_33 had the highest Calmar (0.94).
12. 1x100 had the best return per invested day.
13. Relative to 3×25%, 3x33_33 changed maximum drawdown from -13.4% to -17.6%.
14. Largest single-gap portfolio impact changed from -6.7% to -8.9%.
15. Yes. 100% concentration produced a -29.1% worst day and -52.6% drawdown, disproportionate to its return advantage.
16. Yes. Three-to-four sleeves materially reduce the portfolio impact of the same stock-level overnight gap.
17. Yes. 2024 return moved from -4.7% at 3×25% to -6.7% for 3x33_33.
18. After top-10% trade removal, 2x50 retained the highest return (34.3%).
19. Between the tested controls, 3x33_33 had the stronger matched-random return percentile (99.3%).
20. The best high-alpha trade-off is 3x33_33: it materially increases CAGR while retaining diversification and bounded single-gap impact.

## Decision

**MOVE TO 3 ×33.33%.** Do not lower the threshold or force investment. Cash remains the correct allocation when too few frozen-quality signals qualify. This is a research allocation decision, not a live-deployment recommendation; clean point-in-time validation remains required.
