"""Run the frozen-strategy 2024 forensic diagnosis."""

import argparse

from src.fast_rebound_2024_diagnosis import run_fast_rebound_2024_diagnosis


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--simulations",type=int,default=20000)
    args=parser.parse_args()
    result=run_fast_rebound_2024_diagnosis(args.simulations)
    print(f"Primary explanation: {result['primary_explanation']}")
    print(f"Decision: {result['decision']}")
    print("Wrote outputs/fast_rebound_2024_diagnosis.md")
