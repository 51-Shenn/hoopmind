"""Gemini API key manager with automatic rotation and fallback."""

import os
import time
import logging
import threading
from typing import Optional, List
from itertools import cycle

logger = logging.getLogger(__name__)


class GeminiKeyManager:
    """Manages multiple Gemini API keys with automatic rotation on failure.

    Reads keys from environment variables:
      GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, ...

    Usage:
        manager = GeminiKeyManager()
        key = manager.get_key()  # Returns current active key
        manager.mark_failed(key)  # Marks key as failed, rotates to next
        manager.mark_success(key)  # Marks key as working (resets failure count)
    """

    _COOLDOWN_SECONDS = 60  # How long to skip a failed key
    _MAX_FAILURES = 3  # Failures before long cooldown

    def __init__(self):
        self._keys: List[str] = []
        self._failed_until: dict = {}  # key -> timestamp when it becomes available again
        self._failure_count: dict = {}  # key -> consecutive failure count
        self._lock = threading.Lock()
        self._current_index = 0
        self._load_keys()

    def _load_keys(self):
        """Load all API keys from environment variables."""
        keys = []

        # Primary key
        primary = os.environ.get("GEMINI_API_KEY")
        if primary:
            keys.append(primary)

        # Numbered keys: GEMINI_API_KEY_1 through GEMINI_API_KEY_9
        for i in range(1, 10):
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if key and key not in keys:
                keys.append(key)

        self._keys = keys
        if keys:
            logger.info(f"Loaded {len(keys)} Gemini API key(s)")
        else:
            logger.warning("No Gemini API keys found in environment variables")

    def get_key(self) -> Optional[str]:
        """Get the next available API key, skipping any in cooldown."""
        with self._lock:
            if not self._keys:
                return None

            now = time.time()
            attempts = 0

            while attempts < len(self._keys):
                key = self._keys[self._current_index % len(self._keys)]
                self._current_index = (self._current_index + 1) % len(self._keys)

                # Check if this key is in cooldown
                cooldown_until = self._failed_until.get(key, 0)
                if now >= cooldown_until:
                    return key

                attempts += 1

            # All keys in cooldown — use the one with shortest wait
            soonest_key = min(self._keys, key=lambda k: self._failed_until.get(k, 0))
            wait = self._failed_until[soonest_key] - now
            logger.warning(f"All keys in cooldown. Earliest available in {wait:.0f}s")
            return soonest_key

    def mark_failed(self, key: str):
        """Mark a key as failed and rotate to the next one."""
        with self._lock:
            failures = self._failure_count.get(key, 0) + 1
            self._failure_count[key] = failures

            if failures >= self._MAX_FAILURES:
                cooldown = self._COOLDOWN_SECONDS * (failures - self._MAX_FAILURES + 1)
            else:
                cooldown = 5  # Short cooldown for first few failures

            self._failed_until[key] = time.time() + cooldown
            logger.warning(
                f"Gemini key ...{key[-8:]} failed ({failures}x), "
                f"cooling down for {cooldown}s"
            )

    def mark_success(self, key: str):
        """Mark a key as working (resets failure count)."""
        with self._lock:
            self._failure_count[key] = 0
            self._failed_until.pop(key, None)

    def get_status(self) -> dict:
        """Get status of all keys."""
        with self._lock:
            now = time.time()
            status = {}
            for i, key in enumerate(self._keys):
                cooldown_until = self._failed_until.get(key, 0)
                status[f"key_{i+1}"] = {
                    "suffix": f"...{key[-8:]}",
                    "available": now >= cooldown_until,
                    "failures": self._failure_count.get(key, 0),
                    "cooldown_remaining": max(0, cooldown_until - now),
                }
            return status

    @property
    def key_count(self) -> int:
        return len(self._keys)


# Singleton instance
_manager: Optional[GeminiKeyManager] = None


def get_key_manager() -> GeminiKeyManager:
    """Get or create the singleton key manager."""
    global _manager
    if _manager is None:
        _manager = GeminiKeyManager()
    return _manager
