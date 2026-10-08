"""Parse MQSC reply text into attribute rows.

MQSC output (runmqsc, or the EscapedReply of a PCF MQCMD_ESCAPE) is a series
of message lines, each followed by that object's attributes:

    AMQ8417I: Display Channel Status details.
       CHANNEL(APP.SVRCONN)                    CHLTYPE(SVRCONN)
       CONNAME(10.0.0.42(1414))                CURRENT
       STATUS(RETRYING)

Each message line starts a new row. Attributes are ``KEY(VALUE)`` pairs, where
VALUE may contain nested parentheses or a quoted string, or bare keywords such
as ``CURRENT`` (stored with an empty value). Message lines with no attributes,
such as ``AMQ8420I: Channel Status not found.``, produce no row.
"""

from __future__ import annotations

import re

# Distributed (AMQnnnnX:) and z/OS (CSQxnnnX) message identifiers.
_MESSAGE_LINE = re.compile(r"^\s*(?:AMQ\d{4}[A-Z]:|CSQ[A-Z0-9]\d{3}[A-Z]\b)")
_KEY = re.compile(r"[A-Z][A-Z0-9_]*")
# A distributed message id that is not at the start of a line (some escaped
# replies arrive without line breaks between objects).
_INLINE_AMQ = re.compile(r"(?<=\S)[ \t]+(?=AMQ\d{4}[A-Z]:)")


def parse_mqsc_reply(text: str) -> list[dict[str, str]]:
    """Split MQSC reply text into one ``{ATTR: value}`` dict per object."""
    rows: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in _INLINE_AMQ.sub("\n", text).splitlines():
        if _MESSAGE_LINE.match(line):
            if current:
                rows.append(current)
            # The message text itself is prose; keep only KEY(VALUE) pairs that
            # share its line.
            current = _parse_attributes(line, pairs_only=True)
            continue
        if current is None:
            continue  # command echo / banner before the first message line
        current.update(_parse_attributes(line))
    if current:
        rows.append(current)
    return rows


def message_ids(text: str) -> list[str]:
    """Return the AMQ/CSQ message ids in reply text, e.g. ``["AMQ8420I"]``."""
    ids: list[str] = []
    for line in text.splitlines():
        if _MESSAGE_LINE.match(line):
            ids.append(line.strip().split(":", 1)[0].split()[0])
    return ids


def _parse_attributes(line: str, *, pairs_only: bool = False) -> dict[str, str]:
    """Parse one attribute line. Prose lines (runmqsc trailers) yield nothing.

    With ``pairs_only``, skip anything that isn't ``KEY(VALUE)`` instead.
    """
    attrs: dict[str, str] = {}
    i, n = 0, len(line)
    while i < n:
        if line[i].isspace():
            i += 1
            continue
        match = _KEY.match(line, i)
        end = match.end() if match else i
        is_pair = match is not None and end < n and line[end] == "("
        if (
            match is None
            or (end < n and line[end] != "(" and not line[end].isspace())
            or (pairs_only and not is_pair)
        ):
            # Not an attribute token. On the first token this is prose; drop the line.
            if not attrs and not pairs_only:
                return {}
            while i < n and not line[i].isspace():
                i += 1
            continue
        assert match is not None
        key = match.group(0)
        i = end
        if i < n and line[i] == "(":
            value, i = _read_value(line, i + 1)
            attrs[key] = value
        else:
            attrs[key] = ""
    return attrs


def _read_value(line: str, i: int) -> tuple[str, int]:
    """Read from just after ``(`` to the matching ``)``; honours quotes and nesting."""
    depth = 1
    out: list[str] = []
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "'":
            # Quoted string; '' is an escaped quote.
            j = i + 1
            while j < n:
                if line[j] == "'":
                    if j + 1 < n and line[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append(line[i : j + 1])
            i = j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return "".join(out).strip(), i + 1
        out.append(ch)
        i += 1
    return "".join(out).strip(), i  # unterminated: take the rest of the line
