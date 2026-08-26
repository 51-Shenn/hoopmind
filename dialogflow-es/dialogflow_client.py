"""
HoopMind - Dialogflow ES detection client.

Streamlit chat flow: the Flask /chat endpoint forwards the raw
user text to Dialogflow ES (intent + entities), then runs the
same local pipeline as the offline fallback. If Dialogflow
is unreachable or no credentials are configured, a local
centroid classifier over the training phrases keeps the
demo alive offline.
"""

from __future__ import annotations

import json
import os
import re

_DF_PROJECT = None


def _project_id() -> str | None:
    global _DF_PROJECT

    if _DF_PROJECT:
        return _DF_PROJECT

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_path and os.path.exists(creds_path):
        try:
            with open(creds_path, encoding="utf-8") as fh:
                data = json.load(fh)

            _DF_PROJECT = data.get("project_id")

            return _DF_PROJECT
        except Exception:
            pass

    return os.environ.get("HOOPMIND_DF_PROJECT") or None


def detect_via_dialogflow(
    text: str, session_id: str
) -> tuple[str, float, dict, str] | None:
    """
    Returns (intent_name, confidence, parameters, query_text)
    or None when Dialogflow cannot be used.
    """

    project = _project_id()
    if not project:
        return None
    try:
        from google.cloud import dialogflow

        session_client = dialogflow.SessionsClient()
        session = session_client.session_path(project, session_id)
        text_input = dialogflow.TextInput(text=text, language_code="en")
        query_input = dialogflow.QueryInput(text=text_input)
        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )
        result = response.query_result

        params = {
            k: (
                list(v)
                if isinstance(v, (list,))
                else (dict(v.fields) if hasattr(v, "fields") else v)
            )
            for k, v in result.parameters.items()
        }

        # List-valued entities arrive as protobuf RepeatedComposite.
        cleaned: dict = {}

        for key, value in params.items():
            if isinstance(value, list):
                cleaned[key] = [str(v) for v in value]
            elif hasattr(value, "ListFields"):
                cleaned[key] = [str(x) for x in value]
            else:
                cleaned[key] = value

        intent_name = result.intent.display_name
        confidence = result.intent_detection_confidence

        return (intent_name, confidence, cleaned, result.query_text)

    except Exception as exc:  # pragma: no cover
        print(f"[dialogflow] unavailable: {exc}")
        return None


# ------------------------------------------------------------
# OFFLINE FALLBACK: centroid classifier over training phrases
# Returns (intent, confidence) — confidence is the cosine
# similarity to the best centroid.
# ------------------------------------------------------------

_FALLBACK = None


def classify_locally(text: str) -> tuple[str, float] | None:
    global _FALLBACK
    try:
        if _FALLBACK is None:
            from pathlib import Path
            import importlib.util

            evaluation_dir = Path(__file__).resolve().parent / "evaluation"
            evaluate_intent_path = evaluation_dir / "evaluate_intent.py"

            spec = importlib.util.spec_from_file_location(
                "hoopmind_evaluate_intent",
                evaluate_intent_path
            )

            if spec is None or spec.loader is None:
                raise ImportError(
                    f"Could not load evaluation module: {evaluate_intent_path}"
                )

            ei = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ei)

            data_map = ei.load_training_data()
            utterances: list = []
            labels_intents: list = []

            for lab, phrases in data_map.items():
                for phrase in phrases:
                    utterances.append(phrase)
                    labels_intents.append(lab)

            from sklearn.feature_extraction.text import TfidfVectorizer

            vec = TfidfVectorizer(analyzer=ei.tokenize, sublinear_tf=True)
            X = vec.fit_transform(utterances)

            import numpy as np

            centroids = {}
            unique_labels = sorted(set(labels_intents))

            for lab in unique_labels:
                idx = [i for i, l in enumerate(labels_intents) if l == lab]
                centroids[lab] = np.asarray(X[idx].mean(axis=0)).ravel()

            def predict(t: str) -> tuple[str, float] | None:
                # Collapse repeated characters only for short inputs
                # (handles misspelled greetings like "hii", "hey!!")
                # without breaking valid names like "curry".
                q = t
                if len(t) <= 4:
                    q = re.sub(r"(.)\1{1,}", r"\1", t)
                v = vec.transform([q]).toarray()[0].ravel()
                best, best_sim = "", -2.0

                for lab, cen in centroids.items():
                    denom = ((v * v).sum() * (cen * cen).sum()) ** 0.5
                    sim = float(v @ cen) / denom if denom else 0.0
                    if sim > best_sim:
                        best, best_sim = lab, sim

                return (best, best_sim)

            _FALLBACK = predict

        return _FALLBACK(text)
    except Exception as exc:  # pragma: no cover
        print(f"[fallback] failed: {exc}")
        return None
