"""
HoopMind - Usability / SUS scoring.

Reads evaluation/usability_responses.csv with columns:

    respondent,sus1,...,sus10,sat_overall,sat_accuracy,sat_quality,
    sat_speed,sat_paraphrase,sat_recommend

All rating cells are integers 1-5.

Usage:
    python score_usability.py [path-to-csv]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = EVAL_DIR / "usability_responses.csv"

SUS_ITEMS = [f"sus{i}" for i in range(1, 11)]
SAT_ITEMS = [
    "sat_overall",
    "sat_accuracy",
    "sat_quality",
    "sat_speed",
    "sat_paraphrase",
    "sat_recommend",
]


def sus_score(row: dict[str, str]) -> float:
    """Standard SUS: odd items (x-1), even items (5-x), sum * 2.5."""

    total = 0.0

    for i, item in enumerate(SUS_ITEMS, start=1):

        value = int(float(row[item]))

        if i % 2 == 1:
            total += value - 1
        else:
            total += 5 - value

    return total * 2.5


def band(score: float) -> str:

    if score >= 80.3:
        return "Excellent"
    if score >= 68:
        return "Good"
    if score >= 51:
        return "OK / Marginal"
    return "Poor"


def main() -> None:

    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    if not csv_path.exists():
        print(f"No response file found at {csv_path}.")
        print(
            "Copy usability_responses_template.csv to "
            "usability_responses.csv and fill in one row per respondent."
        )
        return

    raw_rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    required = SUS_ITEMS + SAT_ITEMS

    valid = []
    skipped = 0

    for r in raw_rows:
        if all(
            str(r.get(col, '')).strip()
            for col in required
        ):
            valid.append(r)
        else:
            skipped += 1

    if skipped:
        print(f"Skipped {skipped} incomplete response(s).")

    rows = valid

    if not rows:
        print("No complete responses found.")
        return

    sus_values = [sus_score(r) for r in rows]
    avg_sus = sum(sus_values) / len(sus_values)

    sat_means = {
        item: sum(int(float(r[item])) for r in rows) / len(rows)
        for item in SAT_ITEMS
    }
    overall_sat = sum(sat_means.values()) / len(sat_means)

    print("=" * 60)
    print("HOOPMIND USABILITY RESULTS")
    print("=" * 60)
    print(f"Respondents          : {len(rows)}")

    print("\nIndividual SUS scores:")
    for r, s in zip(rows, sus_values):
        print(f"  {r['respondent']:<15} {s:>6.1f}  ({band(s)})")

    print(f"\nAverage SUS score    : {avg_sus:.1f} / 100  -> {band(avg_sus)}")
    print("\nSatisfaction ratings (mean of 1-5):")

    labels = {
        "sat_overall": "Overall satisfaction   ",
        "sat_accuracy": "Answer accuracy        ",
        "sat_quality": "Response quality       ",
        "sat_speed": "Response speed         ",
        "sat_paraphrase": "Paraphrase handling    ",
        "sat_recommend": "Recommendation intent  ",
    }

    for item in SAT_ITEMS:
        print(f"  {labels[item]} : {sat_means[item]:.2f}")

    print(f"\nOverall satisfaction mean: {overall_sat:.2f} / 5")


if __name__ == "__main__":
    main()
