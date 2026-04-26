from __future__ import annotations

from pathlib import Path

import orjson
import pytest

from mq_sentinel.audit import AuditEvent, AuditLogger, verify_chain


def _event(tool: str = "t") -> AuditEvent:
    return AuditEvent(
        actor="u",
        tenant="t",
        tool=tool,
        target_qm="QM1",
        params_hash="deadbeef",
        outcome="ok",
        duration_ms=1,
    )


def test_chain_intact_after_writes(tmp_path: Path) -> None:
    log = tmp_path / "a.jsonl"
    logger = AuditLogger(log)
    for i in range(5):
        logger.write(_event(f"t{i}"))
    assert verify_chain(log) is True


def test_tamper_detected(tmp_path: Path) -> None:
    log = tmp_path / "a.jsonl"
    logger = AuditLogger(log)
    for i in range(3):
        logger.write(_event(f"t{i}"))

    lines = log.read_bytes().splitlines()
    rec = orjson.loads(lines[1])
    rec["tool"] = "forged"
    lines[1] = orjson.dumps(rec)
    log.write_bytes(b"\n".join(lines) + b"\n")

    with pytest.raises(ValueError):
        verify_chain(log)


def test_logger_resumes_chain(tmp_path: Path) -> None:
    log = tmp_path / "a.jsonl"
    AuditLogger(log).write(_event("first"))
    AuditLogger(log).write(_event("second"))  # new logger, same file
    assert verify_chain(log) is True
