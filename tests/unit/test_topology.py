from __future__ import annotations

from collections.abc import Sequence

from mq_sentinel.connectors.base import MQSCResult
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.topology.detect import TopologyDetector


class _FakeConn:
    def __init__(self, mqsc: dict[str, MQSCResult], shell: dict[str, str]) -> None:
        self._mqsc = mqsc
        self._shell = shell

    def connect(self, entry: QMEntry, credential: MQCredential) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def execute_mqsc(self, command: str) -> MQSCResult:
        return self._mqsc.get(command, MQSCResult(command=command, raw="", rows=[]))

    def execute_shell(self, argv: Sequence[str]) -> str:
        return self._shell.get(" ".join(argv), "")


def test_classify_zos() -> None:
    conn = _FakeConn(
        {
            "DISPLAY QMGR PLATFORM": MQSCResult(
                command="x", rows=[{"PLATFORM": "MVS"}], raw="PLATFORM(MVS)"
            ),
        },
        {},
    )
    fp = TopologyDetector(conn).detect()
    assert fp.topology == Topology.ZOS_QSG
    assert fp.is_zos


def test_classify_native_ha() -> None:
    conn = _FakeConn(
        {"DISPLAY QMSTATUS": MQSCResult(command="x", rows=[], raw="NATIVEHA(YES) INSYNC")},
        {},
    )
    fp = TopologyDetector(conn).detect()
    assert fp.topology == Topology.NATIVE_HA
    assert fp.is_native_ha


def test_classify_rdqm() -> None:
    conn = _FakeConn({}, {"rdqmstatus": "Node: rdqm-1\nDRBD role: Primary"})
    fp = TopologyDetector(conn).detect()
    assert fp.topology == Topology.RDQM
    assert fp.is_rdqm


def test_classify_standalone_default() -> None:
    fp = TopologyDetector(_FakeConn({}, {})).detect()
    assert fp.topology == Topology.STANDALONE


def test_classify_clustered() -> None:
    conn = _FakeConn(
        {
            "DISPLAY CLUSQMGR(*) CLUSTER": MQSCResult(
                command="x", rows=[{"CLUSQMGR": "QM1"}], raw="CLUSQMGR(QM1) CLUSTER(C1)"
            ),
        },
        {},
    )
    fp = TopologyDetector(conn).detect()
    assert fp.topology == Topology.TRADITIONAL_CLUSTER
    assert fp.is_clustered
