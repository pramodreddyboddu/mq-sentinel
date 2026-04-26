from __future__ import annotations

from mq_sentinel.security.ratelimit import RateLimiter


def test_bucket_allows_burst_then_denies() -> None:
    rl = RateLimiter(rate_per_minute=60, burst=3)
    assert rl.allow("u")
    assert rl.allow("u")
    assert rl.allow("u")
    assert not rl.allow("u")


def test_separate_keys_independent() -> None:
    rl = RateLimiter(rate_per_minute=60, burst=1)
    assert rl.allow("a")
    assert rl.allow("b")
    assert not rl.allow("a")
