"""Run the fast-rebound event-study and portfolio report."""

import argparse

from src.fast_rebound_report import run_fast_rebound_research


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--simulations",type=int,default=5000)
    args=parser.parse_args()
    result=run_fast_rebound_research(args.simulations)
    print(f"Decision: {result['decision']}")
    print(f"Selected stop: -{result['stop']:.1%}")
    print(f"Selected profit method: {result['best_method']}")
    print("Wrote outputs/fast_rebound_research_report.md")
