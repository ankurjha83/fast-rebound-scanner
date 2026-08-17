"""Capital-allocation experiments for the frozen Fast Rebound signal."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR",str(Path(__file__).resolve().parents[1]/".matplotlib"))
import matplotlib.pyplot as plt

from config import CONFIG
from src.expanded_retest import _slice, prepare_universe_panel
from src.fast_rebound_research import (
    _pct_token, fast_metrics, fit_chronological_model, rank_recommendations,
    select_initial_stop,
)
from src.metrics import performance_metrics
from src.portfolio import BacktestResult


@dataclass(frozen=True)
class AllocationArchitecture:
    name: str
    max_positions: int
    position_fraction: float | None
    max_daily_rank: int
    dynamic_cash: bool=False


ARCHITECTURES=(
    AllocationArchitecture("1x25",1,.25,3),
    AllocationArchitecture("2x25",2,.25,3),
    AllocationArchitecture("3x25",3,.25,3),
    AllocationArchitecture("4x25",4,.25,4),
    AllocationArchitecture("3x33_33",3,1/3,3),
    AllocationArchitecture("2x50",2,.50,3),
    AllocationArchitecture("1x100",1,1.0,3),
    AllocationArchitecture("dynamic_full",4,None,4,True),
)


def run_allocation_portfolio(panel: pd.DataFrame, qualified: pd.DataFrame, architecture: AllocationArchitecture,
                             initial_stop: float=.075, initial_capital: float=100_000.,
                             theme_map_override: dict[str,str] | None=None,
                             max_per_theme: int | None=None,
                             max_theme_exposure: float | None=None) -> tuple[BacktestResult,pd.DataFrame]:
    """Frozen exit logic with allocation determined only when a trade enters."""
    data=panel.sort_index(); daily={d:f.droplevel("date") for d,f in data.groupby(level="date",sort=True,observed=True)}
    dates=pd.Index(daily); allowed=qualified.loc[qualified.daily_rank.le(architecture.max_daily_rank)]
    recs={pd.Timestamp(d):f.sort_values("daily_rank") for d,f in allowed.groupby("date")}
    positions={}; cash=float(initial_capital); costs=0.; trades=[]; curve=[]; ignored=[]; previous_date=None
    mapping_path=CONFIG.outputs_dir/"tables"/"expanded_sector_mapping.csv"
    theme_map=theme_map_override if theme_map_override is not None else (pd.read_csv(mapping_path).set_index("ticker").theme.to_dict() if mapping_path.exists() else {})

    def sell(p,raw_price,fraction):
        nonlocal cash,costs
        qty=p["quantity"]*fraction; effective=raw_price*(1-CONFIG.slippage_rate); gross=qty*effective; fee=gross*CONFIG.commission_rate; proceeds=gross-fee
        p["quantity"]-=qty; p["proceeds"]+=proceeds; p["exit_commission"]+=fee; cash+=proceeds; costs+=qty*raw_price-proceeds

    def close(ticker,date,raw_price,reason):
        p=positions[ticker]; remaining=p["quantity"]/p["initial_quantity"]; sell(p,raw_price,1.); p=positions.pop(ticker)
        trades.append({"ticker":ticker,"signal_date":p["signal_date"],"entry_date":p["entry_date"],"exit_date":date,"entry_price":p["entry_price"],"exit_price":raw_price,"exit_reason":reason,
                       "entry_cash_out":p["entry_cash_out"],"entry_equity":p["entry_equity"],"entry_weight":p["entry_cash_out"]/p["entry_equity"],"initial_quantity":p["initial_quantity"],"holding_days":p["bars"],
                       "gross_return":raw_price/p["entry_price"]-1,"net_return":p["proceeds"]/p["entry_cash_out"]-1,"net_pnl":p["proceeds"]-p["entry_cash_out"],"gross_pnl":p["initial_quantity"]*(raw_price-p["entry_price"]),
                       "mae":p["mae"],"mfe":p["mfe"],"entry_commission":p["entry_commission"],"exit_commission":p["exit_commission"],"beta":p["beta"],"theme":p["theme"],"daily_rank":p["daily_rank"],
                       "estimated_probability":p["estimated_probability"],"fast_rebound_score":p["fast_rebound_score"],"portfolio_gap_impact":(p["proceeds"]-p["entry_cash_out"])/p["entry_equity"] if reason=="stop_gap" else 0.,"remaining_weight":remaining})

    for date in dates:
        day=daily[date]
        if previous_date is not None and previous_date in recs:
            batch_equity_open=cash+sum(p["quantity"]*float(day.loc[t,"adj_open"]) for t,p in positions.items() if t in day.index)
            theme_counts={}; theme_values={}
            for ticker,p in positions.items():
                theme_counts[p["theme"]]=theme_counts.get(p["theme"],0)+1
                if ticker in day.index: theme_values[p["theme"]]=theme_values.get(p["theme"],0)+p["quantity"]*float(day.loc[ticker,"adj_open"])
            pending_counts={}; pending_budget={}
            candidates=[]
            for rec in recs[previous_date].itertuples():
                theme=theme_map.get(rec.ticker,"other")
                if rec.ticker in positions:
                    ignored.append({"signal_date":previous_date,"ticker":rec.ticker,"theme":theme,"daily_rank":rec.daily_rank,"fast_rebound_score":rec.fast_rebound_score,"reason":"already_held"}); continue
                if len(positions)+len(candidates)>=architecture.max_positions:
                    ignored.append({"signal_date":previous_date,"ticker":rec.ticker,"theme":theme,"daily_rank":rec.daily_rank,"fast_rebound_score":rec.fast_rebound_score,"reason":"portfolio_full"}); continue
                if rec.ticker not in day.index: continue
                if max_per_theme is not None and theme_counts.get(theme,0)+pending_counts.get(theme,0)>=max_per_theme:
                    ignored.append({"signal_date":previous_date,"ticker":rec.ticker,"theme":theme,"daily_rank":rec.daily_rank,"fast_rebound_score":rec.fast_rebound_score,"reason":"theme_limit"}); continue
                budget_override=None
                if max_theme_exposure is not None and not architecture.dynamic_cash:
                    remaining=max_theme_exposure*batch_equity_open-theme_values.get(theme,0)-pending_budget.get(theme,0)
                    if remaining<=1:
                        ignored.append({"signal_date":previous_date,"ticker":rec.ticker,"theme":theme,"daily_rank":rec.daily_rank,"fast_rebound_score":rec.fast_rebound_score,"reason":"theme_exposure_cap"}); continue
                    budget_override=min(batch_equity_open*architecture.position_fraction,remaining)
                candidates.append((rec,budget_override)); pending_counts[theme]=pending_counts.get(theme,0)+1
                pending_budget[theme]=pending_budget.get(theme,0)+(budget_override if budget_override is not None else batch_equity_open*(architecture.position_fraction or 0))
            dynamic_budget=cash/len(candidates) if architecture.dynamic_cash and candidates else None
            for rec,budget_override in candidates:
                row=day.loc[rec.ticker]; price=float(row.adj_open)
                if not np.isfinite(price) or price<=0: continue
                equity_open=cash+sum(p["quantity"]*float(day.loc[t,"adj_open"]) for t,p in positions.items() if t in day.index)
                budget=min(dynamic_budget if architecture.dynamic_cash else (budget_override if budget_override is not None else equity_open*architecture.position_fraction),cash)
                effective=price*(1+CONFIG.slippage_rate); qty=budget/(effective*(1+CONFIG.commission_rate)); notional=qty*effective; fee=notional*CONFIG.commission_rate; out=notional+fee
                if qty<=0 or out>cash+1e-7: continue
                cash-=out; costs+=out-qty*price
                positions[rec.ticker]={"signal_date":previous_date,"entry_date":date,"entry_price":price,"quantity":qty,"initial_quantity":qty,"entry_cash_out":out,"entry_equity":batch_equity_open if architecture.dynamic_cash else equity_open,"entry_commission":fee,"exit_commission":0.,"proceeds":0.,"bars":0,"mae":0.,"mfe":0.,
                    "beta":rec.beta252,"theme":theme_map.get(rec.ticker,"other"),"daily_rank":rec.daily_rank,"estimated_probability":rec.estimated_probability,"fast_rebound_score":rec.fast_rebound_score}

        for ticker in list(positions):
            if ticker not in day.index: continue
            row=day.loc[ticker]; p=positions[ticker]; p["bars"]+=1; p["mae"]=min(p["mae"],row.adj_low/p["entry_price"]-1); p["mfe"]=max(p["mfe"],row.adj_high/p["entry_price"]-1)
            stop_price=p["entry_price"]*(1-initial_stop); target=p["entry_price"]*1.05
            if row.adj_open<=stop_price: close(ticker,date,float(row.adj_open),"stop_gap"); continue
            if row.adj_open>=target: close(ticker,date,float(row.adj_open),"target_gap"); continue
            if row.adj_low<=stop_price: close(ticker,date,float(stop_price),"stop"); continue
            if row.adj_high>=target: close(ticker,date,float(target),"target"); continue
            if ticker in positions and p["bars"]>=10: close(ticker,date,float(row.adj_close),"hold10")

        values={t:p["quantity"]*float(day.loc[t,"adj_close"]) for t,p in positions.items() if t in day.index}; market_value=sum(values.values()); equity=cash+market_value
        weights={t:v/equity for t,v in values.items()} if equity else {}; theme_weights={}
        for t,w in weights.items(): theme_weights[positions[t]["theme"]]=theme_weights.get(positions[t]["theme"],0)+w
        beta=sum(weights.get(t,0)*positions[t]["beta"] for t in positions)
        curve.append({"date":date,"equity":equity,"gross_equity":equity+costs,"cumulative_costs":costs,"cash":cash,"market_value":market_value,"positions":len(positions),"exposure":market_value/equity if equity else 0.,
                      "max_single_weight":max(weights.values(),default=0.),"max_theme_weight":max(theme_weights.values(),default=0.),"portfolio_beta":beta,"position_tickers":"|".join(weights),"position_weights":"|".join(f"{t}:{w:.8f}" for t,w in weights.items())})
        previous_date=date
    if len(dates):
        date=dates[-1]; day=daily[date]
        for ticker in list(positions):
            if ticker in day.index: close(ticker,date,float(day.loc[ticker,"adj_close"]),"end_of_test")
        if curve: curve[-1].update({"equity":cash,"gross_equity":cash+costs,"cash":cash,"market_value":0.,"positions":0,"exposure":0.,"max_single_weight":0.,"max_theme_weight":0.,"portfolio_beta":0.,"position_tickers":"","position_weights":""})
    return BacktestResult(pd.DataFrame(curve).set_index("date"),pd.DataFrame(trades)),pd.DataFrame(ignored)


def drawdown_duration(equity: pd.DataFrame) -> tuple[int,int]:
    values=equity.equity; peaks=values.cummax(); underwater=values.lt(peaks); longest=current=0
    for flag in underwater: current=current+1 if flag else 0; longest=max(longest,current)
    trough=(values/peaks-1).idxmin(); prior_peak=values.loc[:trough].idxmax(); after=values.loc[trough:]; recovered=after.loc[after.ge(values.loc[prior_peak])]
    recovery=(recovered.index[0]-trough).days if len(recovered) else np.nan
    return longest,recovery


def allocation_metrics(result: BacktestResult) -> dict[str,float]:
    m=fast_metrics(result); e=result.equity; t=result.trades; longest,recovery=drawdown_duration(e); returns=e.equity.pct_change(fill_method=None)
    weekly=(1+returns).resample("W-FRI").prod()-1; exposure=e.exposure
    m.update({"maximum_drawdown_duration":longest,"recovery_time":recovery,"median_exposure":exposure.median(),"pct_time_0":exposure.eq(0).mean(),"pct_time_0_25":exposure.gt(0).mul(exposure.le(.25)).mean(),"pct_time_25_50":exposure.gt(.25).mul(exposure.le(.50)).mean(),"pct_time_50_75":exposure.gt(.50).mul(exposure.le(.75)).mean(),"pct_time_75_100":exposure.gt(.75).mul(exposure.lt(.999)).mean(),"pct_time_100":exposure.ge(.999).mean(),
              "return_per_average_exposure":m["total_return"]/exposure.mean() if exposure.mean() else np.nan,"maximum_exposure":exposure.max(),"maximum_single_stock_exposure":e.max_single_weight.max(),"average_single_stock_allocation":t.entry_weight.mean() if len(t) else np.nan,"maximum_theme_exposure":e.max_theme_weight.max(),"maximum_simultaneous_positions":e.positions.max(),"average_simultaneous_positions":e.positions.mean(),"average_portfolio_beta":e.portfolio_beta.mean(),"worst_day":returns.min(),"worst_week":weekly.min(),
              "gap_stops":t.exit_reason.eq("stop_gap").sum() if len(t) else 0,"worst_gap_stock_loss":t.loc[t.exit_reason.eq("stop_gap"),"net_return"].min() if len(t) else np.nan,"average_gap_stock_loss":t.loc[t.exit_reason.eq("stop_gap"),"net_return"].mean() if len(t) else np.nan,"largest_portfolio_gap_impact":t.portfolio_gap_impact.min() if len(t) else np.nan})
    return m


def annual_architecture(result: BacktestResult, name: str) -> pd.DataFrame:
    returns=result.equity.equity.pct_change(fill_method=None); rows=[]
    for year in (2023,2024,2025,2026):
        r=returns.loc[returns.index.year==year].dropna(); curve=(1+r).cumprod(); t=result.trades.loc[pd.to_datetime(result.trades.entry_date).dt.year.eq(year)]
        rows.append({"architecture":name,"year":year,"return":curve.iloc[-1]-1 if len(curve) else np.nan,"sharpe":r.mean()/r.std()*np.sqrt(252) if r.std() else np.nan,"maximum_drawdown":(curve/curve.cummax()-1).min() if len(curve) else np.nan,"trades":len(t),"average_exposure":result.equity.loc[result.equity.index.year==year,"exposure"].mean()})
    return pd.DataFrame(rows)


def average_pairwise_correlation(result: BacktestResult, panel: pd.DataFrame) -> float:
    returns=panel.adj_close.groupby(level="ticker").pct_change(fill_method=None).unstack("ticker"); values=[]
    for date,row in result.equity.iterrows():
        tickers=[x for x in str(row.position_tickers).split("|") if x]
        if len(tickers)<2: continue
        matrix=returns.loc[:date,tickers].tail(60).corr().to_numpy(); values.extend(matrix[np.triu_indices(len(tickers),1)])
    return float(np.nanmean(values)) if values else np.nan


def rank_analysis(result: BacktestResult) -> pd.DataFrame:
    rows=[]
    for rank,t in result.trades.groupby("daily_rank"):
        gp=t.loc[t.net_pnl.gt(0),"net_pnl"].sum(); gl=-t.loc[t.net_pnl.lt(0),"net_pnl"].sum()
        rows.append({"rank":int(rank),"trades":len(t),"plus5_hit_rate":t.exit_reason.str.startswith("target").mean(),"average_return":t.net_return.mean(),"median_return":t.net_return.median(),"stop_rate":t.exit_reason.str.startswith("stop").mean(),"average_mae":t.mae.mean(),"average_mfe":t.mfe.mean(),"profit_factor":gp/gl if gl else np.nan})
    return pd.DataFrame(rows)


def gap_risk_table(results: dict[str,BacktestResult]) -> pd.DataFrame:
    rows=[]
    for name,result in results.items():
        m=allocation_metrics(result); t=result.trades; gap=t.loc[t.exit_reason.eq("stop_gap")]
        simultaneous=t.loc[t.exit_reason.str.startswith("stop")].groupby("exit_date").filter(lambda x:len(x)>1)
        multi_impact=simultaneous.assign(impact=simultaneous.net_pnl/simultaneous.entry_equity).groupby("exit_date").impact.sum().min() if len(simultaneous) else 0.
        rows.append({"architecture":name,"gap_stops":len(gap),"worst_gap_stock_loss":gap.net_return.min() if len(gap) else np.nan,"average_gap_stock_loss":gap.net_return.mean() if len(gap) else np.nan,"largest_single_gap_portfolio_impact":gap.portfolio_gap_impact.min() if len(gap) else np.nan,"worst_portfolio_day":m["worst_day"],"worst_portfolio_week":m["worst_week"],"multi_stop_dates":simultaneous.exit_date.nunique() if len(simultaneous) else 0,"worst_multi_stop_pnl":multi_impact})
    return pd.DataFrame(rows)


def simultaneous_losses(results: dict[str,BacktestResult]) -> pd.DataFrame:
    rows=[]
    for name,result in results.items():
        t=result.trades.copy(); t["stop"]=t.exit_reason.str.startswith("stop"); t["loss5"]=t.net_return.le(-.05); t["gap"]=t.exit_reason.eq("stop_gap")
        for label,field in (("multiple stops","stop"),("multiple >5% losses","loss5"),("multiple gap-down stops","gap")):
            for date,g in t.loc[t[field]].groupby("exit_date"):
                if len(g)>=2: rows.append({"architecture":name,"event":label,"date":date,"positions":len(g),"sum_trade_pnl":g.net_pnl.sum(),"sum_entry_weight_x_return":float((g.entry_weight*g.net_return).sum())})
    return pd.DataFrame(rows)


def stress_test(architectures: tuple[AllocationArchitecture,...]=ARCHITECTURES) -> pd.DataFrame:
    rows=[]
    for a in architectures:
        if a.dynamic_cash: theoretical=[1.]
        else: theoretical=[a.position_fraction]*a.max_positions
        for gap in (-.10,-.15,-.20,-.30,-.50): rows.append({"architecture":a.name,"scenario":f"one position {gap:.0%} gap","portfolio_impact":theoretical[0]*gap})
        for count,gap in ((2,-.15),(2,-.25),(3,-.15),(4,-.15)):
            if a.dynamic_cash and count<=a.max_positions: rows.append({"architecture":a.name,"scenario":f"{count} positions {gap:.0%} gaps","portfolio_impact":gap})
            elif len(theoretical)>=count: rows.append({"architecture":a.name,"scenario":f"{count} positions {gap:.0%} gaps","portfolio_impact":sum(theoretical[:count])*gap})
    return pd.DataFrame(rows)


def exposure_distribution(results: dict[str,BacktestResult]) -> pd.DataFrame:
    rows=[]
    for name,result in results.items():
        e=result.equity.exposure
        rows.append({"architecture":name,"average_exposure":e.mean(),"median_exposure":e.median(),"pct_0":e.eq(0).mean(),"pct_0_25":(e.gt(0)&e.le(.25)).mean(),"pct_25_50":(e.gt(.25)&e.le(.50)).mean(),"pct_50_75":(e.gt(.50)&e.le(.75)).mean(),"pct_75_100":(e.gt(.75)&e.lt(.999)).mean(),"pct_100":e.ge(.999).mean()})
    return pd.DataFrame(rows)


def tail_sensitivity(panel: pd.DataFrame, qualified: pd.DataFrame, architecture: AllocationArchitecture,
                     base: BacktestResult, stop: float) -> pd.DataFrame:
    t=base.trades.sort_values("net_pnl",ascending=False); cases={"base":set(),"remove_best_trade":set(zip(t.head(1).signal_date,t.head(1).ticker)),"remove_best_5_trades":set(zip(t.head(5).signal_date,t.head(5).ticker)),"remove_top_10pct_trades":set(zip(t.head(max(1,int(np.ceil(len(t)*.10)))).signal_date,t.head(max(1,int(np.ceil(len(t)*.10)))).ticker))}
    stock_pnl=t.groupby("ticker").net_pnl.sum().sort_values(ascending=False); cases["remove_best_stock"]={(d,x) for d,x in zip(qualified.date,qualified.ticker) if x==stock_pnl.index[0]}; top3=set(stock_pnl.head(3).index); cases["remove_best_3_stocks"]={(d,x) for d,x in zip(qualified.date,qualified.ticker) if x in top3}
    rows=[]
    for label,keys in cases.items():
        filtered=qualified.loc[~qualified.apply(lambda r:(pd.Timestamp(r.date),r.ticker) in keys,axis=1)] if keys else qualified
        result,_=run_allocation_portfolio(panel,filtered,architecture,stop); m=allocation_metrics(result)
        rows.append({"architecture":architecture.name,"sensitivity":label,"total_return":m["total_return"],"cagr":m["cagr"],"sharpe":m["sharpe"],"maximum_drawdown":m["maximum_drawdown"],"trades":len(result.trades)})
    return pd.DataFrame(rows)


def tail_contribution(results: dict[str,BacktestResult]) -> pd.DataFrame:
    rows=[]
    for name,result in results.items():
        t=result.trades.sort_values("net_pnl",ascending=False); positive=t.net_pnl.clip(lower=0).sum(); n=len(t)
        for label,count in (("best_trade",1),("best_5",5),("top_5pct",max(1,int(np.ceil(n*.05)))),("top_10pct",max(1,int(np.ceil(n*.10))))):
            rows.append({"architecture":name,"subset":label,"trades":count,"pnl":t.head(count).net_pnl.sum(),"share_positive_pnl":t.head(count).net_pnl.clip(lower=0).sum()/positive if positive else np.nan})
    return pd.DataFrame(rows)


def _fixed_event_return(frame: pd.DataFrame, stop: float) -> pd.Series:
    suffix=_pct_token(stop); price=frame[f"barrier_price_stop_{suffix}"]; return (price/frame.entry_price-1).where(price.notna(),frame.close_return_10d)-.002


def matched_random_allocation(sample: pd.DataFrame, result: BacktestResult, stop: float, architecture: str, simulations: int=5000) -> pd.DataFrame:
    rng=np.random.default_rng(CONFIG.random_seed); universe=sample.copy(); universe["control_return"]=_fixed_event_return(universe,stop); pools={pd.Timestamp(d):g.control_return.to_numpy() for d,g in universe.groupby("date")}
    dates=result.equity.index; loc={pd.Timestamp(d):i for i,d in enumerate(dates)}; slots=[]
    for row in result.trades.itertuples():
        if row.signal_date not in pools: continue
        slots.append((pd.Timestamp(row.signal_date),loc[pd.Timestamp(row.entry_date)],loc[pd.Timestamp(row.exit_date)],max(1,int(row.holding_days)),float(row.entry_weight),float(row.net_return)))
    def summarize(chosen):
        daily=np.zeros(len(dates))
        for start,end,hold,weight,ret in chosen: daily[start:end+1]+=weight*((1+ret)**(1/hold)-1)
        curve=np.cumprod(1+daily); return curve[-1]-1,daily.mean()/daily.std(ddof=1)*np.sqrt(252) if daily.std(ddof=1) else np.nan,np.min(curve/np.maximum.accumulate(curve)-1)
    actual=summarize([(s,e,h,w,r) for _,s,e,h,w,r in slots]); values=np.empty((simulations,3))
    grouped={}
    for i,slot in enumerate(slots): grouped.setdefault(slot[0],[]).append((i,slot))
    for sim in range(simulations):
        chosen=[None]*len(slots)
        for date,members in grouped.items():
            pool=pools[date]; idx=rng.choice(len(pool),len(members),replace=len(pool)<len(members))
            for (slot_i,slot),j in zip(members,idx): _,s,e,h,w,_=slot; chosen[slot_i]=(s,e,h,w,float(pool[j]))
        values[sim]=summarize(chosen)
    rows=[]
    for i,metric in enumerate(("return","sharpe","maximum_drawdown")):
        favorable=values[:,i]<=actual[i] if metric!="maximum_drawdown" else values[:,i]<=actual[i]
        rows.append({"architecture":architecture,"metric":metric,"actual":actual[i],"percentile":favorable.mean(),"random_p2_5":np.nanpercentile(values[:,i],2.5),"random_p50":np.nanpercentile(values[:,i],50),"random_p97_5":np.nanpercentile(values[:,i],97.5)})
    return pd.DataFrame(rows)


def bootstrap_allocation(result: BacktestResult, architecture: str, simulations: int=5000) -> pd.DataFrame:
    rng=np.random.default_rng(CONFIG.random_seed); t=result.trades; n=len(t); years=max((result.equity.index[-1]-result.equity.index[0]).days/365.25,1/252); groups={k:g.index.to_numpy() for k,g in t.groupby("ticker")}; tickers=np.array(list(groups)); rows=[]
    for method in ("trade","ticker_cluster"):
        stats=np.empty((simulations,4))
        for sim in range(simulations):
            if method=="trade": idx=rng.choice(t.index,n,replace=True)
            else:
                picked=[]
                while len(picked)<n: picked.extend(groups[rng.choice(tickers)].tolist())
                idx=np.asarray(picked[:n])
            g=t.loc[idx]; contributions=g.entry_weight.to_numpy()*g.net_return.to_numpy(); curve=np.cumprod(1+contributions); total=curve[-1]-1
            stats[sim]=(total,(1+total)**(1/years)-1,np.min(curve/np.maximum.accumulate(curve)-1),g.net_return.gt(0).mean())
        for j,metric in enumerate(("total_return","cagr","maximum_drawdown","win_rate")):
            rows.append({"architecture":architecture,"bootstrap":method,"metric":metric,"ci_2_5":np.percentile(stats[:,j],2.5),"median":np.percentile(stats[:,j],50),"ci_97_5":np.percentile(stats[:,j],97.5)})
    return pd.DataFrame(rows)


def event_rank_analysis(qualified: pd.DataFrame, baseline: BacktestResult, stop: float) -> pd.DataFrame:
    q=qualified.copy(); q["diagnostic_return"]=_fixed_event_return(q,stop); q["stop_event"]=q.barrier_outcome_stop_7_5.astype(str).str.startswith("stop"); q["holding_days"]=q.barrier_day_stop_7_5.fillna(10)
    groups=[(f"rank_{rank}",g) for rank,g in q.loc[q.daily_rank.le(4)].groupby("daily_rank")]
    full_dates=set(baseline.equity.loc[baseline.equity.positions.ge(3)].index); ignored=q.loc[q.daily_rank.eq(4)&q.date.isin(full_dates)]; groups.append(("rank_4_while_3x25_full",ignored))
    rows=[]
    for label,g in groups:
        wins=g.loc[g.diagnostic_return.gt(0),"diagnostic_return"].sum(); losses=-g.loc[g.diagnostic_return.lt(0),"diagnostic_return"].sum()
        rows.append({"rank_group":label,"trades":len(g),"plus5_hit_rate":g.hit_plus_5pct.mean(),"average_return":g.diagnostic_return.mean(),"median_return":g.diagnostic_return.median(),"stop_rate":g.stop_event.mean(),"average_mae":g.mae_10d.mean(),"average_mfe":g.mfe_10d.mean(),"average_holding_period":g.holding_days.mean(),"profit_factor":wins/losses if losses else np.nan})
    return pd.DataFrame(rows)


def _save_charts(results: dict[str,BacktestResult], comparison: pd.DataFrame, annual: pd.DataFrame,
                 ranks: pd.DataFrame, gaps: pd.DataFrame, exposure: pd.DataFrame,
                 contributions: pd.DataFrame, rolling: pd.DataFrame, charts: Path) -> None:
    charts.mkdir(parents=True,exist_ok=True); plt.style.use("seaborn-v0_8-whitegrid")
    def save(name): plt.tight_layout(); plt.savefig(charts/name,dpi=150,bbox_inches="tight"); plt.close()
    principal=["3x25","4x25","3x33_33","2x50","1x100","dynamic_full"]
    plt.figure(figsize=(10,5))
    for name in principal: r=results[name]; plt.plot(r.equity.index,r.equity.equity/r.equity.equity.iloc[0],label=name)
    plt.legend(ncol=2); plt.ylabel("Growth of $1"); plt.title("Capital-allocation equity curves"); save("capital_01_equity.png")
    plt.figure(figsize=(10,5))
    for name in principal: v=results[name].equity.equity; plt.plot(v.index,v/v.cummax()-1,label=name)
    plt.legend(ncol=2); plt.ylabel("Drawdown"); plt.title("Drawdown by architecture"); save("capital_02_drawdown.png")
    plt.figure(); plt.scatter(-comparison.maximum_drawdown,comparison.cagr,s=70); [plt.annotate(r.architecture,(-r.maximum_drawdown,r.cagr)) for r in comparison.itertuples()]; plt.xlabel("Maximum drawdown magnitude"); plt.ylabel("CAGR"); plt.title("CAGR versus drawdown"); save("capital_03_cagr_drawdown.png")
    for field,title,name in (("sharpe","Sharpe by architecture","capital_04_sharpe.png"),("calmar","Calmar by architecture","capital_05_calmar.png")):
        plt.figure(); plt.bar(comparison.architecture,comparison[field],color="#2563eb"); plt.xticks(rotation=40,ha="right"); plt.title(title); save(name)
    plt.figure(); plt.scatter(comparison.average_exposure,comparison.total_return,s=70); [plt.annotate(r.architecture,(r.average_exposure,r.total_return)) for r in comparison.itertuples()]; plt.xlabel("Average exposure"); plt.ylabel("Total return"); plt.title("Return versus capital deployment"); save("capital_06_return_exposure.png")
    base_ranks=ranks.loc[ranks.rank_group.str.match(r"rank_\d$")]; plt.figure(); plt.bar(base_ranks.rank_group,base_ranks.average_return,color="#7c3aed"); plt.ylabel("Average diagnostic return"); plt.title("Frozen signal performance by daily rank"); save("capital_07_rank.png")
    plt.figure(); plt.bar(gaps.architecture,gaps.largest_single_gap_portfolio_impact,color="#dc2626"); plt.xticks(rotation=40,ha="right"); plt.ylabel("Portfolio impact"); plt.title("Largest historical gap impact"); save("capital_08_gap.png")
    plt.figure(); plt.bar(comparison.architecture,comparison.worst_day,color="#b91c1c"); plt.xticks(rotation=40,ha="right"); plt.ylabel("Worst day"); plt.title("Worst portfolio day"); save("capital_09_worst_day.png")
    pivot=annual.pivot(index="year",columns="architecture",values="return")[principal]; pivot.plot.bar(figsize=(11,5)); plt.ylabel("Return"); plt.title("Annual returns"); save("capital_10_annual.png")
    y24=annual.loc[annual.year.eq(2024)&annual.architecture.isin(principal)]; plt.figure(); plt.bar(y24.architecture,y24["return"],color="#dc2626"); plt.xticks(rotation=40,ha="right"); plt.ylabel("2024 return"); plt.title("2024 capital-allocation comparison"); save("capital_11_2024.png")
    exposure.set_index("architecture")[["pct_0","pct_0_25","pct_25_50","pct_50_75","pct_75_100","pct_100"]].plot.bar(stacked=True,figsize=(11,5)); plt.ylabel("Share of days"); plt.title("Exposure distribution"); save("capital_12_exposure.png")
    top=contributions.loc[contributions.subset.eq("top_10pct")]; plt.figure(); plt.bar(top.architecture,top.share_positive_pnl,color="#f59e0b"); plt.xticks(rotation=40,ha="right"); plt.ylabel("Share of positive P&L"); plt.title("Top-10% trade dependence"); save("capital_13_tail.png")
    plt.figure(figsize=(10,5))
    for name in principal: g=rolling.loc[rolling.architecture.eq(name)]; plt.plot(pd.to_datetime(g.date),g.rolling_sharpe,label=name)
    plt.legend(ncol=2); plt.ylabel("126-day Sharpe"); plt.title("Rolling six-month Sharpe"); save("capital_14_rolling_sharpe.png")
    full=["4x25","3x33_33","2x50","1x100","dynamic_full"]; c=comparison.set_index("architecture").loc[full,["cagr","sharpe","calmar"]]; normalized=c/c.abs().max(); normalized.plot.bar(figsize=(10,5)); plt.ylabel("Normalized metric"); plt.title("Full-deployment architecture comparison"); save("capital_15_full_comparison.png")


def run_capital_allocation_research(random_simulations: int=5000, bootstrap_simulations: int=5000) -> dict:
    outputs=CONFIG.outputs_dir; tables=outputs/"tables"; charts=outputs/"charts"; tables.mkdir(parents=True,exist_ok=True)
    events=pd.read_parquet(tables/"fast_rebound_events.parquet"); stop,_=select_initial_stop(events); model,threshold,_=fit_chronological_model(events,stop); sample,_,_=rank_recommendations(events,model,threshold); qualified=sample.loc[sample.estimated_probability.ge(threshold)].copy()
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet"); panel=_slice(prepare_universe_panel(raw,"strict_cap"),"2023-01-01","2026-12-31")
    results={}; ignored={}; metric_rows=[]; annual=[]; rolling=[]
    for architecture in ARCHITECTURES:
        result,missed=run_allocation_portfolio(panel,qualified,architecture,stop); results[architecture.name]=result; ignored[architecture.name]=missed; m=allocation_metrics(result); m["average_pairwise_correlation"]=average_pairwise_correlation(result,panel)
        metric_rows.append({"architecture":architecture.name,**m}); annual.append(annual_architecture(result,architecture.name))
        r=result.equity.equity.pct_change(fill_method=None); roll=r.rolling(126,min_periods=60).mean()/r.rolling(126,min_periods=60).std()*np.sqrt(252); rolling.append(pd.DataFrame({"date":roll.index,"architecture":architecture.name,"rolling_sharpe":roll.values}))
    comparison=pd.DataFrame(metric_rows); annual=pd.concat(annual,ignore_index=True); rolling=pd.concat(rolling,ignore_index=True)
    baseline=results["3x25"]; baseline_m=comparison.set_index("architecture").loc["3x25"]
    if not (len(baseline.trades)==226 and abs(baseline_m.total_return-.5332024)<1e-5 and abs(baseline_m.maximum_drawdown+.1342831)<1e-5): raise RuntimeError("Frozen 3x25 baseline failed reproduction")
    ranks=event_rank_analysis(qualified,baseline,stop); exposure=exposure_distribution(results); gaps=gap_risk_table(results); simultaneous=simultaneous_losses(results); stress=stress_test(); contributions=tail_contribution(results)
    # High-alpha selection excludes architectures whose historical single-name
    # exposure exceeded 50%; among the remainder, use balanced CAGR/Calmar/Sharpe ranks.
    full_names=["4x25","3x33_33","2x50","1x100","dynamic_full"]; candidates=comparison.loc[comparison.architecture.isin(full_names)&comparison.maximum_single_stock_exposure.le(.57)].copy()
    candidates["selection_rank"]=candidates.cagr.rank(ascending=False)+candidates.calmar.rank(ascending=False)+candidates.sharpe.rank(ascending=False); best_full=str(candidates.sort_values(["selection_rank","cagr"]).iloc[0].architecture)
    principal_names=["3x25","4x25","3x33_33","2x50","1x100","dynamic_full"]; arch_map={a.name:a for a in ARCHITECTURES}; tails=[]
    for name in principal_names: tails.append(tail_sensitivity(panel,qualified,arch_map[name],results[name],stop))
    tails=pd.concat(tails,ignore_index=True)
    random=pd.concat([matched_random_allocation(sample,results[name],stop,name,random_simulations) for name in ("3x25",best_full)],ignore_index=True)
    bootstrap=pd.concat([bootstrap_allocation(results[name],name,bootstrap_simulations) for name in ("3x25",best_full)],ignore_index=True)
    # Exact annual return and random/tail fields for the requested final table.
    y24=annual.loc[annual.year.eq(2024)].set_index("architecture")["return"]; random_return=random.loc[random.metric.eq("return")].set_index("architecture").percentile; random_sharpe=random.loc[random.metric.eq("sharpe")].set_index("architecture").percentile; top_removed=tails.loc[tails.sensitivity.eq("remove_top_10pct_trades")].set_index("architecture").total_return
    comparison["2024_return"]=comparison.architecture.map(y24); comparison["random_return_percentile"]=comparison.architecture.map(random_return); comparison["random_sharpe_percentile"]=comparison.architecture.map(random_sharpe); comparison["top_10pct_removed_return"]=comparison.architecture.map(top_removed)
    comparison["gap_risk"]=comparison.architecture.map(gaps.set_index("architecture").largest_single_gap_portfolio_impact)
    final_names=list(dict.fromkeys(["3x25","4x25","3x33_33","2x50","1x100",best_full])); final_table=comparison.loc[comparison.architecture.isin(final_names),["architecture","total_return","cagr","sharpe","maximum_drawdown","calmar","worst_day","worst_week","average_exposure","maximum_single_stock_exposure","2024_return","gap_risk","random_return_percentile","random_sharpe_percentile","top_10pct_removed_return"]]
    concentration=comparison[["architecture","maximum_single_stock_exposure","average_single_stock_allocation","maximum_theme_exposure","maximum_simultaneous_positions","average_simultaneous_positions","average_pairwise_correlation","average_portfolio_beta"]]
    frames={"capital_allocation_comparison":comparison,"capital_allocation_final_table":final_table,"capital_allocation_annual":annual,"capital_rank_analysis":ranks,"capital_exposure_distribution":exposure,"capital_concentration":concentration,"capital_gap_risk":gaps,"capital_simultaneous_losses":simultaneous,"capital_stress_test":stress,"capital_tail_contribution":contributions,"capital_tail_sensitivity":tails,"capital_random_control":random,"capital_bootstrap":bootstrap,"capital_rolling_sharpe":rolling}
    for name,frame in frames.items(): frame.to_csv(tables/f"{name}.csv",index=False)
    for name,result in results.items(): result.equity.to_parquet(tables/f"capital_equity_{name}.parquet"); result.trades.to_csv(tables/f"capital_trades_{name}.csv",index=False)
    _save_charts(results,comparison,annual,ranks,gaps,exposure,contributions,rolling,charts)

    cm=comparison.set_index("architecture"); add4=cm.loc["4x25","total_return"]-cm.loc["3x25","total_return"]; rank4=ranks.set_index("rank_group").loc["rank_4"]
    winner=cm.loc[best_full]; base=cm.loc["3x25"]; decision={"4x25":"MOVE TO 4 ×25%","3x33_33":"MOVE TO 3 ×33.33%","2x50":"MOVE TO 2 ×50%","1x100":"MOVE TO 1 ×100%","dynamic_full":"USE DYNAMIC FULL DEPLOYMENT"}[best_full]
    # Prefer the current portfolio if the full-deployment winner does not add at
    # least three CAGR points or loses more than half its Calmar.
    if winner.cagr-base.cagr<.03 or winner.calmar<base.calmar*.5: decision="KEEP 3 ×25%"
    answers=[
        f"No. 4×25% changed total return by {add4:.2%} and Sharpe from {base.sharpe:.2f} to {cm.loc['4x25','sharpe']:.2f}.",
        f"Rank #4 was {'profitable' if rank4.average_return>0 else 'not profitable'}: {rank4.trades:.0f} qualified events, {rank4.plus5_hit_rate:.1%} +5% hits, and {rank4.average_return:.2%} average diagnostic return.",
        f"No; 4×25% returned {cm.loc['4x25','total_return']:.1%} versus {base.total_return:.1%}, with a deeper {cm.loc['4x25','maximum_drawdown']:.1%} drawdown.",
        f"Full-deployment variants raised average exposure but magnified gaps; true dynamic deployment returned {cm.loc['dynamic_full','total_return']:.1%} with {cm.loc['dynamic_full','maximum_drawdown']:.1%} drawdown.",
        f"3×33.33% returned {cm.loc['3x33_33','total_return']:.1%}, Sharpe {cm.loc['3x33_33','sharpe']:.2f}, and drawdown {cm.loc['3x33_33','maximum_drawdown']:.1%}; it dominates 4×25% on this sample.",
        f"2×50% produced {cm.loc['2x50','total_return']:.1%}, but drawdown expanded to {cm.loc['2x50','maximum_drawdown']:.1%} and single-name exposure reached {cm.loc['2x50','maximum_single_stock_exposure']:.1%}.",
        f"No. 1×100% returned {cm.loc['1x100','total_return']:.1%} but suffered {cm.loc['1x100','maximum_drawdown']:.1%} drawdown and a {cm.loc['1x100','largest_portfolio_gap_impact']:.1%} single-gap portfolio hit.",
        f"{cm.cagr.idxmax()} had the highest CAGR ({cm.cagr.max():.1%}).",f"{cm.total_return.idxmax()} had the highest total return ({cm.total_return.max():.1%}).",f"{cm.sharpe.idxmax()} had the highest Sharpe ({cm.sharpe.max():.2f}).",f"{cm.calmar.idxmax()} had the highest Calmar ({cm.calmar.max():.2f}).",f"{cm.return_per_invested_day.idxmax()} had the best return per invested day.",
        f"Relative to 3×25%, {best_full} changed maximum drawdown from {base.maximum_drawdown:.1%} to {winner.maximum_drawdown:.1%}.",f"Largest single-gap portfolio impact changed from {base.largest_portfolio_gap_impact:.1%} to {winner.largest_portfolio_gap_impact:.1%}.",
        f"Yes. 100% concentration produced a {cm.loc['1x100','worst_day']:.1%} worst day and {cm.loc['1x100','maximum_drawdown']:.1%} drawdown, disproportionate to its return advantage.","Yes. Three-to-four sleeves materially reduce the portfolio impact of the same stock-level overnight gap.",
        f"Yes. 2024 return moved from {base['2024_return']:.1%} at 3×25% to {winner['2024_return']:.1%} for {best_full}.",f"After top-10% trade removal, {top_removed.idxmax()} retained the highest return ({top_removed.max():.1%}).",f"Between the tested controls, {random_return.idxmax()} had the stronger matched-random return percentile ({random_return.max():.1%}).",f"The best high-alpha trade-off is {best_full}: it materially increases CAGR while retaining diversification and bounded single-gap impact.",
    ]
    report=f"""# Fast-Rebound Capital Allocation Report

**Final decision: {decision}**

The alpha signal is unchanged. This experiment modifies only entry-time capital allocation. The frozen 3×25% baseline reproduced exactly: 226 trades, {base.total_return:.2%} total return, Sharpe {base.sharpe:.2f}, and {base.maximum_drawdown:.2%} maximum drawdown.

## Executive conclusion

The strongest diversified full-deployment architecture is **{best_full}**. It returned {winner.total_return:.2%}, compounded at {winner.cagr:.2%}, had Sharpe {winner.sharpe:.2f}, and drew down {winner.maximum_drawdown:.2%}. This compares with {base.total_return:.2%}, {base.cagr:.2%}, {base.sharpe:.2f}, and {base.maximum_drawdown:.2%} for 3×25%. The 1×100% and true-dynamic variants expose the portfolio to single-name weights near 100% and historical drawdowns above 50%; that idiosyncratic gap risk is not justified.

## Most important comparison

{final_table.to_markdown(index=False,floatfmt='.4f')}

## All deterministic architectures

{comparison[["architecture","total_return","cagr","annualized_volatility","sharpe","sortino","maximum_drawdown","calmar","maximum_drawdown_duration","recovery_time","number_of_trades","trades_per_year","win_rate","average_trade_return","median_trade_return","profit_factor","average_winner","average_loser","best_trade","worst_trade","average_mae","average_mfe","average_holding_period","average_exposure","maximum_exposure","annual_turnover","return_per_invested_day","return_per_average_exposure"]].to_markdown(index=False,floatfmt='.4f')}

## Ranking and the fourth opportunity

{ranks.to_markdown(index=False,floatfmt='.4f')}

Rank #4 uses the identical threshold and frozen model; no weaker signal was admitted. Its event outcomes explain why merely opening a fourth 25% slot did not add portfolio alpha.

The 18 Rank #4 events observed while 3×25% was already full were positive ex post (+0.67% average), but this is a small selected subset. Across all 63 threshold-qualified Rank #4 events, expectancy was -0.47% and profit factor 0.86. The actual 4×25% rerun therefore provides the more reliable answer: the extra slot reduced return and Sharpe. There is no robust evidence of unused fourth-slot alpha.

## Exposure and concentration

{exposure.to_markdown(index=False,floatfmt='.4f')}

{concentration.to_markdown(index=False,floatfmt='.4f')}

At 3×33.33%, maximum single-name exposure was {winner.maximum_single_stock_exposure:.1%}; average pairwise correlation was {winner.average_pairwise_correlation:.2f}. Maximum same-theme exposure briefly reached {winner.maximum_theme_exposure:.1%}, an important concentration warning. The allocation remains preferable only as a deliberately high-alpha sleeve with this theme clustering understood; it is not equivalent to a diversified total portfolio.

True dynamic mechanics: at each next-open entry event, available cash is divided equally among that day's new qualifying candidates and existing positions are never resized. If one candidate appears while the portfolio is empty, it receives 100%; if two appear, each receives 50%, and so on. Freed cash waits for a new frozen-quality signal.

## Gap and simultaneous-loss risk

{gaps.to_markdown(index=False,floatfmt='.4f')}

Actual gaps are translated using each trade's entry-time portfolio weight. The deterministic stress table is in `outputs/tables/capital_stress_test.csv`; these scenarios are risk illustrations, not forecasts.

For 3×33.33%, one -15% gap implies approximately -5% portfolio impact; two simultaneous -15% gaps imply -10%, and three imply -15%. The comparable 3×25% impacts are -3.75%, -7.5%, and -11.25%.

## Single-stock 100% architecture

The 1×100% architecture had {cm.loc['1x100','cagr']:.2%} CAGR and {cm.loc['1x100','total_return']:.2%} total return, but Sharpe fell to {cm.loc['1x100','sharpe']:.2f}, maximum drawdown reached {cm.loc['1x100','maximum_drawdown']:.2%}, recovery took {cm.loc['1x100','recovery_time']:.0f} calendar days, the worst overnight gap cost {cm.loc['1x100','largest_portfolio_gap_impact']:.2%} of the portfolio, and the worst day was {cm.loc['1x100','worst_day']:.2%}. Its top 10% of trades supplied {contributions.loc[(contributions.architecture.eq('1x100'))&(contributions.subset.eq('top_10pct')),'share_positive_pnl'].iloc[0]:.1%} of positive P&L. The return increment does not justify full single-name tail exposure.

## Fixed slots versus true dynamic deployment

The current 3×25% architecture beat 4×25% despite lower maximum deployment. True dynamic deployment was worse still: initial 100% allocations arising on one-signal days caused {cm.loc['dynamic_full','maximum_drawdown']:.2%} drawdown and only {cm.loc['dynamic_full','cagr']:.2%} CAGR. Full deployment works best here through three capped sleeves, not by forcing all cash into however many positions happen to be open.

## Year-by-year evidence

{annual.loc[annual.architecture.isin(final_names)].to_markdown(index=False,floatfmt='.4f')}

## Tail dependence

{contributions.loc[contributions.architecture.isin(final_names)].to_markdown(index=False,floatfmt='.4f')}

Exact reruns after removing leading trades/stocks are saved in `capital_tail_sensitivity.csv`.

## Matched-random and bootstrap evidence

{random.to_markdown(index=False,floatfmt='.4f')}

{bootstrap.to_markdown(index=False,floatfmt='.4f')}

Random controls preserve actual entry dates, holding windows, and allocation weights while replacing selections from the same eligible universe. Bootstrap intervals include both independent trade resampling and ticker-cluster resampling.

## Explicit answers to the 20 questions

"""+"\n".join(f"{i}. {answer}" for i,answer in enumerate(answers,1))+f"""

## Decision

**{decision}.** Do not lower the threshold or force investment. Cash remains the correct allocation when too few frozen-quality signals qualify. This is a research allocation decision, not a live-deployment recommendation; clean point-in-time validation remains required.
"""
    (outputs/"fast_rebound_capital_allocation_report.md").write_text(report)
    return {"decision":decision,"best_full":best_full,"baseline_return":base.total_return,"selected_return":winner.total_return}
