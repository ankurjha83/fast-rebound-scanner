"""Run portfolio-level risk-management research."""
import argparse
from src.portfolio_risk_research import run_portfolio_risk_research

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--simulations",type=int,default=1000); args=parser.parse_args()
    result=run_portfolio_risk_research(args.simulations)
    print(f"Decision: {result['decision']}"); print(f"Best risk variant: {result['best_variant']}"); print(f"Combined controls: {', '.join(result['components']) or 'none'}"); print("Wrote outputs/portfolio_risk_research_report.md")
