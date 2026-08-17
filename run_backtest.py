"""Run the complete research pipeline."""

import argparse

from data.provider import CacheMode
from src.research import run_research

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-mode", choices=[m.value for m in CacheMode], default="refresh_recent")
    parser.add_argument("--random-simulations", type=int, default=1_000)
    parser.add_argument("--skip-robustness", action="store_true")
    args = parser.parse_args()
    run_research(CacheMode(args.cache_mode), random_simulations=args.random_simulations, run_robustness=not args.skip_robustness)
    print("Research outputs written to outputs/.")


if __name__ == "__main__":
    main()
