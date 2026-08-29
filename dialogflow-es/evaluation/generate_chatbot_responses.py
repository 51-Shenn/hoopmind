"""
Fill chatbot_response in test_results.csv with the ACTUAL text HoopMind shows
users, generated the same way the /chat endpoint does.

WHY THIS SCRIPT EXISTS
-----------------------
run_dialogflow_evaluation.py reads `result.fulfillment_text` from the
Dialogflow ES `detectIntent` response. That field is only populated when a
Dialogflow *fulfillment webhook* is configured and answers each intent.
HoopMind does not do this: dialogflow_client.py and webhook.py show that
Dialogflow ES is used ONLY for intent/entity detection, and the actual
answer (rich cards) is built afterwards, locally, by
`webhook.process_message()` -> query_engine + response_generator. There is
also no Dialogflow-webhook-shaped route in webhook.py (only "/" and
"/chat"), so fulfillment_text will always be empty here - that's why
chatbot_response ended up blank for all 130 rows after the intent-only run.

This script re-runs the SAME local pipeline the Streamlit app uses
(webhook.process_message) for every test phrase, using the predicted_intent
already captured by run_dialogflow_evaluation.py, and flattens the resulting
rich-card payload into plain text so it can be rated / compared with
BLEU-ROUGE. No network or GCP credentials are needed for this step.

Usage:
    python evaluation/generate_chatbot_responses.py
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
APP_DIR = EVAL_DIR.parent
RESULT_FILE = EVAL_DIR / "test_results.csv"
FIELDS = ["test_id", "expected_intent", "test_phrase", "predicted_intent",
          "confidence", "correct", "chatbot_response",
          "response_quality_1_to_5", "reference_response"]

sys.path.insert(0, str(APP_DIR))


def flatten(payload: dict) -> str:
    """Turn a process_message() result into one plain-text answer string,
    the same content a user reads in the Streamlit card, minus suggestion
    chips (those are UI shortcuts, not answer content)."""
    if payload.get("text"):
        return str(payload["text"]).strip()
    rich = payload.get("rich")
    if not rich:
        return ""
    lines = []
    for card in rich:
        for block in card:
            btype = block.get("type")
            if btype == "chips":
                continue
            title = block.get("title")
            subtitle = block.get("subtitle")
            if title:
                lines.append(str(title))
            if subtitle:
                lines.append(str(subtitle))
            for t in block.get("text") or []:
                if t:
                    lines.append(str(t))
    # collapse to single line, keep readable spacing
    return " | ".join(l.strip() for l in lines if l.strip())


def main():
    if not RESULT_FILE.exists():
        raise SystemExit("Run run_dialogflow_evaluation.py first.")
    import webhook  # local pipeline only; makes no network calls

    with RESULT_FILE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for i, r in enumerate(rows, 1):
        intent = r["predicted_intent"] or "Default Fallback Intent"
        try:
            result = webhook.process_message(intent, {}, r["test_phrase"], source="eval")
            r["chatbot_response"] = flatten(result)
        except Exception as exc:
            r["chatbot_response"] = f"[ERROR generating response: {exc}]"
        print(f"[{i:03}/{len(rows)}] {r['test_id']} {intent:<16} -> {r['chatbot_response'][:70]}")

    with RESULT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nUpdated {RESULT_FILE.name} with real chatbot_response text for {len(rows)} rows.")
    print("Next: fill response_quality_1_to_5 for all rows, and reference_response for the "
          "subset you want scored with BLEU/ROUGE, then run evaluate_responses.py.")


if __name__ == "__main__":
    main()