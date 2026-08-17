"""Run the frozen Fast Rebound theme-concentration diagnostic."""

import argparse

from src.theme_concentration_diagnostic import run_theme_diagnostic


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--random-simulations",type=int,default=5000)
    args=parser.parse_args()
    result=run_theme_diagnostic(args.random_simulations)
    print(f"Decision: {result['decision']}")
    print(f"Audited maximum same-theme exposure: {result['audited_max_theme_exposure']:.2%}")
    print("Wrote outputs/fast_rebound_theme_diagnostic_report.md")
