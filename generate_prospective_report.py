from pathlib import Path

from src.production.reporting import generate_report


if __name__=="__main__":
    root=Path(__file__).resolve().parent; metrics=generate_report(root/"state"/"prospective_ledger.csv",root/"outputs"/"prospective"/"fast_rebound_prospective_report.md",root/"state"/"prospective_equity.csv"); print(metrics)
