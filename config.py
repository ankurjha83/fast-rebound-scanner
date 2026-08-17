"""Central configuration for the high-beta mean-reversion research."""

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ResearchConfig:
    tickers: tuple[str, ...] = (
        "IONQ", "ASTS", "RKLB", "COIN", "HOOD", "CVNA", "MSTR", "APP"
    )
    benchmarks: tuple[str, ...] = ("SPY", "QQQ")
    start_date: str = "2016-01-01"
    development_end: str = "2022-12-31"
    out_of_sample_start: str = "2023-01-01"
    beta_lookback: int = 252
    min_beta: float = 2.0
    range_lookback: int = 100
    max_range_position: float = 0.25
    min_market_cap: float = 10_000_000_000.0
    min_price: float = 10.0
    min_average_dollar_volume: float = 100_000_000.0
    initial_capital: float = 100_000.0
    max_positions: int = 10
    position_fraction: float = 0.10
    commission_rate: float = 0.0005
    slippage_rate: float = 0.0005
    random_seed: int = 20260816
    random_simulations: int = 1_000
    cache_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "cache")
    outputs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "outputs")


CONFIG = ResearchConfig()

