import pandas as pd
import pytest

from src.portfolio import ExitRule, PortfolioRiskRule, run_portfolio
from src.exit_research import mfe_capture_ratio
from src.signals import ConfirmationVariant, generate_confirmation_signals


def panel(opens, highs, lows, closes, signals):
    dates = pd.date_range("2024-01-02", periods=len(opens), freq="B")
    index = pd.MultiIndex.from_product([dates, ["TEST"]], names=["date", "ticker"])
    return pd.DataFrame(
        {
            "adj_open": opens,
            "adj_high": highs,
            "adj_low": lows,
            "adj_close": closes,
            "entry_signal": signals,
            "range_position": [0.1] * len(dates),
            "beta252": [2.5] * len(dates),
            "market_cap": [20e9] * len(dates),
            "market_cap_is_proxy": [False] * len(dates),
            "low_range": [80.0] * len(dates),
            "high_range": [120.0] * len(dates),
            "sma_range": [100.0] * len(dates),
            "distance_sma": [0.0] * len(dates),
            "average_dollar_volume": [200e6] * len(dates),
        },
        index=index,
    )


def test_next_day_execution_no_duplicate_and_position_size():
    data = panel(
        [100, 101, 102, 103, 104], [101, 102, 103, 104, 105], [99, 100, 101, 102, 103],
        [100, 101, 102, 103, 104], [True, True, True, True, True],
    )
    result = run_portfolio(data, ExitRule("hold3", hold_days=3), commission=0, slippage=0)
    first = result.trades.iloc[0]
    assert first["signal_date"] == pd.Timestamp("2024-01-02")
    assert first["entry_date"] == pd.Timestamp("2024-01-03")
    assert first["entry_price"] == 101
    assert first["quantity"] == pytest.approx(10_000 / 101)
    assert len(result.trades.loc[result.trades["entry_date"] == pd.Timestamp("2024-01-03")]) == 1


def test_stop_target_same_bar_is_conservative_and_tracks_excursions():
    data = panel(
        [100, 100, 100], [101, 112, 101], [99, 88, 99], [100, 100, 100], [True, False, False]
    )
    result = run_portfolio(data, ExitRule("bracket", take_profit=.10, stop_loss=.10), commission=0, slippage=0)
    trade = result.trades.iloc[0]
    assert trade["exit_reason"] == "stop_same_bar_conservative"
    assert trade["exit_price"] == 90
    assert trade["mae"] == -0.12
    assert trade["mfe"] == pytest.approx(0.12)


def test_overnight_gap_and_transaction_costs():
    data = panel(
        [100, 100, 80], [101, 101, 81], [99, 99, 79], [100, 100, 80], [True, False, False]
    )
    result = run_portfolio(data, ExitRule("stop", stop_loss=.10), commission=.001, slippage=.001)
    trade = result.trades.iloc[0]
    assert trade["exit_reason"] == "stop_gap"
    assert trade["exit_price"] == 80
    assert trade["net_return"] < trade["gross_return"]
    assert result.equity["cash"].min() >= 0


def test_signal_on_final_day_cannot_execute():
    data = panel([100, 100], [101, 101], [99, 99], [100, 100], [False, True])
    result = run_portfolio(data, ExitRule("hold", hold_days=2), commission=0, slippage=0)
    assert result.trades.empty


def test_confirmation_signal_executes_next_open_only():
    data = panel(
        [100, 101, 105, 106], [101, 102, 106, 107], [99, 100, 104, 105],
        [100, 101, 105, 106], [False, False, False, False],
    )
    data["eligible"] = True
    data["sma20"] = 100.0
    data["previous_5d_return"] = [-.01, .02, -.01, -.01]
    data["entry_signal"] = generate_confirmation_signals(data, ConfirmationVariant.POSITIVE_5D)
    result = run_portfolio(data, ExitRule("hold2", hold_days=2), commission=0, slippage=0)
    trade = result.trades.iloc[0]
    assert trade["signal_date"] == pd.Timestamp("2024-01-03")
    assert trade["entry_date"] == pd.Timestamp("2024-01-04")
    assert trade["entry_price"] == 105


def test_fixed_time_exit_uses_requested_trading_bars():
    data = panel([100]*6, [101]*6, [99]*6, [100]*6, [True]+[False]*5)
    trade = run_portfolio(data, ExitRule("hold4", hold_days=4), commission=0, slippage=0).trades.iloc[0]
    assert trade["holding_days"] == 4
    assert trade["exit_date"] == pd.Timestamp("2024-01-08")
    assert trade["exit_reason"] == "hold4"


def test_trailing_stop_activates_and_uses_high_water_mark():
    data = panel(
        [100, 100, 100, 108, 100], [101, 109, 112, 120, 101],
        [99, 95, 105, 106, 99], [100, 105, 110, 108, 100], [True, False, False, False, False],
    )
    rule = ExitRule("trail10", stop_loss=.15, trail_activation=.10, trailing_stop=.10)
    trade = run_portfolio(data, rule, commission=0, slippage=0).trades.iloc[0]
    assert trade["exit_reason"] == "trailing_stop"
    assert trade["exit_price"] == pytest.approx(108.0)
    assert trade["high_water"] == 120


def test_profit_protection_ratchet_raises_stop_mechanically():
    data = panel(
        [100, 100, 106, 110, 100], [101, 106, 111, 116, 101],
        [99, 101, 104, 106, 99], [100, 105, 109, 107, 100], [True, False, False, False, False],
    )
    rule = ExitRule("ratchet", stop_loss=.15, hold_days=90, profit_ratchet=True)
    trade = run_portfolio(data, rule, commission=0, slippage=0).trades.iloc[0]
    assert trade["exit_reason"] == "ratchet_stop"
    assert trade["exit_price"] == pytest.approx(107.0)


def test_range_exit_is_observed_at_close_and_executes_next_open():
    data = panel([100, 100, 107, 100], [101, 106, 108, 101], [99, 99, 106, 99], [100, 105, 107, 100], [True, False, False, False])
    dates = data.index.get_level_values("date").unique()
    data.loc[(dates[1], "TEST"), "range_position"] = .80
    trade = run_portfolio(data, ExitRule("range75", range_exit=.75, hold_days=90), commission=0, slippage=0).trades.iloc[0]
    assert trade["exit_reason"] == "range75"
    assert trade["exit_date"] == dates[2]
    assert trade["exit_price"] == 107


def test_hybrid_exit_honors_stop_before_range_or_time_exit():
    data = panel([100, 100, 80, 100], [101, 101, 81, 101], [99, 99, 79, 99], [100, 100, 80, 100], [True, False, False, False])
    trade = run_portfolio(data, ExitRule("hybrid", stop_loss=.15, range_exit=.75, hold_days=90), commission=0, slippage=0).trades.iloc[0]
    assert trade["exit_reason"] == "stop_gap"
    assert trade["exit_price"] == 80


def test_mfe_capture_uses_only_profitable_trades_with_positive_mfe():
    trades = pd.DataFrame({"net_return": [.10, .20, -.05], "mfe": [.20, .25, .10]})
    assert mfe_capture_ratio(trades) == pytest.approx((.5 + .8) / 2)


def multi_ticker_panel(tickers, periods=40):
    frames=[]
    for ticker in tickers:
        frame=panel([100.0]*periods,[101.0]*periods,[99.0]*periods,[100.0]*periods,[False]*periods)
        frame=frame.rename(index={"TEST":ticker},level="ticker")
        frame["theme"]="shared"
        frame["qqq_above_sma200"]=True
        frames.append(frame)
    return pd.concat(frames).sort_index()


def test_maximum_positions_and_position_size_are_enforced():
    data=multi_ticker_panel(["A","B","C"],6)
    first=data.index.get_level_values("date").unique()[0]
    data.loc[(first,slice(None)),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold5",hold_days=5),max_positions=2,position_fraction=.05,commission=0,slippage=0)
    assert result.equity.positions.max()==2
    assert result.trades.iloc[0].quantity==pytest.approx(5000/100)


@pytest.mark.parametrize("maximum", [1, 2, 5])
def test_requested_position_limits(maximum):
    data=multi_ticker_panel(["A","B","C","D","E","F"],6); first=data.index.get_level_values("date").unique()[0]
    data.loc[(first,slice(None)),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold5",hold_days=5),max_positions=maximum,position_fraction=.10,commission=0,slippage=0)
    assert result.equity.positions.max()==maximum


@pytest.mark.parametrize("fraction", [.10, .25, .50, .75, 1.0])
def test_requested_current_equity_position_sizes(fraction):
    data=multi_ticker_panel(["A"],6); first=data.index.get_level_values("date").unique()[0]
    data.loc[(first,"A"),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold5",hold_days=5),max_positions=1,position_fraction=fraction,commission=0,slippage=0,size_at_open_equity=True)
    assert result.trades.iloc[0].quantity*result.trades.iloc[0].entry_price==pytest.approx(100_000*fraction)


def test_strict_sequential_does_not_queue_signal_seen_while_held():
    data=multi_ticker_panel(["A","B"],7); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],"A"),"entry_signal"]=True
    data.loc[(dates[2],"B"),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold3",hold_days=3),max_positions=1,commission=0,slippage=0,strict_no_queue=True,track_signals=True)
    assert set(result.trades.ticker)=={"A"}
    assert result.signals.loc[result.signals.ticker.eq("B"),"disposition"].iloc[0]=="ignored_while_full"


def test_strict_sequential_rescans_current_signal_after_exit():
    data=multi_ticker_panel(["A","B"],8); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],"A"),"entry_signal"]=True
    data.loc[(dates[3],"B"),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold3",hold_days=3),max_positions=1,commission=0,slippage=0,strict_no_queue=True)
    assert list(result.trades.ticker)==["A","B"]


def test_stop_lockout_requires_above_then_new_below_signal():
    data=multi_ticker_panel(["A"],10); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],"A"),"entry_signal"]=True
    data.loc[(dates[2:7],"A"),"entry_signal"]=True
    data.loc[(dates[1],"A"),["adj_low","adj_close"]]=[79,80]
    data.loc[(dates[2:5],"A"),"range_position"]=.10
    data.loc[(dates[5],"A"),"range_position"]=.30
    data.loc[(dates[5],"A"),"entry_signal"]=False
    data.loc[(dates[6],"A"),"range_position"]=.10
    result=run_portfolio(data,ExitRule("stop20",stop_loss=.20,hold_days=90),max_positions=1,commission=0,slippage=0,strict_no_queue=True,stop_reentry_lockout=True)
    assert len(result.trades)==2
    assert result.trades.iloc[1].signal_date==dates[6]


def test_signal_tracking_preserves_existing_ranking():
    data=multi_ticker_panel(["A","B"],5); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],slice(None)),"entry_signal"]=True
    data.loc[(dates[0],"A"),"range_position"]=.20
    data.loc[(dates[0],"B"),"range_position"]=.10
    result=run_portfolio(data,ExitRule("hold3",hold_days=3),max_positions=1,commission=0,slippage=0,strict_no_queue=True,track_signals=True)
    assert result.trades.iloc[0].ticker=="B"
    assert result.signals.sort_values("rank").ticker.tolist()==["B","A"]


def test_open_equity_sizing_does_not_use_same_day_close():
    data=multi_ticker_panel(["A","B"],7); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],"A"),"entry_signal"]=True
    data.loc[(dates[1],"B"),"entry_signal"]=True
    data.loc[(dates[2],"A"),"adj_close"]=200.0
    result=run_portfolio(data,ExitRule("hold6",hold_days=6),max_positions=2,position_fraction=.25,commission=0,slippage=0,size_at_open_equity=True)
    b=result.trades.loc[result.trades.ticker.eq("B")].iloc[0]
    assert b.quantity*b.entry_price==pytest.approx(25_000)


def test_gross_exposure_cap_and_portfolio_beta_cap():
    data=multi_ticker_panel(["A","B","C"],6); first=data.index.get_level_values("date").unique()[0]
    data.loc[(first,slice(None)),"entry_signal"]=True
    exposure=run_portfolio(data,ExitRule("hold5",hold_days=5),position_fraction=.10,commission=0,slippage=0,risk_rule=PortfolioRiskRule(gross_exposure_cap=.15))
    assert exposure.equity.positions.max()==1
    allowed=run_portfolio(data,ExitRule("hold5",hold_days=5),position_fraction=.10,commission=0,slippage=0,risk_rule=PortfolioRiskRule(portfolio_beta_cap=.30))
    rejected=run_portfolio(data,ExitRule("hold5",hold_days=5),position_fraction=.10,commission=0,slippage=0,risk_rule=PortfolioRiskRule(portfolio_beta_cap=.20))
    assert allowed.equity.portfolio_beta.max()==pytest.approx(.25)
    assert rejected.trades.empty


def test_theme_cap_rejects_additional_same_theme_position():
    data=multi_ticker_panel(["A","B","C"],6); first=data.index.get_level_values("date").unique()[0]
    data.loc[(first,slice(None)),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold5",hold_days=5),position_fraction=.10,commission=0,slippage=0,risk_rule=PortfolioRiskRule(theme_cap=.15))
    assert result.equity.positions.max()==1


def test_correlation_rule_uses_trailing_history_and_rejects_most_correlated_candidate():
    data=multi_ticker_panel(["A","B"],45); dates=data.index.get_level_values("date").unique()
    prices=pd.Series(100+pd.RangeIndex(len(dates))*1.0,index=dates)
    for ticker in ("A","B"):
        data.loc[(slice(None),ticker),"adj_close"]=prices.to_numpy()
        data.loc[(slice(None),ticker),"adj_open"]=prices.to_numpy()
        data.loc[(slice(None),ticker),"adj_high"]=prices.to_numpy()+1
        data.loc[(slice(None),ticker),"adj_low"]=prices.to_numpy()-1
    data.loc[(dates[0],"A"),"entry_signal"]=True; data.loc[(dates[35],"B"),"entry_signal"]=True
    result=run_portfolio(data,ExitRule("hold90",hold_days=90),commission=0,slippage=0,risk_rule=PortfolioRiskRule(correlation_threshold=.75,correlation_window=60))
    assert set(result.trades.ticker)=={"A"}


def test_qqq_risk_off_rule_caps_new_entry_exposure_without_lookahead():
    data=multi_ticker_panel(["A","B","C","D","E","F"],6); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],slice(None)),"entry_signal"]=True; data.loc[(dates[0],slice(None)),"qqq_above_sma200"]=False
    result=run_portfolio(data,ExitRule("hold5",hold_days=5),commission=0,slippage=0,risk_rule=PortfolioRiskRule(qqq_risk_off=True))
    assert result.equity.positions.max()==5
    changed=data.copy(); changed.loc[(dates[2:],slice(None)),"qqq_above_sma200"]=True
    result_changed=run_portfolio(changed,ExitRule("hold5",hold_days=5),commission=0,slippage=0,risk_rule=PortfolioRiskRule(qqq_risk_off=True))
    assert result_changed.equity.positions.max()==5


def test_drawdown_circuit_breaker_blocks_and_then_recovers():
    data=multi_ticker_panel(["A","B","C"],8); dates=data.index.get_level_values("date").unique()
    data.loc[(dates[0],"A"),"entry_signal"]=True
    data.loc[(dates[2],"B"),"entry_signal"]=True
    data.loc[(dates[5],"C"),"entry_signal"]=True
    for field in ("adj_open","adj_high","adj_low","adj_close"):
        data.loc[(dates[2:5],"A"),field]=79.0
        data.loc[(dates[5:],"A"),field]=100.0
    result=run_portfolio(data,ExitRule("hold90",hold_days=90),max_positions=3,position_fraction=.5,commission=0,slippage=0,risk_rule=PortfolioRiskRule(circuit_breaker=True))
    assert "B" not in set(result.trades.ticker)
    assert "C" in set(result.trades.ticker)
