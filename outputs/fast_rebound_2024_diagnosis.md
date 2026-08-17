# Fast-Rebound 2024 Diagnosis

**Primary explanation: TAIL-LOSS PROBLEM**  
**Final decision: KEEP STRATEGY UNCHANGED**

The current strategy remained fully frozen: strict $10B+ historical universe, beta >=2, original logistic model and 0.636 threshold, maximum three recommendations and positions, 25% sleeves, -7.5% stop, fixed +5% target, 10-day hold, next-open execution, and existing costs. Reproduction yielded 226 trades and 53.32% total return.

## Bottom line

2024's -4.74% return was not a uniform failure across all trades. The loss was dominated by stop/gap tails and repeated exposure to a small ticker cluster. The worst three trades represented 36.7% of gross 2024 losses and 2.37 times the net annual loss; SMCI contributed $-7,053. The outside-2024 ticker-cluster bootstrap estimates a 9.2% chance of a negative 40-trade year and a 2.7% chance of a year at least as bad as 2024. This supports a tail-loss diagnosis, but the small number of extreme observations is insufficient to justify changing a frozen rule.

## Year-by-year decomposition

|      year |   recommendations |   executed_trades |   trades_per_month |   total_return |   sharpe |   sortino |   maximum_drawdown |   win_rate |   plus5_hit_rate |   stop_loss_rate |   timeout_rate |   average_trade_return |   median_trade_return |   average_winner |   average_loser |   profit_factor |   average_mae |   median_mae |   average_mfe |   median_mfe |   average_holding_period |   median_holding_period |   average_fast_rebound_score |   average_portfolio_exposure |
|----------:|------------------:|------------------:|-------------------:|---------------:|---------:|----------:|-------------------:|-----------:|-----------------:|-----------------:|---------------:|-----------------------:|----------------------:|-----------------:|----------------:|----------------:|--------------:|-------------:|--------------:|-------------:|-------------------------:|------------------------:|-----------------------------:|-----------------------------:|
| 2023.0000 |           12.0000 |            5.0000 |             0.4167 |         0.0309 |   0.9975 |    1.5418 |            -0.0172 |     0.8000 |           1.0000 |           0.2000 |         0.0000 |                 0.0246 |                0.0479 |           0.0499 |         -0.0768 |          2.6089 |       -0.0346 |      -0.0366 |        0.0710 |       0.0807 |                   3.6000 |                  4.0000 |                      66.0200 |                       0.0130 |
| 2024.0000 |           86.0000 |           40.0000 |             3.3333 |        -0.0474 |  -0.2690 |   -0.3654 |            -0.1297 |     0.6000 |           0.6750 |           0.3750 |         0.0250 |                -0.0051 |                0.0479 |           0.0537 |         -0.0932 |          0.8455 |       -0.0640 |      -0.0498 |        0.0603 |       0.0528 |                   3.7500 |                  3.5000 |                      68.0775 |                       0.1054 |
| 2025.0000 |          209.0000 |           95.0000 |             7.9167 |         0.1448 |   0.7647 |    1.1404 |            -0.1343 |     0.6737 |           0.7895 |           0.3158 |         0.0211 |                 0.0087 |                0.0479 |           0.0504 |         -0.0774 |          1.2925 |       -0.0536 |      -0.0485 |        0.0637 |       0.0576 |                   2.7053 |                  2.0000 |                      68.0716 |                       0.1631 |
| 2026.0000 |          168.0000 |           86.0000 |            10.7500 |         0.3638 |   2.3754 |    4.2468 |            -0.1021 |     0.6977 |           0.8372 |           0.3023 |         0.0000 |                 0.0134 |                0.0479 |           0.0534 |         -0.0788 |          1.5147 |       -0.0473 |      -0.0305 |        0.0637 |       0.0584 |                   2.2558 |                  2.0000 |                      66.8767 |                       0.1740 |

## 2024 P&L concentration

| subset    |   trades |         pnl |   share_of_gross_losses |   multiple_of_net_year_loss |
|:----------|---------:|------------:|------------------------:|----------------------------:|
| worst 1   |        1 |  -7412.0812 |                  0.1864 |                      1.2063 |
| worst 3   |        3 | -14592.0703 |                  0.3670 |                      2.3748 |
| worst 5   |        5 | -19130.4472 |                  0.4811 |                      3.1134 |
| worst 10% |        4 | -17009.0695 |                  0.4278 |                      2.7682 |
| worst 20% |        8 | -25333.2997 |                  0.6371 |                      4.1230 |

The complete worst-to-best ledger is in `outputs/tables/fast_rebound_2024_trades.csv`.

## Stops, gaps, and post-stop behavior

|      year |   stop_outs |   average_loss |   median_loss |   gap_throughs |   gap_rate |   false_stop_rate |   genuine_collapse_rate |   average_next10_rebound |
|----------:|------------:|---------------:|--------------:|---------------:|-----------:|------------------:|------------------------:|-------------------------:|
| 2023.0000 |      1.0000 |        -0.0768 |       -0.0768 |         0.0000 |     0.0000 |            1.0000 |                  0.0000 |                   0.2738 |
| 2024.0000 |     15.0000 |        -0.0985 |       -0.0768 |         5.0000 |     0.3333 |            0.8000 |                  0.5333 |                   0.1033 |
| 2025.0000 |     30.0000 |        -0.0782 |       -0.0768 |         3.0000 |     0.1000 |            0.7000 |                  0.6667 |                   0.1268 |
| 2026.0000 |     26.0000 |        -0.0788 |       -0.0768 |         5.0000 |     0.1923 |            0.8462 |                  0.6923 |                   0.2126 |

## Timeouts and delayed rebounds

|      year |   trades |   timeouts |   timeout_rate |   after_exit_plus5_rate |   average_timeout_return |
|----------:|---------:|-----------:|---------------:|------------------------:|-------------------------:|
| 2023.0000 |   5.0000 |     0.0000 |         0.0000 |                nan      |                 nan      |
| 2024.0000 |  40.0000 |     1.0000 |         0.0250 |                  0.0000 |                  -0.0134 |
| 2025.0000 |  95.0000 |     2.0000 |         0.0211 |                  0.0000 |                  -0.0230 |
| 2026.0000 |  86.0000 |     0.0000 |         0.0000 |                nan      |                 nan      |

## Barrier paths

|      year |   trades |   plus5_before_minus7_5 |   minus7_5_before_plus5 |   neither_within_10d |   plus5_within_1d |   plus5_within_3d |   plus5_within_5d |   plus5_within_10d |
|----------:|---------:|------------------------:|------------------------:|---------------------:|------------------:|------------------:|------------------:|-------------------:|
| 2023.0000 |   5.0000 |                  0.8000 |                  0.2000 |               0.0000 |            0.0000 |            0.2000 |            1.0000 |             1.0000 |
| 2024.0000 |  40.0000 |                  0.6000 |                  0.3750 |               0.0250 |            0.2750 |            0.3500 |            0.4750 |             0.6750 |
| 2025.0000 |  95.0000 |                  0.6632 |                  0.3158 |               0.0211 |            0.2421 |            0.5789 |            0.6632 |             0.7895 |
| 2026.0000 |  86.0000 |                  0.6977 |                  0.3023 |               0.0000 |            0.3488 |            0.6512 |            0.7558 |             0.8372 |

## Score and probability calibration

|   year | score_band   |   trades |   average_score |   plus5_hit_rate |   stop_rate |   average_return |   median_return |   average_mae |   average_mfe |
|-------:|:-------------|---------:|----------------:|-----------------:|------------:|-----------------:|----------------:|--------------:|--------------:|
|   2023 | [60, 65)     |        2 |         64.8500 |           1.0000 |      0.0000 |           0.0520 |          0.0520 |       -0.0296 |        0.0814 |
|   2023 | [65, 70)     |        3 |         66.8000 |           1.0000 |      0.3333 |           0.0063 |          0.0479 |       -0.0379 |        0.0641 |
|   2024 | [60, 65)     |       12 |         64.3417 |           0.6667 |      0.4167 |          -0.0016 |          0.0479 |       -0.0575 |        0.0495 |
|   2024 | [65, 70)     |       19 |         67.4474 |           0.6316 |      0.3684 |          -0.0125 |          0.0479 |       -0.0674 |        0.0553 |
|   2024 | [70, 75)     |        6 |         73.3333 |           0.8333 |      0.1667 |           0.0264 |          0.0479 |       -0.0607 |        0.1124 |
|   2024 | [75, 80)     |        3 |         76.5000 |           0.6667 |      0.6667 |          -0.0353 |         -0.0768 |       -0.0751 |        0.0314 |
|   2025 | [60, 65)     |       22 |         64.1409 |           0.7273 |      0.2727 |           0.0112 |          0.0479 |       -0.0525 |        0.0551 |
|   2025 | [65, 70)     |       46 |         67.5913 |           0.7826 |      0.3913 |           0.0002 |          0.0479 |       -0.0592 |        0.0577 |
|   2025 | [70, 75)     |       25 |         71.7960 |           0.8400 |      0.2400 |           0.0189 |          0.0479 |       -0.0461 |        0.0764 |
|   2025 | [75, 80)     |        2 |         75.8000 |           1.0000 |      0.0000 |           0.0479 |          0.0479 |       -0.0320 |        0.1387 |
|   2026 | [60, 65)     |       28 |         64.1429 |           0.8929 |      0.2143 |           0.0225 |          0.0479 |       -0.0420 |        0.0637 |
|   2026 | [65, 70)     |       47 |         67.2702 |           0.7872 |      0.3617 |           0.0074 |          0.0479 |       -0.0529 |        0.0618 |
|   2026 | [70, 75)     |       10 |         71.6800 |           0.9000 |      0.3000 |           0.0114 |          0.0479 |       -0.0402 |        0.0703 |
|   2026 | [75, 80)     |        1 |         76.9000 |           1.0000 |      0.0000 |           0.0653 |          0.0653 |       -0.0071 |        0.0917 |

|   year | probability_band   |   trades |   predicted_probability |   actual_plus5_rate |   calibration_error |
|-------:|:-------------------|---------:|------------------------:|--------------------:|--------------------:|
|   2023 | [0.65, 0.7)        |        2 |                  0.6839 |              1.0000 |              0.3161 |
|   2023 | [0.7, 0.75)        |        1 |                  0.7394 |              1.0000 |              0.2606 |
|   2023 | [0.75, 0.8)        |        2 |                  0.7556 |              1.0000 |              0.2444 |
|   2024 | [0.65, 0.7)        |        2 |                  0.6509 |              0.0000 |             -0.6509 |
|   2024 | [0.7, 0.75)        |       13 |                  0.7185 |              0.7692 |              0.0508 |
|   2024 | [0.75, 0.8)        |       11 |                  0.7728 |              0.6364 |             -0.1364 |
|   2024 | [0.8, 1.01)        |       14 |                  0.8817 |              0.7143 |             -0.1674 |
|   2025 | [0.6, 0.65)        |        1 |                  0.6468 |              1.0000 |              0.3532 |
|   2025 | [0.65, 0.7)        |        3 |                  0.6894 |              0.6667 |             -0.0228 |
|   2025 | [0.7, 0.75)        |       11 |                  0.7262 |              0.6364 |             -0.0898 |
|   2025 | [0.75, 0.8)        |       25 |                  0.7749 |              0.6400 |             -0.1349 |
|   2025 | [0.8, 1.01)        |       55 |                  0.8503 |              0.8909 |              0.0406 |
|   2026 | [0.65, 0.7)        |        1 |                  0.6941 |              1.0000 |              0.3059 |
|   2026 | [0.7, 0.75)        |       13 |                  0.7288 |              0.8462 |              0.1173 |
|   2026 | [0.75, 0.8)        |       32 |                  0.7776 |              0.8438 |              0.0661 |
|   2026 | [0.8, 1.01)        |       40 |                  0.8413 |              0.8250 |             -0.0163 |

## Market regime and loss driver

|      year |   spy_5d_return |   spy_20d_return |   spy_60d_return |   qqq_5d_return |   qqq_20d_return |   qqq_60d_return |   spy_distance_sma200 |   qqq_distance_sma200 |   vix_level |   vix_5d_change |
|----------:|----------------:|-----------------:|-----------------:|----------------:|-----------------:|-----------------:|----------------------:|----------------------:|------------:|----------------:|
| 2023.0000 |          0.0149 |          -0.0267 |           0.0612 |          0.0199 |          -0.0550 |          -0.0007 |               -0.0158 |               -0.0838 |     20.8220 |         -3.2050 |
| 2024.0000 |         -0.0072 |           0.0023 |           0.0624 |         -0.0101 |          -0.0073 |           0.0621 |                0.0947 |                0.0888 |     18.5582 |          2.9577 |
| 2025.0000 |         -0.0162 |          -0.0322 |          -0.0269 |         -0.0212 |          -0.0412 |          -0.0321 |                0.0173 |                0.0158 |     23.7695 |          3.0727 |
| 2026.0000 |         -0.0089 |          -0.0136 |           0.0450 |         -0.0182 |          -0.0248 |           0.0684 |                0.0545 |                0.0719 |     20.3352 |          1.3057 |

|   year | loss_driver   |   losses |         pnl |   average_return |
|-------:|:--------------|---------:|------------:|-----------------:|
|   2023 | idiosyncratic |        1 |  -1921.2038 |          -0.0768 |
|   2024 | idiosyncratic |       12 | -31160.2329 |          -0.0976 |
|   2024 | market_beta   |        4 |  -8600.8428 |          -0.0800 |
|   2025 | idiosyncratic |        8 | -17493.9041 |          -0.0768 |
|   2025 | market_beta   |       23 | -49459.9780 |          -0.0775 |
|   2026 | idiosyncratic |       14 | -37806.4579 |          -0.0782 |
|   2026 | market_beta   |       12 | -33670.0870 |          -0.0794 |

Losses are classified as market-beta when the holding window coincided with QQQ <=-2%, SPY <=-1.5%, or a <=-2% median eligible high-beta move; otherwise they are labeled idiosyncratic. This simple attribution assigns 78% of 2024 losing-trade P&L to idiosyncratic moves.

## Sector/theme and ticker concentration

|   year | theme               |   trades |        pnl |   average_return |   win_rate |   plus5_hit_rate |   stop_rate |
|-------:|:--------------------|---------:|-----------:|-----------------:|-----------:|-----------------:|------------:|
|   2024 | semiconductors / AI |        9 | -3879.7963 |          -0.0158 |     0.4444 |           0.4444 |      0.4444 |
|   2024 | other               |       26 | -3176.4519 |          -0.0036 |     0.6538 |           0.7692 |      0.3462 |
|   2024 | software            |        3 | -2674.4818 |          -0.0353 |     0.3333 |           0.3333 |      0.6667 |
|   2024 | consumer            |        2 |  3586.2757 |           0.0694 |     1.0000 |           1.0000 |      0.0000 |

|   year | ticker   |   trades |        pnl |   average_return |   win_rate |   plus5_hit_rate |   stop_rate |
|-------:|:---------|---------:|-----------:|-----------------:|-----------:|-----------------:|------------:|
|   2024 | SMCI     |       15 | -7052.6096 |          -0.0164 |     0.6000 |           0.6667 |      0.4000 |
|   2024 | AMAT     |        2 | -4538.3768 |          -0.0832 |     0.0000 |           0.0000 |      1.0000 |
|   2024 | PLTR     |        3 | -2674.4818 |          -0.0353 |     0.3333 |           0.3333 |      0.6667 |
|   2024 | ENPH     |        7 | -1135.7163 |          -0.0056 |     0.5714 |           0.8571 |      0.4286 |
|   2024 | AMD      |        2 |  -724.3833 |          -0.0145 |     0.5000 |           0.5000 |      0.5000 |
|   2024 | INTC     |        1 |  -375.3397 |          -0.0134 |     0.0000 |           0.0000 |      0.0000 |
|   2024 | NVDA     |        4 |  1758.3036 |           0.0167 |     0.7500 |           0.7500 |      0.2500 |
|   2024 | ALB      |        2 |  2483.8375 |           0.0479 |     1.0000 |           1.0000 |      0.0000 |
|   2024 | AVGO     |        2 |  2528.0365 |           0.0479 |     1.0000 |           1.0000 |      0.0000 |
|   2024 | TSLA     |        2 |  3586.2757 |           0.0694 |     1.0000 |           1.0000 |      0.0000 |

## Repeat entries

|   year | entry_group          |   trades |   average_return |         pnl |   win_rate |   stop_rate |
|-------:|:---------------------|---------:|-----------------:|------------:|-----------:|------------:|
|   2024 | first                |        8 |           0.0132 |   2528.8470 |     0.6250 |      0.2500 |
|   2024 | second               |        8 |           0.0163 |   3418.2548 |     0.7500 |      0.2500 |
|   2024 | third+               |       24 |          -0.0183 | -12091.5560 |     0.5417 |      0.4583 |
|   2024 | not after prior stop |       28 |          -0.0055 |  -4764.0463 |     0.5714 |    nan      |
|   2024 | after prior stop     |       12 |          -0.0042 |  -1380.4080 |     0.6667 |    nan      |

## Pullback depth and velocity

|   year | outcome   |   trades |   range_position_20d |   range_position_50d |   range_position_100d |   drawdown_from_20d_high |   drawdown_from_50d_high |   drawdown_from_100d_high |   distance_sma20 |   distance_sma50 |
|-------:|:----------|---------:|---------------------:|---------------------:|----------------------:|-------------------------:|-------------------------:|--------------------------:|-----------------:|-----------------:|
|   2024 | winner    |       24 |               0.3313 |               0.2692 |                0.2527 |                  -0.1600 |                  -0.2688 |                   -0.3818 |          -0.0104 |          -0.0800 |
|   2024 | loser     |       16 |               0.5583 |               0.4329 |                0.2959 |                  -0.0887 |                  -0.1916 |                   -0.3452 |           0.0850 |           0.0446 |

|      year |   trades |   atr_pct |   realized_volatility_10d |   realized_volatility_20d |   absolute_move_3pct_frequency_60d |   absolute_move_5pct_frequency_60d |   beta |
|----------:|---------:|----------:|--------------------------:|--------------------------:|-----------------------------------:|-----------------------------------:|-------:|
| 2023.0000 |   5.0000 |    0.0437 |                    0.4605 |                    0.4847 |                             0.3700 |                             0.1400 | 2.0661 |
| 2024.0000 |  40.0000 |    0.0785 |                    1.0526 |                    1.0323 |                             0.3876 |                             0.2057 | 2.6763 |
| 2025.0000 |  95.0000 |    0.0783 |                    0.8596 |                    0.8752 |                             0.4839 |                             0.2861 | 2.3748 |
| 2026.0000 |  86.0000 |    0.0807 |                    0.9306 |                    0.9372 |                             0.4905 |                             0.2963 | 2.4875 |

2024 candidates retained substantial movement capability (7.85% average ATR, similar to 2025/26), so inadequate velocity was not the cause.

## Capital crowding

| period        |   days |   average_positions |   average_exposure |   average_beta |   average_pairwise_correlation |
|:--------------|-------:|--------------------:|-------------------:|---------------:|-------------------------------:|
| 2024 drawdown |     41 |              0.8293 |             0.1211 |         2.8872 |                         0.1005 |
| normal        |    866 |              0.6755 |             0.1069 |         2.3271 |                         0.4263 |

## Drawdown forensics

| start_date          | trough_date         | recovery_date       |   depth | stocks_held                                           | trade_outcomes                                                                                                                                                                                                                                                          |   spy_return |   qqq_return |   vix_change | dominant_theme   |   average_exposure |
|:--------------------|:--------------------|:--------------------|--------:|:------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|:-----------------|-------------------:|
| 2024-10-11 00:00:00 | 2025-01-14 00:00:00 | 2025-02-12 00:00:00 | -0.1333 | AMAT,INTC,MPWR,ON,PLTR,SMCI                           | INTC:-1.3%; SMCI:-26.6%; SMCI:-10.0%; SMCI:4.8%; SMCI:4.8%; PLTR:-7.7%; SMCI:4.8%; SMCI:14.4%; PLTR:4.8%; SMCI:-7.7%; SMCI:4.8%; SMCI:4.8%; SMCI:-7.7%; SMCI:-7.7%; SMCI:-17.7%; SMCI:4.8%; AMAT:-8.0%; SMCI:4.8%; ON:4.8%; PLTR:-7.7%; MPWR:4.8%; PLTR:4.8%; SMCI:6.1% |       0.0079 |       0.0254 |      10.3900 | other            |             0.1629 |
| 2025-02-21 00:00:00 | 2025-03-13 00:00:00 | 2025-04-28 00:00:00 | -0.1343 | ANET,MPWR,ON,PLTR,SMCI                                | PLTR:4.8%; PLTR:-7.7%; SMCI:-7.7%; SMCI:-7.7%; PLTR:4.8%; SMCI:-7.7%; SMCI:4.8%; PLTR:4.8%; ANET:-7.7%; SMCI:-7.7%; PLTR:-9.7%; SMCI:4.8%; ANET:-7.7%; ON:-7.7%; ANET:4.8%; MPWR:4.8%                                                                                   |      -0.0809 |      -0.1098 |       8.2400 | other            |             0.4865 |
| 2025-11-14 00:00:00 | 2025-11-21 00:00:00 | 2025-12-08 00:00:00 | -0.0948 | COIN,MU,SMCI                                          | COIN:-7.7%; MU:-7.7%; SMCI:-7.7%; COIN:-7.7%; MU:-7.7%; MU:4.8%; COIN:4.8%                                                                                                                                                                                              |      -0.0192 |      -0.0309 |       6.5900 | crypto-linked    |             0.2464 |
| 2025-12-10 00:00:00 | 2025-12-17 00:00:00 | 2026-02-18 00:00:00 | -0.0760 | COIN,MU,SMCI                                          | SMCI:-7.7%; COIN:-7.7%; SMCI:-7.7%; MU:8.6%; COIN:-7.7%                                                                                                                                                                                                                 |      -0.0235 |      -0.0433 |       1.5200 | other            |             0.4532 |
| 2026-03-09 00:00:00 | 2026-03-30 00:00:00 | 2026-06-11 00:00:00 | -0.1021 | AMD,APP,COIN,LRCX,SNDK                                | SNDK:4.8%; APP:-7.7%; COIN:4.8%; APP:-7.7%; SNDK:4.8%; AMD:4.8%; APP:4.8%; SNDK:-9.3%; SNDK:-7.7%; COIN:-9.1%; SNDK:4.8%; AMD:-7.7%; SNDK:-7.7%; LRCX:4.8%                                                                                                              |      -0.0657 |      -0.0803 |       7.3000 | other            |             0.3558 |
| 2026-06-30 00:00:00 | 2026-07-17 00:00:00 | NaT                 | -0.0678 | AMAT,APP,AVGO,CIEN,COIN,GLW,KLAC,ON,QCOM,SMCI,STX,WDC | ON:4.8%; WDC:-7.7%; STX:-7.7%; WDC:4.8%; STX:-7.7%; AVGO:4.8%; AMAT:4.8%; GLW:7.7%; AMAT:-8.0%; KLAC:-7.7%; APP:4.8%; COIN:4.8%; SMCI:-8.4%; CIEN:-8.5%; QCOM:-7.7%                                                                                                     |      -0.0047 |      -0.0558 |       2.8400 | other            |             0.3607 |

The October 2024–January 2025 episode was idiosyncratic: SPY and QQQ rose 0.8% and 2.5% from peak to trough while repeated SMCI and other single-name losses drove the portfolio down. By contrast, the February–March 2025 and March 2026 episodes coincided with broad QQQ declines and are better described as market-beta drawdowns.

## 2024 month by month

| month   |   trades |   plus5_hits |   stops |   timeouts |   return |   win_rate |   average_trade |   profit_factor |
|:--------|---------:|-------------:|--------:|-----------:|---------:|-----------:|----------------:|----------------:|
| 2024-01 |        0 |            0 |       0 |          0 |   0.0000 |   nan      |        nan      |        nan      |
| 2024-02 |        0 |            0 |       0 |          0 |   0.0000 |   nan      |        nan      |        nan      |
| 2024-03 |        1 |            1 |       0 |          0 |   0.0120 |     1.0000 |          0.0479 |        nan      |
| 2024-04 |        5 |            3 |       2 |          0 |   0.0201 |     0.6000 |          0.0066 |          1.1724 |
| 2024-05 |        2 |            2 |       0 |          0 |   0.0106 |     1.0000 |          0.0479 |        nan      |
| 2024-06 |        1 |            0 |       1 |          0 |  -0.0192 |     0.0000 |         -0.0768 |          0.0000 |
| 2024-07 |        3 |            2 |       1 |          0 |  -0.0060 |     0.6667 |          0.0063 |          1.2481 |
| 2024-08 |        8 |            6 |       2 |          0 |   0.0648 |     0.7500 |          0.0155 |          1.7138 |
| 2024-09 |        0 |            0 |       0 |          0 |  -0.0221 |   nan      |        nan      |        nan      |
| 2024-10 |        4 |            2 |       1 |          1 |  -0.0472 |     0.5000 |         -0.0459 |          0.3378 |
| 2024-11 |        7 |            5 |       2 |          0 |  -0.0113 |     0.7143 |          0.0226 |          1.8640 |
| 2024-12 |        9 |            3 |       6 |          0 |  -0.0451 |     0.3333 |         -0.0467 |          0.2530 |

## Diagnostic counterfactuals—not strategy proposals

| case                             |   return_2024 | method                    |
|:---------------------------------|--------------:|:--------------------------|
| actual frozen strategy           |       -0.0474 | exact OHLC rerun          |
| remove worst 1                   |       -0.0490 | diagnostic exact rerun    |
| remove worst 3                   |        0.0061 | diagnostic exact rerun    |
| remove worst 5                   |        0.0473 | diagnostic exact rerun    |
| cap gap losses at -7.5%          |        0.0382 | diagnostic P&L adjustment |
| exclude entries after prior stop |       -0.0021 | diagnostic exact rerun    |
| daily rank 1 only                |       -0.0852 | diagnostic exact rerun    |

## Normal-variance test

| metric                  |   observed |   probability |   percentile |
|:------------------------|-----------:|--------------:|-------------:|
| negative_year           |    -0.0474 |        0.0916 |       0.0271 |
| year_as_bad_as_2024     |    -0.0474 |        0.0271 |       0.0271 |
| drawdown_as_bad_as_2024 |    -0.1297 |        0.0063 |       0.0063 |

This Monte Carlo uses the observed non-2024 trade-return distribution with ticker-cluster resampling and the actual 2024 trade count. It is a diagnostic approximation, not an independent validation sample.

## Rolling behavior

Rolling 20-trade win rate, return, profit factor and +5% hit rate, plus rolling 6/12-month Sharpe, are saved in the rolling tables and charts. With only five 2023 trades, a 20-trade statistic was not available before 2024; degradation therefore appears as an abrupt 2024 sample effect rather than a long pre-2024 slide. Six-month Sharpe weakened during the 2024 tail-loss cluster and recovered through 2025. There is no evidence of permanent post-2024 decay.

## Explicit answers to the 20 questions

1. 2024 was negative because 15 stops, including 5 gaps, overwhelmed 24 targets; the worst three trades supplied 36.7% of gross losses.
2. Concentrated. The worst month was 2024-10 (-4.7%), and SMCI alone contributed $-7,053 across 15 trades.
3. worst 1: $-7,412, worst 3: $-14,592, worst 5: $-19,130.
4. Yes: 37.5% of 2024 trades stopped versus 30.6% outside 2024.
5. Yes. Five 2024 gap stops averaged -14.2%; the 2024 gap share of stops was 33.3% versus 14.0% otherwise.
6. No. Timeouts were 2.5% in 2024 versus 1.1% outside 2024.
7. No material evidence: only 1 timeout occurred; see the five-day post-timeout audit.
8. No—2024 score-band monotonicity was preserved, so this is not ranking degradation at the coarse-band level.
9. The 2024 probability buckets were overconfident by approximately 11.2% on average, but bucket counts are small.
10. No. At entry, 2024 SPY/QQQ 60-day returns averaged 6.2%/6.2%, both above 2025, while VIX averaged 18.6; 2025 was profitable despite weaker broad-market context.
11. Loss P&L was predominantly idiosyncratic ($-31,160 idiosyncratic versus $-8,601 market-beta classified).
12. Concentration mattered: the worst theme and ticker tables show SMCI and its mapped theme dominated tail losses, rather than every theme failing.
13. Entries after prior stops contributed $-1,380 in 2024; this was secondary to, and overlapping with, the SMCI tail events.
14. No. 2024 losers were less depressed than winners: average 100D RangePosition 29.6% versus 25.3%; they were not systematically bought too early in a deeper decline.
15. Not primarily. During 2024 drawdown days exposure was 12.1% versus 10.7%, but pairwise correlation was lower (0.10 versus 0.43).
16. The ticker-cluster bootstrap assigned a 2.7% probability to a year at least as bad as 2024.
17. Estimated probability of a negative 40-trade year was 9.2% using non-2024 trade clusters.
18. No; its return was at the 2.7% lower-tail probability under the specified clustered bootstrap.
19. No modification clears the evidence bar: gap/ticker tail concentration is economically clear, but an overnight gap cannot realistically be capped and repeat-after-stop performance was positive in later years.
20. Leave the frozen strategy unchanged and move to clean-data/prospective validation; do not optimize against one losing year.

## Decision and next step

**KEEP STRATEGY UNCHANGED.** No modification is supported by the current evidence.

Freeze the current universe, ranking model, quality threshold, -7.5% stop, +5% target, 10-day hold, 25% sizing, and maximum three positions. Proceed to clean point-in-time data validation and prospective scanner observation. A losing year is allowed; fitting a new rule to a handful of SMCI/gap observations would be classic post-hoc overfitting.
