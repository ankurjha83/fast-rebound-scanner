"""Run the continuation-stage regime diagnosis from cached research data."""

from src.regime_diagnosis import run_regime_diagnosis


if __name__ == "__main__":
    result = run_regime_diagnosis()
    print(
        f"Best confirmation: {result['best_variant']} | "
        f"material improvement: {result['materially_better']} | "
        f"decision: {result['decision']}"
    )
    print("Wrote outputs/regime_diagnosis_report.md")
