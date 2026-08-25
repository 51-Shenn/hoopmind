"""Local Gemini API proxy with automatic key rotation and fallback.

Runs a local HTTP server that proxies requests to the Gemini API,
rotating between multiple API keys on failure.

Usage:
    python gemini_proxy.py                    # Start on default port 8080
    python gemini_proxy.py --port 9090        # Custom port

Environment variables:
    GEMINI_API_KEY        - Primary key
    GEMINI_API_KEY_1..N   - Additional keys
    GEMINI_PROXY_PORT     - Server port (default: 8080)
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gemini_proxy")


# ---------------------------------------------------------------------------
# Key Manager
# ---------------------------------------------------------------------------

class KeyManager:
    """Manages multiple Gemini API keys with rotation on failure."""

    COOLDOWN_BASE = 10       # seconds after first failure
    COOLDOWN_MAX = 300       # max cooldown (5 min)
    MAX_FAILURES = 3         # failures before long cooldown

    def __init__(self):
        self._keys: List[str] = []
        self._index = 0
        self._failures: dict = {}      # key -> consecutive failure count
        self._cooldown_until: dict = {} # key -> timestamp
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        seen = set()
        # Primary
        k = os.environ.get("GEMINI_API_KEY", "")
        if k and k not in seen:
            self._keys.append(k)
            seen.add(k)
        # Numbered
        for i in range(1, 20):
            k = os.environ.get(f"GEMINI_API_KEY_{i}", "")
            if k and k not in seen:
                self._keys.append(k)
                seen.add(k)
        logger.info(f"Loaded {len(self._keys)} API key(s)")

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def next(self) -> Optional[str]:
        with self._lock:
            if not self._keys:
                return None
            now = time.time()
            for _ in range(len(self._keys)):
                key = self._keys[self._index % len(self._keys)]
                self._index += 1
                if now >= self._cooldown_until.get(key, 0):
                    return key
            # All in cooldown → pick shortest wait
            return min(self._keys, key=lambda k: self._cooldown_until.get(k, 0))

    def mark_ok(self, key: str):
        with self._lock:
            self._failures[key] = 0
            self._cooldown_until.pop(key, None)

    def mark_fail(self, key: str):
        with self._lock:
            f = self._failures.get(key, 0) + 1
            self._failures[key] = f
            if f >= self.MAX_FAILURES:
                cd = self.COOLDOWN_BASE * min(f - self.MAX_FAILURES + 1, self.COOLDOWN_MAX // self.COOLDOWN_BASE)
            else:
                cd = 5
            self._cooldown_until[key] = time.time() + cd
            logger.warning(f"Key ...{key[-6:]} failed ({f}x) → cooldown {cd}s")

    def status(self) -> dict:
        with self._lock:
            now = time.time()
            return {
                f"key_{i+1}": {
                    "suffix": f"...{k[-6:]}",
                    "ok": now >= self._cooldown_until.get(k, 0),
                    "failures": self._failures.get(k, 0),
                }
                for i, k in enumerate(self._keys)
            }


# ---------------------------------------------------------------------------
# Proxy Handler
# ---------------------------------------------------------------------------

GEMINI_BASE = "https://generativelanguage.googleapis.com"

# Paths that should be forwarded to Gemini
ALLOWED_PREFIXES = ["/v1beta/", "/v1/"]


class ProxyHandler(BaseHTTPRequestHandler):
    """Forward requests to Gemini API, rotating keys on failure."""

    km: KeyManager  # set by the server class

    def do_POST(self):
        self._proxy("POST")

    def do_GET(self):
        self._proxy("GET")

    def _proxy(self, method: str):
        # Status endpoint for debugging
        if self.path == "/status":
            self._send(200, {"status": "ok", "keys": self.km.status()})
            return

        # Only forward Gemini API paths
        if not any(self.path.startswith(p) for p in ALLOWED_PREFIXES):
            logger.warning(f"Blocked non-Gemini path: {method} {self.path}")
            self._send(404, {"error": "not found"})
            return

        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None

        # Try each key
        last_error = None
        tried_keys = set()

        for attempt in range(self.km.key_count + 1):
            key = self.km.next()
            if key is None:
                self._send(503, {"error": "no API keys available"})
                return
            if key in tried_keys and attempt > 0:
                # Circled back to a key we already tried
                logger.error("All keys exhausted for this request")
                break
            tried_keys.add(key)

            # Strip existing ?key= from path and add our rotated key
            # Preserve other query params
            from urllib.parse import urlparse, parse_qs, urlencode
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            params.pop("key", None)  # Remove existing key
            # Flatten single-value lists
            flat = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
            qs = urlencode(flat)
            clean_path = parsed.path
            if qs:
                url = f"{GEMINI_BASE}{clean_path}?{qs}&key={key}"
            else:
                url = f"{GEMINI_BASE}{clean_path}?key={key}"
            logger.info(f"→ {method} {clean_path} (key ...{key[-6:]})")
            try:
                req = Request(url, data=body, method=method)
                req.add_header("Content-Type", "application/json")

                with urlopen(req, timeout=120) as resp:
                    data = resp.read()
                    self.km.mark_ok(key)
                    self.send_response(resp.status)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data)
                    return

            except HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                status = e.code

                # Don't rotate on client errors (bad request, etc.)
                if 400 <= status < 500 and status != 429:
                    self._send(status, json.loads(error_body) if error_body else {"error": str(e)})
                    return

                # Rate limit or server error → rotate
                self.km.mark_fail(key)
                last_error = error_body
                logger.warning(f"Key ...{key[-6:]} got HTTP {status}: {error_body[:200]}")

            except (URLError, OSError, TimeoutError) as e:
                self.km.mark_fail(key)
                last_error = str(e)
                logger.warning(f"Key ...{key[-6:]} network error: {e}")

        self._send(502, {"error": "all API keys failed", "detail": last_error[:500] if last_error else ""})

    def _send(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress default HTTP logging
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gemini API proxy with key rotation")
    parser.add_argument("--port", type=int, default=int(os.environ.get("GEMINI_PROXY_PORT", 8080)))
    args = parser.parse_args()

    km = KeyManager()
    if km.key_count == 0:
        logger.error("No API keys found. Set GEMINI_API_KEY or GEMINI_API_KEY_1..N")
        sys.exit(1)

    ProxyHandler.km = km
    server = HTTPServer(("127.0.0.1", args.port), ProxyHandler)
    logger.info(f"Gemini proxy listening on http://127.0.0.1:{args.port}")
    logger.info(f"Status: {km.status()}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
