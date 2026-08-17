"""Run frozen-signal Fast Rebound capital-allocation research."""

import argparse

from src.capital_allocation_research import run_capital_allocation_research


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--random-simulations",type=int,default=5000)
    parser.add_argument("--bootstrap-simulations",type=int,default=5000)
    args=parser.parse_args()
    result=run_capital_allocation_research(args.random_simulations,args.bootstrap_simulations)
    print(f"Best full-deployment architecture: {result['best_full']}")
    print(f"Decision: {result['decision']}")
    print("Wrote outputs/fast_rebound_capital_allocation_report.md")
