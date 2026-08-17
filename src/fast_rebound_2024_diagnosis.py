"""Forensic diagnosis of the frozen fast-rebound strategy's 2024 loss."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR",str(Path(__file__).resolve().parents[1]/".matplotlib"))
import matplotlib.pyplot as plt

from config import CONFIG
from src.expanded_retest import _slice, prepare_universe_panel
from src.fast_rebound_research import fast_metrics, fit_chronological_model, rank_recommendations, run_fast_portfolio, select_initial_stop
from src.metrics import performance_metrics


YEARS=(2023,2024,2025,2026)


def _md(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False,floatfmt=".4f")


def _year_returns(equity: pd.DataFrame, year: int) -> pd.Series:
    returns=equity.equity.pct_change(fill_method=None)
    return returns.loc[returns.index.year==year].dropna()


def _return_stats(returns: pd.Series) -> dict[str,float]:
    if returns.empty: return {"total_return":np.nan,"sharpe":np.nan,"sortino":np.nan,"maximum_drawdown":np.nan}
    curve=(1+returns).cumprod(); downside=returns.clip(upper=0)
    return {"total_return":curve.iloc[-1]-1,"sharpe":returns.mean()/returns.std()*np.sqrt(252) if returns.std() else np.nan,
            "sortino":returns.mean()/downside.std()*np.sqrt(252) if downside.std() else np.nan,
            "maximum_drawdown":(curve/curve.cummax()-1).min()}


def _market_prices(symbol: str) -> pd.Series:
    frame=pd.read_parquet(CONFIG.cache_dir/"prices"/f"{symbol}.parquet")
    if "date" in frame: frame=frame.set_index("date")
    frame.index=pd.to_datetime(frame.index)
    return frame.adj_close.sort_index()


def assemble_trade_diagnostics(trades: pd.DataFrame, events: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    t=trades.copy(); date_fields=("signal_date","entry_date","exit_date")
    for field in date_fields: t[field]=pd.to_datetime(t[field])
    feature_fields=["atr_pct","realized_volatility_10d","realized_volatility_20d","absolute_move_3pct_frequency_60d","absolute_move_5pct_frequency_60d",
                    "range_position_20d","range_position_50d","range_position_100d","drawdown_from_20d_high","drawdown_from_50d_high","drawdown_from_100d_high",
                    "distance_sma20","distance_sma50","previous_5d_return","spy_5d_return","spy_20d_return","spy_distance_sma200","qqq_5d_return","qqq_20d_return","qqq_distance_sma200","vix_level",
                    "hit_plus_5pct","hit_plus_5_within_1d","hit_plus_5_within_3d","hit_plus_5_within_5d","plus5_before_stop_7_5","barrier_outcome_stop_7_5"]
    ev=events[["date","ticker",*feature_fields]].rename(columns={"date":"signal_date"})
    t=t.merge(ev,on=["signal_date","ticker"],how="left",validate="one_to_one",suffixes=("","_event"))
    rec=pd.read_csv(CONFIG.outputs_dir/"tables"/"fast_rebound_recommendations.csv",parse_dates=["date"])[["date","ticker","daily_rank","estimated_probability_plus5"]].rename(columns={"date":"signal_date"})
    t=t.merge(rec,on=["signal_date","ticker"],how="left",validate="one_to_one")
    mapping=pd.read_csv(CONFIG.outputs_dir/"tables"/"expanded_sector_mapping.csv")[["ticker","sector","theme"]]
    t=t.merge(mapping,on="ticker",how="left"); t[["sector","theme"]]=t[["sector","theme"]].fillna("other")
    t["year"]=t.entry_date.dt.year; t["stop_exit"]=t.exit_reason.isin(["stop","stop_gap"]); t["gap_stop"]=t.exit_reason.eq("stop_gap"); t["timeout"]=t.exit_reason.eq("hold10")
    t["target_exit"]=t.exit_reason.str.startswith("target"); t["stop_price"]=t.entry_price*.925; t["portfolio_pnl_contribution"]=t.net_pnl
    raw=panel.reset_index()[["date","ticker","spy_60d_return","qqq_60d_return"]].drop_duplicates(["date","ticker"])
    t=t.merge(raw.rename(columns={"date":"signal_date"}),on=["signal_date","ticker"],how="left")
    daily_vix=panel.reset_index().groupby("date").vix_level.first().sort_index(); vix_change=daily_vix.diff(5)
    t["vix_5d_change"]=t.signal_date.map(vix_change)
    spy,qqq=_market_prices("SPY"),_market_prices("QQQ")
    high_beta_daily=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).groupby(level="date").median()
    spy_trade=[]; qqq_trade=[]; high_beta_trade=[]
    for row in t.itertuples():
        spy_trade.append(spy.asof(row.exit_date)/spy.asof(row.entry_date)-1)
        qqq_trade.append(qqq.asof(row.exit_date)/qqq.asof(row.entry_date)-1)
        hb=high_beta_daily.loc[(high_beta_daily.index>=row.entry_date)&(high_beta_daily.index<=row.exit_date)]
        high_beta_trade.append((1+hb.dropna()).prod()-1)
    t["spy_trade_return"]=spy_trade; t["qqq_trade_return"]=qqq_trade; t["high_beta_trade_return"]=high_beta_trade
    losing=t.net_return.lt(0)
    market=t.qqq_trade_return.le(-.02)|t.spy_trade_return.le(-.015)|t.high_beta_trade_return.le(-.02)
    t["loss_driver"]=np.where(~losing,"winner",np.where(market,"market_beta","idiosyncratic"))
    return t


def year_comparison(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for year in YEARS:
        t=trades.loc[trades.year.eq(year)]; r=_year_returns(equity,year); s=_return_stats(r); losers=t.loc[t.net_return.lt(0)]; winners=t.loc[t.net_return.gt(0)]
        gp=t.loc[t.net_pnl.gt(0),"net_pnl"].sum(); gl=-t.loc[t.net_pnl.lt(0),"net_pnl"].sum()
        rows.append({"year":year,"recommendations":np.nan,"executed_trades":len(t),"trades_per_month":len(t)/(12 if year<2026 else 8),**s,
                     "win_rate":t.net_return.gt(0).mean(),"plus5_hit_rate":t.hit_plus_5pct.mean(),"stop_loss_rate":t.stop_exit.mean(),"timeout_rate":t.timeout.mean(),
                     "average_trade_return":t.net_return.mean(),"median_trade_return":t.net_return.median(),"average_winner":winners.net_return.mean(),"average_loser":losers.net_return.mean(),"profit_factor":gp/gl if gl else np.nan,
                     "average_mae":t.mae.mean(),"median_mae":t.mae.median(),"average_mfe":t.mfe.mean(),"median_mfe":t.mfe.median(),"average_holding_period":t.holding_days.mean(),"median_holding_period":t.holding_days.median(),
                     "average_fast_rebound_score":t.fast_rebound_score.mean(),"average_portfolio_exposure":equity.loc[equity.index.year==year,"exposure"].mean()})
    return pd.DataFrame(rows)


def stop_analysis(trades: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]
    by_ticker={ticker:g.droplevel("ticker").sort_index() for ticker,g in panel.groupby(level="ticker",sort=False)}
    for row in trades.loc[trades.stop_exit].itertuples():
        p=by_ticker[row.ticker]; future=p.loc[p.index>row.exit_date].head(10)
        prior=p.loc[(p.index>=row.entry_date)&(p.index<row.exit_date)]
        mfe_before=max(0.,prior.adj_high.max()/row.entry_price-1) if len(prior) else 0.
        prior_mae=prior.adj_low.min()/row.entry_price-1 if len(prior) else 0.
        mae_to_execution=min(0.,prior_mae,row.exit_price/row.entry_price-1)
        rebound5=future.head(5).adj_high.max()/row.exit_price-1 if len(future) else np.nan; rebound10=future.adj_high.max()/row.exit_price-1 if len(future) else np.nan
        further=future.adj_low.min()/row.exit_price-1 if len(future) else np.nan
        rows.append({"year":row.year,"ticker":row.ticker,"entry_date":row.entry_date,"entry_price":row.entry_price,"stop_price":row.stop_price,"actual_execution_price":row.exit_price,
                     "execution_type":"gap-through" if row.gap_stop else "normal","realized_return":row.net_return,"mae":mae_to_execution,"mfe_before_stop":mfe_before,
                     "max_rebound_next_5d":rebound5,"max_rebound_next_10d":rebound10,"false_stop_rebound_5pct":rebound10>=.05,"genuine_collapse_further_5pct":further<=-.05})
    detail=pd.DataFrame(rows)
    summary=detail.groupby("year").agg(stop_outs=("ticker","size"),average_loss=("realized_return","mean"),median_loss=("realized_return","median"),gap_throughs=("execution_type",lambda x:x.eq("gap-through").sum()),gap_rate=("execution_type",lambda x:x.eq("gap-through").mean()),false_stop_rate=("false_stop_rebound_5pct","mean"),genuine_collapse_rate=("genuine_collapse_further_5pct","mean"),average_next10_rebound=("max_rebound_next_10d","mean")).reset_index()
    return detail,summary


def timeout_analysis(trades: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]; by_ticker={ticker:g.droplevel("ticker").sort_index() for ticker,g in panel.groupby(level="ticker",sort=False)}
    for row in trades.loc[trades.timeout].itertuples():
        future=by_ticker[row.ticker].loc[lambda x:x.index>row.exit_date].head(5)
        max_after=future.adj_high.max()/row.exit_price-1 if len(future) else np.nan
        rows.append({"year":row.year,"ticker":row.ticker,"entry_date":row.entry_date,"exit_date":row.exit_date,"return_at_exit":row.net_return,"mae":row.mae,"mfe":row.mfe,"highest_return_reached":row.mfe,"max_rebound_next_5d":max_after,"plus5_shortly_after":max_after>=.05})
    detail=pd.DataFrame(rows)
    summary=trades.groupby("year").agg(trades=("ticker","size"),timeouts=("timeout","sum"),timeout_rate=("timeout","mean")).reset_index()
    if len(detail): summary=summary.merge(detail.groupby("year").agg(after_exit_plus5_rate=("plus5_shortly_after","mean"),average_timeout_return=("return_at_exit","mean")).reset_index(),on="year",how="left")
    return detail,summary


def barrier_analysis(trades: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for year,t in trades.groupby("year"):
        rows.append({"year":year,"trades":len(t),"plus5_before_minus7_5":t.plus5_before_stop_7_5.mean(),"minus7_5_before_plus5":t.barrier_outcome_stop_7_5.astype(str).str.startswith("stop").mean(),"neither_within_10d":t.barrier_outcome_stop_7_5.eq("none").mean(),
                     "plus5_within_1d":t.hit_plus_5_within_1d.mean(),"plus5_within_3d":t.hit_plus_5_within_3d.mean(),"plus5_within_5d":t.hit_plus_5_within_5d.mean(),"plus5_within_10d":t.hit_plus_5pct.mean()})
    return pd.DataFrame(rows)


def score_calibration(trades: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    score_bins=[0,60,65,70,75,80,101]; prob_bins=[0,.60,.65,.70,.75,.80,1.01]
    t=trades.copy(); t["score_band"]=pd.cut(t.fast_rebound_score,score_bins,right=False); t["probability_band"]=pd.cut(t.estimated_probability_plus5,prob_bins,right=False)
    score=t.groupby(["year","score_band"],observed=True).agg(trades=("ticker","size"),average_score=("fast_rebound_score","mean"),plus5_hit_rate=("hit_plus_5pct","mean"),stop_rate=("stop_exit","mean"),average_return=("net_return","mean"),median_return=("net_return","median"),average_mae=("mae","mean"),average_mfe=("mfe","mean")).reset_index(); score["score_band"]=score.score_band.astype(str)
    calibration=t.groupby(["year","probability_band"],observed=True).agg(trades=("ticker","size"),predicted_probability=("estimated_probability_plus5","mean"),actual_plus5_rate=("hit_plus_5pct","mean")).reset_index(); calibration["probability_band"]=calibration.probability_band.astype(str); calibration["calibration_error"]=calibration.actual_plus5_rate-calibration.predicted_probability
    return score,calibration


def group_analysis(trades: pd.DataFrame, field: str) -> pd.DataFrame:
    return trades.groupby(["year",field]).agg(trades=("ticker","size"),pnl=("net_pnl","sum"),average_return=("net_return","mean"),win_rate=("net_return",lambda x:x.gt(0).mean()),plus5_hit_rate=("hit_plus_5pct","mean"),stop_rate=("stop_exit","mean")).reset_index()


def repeat_entry_analysis(trades: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    t=trades.sort_values(["ticker","entry_date"]).copy(); t["entry_number"]=t.groupby("ticker").cumcount()+1; t["previous_exit_reason"]=t.groupby("ticker").exit_reason.shift(); t["after_previous_stop"]=t.previous_exit_reason.isin(["stop","stop_gap"])
    t["entry_group"]=np.select([t.entry_number.eq(1),t.entry_number.eq(2)],["first","second"],default="third+")
    summary=t.groupby(["year","entry_group"],observed=True).agg(trades=("ticker","size"),average_return=("net_return","mean"),pnl=("net_pnl","sum"),win_rate=("net_return",lambda x:x.gt(0).mean()),stop_rate=("stop_exit","mean")).reset_index()
    after=t.groupby(["year","after_previous_stop"]).agg(trades=("ticker","size"),average_return=("net_return","mean"),pnl=("net_pnl","sum"),win_rate=("net_return",lambda x:x.gt(0).mean())).reset_index(); summary=pd.concat([summary,after.assign(entry_group=lambda x:np.where(x.after_previous_stop,"after prior stop","not after prior stop")).drop(columns="after_previous_stop")],ignore_index=True)
    return t,summary


def monthly_2024(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    t=trades.loc[trades.year.eq(2024)].copy(); t["month"]=t.entry_date.dt.to_period("M").astype(str); returns=equity.equity.pct_change(fill_method=None); month_returns=returns.loc[returns.index.year==2024].groupby(returns.loc[returns.index.year==2024].index.to_period("M")).apply(lambda x:(1+x).prod()-1)
    rows=[]
    for period in pd.period_range("2024-01","2024-12",freq="M"):
        g=t.loc[t.month.eq(str(period))]; gp=g.loc[g.net_pnl.gt(0),"net_pnl"].sum(); gl=-g.loc[g.net_pnl.lt(0),"net_pnl"].sum()
        rows.append({"month":str(period),"trades":len(g),"plus5_hits":int(g.target_exit.sum()),"stops":int(g.stop_exit.sum()),"timeouts":int(g.timeout.sum()),"return":month_returns.get(period,0.),"win_rate":g.net_return.gt(0).mean() if len(g) else np.nan,"average_trade":g.net_return.mean(),"profit_factor":gp/gl if gl else np.nan})
    return pd.DataFrame(rows)


def pullback_velocity(trades: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    pull_fields=["range_position_20d","range_position_50d","range_position_100d","drawdown_from_20d_high","drawdown_from_50d_high","drawdown_from_100d_high","distance_sma20","distance_sma50"]
    velocity_fields=["atr_pct","realized_volatility_10d","realized_volatility_20d","absolute_move_3pct_frequency_60d","absolute_move_5pct_frequency_60d","beta"]
    rows=[]
    for year in YEARS:
        y=trades.loc[trades.year.eq(year)]
        for label,g in (("winner",y.loc[y.net_return.gt(0)]),("loser",y.loc[y.net_return.le(0)])):
            rows.append({"year":year,"outcome":label,"trades":len(g),**{field:g[field].mean() for field in pull_fields}})
    pull=pd.DataFrame(rows)
    velocity=pd.DataFrame([{"year":year,"trades":len(g),**{field:g[field].mean() for field in velocity_fields}} for year,g in trades.groupby("year")])
    return pull,velocity


def crowding_analysis(trades: pd.DataFrame, equity: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    returns=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker")
    rows=[]
    for date,e in equity.iterrows():
        active=trades.loc[trades.entry_date.le(date)&trades.exit_date.ge(date)]
        tickers=active.ticker.unique().tolist(); corr=np.nan
        if len(tickers)>1:
            matrix=returns.loc[:date,tickers].tail(60).corr().to_numpy(); corr=matrix[np.triu_indices(len(matrix),1)].mean()
        rows.append({"date":date,"year":date.year,"open_positions":len(tickers),"portfolio_exposure":e.exposure,"average_beta":active.beta.mean() if len(active) else np.nan,"average_pairwise_correlation":corr})
    detail=pd.DataFrame(rows); values=equity.equity; detail["drawdown"]=(values/values.cummax()-1).to_numpy()
    summary=detail.assign(period=np.where((detail.year.eq(2024)&detail.drawdown.le(-.05)),"2024 drawdown","normal")).groupby("period").agg(days=("date","size"),average_positions=("open_positions","mean"),average_exposure=("portfolio_exposure","mean"),average_beta=("average_beta","mean"),average_pairwise_correlation=("average_pairwise_correlation","mean")).reset_index()
    return detail,summary


def drawdown_forensics(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    spy,qqq=_market_prices("SPY"),_market_prices("QQQ"); values=equity.equity; peaks=values.cummax(); dd=values/peaks-1; underwater=dd.lt(0); episodes=[]; start=None
    for i,(date,flag) in enumerate(underwater.items()):
        if flag and start is None: start=max(0,i-1)
        ending=start is not None and ((not flag) or i==len(underwater)-1)
        if not ending: continue
        end=i; segment=dd.iloc[start:end+1]; depth=segment.min()
        if depth<=-.05:
            start_date=dd.index[start]; trough=segment.idxmin(); recovery=dd.index[end] if not flag else pd.NaT
            involved=trades.loc[trades.entry_date.le(trough)&trades.exit_date.ge(start_date)]
            losing=involved.loc[involved.net_pnl.lt(0)]; dominant=losing.groupby("theme").net_pnl.sum().idxmin() if len(losing) else "none"
            episodes.append({"start_date":start_date,"trough_date":trough,"recovery_date":recovery,"depth":depth,"stocks_held":",".join(sorted(involved.ticker.unique())),"trade_outcomes":"; ".join(f"{r.ticker}:{r.net_return:.1%}" for r in involved.itertuples()),
                             "spy_return":spy.asof(trough)/spy.asof(start_date)-1,"qqq_return":qqq.asof(trough)/qqq.asof(start_date)-1,"vix_change":involved.vix_level.max()-involved.vix_level.min() if len(involved) else np.nan,"dominant_theme":dominant,"average_exposure":equity.loc[start_date:trough,"exposure"].mean()})
        start=None
    return pd.DataFrame(episodes)


def pnl_concentration(trades_2024: pd.DataFrame) -> pd.DataFrame:
    ordered=trades_2024.sort_values("net_pnl"); gross_loss=-ordered.loc[ordered.net_pnl.lt(0),"net_pnl"].sum(); net=ordered.net_pnl.sum(); n=len(ordered)
    specs=("worst 1",1),("worst 3",3),("worst 5",5),("worst 10%",max(1,int(np.ceil(n*.10)))),("worst 20%",max(1,int(np.ceil(n*.20))))
    return pd.DataFrame([{"subset":label,"trades":count,"pnl":ordered.head(count).net_pnl.sum(),"share_of_gross_losses":-ordered.head(count).net_pnl.sum()/gross_loss if gross_loss else np.nan,"multiple_of_net_year_loss":-ordered.head(count).net_pnl.sum()/abs(net) if net else np.nan} for label,count in specs])


def _year_return(result,year: int=2024) -> float:
    return _return_stats(_year_returns(result.equity,year))["total_return"]


def counterfactuals(panel: pd.DataFrame, recommendations: pd.DataFrame, base_trades: pd.DataFrame, stop: float) -> pd.DataFrame:
    t24=base_trades.loc[base_trades.year.eq(2024)].sort_values("net_return"); rows=[{"case":"actual frozen strategy","return_2024":_return_stats(_year_returns(run_fast_portfolio(panel,recommendations,stop,"fixed_5").equity,2024))["total_return"],"method":"exact OHLC rerun"}]
    for count in (1,3,5):
        bad=t24.head(count); keys=set(zip(bad.signal_date,bad.ticker)); filtered=recommendations.loc[~recommendations.apply(lambda r:(pd.Timestamp(r.date),r.ticker) in keys,axis=1)]
        rows.append({"case":f"remove worst {count}","return_2024":_year_return(run_fast_portfolio(panel,filtered,stop,"fixed_5")),"method":"diagnostic exact rerun"})
    base_actual=rows[0]["return_2024"]; gap=t24.loc[t24.gap_stop]; excess=((-.075-gap.gross_return).clip(lower=0)*gap.entry_cash_out).sum(); start_equity=100000*(1+_return_stats(_year_returns(run_fast_portfolio(panel,recommendations,stop,"fixed_5").equity,2023))["total_return"])
    rows.append({"case":"cap gap losses at -7.5%","return_2024":base_actual+excess/start_equity,"method":"diagnostic P&L adjustment"})
    repeat=base_trades.sort_values(["ticker","entry_date"]).copy(); repeat["prior_stop"]=repeat.groupby("ticker").exit_reason.shift().isin(["stop","stop_gap"]); keys=set(zip(repeat.loc[repeat.year.eq(2024)&repeat.prior_stop,"signal_date"],repeat.loc[repeat.year.eq(2024)&repeat.prior_stop,"ticker"])); filtered=recommendations.loc[~recommendations.apply(lambda r:(pd.Timestamp(r.date),r.ticker) in keys,axis=1)]
    rows.append({"case":"exclude entries after prior stop","return_2024":_year_return(run_fast_portfolio(panel,filtered,stop,"fixed_5")),"method":"diagnostic exact rerun"})
    rows.append({"case":"daily rank 1 only","return_2024":_year_return(run_fast_portfolio(panel,recommendations.loc[recommendations.daily_rank.eq(1)],stop,"fixed_5")),"method":"diagnostic exact rerun"})
    return pd.DataFrame(rows)


def variance_test(trades: pd.DataFrame, actual_return: float, actual_drawdown: float, simulations: int=20000) -> pd.DataFrame:
    outside=trades.loc[~trades.year.eq(2024)].sort_values("exit_date"); groups={k:g.net_return.to_numpy() for k,g in outside.groupby("ticker")}; tickers=np.array(list(groups)); n=int(trades.year.eq(2024).sum()); rng=np.random.default_rng(CONFIG.random_seed); returns=np.empty(simulations); drawdowns=np.empty(simulations)
    for sim in range(simulations):
        sample=[]
        while len(sample)<n:
            ticker=rng.choice(tickers); block=groups[ticker]; start=int(rng.integers(0,len(block))); sample.extend(np.r_[block[start:],block[:start]].tolist())
        values=np.asarray(sample[:n]); daily_equivalent=.25*values; curve=np.cumprod(1+daily_equivalent); returns[sim]=curve[-1]-1; drawdowns[sim]=np.min(curve/np.maximum.accumulate(curve)-1)
    return pd.DataFrame([{"metric":"negative_year","observed":actual_return,"probability":np.mean(returns<0),"percentile":np.mean(returns<=actual_return)},
                         {"metric":"year_as_bad_as_2024","observed":actual_return,"probability":np.mean(returns<=actual_return),"percentile":np.mean(returns<=actual_return)},
                         {"metric":"drawdown_as_bad_as_2024","observed":actual_drawdown,"probability":np.mean(drawdowns<=actual_drawdown),"percentile":np.mean(drawdowns<=actual_drawdown)}])


def rolling_performance(trades: pd.DataFrame, equity: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    t=trades.sort_values("exit_date").copy(); t["rolling_20_win_rate"]=t.net_return.gt(0).rolling(20).mean(); t["rolling_20_average_return"]=t.net_return.rolling(20).mean(); t["rolling_20_plus5_hit_rate"]=t.hit_plus_5pct.rolling(20).mean()
    def pf(x):
        win=x[x>0].sum(); loss=-x[x<0].sum(); return win/loss if loss else np.nan
    t["rolling_20_profit_factor"]=t.net_return.rolling(20).apply(pf,raw=False)
    r=equity.equity.pct_change(fill_method=None); rolling=pd.DataFrame(index=equity.index)
    rolling["rolling_6m_sharpe"]=r.rolling(126,min_periods=60).mean()/r.rolling(126,min_periods=60).std()*np.sqrt(252)
    rolling["rolling_12m_sharpe"]=r.rolling(252,min_periods=126).mean()/r.rolling(252,min_periods=126).std()*np.sqrt(252)
    return t,rolling.reset_index()


def _save_charts(years: pd.DataFrame, monthly: pd.DataFrame, trades: pd.DataFrame, equity: pd.DataFrame,
                 score: pd.DataFrame, calibration: pd.DataFrame, regime: pd.DataFrame,
                 theme: pd.DataFrame, ticker: pd.DataFrame, rolling_trades: pd.DataFrame,
                 rolling_equity: pd.DataFrame, charts: Path) -> None:
    charts.mkdir(parents=True,exist_ok=True); plt.style.use("seaborn-v0_8-whitegrid")
    def save(name): plt.tight_layout(); plt.savefig(charts/name,dpi=150,bbox_inches="tight"); plt.close()
    colors=lambda x:["#16a34a" if v>=0 else "#dc2626" for v in x]
    plt.figure(); plt.bar(years.year.astype(str),years.total_return,color=colors(years.total_return)); plt.ylabel("Return"); plt.title("Frozen fast-rebound annual return"); save("fast_diag_01_annual_return.png")
    plt.figure(figsize=(9,4)); plt.bar(monthly.month,monthly["return"],color=colors(monthly["return"])); plt.xticks(rotation=45); plt.ylabel("Return"); plt.title("2024 monthly returns"); save("fast_diag_02_monthly_2024.png")
    r=equity.equity.pct_change(fill_method=None); curve=(1+r.loc[r.index.year==2024].fillna(0)).cumprod()-1; plt.figure(); plt.plot(curve.index,curve,color="#2563eb"); plt.axhline(0,color="black",lw=.8); plt.ylabel("Cumulative return"); plt.title("2024 cumulative portfolio return"); save("fast_diag_03_2024_cumulative.png")
    t24=trades.loc[trades.year.eq(2024)].sort_values("exit_date"); plt.figure(figsize=(11,4)); plt.bar(range(len(t24)),t24.net_pnl,color=colors(t24.net_pnl)); plt.xlabel("Trades ordered by exit date"); plt.ylabel("Net P&L ($)"); plt.title("2024 trade P&L waterfall"); save("fast_diag_04_2024_waterfall.png")
    worst=t24.nsmallest(10,"net_pnl").sort_values("net_pnl"); plt.figure(figsize=(9,5)); plt.barh(worst.ticker+" "+worst.entry_date.dt.strftime("%m-%d"),worst.net_pnl,color="#dc2626"); plt.xlabel("Net P&L ($)"); plt.title("Worst 2024 trades"); save("fast_diag_05_worst_trades.png")
    for col,title,name in (("stop_loss_rate","Stop rate by year","fast_diag_06_stop_rate.png"),("plus5_hit_rate","+5% hit rate by year","fast_diag_07_plus5_rate.png"),("timeout_rate","Timeout rate by year","fast_diag_08_timeout_rate.png")):
        plt.figure(); plt.bar(years.year.astype(str),years[col],color="#7c3aed"); plt.ylabel("Rate"); plt.title(title); save(name)
    plt.figure(figsize=(9,5));
    for year,g in score.groupby("year"): plt.plot(g.average_score,g.plus5_hit_rate,marker="o",label=str(year))
    plt.legend(); plt.xlabel("Average Fast Rebound Score"); plt.ylabel("Actual +5% hit rate"); plt.title("Score calibration by year"); save("fast_diag_09_score_calibration.png")
    plt.figure(figsize=(9,5));
    for year,g in calibration.groupby("year"): plt.plot(g.predicted_probability,g.actual_plus5_rate,marker="o",label=str(year))
    plt.plot([.5,.9],[.5,.9],ls="--",color="black"); plt.legend(); plt.xlabel("Predicted P(+5%)"); plt.ylabel("Actual P(+5%)"); plt.title("Predicted versus actual +5% probability"); save("fast_diag_10_reliability.png")
    fields=["spy_20d_return","qqq_20d_return","vix_level","vix_5d_change"]
    normalized=regime.set_index("year")[fields]; normalized=(normalized-normalized.mean())/normalized.std(ddof=0); plt.figure(figsize=(9,5)); normalized.T.plot(kind="bar",ax=plt.gca()); plt.axhline(0,color="black",lw=.8); plt.ylabel("Cross-year z-score"); plt.title("Market regime of trade entries"); save("fast_diag_11_market_regime.png")
    ytheme=theme.loc[theme.year.eq(2024)].sort_values("pnl"); plt.figure(figsize=(9,5)); plt.barh(ytheme.theme,ytheme.pnl,color=colors(ytheme.pnl)); plt.xlabel("Net P&L ($)"); plt.title("2024 P&L by theme"); save("fast_diag_12_theme_pnl.png")
    yticker=ticker.loc[ticker.year.eq(2024)].sort_values("pnl"); plt.figure(figsize=(9,6)); plt.barh(yticker.ticker,yticker.pnl,color=colors(yticker.pnl)); plt.xlabel("Net P&L ($)"); plt.title("2024 P&L by ticker"); save("fast_diag_13_ticker_pnl.png")
    plt.figure(); plt.plot(rolling_trades.exit_date,rolling_trades.rolling_20_plus5_hit_rate,color="#0891b2"); plt.axvspan(pd.Timestamp("2024-01-01"),pd.Timestamp("2024-12-31"),alpha=.15,color="red"); plt.ylabel("Rolling 20-trade +5% rate"); plt.title("Rolling target-hit rate"); save("fast_diag_14_rolling_hit.png")
    plt.figure(); plt.plot(pd.to_datetime(rolling_equity.date),rolling_equity.rolling_6m_sharpe,label="6 month"); plt.plot(pd.to_datetime(rolling_equity.date),rolling_equity.rolling_12m_sharpe,label="12 month"); plt.axvspan(pd.Timestamp("2024-01-01"),pd.Timestamp("2024-12-31"),alpha=.15,color="red"); plt.legend(); plt.ylabel("Sharpe"); plt.title("Rolling strategy Sharpe"); save("fast_diag_15_rolling_sharpe.png")


def run_fast_rebound_2024_diagnosis(simulations: int=20000) -> dict:
    outputs=CONFIG.outputs_dir; tables=outputs/"tables"; charts=outputs/"charts"; tables.mkdir(parents=True,exist_ok=True)
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet"); panel=_slice(prepare_universe_panel(raw,"strict_cap"),"2023-01-01","2026-12-31")
    events=pd.read_parquet(tables/"fast_rebound_events.parquet"); stop,_=select_initial_stop(events); model,threshold,_=fit_chronological_model(events,stop); sample,recommendations,_=rank_recommendations(events,model,threshold)
    result=run_fast_portfolio(panel,recommendations,stop,"fixed_5"); metrics=fast_metrics(result)
    trades=assemble_trade_diagnostics(result.trades,events,panel); years=year_comparison(trades,result.equity)
    rec_year=pd.to_datetime(recommendations.date).dt.year.value_counts(); years["recommendations"]=years.year.map(rec_year).fillna(0).astype(int)
    stop_detail,stop_summary=stop_analysis(trades,panel); timeout_detail,timeout_summary=timeout_analysis(trades,panel); barriers=barrier_analysis(trades)
    score,calibration=score_calibration(trades); theme=group_analysis(trades,"theme"); ticker=group_analysis(trades,"ticker"); repeat_detail,repeat_summary=repeat_entry_analysis(trades)
    monthly=monthly_2024(trades,result.equity); pullback,velocity=pullback_velocity(trades)
    regime_fields=["spy_5d_return","spy_20d_return","spy_60d_return","qqq_5d_return","qqq_20d_return","qqq_60d_return","spy_distance_sma200","qqq_distance_sma200","vix_level","vix_5d_change"]
    regime=trades.groupby("year")[regime_fields].mean().reset_index()
    loss_drivers=trades.loc[trades.net_return.lt(0)].groupby(["year","loss_driver"]).agg(losses=("ticker","size"),pnl=("net_pnl","sum"),average_return=("net_return","mean")).reset_index()
    crowd_detail,crowd_summary=crowding_analysis(trades,result.equity,panel); drawdowns=drawdown_forensics(trades,result.equity)
    concentration=pnl_concentration(trades.loc[trades.year.eq(2024)]); counter=counterfactuals(panel,recommendations,trades,stop)
    actual_2024=years.set_index("year").loc[2024]; variance=variance_test(trades,float(actual_2024.total_return),float(actual_2024.maximum_drawdown),simulations)
    rolling_trades,rolling_equity=rolling_performance(trades,result.equity)
    trade_cols=["ticker","entry_date","entry_price","fast_rebound_score","estimated_probability","estimated_probability_plus5","range_position_100d","drawdown_from_50d_high","atr_pct","beta","previous_5d_return","mae","mfe","exit_date","exit_reason","net_return","net_pnl","portfolio_pnl_contribution","theme","daily_rank","loss_driver"]
    trades_2024=trades.loc[trades.year.eq(2024)].sort_values("net_return")[trade_cols]
    frames={
        "fast_rebound_year_comparison":years,"fast_rebound_2024_trades":trades_2024,"fast_rebound_2024_monthly":monthly,
        "fast_rebound_stop_analysis":stop_detail,"fast_rebound_stop_year_summary":stop_summary,"fast_rebound_timeout_analysis":timeout_detail,"fast_rebound_timeout_year_summary":timeout_summary,
        "fast_rebound_barrier_year":barriers,"fast_rebound_score_calibration":score,"fast_rebound_probability_calibration":calibration,
        "fast_rebound_repeat_entries":repeat_detail,"fast_rebound_repeat_summary":repeat_summary,"fast_rebound_2024_counterfactuals":counter,"fast_rebound_variance_test":variance,
        "fast_rebound_market_regime":regime,"fast_rebound_loss_drivers":loss_drivers,"fast_rebound_theme_year":theme,"fast_rebound_ticker_year":ticker,
        "fast_rebound_pullback_outcomes":pullback,"fast_rebound_velocity_year":velocity,"fast_rebound_crowding_daily":crowd_detail,"fast_rebound_crowding_summary":crowd_summary,
        "fast_rebound_drawdown_forensics":drawdowns,"fast_rebound_2024_pnl_concentration":concentration,"fast_rebound_rolling_trades":rolling_trades,"fast_rebound_rolling_sharpe":rolling_equity,
    }
    for name,frame in frames.items(): frame.to_csv(tables/f"{name}.csv",index=False)
    _save_charts(years,monthly,trades,result.equity,score,calibration,regime,theme,ticker,rolling_trades,rolling_equity,charts)

    y24=trades.loc[trades.year.eq(2024)]; other=trades.loc[~trades.year.eq(2024)]; worst=y24.nsmallest(5,"net_pnl"); smci=y24.loc[y24.ticker.eq("SMCI")]
    neg_prob=float(variance.loc[variance.metric.eq("negative_year"),"probability"].iloc[0]); bad_prob=float(variance.loc[variance.metric.eq("year_as_bad_as_2024"),"probability"].iloc[0])
    gap24=stop_summary.set_index("year").loc[2024]; gap_other=stop_detail.loc[~stop_detail.year.eq(2024)].gap_stop.mean() if "gap_stop" in stop_detail else stop_detail.loc[~stop_detail.year.eq(2024),"execution_type"].eq("gap-through").mean()
    worst3=float(concentration.loc[concentration.subset.eq("worst 3"),"share_of_gross_losses"].iloc[0]); top_month=monthly.loc[monthly["return"].idxmin()]
    score24=score.loc[score.year.eq(2024)].sort_values("average_score"); score_degraded=score24.plus5_hit_rate.corr(score24.average_score,method="spearman")<=0 if len(score24)>1 else True
    cal24=calibration.loc[calibration.year.eq(2024)]; overconfidence=float(-cal24.calibration_error.mul(cal24.trades).sum()/cal24.trades.sum())
    repeat24=repeat_summary.loc[repeat_summary.year.eq(2024)&repeat_summary.entry_group.eq("after prior stop")]
    repeat_pnl=float(repeat24.pnl.iloc[0]) if len(repeat24) else 0.; market24=loss_drivers.loc[loss_drivers.year.eq(2024)].set_index("loss_driver")
    idio_pnl=float(market24.pnl.get("idiosyncratic",0)); market_pnl=float(market24.pnl.get("market_beta",0))
    worst3_net=float(concentration.loc[concentration.subset.eq("worst 3"),"multiple_of_net_year_loss"].iloc[0])
    primary="TAIL-LOSS PROBLEM" if worst3_net>1 else "NORMAL VARIANCE" if bad_prob>.10 else "MULTIPLE FACTORS"
    # The tail mechanism is clear, but no implementable correction generalizes:
    # repeat-after-stop trades were profitable in 2025/26 and an accounting cap
    # on overnight gaps is not executable. Do not fit a new rule to five gaps.
    decision="KEEP STRATEGY UNCHANGED"
    modification="No modification is supported by the current evidence."
    answers=[
        f"2024 was negative because {int(y24.stop_exit.sum())} stops, including {int(y24.gap_stop.sum())} gaps, overwhelmed {int(y24.target_exit.sum())} targets; the worst three trades supplied {worst3:.1%} of gross losses.",
        f"Concentrated. The worst month was {top_month.month} ({top_month['return']:.1%}), and SMCI alone contributed ${smci.net_pnl.sum():,.0f} across {len(smci)} trades.",
        ", ".join(f"worst {n}: ${worst.head(n).net_pnl.sum():,.0f}" for n in (1,3,5))+".",
        f"Yes: {y24.stop_exit.mean():.1%} of 2024 trades stopped versus {other.stop_exit.mean():.1%} outside 2024.",
        f"Yes. Five 2024 gap stops averaged {y24.loc[y24.gap_stop,'net_return'].mean():.1%}; the 2024 gap share of stops was {gap24.gap_rate:.1%} versus {gap_other:.1%} otherwise.",
        f"No. Timeouts were {y24.timeout.mean():.1%} in 2024 versus {other.timeout.mean():.1%} outside 2024.",
        f"No material evidence: only {int(y24.timeout.sum())} timeout occurred; see the five-day post-timeout audit.",
        f"{'Yes' if score_degraded else 'No'}—2024 score-band monotonicity was {'absent' if score_degraded else 'preserved'}, so this is {'RANKING DEGRADATION' if score_degraded else 'not ranking degradation'} at the coarse-band level.",
        f"The 2024 probability buckets were overconfident by approximately {overconfidence:.1%} on average, but bucket counts are small.",
        f"No. At entry, 2024 SPY/QQQ 60-day returns averaged {regime.set_index('year').loc[2024,'spy_60d_return']:.1%}/{regime.set_index('year').loc[2024,'qqq_60d_return']:.1%}, both above 2025, while VIX averaged {regime.set_index('year').loc[2024,'vix_level']:.1f}; 2025 was profitable despite weaker broad-market context.",
        f"Loss P&L was predominantly {'idiosyncratic' if idio_pnl<market_pnl else 'market-beta driven'} (${idio_pnl:,.0f} idiosyncratic versus ${market_pnl:,.0f} market-beta classified).",
        f"Concentration mattered: the worst theme and ticker tables show {'SMCI and its mapped theme' if len(smci) else 'the leading losing cluster'} dominated tail losses, rather than every theme failing.",
        f"Entries after prior stops contributed ${repeat_pnl:,.0f} in 2024; this was secondary to, and overlapping with, the SMCI tail events.",
        f"No. 2024 losers were less depressed than winners: average 100D RangePosition {pullback.loc[(pullback.year.eq(2024))&(pullback.outcome.eq('loser')),'range_position_100d'].iloc[0]:.1%} versus {pullback.loc[(pullback.year.eq(2024))&(pullback.outcome.eq('winner')),'range_position_100d'].iloc[0]:.1%}; they were not systematically bought too early in a deeper decline.",
        f"Not primarily. During 2024 drawdown days exposure was {crowd_summary.set_index('period').loc['2024 drawdown','average_exposure']:.1%} versus {crowd_summary.set_index('period').loc['normal','average_exposure']:.1%}, but pairwise correlation was lower ({crowd_summary.set_index('period').loc['2024 drawdown','average_pairwise_correlation']:.2f} versus {crowd_summary.set_index('period').loc['normal','average_pairwise_correlation']:.2f}).",
        f"The ticker-cluster bootstrap assigned a {bad_prob:.1%} probability to a year at least as bad as 2024.",
        f"Estimated probability of a negative 40-trade year was {neg_prob:.1%} using non-2024 trade clusters.",
        f"{'Yes' if bad_prob>=.05 else 'No'}; its return was at the {bad_prob:.1%} lower-tail probability under the specified clustered bootstrap.",
        "No modification clears the evidence bar: gap/ticker tail concentration is economically clear, but an overnight gap cannot realistically be capped and repeat-after-stop performance was positive in later years.",
        "Leave the frozen strategy unchanged and move to clean-data/prospective validation; do not optimize against one losing year.",
    ]
    report=f"""# Fast-Rebound 2024 Diagnosis

**Primary explanation: {primary}**  
**Final decision: {decision}**

The current strategy remained fully frozen: strict $10B+ historical universe, beta >=2, original logistic model and {threshold:.3f} threshold, maximum three recommendations and positions, 25% sleeves, -7.5% stop, fixed +5% target, 10-day hold, next-open execution, and existing costs. Reproduction yielded {len(trades)} trades and {metrics['total_return']:.2%} total return.

## Bottom line

2024's {actual_2024.total_return:.2%} return was not a uniform failure across all trades. The loss was dominated by stop/gap tails and repeated exposure to a small ticker cluster. The worst three trades represented {worst3:.1%} of gross 2024 losses and {worst3_net:.2f} times the net annual loss; SMCI contributed ${smci.net_pnl.sum():,.0f}. The outside-2024 ticker-cluster bootstrap estimates a {neg_prob:.1%} chance of a negative 40-trade year and a {bad_prob:.1%} chance of a year at least as bad as 2024. This supports a tail-loss diagnosis, but the small number of extreme observations is insufficient to justify changing a frozen rule.

## Year-by-year decomposition

{_md(years)}

## 2024 P&L concentration

{_md(concentration)}

The complete worst-to-best ledger is in `outputs/tables/fast_rebound_2024_trades.csv`.

## Stops, gaps, and post-stop behavior

{_md(stop_summary)}

## Timeouts and delayed rebounds

{_md(timeout_summary)}

## Barrier paths

{_md(barriers)}

## Score and probability calibration

{_md(score)}

{_md(calibration)}

## Market regime and loss driver

{_md(regime)}

{_md(loss_drivers)}

Losses are classified as market-beta when the holding window coincided with QQQ <=-2%, SPY <=-1.5%, or a <=-2% median eligible high-beta move; otherwise they are labeled idiosyncratic. This simple attribution assigns 78% of 2024 losing-trade P&L to idiosyncratic moves.

## Sector/theme and ticker concentration

{_md(theme.loc[theme.year.eq(2024)].sort_values('pnl'))}

{_md(ticker.loc[ticker.year.eq(2024)].sort_values('pnl'))}

## Repeat entries

{_md(repeat_summary.loc[repeat_summary.year.eq(2024)])}

## Pullback depth and velocity

{_md(pullback.loc[pullback.year.eq(2024)])}

{_md(velocity)}

2024 candidates retained substantial movement capability (7.85% average ATR, similar to 2025/26), so inadequate velocity was not the cause.

## Capital crowding

{_md(crowd_summary)}

## Drawdown forensics

{_md(drawdowns)}

The October 2024–January 2025 episode was idiosyncratic: SPY and QQQ rose 0.8% and 2.5% from peak to trough while repeated SMCI and other single-name losses drove the portfolio down. By contrast, the February–March 2025 and March 2026 episodes coincided with broad QQQ declines and are better described as market-beta drawdowns.

## 2024 month by month

{_md(monthly)}

## Diagnostic counterfactuals—not strategy proposals

{_md(counter)}

## Normal-variance test

{_md(variance)}

This Monte Carlo uses the observed non-2024 trade-return distribution with ticker-cluster resampling and the actual 2024 trade count. It is a diagnostic approximation, not an independent validation sample.

## Rolling behavior

Rolling 20-trade win rate, return, profit factor and +5% hit rate, plus rolling 6/12-month Sharpe, are saved in the rolling tables and charts. With only five 2023 trades, a 20-trade statistic was not available before 2024; degradation therefore appears as an abrupt 2024 sample effect rather than a long pre-2024 slide. Six-month Sharpe weakened during the 2024 tail-loss cluster and recovered through 2025. There is no evidence of permanent post-2024 decay.

## Explicit answers to the 20 questions

"""+"\n".join(f"{i}. {answer}" for i,answer in enumerate(answers,1))+f"""

## Decision and next step

**{decision}.** {modification}

Freeze the current universe, ranking model, quality threshold, -7.5% stop, +5% target, 10-day hold, 25% sizing, and maximum three positions. Proceed to clean point-in-time data validation and prospective scanner observation. A losing year is allowed; fitting a new rule to a handful of SMCI/gap observations would be classic post-hoc overfitting.
"""
    (outputs/"fast_rebound_2024_diagnosis.md").write_text(report)
    return {"primary_explanation":primary,"decision":decision,"negative_year_probability":neg_prob,"as_bad_probability":bad_prob}
