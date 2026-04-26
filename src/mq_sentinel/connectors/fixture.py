"""Fixture-based connector for tests and demo sandbox (no live MQ required)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import orjson

from mq_sentinel.connectors.base import MQConnectionError, MQSCResult
from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.security.allowlist import assert_mqsc_allowed, assert_shell_allowed


class FixtureConnector:
    """Serves recorded MQSC/shell outputs from a directory of JSON files."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._dir = fixtures_dir
        self._connected = False
        self._qm: str | None = None

    def connect(self, entry: QMEntry, credential: MQCredential) -> None:
        if not self._dir.exists():
            raise MQConnectionError(f"fixtures directory {self._dir} missing")
        _ = credential
        self._qm = entry.qm_name
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._qm = None

    def execute_mqsc(self, command: str) -> MQSCResult:
        if not self._connected:
            raise MQConnectionError("not connected")
        assert_mqsc_allowed(command)
        key = self._fingerprint(command)
        fixture_path = self._dir / "mqsc" / f"{key}.json"
        if not fixture_path.exists():
            return MQSCResult(command=command, raw="", rows=[], completion_code=0)
        data = orjson.loads(fixture_path.read_bytes())
        return MQSCResult(
            command=command,
            rows=data.get("rows", []),
            raw=data.get("raw", ""),
            reason_code=data.get("reason_code"),
            completion_code=data.get("completion_code"),
        )

    def execute_shell(self, argv: Sequence[str]) -> str:
        if not self._connected:
            raise MQConnectionError("not connected")
        assert_shell_allowed(argv)
        key = "_".join(argv).replace("/", "_").replace(" ", "_")
        fixture_path = self._dir / "shell" / f"{key}.txt"
        if not fixture_path.exists():
            return ""
        return fixture_path.read_text(encoding="utf-8")

    @staticmethod
    def _fingerprint(command: str) -> str:
        return (
            command.strip()
            .upper()
            .replace(" ", "_")
            .replace("(", "_")
            .replace(")", "_")
            .replace("*", "ALL")
            .replace("'", "")
            .replace("/", "_")
        )
