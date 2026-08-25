"""Grounded LLM answer composition for HoopMind custom actions.

Takes the user's question plus the factual data fetched from CSVs and asks
Gemini to compose a natural, conversational answer. Falls back to the
caller-provided template text whenever the LLM is unavailable.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_PROXY_BASE = "http://127.0.0.1:8080/v1beta"
_GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT_SECONDS = 12

_PROMPT_TEMPLATE = """You are HoopMind, an NBA stats chatbot. Answer the user's question conversationally \
using ONLY the data provided below. Do not invent numbers or facts that are not in the data. \
If the data does not fully answer the question, say what you can and note the limitation briefly. \
Keep it natural and concise (1-4 sentences). Never mention "the data" or "the database" explicitly.

User question: {question}

Data retrieved:
{data}

Answer:"""


def _get_model() -> str:
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    return model.strip().strip('"').strip("'")


def _generate_via_http(url: str, key: str, prompt: str) -> Optional[str]:
    # Note: this Gemini model always "thinks" internally and rejects
    # thinkingConfig/thinkingBudget=0 with HTTP 400 - so we simply give the
    # response enough room (thoughts count against maxOutputTokens).
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    resp = requests.post(
        f"{url}/models/{_get_model()}:generateContent",
        params={"key": key},
        json=body,
        timeout=_TIMEOUT_SECONDS,
    )
    if resp.status_code == 400:
        # Retry once without any generationConfig extras in case of
        # unsupported fields on other model versions.
        resp = requests.post(
            f"{url}/models/{_get_model()}:generateContent",
            params={"key": key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 2048},
            },
            timeout=_TIMEOUT_SECONDS,
        )
    resp.raise_for_status()
    payload = resp.json()
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        texts = [p.get("text", "") for p in parts if not p.get("thought", False)]
        return "".join(texts).strip() or None
    except (KeyError, IndexError, TypeError):
        return None


def _try_proxy(prompt: str) -> Optional[str]:
    """Proxy rotates keys internally on failures."""
    try:
        return _generate_via_http(_PROXY_BASE, os.environ.get("GEMINI_API_KEY", ""), prompt)
    except Exception as exc:
        logger.info("Gemini proxy unavailable (%s) - falling back to direct API", exc)
        return None


def _try_direct(prompt: str) -> Optional[str]:
    """Direct call to Google with local key rotation."""
    try:
        from actions.gemini_key_manager import GeminiKeyManager

        manager = GeminiKeyManager()
        for _ in range(max(manager.key_count if hasattr(manager, "key_count") else len(manager._keys), 1)):
            key = manager.get_key()
            if not key:
                break
            try:
                answer = _generate_via_http(_GOOGLE_BASE, key, prompt)
                if answer:
                    manager.mark_success(key)
                    return answer
                manager.mark_failed(key)
            except Exception:
                manager.mark_failed(key)
    except Exception as exc:
        logger.warning("Direct Gemini call failed: %s", exc)
    return None


def compose_answer(question: str, data_text: str, fallback: str = "", context: str = "") -> str:
    """Compose a natural answer from `data_text` grounded in the CSV facts.

    Returns `fallback` (typically the original template-formatted string)
    whenever the LLM cannot be reached.
    """
    fallback = fallback or data_text
    prompt = _PROMPT_TEMPLATE.format(question=question or context or "NBA question", data=data_text)
    if context:
        prompt += f"\n\nAdditional context: {context}"

    for attempt in (_try_proxy, _try_direct):
        answer = attempt(prompt)
        if answer:
            return answer

    logger.warning("LLM composition unavailable - using template fallback")
    return fallback
