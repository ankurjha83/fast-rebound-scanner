"""Run the frozen-entry exit-management research."""

import argparse

from src.exit_research import run_exit_research


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--simulations",type=int,default=1000)
    parser.add_argument("--reuse-random",action="store_true")
    args=parser.parse_args()
    result=run_exit_research(args.simulations,args.reuse_random)
    print(f"Decision: {result['decision']}")
    print(f"Candidates: {', '.join(result['candidates'])}")
    print("Wrote outputs/exit_strategy_research_report.md")
