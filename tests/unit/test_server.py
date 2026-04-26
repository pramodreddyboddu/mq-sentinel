from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.audit import verify_chain
from mq_sentinel.config import Settings
from mq_sentinel.server import MQSentinelServer


def _settings(tmp_path: Path) -> Settings:
    s = Settings()
    s.audit.log_path = tmp_path / "audit.jsonl"
    return s


def test_health_success_and_audit_ok(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    srv = MQSentinelServer(s)
    res = srv.dispatch(token="dev", tool="health", params={})
    assert res["status"] == "ok"
    assert verify_chain(s.audit.log_path) is True


def test_unknown_tool_rejected_and_audited(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    srv = MQSentinelServer(s)
    with pytest.raises(LookupError):
        srv.dispatch(token="dev", tool="nope", params={})
    assert s.audit.log_path.exists()
    assert verify_chain(s.audit.log_path) is True
