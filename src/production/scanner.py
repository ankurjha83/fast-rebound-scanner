"""Close-T feature construction and inference for the frozen model."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.indicators import consecutive_down_days
from src.production.frozen_config import (
    COEFFICIENTS, FEATURES, IMPUTER_STATISTICS, INTERCEPT, MAX_POSITIONS,
    RECOMMENDATION_THRESHOLD, SCALER_MEAN, SCALER_SCALE,
)


def frozen_probabilities(features: pd.DataFrame) -> np.ndarray:
    matrix=features.loc[:,FEATURES].to_numpy(dtype=float)
    medians=np.asarray(IMPUTER_STATISTICS); matrix=np.where(np.isfinite(matrix),matrix,medians)
    standardized=(matrix-np.asarray(SCALER_MEAN))/np.asarray(SCALER_SCALE)
    logits=INTERCEPT+standardized@np.asarray(COEFFICIENTS)
    return 1/(1+np.exp(-np.clip(logits,-700,700)))


def build_signal_features(panel: pd.DataFrame, session: str | pd.Timestamp) -> pd.DataFrame:
    """Recreate the research close-T fields without constructing a future path."""
    session=pd.Timestamp(session).normalize(); qqq=panel.xs("QQQ",level="ticker").adj_close.sort_index()
    qqq20=qqq.pct_change(20,fill_method=None).get(session,np.nan); rows=[]
    for ticker,group in panel.groupby(level="ticker",sort=False):
        if ticker in ("SPY","QQQ","^VIX"): continue
        frame=group.droplevel("ticker").sort_index();
        if session not in frame.index: continue
        close,high,low,open_,volume=(frame[c] for c in ("adj_close","adj_high","adj_low","adj_open","volume")); ret=close.pct_change(fill_method=None)
        previous=close.shift(1); tr=pd.concat([high-low,(high-previous).abs(),(low-previous).abs()],axis=1).max(axis=1)
        low100,high100=close.rolling(100).min(),close.rolling(100).max(); high50=close.rolling(50).max(); sma20=close.rolling(20).mean()
        intraday=(close-low)/(high-low).replace(0,np.nan); five_gain=high.rolling(5).max()/close.shift(5)-1; row=frame.loc[session]
        def existing_or(value,field): return row.get(field,value) if pd.notna(row.get(field,np.nan)) else value
        values={
            "atr_pct":(tr.rolling(14).mean()/close).get(session),
            "realized_volatility_10d":(ret.rolling(10).std()*np.sqrt(252)).get(session),
            "absolute_move_3pct_frequency_60d":ret.abs().ge(.03).rolling(60,min_periods=40).mean().get(session),
            "plus5_5d_frequency_60d":five_gain.ge(.05).rolling(60,min_periods=40).mean().get(session),
            "range_position_100d":((close-low100)/(high100-low100).replace(0,np.nan)).get(session),
            "drawdown_from_50d_high":(close/high50-1).get(session),
            "distance_sma20":existing_or((close/sma20-1).get(session),"distance_sma20"),
            "previous_5d_return":existing_or(close.pct_change(5,fill_method=None).get(session),"previous_5d_return"),
            "close_position_in_day_range":intraday.get(session),
            "consecutive_down_days":existing_or(consecutive_down_days(ret).get(session),"consecutive_down_days"),
            "sma20_slope":existing_or((sma20/sma20.shift(5)-1).get(session),"sma20_slope"),
            "volume_relative_20d":(volume/volume.rolling(20).mean()).get(session),
            "qqq_20d_return":qqq20,
        }
        rows.append({"date":session,"ticker":ticker,"previous_close":row.adj_close,"market_cap":row.get("market_cap",row.get("historical_market_cap",np.nan)),"beta252":row.get("beta252",np.nan),"average_dollar_volume":row.get("average_dollar_volume",np.nan),"eligible":bool(row.get("eligible",row.get("eligible_strict",False))),**values})
    return pd.DataFrame(rows)


def rank_recommendations(features: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    scored=features.loc[features.eligible].copy()
    if scored.empty:
        scored["estimated_probability"]=pd.Series(dtype=float); scored["fast_rebound_score"]=pd.Series(dtype=float); scored["daily_rank"]=pd.Series(dtype=int)
        return scored,scored.copy()
    scored["estimated_probability"]=frozen_probabilities(scored)
    scored["fast_rebound_score"]=(100*scored.estimated_probability).round(1)
    scored=scored.sort_values(["estimated_probability","ticker"],ascending=[False,True]).reset_index(drop=True)
    scored["daily_rank"]=np.arange(1,len(scored)+1)
    qualifying=scored.loc[scored.estimated_probability.ge(RECOMMENDATION_THRESHOLD)].head(MAX_POSITIONS).copy()
    return scored,qualifying
