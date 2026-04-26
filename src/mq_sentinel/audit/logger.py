"""Hash-chained, append-only JSONL audit log.

Each record contains a SHA-256 hash of (prev_hash || canonical_record). Any
tampering with an earlier record breaks the chain for every record after it.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

_GENESIS_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class AuditEvent:
    actor: str
    tenant: str | None
    tool: str
    target_qm: str | None
    params_hash: str
    outcome: str  # "ok" | "denied" | "error"
    duration_ms: int
    error: str | None = None


class AuditLogger:
    """Append-only, hash-chained audit logger. Thread-safe within a process."""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        self._lock = threading.Lock()
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._path.exists() or self._path.stat().st_size == 0:
            return _GENESIS_HASH
        with self._path.open("rb") as f:
            last_line = b""
            for line in f:
                if line.strip():
                    last_line = line
        if not last_line:
            return _GENESIS_HASH
        try:
            record = orjson.loads(last_line)
            last_hash = record.get("hash", _GENESIS_HASH)
            return last_hash if isinstance(last_hash, str) else _GENESIS_HASH
        except orjson.JSONDecodeError:
            return _GENESIS_HASH

    def write(self, event: AuditEvent) -> str:
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "actor": event.actor,
            "tenant": event.tenant,
            "tool": event.tool,
            "target_qm": event.target_qm,
            "params_hash": event.params_hash,
            "outcome": event.outcome,
            "duration_ms": event.duration_ms,
            "error": event.error,
        }
        with self._lock:
            record["prev_hash"] = self._prev_hash
            canonical = orjson.dumps(record, option=orjson.OPT_SORT_KEYS)
            record_hash = hashlib.sha256(canonical).hexdigest()
            record["hash"] = record_hash
            line = orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("ab") as f:
                f.write(line)
            self._prev_hash = record_hash
            return record_hash


def verify_chain(log_path: Path) -> bool:
    """Re-hash every record and confirm the chain is intact."""
    prev_hash = _GENESIS_HASH
    if not log_path.exists():
        return True
    with log_path.open("rb") as f:
        for line_num, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            record = orjson.loads(raw)
            expected_prev = record.get("prev_hash")
            stored_hash = record.pop("hash", None)
            if expected_prev != prev_hash:
                raise ValueError(f"audit chain broken at line {line_num}: prev_hash mismatch")
            canonical = orjson.dumps(record, option=orjson.OPT_SORT_KEYS)
            recomputed = hashlib.sha256(canonical).hexdigest()
            if recomputed != stored_hash:
                raise ValueError(f"audit chain broken at line {line_num}: record hash mismatch")
            prev_hash = stored_hash
    return True
