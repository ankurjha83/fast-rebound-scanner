"""Record an explicit human TRADE/SKIP decision; never changes model state."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.production.human_ledger import record_decision


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--run-id",required=True); parser.add_argument("--recommendation-date",required=True); parser.add_argument("--ticker",required=True); parser.add_argument("--decision",required=True,choices=["TRADE","SKIP"]); parser.add_argument("--reason",default=""); parser.add_argument("--intended-allocation",type=float); parser.add_argument("--order-type",default=""); parser.add_argument("--actual-entry-price",type=float); parser.add_argument("--actual-exit-price",type=float); parser.add_argument("--broker-notes",default=""); args=parser.parse_args()
    row=record_decision(Path(__file__).resolve().parent/"state"/"human_decisions.csv",**vars(args)); print(f"Recorded {row['decision']} for {row['ticker']}; model portfolio unchanged.")

