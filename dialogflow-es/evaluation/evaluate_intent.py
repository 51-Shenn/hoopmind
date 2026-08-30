"""
evaluate_intent.py — training-data loader + tokenizer for HoopMind's
offline intent classifier.

Consumed by dialogflow_client.classify_locally() (dynamically loaded via
importlib) to build a TF-IDF centroid classifier over the training
phrases exported from the Dialogflow ES agent. Not meant to be run
directly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
TRAINING_FILE = EVAL_DIR / "intent_training_phrases.json"

# Lowercase word tokens; keeps internal apostrophes ("curry's") and
# digit tokens (season years like "2016") intact as single tokens.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    """Tokenizer used as the TfidfVectorizer `analyzer`."""
    return _TOKEN_RE.findall(text.lower())


def load_training_data(path: "Path | str | None" = None) -> dict[str, list[str]]:
    """Load the intent -> training-phrases mapping from
    intent_training_phrases.json.

    Returns a dict like {"player_info": ["Who is Stephen Curry", ...], ...},
    skipping the "description" / "intents" metadata keys.
    """
    file_path = Path(path) if path else TRAINING_FILE
    with file_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    intents = raw.get("intents") or [
        k for k in raw.keys() if k not in ("description", "intents")
    ]

    return {intent: list(raw[intent]) for intent in intents if intent in raw}