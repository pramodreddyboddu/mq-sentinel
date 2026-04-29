from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.rdqm import match_rdqm_findings


def test_empty_input_no_findings() -> None:
    assert match_rdqm_findings({}, KCRegistry()) == []


def test_pacemaker_quorum_lost_critical() -> None:
    raw = {
        "pacemaker": {
            "total_nodes": 3,
            "online_nodes": ["a"],
            "offline_nodes": ["b", "c"],
            "failed_resources": [],
        }
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    crits = [f for f in findings if "quorum lost" in f.issue]
    assert crits and crits[0].severity.value == "CRITICAL"


def test_offline_nodes_high() -> None:
    raw = {
        "pacemaker": {
            "total_nodes": 3,
            "online_nodes": ["a", "b"],
            "offline_nodes": ["c"],
            "failed_resources": [],
        }
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    bad = [f for f in findings if "offline node" in f.issue]
    assert bad and bad[0].severity.value == "HIGH"


def test_failed_pacemaker_resource_high() -> None:
    raw = {
        "pacemaker": {
            "total_nodes": 3,
            "online_nodes": ["a", "b", "c"],
            "offline_nodes": [],
            "failed_resources": [{"resource": "DEMO_QM-monitor", "node": "c", "status": "FAILED"}],
        }
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    assert any("DEMO_QM-monitor" in f.issue for f in findings)


def test_drbd_split_brain_critical() -> None:
    raw = {
        "drbd": [{"resource": "DEMO_QM", "split_brain": True}],
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    sb = [f for f in findings if "split-brain" in f.issue]
    assert sb and sb[0].severity.value == "CRITICAL"
    assert any("www.ibm.com" in d.url for d in sb[0].doc_refs)


def test_drbd_disconnected_high() -> None:
    raw = {
        "drbd": [
            {
                "resource": "DEMO_QM",
                "connection_state": "WFConnection",
                "disk_state": "UpToDate",
                "peer_disk_state": "UpToDate",
            }
        ]
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    assert any("WFConnection" in f.issue and f.severity.value == "HIGH" for f in findings)


def test_drbd_sync_target_medium() -> None:
    raw = {
        "drbd": [
            {
                "resource": "DEMO_QM",
                "connection_state": "SyncTarget",
                "disk_state": "UpToDate",
                "peer_disk_state": "UpToDate",
            }
        ]
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    assert any("SyncTarget" in f.issue and f.severity.value == "MEDIUM" for f in findings)


def test_drbd_inconsistent_disk_high() -> None:
    raw = {
        "drbd": [
            {
                "resource": "DEMO_QM_LOGS",
                "connection_state": "Connected",
                "disk_state": "Inconsistent",
                "peer_disk_state": "UpToDate",
            }
        ]
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    assert any("Inconsistent" in f.issue and f.severity.value == "HIGH" for f in findings)


def test_rdqm_no_running_node_critical() -> None:
    raw = {
        "rdqm_status": {"qm_name": "Q", "ha_state": "Offline", "running_node": ""},
    }
    findings = match_rdqm_findings(raw, KCRegistry())
    assert any("no running node" in f.issue and f.severity.value == "CRITICAL" for f in findings)


def test_fix_steps_are_read_only() -> None:
    raw = {
        "pacemaker": {
            "total_nodes": 3,
            "online_nodes": ["a"],
            "offline_nodes": ["b", "c"],
            "failed_resources": [{"resource": "x", "node": "c", "status": "FAILED"}],
        },
        "drbd": [
            {"resource": "DEMO_QM", "split_brain": True},
            {
                "resource": "L",
                "connection_state": "WFConnection",
                "disk_state": "Inconsistent",
                "peer_disk_state": "UpToDate",
            },
        ],
        "rdqm_status": {"qm_name": "Q", "ha_state": "Offline", "running_node": ""},
    }
    for f in match_rdqm_findings(raw, KCRegistry()):
        for step in f.fix_steps:
            for verb in (
                "pcs ",
                "crm ",
                "drbdadm primary",
                "drbdadm secondary",
                "drbdadm connect",
                "drbdadm disconnect",
                "drbdadm invalidate",
                "drbdadm new-current-uuid",
                "rdqmadm",
                "ALTER ",
                "DELETE ",
                "DEFINE ",
                "REFRESH ",
                "RESET ",
                "CLEAR ",
                "SET ",
                "MOVE ",
                "START ",
                "STOP ",
                "RESUME ",
                "SUSPEND ",
                "RECOVER ",
                "FAILOVER ",
            ):
                assert verb.lower() not in step.lower(), f"destructive verb in: {step}"
