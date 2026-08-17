import pandas as pd

from src.signals import (
    ConfirmationVariant,
    EntryStrategy,
    generate_confirmation_signals,
    generate_entry_signals,
    sma_cross_above,
)


def sample_frame():
    return pd.DataFrame(
        {
            "eligible": [True, True, True, False],
            "range_position": [0.1, 0.2, 0.3, 0.1],
            "adj_close": [90.0, 101.0, 100.0, 100.0],
            "sma_range": [100.0, 100.0, 100.0, 100.0],
            "distance_sma": [-0.10, 0.01, 0.0, 0.0],
        }
    )


def test_three_entry_strategies():
    frame = sample_frame()
    assert generate_entry_signals(frame, EntryStrategy.PURE).tolist() == [True, True, False, False]
    assert generate_entry_signals(frame, EntryStrategy.ABOVE_SMA).tolist() == [False, True, False, False]
    assert generate_entry_signals(frame, EntryStrategy.NEAR_SMA).tolist() == [False, True, False, False]


def confirmation_frame():
    dates = pd.date_range("2024-01-01", periods=4)
    index = pd.MultiIndex.from_product([dates, ["TEST"]], names=["date", "ticker"])
    return pd.DataFrame({
        "eligible": True,
        "range_position": [0.2, 0.2, 0.2, 0.2],
        "adj_close": [90.0, 99.0, 101.0, 102.0],
        "sma_range": [100.0, 100.0, 100.0, 100.0],
        "sma20": [95.0, 100.0, 100.0, 101.0],
        "previous_5d_return": [-.1, -.02, .01, .03],
    }, index=index)


def test_strict_sma20_cross_detection():
    frame = confirmation_frame()
    cross = sma_cross_above(frame["adj_close"], frame["sma20"])
    assert cross.tolist() == [False, False, True, False]


def test_confirmation_variants():
    frame = confirmation_frame()
    assert generate_confirmation_signals(frame, ConfirmationVariant.SMA100_TREND).tolist() == [False, False, True, True]
    assert generate_confirmation_signals(frame, ConfirmationVariant.SMA20_RECOVERY).tolist() == [False, False, True, False]
    assert generate_confirmation_signals(frame, ConfirmationVariant.POSITIVE_5D).tolist() == [False, False, True, True]
    assert generate_confirmation_signals(frame, ConfirmationVariant.COMBINED).tolist() == [False, False, True, True]
