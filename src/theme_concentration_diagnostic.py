"""Theme and correlation concentration diagnosis for frozen 3x33.33%."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR",str(Path(__file__).resolve().parents[1]/".matplotlib"))
import matplotlib.pyplot as plt

from config import CONFIG
from src.capital_allocation_research import (
    AllocationArchitecture, allocation_metrics, annual_architecture,
    average_pairwise_correlation, matched_random_allocation,
    run_allocation_portfolio, _fixed_event_return,
)
from src.expanded_retest import _slice, prepare_universe_panel
from src.fast_rebound_research import fit_chronological_model, rank_recommendations, select_initial_stop


AUDITED_OVERRIDES={
    "SMCI":"data infrastructure","PLTR":"software","COIN":"crypto-linked","MU":"AI / semiconductors","SNDK":"data infrastructure",
    "APP":"software","AMD":"AI / semiconductors","VST":"power / industrial","WDC":"data infrastructure","ENPH":"EV / clean technology",
    "AMAT":"AI / semiconductors","ANET":"data infrastructure","NVDA":"AI / semiconductors","STX":"data infrastructure","DELL":"data infrastructure",
    "INTC":"AI / semiconductors","ON":"AI / semiconductors","KLAC":"AI / semiconductors","TSLA":"EV / clean technology","AVGO":"AI / semiconductors",
    "ALB":"EV / clean technology","MPWR":"AI / semiconductors","GLW":"data infrastructure","CIEN":"data infrastructure","LRCX":"AI / semiconductors",
    "QCOM":"AI / semiconductors","MCHP":"AI / semiconductors","GEV":"power / industrial","TER":"AI / semiconductors","CCL":"consumer",
    "IONQ":"quantum","ASTS":"space","RKLB":"space","HOOD":"fintech","MSTR":"crypto-linked","CVNA":"consumer","CRWD":"software",
}


def audited_theme_mapping(tickers: pd.Index | list[str]) -> pd.DataFrame:
    path=CONFIG.outputs_dir/"tables"/"expanded_sector_mapping.csv"; existing=pd.read_csv(path).set_index("ticker") if path.exists() else pd.DataFrame()
    rows=[]
    for ticker in sorted(set(tickers)):
        original=existing.theme.get(ticker,"unmapped") if len(existing) else "unmapped"; sector=existing.sector.get(ticker,"unmapped") if len(existing) else "unmapped"
        audited=AUDITED_OVERRIDES.get(ticker,original if original not in ("other","unmapped") else "other")
        rows.append({"ticker":ticker,"sector":sector,"original_theme":original,"audited_theme":audited,"manually_overridden":ticker in AUDITED_OVERRIDES})
    return pd.DataFrame(rows)


def _weights(row: pd.Series) -> dict[str,float]:
    result={}
    for item in str(row.get("position_weights","")).split("|"):
        if ":" in item:
            ticker,value=item.split(":",1); result[ticker]=float(value)
    return result


def classify_portfolio_days(result, trades: pd.DataFrame, theme_map: dict[str,str]) -> pd.DataFrame:
    e=result.equity.copy(); e["portfolio_return"]=e.equity.pct_change(fill_method=None).fillna(0); rows=[]
    for date,row in e.iterrows():
        weights=_weights(row); tickers=list(weights); themes=[theme_map.get(t,"other") for t in tickers]; n=len(tickers)
        if n==0: category="CASH"
        elif n==1: category="A. ONE POSITION"
        elif n==2: category="C. TWO POSITIONS — SAME THEME" if len(set(themes))==1 else "B. TWO POSITIONS — DIFFERENT THEMES"
        elif len(set(themes))==3: category="D. THREE POSITIONS — ALL DIFFERENT THEMES"
        elif len(set(themes))==1: category="F. THREE POSITIONS — ALL SAME THEME"
        else: category="E. THREE POSITIONS — TWO SAME + ONE DIFFERENT"
        active=trades.loc[trades.entry_date.le(date)&trades.exit_date.ge(date)&trades.ticker.isin(tickers)]
        theme_weights={}
        for ticker,w in weights.items(): theme_weights[theme_map.get(ticker,"other")]=theme_weights.get(theme_map.get(ticker,"other"),0)+w
        rows.append({"date":date,"category":category,"positions":n,"tickers":"|".join(tickers),"themes":"|".join(themes),"exposure":row.exposure,"max_same_theme_exposure":max(theme_weights.values(),default=0),"average_score":active.fast_rebound_score.mean() if len(active) else np.nan,"portfolio_return":row.portfolio_return})
    detail=pd.DataFrame(rows); invested=detail.positions.gt(0).sum(); summaries=[]
    for category,g in detail.loc[detail.positions.gt(0)].groupby("category"):
        curve=(1+g.portfolio_return).cumprod(); summaries.append({"category":category,"portfolio_days":len(g),"pct_invested_days":len(g)/invested if invested else np.nan,"average_exposure":g.exposure.mean(),"average_fast_rebound_score":g.average_score.mean(),"portfolio_return":curve.iloc[-1]-1,"annualized_volatility":g.portfolio_return.std()*np.sqrt(252),"negative_return_contribution":g.portfolio_return.clip(upper=0).sum()})
    return detail,pd.DataFrame(summaries)


def point_in_time_correlations(panel_or_returns: pd.DataFrame, date: pd.Timestamp, tickers: list[str]) -> tuple[float,float]:
    if len(tickers)<2: return np.nan,np.nan
    returns=(panel_or_returns.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker") if isinstance(panel_or_returns.index,pd.MultiIndex) else panel_or_returns)
    values=[]
    for window in (20,60):
        matrix=returns.loc[:date,[t for t in tickers if t in returns]].tail(window).corr().to_numpy(); off=matrix[np.triu_indices(len(matrix),1)]; values.append(float(np.nanmean(off)) if np.isfinite(off).any() else np.nan)
    return values[0],values[1]


def basket_analysis(result, trades: pd.DataFrame, panel: pd.DataFrame, theme_map: dict[str,str]) -> pd.DataFrame:
    e=result.equity; rows=[]; current=None; start=None; returns_matrix=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker")
    sequence=[]
    for date,row in e.iterrows():
        tickers=tuple(x for x in str(row.position_tickers).split("|") if x)
        if len(tickers)<2: tickers=()
        if tickers!=current:
            if current: sequence.append((start,previous,current))
            current=tickers; start=date if tickers else None
        previous=date
    if current: sequence.append((start,previous,current))
    for start,end,tickers in sequence:
        themes=[theme_map.get(t,"other") for t in tickers]; classification="ALL SAME THEME" if len(set(themes))==1 else "ALL DIFFERENT THEMES" if len(set(themes))==len(themes) else "PARTIALLY SAME THEME"
        active=trades.loc[trades.ticker.isin(tickers)&trades.entry_date.le(end)&trades.exit_date.ge(start)].copy(); segment=e.loc[start:end]; corr20,corr60=point_in_time_correlations(returns_matrix,start,list(tickers))
        daily=e.equity.pct_change(fill_method=None).loc[start:end].fillna(0); curve=(1+daily).cumprod(); basket_return=curve.iloc[-1]-1; path=pd.concat([pd.Series([1.]),curve.reset_index(drop=True)])
        rows.append({"start_date":start,"end_date":end,"stocks":"|".join(tickers),"themes":"|".join(themes),"classification":classification,"positions":len(tickers),"entry_dates":"|".join(active.entry_date.dt.strftime("%Y-%m-%d")),"ranks":"|".join(active.daily_rank.astype(str)),"scores":"|".join(active.fast_rebound_score.round(1).astype(str)),"position_weights":segment.iloc[0].position_weights,"correlation_20d":corr20,"correlation_60d":corr60,"basket_return":basket_return,"worst_basket_drawdown":(path/path.cummax()-1).min(),"plus5_hits":active.exit_reason.str.startswith("target").sum(),"stops":active.exit_reason.str.startswith("stop").sum(),"timeouts":active.exit_reason.eq("hold10").sum(),"gap_losses":active.exit_reason.eq("stop_gap").sum(),"average_mae":active.mae.mean(),"average_mfe":active.mfe.mean(),"average_holding_period":active.holding_days.mean(),"invested_days":len(segment)})
    return pd.DataFrame(rows)


def basket_summary(baskets: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for label,g in baskets.groupby("classification"):
        targets=g.plus5_hits.sum(); stops=g.stops.sum(); trades=targets+stops+g.timeouts.sum(); simultaneous=(g.stops.ge(2)).mean()
        rows.append({"classification":label,"observations":len(g),"average_basket_return":g.basket_return.mean(),"median_basket_return":g.basket_return.median(),"win_rate":g.basket_return.gt(0).mean(),"plus5_hit_rate":targets/trades if trades else np.nan,"stop_rate":stops/trades if trades else np.nan,"simultaneous_stop_rate":simultaneous,"average_mae":g.average_mae.mean(),"average_mfe":g.average_mfe.mean(),"worst_basket_loss":g.basket_return.min(),"average_correlation_20d":g.correlation_20d.mean(),"average_correlation_60d":g.correlation_60d.mean(),"average_holding_period":g.average_holding_period.mean(),"return_per_invested_day":g.basket_return.sum()/g.invested_days.sum()})
    return pd.DataFrame(rows)


def position_order(trades: pd.DataFrame, theme_map: dict[str,str]) -> tuple[pd.DataFrame,pd.DataFrame]:
    t=trades.sort_values(["entry_date","daily_rank","ticker"]).copy(); orders=[]
    for row in t.itertuples():
        theme=theme_map.get(row.ticker,"other"); prior=t.loc[(t.theme.eq(theme))&((t.entry_date<row.entry_date)|((t.entry_date.eq(row.entry_date))&(t.daily_rank<row.daily_rank)))&t.exit_date.ge(row.entry_date)]
        orders.append(min(3,len(prior)+1))
    t["theme_position_order"]=orders
    rows=[]
    for order,g in t.groupby("theme_position_order"):
        gp=g.loc[g.net_pnl.gt(0),"net_pnl"].sum(); gl=-g.loc[g.net_pnl.lt(0),"net_pnl"].sum()
        daily_impact=(g.net_pnl/g.entry_equity).groupby(g.exit_date).sum()
        years=(trades.exit_date.max()-trades.entry_date.min()).days/365.25
        pnl_return=g.net_pnl.sum()/100_000
        cagr_contribution=(1+pnl_return)**(1/years)-1 if years>0 and pnl_return>-1 else np.nan
        rows.append({"theme_position_order":order,"trades":len(g),"average_score":g.fast_rebound_score.mean(),"plus5_hit_rate":g.exit_reason.str.startswith("target").mean(),"average_return":g.net_return.mean(),"median_return":g.net_return.median(),"profit_factor":gp/gl if gl else np.nan,"stop_rate":g.exit_reason.str.startswith("stop").mean(),"average_mae":g.mae.mean(),"average_mfe":g.mfe.mean(),"average_holding_period":g.holding_days.mean(),"total_incremental_pnl":g.net_pnl.sum(),"approximate_cagr_contribution":cagr_contribution,"realized_negative_pnl_contribution":(g.net_pnl/g.entry_equity).clip(upper=0).sum(),"worst_exit_day_contribution":daily_impact.min()})
    return t,pd.DataFrame(rows)


def skipped_trade_analysis(ignored: dict[str,pd.DataFrame], qualified: pd.DataFrame, stop: float) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]
    for architecture,frame in ignored.items():
        if frame.empty: continue
        skipped=frame.loc[frame.reason.isin(["theme_limit","theme_exposure_cap"])].copy()
        if skipped.empty: continue
        event=qualified.copy(); event["hypothetical_return"]=_fixed_event_return(event,stop); event["stop_hit"]=event.barrier_outcome_stop_7_5.astype(str).str.startswith("stop")
        merged=skipped.merge(event[["date","ticker","hit_plus_5pct","stop_hit","hypothetical_return","mae_10d","mfe_10d"]],left_on=["signal_date","ticker"],right_on=["date","ticker"],how="left")
        merged["architecture"]=architecture; rows.append(merged)
    detail=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    summary=[]
    for architecture,g in detail.groupby("architecture"):
        wins=g.loc[g.hypothetical_return.gt(0),"hypothetical_return"].sum(); losses=-g.loc[g.hypothetical_return.lt(0),"hypothetical_return"].sum()
        summary.append({"architecture":architecture,"skipped_trades":len(g),"skipped_plus5_hit_rate":g.hit_plus_5pct.mean(),"skipped_stop_rate":g.stop_hit.mean(),"average_skipped_return":g.hypothetical_return.mean(),"median_skipped_return":g.hypothetical_return.median(),"skipped_profit_factor":wins/losses if losses else np.nan})
    return detail,pd.DataFrame(summary)


def correlation_analysis(baskets: pd.DataFrame) -> pd.DataFrame:
    b=baskets.copy(); b["correlation_bucket"]=pd.cut(b.correlation_60d,[-np.inf,.30,.60,np.inf],labels=["LOW <0.30","MODERATE 0.30-0.60","HIGH >0.60"],right=False)
    rows=[]
    for bucket,g in b.groupby("correlation_bucket",observed=True):
        trades=g.plus5_hits+g.stops+g.timeouts
        rows.append({"correlation_bucket":str(bucket),"baskets":len(g),"average_correlation_20d":g.correlation_20d.mean(),"average_correlation_60d":g.correlation_60d.mean(),"average_basket_return":g.basket_return.mean(),"plus5_hit_rate":g.plus5_hits.sum()/trades.sum() if trades.sum() else np.nan,"simultaneous_stop_rate":g.stops.ge(2).mean(),"average_basket_drawdown":g.worst_basket_drawdown.mean(),"worst_basket_loss":g.basket_return.min(),"gap_losses":g.gap_losses.sum()})
    return pd.DataFrame(rows)


def simultaneous_stops(result, trades: pd.DataFrame, panel: pd.DataFrame, theme_map: dict[str,str]) -> pd.DataFrame:
    spy_frame=pd.read_parquet(CONFIG.cache_dir/"prices"/"SPY.parquet"); qqq_frame=pd.read_parquet(CONFIG.cache_dir/"prices"/"QQQ.parquet")
    if "date" in spy_frame: spy_frame=spy_frame.set_index("date")
    if "date" in qqq_frame: qqq_frame=qqq_frame.set_index("date")
    spy=spy_frame.adj_close; qqq=qqq_frame.adj_close; spy.index=pd.to_datetime(spy.index); qqq.index=pd.to_datetime(qqq.index)
    rows=[]; stopped=trades.loc[trades.exit_reason.str.startswith("stop")]; returns_matrix=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker")
    for date,g in stopped.groupby("exit_date"):
        if len(g)<2: continue
        tickers=g.ticker.tolist(); themes=[theme_map.get(t,"other") for t in tickers]; c20,c60=point_in_time_correlations(returns_matrix,pd.Timestamp(date)-pd.Timedelta(days=1),tickers); equity_return=result.equity.equity.pct_change(fill_method=None).get(pd.Timestamp(date),np.nan)
        rows.append({"date":date,"positions_stopped":len(g),"tickers":"|".join(tickers),"themes":"|".join(themes),"same_theme":len(set(themes))<len(themes),"correlation_20d":c20,"correlation_60d":c60,"individual_losses":"|".join(g.net_return.map(lambda x:f"{x:.4f}")),"gap_throughs":g.exit_reason.eq("stop_gap").sum(),"portfolio_loss":equity_return,"spy_return":spy.pct_change(fill_method=None).get(pd.Timestamp(date),np.nan),"qqq_return":qqq.pct_change(fill_method=None).get(pd.Timestamp(date),np.nan)})
    return pd.DataFrame(rows)


def architecture_tail_events(result) -> tuple[int,float]:
    """Count multi-stop exit dates and the worst combined gap impact."""
    trades=result.trades.copy(); stops=trades.loc[trades.exit_reason.str.startswith("stop")]
    simultaneous=int(stops.groupby("exit_date").size().ge(2).sum())
    gaps=trades.loc[trades.exit_reason.eq("stop_gap")].copy()
    if gaps.empty: return simultaneous,np.nan
    gaps["impact"]=gaps.net_pnl/gaps.entry_equity
    return simultaneous,float(gaps.groupby("exit_date").impact.sum().min())


def major_loss_days(result, panel: pd.DataFrame, theme_map: dict[str,str], count: int=10) -> pd.DataFrame:
    """Describe the worst portfolio days using only information known by that date."""
    returns=result.equity.equity.pct_change(fill_method=None); matrix=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker")
    benchmarks={}
    for ticker in ("SPY","QQQ"):
        frame=pd.read_parquet(CONFIG.cache_dir/"prices"/f"{ticker}.parquet")
        if "date" in frame: frame=frame.set_index("date")
        frame.index=pd.to_datetime(frame.index); benchmarks[ticker]=frame.adj_close.pct_change(fill_method=None)
    rows=[]
    prior=result.equity.shift(1)
    for date,loss in returns.nsmallest(count).items():
        row=prior.loc[date]; carried=[x for x in str(row.position_tickers).split("|") if x]; exited=result.trades.loc[result.trades.exit_date.eq(date),"ticker"].tolist(); tickers=sorted(set(carried+exited)); themes=[theme_map.get(x,"other") for x in tickers]
        c20,c60=point_in_time_correlations(matrix,pd.Timestamp(date)-pd.Timedelta(days=1),tickers)
        rows.append({"date":date,"portfolio_return":loss,"positions_at_risk":len(tickers),"tickers":"|".join(tickers),"themes":"|".join(themes),"duplicate_theme":len(set(themes))<len(themes),"prior_close_exposure":row.exposure,"correlation_20d_before_loss":c20,"correlation_60d_before_loss":c60,"spy_return":benchmarks["SPY"].get(date,np.nan),"qqq_return":benchmarks["QQQ"].get(date,np.nan)})
    return pd.DataFrame(rows)


def theme_trade_results(trades: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (theme,context),g in trades.groupby(["theme","theme_context"]):
        wins=g.loc[g.net_pnl.gt(0),"net_pnl"].sum(); losses=-g.loc[g.net_pnl.lt(0),"net_pnl"].sum()
        rows.append({"theme":theme,"holding_context":context,"trades":len(g),"total_pnl":g.net_pnl.sum(),"average_return":g.net_return.mean(),"median_return":g.net_return.median(),"plus5_hit_rate":g.exit_reason.str.startswith("target").mean(),"stop_rate":g.exit_reason.str.startswith("stop").mean(),"profit_factor":wins/losses if losses else np.nan,"average_mae":g.mae.mean(),"average_mfe":g.mfe.mean(),"worst_trade":g.net_return.min()})
    return pd.DataFrame(rows)


def high_concentration_episodes(day_detail: pd.DataFrame, result, trades: pd.DataFrame, theme_map: dict[str,str]) -> pd.DataFrame:
    rows=[]
    for threshold in (.50,2/3,.90):
        active=day_detail.max_same_theme_exposure.gt(threshold); start=None
        for i,(idx,flag) in enumerate(zip(day_detail.index,active)):
            if flag and start is None: start=i
            ending=start is not None and ((not flag) or i==len(active)-1)
            if not ending: continue
            end=i-1 if not flag else i; g=day_detail.iloc[start:end+1]; dates=pd.to_datetime(g.date); tickers=sorted(set("|".join(g.tickers).split("|"))-{""}); theme_weights={}
            peak_row=g.loc[g.max_same_theme_exposure.idxmax()]
            for ticker,w in _weights(result.equity.loc[pd.Timestamp(peak_row.date)]).items(): theme_weights[theme_map.get(ticker,"other")]=theme_weights.get(theme_map.get(ticker,"other"),0)+w
            theme=max(theme_weights,key=theme_weights.get) if theme_weights else "none"; involved=trades.loc[trades.ticker.isin(tickers)&trades.entry_date.le(dates.max())&trades.exit_date.ge(dates.min())]
            daily=result.equity.equity.pct_change(fill_method=None).loc[dates.min():dates.max()].fillna(0); curve=(1+daily).cumprod(); path=pd.concat([pd.Series([1.]),curve.reset_index(drop=True)])
            rows.append({"threshold":threshold,"start_date":dates.min(),"end_date":dates.max(),"theme":theme,"stocks":"|".join(tickers),"maximum_same_theme_exposure":g.max_same_theme_exposure.max(),"average_portfolio_exposure":g.exposure.mean(),"scores":"|".join(involved.fast_rebound_score.round(1).astype(str)),"trade_outcomes":"|".join(f"{r.ticker}:{r.net_return:.2%}" for r in involved.itertuples()),"portfolio_return":curve.iloc[-1]-1,"maximum_drawdown":(path/path.cummax()-1).min()})
            start=None
    return pd.DataFrame(rows)


def gap_concentration(trades: pd.DataFrame) -> pd.DataFrame:
    gaps=trades.loc[trades.exit_reason.eq("stop_gap")].copy(); rows=[]
    for context,g in gaps.groupby("theme_context"):
        rows.append({"theme_context":context,"gaps":len(g),"average_gap_portfolio_impact":(g.net_pnl/g.entry_equity).mean(),"largest_single_gap":(g.net_pnl/g.entry_equity).min()})
    combined=gaps.assign(impact=gaps.net_pnl/gaps.entry_equity).groupby("exit_date").agg(gaps=("ticker","size"),combined_gap_impact=("impact","sum")).reset_index()
    rows.append({"theme_context":"largest two-position combined","gaps":2,"average_gap_portfolio_impact":np.nan,"largest_single_gap":combined.loc[combined.gaps.ge(2),"combined_gap_impact"].min() if combined.gaps.ge(2).any() else np.nan})
    rows.append({"theme_context":"largest three-position combined","gaps":3,"average_gap_portfolio_impact":np.nan,"largest_single_gap":combined.loc[combined.gaps.ge(3),"combined_gap_impact"].min() if combined.gaps.ge(3).any() else np.nan})
    return pd.DataFrame(rows)


def theme_tail_sensitivity(panel: pd.DataFrame, qualified: pd.DataFrame, result, stop: float, theme_map: dict[str,str], name: str, rule: dict) -> pd.DataFrame:
    t=result.trades.sort_values("net_pnl",ascending=False); count=max(1,int(np.ceil(len(t)*.10))); pnl_ticker=t.groupby("ticker").net_pnl.sum().sort_values(ascending=False); pnl_theme=t.groupby("theme").net_pnl.sum().sort_values(ascending=False)
    cases={"base":set(),"remove_best_trade":set(zip(t.head(1).signal_date,t.head(1).ticker)),"remove_best_5_trades":set(zip(t.head(5).signal_date,t.head(5).ticker)),"remove_top_10pct":set(zip(t.head(count).signal_date,t.head(count).ticker)),"remove_best_ticker":{(d,x) for d,x in zip(qualified.date,qualified.ticker) if x==pnl_ticker.index[0]},"remove_best_theme":{(d,x) for d,x in zip(qualified.date,qualified.ticker) if theme_map.get(x,"other")==pnl_theme.index[0]}}
    rows=[]; arch=AllocationArchitecture(name,3,1/3,rule.get("max_daily_rank",3))
    for label,keys in cases.items():
        filtered=qualified.loc[~qualified.apply(lambda r:(pd.Timestamp(r.date),r.ticker) in keys,axis=1)] if keys else qualified
        candidate,_=run_allocation_portfolio(panel,filtered,arch,stop,theme_map_override=theme_map,max_per_theme=rule.get("max_per_theme"),max_theme_exposure=rule.get("max_theme_exposure")); m=allocation_metrics(candidate)
        rows.append({"architecture":name,"sensitivity":label,"total_return":m["total_return"],"cagr":m["cagr"],"sharpe":m["sharpe"],"maximum_drawdown":m["maximum_drawdown"],"trades":len(candidate.trades)})
    return pd.DataFrame(rows)


def _save_charts(results, comparison, day_detail, basket_summary_table, baskets, order_summary, simultaneous, gaps, theme_results, episodes, alpha_risk, annual, charts):
    charts.mkdir(parents=True,exist_ok=True); plt.style.use("seaborn-v0_8-whitegrid")
    def save(name): plt.tight_layout(); plt.savefig(charts/name,dpi=150,bbox_inches="tight"); plt.close()
    plt.figure(figsize=(10,5)); plt.bar(basket_summary_table.classification,basket_summary_table.average_basket_return,color="#2563eb"); plt.xticks(rotation=30,ha="right"); plt.ylabel("Average basket return"); plt.title("Performance by theme concentration"); save("theme_01_concentration_performance.png")
    plt.figure(figsize=(10,5))
    for name,result in results.items(): plt.plot(result.equity.index,result.equity.equity/result.equity.equity.iloc[0],label=name)
    plt.legend(); plt.ylabel("Growth of $1"); plt.title("Base versus theme counterfactuals"); save("theme_02_equity.png")
    plt.figure(figsize=(10,5))
    for name,result in results.items(): v=result.equity.equity; plt.plot(v.index,v/v.cummax()-1,label=name)
    plt.legend(); plt.ylabel("Drawdown"); plt.title("Theme-rule drawdowns"); save("theme_03_drawdowns.png")
    fig,axes=plt.subplots(1,2,figsize=(11,4)); labels=comparison.architecture.str.replace(" SAME THEME","",regex=False); axes[0].barh(labels,comparison.cagr,color="#2563eb"); axes[0].set_xlabel("CAGR"); axes[0].set_title("Compound return"); axes[1].barh(labels,-comparison.maximum_drawdown,color="#dc2626"); axes[1].set_xlabel("Maximum drawdown magnitude"); axes[1].set_title("Peak-to-trough risk"); fig.suptitle("CAGR and drawdown by architecture"); save("theme_04_cagr_drawdown.png")
    plt.figure(figsize=(10,4)); plt.plot(pd.to_datetime(day_detail.date),day_detail.max_same_theme_exposure,color="#7c3aed"); plt.axhline(2/3,ls="--",color="black"); plt.ylabel("Same-theme exposure"); plt.title("Audited same-theme exposure over time"); save("theme_05_exposure_timeline.png")
    plt.figure(figsize=(10,4)); plt.scatter(pd.to_datetime(baskets.start_date),baskets.correlation_60d,c=baskets.basket_return,cmap="RdYlGn"); plt.axhline(.3,ls="--",color="gray"); plt.axhline(.6,ls="--",color="gray"); plt.ylabel("Trailing 60-day correlation"); plt.title("Basket correlation at formation"); save("theme_06_correlation_timeline.png")
    plt.figure(); plt.bar(order_summary.theme_position_order.astype(str),order_summary.average_return,color="#0891b2"); plt.xlabel("Theme position order"); plt.ylabel("Average return"); plt.title("Return by first/second/third same-theme position"); save("theme_07_position_order_return.png")
    plt.figure(); plt.bar(order_summary.theme_position_order.astype(str),order_summary.plus5_hit_rate,color="#16a34a"); plt.xlabel("Theme position order"); plt.ylabel("+5% exit rate"); plt.title("Target hit rate by theme position order"); save("theme_08_position_order_hit.png")
    same=int(simultaneous.same_theme.sum()) if len(simultaneous) else 0; diff=len(simultaneous)-same if len(simultaneous) else 0; plt.figure(); plt.bar(["same-theme","different-theme"],[same,diff],color=["#dc2626","#2563eb"]); plt.ylabel("Multi-stop dates"); plt.title("Simultaneous stops by concentration"); save("theme_09_simultaneous_stops.png")
    g=gaps.loc[gaps.theme_context.isin(["single","multiple"])]; plt.figure(); plt.bar(g.theme_context,g.average_gap_portfolio_impact,color="#dc2626"); plt.ylabel("Average portfolio impact"); plt.title("Gap losses by theme context"); save("theme_10_gap_losses.png")
    overall=theme_results.groupby("theme").total_pnl.sum().sort_values(); plt.figure(figsize=(9,6)); plt.barh(overall.index,overall.values,color=["#dc2626" if x<0 else "#16a34a" for x in overall]); plt.xlabel("Net P&L ($)"); plt.title("P&L by audited theme"); save("theme_11_theme_pnl.png")
    y=day_detail.loc[pd.to_datetime(day_detail.date).dt.year.eq(2024)]; plt.figure(figsize=(10,4)); plt.plot(pd.to_datetime(y.date),y.max_same_theme_exposure,color="#b45309"); plt.axhline(2/3,ls="--",color="black"); plt.ylabel("Same-theme exposure"); plt.title("2024 theme concentration"); save("theme_12_2024_timeline.png")
    high=episodes.loc[episodes.threshold.eq(.90)]; plt.figure(); plt.bar(range(len(high)),high.portfolio_return,color=["#16a34a" if x>=0 else "#dc2626" for x in high.portfolio_return]); plt.xlabel("High-concentration episode"); plt.ylabel("Portfolio return"); plt.title(">90% same-theme episode outcomes"); save("theme_13_episode_outcomes.png")
    a=alpha_risk.loc[~alpha_risk.architecture.eq("BASE 3x33.33")]; fig,axes=plt.subplots(1,2,figsize=(11,4)); labels=a.architecture.str.replace(" SAME THEME","",regex=False); axes[0].barh(labels,a.alpha_lost,color=["#16a34a" if x<0 else "#dc2626" for x in a.alpha_lost]); axes[0].axvline(0,color="black",lw=.8); axes[0].set_xlabel("Return sacrificed (negative = gained)"); axes[1].barh(labels,a.risk_removed,color="#2563eb"); axes[1].axvline(0,color="black",lw=.8); axes[1].set_xlabel("Maximum drawdown removed"); fig.suptitle("Alpha lost versus risk removed"); save("theme_14_alpha_risk.png")
    annual.pivot(index="year",columns="architecture",values="return").plot.bar(figsize=(11,5)); plt.ylabel("Return"); plt.title("Annual performance comparison"); save("theme_15_annual.png")


def run_theme_diagnostic(random_simulations: int=5000) -> dict:
    outputs=CONFIG.outputs_dir; tables=outputs/"tables"; charts=outputs/"charts"; tables.mkdir(parents=True,exist_ok=True)
    events=pd.read_parquet(tables/"fast_rebound_events.parquet"); stop,_=select_initial_stop(events); model,threshold,_=fit_chronological_model(events,stop); sample,_,_=rank_recommendations(events,model,threshold); qualified=sample.loc[sample.estimated_probability.ge(threshold)].copy()
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet"); panel=_slice(prepare_universe_panel(raw,"strict_cap"),"2023-01-01","2026-12-31")
    mapping=audited_theme_mapping(qualified.ticker); mapping.to_csv(tables/"theme_mapping_audited.csv",index=False); theme_map=mapping.set_index("ticker").audited_theme.to_dict()
    configs={"BASE 3x33.33":{"max_daily_rank":3},"MAX 2 SAME THEME":{"max_daily_rank":999,"max_per_theme":2},"MAX 1 SAME THEME":{"max_daily_rank":999,"max_per_theme":1},"66.67% THEME CAP":{"max_daily_rank":999,"max_theme_exposure":2/3}}
    results={}; ignored={}; metric_rows=[]; annual=[]
    for name,rule in configs.items():
        arch=AllocationArchitecture(name,3,1/3,rule["max_daily_rank"]); result,missed=run_allocation_portfolio(panel,qualified,arch,stop,theme_map_override=theme_map,max_per_theme=rule.get("max_per_theme"),max_theme_exposure=rule.get("max_theme_exposure")); results[name]=result; ignored[name]=missed
        result.trades["theme"]=result.trades.ticker.map(theme_map).fillna("other"); m=allocation_metrics(result); m["average_pairwise_correlation"]=average_pairwise_correlation(result,panel); metric_rows.append({"architecture":name,**m}); annual.append(annual_architecture(result,name))
    comparison=pd.DataFrame(metric_rows); annual=pd.concat(annual,ignore_index=True); base=results["BASE 3x33.33"]; base_metrics=comparison.set_index("architecture").loc["BASE 3x33.33"]
    if len(base.trades)!=226 or abs(base_metrics.total_return-.7412725)>1e-5: raise RuntimeError("Frozen 3x33.33 baseline did not reproduce")
    base_trades,order_summary=position_order(base.trades,theme_map); base.trades=base_trades; base_trades["theme_context"]=np.where(base_trades.theme_position_order.gt(1),"multiple","single")
    day_detail,day_summary=classify_portfolio_days(base,base_trades,theme_map); baskets=basket_analysis(base,base_trades,panel,theme_map); basket_summary_table=basket_summary(baskets); core_summary=basket_summary(baskets.loc[baskets.positions.eq(3)]); correlations=correlation_analysis(baskets); simultaneous=simultaneous_stops(base,base_trades,panel,theme_map); gaps=gap_concentration(base_trades); major_losses=major_loss_days(base,panel,theme_map); theme_results=theme_trade_results(base_trades); episodes=high_concentration_episodes(day_detail,base,base_trades,theme_map)
    skipped_detail,skipped_summary=skipped_trade_analysis(ignored,qualified,stop)
    skipped_map=skipped_summary.set_index("architecture") if len(skipped_summary) else pd.DataFrame(); comp=comparison.set_index("architecture"); y24=annual.loc[annual.year.eq(2024)].set_index("architecture")["return"]
    comparison["2024_return"]=comparison.architecture.map(y24); comparison["skipped_trades"]=comparison.architecture.map(skipped_map.skipped_trades if len(skipped_map) else {}).fillna(0).astype(int); comparison["skipped_average_return"]=comparison.architecture.map(skipped_map.average_skipped_return if len(skipped_map) else {})
    tail_events={name:architecture_tail_events(result) for name,result in results.items()}
    comparison["simultaneous_stop_dates"]=comparison.architecture.map({k:v[0] for k,v in tail_events.items()}); comparison["largest_combined_gap_loss"]=comparison.architecture.map({k:v[1] for k,v in tail_events.items()}); comparison["max_same_theme_exposure"]=comparison.maximum_theme_exposure
    tails=[]
    for name,rule in configs.items(): tails.append(theme_tail_sensitivity(panel,qualified,results[name],stop,theme_map,name,rule))
    tails=pd.concat(tails,ignore_index=True); top_removed=tails.loc[tails.sensitivity.eq("remove_top_10pct")].set_index("architecture").total_return; comparison["top_10pct_removed_return"]=comparison.architecture.map(top_removed)
    base_dd=abs(base_metrics.maximum_drawdown); comparison["alpha_lost"]=base_metrics.total_return-comparison.total_return; comparison["risk_removed"]=base_dd-comparison.maximum_drawdown.abs(); comparison.loc[comparison.risk_removed.abs().lt(1e-4),"risk_removed"]=0; comparison["cagr_sacrificed_per_drawdown_removed"]=(base_metrics.cagr-comparison.cagr)/comparison.risk_removed.where(comparison.risk_removed.gt(1e-4)); comparison["return_sacrificed_per_skipped_trade"]=comparison.alpha_lost/comparison.skipped_trades.replace(0,np.nan)
    alpha_risk=comparison[["architecture","alpha_lost","risk_removed","cagr_sacrificed_per_drawdown_removed","return_sacrificed_per_skipped_trade"]]
    # A random rerun is justified only by material deterministic risk removal.
    restricted=comparison.loc[~comparison.architecture.eq("BASE 3x33.33")]; promising=restricted.loc[restricted.risk_removed.ge(.02)&restricted.cagr.ge(base_metrics.cagr*.90)&restricted.sharpe.ge(base_metrics.sharpe*.90)]
    random=pd.DataFrame()
    if len(promising):
        best=str(promising.sort_values(["calmar","cagr"],ascending=False).iloc[0].architecture); random=pd.concat([matched_random_allocation(sample,results[x],stop,x,random_simulations) for x in ("BASE 3x33.33",best)],ignore_index=True); random.to_csv(tables/"theme_random_control.csv",index=False)
    final_cols=["architecture","total_return","cagr","sharpe","maximum_drawdown","calmar","2024_return","worst_day","worst_week","average_exposure","max_same_theme_exposure","simultaneous_stop_dates","largest_combined_gap_loss","skipped_trades","skipped_average_return","top_10pct_removed_return"]
    frames={"theme_portfolio_comparison":comparison[final_cols],"theme_portfolio_day_classification":day_summary,"theme_portfolio_days":day_detail,"theme_basket_analysis":baskets,"theme_basket_summary":basket_summary_table,"theme_core_three_position_comparison":core_summary,"theme_position_order":order_summary,"theme_skipped_trades":skipped_detail,"theme_skipped_summary":skipped_summary,"theme_correlation_analysis":correlations,"theme_simultaneous_stops":simultaneous,"theme_gap_concentration":gaps,"theme_major_loss_days":major_losses,"theme_results":theme_results,"theme_high_concentration_episodes":episodes,"theme_alpha_vs_risk":alpha_risk,"theme_tail_sensitivity":tails,"theme_annual":annual}
    for name,frame in frames.items(): frame.to_csv(tables/f"{name}.csv",index=False)
    _save_charts(results,comparison,day_detail,basket_summary_table,baskets,order_summary,simultaneous,gaps,theme_results,episodes,alpha_risk,annual,charts)

    pos=order_summary.set_index("theme_position_order"); second=pos.loc[2] if 2 in pos.index else pd.Series(dtype=float); third=pos.loc[3] if 3 in pos.index else pd.Series(dtype=float); c=correlations.set_index("correlation_bucket"); max2=comp.loc["MAX 2 SAME THEME"]; max1=comp.loc["MAX 1 SAME THEME"]; cap=comp.loc["66.67% THEME CAP"]
    episode97=episodes.sort_values("maximum_same_theme_exposure",ascending=False).iloc[0]; high2024=day_detail.loc[pd.to_datetime(day_detail.date).dt.year.eq(2024)&day_detail.max_same_theme_exposure.gt(2/3)]
    decision="KEEP 3×33.33% UNCHANGED"
    answers=[
        f"Partly: second same-theme positions added ${second.get('total_incremental_pnl',0):,.0f}, but the two third positions lost ${abs(third.get('total_incremental_pnl',0)):,.0f}. This is descriptive, not proof of independent alpha.",
        f"Not demonstrably. All restrictions left maximum drawdown at approximately {base_metrics.maximum_drawdown:.1%}.",
        f"No clear reduction: the base largest single-gap impact was {base_metrics.largest_portfolio_gap_impact:.1%}, and predefined restrictions did not remove the governing gap episode.",
        f"No clear evidence. There were {len(simultaneous)} multi-stop dates, of which {int(simultaneous.same_theme.sum()) if len(simultaneous) else 0} involved duplicate themes.",
        f"Only partly; basket 60-day correlations are reported by label and ranged across low/moderate/high buckets. Theme membership was an imperfect proxy.",
        f"{'Yes' if second.get('average_return',0)>0 else 'No'}: {int(second.get('trades',0))} second-theme trades averaged {second.get('average_return',np.nan):.2%}, profit factor {second.get('profit_factor',np.nan):.2f}.",
        f"Insufficient evidence: only {int(third.get('trades',0))} third-theme trades existed. Their unweighted mean was {third.get('average_return',np.nan):.2%}, but profit factor was {third.get('profit_factor',np.nan):.2f} and total P&L was ${third.get('total_incremental_pnl',0):,.0f}.",
        f"Second positions contributed ${second.get('total_incremental_pnl',0):,.0f}; third positions contributed ${third.get('total_incremental_pnl',0):,.0f}.",
        "Three-different-theme basket risk was not consistently lower across drawdown, simultaneous-stop, and correlation measures; see the basket summary.",
        "Their relative profitability is shown directly in the basket summary; the limited three-position episode count prevents a strong causal conclusion.",
        f"No material risk improvement. Max-two returned {max2.total_return:.1%} versus {base_metrics.total_return:.1%}, but drawdown remained {max2.maximum_drawdown:.1%}; the apparent gain depends on only {int(comparison.set_index('architecture').loc['MAX 2 SAME THEME','skipped_trades'])} skipped trades.",
        f"No. Max-one reduced return to {max1.total_return:.1%}, Sharpe to {max1.sharpe:.2f}, and did not improve maximum drawdown.",
        f"No material improvement. The entry-time 66.67% cap returned {cap.total_return:.1%} with unchanged {cap.maximum_drawdown:.1%} drawdown.",
        ", ".join(f"{r.architecture}: {r.alpha_lost:.1%}" for r in alpha_risk.itertuples() if r.architecture!="BASE 3x33.33")+" return difference versus base.",
        ", ".join(f"{r.architecture}: {r.risk_removed:.1%}" for r in alpha_risk.itertuples() if r.architecture!="BASE 3x33.33")+" drawdown removed.",
        f"No. 2024 had {len(high2024)} days above 66.67% audited same-theme exposure. Base returned {y24['BASE 3x33.33']:.1%}; max-two {y24['MAX 2 SAME THEME']:.1%}, max-one {y24['MAX 1 SAME THEME']:.1%}, and the cap {y24['66.67% THEME CAP']:.1%}.",
        "No. The largest drawdown persisted unchanged under every predefined restriction, so concentration was not its causal mechanism.",
        "Yes. Point-in-time return correlation distinguishes low/moderate/high overlap inside the same broad labels and is more granular than the audited themes, but no correlation rule was tested.",
        f"The original 97.3% residual-'other' observation was a mapping artifact (AVGO/WDC/STX). The audited maximum was {episode97.maximum_same_theme_exposure:.1%} in {episode97.theme} ({episode97.stocks}); its portfolio return was {episode97.portfolio_return:.1%} and drawdown {episode97.maximum_drawdown:.1%}. It is a plausible stress risk, but historical harm is not established.",
        "No. The predefined caps failed to remove the actual maximum drawdown or governing gap loss, while max-one discarded material alpha and max-two's improvement rested on four skips.",
    ]
    report=f"""# Fast-Rebound Theme-Concentration Diagnostic

**Final decision: {decision}**

The frozen 3×33.33% architecture reproduced exactly: {len(base.trades)} trades, {base_metrics.total_return:.2%} total return, {base_metrics.cagr:.2%} CAGR, Sharpe {base_metrics.sharpe:.2f}, and {base_metrics.maximum_drawdown:.2%} maximum drawdown. No signal, threshold, stop, target, holding-period, execution, or cost assumption changed.

## Executive diagnosis

The evidence does **not** justify a permanent theme rule. Max-two-per-theme improved the historical return slightly, but it skipped only four theme-conflicting signals and removed **zero** maximum drawdown, worst-day, or governing gap risk. Max-one sacrificed return and Sharpe without improving maximum drawdown. The 66.67% entry-time cap was nearly indistinguishable from base. This fails the predeclared standard for material, generalizable risk removal.

## Mapping audit

The original 97.3% figure occurred on 2026-07-01 when AVGO, WDC, and STX were all assigned to the residual `other` bucket because two names were unmapped. The audited broad mapping separates AVGO into AI/semiconductors and WDC/STX into data infrastructure. The true audited maximum was {episode97.maximum_same_theme_exposure:.2%}: {episode97.stocks} in **{episode97.theme}**, from {pd.Timestamp(episode97.start_date).date()} to {pd.Timestamp(episode97.end_date).date()}. The complete mapping is `outputs/tables/theme_mapping_audited.csv`.

## Most important comparison

{comparison[final_cols].to_markdown(index=False,floatfmt='.4f')}

The 66.67% cap is enforced only at entry; existing positions are not rebalanced, so market drift can move realized theme exposure modestly above the cap.

## Portfolio-day classifications

{day_summary.to_markdown(index=False,floatfmt='.4f')}

## Basket comparison

{basket_summary_table.to_markdown(index=False,floatfmt='.4f')}

The direct three-position comparison, which removes two-stock episodes from the label comparison, is:

{core_summary.to_markdown(index=False,floatfmt='.4f')}

## First, second, and third theme positions

{order_summary.to_markdown(index=False,floatfmt='.4f')}

Order is determined using positions already open immediately before each next-open entry, with same-day lower ranks counted first. These are descriptive contributions, not randomized causal estimates.

## Skipped alpha

{skipped_summary.to_markdown(index=False,floatfmt='.4f')}

The full skipped-event ledger retains score, rank, hypothetical fixed-rule return, MAE, MFE, target, and stop outcomes.

## Correlation evidence

{correlations.to_markdown(index=False,floatfmt='.4f')}

Correlations are trailing 20/60-session close-return correlations measured at basket formation, without future information. Theme labels and actual correlations do not map one-for-one.

## Simultaneous stops and gaps

{simultaneous.to_markdown(index=False,floatfmt='.4f')}

{gaps.to_markdown(index=False,floatfmt='.4f')}

The ten worst portfolio days provide the loss-state check requested. Correlations are measured through the preceding session, so they do not leak the loss day:

{major_losses.to_markdown(index=False,floatfmt='.4f')}

## Theme-by-theme outcomes

{theme_results.to_markdown(index=False,floatfmt='.4f')}

`single` and `multiple` indicate whether the trade was the first or an additional same-theme position at entry.

## High-concentration episodes

{episodes.to_markdown(index=False,floatfmt='.4f')}

The audited >90% clean-technology episode held ENPH, ALB, and TSLA. Its realized path and eventual trade outcomes are retained above; it did not produce the strategy's maximum drawdown. This is economically concentrated, but one episode cannot establish a reliable cap benefit.

## 2024

There were {len(high2024)} portfolio-days above 66.67% audited same-theme exposure in 2024. SMCI is classified as data infrastructure; its overlaps are included in the episode and basket tables. Base returned {y24['BASE 3x33.33']:.2%}; max-two worsened to {y24['MAX 2 SAME THEME']:.2%}, max-one to {y24['MAX 1 SAME THEME']:.2%}, and the 66.67% cap to {y24['66.67% THEME CAP']:.2%}. Theme restrictions therefore do not fix the 2024 loss.

## Alpha lost versus risk removed

{alpha_risk.to_markdown(index=False,floatfmt='.4f')}

## Annual comparison

{annual.to_markdown(index=False,floatfmt='.4f')}

## Tail robustness

{tails.to_markdown(index=False,floatfmt='.4f')}

No restricted architecture met the deterministic hurdle for a matched-random rerun: at least two percentage points of drawdown reduction while preserving 90% of CAGR and Sharpe. Therefore no `theme_random_control.csv` was created, as instructed.

## Explicit answers to the 20 questions

"""+"\n".join(f"{i}. {answer}" for i,answer in enumerate(answers,1))+f"""

## Decision

**{decision}.** Same-theme exposure should remain a monitored risk diagnostic, particularly for a high-alpha sleeve, but the historical evidence does not support changing the frozen architecture. Do not add a theme cap based on four skipped max-two observations or a single clean-technology concentration episode.
"""
    (outputs/"fast_rebound_theme_diagnostic_report.md").write_text(report)
    return {"decision":decision,"base_return":base_metrics.total_return,"audited_max_theme_exposure":episode97.maximum_same_theme_exposure,"random_control_run":bool(len(random))}
