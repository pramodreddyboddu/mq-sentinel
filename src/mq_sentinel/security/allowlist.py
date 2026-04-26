"""Read-only command allowlist. Deny-by-default at the connection layer.

Policy:
- MQSC: only DISPLAY/DIS verbs and the PING CHANNEL probe.
- Shell: only a fixed set of diagnostic binaries with argument patterns.
- No multi-statement MQSC, no comments-that-hide-verbs, no shell metacharacters.

This module is security-critical. Changes require security review and a
passing negative-test corpus (tests/security/test_allowlist.py).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_MQSC_ALLOWED_VERBS: frozenset[str] = frozenset(
    {
        "DISPLAY",
        "DIS",
        "PING",  # PING CHANNEL only — validated below
    }
)

_MQSC_DENIED_VERBS: frozenset[str] = frozenset(
    {
        "ALTER",
        "DEFINE",
        "DELETE",
        "START",
        "STOP",
        "SUSPEND",
        "RESUME",
        "REFRESH",
        "RESET",
        "CLEAR",
        "MOVE",
        "RECOVER",
        "SET",
        "BACKUP",
        "END",
        "ARCHIVE",
        "RECORD",
        "REVERIFY",
        "CHANGE",
    }
)

_MQSC_FORBIDDEN_CHARS = re.compile(r"[;\n\r\x00]")
_MQSC_COMMENT = re.compile(r"\*.*$|--.*$", re.MULTILINE)

_SHELL_ALLOWED: dict[str, re.Pattern[str]] = {
    "dspmq": re.compile(r"^(|(-[mnosxa]|-o\s+\w+)(\s+(-[mnosxa]|-o\s+\w+))*)$"),
    "dspmqinf": re.compile(r"^[A-Z0-9._%/]{1,48}$"),
    "dspmqver": re.compile(r"^(|-[pf])$"),
    "rdqmstatus": re.compile(r"^(|-m\s+[A-Z0-9._%/]{1,48})$"),
    "crm_mon": re.compile(r"^(|-[1rnfA]+)$"),
    "drbdadm": re.compile(r"^status(\s+[a-z0-9_-]+)?$"),
}


class CommandNotAllowedError(PermissionError):
    """Raised when a command fails the allowlist. Never caught silently."""


def _strip_mqsc_comments(command: str) -> str:
    return _MQSC_COMMENT.sub("", command).strip()


def assert_mqsc_allowed(command: str) -> None:
    """Validate an MQSC command against the read-only allowlist.

    Raises CommandNotAllowedError if the command is not permitted.
    """
    if not command or not command.strip():
        raise CommandNotAllowedError("empty MQSC command")

    if _MQSC_FORBIDDEN_CHARS.search(command):
        raise CommandNotAllowedError("MQSC contains forbidden character (;, newline, NUL)")

    cleaned = _strip_mqsc_comments(command)
    if not cleaned:
        raise CommandNotAllowedError("MQSC command is empty after comment strip")

    tokens = cleaned.split()
    verb = tokens[0].upper()

    if verb in _MQSC_DENIED_VERBS:
        raise CommandNotAllowedError(f"MQSC verb '{verb}' is denied (read-only mode)")

    if verb not in _MQSC_ALLOWED_VERBS:
        raise CommandNotAllowedError(f"MQSC verb '{verb}' is not in allowlist")

    if verb == "PING":
        # Accept "PING CHANNEL(NAME)" — strip "(...)" from the second token before compare.
        second = tokens[1].upper().split("(", 1)[0] if len(tokens) >= 2 else ""
        if second != "CHANNEL":
            raise CommandNotAllowedError("PING is only allowed as 'PING CHANNEL'")


def assert_shell_allowed(argv: Sequence[str]) -> None:
    """Validate a shell argv against the allowlist. argv MUST be a list, never a string."""
    if not argv:
        raise CommandNotAllowedError("empty argv")

    binary = argv[0]
    if binary not in _SHELL_ALLOWED:
        raise CommandNotAllowedError(f"binary '{binary}' not in shell allowlist")

    args = " ".join(argv[1:])
    if not _SHELL_ALLOWED[binary].match(args):
        raise CommandNotAllowedError(f"arguments for '{binary}' failed validation: {args!r}")
