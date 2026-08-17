# Fast-Rebound Theme-Concentration Diagnostic

**Final decision: KEEP 3×33.33% UNCHANGED**

The frozen 3×33.33% architecture reproduced exactly: 226 trades, 74.13% total return, 16.60% CAGR, Sharpe 0.83, and -17.64% maximum drawdown. No signal, threshold, stop, target, holding-period, execution, or cost assumption changed.

## Executive diagnosis

The evidence does **not** justify a permanent theme rule. Max-two-per-theme improved the historical return slightly, but it skipped only four theme-conflicting signals and removed **zero** maximum drawdown, worst-day, or governing gap risk. Max-one sacrificed return and Sharpe without improving maximum drawdown. The 66.67% entry-time cap was nearly indistinguishable from base. This fails the predeclared standard for material, generalizable risk removal.

## Mapping audit

The original 97.3% figure occurred on 2026-07-01 when AVGO, WDC, and STX were all assigned to the residual `other` bucket because two names were unmapped. The audited broad mapping separates AVGO into AI/semiconductors and WDC/STX into data infrastructure. The true audited maximum was 99.48%: ALB|ENPH|TSLA in **EV / clean technology**, from 2024-04-19 to 2024-04-23. The complete mapping is `outputs/tables/theme_mapping_audited.csv`.

## Most important comparison

| architecture     |   total_return |   cagr |   sharpe |   maximum_drawdown |   calmar |   2024_return |   worst_day |   worst_week |   average_exposure |   max_same_theme_exposure |   simultaneous_stop_dates |   largest_combined_gap_loss |   skipped_trades |   skipped_average_return |   top_10pct_removed_return |
|:-----------------|---------------:|-------:|---------:|-------------------:|---------:|--------------:|------------:|-------------:|-------------------:|--------------------------:|--------------------------:|----------------------------:|-----------------:|-------------------------:|---------------------------:|
| BASE 3x33.33     |         0.7413 | 0.1660 |   0.8252 |            -0.1764 |   0.9410 |       -0.0673 |     -0.0993 |      -0.1245 |             0.1431 |                    0.9948 |                         9 |                     -0.0887 |                0 |                 nan      |                     0.3350 |
| MAX 2 SAME THEME |         0.7735 | 0.1719 |   0.8521 |            -0.1764 |   0.9746 |       -0.0798 |     -0.0993 |      -0.1245 |             0.1427 |                    0.6823 |                         9 |                     -0.0887 |                4 |                   0.0234 |                     0.3378 |
| MAX 1 SAME THEME |         0.6481 | 0.1484 |   0.7899 |            -0.1764 |   0.8410 |       -0.1221 |     -0.0993 |      -0.1245 |             0.1351 |                    0.3575 |                         9 |                     -0.0887 |               87 |                   0.0232 |                     0.1364 |
| 66.67% THEME CAP |         0.7451 | 0.1667 |   0.8324 |            -0.1764 |   0.9450 |       -0.0935 |     -0.0993 |      -0.1245 |             0.1422 |                    0.6825 |                         9 |                     -0.0887 |                2 |                  -0.0770 |                     0.3155 |

The 66.67% cap is enforced only at entry; existing positions are not rebalanced, so market drift can move realized theme exposure modestly above the cap.

## Portfolio-day classifications

| category                                      |   portfolio_days |   pct_invested_days |   average_exposure |   average_fast_rebound_score |   portfolio_return |   annualized_volatility |   negative_return_contribution |
|:----------------------------------------------|-----------------:|--------------------:|-------------------:|-----------------------------:|-------------------:|------------------------:|-------------------------------:|
| A. ONE POSITION                               |              156 |              0.6000 |             0.3310 |                      65.8288 |             0.1081 |                  0.3027 |                        -0.9533 |
| B. TWO POSITIONS — DIFFERENT THEMES           |               67 |              0.2577 |             0.6580 |                      66.5433 |             0.0480 |                  0.3164 |                        -0.4679 |
| C. TWO POSITIONS — SAME THEME                 |                8 |              0.0308 |             0.6544 |                      67.4125 |             0.0838 |                  0.3897 |                        -0.0305 |
| D. THREE POSITIONS — ALL DIFFERENT THEMES     |               10 |              0.0385 |             0.9906 |                      67.7167 |             0.0517 |                  0.2880 |                        -0.0516 |
| E. THREE POSITIONS — TWO SAME + ONE DIFFERENT |               16 |              0.0615 |             0.9940 |                      66.1958 |            -0.1665 |                  0.4734 |                        -0.3000 |
| F. THREE POSITIONS — ALL SAME THEME           |                3 |              0.0115 |             0.9948 |                      65.6667 |             0.0102 |                  0.2586 |                        -0.0116 |

## Basket comparison

| classification       |   observations |   average_basket_return |   median_basket_return |   win_rate |   plus5_hit_rate |   stop_rate |   simultaneous_stop_rate |   average_mae |   average_mfe |   worst_basket_loss |   average_correlation_20d |   average_correlation_60d |   average_holding_period |   return_per_invested_day |
|:---------------------|---------------:|------------------------:|-----------------------:|-----------:|-----------------:|------------:|-------------------------:|--------------:|--------------:|--------------------:|--------------------------:|--------------------------:|-------------------------:|--------------------------:|
| ALL DIFFERENT THEMES |             58 |                  0.0019 |                 0.0010 |     0.5345 |           0.6508 |      0.2778 |                   0.1034 |       -0.0596 |        0.0642 |             -0.0807 |                    0.4894 |                    0.3934 |                   4.7845 |                    0.0015 |
| ALL SAME THEME       |              7 |                  0.0133 |                 0.0102 |     0.7143 |           0.6000 |      0.4000 |                   0.2857 |       -0.0624 |        0.0512 |             -0.0212 |                    0.6495 |                    0.6003 |                   4.5476 |                    0.0085 |
| PARTIALLY SAME THEME |             10 |                 -0.0179 |                -0.0234 |     0.2000 |           0.4333 |      0.5667 |                   0.6000 |       -0.0836 |        0.0552 |             -0.0420 |                    0.3874 |                    0.3845 |                   5.6000 |                   -0.0112 |

The direct three-position comparison, which removes two-stock episodes from the label comparison, is:

| classification       |   observations |   average_basket_return |   median_basket_return |   win_rate |   plus5_hit_rate |   stop_rate |   simultaneous_stop_rate |   average_mae |   average_mfe |   worst_basket_loss |   average_correlation_20d |   average_correlation_60d |   average_holding_period |   return_per_invested_day |
|:---------------------|---------------:|------------------------:|-----------------------:|-----------:|-----------------:|------------:|-------------------------:|--------------:|--------------:|--------------------:|--------------------------:|--------------------------:|-------------------------:|--------------------------:|
| ALL DIFFERENT THEMES |             10 |                  0.0052 |                 0.0038 |     0.5000 |           0.7333 |      0.2000 |                   0.1000 |       -0.0512 |        0.0676 |             -0.0191 |                    0.5069 |                    0.3644 |                   4.0000 |                    0.0052 |
| ALL SAME THEME       |              1 |                  0.0102 |                 0.0102 |     1.0000 |           1.0000 |      0.0000 |                   0.0000 |       -0.0513 |        0.0808 |              0.0102 |                    0.5084 |                    0.4399 |                   5.3333 |                    0.0034 |
| PARTIALLY SAME THEME |             10 |                 -0.0179 |                -0.0234 |     0.2000 |           0.4333 |      0.5667 |                   0.6000 |       -0.0836 |        0.0552 |             -0.0420 |                    0.3874 |                    0.3845 |                   5.6000 |                   -0.0112 |

## First, second, and third theme positions

|   theme_position_order |   trades |   average_score |   plus5_hit_rate |   average_return |   median_return |   profit_factor |   stop_rate |   average_mae |   average_mfe |   average_holding_period |   total_incremental_pnl |   approximate_cagr_contribution |   realized_negative_pnl_contribution |   worst_exit_day_contribution |
|-----------------------:|---------:|----------------:|-----------------:|-----------------:|----------------:|----------------:|------------:|--------------:|--------------:|-------------------------:|------------------------:|--------------------------------:|-------------------------------------:|------------------------------:|
|                 1.0000 | 189.0000 |         67.5556 |           0.6720 |           0.0087 |          0.0479 |          1.3231 |      0.3175 |       -0.0520 |        0.0634 |                   2.7302 |              66513.3159 |                          0.1530 |                              -1.6719 |                       -0.0887 |
|                 2.0000 |  35.0000 |         67.7286 |           0.6571 |           0.0068 |          0.0479 |          1.2119 |      0.3143 |       -0.0550 |        0.0620 |                   2.7714 |               8965.3771 |                          0.0243 |                              -0.2956 |                       -0.0284 |
|                 3.0000 |   2.0000 |         66.4500 |           0.5000 |           0.0070 |          0.0070 |          0.6964 |      0.5000 |       -0.0720 |        0.0782 |                   3.0000 |              -1351.4431 |                         -0.0038 |                              -0.0253 |                       -0.0253 |

Order is determined using positions already open immediately before each next-open entry, with same-day lower ranks counted first. These are descriptive contributions, not randomized causal estimates.

## Skipped alpha

| architecture     |   skipped_trades |   skipped_plus5_hit_rate |   skipped_stop_rate |   average_skipped_return |   median_skipped_return |   skipped_profit_factor |
|:-----------------|-----------------:|-------------------------:|--------------------:|-------------------------:|------------------------:|------------------------:|
| 66.67% THEME CAP |                2 |                   1.0000 |              1.0000 |                  -0.0770 |                 -0.0770 |                  0.0000 |
| MAX 1 SAME THEME |               87 |                   0.8276 |              0.2414 |                   0.0232 |                  0.0480 |                  2.1955 |
| MAX 2 SAME THEME |                4 |                   1.0000 |              0.5000 |                   0.0234 |                  0.0071 |                  1.6079 |

The full skipped-event ledger retains score, rank, hypothetical fixed-rule return, MAE, MFE, target, and stop outcomes.

## Correlation evidence

| correlation_bucket   |   baskets |   average_correlation_20d |   average_correlation_60d |   average_basket_return |   plus5_hit_rate |   simultaneous_stop_rate |   average_basket_drawdown |   worst_basket_loss |   gap_losses |
|:---------------------|----------:|--------------------------:|--------------------------:|------------------------:|-----------------:|-------------------------:|--------------------------:|--------------------:|-------------:|
| LOW <0.30            |        18 |                    0.2660 |                    0.1798 |                  0.0009 |           0.5610 |                   0.1111 |                   -0.0080 |             -0.0381 |            2 |
| MODERATE 0.30-0.60   |        50 |                    0.5306 |                    0.4502 |                  0.0017 |           0.6435 |                   0.1800 |                   -0.0124 |             -0.0807 |            3 |
| HIGH >0.60           |         6 |                    0.8064 |                    0.7530 |                 -0.0089 |           0.4615 |                   0.5000 |                   -0.0115 |             -0.0215 |            3 |

Correlations are trailing 20/60-session close-return correlations measured at basket formation, without future information. Theme labels and actual correlations do not map one-for-one.

## Simultaneous stops and gaps

| date                |   positions_stopped | tickers       | themes                                                | same_theme   |   correlation_20d |   correlation_60d | individual_losses       |   gap_throughs |   portfolio_loss |   spy_return |   qqq_return |
|:--------------------|--------------------:|:--------------|:------------------------------------------------------|:-------------|------------------:|------------------:|:------------------------|---------------:|-----------------:|-------------:|-------------:|
| 2025-02-25 00:00:00 |                   2 | PLTR|SMCI     | software|data infrastructure                          | False        |            0.4184 |            0.2768 | -0.0768|-0.0768         |              0 |          -0.0185 |      -0.0050 |      -0.0126 |
| 2025-03-03 00:00:00 |                   2 | ANET|SMCI     | data infrastructure|data infrastructure               | True         |            0.5019 |            0.3655 | -0.0768|-0.0768         |              0 |          -0.0673 |      -0.0175 |      -0.0219 |
| 2025-04-04 00:00:00 |                   3 | VST|ANET|PLTR | power / industrial|data infrastructure|software       | False        |            0.7782 |            0.5897 | -0.0951|-0.0797|-0.0768 |              2 |          -0.0563 |      -0.0585 |      -0.0621 |
| 2025-04-08 00:00:00 |                   3 | PLTR|VST|DELL | software|power / industrial|data infrastructure       | False        |            0.7843 |            0.5513 | -0.0768|-0.0768|-0.0768 |              0 |          -0.0768 |      -0.0157 |      -0.0180 |
| 2025-11-19 00:00:00 |                   2 | COIN|MU       | crypto-linked|AI / semiconductors                     | False        |            0.6003 |            0.5450 | -0.0768|-0.0768         |              0 |          -0.0334 |       0.0039 |       0.0060 |
| 2025-11-20 00:00:00 |                   3 | SMCI|COIN|MU  | data infrastructure|crypto-linked|AI / semiconductors | False        |            0.3316 |            0.4634 | -0.0768|-0.0768|-0.0768 |              0 |          -0.0690 |      -0.0152 |      -0.0237 |
| 2026-03-30 00:00:00 |                   2 | AMD|SNDK      | AI / semiconductors|data infrastructure               | False        |            0.6352 |            0.3590 | -0.0768|-0.0768         |              0 |          -0.0593 |      -0.0033 |      -0.0076 |
| 2026-07-02 00:00:00 |                   2 | WDC|STX       | data infrastructure|data infrastructure               | True         |            0.9479 |            0.8689 | -0.0768|-0.0768         |              0 |          -0.0471 |      -0.0013 |      -0.0173 |
| 2026-07-17 00:00:00 |                   2 | SMCI|CIEN     | data infrastructure|data infrastructure               | True         |            0.5307 |            0.4044 | -0.0844|-0.0853         |              2 |          -0.0182 |      -0.0099 |      -0.0150 |

| theme_context                   |   gaps |   average_gap_portfolio_impact |   largest_single_gap |
|:--------------------------------|-------:|-------------------------------:|---------------------:|
| multiple                        |      2 |                        -0.0273 |              -0.0284 |
| single                          |     11 |                        -0.0376 |              -0.0887 |
| largest two-position combined   |      2 |                       nan      |              -0.0582 |
| largest three-position combined |      3 |                       nan      |             nan      |

The ten worst portfolio days provide the loss-state check requested. Correlations are measured through the preceding session, so they do not leak the loss day:

| date                |   portfolio_return |   positions_at_risk | tickers       | themes                                                      | duplicate_theme   |   prior_close_exposure |   correlation_20d_before_loss |   correlation_60d_before_loss |   spy_return |   qqq_return |
|:--------------------|-------------------:|--------------------:|:--------------|:------------------------------------------------------------|:------------------|-----------------------:|------------------------------:|------------------------------:|-------------:|-------------:|
| 2024-10-30 00:00:00 |            -0.0993 |                   1 | SMCI          | data infrastructure                                         | False             |                 0.3411 |                      nan      |                      nan      |      -0.0030 |      -0.0076 |
| 2025-04-08 00:00:00 |            -0.0768 |                   3 | DELL|PLTR|VST | data infrastructure|software|power / industrial             | False             |                 0.0000 |                        0.7843 |                        0.5513 |      -0.0157 |      -0.0180 |
| 2025-11-20 00:00:00 |            -0.0690 |                   3 | COIN|MU|SMCI  | crypto-linked|AI / semiconductors|data infrastructure       | False             |                 0.3356 |                        0.3316 |                        0.4634 |      -0.0152 |      -0.0237 |
| 2025-03-03 00:00:00 |            -0.0673 |                   2 | ANET|SMCI     | data infrastructure|data infrastructure                     | True              |                 0.3488 |                        0.5019 |                        0.3655 |      -0.0175 |      -0.0219 |
| 2026-03-26 00:00:00 |            -0.0650 |                   3 | AMD|COIN|SNDK | AI / semiconductors|crypto-linked|data infrastructure       | False             |                 0.6690 |                        0.4351 |                        0.2487 |      -0.0179 |      -0.0239 |
| 2026-03-30 00:00:00 |            -0.0593 |                   2 | AMD|SNDK      | AI / semiconductors|data infrastructure                     | False             |                 0.3372 |                        0.6352 |                        0.3590 |      -0.0033 |      -0.0076 |
| 2025-03-06 00:00:00 |            -0.0572 |                   3 | ANET|MPWR|ON  | data infrastructure|AI / semiconductors|AI / semiconductors | True              |                 0.9966 |                        0.3269 |                        0.4265 |      -0.0178 |      -0.0275 |
| 2025-04-04 00:00:00 |            -0.0563 |                   3 | ANET|PLTR|VST | data infrastructure|software|power / industrial             | False             |                 0.6464 |                        0.7782 |                        0.5897 |      -0.0585 |      -0.0621 |
| 2025-04-21 00:00:00 |            -0.0499 |                   2 | PLTR|VST      | software|power / industrial                                 | False             |                 0.3343 |                        0.8213 |                        0.5517 |      -0.0238 |      -0.0247 |
| 2026-07-02 00:00:00 |            -0.0471 |                   3 | AVGO|STX|WDC  | AI / semiconductors|data infrastructure|data infrastructure | True              |                 0.9734 |                        0.6959 |                        0.6162 |      -0.0013 |      -0.0173 |

## Theme-by-theme outcomes

| theme                 | holding_context   |   trades |   total_pnl |   average_return |   median_return |   plus5_hit_rate |   stop_rate |   profit_factor |   average_mae |   average_mfe |   worst_trade |
|:----------------------|:------------------|---------:|------------:|-----------------:|----------------:|-----------------:|------------:|----------------:|--------------:|--------------:|--------------:|
| AI / semiconductors   | multiple          |       15 |  14441.2663 |           0.0249 |          0.0479 |           0.8000 |      0.1333 |          2.4026 |       -0.0373 |        0.0646 |       -0.0801 |
| AI / semiconductors   | single            |       40 |  20941.2834 |           0.0116 |          0.0479 |           0.6750 |      0.3000 |          1.5266 |       -0.0502 |        0.0586 |       -0.0866 |
| EV / clean technology | multiple          |        4 |   3651.2751 |           0.0275 |          0.0479 |           0.7500 |      0.2500 |          2.3063 |       -0.0527 |        0.0731 |       -0.0768 |
| EV / clean technology | single            |        8 |   4595.3799 |           0.0167 |          0.0479 |           0.7500 |      0.2500 |          1.8227 |       -0.0499 |        0.0608 |       -0.0768 |
| consumer              | single            |        1 |   1610.8558 |           0.0479 |          0.0479 |           1.0000 |      0.0000 |        nan      |       -0.0010 |        0.0778 |        0.0479 |
| crypto-linked         | single            |       20 |   5466.5275 |           0.0049 |          0.0479 |           0.6500 |      0.3500 |          1.2328 |       -0.0476 |        0.0522 |       -0.0914 |
| data infrastructure   | multiple          |       17 | -12151.2690 |          -0.0164 |         -0.0768 |           0.4706 |      0.5294 |          0.6391 |       -0.0755 |        0.0532 |       -0.0853 |
| data infrastructure   | single            |       65 |   7997.6003 |           0.0032 |          0.0479 |           0.6308 |      0.3538 |          1.0911 |       -0.0578 |        0.0676 |       -0.2661 |
| power / industrial    | multiple          |        1 |   1672.6616 |           0.0479 |          0.0479 |           1.0000 |      0.0000 |        nan      |       -0.0153 |        0.1613 |        0.0479 |
| power / industrial    | single            |       10 |    257.7408 |           0.0026 |          0.0479 |           0.6000 |      0.4000 |          1.0216 |       -0.0661 |        0.0796 |       -0.0951 |
| software              | single            |       45 |  25643.9281 |           0.0149 |          0.0479 |           0.7333 |      0.2667 |          1.6871 |       -0.0456 |        0.0630 |       -0.0966 |

`single` and `multiple` indicate whether the trade was the first or an additional same-theme position at entry.

## High-concentration episodes

|   threshold | start_date          | end_date            | theme                 | stocks              |   maximum_same_theme_exposure |   average_portfolio_exposure | scores              | trade_outcomes                                 |   portfolio_return |   maximum_drawdown |
|------------:|:--------------------|:--------------------|:----------------------|:--------------------|------------------------------:|-----------------------------:|:--------------------|:-----------------------------------------------|-------------------:|-------------------:|
|      0.5000 | 2023-01-04 00:00:00 | 2023-01-05 00:00:00 | AI / semiconductors   | AMD|NVDA            |                        0.6671 |                       0.6632 | 68.4|66.7           | AMD:-7.68%|NVDA:4.79%                          |            -0.0212 |            -0.0230 |
|      0.5000 | 2024-04-19 00:00:00 | 2024-04-23 00:00:00 | EV / clean technology | ALB|ENPH|TSLA       |                        0.9948 |                       0.9948 | 68.2|64.7|64.1      | ENPH:4.79%|ALB:4.79%|TSLA:9.09%                |             0.0102 |            -0.0116 |
|      0.5000 | 2024-07-22 00:00:00 | 2024-07-23 00:00:00 | EV / clean technology | ALB|AMD|ENPH        |                        0.6627 |                       1.0000 | 67.6|65.1|64.7      | ENPH:4.79%|AMD:-7.68%|ALB:4.79%                |            -0.0068 |            -0.0150 |
|      0.5000 | 2024-08-07 00:00:00 | 2024-08-09 00:00:00 | AI / semiconductors   | AMD|NVDA|TSLA       |                        0.6708 |                       0.9932 | 69.5|67.1|66.3      | NVDA:4.79%|TSLA:4.79%|AMD:4.79%                |             0.0015 |            -0.0445 |
|      0.5000 | 2025-02-24 00:00:00 | 2025-02-24 00:00:00 | data infrastructure   | ANET|PLTR|SMCI      |                        0.6723 |                       0.9997 | 71.8|65.2|64.2      | PLTR:-7.68%|ANET:-7.68%|SMCI:-7.68%            |            -0.0379 |            -0.0379 |
|      0.5000 | 2025-03-05 00:00:00 | 2025-03-12 00:00:00 | AI / semiconductors   | ANET|MPWR|ON        |                        0.6823 |                       0.9457 | 66.2|64.5|63.9|66.1 | ON:-7.68%|ANET:-7.68%|MPWR:4.79%|ANET:4.79%    |            -0.0426 |            -0.0796 |
|      0.5000 | 2026-03-31 00:00:00 | 2026-03-31 00:00:00 | AI / semiconductors   | AMD|LRCX            |                        0.6680 |                       0.6680 | 69.8|73.2           | LRCX:4.79%|AMD:4.79%                           |             0.0475 |             0.0000 |
|      0.5000 | 2026-06-10 00:00:00 | 2026-06-10 00:00:00 | data infrastructure   | STX|WDC             |                        0.6521 |                       0.6521 | 67.3|63.6           | WDC:4.79%|STX:4.79%                            |             0.0046 |             0.0000 |
|      0.5000 | 2026-07-01 00:00:00 | 2026-07-01 00:00:00 | data infrastructure   | AVGO|STX|WDC        |                        0.6547 |                       0.9734 | 67.2|71.3|65.4      | AVGO:4.79%|WDC:-7.68%|STX:-7.68%               |            -0.0215 |            -0.0215 |
|      0.5000 | 2026-07-09 00:00:00 | 2026-07-09 00:00:00 | AI / semiconductors   | AMAT|KLAC           |                        0.6479 |                       0.6479 | 68.9|68.9           | KLAC:-7.68%|AMAT:-8.01%                        |            -0.0046 |            -0.0046 |
|      0.5000 | 2026-07-16 00:00:00 | 2026-07-16 00:00:00 | data infrastructure   | CIEN|QCOM|SMCI      |                        0.6572 |                       0.9997 | 67.0|65.9|65.1      | SMCI:-8.44%|CIEN:-8.53%|QCOM:-7.68%            |            -0.0420 |            -0.0420 |
|      0.5000 | 2026-07-21 00:00:00 | 2026-07-24 00:00:00 | AI / semiconductors   | COIN|KLAC|QCOM|SMCI |                        0.6587 |                       0.8046 | 65.1|68.2|68.2|64.3 | QCOM:-7.68%|SMCI:18.41%|KLAC:-7.68%|COIN:4.79% |             0.0410 |            -0.0282 |
|      0.5000 | 2026-07-28 00:00:00 | 2026-07-28 00:00:00 | AI / semiconductors   | COIN|INTC|QCOM      |                        0.6472 |                       1.0000 | 65.1|64.3|64.5      | QCOM:-7.68%|COIN:4.79%|INTC:4.79%              |            -0.0145 |            -0.0145 |
|      0.6667 | 2023-01-04 00:00:00 | 2023-01-04 00:00:00 | AI / semiconductors   | AMD|NVDA            |                        0.6671 |                       0.6671 | 68.4|66.7           | AMD:-7.68%|NVDA:4.79%                          |             0.0018 |             0.0000 |
|      0.6667 | 2024-04-19 00:00:00 | 2024-04-23 00:00:00 | EV / clean technology | ALB|ENPH|TSLA       |                        0.9948 |                       0.9948 | 68.2|64.7|64.1      | ENPH:4.79%|ALB:4.79%|TSLA:9.09%                |             0.0102 |            -0.0116 |
|      0.6667 | 2024-08-08 00:00:00 | 2024-08-09 00:00:00 | AI / semiconductors   | AMD|NVDA|TSLA       |                        0.6708 |                       0.9933 | 69.5|67.1|66.3      | NVDA:4.79%|TSLA:4.79%|AMD:4.79%                |             0.0481 |            -0.0039 |
|      0.6667 | 2025-02-24 00:00:00 | 2025-02-24 00:00:00 | data infrastructure   | ANET|PLTR|SMCI      |                        0.6723 |                       0.9997 | 71.8|65.2|64.2      | PLTR:-7.68%|ANET:-7.68%|SMCI:-7.68%            |            -0.0379 |            -0.0379 |
|      0.6667 | 2025-03-05 00:00:00 | 2025-03-05 00:00:00 | AI / semiconductors   | ANET|MPWR|ON        |                        0.6678 |                       0.9966 | 66.2|64.5|63.9      | ON:-7.68%|ANET:-7.68%|MPWR:4.79%               |             0.0278 |             0.0000 |
|      0.6667 | 2025-03-07 00:00:00 | 2025-03-12 00:00:00 | AI / semiconductors   | ANET|MPWR|ON        |                        0.6823 |                       0.9203 | 66.2|64.5|63.9|66.1 | ON:-7.68%|ANET:-7.68%|MPWR:4.79%|ANET:4.79%    |            -0.0119 |            -0.0379 |
|      0.6667 | 2026-03-31 00:00:00 | 2026-03-31 00:00:00 | AI / semiconductors   | AMD|LRCX            |                        0.6680 |                       0.6680 | 69.8|73.2           | LRCX:4.79%|AMD:4.79%                           |             0.0475 |             0.0000 |
|      0.9000 | 2024-04-19 00:00:00 | 2024-04-23 00:00:00 | EV / clean technology | ALB|ENPH|TSLA       |                        0.9948 |                       0.9948 | 68.2|64.7|64.1      | ENPH:4.79%|ALB:4.79%|TSLA:9.09%                |             0.0102 |            -0.0116 |

The audited >90% clean-technology episode held ENPH, ALB, and TSLA. Its realized path and eventual trade outcomes are retained above; it did not produce the strategy's maximum drawdown. This is economically concentrated, but one episode cannot establish a reliable cap benefit.

## 2024

There were 5 portfolio-days above 66.67% audited same-theme exposure in 2024. SMCI is classified as data infrastructure; its overlaps are included in the episode and basket tables. Base returned -6.73%; max-two worsened to -7.98%, max-one to -12.21%, and the 66.67% cap to -9.35%. Theme restrictions therefore do not fix the 2024 loss.

## Alpha lost versus risk removed

| architecture     |   alpha_lost |   risk_removed |   cagr_sacrificed_per_drawdown_removed |   return_sacrificed_per_skipped_trade |
|:-----------------|-------------:|---------------:|---------------------------------------:|--------------------------------------:|
| BASE 3x33.33     |       0.0000 |         0.0000 |                                    nan |                              nan      |
| MAX 2 SAME THEME |      -0.0322 |         0.0000 |                                    nan |                               -0.0080 |
| MAX 1 SAME THEME |       0.0932 |         0.0000 |                                    nan |                                0.0011 |
| 66.67% THEME CAP |      -0.0038 |         0.0000 |                                    nan |                               -0.0019 |

## Annual comparison

| architecture     |   year |   return |   sharpe |   maximum_drawdown |   trades |   average_exposure |
|:-----------------|-------:|---------:|---------:|-------------------:|---------:|-------------------:|
| BASE 3x33.33     |   2023 |   0.0413 |   0.9991 |            -0.0230 |        5 |             0.0174 |
| BASE 3x33.33     |   2024 |  -0.0673 |  -0.2701 |            -0.1717 |       40 |             0.1407 |
| BASE 3x33.33     |   2025 |   0.1923 |   0.7863 |            -0.1721 |       95 |             0.2163 |
| BASE 3x33.33     |   2026 |   0.5036 |   2.3842 |            -0.1340 |       86 |             0.2314 |
| MAX 2 SAME THEME |   2023 |   0.0413 |   0.9991 |            -0.0230 |        5 |             0.0174 |
| MAX 2 SAME THEME |   2024 |  -0.0798 |  -0.3592 |            -0.1717 |       40 |             0.1381 |
| MAX 2 SAME THEME |   2025 |   0.1923 |   0.7863 |            -0.1721 |       95 |             0.2163 |
| MAX 2 SAME THEME |   2026 |   0.5524 |   2.5491 |            -0.1340 |       86 |             0.2335 |
| MAX 1 SAME THEME |   2023 |   0.0245 |   0.6951 |            -0.0236 |        4 |             0.0133 |
| MAX 1 SAME THEME |   2024 |  -0.1221 |  -0.6576 |            -0.1717 |       37 |             0.1182 |
| MAX 1 SAME THEME |   2025 |   0.1910 |   0.7917 |            -0.1576 |       93 |             0.2165 |
| MAX 1 SAME THEME |   2026 |   0.5386 |   2.7885 |            -0.1204 |       77 |             0.2274 |
| 66.67% THEME CAP |   2023 |   0.0402 |   0.9774 |            -0.0230 |        5 |             0.0172 |
| 66.67% THEME CAP |   2024 |  -0.0935 |  -0.4459 |            -0.1717 |       40 |             0.1368 |
| 66.67% THEME CAP |   2025 |   0.1920 |   0.7853 |            -0.1724 |       95 |             0.2164 |
| 66.67% THEME CAP |   2026 |   0.5526 |   2.5507 |            -0.1341 |       86 |             0.2334 |

## Tail robustness

| architecture     | sensitivity          |   total_return |   cagr |   sharpe |   maximum_drawdown |   trades |
|:-----------------|:---------------------|---------------:|-------:|---------:|-------------------:|---------:|
| BASE 3x33.33     | base                 |         0.7413 | 0.1660 |   0.8252 |            -0.1764 |      226 |
| BASE 3x33.33     | remove_best_trade    |         0.7454 | 0.1668 |   0.8269 |            -0.1764 |      226 |
| BASE 3x33.33     | remove_best_5_trades |         0.4921 | 0.1172 |   0.6221 |            -0.2009 |      226 |
| BASE 3x33.33     | remove_top_10pct     |         0.3350 | 0.0833 |   0.4819 |            -0.2009 |      216 |
| BASE 3x33.33     | remove_best_ticker   |         0.5242 | 0.1238 |   0.6648 |            -0.1764 |      213 |
| BASE 3x33.33     | remove_best_theme    |         0.3317 | 0.0825 |   0.5193 |            -0.1668 |      185 |
| MAX 2 SAME THEME | base                 |         0.7735 | 0.1719 |   0.8521 |            -0.1764 |      226 |
| MAX 2 SAME THEME | remove_best_trade    |         0.7776 | 0.1727 |   0.8537 |            -0.1764 |      226 |
| MAX 2 SAME THEME | remove_best_5_trades |         0.5433 | 0.1277 |   0.6668 |            -0.2009 |      226 |
| MAX 2 SAME THEME | remove_top_10pct     |         0.3378 | 0.0839 |   0.4833 |            -0.2009 |      220 |
| MAX 2 SAME THEME | remove_best_ticker   |         0.5524 | 0.1295 |   0.6917 |            -0.1764 |      213 |
| MAX 2 SAME THEME | remove_best_theme    |         0.3240 | 0.0808 |   0.4999 |            -0.1668 |      194 |
| MAX 1 SAME THEME | base                 |         0.6481 | 0.1484 |   0.7899 |            -0.1764 |      211 |
| MAX 1 SAME THEME | remove_best_trade    |         0.6737 | 0.1533 |   0.8126 |            -0.1764 |      212 |
| MAX 1 SAME THEME | remove_best_5_trades |         0.3693 | 0.0909 |   0.5313 |            -0.2009 |      212 |
| MAX 1 SAME THEME | remove_top_10pct     |         0.1364 | 0.0360 |   0.2785 |            -0.2009 |      206 |
| MAX 1 SAME THEME | remove_best_ticker   |         0.4424 | 0.1068 |   0.6188 |            -0.1764 |      198 |
| MAX 1 SAME THEME | remove_best_theme    |         0.3492 | 0.0865 |   0.5452 |            -0.1668 |      174 |
| 66.67% THEME CAP | base                 |         0.7451 | 0.1667 |   0.8324 |            -0.1764 |      226 |
| 66.67% THEME CAP | remove_best_trade    |         0.7487 | 0.1674 |   0.8336 |            -0.1764 |      226 |
| 66.67% THEME CAP | remove_best_5_trades |         0.5184 | 0.1226 |   0.6467 |            -0.2009 |      226 |
| 66.67% THEME CAP | remove_top_10pct     |         0.3155 | 0.0789 |   0.4621 |            -0.2009 |      220 |
| 66.67% THEME CAP | remove_best_ticker   |         0.5276 | 0.1245 |   0.6711 |            -0.1764 |      213 |
| 66.67% THEME CAP | remove_best_theme    |         0.3014 | 0.0757 |   0.4781 |            -0.1668 |      196 |

No restricted architecture met the deterministic hurdle for a matched-random rerun: at least two percentage points of drawdown reduction while preserving 90% of CAGR and Sharpe. Therefore no `theme_random_control.csv` was created, as instructed.

## Explicit answers to the 20 questions

1. Partly: second same-theme positions added $8,965, but the two third positions lost $1,351. This is descriptive, not proof of independent alpha.
2. Not demonstrably. All restrictions left maximum drawdown at approximately -17.6%.
3. No clear reduction: the base largest single-gap impact was -8.9%, and predefined restrictions did not remove the governing gap episode.
4. No clear evidence. There were 9 multi-stop dates, of which 3 involved duplicate themes.
5. Only partly; basket 60-day correlations are reported by label and ranged across low/moderate/high buckets. Theme membership was an imperfect proxy.
6. Yes: 35 second-theme trades averaged 0.68%, profit factor 1.21.
7. Insufficient evidence: only 2 third-theme trades existed. Their unweighted mean was 0.70%, but profit factor was 0.70 and total P&L was $-1,351.
8. Second positions contributed $8,965; third positions contributed $-1,351.
9. Three-different-theme basket risk was not consistently lower across drawdown, simultaneous-stop, and correlation measures; see the basket summary.
10. Their relative profitability is shown directly in the basket summary; the limited three-position episode count prevents a strong causal conclusion.
11. No material risk improvement. Max-two returned 77.3% versus 74.1%, but drawdown remained -17.6%; the apparent gain depends on only 4 skipped trades.
12. No. Max-one reduced return to 64.8%, Sharpe to 0.79, and did not improve maximum drawdown.
13. No material improvement. The entry-time 66.67% cap returned 74.5% with unchanged -17.6% drawdown.
14. MAX 2 SAME THEME: -3.2%, MAX 1 SAME THEME: 9.3%, 66.67% THEME CAP: -0.4% return difference versus base.
15. MAX 2 SAME THEME: 0.0%, MAX 1 SAME THEME: 0.0%, 66.67% THEME CAP: 0.0% drawdown removed.
16. No. 2024 had 5 days above 66.67% audited same-theme exposure. Base returned -6.7%; max-two -8.0%, max-one -12.2%, and the cap -9.3%.
17. No. The largest drawdown persisted unchanged under every predefined restriction, so concentration was not its causal mechanism.
18. Yes. Point-in-time return correlation distinguishes low/moderate/high overlap inside the same broad labels and is more granular than the audited themes, but no correlation rule was tested.
19. The original 97.3% residual-'other' observation was a mapping artifact (AVGO/WDC/STX). The audited maximum was 99.5% in EV / clean technology (ALB|ENPH|TSLA); its portfolio return was 1.0% and drawdown -1.2%. It is a plausible stress risk, but historical harm is not established.
20. No. The predefined caps failed to remove the actual maximum drawdown or governing gap loss, while max-one discarded material alpha and max-two's improvement rested on four skips.

## Decision

**KEEP 3×33.33% UNCHANGED.** Same-theme exposure should remain a monitored risk diagnostic, particularly for a high-alpha sleeve, but the historical evidence does not support changing the frozen architecture. Do not add a theme cap based on four skipped max-two observations or a single clean-technology concentration episode.
