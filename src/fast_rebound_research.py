"""Fast-rebound event study, chronological ranking, and portfolio research.

The large/liquid/high-beta eligibility rule is inherited unchanged.  This
module intentionally limits the new search to interpretable path features,
four predeclared stops, and four predeclared profit-management methods.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import CONFIG
from src.expanded_retest import _slice, prepare_universe_panel
from src.metrics import performance_metrics
from src.portfolio import BacktestResult
from src.portfolio_risk_research import attach_themes


POSITIVE_LEVELS = (.03, .05, .075, .10, .15)
NEGATIVE_LEVELS = (.03, .05, .075, .10, .15)
STOP_LEVELS = (.05, .075, .10, .15)
HORIZONS = (1, 3, 5, 10)
FEATURES = (
    "atr_pct", "realized_volatility_10d", "absolute_move_3pct_frequency_60d",
    "plus5_5d_frequency_60d", "range_position_100d", "drawdown_from_50d_high",
    "distance_sma20", "previous_5d_return", "close_position_in_day_range",
    "consecutive_down_days", "sma20_slope", "volume_relative_20d",
    "qqq_20d_return",
)
PROFIT_METHODS = ("fixed_5", "trail_3", "trail_5", "partial_5_trail_5")


def _pct_token(level: float) -> str:
    return f"{level * 100:g}".replace(".", "_")


def _level_name(prefix: str, level: float) -> str:
    return f"{prefix}_{_pct_token(level)}pct"


def barrier_first(
    entry_price: float, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
    target: float, stop: float,
) -> tuple[str, int | None, float | None]:
    """Return first barrier using conservative daily-bar ordering.

    Opening gaps are observed first.  If both barriers occur intraday on the
    same bar, the stop is assumed first.
    """
    target_price, stop_price = entry_price * (1 + target), entry_price * (1 - stop)
    for day, (open_price, high, low) in enumerate(zip(opens, highs, lows), 1):
        if open_price <= stop_price:
            return "stop_gap", day, float(open_price)
        if open_price >= target_price:
            return "target_gap", day, float(open_price)
        hit_stop, hit_target = low <= stop_price, high >= target_price
        if hit_stop:
            return "stop", day, float(stop_price)
        if hit_target:
            return "target", day, float(target_price)
    return "none", None, None


def analyze_forward_path(
    entry_price: float, opens: np.ndarray, highs: np.ndarray,
    lows: np.ndarray, closes: np.ndarray,
) -> dict[str, float | bool | str]:
    result: dict[str, float | bool | str] = {}
    for level in POSITIVE_LEVELS:
        hits = np.flatnonzero(highs >= entry_price * (1 + level))
        result[_level_name("hit_plus", level)] = bool(len(hits))
        result[_level_name("days_to_plus", level)] = float(hits[0] + 1) if len(hits) else np.nan
    for level in NEGATIVE_LEVELS:
        hits = np.flatnonzero(lows <= entry_price * (1 - level))
        result[_level_name("hit_minus", level)] = bool(len(hits))
        result[_level_name("days_to_minus", level)] = float(hits[0] + 1) if len(hits) else np.nan
    for horizon in HORIZONS:
        if len(closes) >= horizon:
            result[f"close_return_{horizon}d"] = closes[horizon - 1] / entry_price - 1
            result[f"hit_plus_5_within_{horizon}d"] = bool(np.any(highs[:horizon] >= entry_price * 1.05))
        else:
            result[f"close_return_{horizon}d"] = np.nan
            result[f"hit_plus_5_within_{horizon}d"] = False
    result["mae_10d"] = float(np.min(lows) / entry_price - 1) if len(lows) else np.nan
    result["mfe_10d"] = float(np.max(highs) / entry_price - 1) if len(highs) else np.nan
    plus5 = np.flatnonzero(highs >= entry_price * 1.05)
    if len(plus5):
        hit = int(plus5[0])
        result["mae_before_plus5"] = float(np.min(lows[:hit + 1]) / entry_price - 1)
        result["mfe_after_plus5"] = float(np.max(highs[hit:]) / entry_price - 1)
        high_water = np.maximum.accumulate(highs[hit:])
        result["retracement_after_plus5"] = float(np.min(lows[hit:] / high_water - 1))
    else:
        result["mae_before_plus5"] = np.nan
        result["mfe_after_plus5"] = np.nan
        result["retracement_after_plus5"] = np.nan
    for stop in STOP_LEVELS:
        outcome, day, price = barrier_first(entry_price, opens, highs, lows, .05, stop)
        suffix = _pct_token(stop)
        result[f"plus5_before_stop_{suffix}"] = outcome.startswith("target")
        result[f"barrier_outcome_stop_{suffix}"] = outcome
        result[f"barrier_day_stop_{suffix}"] = float(day) if day else np.nan
        result[f"barrier_price_stop_{suffix}"] = price if price is not None else np.nan
    return result


def _past_plus5_days(open_: pd.Series, high: pd.Series) -> pd.Series:
    entry = open_.shift(-1).to_numpy()
    values = np.full(len(open_), np.nan)
    for offset in range(1, 11):
        future = high.shift(-offset).to_numpy()
        hit = np.isnan(values) & np.isfinite(entry) & (future >= entry * 1.05)
        values[hit] = offset
    return pd.Series(values, index=open_.index)


def _context_series(symbol: str) -> pd.DataFrame:
    frame = pd.read_parquet(CONFIG.cache_dir / "prices" / f"{symbol}.parquet")
    if "date" in frame.columns:
        frame = frame.set_index("date")
    frame.index = pd.to_datetime(frame.index)
    close = frame["adj_close"].sort_index()
    return pd.DataFrame({
        f"{symbol.lower()}_5d_return": close.pct_change(5, fill_method=None),
        f"{symbol.lower()}_20d_return": close.pct_change(20, fill_method=None),
        f"{symbol.lower()}_distance_sma200": close / close.rolling(200).mean() - 1,
    })


def build_event_dataset(panel: pd.DataFrame, start: str = "2016-01-01") -> pd.DataFrame:
    """Build one row per eligible stock-day using only close-T features."""
    spy, qqq = _context_series("SPY"), _context_series("QQQ")
    contexts = spy.join(qqq, how="outer")
    rows: list[dict] = []
    start_date = pd.Timestamp(start)
    for ticker, grouped in panel.groupby(level="ticker", sort=False):
        frame = grouped.droplevel("ticker").sort_index().copy()
        close, high, low, open_, volume = (frame[c] for c in ("adj_close", "adj_high", "adj_low", "adj_open", "volume"))
        previous_close = close.shift(1)
        true_range = pd.concat([high-low, (high-previous_close).abs(), (low-previous_close).abs()], axis=1).max(axis=1)
        for lookback in (20, 50, 100):
            rolling_low, rolling_high = close.rolling(lookback).min(), close.rolling(lookback).max()
            frame[f"range_position_{lookback}d"] = (close-rolling_low)/(rolling_high-rolling_low).replace(0,np.nan)
            frame[f"drawdown_from_{lookback}d_high"] = close/rolling_high-1
        returns = close.pct_change(fill_method=None)
        frame["atr_pct"] = true_range.rolling(14).mean()/close
        frame["realized_volatility_10d"] = returns.rolling(10).std()*np.sqrt(252)
        frame["realized_volatility_20d"] = returns.rolling(20).std()*np.sqrt(252)
        frame["absolute_move_3pct_frequency_60d"] = returns.abs().ge(.03).rolling(60,min_periods=40).mean()
        frame["absolute_move_5pct_frequency_60d"] = returns.abs().ge(.05).rolling(60,min_periods=40).mean()
        five_window_gain = high.rolling(5).max()/close.shift(5)-1
        frame["plus5_5d_frequency_60d"] = five_window_gain.ge(.05).rolling(60,min_periods=40).mean()
        past_days = _past_plus5_days(open_,high)
        frame["historical_median_days_to_plus5"] = past_days.shift(10).rolling(120,min_periods=40).median()
        frame["previous_3d_return"] = close.pct_change(3,fill_method=None)
        for horizon in (5,10,20):
            field=f"previous_{horizon}d_return"
            if field not in frame: frame[field]=close.pct_change(horizon,fill_method=None)
        frame["close_vs_previous_close"] = close/previous_close-1
        frame["close_position_in_day_range"] = (close-low)/(high-low).replace(0,np.nan)
        frame["previous_close_position_in_range"] = frame["close_position_in_day_range"].shift(1)
        frame["volume_relative_20d"] = volume/volume.rolling(20).mean()
        frame["range_position_100d"] = frame.get("range_position_100d",frame.get("range_position"))
        frame["distance_sma100"] = frame.get("distance_sma100",frame.get("distance_sma"))
        for context_column in contexts.columns:
            frame[context_column] = contexts[context_column].reindex(frame.index)
        eligible_locs = np.flatnonzero(frame.get("eligible",pd.Series(False,index=frame.index)).fillna(False).to_numpy() & (frame.index >= start_date))
        for loc in eligible_locs:
            if loc + 1 >= len(frame):
                continue
            end = min(loc + 11, len(frame))
            path = frame.iloc[loc + 1:end]
            if path.empty:
                continue
            signal_row = frame.iloc[loc]
            entry_price = float(path.iloc[0].adj_open)
            record = {
                "date": frame.index[loc], "ticker": ticker, "entry_date": path.index[0],
                "entry_price": entry_price, "market_cap": signal_row.get("historical_market_cap",np.nan),
                "beta252": signal_row.beta252,
            }
            feature_fields = [
                "atr_pct","realized_volatility_10d","realized_volatility_20d",
                "absolute_move_3pct_frequency_60d","absolute_move_5pct_frequency_60d",
                "plus5_5d_frequency_60d","historical_median_days_to_plus5",
                "range_position_20d","range_position_50d","range_position_100d",
                "drawdown_from_20d_high","drawdown_from_50d_high","drawdown_from_100d_high",
                "distance_sma20","distance_sma50","distance_sma100",
                "previous_3d_return","previous_5d_return","previous_10d_return","previous_20d_return",
                "close_vs_previous_close","close_position_in_day_range","previous_close_position_in_range",
                "consecutive_down_days","sma20_slope","sma50_slope","volume_relative_20d",
                "spy_5d_return","spy_20d_return","spy_distance_sma200",
                "qqq_5d_return","qqq_20d_return","qqq_distance_sma200","vix_level",
            ]
            record.update({field: signal_row.get(field,np.nan) for field in feature_fields})
            record.update(analyze_forward_path(
                entry_price, path.adj_open.to_numpy(), path.adj_high.to_numpy(),
                path.adj_low.to_numpy(), path.adj_close.to_numpy(),
            ))
            record["complete_10d_path"] = len(path) == 10
            rows.append(record)
    return pd.DataFrame(rows).sort_values(["date","ticker"]).reset_index(drop=True)


def select_initial_stop(events: pd.DataFrame, development_end: str = "2022-12-31") -> tuple[float,pd.DataFrame]:
    dev=events.loc[pd.to_datetime(events.date).le(pd.Timestamp(development_end)) & events.complete_10d_path]
    winners=dev.loc[dev.hit_plus_5pct]
    rows=[]
    for stop in STOP_LEVELS:
        suffix=_pct_token(stop)
        actual=dev[f"plus5_before_stop_{suffix}"].mean()
        false_stop=1-winners[f"plus5_before_stop_{suffix}"].mean() if len(winners) else np.nan
        breakeven_before=stop/(stop+.05)
        breakeven=(stop+.002)/(stop+.05)  # 0.20% round trip included conservatively
        rows.append({"stop":stop,"plus5_before_stop_rate":actual,"eventual_winner_false_stop_rate":false_stop,
                     "breakeven_before_costs":breakeven_before,"theoretical_breakeven_win_rate":breakeven,
                     "edge_over_breakeven":actual-breakeven})
    table=pd.DataFrame(rows)
    eligible=table.loc[table.eventual_winner_false_stop_rate.le(.10)]
    selected=float(eligible.stop.min()) if len(eligible) else .15
    table["selected"] = table.stop.eq(selected)
    return selected,table


def fit_chronological_model(events: pd.DataFrame, stop: float) -> tuple[Pipeline,float,pd.DataFrame]:
    complete=events.loc[events.complete_10d_path].copy()
    dates=pd.to_datetime(complete.date)
    dev=complete.loc[dates.le(pd.Timestamp("2022-12-31"))]
    suffix=_pct_token(stop)
    target=f"plus5_before_stop_{suffix}"
    model=Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",StandardScaler()),
                    ("logit",LogisticRegression(C=1.0,max_iter=1000,class_weight=None,random_state=CONFIG.random_seed))])
    model.fit(dev[list(FEATURES)],dev[target].astype(int))
    dev_prob=model.predict_proba(dev[list(FEATURES)])[:,1]
    breakeven=(stop+.002)/(stop+.05)
    # A recommendation must clear both the development top quintile and an
    # economic hurdle two probability points above cost-adjusted break-even.
    threshold=float(max(np.quantile(dev_prob,.80),breakeven+.02))
    coefficients=pd.DataFrame({"feature":FEATURES,"coefficient":model.named_steps["logit"].coef_[0]}).sort_values("coefficient",ascending=False)
    coefficients["development_observations"]=len(dev); coefficients["development_base_rate"]=dev[target].mean(); coefficients["recommendation_threshold"]=threshold
    return model,threshold,coefficients


def rank_recommendations(events: pd.DataFrame, model: Pipeline, threshold: float, start: str = "2023-01-01") -> tuple[pd.DataFrame,pd.DataFrame]:
    sample=events.loc[pd.to_datetime(events.date).ge(pd.Timestamp(start)) & events.complete_10d_path].copy()
    sample["estimated_probability"]=model.predict_proba(sample[list(FEATURES)])[:,1]
    sample["fast_rebound_score"]=(sample.estimated_probability*100).round(1)
    sample["daily_rank"]=sample.groupby("date").estimated_probability.rank(method="first",ascending=False).astype(int)
    sample["recommended"]=sample.estimated_probability.ge(threshold)&sample.daily_rank.le(3)
    recommendations=sample.loc[sample.recommended].sort_values(["date","daily_rank"]).copy()
    counts=recommendations.groupby("date").size().reindex(pd.date_range(sample.date.min(),sample.date.max(),freq="B"),fill_value=0)
    distribution=counts.clip(upper=3).value_counts().reindex(range(4),fill_value=0).rename_axis("recommendations").reset_index(name="days")
    return sample,recommendations,distribution


@dataclass
class TradePathResult:
    exit_day: int
    exit_price: float
    exit_reason: str
    gross_return: float
    mae: float
    mfe: float
    partial_day: int | None = None


def simulate_trade_path(entry_price: float, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, initial_stop: float, method: str) -> TradePathResult:
    """Simulate one predeclared profit method over at most ten bars."""
    stop_price=entry_price*(1-initial_stop); active=False; high_water=entry_price
    partial=False; realized_half=0.0; partial_day=None
    trail_pct=.03 if method=="trail_3" else .05
    for i,(op,hi,lo,cl) in enumerate(zip(opens[:10],highs[:10],lows[:10],closes[:10]),1):
        current_stop=high_water*(1-trail_pct) if active else stop_price
        if op<=current_stop:
            ret=op/entry_price-1
            gross=realized_half+.5*ret if partial else ret
            return TradePathResult(i,float(op),"trail_gap" if active else "stop_gap",gross,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1),partial_day)
        if not active and op>=entry_price*1.05:
            if method=="fixed_5": return TradePathResult(i,float(op),"target_gap",op/entry_price-1,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1))
            active=True; high_water=max(high_water,float(op)); partial=method=="partial_5_trail_5"; partial_day=i
            if partial: realized_half=.5*(op/entry_price-1)
        if not active and lo<=stop_price:
            return TradePathResult(i,float(stop_price),"stop",-initial_stop,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1))
        if not active and hi>=entry_price*1.05:
            if method=="fixed_5": return TradePathResult(i,float(entry_price*1.05),"target",.05,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1))
            active=True; high_water=max(high_water,float(hi)); partial=method=="partial_5_trail_5"; partial_day=i
            if partial: realized_half=.025
            raised=high_water*(1-trail_pct)
            if lo<=raised:
                ret=raised/entry_price-1; gross=realized_half+.5*ret if partial else ret
                return TradePathResult(i,float(raised),"same_bar_trail",gross,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1),partial_day)
        elif active:
            high_water=max(high_water,float(hi)); raised=high_water*(1-trail_pct)
            if lo<=raised:
                ret=raised/entry_price-1; gross=realized_half+.5*ret if partial else ret
                return TradePathResult(i,float(raised),"trailing_stop",gross,float(np.min(lows[:i])/entry_price-1),float(np.max(highs[:i])/entry_price-1),partial_day)
    final=float(closes[min(9,len(closes)-1)]); ret=final/entry_price-1; gross=realized_half+.5*ret if partial else ret
    return TradePathResult(min(10,len(closes)),final,"hold10",gross,float(np.min(lows[:10])/entry_price-1),float(np.max(highs[:10])/entry_price-1),partial_day)


def run_fast_portfolio(panel: pd.DataFrame, recommendations: pd.DataFrame, initial_stop: float,
                       method: str, initial_capital: float = 100_000.0) -> BacktestResult:
    """Run maximum-three 25% sleeves with no queued recommendations."""
    if method not in PROFIT_METHODS:
        raise ValueError(f"unknown profit method: {method}")
    data=panel.sort_index(); daily={d:f.droplevel("date") for d,f in data.groupby(level="date",sort=True,observed=True)}
    dates=pd.Index(daily); recs={pd.Timestamp(d):f.sort_values("daily_rank") for d,f in recommendations.groupby("date")}
    positions: dict[str,dict]={}; cash=float(initial_capital); costs=0.; trades=[]; curve=[]; previous_date=None

    def sell(position: dict, raw_price: float, fraction: float) -> float:
        nonlocal cash,costs
        quantity=position["quantity"]*fraction; effective=raw_price*(1-CONFIG.slippage_rate)
        gross=quantity*effective; fee=gross*CONFIG.commission_rate; proceeds=gross-fee
        position["quantity"]-=quantity; position["proceeds"]+=proceeds; position["exit_commission"]+=fee
        cash+=proceeds; costs+=quantity*raw_price-proceeds
        return proceeds

    def close(ticker: str, date: pd.Timestamp, raw_price: float, reason: str) -> None:
        p=positions[ticker]; sell(p,raw_price,1.0); p=positions.pop(ticker)
        trades.append({
            "ticker":ticker,"signal_date":p["signal_date"],"entry_date":p["entry_date"],"exit_date":date,
            "entry_price":p["entry_price"],"exit_price":raw_price,"exit_reason":reason,
            "entry_cash_out":p["entry_cash_out"],"initial_quantity":p["initial_quantity"],
            "holding_days":p["bars"],"gross_return":p["gross_return_realized"] + (raw_price/p["entry_price"]-1)*p["remaining_weight_before_final"],
            "net_return":p["proceeds"]/p["entry_cash_out"]-1,"net_pnl":p["proceeds"]-p["entry_cash_out"],
            "gross_pnl":p["initial_quantity"]*p["entry_price"]*(p["gross_return_realized"] + (raw_price/p["entry_price"]-1)*p["remaining_weight_before_final"]),
            "mae":p["mae"],"mfe":p["mfe"],"entry_commission":p["entry_commission"],"exit_commission":p["exit_commission"],
            "beta":p["beta"],"range_position":p["range_position"],"estimated_probability":p["estimated_probability"],
            "fast_rebound_score":p["fast_rebound_score"],"partial_exit":p["partial"],"partial_day":p["partial_day"],
        })

    for date in dates:
        day=daily[date]
        # Close-T recommendations enter at the next open. Capacity is checked
        # before observing this bar, so an intraday exit cannot create a
        # look-ahead replacement. New positions face the full entry-day path.
        if previous_date is not None and len(positions)<3 and previous_date in recs:
            for rec in recs[previous_date].itertuples():
                if len(positions)>=3: break
                ticker=rec.ticker
                if ticker in positions or ticker not in day.index: continue
                row=day.loc[ticker]; price=float(row.adj_open)
                if not np.isfinite(price) or price<=0: continue
                equity_open=cash+sum(p["quantity"]*float(day.loc[t,"adj_open"]) for t,p in positions.items() if t in day.index)
                budget=min(equity_open*.25,cash); effective=price*(1+CONFIG.slippage_rate)
                quantity=budget/(effective*(1+CONFIG.commission_rate)); notional=quantity*effective; fee=notional*CONFIG.commission_rate; out=notional+fee
                if quantity<=0 or out>cash+1e-8: continue
                cash-=out; costs+=out-quantity*price
                positions[ticker]={"signal_date":previous_date,"entry_date":date,"entry_price":price,"quantity":quantity,"initial_quantity":quantity,
                    "entry_cash_out":out,"entry_commission":fee,"exit_commission":0.,"proceeds":0.,"bars":0,"mae":0.,"mfe":0.,"active":False,
                    "high_water":price,"partial":False,"partial_day":None,"gross_return_realized":0.,"remaining_weight_before_final":1.,
                    "beta":rec.beta252,"range_position":rec.range_position_100d,"estimated_probability":rec.estimated_probability,"fast_rebound_score":rec.fast_rebound_score}
        # Manage existing positions using conservative OHLC ordering.
        for ticker in list(positions):
            if ticker not in day.index: continue
            row=day.loc[ticker]; p=positions[ticker]; p["bars"]+=1
            p["mae"]=min(p["mae"],row.adj_low/p["entry_price"]-1); p["mfe"]=max(p["mfe"],row.adj_high/p["entry_price"]-1)
            trail_pct=.03 if method=="trail_3" else .05
            current_stop=p["high_water"]*(1-trail_pct) if p["active"] else p["entry_price"]*(1-initial_stop)
            if row.adj_open<=current_stop:
                p["remaining_weight_before_final"]=p["quantity"]/p["initial_quantity"]
                close(ticker,date,float(row.adj_open),"trail_gap" if p["active"] else "stop_gap"); continue
            if not p["active"] and row.adj_open>=p["entry_price"]*1.05:
                if method=="fixed_5":
                    p["remaining_weight_before_final"]=1.; close(ticker,date,float(row.adj_open),"target_gap"); continue
                p["active"]=True; p["high_water"]=max(p["high_water"],float(row.adj_open))
                if method=="partial_5_trail_5":
                    sold_weight=p["quantity"]*.5/p["initial_quantity"]; p["gross_return_realized"]+=sold_weight*(row.adj_open/p["entry_price"]-1)
                    sell(p,float(row.adj_open),.5); p["partial"]=True; p["partial_day"]=p["bars"]
            initial_stop_price=p["entry_price"]*(1-initial_stop)
            if not p["active"] and row.adj_low<=initial_stop_price:
                p["remaining_weight_before_final"]=1.; close(ticker,date,float(initial_stop_price),"stop"); continue
            if not p["active"] and row.adj_high>=p["entry_price"]*1.05:
                if method=="fixed_5":
                    p["remaining_weight_before_final"]=1.; close(ticker,date,float(p["entry_price"]*1.05),"target"); continue
                p["active"]=True; p["high_water"]=max(p["high_water"],float(row.adj_high))
                if method=="partial_5_trail_5":
                    sold_weight=p["quantity"]*.5/p["initial_quantity"]; p["gross_return_realized"]+=sold_weight*.05
                    sell(p,float(p["entry_price"]*1.05),.5); p["partial"]=True; p["partial_day"]=p["bars"]
                raised=p["high_water"]*(1-trail_pct)
                if row.adj_low<=raised:
                    p["remaining_weight_before_final"]=p["quantity"]/p["initial_quantity"]; close(ticker,date,float(raised),"same_bar_trail"); continue
            elif p["active"]:
                p["high_water"]=max(p["high_water"],float(row.adj_high)); raised=p["high_water"]*(1-trail_pct)
                if row.adj_low<=raised:
                    p["remaining_weight_before_final"]=p["quantity"]/p["initial_quantity"]; close(ticker,date,float(raised),"trailing_stop"); continue
            if ticker in positions and p["bars"]>=10:
                p["remaining_weight_before_final"]=p["quantity"]/p["initial_quantity"]; close(ticker,date,float(row.adj_close),"hold10")

        market_value=sum(p["quantity"]*float(day.loc[t,"adj_close"]) for t,p in positions.items() if t in day.index)
        equity=cash+market_value
        curve.append({"date":date,"equity":equity,"gross_equity":equity+costs,"cumulative_costs":costs,"cash":cash,"market_value":market_value,
                      "positions":len(positions),"exposure":market_value/equity if equity else 0.})
        previous_date=date
    if dates.size:
        date=dates[-1]; day=daily[date]
        for ticker in list(positions):
            if ticker in day.index:
                positions[ticker]["remaining_weight_before_final"]=positions[ticker]["quantity"]/positions[ticker]["initial_quantity"]
                close(ticker,date,float(day.loc[ticker,"adj_close"]),"end_of_test")
        if curve: curve[-1].update({"equity":cash,"gross_equity":cash+costs,"cash":cash,"market_value":0.,"positions":0,"exposure":0.})
    return BacktestResult(pd.DataFrame(curve).set_index("date"),pd.DataFrame(trades))


def fast_metrics(result: BacktestResult) -> dict[str,float]:
    m=performance_metrics(result.equity,result.trades); t=result.trades; e=result.equity
    years=max((e.index[-1]-e.index[0]).days/365.25,1/252) if len(e) else np.nan
    invested_days=int(e.exposure.gt(0).sum()) if len(e) else 0
    m.update({
        "unique_stocks":t.ticker.nunique() if len(t) else 0,"trades_per_year":len(t)/years if years else np.nan,
        "trades_per_month":len(t)/(years*12) if years else np.nan,"median_holding_period":t.holding_days.median() if len(t) else np.nan,
        "average_mae":t.mae.mean() if len(t) else np.nan,"median_mae":t.mae.median() if len(t) else np.nan,
        "average_mfe":t.mfe.mean() if len(t) else np.nan,"median_mfe":t.mfe.median() if len(t) else np.nan,
        "return_per_invested_day":m.get("total_return",np.nan)/invested_days if invested_days else np.nan,
        "invested_days":invested_days,"percentage_days_deployed":e.exposure.gt(0).mean() if len(e) else np.nan,
        "average_exposure":e.exposure.mean() if len(e) else np.nan,
        "annual_turnover":t.entry_cash_out.sum()/e.equity.mean()/years if len(t) and years else np.nan,
        "exit_within_1d":t.holding_days.le(1).mean() if len(t) else np.nan,"exit_within_3d":t.holding_days.le(3).mean() if len(t) else np.nan,
        "exit_within_5d":t.holding_days.le(5).mean() if len(t) else np.nan,"exit_within_10d":t.holding_days.le(10).mean() if len(t) else np.nan,
    })
    return m


def ranking_quality(sample: pd.DataFrame, stop: float) -> pd.DataFrame:
    suffix=_pct_token(stop); target=f"plus5_before_stop_{suffix}"
    groups={"top_rank":sample.loc[sample.daily_rank.eq(1)],"top_3":sample.loc[sample.daily_rank.le(3)],"recommended":sample.loc[sample.recommended],"all_eligible":sample}
    rows=[]
    for label,g in groups.items():
        hit_days=g.loc[g.hit_plus_5pct,"days_to_plus_5pct"]
        rows.append({"group":label,"observations":len(g),"plus5_hit_rate":g.hit_plus_5pct.mean(),"plus5_before_stop_rate":g[target].mean(),
                     "median_days_to_plus5":hit_days.median(),"average_10d_close_return":g.close_return_10d.mean(),"average_mae":g.mae_10d.mean(),"average_mfe":g.mfe_10d.mean()})
    return pd.DataFrame(rows)
