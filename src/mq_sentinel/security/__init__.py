"""Security layer: command allowlist, output sanitizer, rate limiter.

These modules are the last line of defense. Every tool call must pass through
the allowlist (for outbound MQSC/shell) and the sanitizer (for returned data).
"""

from mq_sentinel.security.allowlist import (
    CommandNotAllowedError,
    assert_mqsc_allowed,
    assert_shell_allowed,
)
from mq_sentinel.security.ratelimit import RateLimiter
from mq_sentinel.security.sanitizer import sanitize_mq_output, scrub_injection_markers

__all__ = [
    "CommandNotAllowedError",
    "RateLimiter",
    "assert_mqsc_allowed",
    "assert_shell_allowed",
    "sanitize_mq_output",
    "scrub_injection_markers",
]
