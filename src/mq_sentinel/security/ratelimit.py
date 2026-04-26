"""Token-bucket rate limiter — in-process, thread-safe, monotonic-clock based."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


@dataclass
class RateLimiter:
    """Simple per-key token bucket. Default: 60 req/min burst 60."""

    rate_per_minute: int = 60
    burst: int = 60
    _buckets: dict[str, _Bucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        refill_rate = self.rate_per_minute / 60.0
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=float(self.burst), last_refill=now)
                self._buckets[key] = bucket
            elapsed = now - bucket.last_refill
            bucket.tokens = min(float(self.burst), bucket.tokens + elapsed * refill_rate)
            bucket.last_refill = now
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return True
            return False
