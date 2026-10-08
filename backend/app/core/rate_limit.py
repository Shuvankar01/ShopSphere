"""Small in-process sliding-window rate limiter (no external services).

Used for authentication brute-force protection: only *failed* attempts are
counted, keyed by client IP + target account, so legitimate users are not
locked out by their own successful logins.
"""
from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, window_seconds: float, now: float) -> deque[float]:
        dq = self._events.setdefault(key, deque())
        while dq and now - dq[0] > window_seconds:
            dq.popleft()
        return dq

    def is_blocked(self, key: str, max_failures: int, window_seconds: float) -> bool:
        """True when the key already exhausted its failure budget."""
        now = time.monotonic()
        with self._lock:
            dq = self._prune(key, window_seconds, now)
            return len(dq) >= max_failures

    def record_failure(self, key: str, window_seconds: float) -> None:
        now = time.monotonic()
        with self._lock:
            dq = self._prune(key, window_seconds, now)
            dq.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


# Process-wide instance for login brute-force protection.
login_rate_limiter = SlidingWindowRateLimiter()
