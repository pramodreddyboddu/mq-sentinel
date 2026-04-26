"""Output sanitizer — prompt-injection firewall for data returned from IBM MQ.

MQ log lines, DLQ headers, queue/channel names, and error messages are all
UNTRUSTED. An attacker who can write to a queue name or seed a log line could
otherwise steer the downstream LLM. Every string we return from a tool passes
through sanitize_mq_output().

Design:
- Strip / neutralize control chars, ANSI escapes, zero-width chars, unicode tag
  chars (U+E0000 range), and common injection markers.
- Drop URLs not on the allowlist (typically just www.ibm.com/docs).
- Wrap the result in a quarantine envelope so the client LLM knows this is data,
  not instructions.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Final

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_ZERO_WIDTH = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]")
_TAG_CHARS = re.compile(r"[\U000E0000-\U000E007F]")
_URL = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

_INJECTION_MARKERS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?i)\bignore (?:all )?previous instructions?\b"),
    re.compile(r"(?i)\bdisregard (?:the )?(?:prior|above) (?:prompt|instructions?)\b"),
    re.compile(r"(?i)\byou are now\b"),
    re.compile(r"(?i)\bnew instructions?:\s*"),
    re.compile(r"(?i)</?system>"),
    re.compile(r"(?i)</?assistant>"),
    re.compile(r"(?i)</?user>"),
    re.compile(r"\[\[SYSTEM\]\]", re.IGNORECASE),
    re.compile(r"###\s*system", re.IGNORECASE),
)

_REDACTED = "[REDACTED:injection_pattern]"
_MAX_STRING_LEN = 8192


def scrub_injection_markers(text: str) -> str:
    """Replace prompt-injection markers with a redaction token."""
    for pattern in _INJECTION_MARKERS:
        text = pattern.sub(_REDACTED, text)
    return text


def _drop_disallowed_urls(text: str, allowed_hosts: tuple[str, ...]) -> str:
    def _replace(match: re.Match[str]) -> str:
        url = match.group(0)
        if any(f"://{host}" in url.lower() for host in allowed_hosts):
            return url
        return "[REDACTED:url]"

    return _URL.sub(_replace, text)


def sanitize_mq_output(
    value: Any,
    *,
    allowed_doc_hosts: tuple[str, ...] = ("www.ibm.com",),
    max_len: int = _MAX_STRING_LEN,
) -> Any:
    """Recursively sanitize strings inside MQ-sourced data before returning to the client.

    - Normalizes unicode (NFKC).
    - Strips control / ANSI / zero-width / tag chars.
    - Redacts injection markers.
    - Redacts non-allowlisted URLs.
    - Truncates overly long strings.
    - Leaves numeric and boolean values untouched.
    """
    if isinstance(value, str):
        s = unicodedata.normalize("NFKC", value)
        s = _ANSI_ESCAPE.sub("", s)
        s = _CONTROL_CHARS.sub("", s)
        s = _ZERO_WIDTH.sub("", s)
        s = _TAG_CHARS.sub("", s)
        s = scrub_injection_markers(s)
        s = _drop_disallowed_urls(s, allowed_doc_hosts)
        if len(s) > max_len:
            s = s[:max_len] + "…[truncated]"
        return s
    if isinstance(value, dict):
        return {
            k: sanitize_mq_output(v, allowed_doc_hosts=allowed_doc_hosts, max_len=max_len)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            sanitize_mq_output(v, allowed_doc_hosts=allowed_doc_hosts, max_len=max_len)
            for v in value
        ]
    if isinstance(value, tuple):
        return tuple(
            sanitize_mq_output(v, allowed_doc_hosts=allowed_doc_hosts, max_len=max_len)
            for v in value
        )
    return value


def quarantine_envelope(content: Any) -> dict[str, Any]:
    """Wrap untrusted MQ data so downstream LLMs treat it as data, not instructions."""
    return {
        "source": "mq_untrusted",
        "trust_level": "data_only",
        "content": sanitize_mq_output(content),
    }
