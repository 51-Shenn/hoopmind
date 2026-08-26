"""Convert the repo-root test.csv (test_id,expected_intent,test_phrase) into a
Rasa NLU test file. Regenerate with:

    uv run python tests/csv_to_nlu.py
"""
import csv
import pathlib
from collections import OrderedDict

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "test.csv"
DEST = pathlib.Path(__file__).resolve().parent / "nlu_test.yml"

by_intent: "OrderedDict[str, list[str]]" = OrderedDict()
with SRC.open(encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh):
        intent = (row["expected_intent"] or "").strip()
        phrase = (row["test_phrase"] or "").strip()
        if intent and phrase:
            by_intent.setdefault(intent, []).append(phrase)

lines = ['version: "3.1"', "", "nlu:"]
for intent, phrases in by_intent.items():
    lines.append(f"- intent: {intent}")
    lines.append("  examples: |")
    lines.extend(f"    - {p}" for p in phrases)
lines.append("")

DEST.write_text("\n".join(lines), encoding="utf-8")
print(f"{sum(len(v) for v in by_intent.values())} examples across "
      f"{len(by_intent)} intents -> {DEST}")
