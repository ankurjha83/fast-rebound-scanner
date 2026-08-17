"""Single auditable configuration for the frozen Fast Rebound v1 model.

The numeric preprocessing and logistic-regression parameters were exported
from the research fit that produced ``fast_rebound_model_coefficients.csv``.
Production code performs inference only; it never imports a training routine.
"""

from __future__ import annotations

from dataclasses import dataclass


MODEL_VERSION = "fast-rebound-v1-frozen"
MAX_POSITIONS = 3
POSITION_SIZE = 1 / 3
TAKE_PROFIT = 0.05
STOP_LOSS = -0.075
MAX_HOLDING_DAYS = 10
COMMISSION_RATE = 0.0005
SLIPPAGE_RATE = 0.0005
INITIAL_EQUITY = 100_000.0

MIN_BETA = 2.0
MIN_MARKET_CAP = 10_000_000_000.0
MIN_PRICE = 10.0
MIN_AVERAGE_DOLLAR_VOLUME = 100_000_000.0
MIN_HISTORY_DAYS = 252
RECOMMENDATION_THRESHOLD = 0.636

FEATURES = (
    "atr_pct", "realized_volatility_10d", "absolute_move_3pct_frequency_60d",
    "plus5_5d_frequency_60d", "range_position_100d", "drawdown_from_50d_high",
    "distance_sma20", "previous_5d_return", "close_position_in_day_range",
    "consecutive_down_days", "sma20_slope", "volume_relative_20d", "qqq_20d_return",
)

IMPUTER_STATISTICS = (
    0.03713504270997342, 0.4016833166928841, 0.21666666666666667,
    0.4166666666666667, 0.7406869951251271, -0.06567915989149542,
    0.012868982747339386, 0.007190861482043398, 0.5234229520321358,
    0.0, 0.0065805215783580895, 0.8967954480287172, 0.023066643131483766,
)
SCALER_MEAN = (
    0.04050008532928587, 0.4785593967756145, 0.252684615400883,
    0.4010742239648361, 0.6524283737952169, -0.09648812446902066,
    0.012786804251954319, 0.00832494280631621, 0.515639125791054,
    0.8766094420600858, 0.0063220645986931745, 0.9941877316670493,
    0.015917074321289228,
)
SCALER_SCALE = (
    0.01817093692559997, 0.6729964657636329, 0.1689823521465812,
    0.16941663799320206, 0.3009615018254363, 0.10195162246269031,
    0.07095855608238089, 0.06852478201282584, 0.30334009505198506,
    1.2129531965028806, 0.03107118549792094, 0.47447681686570947,
    0.04785524918664619,
)
COEFFICIENTS = (
    -0.02529610599297697, 0.040319642154837874, -0.22294438311868345,
    0.3778158823980935, -0.1732306329241048, -0.1398684542203175,
    0.17229117055214904, -0.10785388152909353, 0.025899015992502484,
    0.039430793303621876, -0.009424608605148693, -0.0321087794394855,
    -0.15798345164144081,
)
INTERCEPT = -0.09404226580251127


@dataclass(frozen=True)
class FrozenStrategy:
    model_version: str = MODEL_VERSION
    max_positions: int = MAX_POSITIONS
    position_size: float = POSITION_SIZE
    take_profit: float = TAKE_PROFIT
    stop_loss: float = STOP_LOSS
    max_holding_days: int = MAX_HOLDING_DAYS
    recommendation_threshold: float = RECOMMENDATION_THRESHOLD
    min_beta: float = MIN_BETA
    min_market_cap: float = MIN_MARKET_CAP
    min_price: float = MIN_PRICE
    min_average_dollar_volume: float = MIN_AVERAGE_DOLLAR_VOLUME


FROZEN = FrozenStrategy()


def assert_frozen_integrity() -> None:
    lengths={len(FEATURES),len(IMPUTER_STATISTICS),len(SCALER_MEAN),len(SCALER_SCALE),len(COEFFICIENTS)}
    if lengths != {13}:
        raise RuntimeError("Frozen model vectors are inconsistent")
    if (MAX_POSITIONS,POSITION_SIZE,TAKE_PROFIT,STOP_LOSS,MAX_HOLDING_DAYS)!=(3,1/3,.05,-.075,10):
        raise RuntimeError("Frozen trading configuration changed")
