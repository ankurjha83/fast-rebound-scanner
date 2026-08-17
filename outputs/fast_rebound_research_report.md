# Fast-Rebound Research Report

**Final decision: FAST-REBOUND SIGNAL SHOWS PROMISE**

This is research, not a live-deployment recommendation. The strategy is a new fast-rebound hypothesis and does not inherit the old RangePosition <=25% entry gate.

## Executive result

The model was trained only on complete paths ending by **2022-12-31**. The entire **2023-01-01 through 2026-07-31** primary sample is chronological out-of-sample. The selected quality threshold was 0.636, the selected initial stop was -7.5%, and the best predefined exit was **fixed_5**. It executed 226 trades at 5.22/month, returned 53.32%, had Sharpe 0.82, and maximum drawdown -13.43%.

## Data and execution discipline

- Reused `expanded_panel_nocap.parquet`, cached adjusted/raw OHLCV, strict historical $10B market-cap eligibility, rolling beta, price/liquidity rules, SPY/QQQ/VIX context, transaction costs, and existing portfolio/reporting infrastructure.
- Added 20/50/100-day range and drawdown features, velocity/stabilization fields, next-open 10-day barrier paths, conservative barrier-first/trailing rules, and an interpretable logistic ranker.
- No new market-data download was required. Features use close-T information; entries occur at T+1 open. Gap stops execute at the open. If stop and target are both touched within a daily bar, the adverse barrier is assumed first.
- Model development used 2016-2022 only. No randomized time-series split and no feature selection on 2023-2026 outcomes were used.

## Event-study baseline

|   horizon_days |   plus5_hit_rate |   average_close_return |
|---------------:|-----------------:|-----------------------:|
|         1.0000 |           0.0949 |                -0.0001 |
|         3.0000 |           0.3496 |                 0.0029 |
|         5.0000 |           0.4795 |                 0.0058 |
|        10.0000 |           0.6316 |                 0.0128 |

## Stop and break-even analysis

|   stop |   plus5_before_stop_rate |   eventual_winner_false_stop_rate |   breakeven_before_costs |   theoretical_breakeven_win_rate |   edge_over_breakeven | selected   |
|-------:|-------------------------:|----------------------------------:|-------------------------:|---------------------------------:|----------------------:|:-----------|
| 0.0500 |                   0.4292 |                            0.1753 |                   0.5000 |                           0.5200 |               -0.0908 | False      |
| 0.0750 |                   0.4770 |                            0.0833 |                   0.6000 |                           0.6160 |               -0.1390 | True       |
| 0.1000 |                   0.5024 |                            0.0346 |                   0.6667 |                           0.6800 |               -0.1776 | False      |
| 0.1500 |                   0.5170 |                            0.0066 |                   0.7500 |                           0.7600 |               -0.2430 | False      |

Winner MAE (negative values are adverse):

|   median_mae_before_plus5 |   p75_adverse |   p90_adverse |   p95_adverse |
|--------------------------:|--------------:|--------------:|--------------:|
|                   -0.0233 |       -0.0475 |       -0.0819 |       -0.1048 |

## Pullback and velocity evidence

ATR/velocity quintiles:

| bucket           |   observations |   minimum |   maximum |   plus5_hit_rate |   plus5_before_stop_rate |   average_10d_return |   average_mae |   average_mfe |
|:-----------------|---------------:|----------:|----------:|-----------------:|-------------------------:|---------------------:|--------------:|--------------:|
| (0.0203, 0.0357] |           1834 |    0.0213 |    0.0357 |           0.5185 |                   0.5033 |               0.0051 |       -0.0637 |        0.0698 |
| (0.0357, 0.0425] |           1833 |    0.0357 |    0.0425 |           0.5739 |                   0.5434 |               0.0040 |       -0.0743 |        0.0781 |
| (0.0425, 0.0509] |           1834 |    0.0425 |    0.0509 |           0.6412 |                   0.5851 |               0.0222 |       -0.0739 |        0.0963 |
| (0.0509, 0.0656] |           1833 |    0.0509 |    0.0656 |           0.6552 |                   0.5559 |               0.0046 |       -0.0982 |        0.1026 |
| (0.0656, 0.24]   |           1834 |    0.0656 |    0.2402 |           0.7655 |                   0.6009 |               0.0276 |       -0.1140 |        0.1419 |

Low-versus-high quintile contrasts across all velocity measures:

| feature                          |   low_quintile_plus5 |   high_quintile_plus5 |   low_quintile_before_stop |   high_quintile_before_stop |
|:---------------------------------|---------------------:|----------------------:|---------------------------:|----------------------------:|
| atr_pct                          |               0.5185 |                0.7655 |                     0.5033 |                      0.6009 |
| realized_volatility_10d          |               0.5187 |                0.7480 |                     0.5003 |                      0.6008 |
| realized_volatility_20d          |               0.5242 |                0.7497 |                     0.5077 |                      0.5935 |
| absolute_move_3pct_frequency_60d |               0.5215 |                0.7387 |                     0.5090 |                      0.5705 |
| absolute_move_5pct_frequency_60d |               0.5221 |                0.7581 |                     0.5067 |                      0.5872 |
| plus5_5d_frequency_60d           |               0.5677 |                0.7253 |                     0.5321 |                      0.5796 |
| historical_median_days_to_plus5  |               0.7087 |                0.4472 |                     0.6081 |                      0.4283 |
| beta252                          |               0.6167 |                0.6753 |                     0.5797 |                      0.5276 |

100D RangePosition quintiles:

| bucket          |   observations |   minimum |   maximum |   plus5_hit_rate |   plus5_before_stop_rate |   average_10d_return |   average_mae |   average_mfe |
|:----------------|---------------:|----------:|----------:|-----------------:|-------------------------:|---------------------:|--------------:|--------------:|
| (-0.001, 0.225] |           1651 |    0.0000 |    0.2247 |           0.6402 |                   0.5700 |               0.0211 |       -0.0800 |        0.1049 |
| (0.225, 0.474]  |           1651 |    0.2248 |    0.4739 |           0.6166 |                   0.5439 |               0.0080 |       -0.0866 |        0.0936 |
| (0.474, 0.716]  |           1650 |    0.4741 |    0.7161 |           0.6073 |                   0.5467 |               0.0037 |       -0.0862 |        0.0865 |
| (0.716, 0.907]  |           1651 |    0.7162 |    0.9065 |           0.6269 |                   0.5651 |               0.0129 |       -0.0787 |        0.0953 |
| (0.907, 1.0]    |           1651 |    0.9066 |    1.0000 |           0.6293 |                   0.5591 |               0.0194 |       -0.0780 |        0.0974 |

50D drawdown quintiles:

| bucket             |   observations |   minimum |   maximum |   plus5_hit_rate |   plus5_before_stop_rate |   average_10d_return |   average_mae |   average_mfe |
|:-------------------|---------------:|----------:|----------:|-----------------:|-------------------------:|---------------------:|--------------:|--------------:|
| (-0.634, -0.225]   |           1761 |   -0.6333 |   -0.2255 |           0.7223 |                   0.5974 |               0.0265 |       -0.0991 |        0.1245 |
| (-0.225, -0.14]    |           1760 |   -0.2254 |   -0.1397 |           0.5994 |                   0.5398 |               0.0059 |       -0.0862 |        0.0889 |
| (-0.14, -0.0765]   |           1760 |   -0.1397 |   -0.0765 |           0.5926 |                   0.5375 |               0.0027 |       -0.0809 |        0.0868 |
| (-0.0765, -0.0252] |           1760 |   -0.0764 |   -0.0252 |           0.6068 |                   0.5614 |               0.0102 |       -0.0768 |        0.0904 |
| (-0.0252, 0.0]     |           1761 |   -0.0252 |    0.0000 |           0.6139 |                   0.5491 |               0.0163 |       -0.0773 |        0.0930 |

## Model interpretation and ranking quality

| feature                          |   coefficient |
|:---------------------------------|--------------:|
| plus5_5d_frequency_60d           |        0.3778 |
| distance_sma20                   |        0.1723 |
| realized_volatility_10d          |        0.0403 |
| consecutive_down_days            |        0.0394 |
| close_position_in_day_range      |        0.0259 |
| sma20_slope                      |       -0.0094 |
| atr_pct                          |       -0.0253 |
| volume_relative_20d              |       -0.0321 |
| previous_5d_return               |       -0.1079 |
| drawdown_from_50d_high           |       -0.1399 |
| qqq_20d_return                   |       -0.1580 |
| range_position_100d              |       -0.1732 |
| absolute_move_3pct_frequency_60d |       -0.2229 |

| group        |   observations |   plus5_hit_rate |   plus5_before_stop_rate |   median_days_to_plus5 |   average_10d_close_return |   average_mae |   average_mfe |
|:-------------|---------------:|-----------------:|-------------------------:|-----------------------:|---------------------------:|--------------:|--------------:|
| top_rank     |            897 |           0.6734 |                   0.6109 |                 3.0000 |                     0.0203 |       -0.0873 |        0.1127 |
| top_3        |           2588 |           0.6437 |                   0.5757 |                 3.0000 |                     0.0202 |       -0.0802 |        0.1039 |
| recommended  |            475 |           0.7579 |                   0.6484 |                 2.0000 |                     0.0289 |       -0.1120 |        0.1458 |
| all_eligible |           9313 |           0.6316 |                   0.5576 |                 3.0000 |                     0.0128 |       -0.0852 |        0.0981 |

| group        |   observations |   plus5_1d |   plus5_3d |   plus5_5d |   plus5_10d |   plus10_10d |   plus15_10d |
|:-------------|---------------:|-----------:|-----------:|-----------:|------------:|-------------:|-------------:|
| recommended  |            475 |     0.2232 |     0.5305 |     0.6632 |      0.7579 |       0.5558 |       0.3895 |
| all eligible |           9313 |     0.0949 |     0.3496 |     0.4795 |      0.6316 |       0.3643 |       0.2030 |

## Profit-management comparison

| method            |   total_return |    cagr |   sharpe |   sortino |   maximum_drawdown |   calmar |   number_of_trades |   trades_per_year |   win_rate |   average_trade_return |   median_trade_return |   profit_factor |   average_winner |   average_loser |   best_trade |   worst_trade |   average_mae |   average_mfe |   median_holding_period |   return_per_invested_day |   average_exposure |   annual_turnover |   selection_rank |
|:------------------|---------------:|--------:|---------:|----------:|-------------------:|---------:|-------------------:|------------------:|-----------:|-----------------------:|----------------------:|----------------:|-----------------:|----------------:|-------------:|--------------:|--------------:|--------------:|------------------------:|--------------------------:|-------------------:|------------------:|-----------------:|
| fixed_5           |         0.5332 |  0.1256 |   0.8156 |    1.2347 |            -0.1343 |   0.9356 |                226 |           62.5826 |     0.6726 |                 0.0084 |                0.0479 |          1.2960 |           0.0521 |         -0.0813 |       0.1841 |       -0.2661 |       -0.0526 |        0.0633 |                  2.0000 |                    0.0021 |             0.1076 |           16.4810 |           4.0000 |
| trail_3           |         0.3228 |  0.0805 |   0.5123 |    0.8568 |            -0.1879 |   0.4287 |                228 |           63.1365 |     0.6667 |                 0.0059 |                0.0243 |          1.1859 |           0.0496 |         -0.0815 |       0.2963 |       -0.2661 |       -0.0528 |        0.0641 |                  2.0000 |                    0.0012 |             0.1092 |           16.0442 |           8.0000 |
| trail_5           |        -0.1926 | -0.0575 |  -0.2481 |   -0.3732 |            -0.3414 |  -0.1685 |                220 |           60.9212 |     0.5682 |                -0.0029 |                0.0046 |          0.8628 |           0.0443 |         -0.0650 |       0.2696 |       -0.2661 |       -0.0540 |        0.0704 |                  2.0000 |                   -0.0007 |             0.1217 |           14.1655 |          16.0000 |
| partial_5_trail_5 |         0.1108 |  0.0295 |   0.2613 |    0.3890 |            -0.2123 |   0.1391 |                220 |           60.9212 |     0.6682 |                 0.0028 |                0.0261 |          1.0729 |           0.0446 |         -0.0815 |       0.2205 |       -0.2661 |       -0.0540 |        0.0704 |                  2.0000 |                    0.0004 |             0.1110 |           14.9660 |          12.0000 |

## Continuation after +5%

|   plus7_5 |   plus10 |   plus15 |   plus20 |   median_additional_upside |   p75_additional_upside |   median_retracement |   p75_retracement |   p90_retracement |
|----------:|---------:|---------:|---------:|---------------------------:|------------------------:|---------------------:|------------------:|------------------:|
|    0.7752 |   0.5768 |   0.3215 |   0.1845 |                     0.0621 |                  0.1211 |              -0.0956 |           -0.1433 |           -0.2068 |

## Recommendation frequency

|   recommendations |   days |
|------------------:|-------:|
|                 0 |    679 |
|                 1 |    124 |
|                 2 |     42 |
|                 3 |     89 |

Capital velocity:

|   recommendations_per_month |   trades_per_month |   trades_per_year |   median_days_per_trade |   average_days_per_trade |   return_per_trade |   return_per_invested_day |   annual_turnover |   days_capital_deployed |
|----------------------------:|-------------------:|------------------:|------------------------:|-------------------------:|-------------------:|--------------------------:|------------------:|------------------------:|
|                     10.9612 |             5.2152 |           62.5826 |                  2.0000 |                   2.7389 |             0.0084 |                    0.0021 |           16.4810 |                  0.2867 |

## Year-by-year evidence

| year     |   recommendations |   trades |   plus5_hit_rate |   average_holding_period |   return |   sharpe |   maximum_drawdown |
|:---------|------------------:|---------:|-----------------:|-------------------------:|---------:|---------:|-------------------:|
| 2023     |                12 |        5 |           0.8000 |                   3.6000 |   0.0309 |   0.9975 |            -0.0172 |
| 2024     |                86 |       40 |           0.6000 |                   3.7500 |  -0.0474 |  -0.2695 |            -0.1297 |
| 2025     |               209 |       95 |           0.6632 |                   2.7053 |   0.1464 |   0.7733 |            -0.1343 |
| 2026 YTD |               168 |       86 |           0.6977 |                   2.2558 |   0.3146 |   2.1542 |            -0.1021 |

The 2024 loss is retained and is a material warning against declaring the signal production-ready.

## Matched-random control (5,000 simulations)

| metric                     |   actual |   actual_percentile |   random_p1 |   random_p5 |   random_p25 |   random_p50 |   random_p75 |   random_p95 |   random_p99 |
|:---------------------------|---------:|--------------------:|------------:|------------:|-------------:|-------------:|-------------:|-------------:|-------------:|
| return                     |   0.4775 |              0.9928 |     -0.4076 |     -0.3215 |      -0.1829 |      -0.0669 |       0.0598 |       0.2719 |       0.4571 |
| sharpe                     |   1.0322 |              0.9916 |     -1.1838 |     -0.8650 |      -0.4336 |      -0.1111 |       0.1994 |       0.6541 |       1.0113 |
| plus5_before_stop_hit_rate |   0.6681 |              0.9998 |      0.5221 |      0.5354 |       0.5619 |       0.5796 |       0.5973 |       0.6195 |       0.6372 |
| return_per_invested_day    |   0.0015 |              0.9928 |     -0.0012 |     -0.0010 |      -0.0006 |      -0.0002 |       0.0002 |       0.0008 |       0.0014 |

The control replaces each executed selection with eligible stocks from the same signal date while retaining the actual slot dates and holding-period exposure. It is an exposure-matched sleeve approximation; exact portfolio performance remains the OHLC simulation above.

## Falling-knife failures

| failure           |   count |
|:------------------|--------:|
| fell >10%         |     212 |
| fell >15%         |     132 |
| fell >20%         |      75 |
| no +5% within 10d |     115 |

| path                              |   count |
|:----------------------------------|--------:|
| failed quickly: -5% within 3d     |      91 |
| failed gradually: -5% after 3d    |      23 |
| initially +3%, then <=-7.5%       |      39 |
| rangebound: neither +5% nor -7.5% |       9 |
| recovered after <=-7.5% drawdown  |      53 |

Entry-feature comparison:

| group                 |   observations |   atr_pct |   plus5_5d_frequency_60d |   range_position_100d |   drawdown_from_50d_high |   previous_5d_return |   close_position_in_day_range |   consecutive_down_days |   volume_relative_20d |   qqq_20d_return |
|:----------------------|---------------:|----------:|-------------------------:|----------------------:|-------------------------:|---------------------:|------------------------------:|------------------------:|----------------------:|-----------------:|
| recommended +5%       |            360 |    0.0756 |                   0.6420 |                0.3338 |                  -0.2661 |              -0.0546 |                        0.4834 |                  1.7361 |                0.9883 |          -0.0369 |
| recommended no +5%    |            115 |    0.0688 |                   0.6282 |                0.3624 |                  -0.2549 |              -0.0442 |                        0.4493 |                  1.7565 |                0.9158 |          -0.0131 |
| recommended fell >10% |            212 |    0.0775 |                   0.6595 |                0.3510 |                  -0.2633 |              -0.0502 |                        0.4807 |                  1.8349 |                0.9576 |          -0.0204 |

The detailed recommendation file retains every failure. These overlapping path categories distinguish quick failures, gradual failures, initial bounces that collapsed, rangebound misses, and eventual rebounds after large temporary drawdowns; none were deleted or post-filtered.

## Explicit answers to the 24 research questions

1. Yes. The eligible universe hit +5% within 10 days 63.16% of the time across 9,313 complete stock-days.
2. 1d 9.49%, 3d 34.96%, 5d 47.95%, 10d 63.16%.
3. The strongest interpretable model effects are shown in the coefficient table: frequent historical +5% windows, lower 100D range position, deeper 50D drawdown, and weaker recent QQQ performance were associated with higher conditional odds.
4. Lower range position is informative but not monotonically sufficient; no hard <=25% gate was used.
5. Yes, but as a continuous conditional feature. The model coefficient is -0.173.
6. The deepest 50D-drawdown quintile had the highest raw +5% rate, but also worse adverse paths; the relationship does not justify a narrow hard cutoff.
7. The model combines pullback with close location, consecutive down days, SMA20 slope, recent returns, volatility and relative volume; this reduces but does not eliminate falling-knife risk.
8. Eventual winners' median MAE before +5% was -2.33%; the adverse 90th/95th percentiles were -8.19%/-10.48%.
9. A -7.5% initial stop is the tightest candidate preserving at least 90% of development-period eventual winners; it was selected from MAE/path behavior, not CAGR.
10. -5.0%: 17.53%, -7.5%: 8.33%, -10.0%: 3.46%, -15.0%: 0.66%.
11. For recommended OOS stock-days, P(+5% before -7.5%) was 64.84%; all eligible OOS stock-days were 55.76%.
12. After +5%, continuation reached +10% 57.68%, +15% 32.15%, and +20% 18.45%.
13. Yes in this test: fixed +5% produced the best balanced expectancy and capital velocity (0.84% average trade).
14. No: +5% then 3% trail returned 32.28% with Sharpe 0.51.
15. No: +5% then 5% trail returned -19.26% with Sharpe -0.25.
16. No: partial +5%/5% trail returned 11.08%, below fixed +5%.
17. fixed_5 has the best balanced expectancy among the four predeclared methods.
18. fixed_5 has the best return per invested day.
19. The portfolio generated 5.22 trades/month: MODERATE.
20. 0 recs: 679 days, 1 recs: 124 days, 2 recs: 42 days, 3 recs: 89 days.
21. Yes on hit rate: selected +5% frequency was 75.79% versus 63.16% (20.00% relative lift). Its matched-random +5%-before-stop percentile was 99.98%.
22. Not uniformly: 2024 was negative, while 2023, 2025 and 2026 YTD were positive. The annual table makes the instability explicit.
23. Yes relative to the old strategy: 226 trades, 5.22/month, median 2.0 days, and 28.67% of days deployed.
24. Yes for continued research, not deployment. The OOS ranking lift and frequency justify clean-data validation, but annual instability and tail failures require more evidence.

## Artifacts

- `outputs/tables/fast_rebound_recommendations.csv`: historical daily ranked output with model-derived probabilities.
- `outputs/tables/fast_rebound_latest_candidates.csv`: latest top-three scored candidates, including an explicit `recommended` flag so a no-trade day is not forced.
- `outputs/tables/fast_rebound_profit_methods.csv`: complete method metrics.
- `outputs/tables/fast_rebound_random_control.csv`: matched-random percentiles.
- `outputs/tables/fast_rebound_trades_*.csv` and `fast_rebound_equity_*.parquet`: auditable simulations.
- `outputs/charts/fast_01_*.png` through `fast_15_*.png`: the 15 requested charts.

**Conclusion:** FAST-REBOUND SIGNAL SHOWS PROMISE. The signal solves the opportunity-count problem and ranking adds substantial hit-rate lift, but 2024 weakness, survivorship/market-cap-data limitations in the inherited cache, and observed >10% path failures mean the next step is clean point-in-time data validation—not live trading.
