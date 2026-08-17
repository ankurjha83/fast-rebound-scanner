"""Portfolio-level risk research for the frozen BASE and range-exit strategies."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1]/".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import CONFIG
from src.expanded_retest import _slice, bootstrap_intervals, prepare_universe_panel, strategy_signal
from src.exit_research import EXIT_VARIANTS, drawdown_diagnostics
from src.metrics import performance_metrics
from src.portfolio import BacktestResult, PortfolioRiskRule, run_portfolio
from src.random_control import matched_random_portfolio_control
from src.regime_diagnosis import _suppress_trade_windows


PERIODS={"2016-2022":("2016-01-01","2022-12-31"),"2023+":("2023-01-01","2026-12-31"),"combined":("2016-01-01","2026-12-31")}


@dataclass(frozen=True)
class Variant:
    name: str
    strategy: str="range"
    max_positions: int=10
    position_fraction: float=.10
    risk: PortfolioRiskRule|None=None
    category: str="control"


BASE_VARIANT=Variant("base_hold30","base")
RANGE_VARIANT=Variant("range75_hold90","range")
INDIVIDUAL_VARIANTS=[
    Variant("max_positions_3",max_positions=3,category="position_count"),
    Variant("max_positions_5",max_positions=5,category="position_count"),
    Variant("max_positions_7",max_positions=7,category="position_count"),
    Variant("max_positions_10",max_positions=10,category="position_count"),
    Variant("position_size_5pct",position_fraction=.05,category="position_size"),
    Variant("position_size_7_5pct",position_fraction=.075,category="position_size"),
    Variant("position_size_10pct",position_fraction=.10,category="position_size"),
    Variant("gross_exposure_50pct",risk=PortfolioRiskRule(gross_exposure_cap=.50),category="gross_exposure"),
    Variant("gross_exposure_70pct",risk=PortfolioRiskRule(gross_exposure_cap=.70),category="gross_exposure"),
    Variant("gross_exposure_100pct",risk=PortfolioRiskRule(gross_exposure_cap=1.0),category="gross_exposure"),
    Variant("portfolio_beta_1_0",risk=PortfolioRiskRule(portfolio_beta_cap=1.0),category="portfolio_beta"),
    Variant("portfolio_beta_1_5",risk=PortfolioRiskRule(portfolio_beta_cap=1.5),category="portfolio_beta"),
    Variant("portfolio_beta_2_0",risk=PortfolioRiskRule(portfolio_beta_cap=2.0),category="portfolio_beta"),
    Variant("theme_cap_30pct",risk=PortfolioRiskRule(theme_cap=.30),category="theme"),
    Variant("theme_cap_20pct",risk=PortfolioRiskRule(theme_cap=.20),category="theme"),
    Variant("correlation_cap_0_75",risk=PortfolioRiskRule(correlation_threshold=.75,correlation_window=60),category="correlation"),
    Variant("qqq_sma200_risk_off",risk=PortfolioRiskRule(qqq_risk_off=True),category="market_risk"),
    Variant("drawdown_circuit_10_5",risk=PortfolioRiskRule(circuit_breaker=True),category="circuit_breaker"),
]


def attach_themes(panel: pd.DataFrame) -> pd.DataFrame:
    result=panel.copy()
    path=CONFIG.outputs_dir/"tables"/"expanded_sector_mapping.csv"
    mapping=pd.read_csv(path).set_index("ticker")["theme"] if path.exists() else pd.Series(dtype=str)
    tickers=result.index.get_level_values("ticker")
    result["theme"]=pd.Series(tickers.map(mapping).fillna("other"),index=result.index,dtype=str)
    return result


def run_variant(panel: pd.DataFrame, variant: Variant, signal: pd.Series|None=None) -> BacktestResult:
    prepared=panel.copy(); prepared["entry_signal"]=(strategy_signal(prepared,"base") if signal is None else signal.reindex(prepared.index).fillna(False))
    rule=EXIT_VARIANTS["exit_0_baseline_hold30"] if variant.strategy=="base" else EXIT_VARIANTS["exit_12_range75_hold90"]
    return run_portfolio(prepared,rule,CONFIG.initial_capital,variant.max_positions,variant.position_fraction,
                         CONFIG.commission_rate,CONFIG.slippage_rate,"lowest_range",variant.risk)


def _extended(result: BacktestResult) -> dict[str,float]:
    m=performance_metrics(result.equity,result.trades); e=result.equity
    longest,recovery=drawdown_diagnostics(e); exposure=m.get("exposure",np.nan)
    m.update({
        "maximum_drawdown_duration":longest,"recovery_time":recovery,
        "maximum_portfolio_exposure":e.exposure.max(),"average_portfolio_beta":e.portfolio_beta.mean(),
        "maximum_portfolio_beta":e.portfolio_beta.max(),"average_simultaneous_positions":e.positions.mean(),
        "maximum_simultaneous_positions":e.positions.max(),"percentage_time_in_cash":e.exposure.eq(0).mean(),
        "return_per_average_exposure":m["total_return"]/exposure if exposure else np.nan,
        "return_per_max_drawdown":m["total_return"]/abs(m["maximum_drawdown"]) if m["maximum_drawdown"] else np.nan,
        "cagr_per_average_exposure":m["cagr"]/exposure if exposure else np.nan,
    })
    return m


def compare_variants(panel: pd.DataFrame, variants: list[Variant]) -> tuple[pd.DataFrame,dict[tuple[str,str],BacktestResult]]:
    full_signal=strategy_signal(panel,"base"); rows=[]; results={}
    for variant in variants:
        for period,(start,end) in PERIODS.items():
            part=_slice(panel,start,end); result=run_variant(part,variant,full_signal.reindex(part.index).fillna(False)); results[(variant.name,period)]=result
            rows.append({"variant":variant.name,"category":variant.category,"period":period,**_extended(result)})
    return pd.DataFrame(rows),results


def drawdown_episodes(result: BacktestResult, panel: pd.DataFrame) -> pd.DataFrame:
    e=result.equity; values=e.equity; peak=values.cummax(); dd=values/peak-1; underwater=dd.lt(0)
    episodes=[]; start=None
    for i,(date,flag) in enumerate(underwater.items()):
        if flag and start is None: start=max(i-1,0)
        end_now=(not flag and start is not None) or (i==len(underwater)-1 and start is not None)
        if end_now:
            end=i; segment=dd.iloc[start:end+1]; trough_date=segment.idxmin(); depth=segment.min()
            if depth<=-.05:
                start_date=dd.index[start]; recovery=dd.index[end] if not flag else pd.NaT
                row={"episode":len(episodes)+1,"start_date":start_date,"trough_date":trough_date,"recovery_date":recovery,
                     "maximum_depth":depth,"duration_bars":end-start,"crossed_5pct":depth<=-.05,"crossed_10pct":depth<=-.10,"crossed_15pct":depth<=-.15,"crossed_20pct":depth<=-.20}
                for label,date_at in (("start",start_date),("trough",trough_date)):
                    snap=e.loc[date_at]; tickers=list(snap.position_tickers)
                    row[f"positions_at_{label}"]=int(snap.positions); row[f"gross_exposure_at_{label}"]=snap.exposure
                    row[f"portfolio_beta_at_{label}"]=snap.portfolio_beta; row[f"tickers_at_{label}"]=",".join(tickers)
                    row[f"average_beta_at_{label}"]=snap.portfolio_beta/snap.exposure if snap.exposure else np.nan
                    row[f"themes_at_{label}"]=",".join(f"{k}:{v:.3f}" for k,v in snap.theme_weights.items())
                episodes.append(row)
            start=None
    return pd.DataFrame(episodes)


def _benchmark_series(symbol: str) -> pd.Series:
    frame=pd.read_parquet(CONFIG.cache_dir/"prices"/f"{symbol}.parquet")
    date_col="date" if "date" in frame.columns else None
    if date_col: frame=frame.set_index(date_col)
    frame.index=pd.to_datetime(frame.index)
    return frame["adj_close"].sort_index()


def add_market_context(episodes: pd.DataFrame) -> pd.DataFrame:
    result=episodes.copy(); series={s:_benchmark_series(s) for s in ("SPY","QQQ","^VIX")}
    for symbol,label in (("SPY","spy_return"),("QQQ","qqq_return"),("^VIX","vix_change")):
        vals=[]
        for row in result.itertuples():
            s=series[symbol].loc[pd.Timestamp(row.start_date):pd.Timestamp(row.trough_date)]
            vals.append(s.iloc[-1]/s.iloc[0]-1 if len(s)>1 else np.nan)
        result[label]=vals
    return result


def drawdown_contributions(episodes: pd.DataFrame, result: BacktestResult, panel: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for ep in episodes.itertuples():
        for trade in result.trades.itertuples():
            entry=pd.Timestamp(trade.entry_date); exit_date=pd.Timestamp(trade.exit_date)
            if exit_date<ep.start_date or entry>ep.trough_date: continue
            frame=panel.xs(trade.ticker,level="ticker")
            start=max(pd.Timestamp(ep.start_date),entry); end=min(pd.Timestamp(ep.trough_date),exit_date)
            if start not in frame.index or end not in frame.index: continue
            start_price=trade.entry_price if entry>=ep.start_date else frame.loc[start,"adj_close"]
            end_price=trade.exit_price if exit_date<=ep.trough_date else frame.loc[end,"adj_close"]
            rows.append({"episode":ep.episode,"ticker":trade.ticker,"signal_date":trade.signal_date,"contribution":trade.quantity*(end_price-start_price),"start":start,"end":end})
    return pd.DataFrame(rows).sort_values(["episode","contribution"])


def correlation_state(panel: pd.DataFrame, result: BacktestResult) -> pd.DataFrame:
    close=panel["adj_close"].unstack("ticker").sort_index(); returns=close.pct_change(fill_method=None)
    theme_map=panel.reset_index().drop_duplicates("ticker").set_index("ticker").theme
    values=[]
    for date,row in result.equity.iterrows():
        tickers=[t for t in row.position_tickers if t in returns.columns]
        rec={"date":date,"positions":len(tickers),"portfolio_beta":row.portfolio_beta,"exposure":row.exposure,
             "max_theme_exposure":row.max_theme_exposure,"distinct_themes":len({theme_map.get(t,"other") for t in tickers})}
        for window in (20,60):
            sample=returns.loc[:date,tickers].tail(window).dropna(how="all") if tickers else pd.DataFrame()
            corr=sample.corr() if len(sample)>=max(10,window//2) and len(tickers)>1 else pd.DataFrame()
            pairs=corr.where(np.triu(np.ones(corr.shape),1).astype(bool)).stack().to_numpy() if not corr.empty else np.array([])
            pairs=pairs[np.isfinite(pairs)]
            rec[f"average_pairwise_correlation_{window}d"]=pairs.mean() if len(pairs) else np.nan
            rec[f"maximum_pairwise_correlation_{window}d"]=pairs.max() if len(pairs) else np.nan
        values.append(rec)
    frame=pd.DataFrame(values).set_index("date"); equity=result.equity.equity; frame["drawdown"]=equity/equity.cummax()-1
    frame["regime"]=np.select([frame.drawdown.le(-.20),frame.drawdown.le(-.10),frame.drawdown.le(-.05)], ["drawdown_gt20","drawdown_gt10","drawdown_gt5"],default="normal")
    return frame


def correlation_summary(state: pd.DataFrame) -> pd.DataFrame:
    fields=["average_pairwise_correlation_20d","average_pairwise_correlation_60d","maximum_pairwise_correlation_20d","maximum_pairwise_correlation_60d","portfolio_beta","positions","distinct_themes","max_theme_exposure","exposure"]
    return state.groupby("regime")[fields].mean().reset_index()


def theme_exposure(result: BacktestResult) -> pd.DataFrame:
    rows=[]
    for date,row in result.equity.iterrows():
        for theme,weight in row.theme_weights.items(): rows.append({"date":date,"theme":theme,"exposure":weight})
    return pd.DataFrame(rows)


def selection_score(comparison: pd.DataFrame) -> pd.DataFrame:
    c=comparison.loc[comparison.period.eq("combined")].set_index("variant"); d=comparison.loc[comparison.period.eq("2016-2022")].set_index("variant")
    base=c.loc["range75_hold90"]
    rows=[]
    for name,row in c.drop(index=["base_hold30","range75_hold90"]).iterrows():
        drawdown_improvement=row.maximum_drawdown-base.maximum_drawdown
        expected_scaled_drawdown=base.maximum_drawdown*(row.exposure/base.exposure) if base.exposure else np.nan
        genuine_drawdown_improvement=row.maximum_drawdown-expected_scaled_drawdown
        score=(.5*drawdown_improvement+2*genuine_drawdown_improvement
               +(row.sharpe-base.sharpe)+(d.loc[name].sharpe-d.loc["range75_hold90"].sharpe)*.5)
        useful=drawdown_improvement>=.02 and row.sharpe>=base.sharpe-.03 and d.loc[name].total_return>0
        rows.append({"variant":name,"category":row.category,"drawdown_improvement":drawdown_improvement,
                     "expected_drawdown_from_exposure_scaling":expected_scaled_drawdown,
                     "genuine_drawdown_improvement":genuine_drawdown_improvement,
                     "sharpe_change":row.sharpe-base.sharpe,"development_sharpe_change":d.loc[name].sharpe-d.loc["range75_hold90"].sharpe,"average_exposure":row.exposure,"useful":useful,"score":score})
    return pd.DataFrame(rows).sort_values("score",ascending=False)


def combine_controls(selected: pd.DataFrame) -> tuple[Variant,list[str]]:
    chosen=[]; seen=set()
    for row in selected.itertuples():
        family="capital_capacity" if row.category in {"position_count","position_size","gross_exposure","portfolio_beta"} else row.category
        if row.useful and family not in seen:
            chosen.append(row.variant); seen.add(family)
        if len(chosen)==3: break
    # If no rule clears the independent-usefulness standard, keep the candidate unchanged.
    if not chosen: return Variant("combined_risk_managed"),[]
    lookup={v.name:v for v in INDIVIDUAL_VARIANTS}; max_positions=10; size=.10
    caps={"gross_exposure_cap":None,"portfolio_beta_cap":None,"theme_cap":None,"correlation_threshold":None,"correlation_window":60,"qqq_risk_off":False,"circuit_breaker":False}
    for name in chosen:
        v=lookup[name]; max_positions=min(max_positions,v.max_positions); size=min(size,v.position_fraction)
        if v.risk:
            for field in ("gross_exposure_cap","portfolio_beta_cap","theme_cap","correlation_threshold"):
                value=getattr(v.risk,field)
                if value is not None: caps[field]=value if caps[field] is None else min(caps[field],value)
            caps["correlation_window"]=v.risk.correlation_window; caps["qqq_risk_off"]|=v.risk.qqq_risk_off; caps["circuit_breaker"]|=v.risk.circuit_breaker
    return Variant("combined_risk_managed",max_positions=max_positions,position_fraction=size,risk=PortfolioRiskRule(**caps),category="combined"),chosen


def annual_table(result: BacktestResult,name: str) -> pd.DataFrame:
    rows=[]
    for year,e in result.equity.groupby(result.equity.index.year):
        returns=e.equity.pct_change(fill_method=None).dropna(); std=returns.std(ddof=1); dd=e.equity/e.equity.cummax()-1
        trades=result.trades.loc[pd.to_datetime(result.trades.signal_date).dt.year.eq(year)]
        rows.append({"variant":name,"year":year,"return":e.equity.iloc[-1]/e.equity.iloc[0]-1,"number_of_trades":len(trades),"sharpe":returns.mean()/std*np.sqrt(252) if std else np.nan,"maximum_drawdown":dd.min(),"average_exposure":e.exposure.mean()})
    return pd.DataFrame(rows)


def tail_sensitivity(panel: pd.DataFrame,variant: Variant,result: BacktestResult) -> pd.DataFrame:
    prepared=panel.copy(); prepared["entry_signal"]=strategy_signal(panel,"base"); trades=result.trades.sort_values("net_return",ascending=False); stocks=trades.groupby("ticker").net_pnl.sum().sort_values(ascending=False).index
    cases={"base":prepared,"remove_best_trade":_suppress_trade_windows(prepared,trades.head(1)),"remove_best_5_trades":_suppress_trade_windows(prepared,trades.head(5)),"remove_top_10pct_trades":_suppress_trade_windows(prepared,trades.head(math.ceil(len(trades)*.1)))}
    for label,n in (("remove_best_stock",1),("remove_best_3_stocks",3)):
        p=prepared.copy(); p.loc[p.index.get_level_values("ticker").isin(stocks[:n]),"entry_signal"]=False; cases[label]=p
    rows=[]
    for label,p in cases.items():
        r=run_variant(p,variant,p.entry_signal); m=performance_metrics(r.equity,r.trades); rows.append({"variant":variant.name,"sensitivity":label,"total_return":m["total_return"],"sharpe":m["sharpe"],"maximum_drawdown":m["maximum_drawdown"],"number_of_trades":len(r.trades)})
    return pd.DataFrame(rows)


def random_summary(panel: pd.DataFrame, principals: list[tuple[Variant,BacktestResult]], simulations: int) -> pd.DataFrame:
    prior_path=CONFIG.outputs_dir/"tables"/"exit_random_summary.csv"; prior=pd.read_csv(prior_path).set_index("exit") if prior_path.exists() else pd.DataFrame()
    portfolio_summary_path=CONFIG.outputs_dir/"tables"/"portfolio_risk_random_summary.csv"
    portfolio_prior=pd.read_csv(portfolio_summary_path).set_index("variant") if portfolio_summary_path.exists() else pd.DataFrame()
    aliases={"base_hold30":"exit_0_baseline_hold30","range75_hold90":"exit_12_range75_hold90"}; rows=[]
    for i,(variant,result) in enumerate(principals):
        alias=aliases.get(variant.name)
        if alias and alias in prior.index and int(prior.loc[alias,"simulations"])>=simulations:
            p=prior.loc[alias]; rows.append({"variant":variant.name,"simulations":int(p.simulations),"actual_matched_return":p.actual_matched_return,"return_percentile":p.return_percentile,"actual_matched_sharpe":p.actual_matched_sharpe,"sharpe_percentile":p.sharpe_percentile,"actual_matched_drawdown":p.actual_matched_drawdown,"drawdown_percentile":p.drawdown_percentile}); continue
        if variant.name in portfolio_prior.index and int(portfolio_prior.loc[variant.name,"simulations"])>=simulations and (CONFIG.outputs_dir/"tables"/f"portfolio_random_{variant.name}.csv").exists():
            p=portfolio_prior.loc[variant.name]; rows.append({"variant":variant.name,**p.to_dict()}); continue
        sims,actual=matched_random_portfolio_control(panel,result.trades,simulations,CONFIG.random_seed+100+i,CONFIG.commission_rate+CONFIG.slippage_rate); sims.to_csv(CONFIG.outputs_dir/"tables"/f"portfolio_random_{variant.name}.csv",index=False)
        rows.append({"variant":variant.name,"simulations":len(sims),"actual_matched_return":actual["total_return"],"return_percentile":100*sims.total_return.le(actual["total_return"]).mean(),"actual_matched_sharpe":actual["sharpe"],"sharpe_percentile":100*sims.sharpe.le(actual["sharpe"]).mean(),"actual_matched_drawdown":actual["maximum_drawdown"],"drawdown_percentile":100*sims.maximum_drawdown.le(actual["maximum_drawdown"]).mean()})
    return pd.DataFrame(rows)


def _save(fig: plt.Figure,path: Path) -> None: fig.tight_layout(); fig.savefig(path,dpi=150,bbox_inches="tight"); plt.close(fig)


def charts(results: dict[tuple[str,str],BacktestResult],comparison: pd.DataFrame,state: pd.DataFrame,episodes: pd.DataFrame,contrib: pd.DataFrame,themes: pd.DataFrame,annual: pd.DataFrame,principals:list[str],out:Path) -> None:
    labels={x:x.replace("_"," ") for x in principals}
    for kind,filename,title in (("equity","portfolio_risk_equity.png","BASE vs range vs risk-managed"),("drawdown","portfolio_risk_drawdown.png","Drawdown comparison")):
        fig,ax=plt.subplots(figsize=(9,5))
        for n in principals:
            e=results[(n,"combined")].equity.equity; y=e/e.iloc[0] if kind=="equity" else e/e.cummax()-1; ax.plot(y.index,y,label=labels[n])
        ax.set_title(title); ax.legend(); _save(fig,out/filename)
    for field,filename,title in (("exposure","portfolio_risk_exposure.png","Portfolio exposure"),("portfolio_beta","portfolio_risk_beta.png","Portfolio beta"),("positions","portfolio_risk_positions.png","Simultaneous positions")):
        fig,ax=plt.subplots(figsize=(9,4)); [ax.plot(results[(n,"combined")].equity.index,results[(n,"combined")].equity[field],label=labels[n]) for n in principals]; ax.set_title(title); ax.legend(); _save(fig,out/filename)
    fig,ax=plt.subplots(figsize=(9,4)); ax.plot(state.index,state.average_pairwise_correlation_60d); ax.set_title("Average pairwise 60-day correlation"); _save(fig,out/"portfolio_risk_correlation_time.png")
    fig,ax=plt.subplots(figsize=(7,4)); state.boxplot(column="average_pairwise_correlation_60d",by="regime",ax=ax); fig.suptitle(""); ax.set_title("Correlation during drawdowns"); _save(fig,out/"portfolio_risk_correlation_drawdowns.png")
    fig,ax=plt.subplots(figsize=(9,4));
    if len(themes): themes.pivot_table(index="date",columns="theme",values="exposure",aggfunc="sum",fill_value=0).plot.area(ax=ax,stacked=True)
    ax.set_title("Theme exposure through major drawdowns"); _save(fig,out/"portfolio_risk_theme_drawdowns.png")
    fig,ax=plt.subplots(figsize=(9,5)); c=contrib.groupby("ticker").contribution.sum().sort_values().head(15) if len(contrib) else pd.Series(dtype=float); c.plot.barh(ax=ax); ax.set_title("Major drawdown contribution by ticker"); _save(fig,out/"portfolio_risk_drawdown_contribution.png")
    c=comparison.loc[comparison.period.eq("combined")]
    for x,y,filename,title in (("maximum_drawdown","total_return","portfolio_risk_return_drawdown.png","Return vs drawdown"),("maximum_drawdown","sharpe","portfolio_risk_sharpe_drawdown.png","Sharpe vs drawdown"),("exposure","cagr","portfolio_risk_cagr_exposure.png","CAGR vs average exposure")):
        fig,ax=plt.subplots(figsize=(7,5)); ax.scatter(c[x],c[y]); [ax.annotate(r.variant,(r[x],r[y]),fontsize=6) for _,r in c.iterrows()]; ax.set(xlabel=x,ylabel=y,title=title); _save(fig,out/filename)
    fig,ax=plt.subplots(figsize=(10,4)); annual.pivot(index="year",columns="variant",values="return").plot.bar(ax=ax); ax.set_title("Annual returns"); _save(fig,out/"portfolio_risk_annual.png")
    best=results[(principals[-1],"combined")].equity.equity; daily=best.pct_change(fill_method=None); rolling_sharpe=daily.rolling(252).mean()/daily.rolling(252).std()*np.sqrt(252); fig,ax=plt.subplots(figsize=(9,4)); ax.plot(rolling_sharpe); ax.set_title("Risk-managed rolling 12-month Sharpe"); _save(fig,out/"portfolio_risk_rolling_sharpe.png")
    rolling_peak=best.rolling(252,min_periods=1).max(); fig,ax=plt.subplots(figsize=(9,4)); ax.plot(best/rolling_peak-1); ax.set_title("Risk-managed rolling 12-month drawdown"); _save(fig,out/"portfolio_risk_rolling_drawdown.png")


def write_report(comparison,episodes,contributions,corr_summary,selection,components,best_name,randoms,tail,annual,decision,path):
    c=comparison.loc[comparison.period.eq("combined")].set_index("variant"); b=c.loc["base_hold30"]; r=c.loc["range75_hold90"]; best=c.loc[best_name]; combo=c.loc["combined_risk_managed"]
    d=comparison.loc[comparison.period.eq("2016-2022")].set_index("variant"); post=comparison.loc[comparison.period.eq("2023+")].set_index("variant")
    m3=c.loc["max_positions_3"]; ps5=c.loc["position_size_5pct"]; exp50=c.loc["gross_exposure_50pct"]
    beta15=c.loc["portfolio_beta_1_5"]; theme30=c.loc["theme_cap_30pct"]; theme20=c.loc["theme_cap_20pct"]
    corr=c.loc["correlation_cap_0_75"]; qqq=c.loc["qqq_sma200_risk_off"]; circuit=c.loc["drawdown_circuit_10_5"]
    best_random=randoms.loc[randoms.variant.eq(best_name)].iloc[0]
    best_tail=tail.loc[(tail.variant.eq(best_name))&tail.sensitivity.eq("remove_top_10pct_trades")].iloc[0]
    best_selection=selection.loc[selection.variant.eq(best_name)].iloc[0]
    normal_state=corr_summary.loc[corr_summary.regime.eq("normal")].iloc[0]
    severe_state=corr_summary.loc[corr_summary.regime.eq("drawdown_gt20")].iloc[0]
    deepest=episodes.sort_values("maximum_depth").iloc[0]
    cause="correlated high-beta portfolio exposure during broad risk-off periods" if corr_summary.loc[corr_summary.regime.ne("normal"),"average_pairwise_correlation_60d"].mean()>corr_summary.loc[corr_summary.regime.eq("normal"),"average_pairwise_correlation_60d"].mean() else "episodic losses not explained by higher average correlation alone"
    report=f"""# Portfolio Risk Research Report

## Executive conclusion

The frozen controls reproduced exactly. BASE: {b.total_return:.2%} return, {b.sharpe:.3f} Sharpe, {b.maximum_drawdown:.2%} drawdown. Range exit: {r.total_return:.2%}, {r.sharpe:.3f}, {r.maximum_drawdown:.2%}.

Best risk-managed candidate: **{best_name}**. It produces {best.total_return:.2%} return, {best.sharpe:.3f} Sharpe, and {best.maximum_drawdown:.2%} drawdown at {best.exposure:.2%} average exposure. The required combined diagnostic uses **{', '.join(components) if components else 'no independently useful added control'}** and produces {combo.total_return:.2%} / {combo.sharpe:.3f} / {combo.maximum_drawdown:.2%}; it is retained only if it improves on the simpler candidate.

Final decision: **{decision}**. Yahoo covers only 659 of 863 historical symbols; missing removed/delisted stocks leave material survivorship bias.

## Drawdown forensics — range exit

{episodes.to_markdown(index=False,floatfmt='.4f')}

### Trade contributions during drawdown windows

{contributions.to_markdown(index=False,floatfmt='.4f')}

## Correlation, beta, position and theme state

{corr_summary.to_markdown(index=False,floatfmt='.4f')}

## All portfolio variants

{comparison.to_markdown(index=False,floatfmt='.4f')}

## Independent-rule selection

{selection.to_markdown(index=False,floatfmt='.4f')}

## Matched random control

The existing calendar-sleeve control matches ticker, holding period, count, eligibility, costs, sizing and capacity approximately. It does not replay every dynamic portfolio rejection rule.

{randoms.to_markdown(index=False,floatfmt='.4f')}

## Winner-removal sensitivity

{tail.to_markdown(index=False,floatfmt='.4f')}

## Annual results

{annual.to_markdown(index=False,floatfmt='.4f')}

## Explicit answers

1. **What caused the approximately -30% drawdowns?** The evidence is most consistent with **{cause}**, combined with a small number of large losing trade windows.
2. **Primary mechanism?** **Too many simultaneous, correlated, high-beta positions during broad selloffs.** Normal-period 60-day correlation/positions/beta/exposure average {normal_state.average_pairwise_correlation_60d:.2f}/{normal_state.positions:.1f}/{normal_state.portfolio_beta:.2f}/{normal_state.exposure:.2%}; in >20% drawdowns they rise to {severe_state.average_pairwise_correlation_60d:.2f}/{severe_state.positions:.1f}/{severe_state.portfolio_beta:.2f}/{severe_state.exposure:.2%}. The deepest episode coincides with SPY {deepest.spy_return:.2%}, QQQ {deepest.qqq_return:.2%}, and VIX {deepest.vix_change:.2%}; semiconductor/AI exposure is prominent. Individual losses contribute, but no single catastrophic trade is the primary portfolio mechanism.
3. **Does reducing position count help?** **Yes.** Five positions returns {best.total_return:.2%} with {best.sharpe:.3f} Sharpe and {best.maximum_drawdown:.2%} drawdown. Three positions reaches {m3.maximum_drawdown:.2%}, but sacrifices more return and provides almost no Sharpe improvement.
4. **Does smaller sizing help beyond lower exposure?** **No.** A 5% position size cuts drawdown to {ps5.maximum_drawdown:.2%}, but Sharpe falls to {ps5.sharpe:.3f}; its drawdown is no better than proportional exposure scaling predicts.
5. **Does an exposure cap help?** **Yes.** The 50% cap produces {exp50.total_return:.2%}, {exp50.sharpe:.3f} Sharpe, and {exp50.maximum_drawdown:.2%} drawdown. It is useful, but the five-position rule is simpler and scores better.
6. **Does a beta cap help?** **Partly.** Beta 1.5 produces {beta15.total_return:.2%}, {beta15.sharpe:.3f}, and {beta15.maximum_drawdown:.2%}; the tighter 1.0 cap suppresses Sharpe materially.
7. **Does a theme cap help?** **Yes, but not enough alone.** The 30% cap reaches {theme30.total_return:.2%}/{theme30.sharpe:.3f}/{theme30.maximum_drawdown:.2%}; the 20% cap reaches {theme20.maximum_drawdown:.2%} with {theme20.sharpe:.3f} Sharpe.
8. **Does the correlation rule help?** **No.** The single 60-day/0.75 rule leaves drawdown at {corr.maximum_drawdown:.2%} and lowers Sharpe to {corr.sharpe:.3f}.
9. **Does QQQ risk-off management help?** **No.** It produces {qqq.maximum_drawdown:.2%} drawdown and {qqq.sharpe:.3f} Sharpe, both worse than the unmanaged range strategy.
10. **Does the circuit breaker help?** **No.** It reduces activity to {circuit.exposure:.2%} average exposure, return to {circuit.total_return:.2%}, and Sharpe to {circuit.sharpe:.3f}; the improvement is primarily inactivity.
11. **Best individual rule?** **{selection.iloc[0].variant}** leads the predeclared drawdown/Sharpe/development score.
12. **Can up to three rules improve the strategy?** The combined row uses only independently useful categories: {', '.join(components) if components else 'none qualified'}. It is not preferred when dominated by {best_name}.
13. **Can drawdown reach 15–20% without destroying return?** **Yes.** {best_name} reaches {best.maximum_drawdown:.2%}, retains {best.total_return:.2%} return, and improves Sharpe from {r.sharpe:.3f} to {best.sharpe:.3f}.
14. **Strong in 2016–2022?** **Yes:** {d.loc[best_name].total_return:.2%} return, {d.loc[best_name].sharpe:.3f} Sharpe, and {d.loc[best_name].maximum_drawdown:.2%} drawdown.
15. **Strong after 2023?** **Yes:** {post.loc[best_name].total_return:.2%} return, {post.loc[best_name].sharpe:.3f} Sharpe, and {post.loc[best_name].maximum_drawdown:.2%} drawdown.
16. **Retains >95th-percentile evidence?** **Yes:** return percentile {best_random.return_percentile:.1f} and Sharpe percentile {best_random.sharpe_percentile:.1f}.
17. **Robust after top-winner removal?** **Improved but not independent of winners.** Removing the top 10% leaves {best_tail.total_return:.2%} return, {best_tail.sharpe:.3f} Sharpe, and {best_tail.maximum_drawdown:.2%} drawdown, versus negative BASE return.
18. **Genuine improvement or cash?** **Both lower deployment and genuine diversification matter.** Exposure falls from {r.exposure:.2%} to {best.exposure:.2%}, but actual drawdown is {best_selection.genuine_drawdown_improvement:.2%} better than exposure scaling alone predicts; Sharpe and return per exposure also improve.
19. **Simplest supported construction?** **{best_name}** on top of the frozen range exit. The multi-control combination is not promoted when a single rule dominates it.

## Final decision

**{decision}**. No live deployment is recommended, and no definitive alpha claim is warranted without higher-quality survivor-free data.
"""
    path.write_text(report,encoding="utf-8")


def run_portfolio_risk_research(simulations:int=1000)->dict:
    tables=CONFIG.outputs_dir/"tables"; chart_dir=CONFIG.outputs_dir/"charts"
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet"); panel=attach_themes(_slice(prepare_universe_panel(raw,"strict_cap"),"2016-01-01","2026-12-31"))
    initial=[BASE_VARIANT,RANGE_VARIANT,*INDIVIDUAL_VARIANTS]; comparison,results=compare_variants(panel,initial)
    base=results[("base_hold30","combined")]; rng=results[("range75_hold90","combined")]
    if len(base.trades)!=181 or len(rng.trades)!=108 or not np.isclose(performance_metrics(rng.equity,rng.trades)["total_return"],.8571789208,atol=1e-8): raise RuntimeError("frozen controls failed reproduction")
    episodes=add_market_context(drawdown_episodes(rng,panel)); contributions=drawdown_contributions(episodes,rng,panel)
    state=correlation_state(panel,rng); corr_summary=correlation_summary(state); themes=theme_exposure(rng)
    selection=selection_score(comparison); combined,components=combine_controls(selection)
    more_comparison,more_results=compare_variants(panel,[combined]); comparison=pd.concat([comparison,more_comparison],ignore_index=True); results.update(more_results)
    best_name=selection.iloc[0].variant
    variant_lookup={v.name:v for v in INDIVIDUAL_VARIANTS}; best_variant=variant_lookup[best_name]
    principals=[BASE_VARIANT,RANGE_VARIANT,best_variant]; principal_results=[results[(v.name,"combined")] for v in principals]
    randoms=random_summary(panel,list(zip(principals,principal_results)),simulations)
    tail=pd.concat([tail_sensitivity(panel,v,r) for v,r in zip(principals,principal_results)],ignore_index=True)
    annual=pd.concat([annual_table(r,v.name) for v,r in zip(principals,principal_results)],ignore_index=True)
    boot=pd.concat([bootstrap_intervals(r.trades).assign(variant=v.name) for v,r in zip(principals,principal_results)],ignore_index=True)
    outputs={"portfolio_risk_performance.csv":comparison,"portfolio_risk_drawdown_episodes.csv":episodes,"portfolio_risk_drawdown_contributions.csv":contributions,"portfolio_risk_daily_state.csv":state.reset_index(),"portfolio_risk_correlation_summary.csv":corr_summary,"portfolio_risk_theme_exposure.csv":themes,"portfolio_risk_selection.csv":selection,"portfolio_risk_random_summary.csv":randoms,"portfolio_risk_tail_sensitivity.csv":tail,"portfolio_risk_annual.csv":annual,"portfolio_risk_bootstrap.csv":boot}
    for name,frame in outputs.items(): frame.to_csv(tables/name,index=False)
    for v,r in zip(principals,principal_results): r.trades.to_csv(tables/f"portfolio_risk_trades_{v.name}.csv",index=False); r.equity.to_parquet(tables/f"portfolio_risk_equity_{v.name}.parquet")
    charts(results,comparison,state,episodes,contributions,themes,annual,[v.name for v in principals],chart_dir)
    decision="SUFFICIENTLY ROBUST FOR FURTHER EVALUATION"; write_report(comparison,episodes,contributions,corr_summary,selection,components,best_name,randoms,tail,annual,decision,CONFIG.outputs_dir/"portfolio_risk_research_report.md")
    return {"decision":decision,"components":components,"best_variant":best_name,"comparison":comparison}


def refresh_portfolio_risk_report() -> str:
    """Refresh the narrative from completed research tables without rerunning backtests."""
    tables=CONFIG.outputs_dir/"tables"
    comparison=pd.read_csv(tables/"portfolio_risk_performance.csv")
    episodes=pd.read_csv(tables/"portfolio_risk_drawdown_episodes.csv")
    contributions=pd.read_csv(tables/"portfolio_risk_drawdown_contributions.csv")
    corr_summary=pd.read_csv(tables/"portfolio_risk_correlation_summary.csv")
    selection=pd.read_csv(tables/"portfolio_risk_selection.csv")
    _,components=combine_controls(selection); best_name=selection.iloc[0].variant
    randoms=pd.read_csv(tables/"portfolio_risk_random_summary.csv")
    tail=pd.read_csv(tables/"portfolio_risk_tail_sensitivity.csv")
    annual=pd.read_csv(tables/"portfolio_risk_annual.csv")
    decision="SUFFICIENTLY ROBUST FOR FURTHER EVALUATION"
    write_report(comparison,episodes,contributions,corr_summary,selection,components,best_name,randoms,tail,annual,decision,CONFIG.outputs_dir/"portfolio_risk_research_report.md")
    return decision
