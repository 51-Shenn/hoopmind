"""
HoopMind - End-to-end integration test.

Sends utterances to the LIVE Google Dialogflow agent, which then calls
the webhook; prints the matched intent, extracted parameters and the
final user-visible reply. This tests the complete pipeline exactly as
an end user experiences it.

Prerequisites:
  1. A service-account key with the "Dialogflow API Client" role.
     Set:  setx GOOGLE_APPLICATION_CREDENTIALS "C:\\path\\to\\key.json"
     (restart the terminal afterwards)
  2. Your webhook running AND publicly reachable (e.g. via ngrok),
     with the URL pasted into Dialogflow -> Fulfillment.

Usage:
    python evaluation/e2e_test.py PROJECT_ID
    python evaluation/e2e_test.py PROJECT_ID --show-params
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TEST_QUERIES = [
    # (utterance, expected intent)
    ("hello", "greeting"),
    ("bye thanks", "goodbye"),
    ("What data do you have?", "dataset_scope"),
    ("How many points did Michael Jordan average in 1991?", "player_stats"),
    ("What were Stephen Curry's ppg in 2016?", "player_stats"),
    ("Who is Michael Jordan?", "player_info"),
    ("Tell me about Larry Bird", "player_info"),
    ("Was LeBron James an All-Star in 2020?", "all_star"),
    ("How many times was Kobe Bryant an All-Star?", "all_star"),
    ("Where was Stephen Curry drafted?", "draft_info"),
    ("Did Giannis make All-NBA First Team in 2019?", "all_star"),
    ("Compare LeBron James and Michael Jordan points", "compare"),
    ("Which team scored more in 2010, the Lakers or Celtics?", "compare"),
    ("What was the Lakers record in 2000?", "team_info"),
    ("Tell me about the Chicago Bulls franchise", "team_info"),
    ("Opponent points against the Bulls in 1996", "team_info"),
    ("Career points of Kareem Abdul-Jabbar", "player_stats"),
    ("Did Giannis win MVP in 2019?", "player_info"),
    ("Jokic win shares in 2021", "player_stats"),
    ("Curry three-point percentage 2016", "player_stats"),
]


def main() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--show-params", action="store_true")
    args = parser.parse_args()

    try:
        from google.cloud import dialogflow
    except ImportError:
        sys.exit("Install dependency first: pip install google-cloud-dialogflow")

    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(args.project_id, "e2e-test-session")

    passed = 0
    rows = []

    print("=" * 78)
    print(f"HOOPMIND END-TO-END TEST ({len(TEST_QUERIES)} queries)")
    print("=" * 78)

    for utterance, expected in TEST_QUERIES:

        text_input = dialogflow.TextInput(
            text=utterance,
            language_code="en"
        )
        query_input = dialogflow.QueryInput(text=text_input)

        try:
            response = session_client.detect_intent(
                request={
                    "session": session,
                    "query_input": query_input,
                }
            )
            qr = response.query_result
            intent = qr.intent.display_name
            confidence = qr.intent_detection_confidence
            reply = (
                qr.fulfillment_text
                if qr.fulfillment_text
                else "(no reply - check webhook logs)"
            )
            params = dict(qr.parameters)

            ok = intent == expected
            passed += int(ok)
            mark = "PASS" if ok else "FAIL"

            print(f"\n[{mark}] \"{utterance}\"")
            print(f"  intent : {intent} "
                  f"(expected {expected}, conf {confidence:.2f})")

            if args.show_params and params:
                print(f"  params : {json.dumps(params)}")

            print(f"  reply  : {reply}")

            rows.append({
                "utterance": utterance,
                "expected": expected,
                "matched": intent,
                "confidence": round(confidence, 3),
                "pass": ok,
                "reply": reply,
            })

        except Exception as exc:
            print(f"\n[ERROR] \"{utterance}\" -> {exc}")
            rows.append({
                "utterance": utterance,
                "expected": expected,
                "matched": f"ERROR: {exc}",
                "confidence": None,
                "pass": False,
                "reply": "",
            })

        time.sleep(0.3)

    rate = passed / len(TEST_QUERIES)

    print("\n" + "=" * 78)
    print(f"E2E RESULT: {passed}/{len(TEST_QUERIES)} passed "
          f"({rate:.1%} pass rate)")
    print("=" * 78)

    out = Path(__file__).parent / "e2e_test_results.json"
    out.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved details to {out}")


if __name__ == "__main__":
    main()
