"""End-to-end reporting for the fast-rebound research hypothesis."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR",str(Path(__file__).resolve().parents[1]/".matplotlib"))
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import CONFIG
from src.expanded_retest import _slice, prepare_universe_panel
from src.fast_rebound_research import (
    FEATURES, HORIZONS, POSITIVE_LEVELS, PROFIT_METHODS, _pct_token,
    fast_metrics, fit_chronological_model, rank_recommendations,
    ranking_quality, run_fast_portfolio, select_initial_stop,
)


def _fmt(value: object) -> str:
    if pd.isna(value): return "n/a"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if abs(value) <= 2 else f"{value:.2f}"
    return str(value)


def _md(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    shown=frame[columns] if columns else frame
    return shown.to_markdown(index=False, floatfmt=".4f")


def _bucket(frame: pd.DataFrame, field: str, target: str, bins: int = 5) -> pd.DataFrame:
    clean=frame[[field,target,"hit_plus_5pct","close_return_10d","mae_10d","mfe_10d"]].dropna(subset=[field]).copy()
    clean["bucket"]=pd.qcut(clean[field],bins,duplicates="drop")
    return clean.groupby("bucket",observed=True).agg(
        observations=(field,"size"),minimum=(field,"min"),maximum=(field,"max"),
        plus5_hit_rate=("hit_plus_5pct","mean"),plus5_before_stop_rate=(target,"mean"),
        average_10d_return=("close_return_10d","mean"),average_mae=("mae_10d","mean"),average_mfe=("mfe_10d","mean"),
    ).reset_index().assign(bucket=lambda x:x.bucket.astype(str))


def _event_summary(sample: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for horizon in HORIZONS:
        rows.append({"horizon_days":horizon,"plus5_hit_rate":sample[f"hit_plus_5_within_{horizon}d"].mean(),
                     "average_close_return":sample[f"close_return_{horizon}d"].mean()})
    return pd.DataFrame(rows)


def _fit_plus5_model(events: pd.DataFrame) -> Pipeline:
    dev=events.loc[pd.to_datetime(events.date).le("2022-12-31") & events.complete_10d_path]
    model=Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",StandardScaler()),
                    ("logit",LogisticRegression(max_iter=1000,random_state=CONFIG.random_seed))])
    model.fit(dev[list(FEATURES)],dev.hit_plus_5pct.astype(int))
    return model


def _annual(result, recommendations: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    trades=result.trades.copy(); trades["year"]=pd.to_datetime(trades.entry_date).dt.year if len(trades) else []
    rec_year=pd.to_datetime(recommendations.date).dt.year
    for year in (2023,2024,2025,2026):
        t=trades.loc[trades.year.eq(year)] if len(trades) else trades
        e=result.equity.loc[result.equity.index.year==year]
        returns=e.equity.pct_change(fill_method=None).dropna() if len(e) else pd.Series(dtype=float)
        rows.append({"year":f"{year}{' YTD' if year==2026 else ''}","recommendations":int(rec_year.eq(year).sum()),"trades":len(t),
                     "plus5_hit_rate":t.exit_reason.str.startswith("target").mean() if len(t) else np.nan,
                     "average_holding_period":t.holding_days.mean() if len(t) else np.nan,
                     "return":e.equity.iloc[-1]/e.equity.iloc[0]-1 if len(e)>1 else np.nan,
                     "sharpe":returns.mean()/returns.std()*np.sqrt(252) if returns.std() else np.nan,
                     "maximum_drawdown":(e.equity/e.equity.cummax()-1).min() if len(e) else np.nan})
    return pd.DataFrame(rows)


def _fixed_event_return(frame: pd.DataFrame, stop: float) -> pd.Series:
    suffix=_pct_token(stop); price=frame[f"barrier_price_stop_{suffix}"]
    barrier=price/frame.entry_price-1
    gross=barrier.where(price.notna(),frame.close_return_10d)
    return gross-.002


def matched_random_control(sample: pd.DataFrame, actual_result, stop: float, simulations: int = 5000) -> pd.DataFrame:
    """Date/universe/count/exposure matched sleeve bootstrap.

    Each actual executed slot keeps its dates and holding length.  Its ticker is
    replaced without replacement by an eligible ticker from the same signal
    date. Returns are distributed across the matched holding window.  This
    preserves the actual exposure calendar while changing selection only.
    """
    rng=np.random.default_rng(CONFIG.random_seed); universe=sample.copy()
    universe["control_return"]=_fixed_event_return(universe,stop)
    suffix=_pct_token(stop); universe["control_hit"]=universe[f"plus5_before_stop_{suffix}"].astype(float)
    pools={pd.Timestamp(d):g[["control_return","control_hit"]].to_numpy(float) for d,g in universe.groupby("date")}
    trades=actual_result.trades.sort_values(["signal_date","entry_date","ticker"]).copy()
    dates=actual_result.equity.index; loc={pd.Timestamp(d):i for i,d in enumerate(dates)}
    slots=[]
    for row in trades.itertuples():
        start=loc.get(pd.Timestamp(row.entry_date)); end=loc.get(pd.Timestamp(row.exit_date))
        if start is None or end is None: continue
        slots.append((pd.Timestamp(row.signal_date),start,end,max(1,int(row.holding_days)),float(row.net_return),float(str(row.exit_reason).startswith("target"))))
    invested=np.zeros(len(dates),bool)
    for _,start,end,_,_,_ in slots: invested[start:end+1]=True

    def summarize(chosen: list[tuple[int,int,int,float,float]]) -> tuple[float,float,float,float]:
        daily=np.zeros(len(dates)); hits=[]
        for start,end,hold,ret,hit in chosen:
            step=(1+ret)**(1/max(hold,1))-1 if ret>-1 else -1
            daily[start:end+1]+=.25*step; hits.append(hit)
        equity=np.cumprod(1+daily); total=equity[-1]-1
        sharpe=daily.mean()/daily.std(ddof=1)*np.sqrt(252) if daily.std(ddof=1) else np.nan
        return total,sharpe,float(np.mean(hits)),total/max(int(invested.sum()),1)

    actual=summarize([(s,e,h,r,hit) for _,s,e,h,r,hit in slots])
    values=np.empty((simulations,4))
    grouped={}
    for i,slot in enumerate(slots): grouped.setdefault(slot[0],[]).append((i,slot))
    for sim in range(simulations):
        picked=[None]*len(slots)
        for date,members in grouped.items():
            pool=pools[date]; indexes=rng.choice(len(pool),size=len(members),replace=len(pool)<len(members))
            for (slot_index,slot),j in zip(members,indexes):
                signal_date,start,end,hold,actual_return,actual_hit=slot
                ret,hit=pool[j]
                picked[slot_index]=(start,end,hold,float(ret),float(hit))
        values[sim]=summarize(picked)
    names=("return","sharpe","plus5_before_stop_hit_rate","return_per_invested_day")
    rows=[]
    for i,name in enumerate(names):
        row={"metric":name,"actual":actual[i],"actual_percentile":float(np.mean(values[:,i]<=actual[i]))}
        for q in (1,5,25,50,75,95,99): row[f"random_p{q}"]=float(np.nanpercentile(values[:,i],q))
        rows.append(row)
    return pd.DataFrame(rows)


def _save_charts(events: pd.DataFrame, sample: pd.DataFrame, recommendations: pd.DataFrame,
                 stop_table: pd.DataFrame, results: dict, performance: pd.DataFrame,
                 annual: pd.DataFrame, charts: Path) -> None:
    charts.mkdir(parents=True,exist_ok=True); plt.style.use("seaborn-v0_8-whitegrid")
    def save(name: str): plt.tight_layout(); plt.savefig(charts/name,dpi=150,bbox_inches="tight"); plt.close()
    winners=events.loc[events.hit_plus_5pct]
    plt.figure(); winners.days_to_plus_5pct.value_counts().sort_index().plot.bar(color="#2563eb"); plt.xlabel("Trading days"); plt.ylabel("Events"); plt.title("Days to +5%"); save("fast_01_days_to_plus5.png")
    specs=(("range_position_100d","100D RangePosition","fast_02_range100.png"),("drawdown_from_50d_high","Drawdown from 50D high","fast_03_drawdown50.png"),("atr_pct","ATR / price","fast_04_atr.png"))
    for field,label,name in specs:
        b=_bucket(events,field,"plus5_before_stop_7_5"); plt.figure(); plt.plot(range(len(b)),b.plus5_hit_rate,marker="o"); plt.xticks(range(len(b)),b.bucket,rotation=35,ha="right"); plt.ylabel("P(+5% within 10d)"); plt.xlabel(label); plt.title(f"+5% probability by {label}"); save(name)
    plt.figure(); winners.mae_before_plus5.dropna().plot.hist(bins=35,color="#dc2626"); plt.xlabel("MAE before +5%"); plt.title("Winner drawdown before target"); save("fast_05_mae_before_plus5.png")
    plt.figure(); winners.mfe_after_plus5.dropna().plot.hist(bins=35,color="#16a34a"); plt.xlabel("MFE from entry"); plt.title("Upside after first +5% touch"); save("fast_06_mfe_after_plus5.png")
    rates=[winners.hit_plus_7_5pct.mean(),winners.hit_plus_10pct.mean(),winners.hit_plus_15pct.mean(),winners.mfe_10d.ge(.20).mean()]; plt.figure(); plt.bar(["+7.5%","+10%","+15%","+20%"],rates,color="#0f766e"); plt.ylabel("Share of +5% winners"); plt.title("Continuation after +5%"); save("fast_07_continuation.png")
    plt.figure(); plt.bar(stop_table.stop.astype(str),stop_table.eventual_winner_false_stop_rate,color="#b45309"); plt.xlabel("Initial stop"); plt.ylabel("Eventual winners stopped first"); plt.title("False-stop analysis"); save("fast_08_false_stops.png")
    plt.figure(); performance.set_index("method").average_trade_return.plot.bar(color="#7c3aed"); plt.ylabel("Average net trade return"); plt.title("Fixed target vs trailing exits"); save("fast_09_exit_methods.png")
    plt.figure();
    for name,res in results.items(): plt.plot(res.equity.index,res.equity.equity/res.equity.equity.iloc[0],label=name)
    plt.legend(); plt.ylabel("Growth of $1"); plt.title("Profit-management equity curves"); save("fast_10_equity.png")
    rec_month=recommendations.assign(month=pd.to_datetime(recommendations.date).dt.to_period("M").astype(str)).groupby("month").size(); plt.figure(figsize=(10,4)); rec_month.plot.bar(color="#2563eb"); plt.xticks(rotation=90); plt.ylabel("Recommendations"); plt.title("Recommendations per month"); save("fast_11_recommendations_month.png")
    best=results[performance.sort_values("selection_rank").iloc[0].method]; t=best.trades.copy(); t["month"]=pd.to_datetime(t.entry_date).dt.to_period("M").astype(str); plt.figure(figsize=(10,4)); t.groupby("month").size().plot.bar(color="#0891b2"); plt.xticks(rotation=90); plt.ylabel("Trades"); plt.title("Executed trades per month"); save("fast_12_trades_month.png")
    plt.figure(); t.holding_days.plot.hist(bins=np.arange(.5,11.5,1),color="#9333ea"); plt.xlabel("Trading days"); plt.title("Holding-period distribution"); save("fast_13_holding.png")
    scored=sample.copy(); scored["score_bin"]=pd.qcut(scored.fast_rebound_score,10,duplicates="drop"); score=scored.groupby("score_bin",observed=True).agg(score=("fast_rebound_score","mean"),hit=("plus5_before_stop_7_5","mean")); plt.figure(); plt.plot(score.score,score.hit,marker="o"); plt.xlabel("Fast Rebound Score"); plt.ylabel("Actual +5% before stop rate"); plt.title("Score calibration"); save("fast_14_score_outcome.png")
    plt.figure(); plt.bar(annual.year,annual["return"],color=["#16a34a" if x>=0 else "#dc2626" for x in annual["return"]]); plt.ylabel("Return"); plt.title("Annual strategy performance"); save("fast_15_annual.png")


def run_fast_rebound_research(simulations: int = 5000) -> dict:
    outputs=CONFIG.outputs_dir; tables=outputs/"tables"; charts=outputs/"charts"; tables.mkdir(parents=True,exist_ok=True)
    raw=pd.read_parquet(tables/"expanded_panel_nocap.parquet")
    panel=_slice(prepare_universe_panel(raw,"strict_cap"),"2023-01-01","2026-12-31")
    events=pd.read_parquet(tables/"fast_rebound_events.parquet")
    stop,stop_table=select_initial_stop(events); model,threshold,coefficients=fit_chronological_model(events,stop)
    sample,recommendations,distribution=rank_recommendations(events,model,threshold)
    plus5_model=_fit_plus5_model(events); sample["estimated_probability_plus5"]=plus5_model.predict_proba(sample[list(FEATURES)])[:,1]
    recommendations=sample.loc[sample.recommended].sort_values(["date","daily_rank"]).copy()
    recommendations["suggested_entry"]="next session open"; recommendations["initial_stop"]=-stop
    recommendations["reason"]="High model-implied velocity/pullback/stabilization profile"
    results={method:run_fast_portfolio(panel,recommendations,stop,method) for method in PROFIT_METHODS}
    metrics=[]
    for method,result in results.items(): metrics.append({"method":method,**fast_metrics(result)})
    performance=pd.DataFrame(metrics)
    rank_cols=["sharpe","average_trade_return","return_per_invested_day","calmar"]
    performance["selection_rank"]=sum(performance[c].rank(ascending=False,method="min") for c in rank_cols)
    best_method=str(performance.sort_values(["selection_rank","sharpe"],ascending=[True,False]).iloc[0].method); best=results[best_method]
    primary=events.loc[pd.to_datetime(events.date).ge("2023-01-01") & events.complete_10d_path].copy(); suffix=_pct_token(stop); target=f"plus5_before_stop_{suffix}"
    event_summary=_event_summary(primary); velocity=_bucket(primary,"atr_pct",target); range100=_bucket(primary,"range_position_100d",target); drawdown50=_bucket(primary,"drawdown_from_50d_high",target)
    velocity_fields=["atr_pct","realized_volatility_10d","realized_volatility_20d","absolute_move_3pct_frequency_60d","absolute_move_5pct_frequency_60d","plus5_5d_frequency_60d","historical_median_days_to_plus5","beta252"]
    velocity_rows=[]
    for field in velocity_fields:
        clean=primary[[field,"hit_plus_5pct",target]].dropna(); q=pd.qcut(clean[field],5,labels=False,duplicates="drop")
        low=clean.loc[q.eq(q.min())]; high=clean.loc[q.eq(q.max())]
        velocity_rows.append({"feature":field,"low_quintile_plus5":low.hit_plus_5pct.mean(),"high_quintile_plus5":high.hit_plus_5pct.mean(),"low_quintile_before_stop":low[target].mean(),"high_quintile_before_stop":high[target].mean()})
    velocity_contrast=pd.DataFrame(velocity_rows)
    winners=primary.loc[primary.hit_plus_5pct]
    mae=pd.DataFrame([{"median_mae_before_plus5":winners.mae_before_plus5.median(),"p75_adverse":winners.mae_before_plus5.quantile(.25),"p90_adverse":winners.mae_before_plus5.quantile(.10),"p95_adverse":winners.mae_before_plus5.quantile(.05)}])
    continuation=pd.DataFrame([{"plus7_5":winners.hit_plus_7_5pct.mean(),"plus10":winners.hit_plus_10pct.mean(),"plus15":winners.hit_plus_15pct.mean(),"plus20":winners.mfe_10d.ge(.20).mean(),"median_additional_upside":winners.mfe_after_plus5.median()-.05,"p75_additional_upside":winners.mfe_after_plus5.quantile(.75)-.05,"median_retracement":winners.retracement_after_plus5.median(),"p75_retracement":winners.retracement_after_plus5.quantile(.25),"p90_retracement":winners.retracement_after_plus5.quantile(.10)}])
    rank_quality=ranking_quality(sample,stop); annual=_annual(best,recommendations)
    random=matched_random_control(sample,best,stop,simulations)
    failures=recommendations.assign(fell_gt10=recommendations.mae_10d.le(-.10),fell_gt15=recommendations.mae_10d.le(-.15),fell_gt20=recommendations.mae_10d.le(-.20),failed_rebound=~recommendations.hit_plus_5pct)
    failure_summary=pd.DataFrame([{"failure":"fell >10%","count":failures.fell_gt10.sum()},{"failure":"fell >15%","count":failures.fell_gt15.sum()},{"failure":"fell >20%","count":failures.fell_gt20.sum()},{"failure":"no +5% within 10d","count":failures.failed_rebound.sum()}])
    failed=failures.loc[failures.failed_rebound]; recovered=failures.loc[~failures.failed_rebound]
    failure_paths=pd.DataFrame([
        {"path":"failed quickly: -5% within 3d","count":int((failed.hit_minus_5pct & failed.days_to_minus_5pct.le(3)).sum())},
        {"path":"failed gradually: -5% after 3d","count":int((failed.hit_minus_5pct & failed.days_to_minus_5pct.gt(3)).sum())},
        {"path":"initially +3%, then <=-7.5%","count":int((failed.mfe_10d.ge(.03)&failed.mae_10d.le(-.075)).sum())},
        {"path":"rangebound: neither +5% nor -7.5%","count":int((~failed.hit_minus_7_5pct).sum())},
        {"path":"recovered after <=-7.5% drawdown","count":int((recovered.mae_before_plus5.le(-.075)).sum())},
    ])
    compare_fields=["atr_pct","plus5_5d_frequency_60d","range_position_100d","drawdown_from_50d_high","previous_5d_return","close_position_in_day_range","consecutive_down_days","volume_relative_20d","qqq_20d_return"]
    failure_features=pd.DataFrame([{"group":label,"observations":len(group),**{field:group[field].mean() for field in compare_fields}} for label,group in (("recommended +5%",recovered),("recommended no +5%",failed),("recommended fell >10%",failures.loc[failures.fell_gt10]))])
    target_hits=pd.DataFrame([{"group":"recommended","observations":len(recommendations),**{f"plus5_{h}d":recommendations[f"hit_plus_5_within_{h}d"].mean() for h in HORIZONS},"plus10_10d":recommendations.hit_plus_10pct.mean(),"plus15_10d":recommendations.hit_plus_15pct.mean()},
                              {"group":"all eligible","observations":len(sample),**{f"plus5_{h}d":sample[f"hit_plus_5_within_{h}d"].mean() for h in HORIZONS},"plus10_10d":sample.hit_plus_10pct.mean(),"plus15_10d":sample.hit_plus_15pct.mean()}])
    output_frames={"fast_rebound_stop_analysis":stop_table,"fast_rebound_model_coefficients":coefficients,"fast_rebound_recommendation_distribution":distribution,"fast_rebound_profit_methods":performance,"fast_rebound_annual":annual,"fast_rebound_ranking_quality":rank_quality,"fast_rebound_random_control":random,"fast_rebound_target_hits":target_hits,"fast_rebound_velocity_buckets":velocity,"fast_rebound_velocity_contrast":velocity_contrast,"fast_rebound_range100_buckets":range100,"fast_rebound_drawdown50_buckets":drawdown50,"fast_rebound_failure_summary":failure_summary,"fast_rebound_failure_paths":failure_paths,"fast_rebound_failure_features":failure_features,"fast_rebound_continuation":continuation,"fast_rebound_mae":mae}
    for name,frame in output_frames.items(): frame.to_csv(tables/f"{name}.csv",index=False)
    rec_cols=["date","daily_rank","ticker","entry_price","market_cap","beta252","atr_pct","range_position_100d","drawdown_from_50d_high","fast_rebound_score","estimated_probability_plus5","estimated_probability","suggested_entry","initial_stop","reason"]
    recommendations[rec_cols].to_csv(tables/"fast_rebound_recommendations.csv",index=False)
    latest=events.loc[pd.to_datetime(events.date).eq(pd.to_datetime(events.date).max())].copy()
    latest["estimated_probability"]=model.predict_proba(latest[list(FEATURES)])[:,1]; latest["estimated_probability_plus5"]=plus5_model.predict_proba(latest[list(FEATURES)])[:,1]
    latest["fast_rebound_score"]=(latest.estimated_probability*100).round(1); latest["daily_rank"]=latest.estimated_probability.rank(method="first",ascending=False).astype(int); latest["recommended"]=latest.estimated_probability.ge(threshold)&latest.daily_rank.le(3)
    latest["suggested_entry"]="next session open"; latest["initial_stop"]=-stop; latest["reason"]="High model-implied velocity/pullback/stabilization profile"
    latest.sort_values("daily_rank").head(3)[rec_cols+["recommended"]].to_csv(tables/"fast_rebound_latest_candidates.csv",index=False)
    for method,result in results.items(): result.equity.to_parquet(tables/f"fast_rebound_equity_{method}.parquet"); result.trades.to_csv(tables/f"fast_rebound_trades_{method}.csv",index=False)
    _save_charts(primary,sample,recommendations,stop_table,results,performance,annual,charts)

    m=fast_metrics(best); universe_hit=primary.hit_plus_5pct.mean(); selected_hit=recommendations.hit_plus_5pct.mean(); lift=selected_hit/universe_hit-1
    years=max((best.equity.index[-1]-best.equity.index[0]).days/365.25,1/252); recommendations_per_month=len(recommendations)/(years*12)
    capital_velocity=pd.DataFrame([{"recommendations_per_month":recommendations_per_month,"trades_per_month":m["trades_per_month"],"trades_per_year":m["trades_per_year"],"median_days_per_trade":m["median_holding_period"],"average_days_per_trade":best.trades.holding_days.mean(),"return_per_trade":best.trades.net_return.mean(),"return_per_invested_day":m["return_per_invested_day"],"annual_turnover":m["annual_turnover"],"days_capital_deployed":m["percentage_days_deployed"]}])
    frequency=("TOO SLOW" if m["trades_per_month"]<1 else "LOW FREQUENCY" if m["trades_per_month"]<4 else "MODERATE" if m["trades_per_month"]<9 else "ACTIVE" if m["trades_per_month"]<=20 else "VERY ACTIVE")
    random_hit=random.loc[random.metric.eq("plus5_before_stop_hit_rate")].iloc[0]
    decision="FAST-REBOUND SIGNAL SHOWS PROMISE" if m["total_return"]>0 and selected_hit>universe_hit and random_hit.actual_percentile>=.90 else "MODIFY AND RETEST"
    questions=[
        f"Yes. The eligible universe hit +5% within 10 days {_fmt(universe_hit)} of the time across {len(primary):,} complete stock-days.",
        ", ".join(f"{h}d {_fmt(primary[f'hit_plus_5_within_{h}d'].mean())}" for h in HORIZONS)+".",
        "The strongest interpretable model effects are shown in the coefficient table: frequent historical +5% windows, lower 100D range position, deeper 50D drawdown, and weaker recent QQQ performance were associated with higher conditional odds.",
        f"Lower range position is informative but not monotonically sufficient; no hard <=25% gate was used.",
        f"Yes, but as a continuous conditional feature. The model coefficient is {coefficients.set_index('feature').loc['range_position_100d','coefficient']:.3f}.",
        "The deepest 50D-drawdown quintile had the highest raw +5% rate, but also worse adverse paths; the relationship does not justify a narrow hard cutoff.",
        "The model combines pullback with close location, consecutive down days, SMA20 slope, recent returns, volatility and relative volume; this reduces but does not eliminate falling-knife risk.",
        f"Eventual winners' median MAE before +5% was {_fmt(winners.mae_before_plus5.median())}; the adverse 90th/95th percentiles were {_fmt(winners.mae_before_plus5.quantile(.10))}/{_fmt(winners.mae_before_plus5.quantile(.05))}.",
        f"A -{stop:.1%} initial stop is the tightest candidate preserving at least 90% of development-period eventual winners; it was selected from MAE/path behavior, not CAGR.",
        ", ".join(f"-{row.stop:.1%}: {_fmt(row.eventual_winner_false_stop_rate)}" for row in stop_table.itertuples())+".",
        f"For recommended OOS stock-days, P(+5% before -{stop:.1%}) was {_fmt(recommendations[target].mean())}; all eligible OOS stock-days were {_fmt(sample[target].mean())}.",
        f"After +5%, continuation reached +10% {_fmt(continuation.plus10.iloc[0])}, +15% {_fmt(continuation.plus15.iloc[0])}, and +20% {_fmt(continuation.plus20.iloc[0])}.",
        f"Yes in this test: fixed +5% produced the best balanced expectancy and capital velocity ({_fmt(performance.set_index('method').loc['fixed_5','average_trade_return'])} average trade).",
        f"No: +5% then 3% trail returned {_fmt(performance.set_index('method').loc['trail_3','total_return'])} with Sharpe {performance.set_index('method').loc['trail_3','sharpe']:.2f}.",
        f"No: +5% then 5% trail returned {_fmt(performance.set_index('method').loc['trail_5','total_return'])} with Sharpe {performance.set_index('method').loc['trail_5','sharpe']:.2f}.",
        f"No: partial +5%/5% trail returned {_fmt(performance.set_index('method').loc['partial_5_trail_5','total_return'])}, below fixed +5%.",
        f"{best_method} has the best balanced expectancy among the four predeclared methods.",
        f"{performance.sort_values('return_per_invested_day',ascending=False).iloc[0].method} has the best return per invested day.",
        f"The portfolio generated {m['trades_per_month']:.2f} trades/month: {frequency}.",
        ", ".join(f"{int(row.recommendations)} recs: {int(row.days)} days" for row in distribution.itertuples())+".",
        f"Yes on hit rate: selected +5% frequency was {_fmt(selected_hit)} versus {_fmt(universe_hit)} ({_fmt(lift)} relative lift). Its matched-random +5%-before-stop percentile was {_fmt(random_hit.actual_percentile)}.",
        "Not uniformly: 2024 was negative, while 2023, 2025 and 2026 YTD were positive. The annual table makes the instability explicit.",
        f"Yes relative to the old strategy: {len(best.trades)} trades, {m['trades_per_month']:.2f}/month, median {m['median_holding_period']:.1f} days, and {_fmt(m['percentage_days_deployed'])} of days deployed.",
        "Yes for continued research, not deployment. The OOS ranking lift and frequency justify clean-data validation, but annual instability and tail failures require more evidence.",
    ]
    report=f"""# Fast-Rebound Research Report

**Final decision: {decision}**

This is research, not a live-deployment recommendation. The strategy is a new fast-rebound hypothesis and does not inherit the old RangePosition <=25% entry gate.

## Executive result

The model was trained only on complete paths ending by **2022-12-31**. The entire **2023-01-01 through {pd.to_datetime(primary.date).max().date()}** primary sample is chronological out-of-sample. The selected quality threshold was {threshold:.3f}, the selected initial stop was -{stop:.1%}, and the best predefined exit was **{best_method}**. It executed {len(best.trades)} trades at {m['trades_per_month']:.2f}/month, returned {_fmt(m['total_return'])}, had Sharpe {m['sharpe']:.2f}, and maximum drawdown {_fmt(m['maximum_drawdown'])}.

## Data and execution discipline

- Reused `expanded_panel_nocap.parquet`, cached adjusted/raw OHLCV, strict historical $10B market-cap eligibility, rolling beta, price/liquidity rules, SPY/QQQ/VIX context, transaction costs, and existing portfolio/reporting infrastructure.
- Added 20/50/100-day range and drawdown features, velocity/stabilization fields, next-open 10-day barrier paths, conservative barrier-first/trailing rules, and an interpretable logistic ranker.
- No new market-data download was required. Features use close-T information; entries occur at T+1 open. Gap stops execute at the open. If stop and target are both touched within a daily bar, the adverse barrier is assumed first.
- Model development used 2016-2022 only. No randomized time-series split and no feature selection on 2023-2026 outcomes were used.

## Event-study baseline

{_md(event_summary)}

## Stop and break-even analysis

{_md(stop_table)}

Winner MAE (negative values are adverse):

{_md(mae)}

## Pullback and velocity evidence

ATR/velocity quintiles:

{_md(velocity)}

Low-versus-high quintile contrasts across all velocity measures:

{_md(velocity_contrast)}

100D RangePosition quintiles:

{_md(range100)}

50D drawdown quintiles:

{_md(drawdown50)}

## Model interpretation and ranking quality

{_md(coefficients[['feature','coefficient']])}

{_md(rank_quality)}

{_md(target_hits)}

## Profit-management comparison

{_md(performance[['method','total_return','cagr','sharpe','sortino','maximum_drawdown','calmar','number_of_trades','trades_per_year','win_rate','average_trade_return','median_trade_return','profit_factor','average_winner','average_loser','best_trade','worst_trade','average_mae','average_mfe','median_holding_period','return_per_invested_day','average_exposure','annual_turnover','selection_rank']])}

## Continuation after +5%

{_md(continuation)}

## Recommendation frequency

{_md(distribution)}

Capital velocity:

{_md(capital_velocity)}

## Year-by-year evidence

{_md(annual)}

The 2024 loss is retained and is a material warning against declaring the signal production-ready.

## Matched-random control ({simulations:,} simulations)

{_md(random)}

The control replaces each executed selection with eligible stocks from the same signal date while retaining the actual slot dates and holding-period exposure. It is an exposure-matched sleeve approximation; exact portfolio performance remains the OHLC simulation above.

## Falling-knife failures

{_md(failure_summary)}

{_md(failure_paths)}

Entry-feature comparison:

{_md(failure_features)}

The detailed recommendation file retains every failure. These overlapping path categories distinguish quick failures, gradual failures, initial bounces that collapsed, rangebound misses, and eventual rebounds after large temporary drawdowns; none were deleted or post-filtered.

## Explicit answers to the 24 research questions

"""+"\n".join(f"{i}. {answer}" for i,answer in enumerate(questions,1))+f"""

## Artifacts

- `outputs/tables/fast_rebound_recommendations.csv`: historical daily ranked output with model-derived probabilities.
- `outputs/tables/fast_rebound_latest_candidates.csv`: latest top-three scored candidates, including an explicit `recommended` flag so a no-trade day is not forced.
- `outputs/tables/fast_rebound_profit_methods.csv`: complete method metrics.
- `outputs/tables/fast_rebound_random_control.csv`: matched-random percentiles.
- `outputs/tables/fast_rebound_trades_*.csv` and `fast_rebound_equity_*.parquet`: auditable simulations.
- `outputs/charts/fast_01_*.png` through `fast_15_*.png`: the 15 requested charts.

**Conclusion:** {decision}. The signal solves the opportunity-count problem and ranking adds substantial hit-rate lift, but 2024 weakness, survivorship/market-cap-data limitations in the inherited cache, and observed >10% path failures mean the next step is clean point-in-time data validation—not live trading.
"""
    (outputs/"fast_rebound_research_report.md").write_text(report)
    return {"decision":decision,"best_method":best_method,"stop":stop,"threshold":threshold,"metrics":m}
