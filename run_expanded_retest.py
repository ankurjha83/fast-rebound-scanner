"""Run expanded point-in-time historical universe inference and reporting."""

import argparse

from src.expanded_retest import run_expanded_retest


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--simulations",type=int,default=1000)
    args=parser.parse_args()
    result=run_expanded_retest(args.simulations)
    print(f"Decision: {result['decision']}")
    print("Wrote outputs/expanded_universe_retest_report.md")
