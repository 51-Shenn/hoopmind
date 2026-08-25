"""
HoopMind - Intent classification evaluation.

Two modes:

1. Local simulation (default):
   A transparent nearest-centroid bag-of-words classifier trained on the
   SAME training phrases that were imported into Dialogflow. This gives a
   fast, fully offline approximation of intent-classification quality.

2. Live API mode (--api PROJECT_ID):
   Sends every test utterance to the real Google Dialogflow agent using
   google-cloud-dialogflow and measures the actual model.
   Requires GOOGLE_APPLICATION_CREDENTIALS to point at a service-account
   key with the Dialogflow Client role.

Usage:
    python evaluate_intent.py
    python evaluate_intent.py --api YOUR_PROJECT_ID
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
TRAINING_PHRASES = (
    EVAL_DIR / "intent_training_phrases.json"
)
TEST_SET = EVAL_DIR / "intent_test_set.json"


# ============================================================
# TEXT PROCESSING
# ============================================================


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


# ============================================================
# LOCAL NEAREST-CENTROID CLASSIFIER
# ============================================================


class CentroidClassifier:
    """
    Minimal TF cosine-similarity classifier.

    Each intent is represented by the sum of L2-normalised token-count
    vectors of its training phrases; an utterance is assigned to the
    intent whose centroid has the highest cosine similarity.
    """

    def __init__(self) -> None:
        self.centroids: dict[str, Counter] = {}
        self.idf: dict[str, float] = {}

    def fit(self, data: dict[str, list[str]]) -> None:

        doc_freq: Counter = Counter()

        for phrases in data.values():
            for tokens in map(tokenize, phrases):
                doc_freq.update(set(tokens))

        n_docs = sum(len(v) for v in data.values())
        self.idf = {
            term: math.log((1 + n_docs) / (1 + df)) + 1
            for term, df in doc_freq.items()
        }

        for intent, phrases in data.items():

            centroid: Counter = Counter()

            for tokens in map(tokenize, phrases):

                tf = Counter(tokens)
                norm = self._vec_norm(tf)

                for term, count in tf.items():
                    weight = (1 + math.log(count)) * self.idf.get(term, 1.0)
                    centroid[term] += weight / norm

            self.centroids[intent] = centroid

    @staticmethod
    def _vec_norm(tf: Counter) -> float:
        return math.sqrt(
            sum((1 + math.log(c)) ** 2 for c in tf.values())
        ) or 1.0

    def predict(self, utterance: str) -> tuple[str, float]:

        tf = Counter(tokenize(utterance))
        norm = self._vec_norm(tf)

        query = {
            t: (1 + math.log(c)) * self.idf.get(t, 1.0) / norm
            for t, c in tf.items()
        }

        best_intent, best_score = 'Default Fallback Intent', -1.0

        for intent, centroid in self.centroids.items():

            score = sum(
                weight * centroid.get(term, 0.0)
                for term, weight in query.items()
            )

            if score > best_score:
                best_intent, best_score = intent, score

        return best_intent, best_score


def load_training_data() -> dict[str, list[str]]:

    raw = json.loads(
        TRAINING_PHRASES.read_text(encoding="utf-8")
    )

    return {
        intent: list(phrases)
        for intent, phrases in raw.items()
        if isinstance(phrases, list)
    }


# ============================================================
# METRICS
# ============================================================


def classification_report(
    expected: list[str],
    predicted: list[str],
    utterances: list[str],
) -> str:

    labels = sorted(set(expected) | set(predicted))

    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    confusion: list[tuple[str, str, str]] = []

    for utt, exp, pred in zip(utterances, expected, predicted):

        if exp == pred:
            tp[exp] += 1
        else:
            fp[pred] += 1
            fn[exp] += 1
            confusion.append((exp, pred, utt))

    lines = []
    f1_scores = []

    for label in labels:

        precision = (
            tp[label] / (tp[label] + fp[label])
            if tp[label] + fp[label] else 0.0
        )
        recall = (
            tp[label] / (tp[label] + fn[label])
            if tp[label] + fn[label] else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0.0
        )

        f1_scores.append(f1)

        support = expected.count(label)

        lines.append(
            f"{label:<28} P={precision:>6.3f}  R={recall:>6.3f}  "
            f"F1={f1:>6.3f}  n={support}"
        )

    macro_f1 = sum(f1_scores) / len(labels) if labels else 0.0
    accuracy = (
        sum(tp.values()) / len(expected) if expected else 0.0
    )

    report = "\n".join(lines)
    summary = (
        f"\nAccuracy = {accuracy:.3f}   Macro-F1 = {macro_f1:.3f}"
    )

    conf_lines = []
    for exp, pred, utt in confusion[:15]:
        conf_lines.append(f"  '{utt}'\n      expected={exp} got={pred}")

    return (
        f"{'INTENT':<28} METRICS\n"
        + report
        + "\n"
        + summary
        + ("\n\nMisclassifications:\n" + "\n".join(conf_lines) if conf_lines else "")
    )


# ============================================================
# LIVE DIALOGFLOW MODE
# ============================================================


def dialogflow_predict(project_id: str, utterances: list[str]) -> list[str]:

    from google.cloud import dialogflow

    session_client = dialogflow.SessionsClient()

    predictions = []

    for i, utterance in enumerate(utterances):

        session = session_client.session_path(
            project_id,
            f"eval-session-{i % 100}"
        )

        text_input = dialogflow.TextInput(
            text=utterance,
            language_code="en"
        )
        query_input = dialogflow.QueryInput(text=text_input)

        response = session_client.detect_intent(
            request={
                "session": session,
                "query_input": query_input,
            }
        )

        name = response.query_result.intent.display_name

        if response.query_result.intent_detection_confidence < 0.3:
            name = "Default Fallback Intent"

        predictions.append(name)

    return predictions


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("--api", metavar="PROJECT_ID", default=None,
                        help="Evaluate against the live Dialogflow agent")
    args = parser.parse_args()

    cases = json.loads(TEST_SET.read_text(encoding="utf-8"))["cases"]

    expected = [c["expected"] for c in cases]
    utterances = [c["utterance"] for c in cases]

    if args.api:

        predicted = dialogflow_predict(args.api, utterances)
        title = f"DIALOGFLOW LIVE AGENT ({len(cases)} utterances)"

    else:

        training = load_training_data()
        print(
            f"Loaded {sum(len(v) for v in training.values())} training "
            f"phrases across {len(training)} intents."
        )

        clf = CentroidClassifier()
        clf.fit(training)

        predicted = [
            clf.predict(u)[0] for u in utterances
        ]
        title = (
            f"LOCAL SIMULATION - nearest-centroid TF-IDF "
            f"({len(cases)} held-out utterances)"
        )

    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)

    print(classification_report(expected, predicted, utterances))

    print(
        "\nNote: local mode simulates retrieval over the same training "
        "data; run --api PROJECT_ID for the authoritative Dialogflow "
        "metrics for your report."
    )


if __name__ == "__main__":
    main()
