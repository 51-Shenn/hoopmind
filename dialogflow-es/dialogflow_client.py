"""
HoopMind - Dialogflow ES detection client.

Streamlit chat flow: the Flask /chat endpoint forwards the raw
user text to Dialogflow ES (intent + entities), then runs the
same local pipeline as the offline fallback. If Dialogflow
is unreachable or no credentials are configured, a local
centroid classifier over the 217 training phrases keeps the
demo alive offline.
"""

from __future__ import annotations

import json
import os

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
) -> tuple[str, dict, str] | None:
    """
    Returns (intent_name, parameters, query_text) or None when
    Dialogflow cannot be used.
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

        if (
            result.intent_detection_confidence < 0.35
            and intent_name != "Default Fallback Intent"
        ):
            return None  # let local classifier try
        
        return (intent_name, cleaned, result.query_text)

    except Exception as exc:  # pragma: no cover
        print(f"[dialogflow] unavailable: {exc}")
        return None


# ------------------------------------------------------------
# OFFLINE FALLBACK: centroid classifier over training phrases
# ------------------------------------------------------------

_FALLBACK = None


def classify_locally(text: str) -> str | None:
    global _FALLBACK
    try:
        if _FALLBACK is None:
            import sys

            sys.path.insert(
                0, os.path.join(os.path.dirname(__file__), "evaluation")
            )

            import evaluate_intent as ei

            data_map = ei.load_training_data()
            utterances: list = []
            labels: list = []

            for lab, phrases in data_map.items():
                for phrase in phrases:
                    utterances.append(phrase)
                    labels.append(lab)

            data = list(zip(utterances, labels))

            from sklearn.feature_extraction.text import TfidfVectorizer

            vec = TfidfVectorizer(analyzer=ei.tokenize, sublinear_tf=True)
            X = vec.fit_transform([u for u, _ in data])

            import numpy as np

            centroids = {}
            labels = sorted({lab for _, lab in data})

            for lab in labels:
                idx = [i for i, (_, l) in enumerate(data) if l == lab]
                centroids[lab] = np.asarray(X[idx].mean(axis=0)).ravel()

            def predict(t: str) -> str:
                import numpy as np

                v = vec.transform([t]).toarray()[0].ravel()
                best, best_sim = "", -2.0

                for lab, cen in centroids.items():
                    denom = ((v * v).sum() * (cen * cen).sum()) ** 0.5
                    sim = float(v @ cen) / denom if denom else 0.0
                    if sim > best_sim:
                        best, best_sim = lab, sim
                return best

            _FALLBACK = predict

        return _FALLBACK(text)
    except Exception as exc:  # pragma: no cover
        print(f"[fallback] failed: {exc}")
        return None