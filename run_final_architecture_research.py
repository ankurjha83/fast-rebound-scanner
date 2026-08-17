"""Run the final, frozen portfolio-architecture experiment."""

import argparse

from src.final_architecture_research import run_final_architecture_research


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--bootstrap-simulations", type=int, default=5000)
    args = parser.parse_args()
    result = run_final_architecture_research(args.simulations, args.bootstrap_simulations)
    print(f"Decision: {result['decision']}")
    print(f"Frozen architecture: {result['frozen']}")
    print("Wrote outputs/final_architecture_report.md")
