"""IBM Knowledge Center doc registry.

Curated mapping from (mq_version, reason_code) -> KC documentation URL.
Every URL is validated against the allowed_doc_hosts allowlist.
"""

from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_HOSTS = ("www.ibm.com",)


@dataclass(frozen=True, slots=True)
class KCDocRef:
    title: str
    url: str
    mq_versions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not any(f"://{h}/" in self.url for h in _ALLOWED_HOSTS):
            raise ValueError(f"KC URL host not in allowlist: {self.url}")


class KCRegistry:
    """Seeded with Phase 1 reason-code references. Expand per phase."""

    def __init__(self) -> None:
        self._by_reason: dict[int, list[KCDocRef]] = {
            2035: [
                KCDocRef(
                    title="2035 (07F3) MQRC_NOT_AUTHORIZED",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2033: [
                KCDocRef(
                    title="2033 (07F1) MQRC_NO_MSG_AVAILABLE",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2033-07f1-rc2033-mqrc-no-msg-available",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2080: [
                KCDocRef(
                    title="2080 (0820) MQRC_TRUNCATED_MSG_FAILED",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2080-0820-rc2080-mqrc-truncated-msg-failed",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2030: [
                KCDocRef(
                    title="2030 (07EE) MQRC_MSG_TOO_BIG_FOR_Q",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2030-07ee-rc2030-mqrc-msg-too-big-q",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2051: [
                KCDocRef(
                    title="2051 (0803) MQRC_PUT_INHIBITED",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2051-0803-rc2051-mqrc-put-inhibited",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2053: [
                KCDocRef(
                    title="2053 (0805) MQRC_Q_FULL",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2053-0805-rc2053-mqrc-q-full",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2079: [
                KCDocRef(
                    title="2079 (081F) MQRC_TRUNCATED_MSG_ACCEPTED",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2079-081f-rc2079-mqrc-truncated-msg-accepted",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            # --- Connectivity / availability (the most common on-call pages) ---
            2009: [
                KCDocRef(
                    title="2009 (07D9) MQRC_CONNECTION_BROKEN",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2009-07d9-rc2009-mqrc-connection-broken",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2058: [
                KCDocRef(
                    title="2058 (080A) MQRC_Q_MGR_NAME_ERROR",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2058-080a-rc2058-mqrc-q-mgr-name-error",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2059: [
                KCDocRef(
                    title="2059 (080B) MQRC_Q_MGR_NOT_AVAILABLE",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2059-080b-rc2059-mqrc-q-mgr-not-available",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2161: [
                KCDocRef(
                    title="2161 (0871) MQRC_Q_MGR_QUIESCING",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2161-0871-rc2161-mqrc-q-mgr-quiescing",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2162: [
                KCDocRef(
                    title="2162 (0872) MQRC_Q_MGR_STOPPING",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2162-0872-rc2162-mqrc-q-mgr-stopping",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            # --- Object resolution ---
            2085: [
                KCDocRef(
                    title="2085 (0825) MQRC_UNKNOWN_OBJECT_NAME",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2085-0825-rc2085-mqrc-unknown-object-name",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2087: [
                KCDocRef(
                    title="2087 (0827) MQRC_UNKNOWN_REMOTE_Q_MGR",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2087-0827-rc2087-mqrc-unknown-remote-q-mgr",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2189: [
                KCDocRef(
                    title="2189 (088D) MQRC_CLUSTER_RESOLUTION_ERROR",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2189-088d-rc2189-mqrc-cluster-resolution-error",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            # --- Inhibited / capacity ---
            2016: [
                KCDocRef(
                    title="2016 (07E0) MQRC_GET_INHIBITED",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2016-07e0-rc2016-mqrc-get-inhibited",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2192: [
                KCDocRef(
                    title="2192 (0890) MQRC_PAGESET_FULL (STORAGE_MEDIUM_FULL)",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2192-0890-rc2192-mqrc-storage-medium-full",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2042: [
                KCDocRef(
                    title="2042 (07FA) MQRC_OBJECT_IN_USE",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2042-07fa-rc2042-mqrc-object-in-use",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            # --- TLS / security ---
            2393: [
                KCDocRef(
                    title="2393 (0959) MQRC_SSL_INITIALIZATION_ERROR",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2393-0959-rc2393-mqrc-ssl-initialization-error",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2397: [
                KCDocRef(
                    title="2397 (095D) MQRC_JSSE_ERROR",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2397-095d-rc2397-mqrc-jsse-error",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            2400: [
                KCDocRef(
                    title="2400 (0960) MQRC_UNSUPPORTED_CIPHER_SUITE",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2400-0960-rc2400-mqrc-unsupported-cipher-suite",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
        }
        self._by_amq: dict[str, list[KCDocRef]] = {
            "AMQ9202": [
                KCDocRef(
                    title="AMQ9202E: Remote host not available",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9202e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9208": [
                KCDocRef(
                    title="AMQ9208E: Error on receive from host",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9208e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9503": [
                KCDocRef(
                    title="AMQ9503E: Channel negotiation failed",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9503e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9456": [
                KCDocRef(
                    title="AMQ9456E: Update not received from full repository",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9456e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9484": [
                KCDocRef(
                    title="AMQ9484E: Cluster channel error",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9484e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9508": [
                KCDocRef(
                    title="AMQ9508E: Program cannot connect to queue manager",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9508e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ9764": [
                KCDocRef(
                    title="AMQ9764E: Cluster send channel not started",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq9764e",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "AMQ3209": [
                KCDocRef(
                    title="AMQ3209I: Native HA replica is not in sync",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=messages-amq3209i",
                    mq_versions=("9.3", "9.4"),
                ),
            ],
        }
        self._topics: dict[str, list[KCDocRef]] = {
            "cluster_partial_repository": [
                KCDocRef(
                    title="Repositories in a cluster",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=clusters-cluster-repositories",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "cluster_refresh": [
                KCDocRef(
                    title="REFRESH CLUSTER (refresh cluster)",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=commands-refresh-cluster",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "cluster_stale_entry": [
                KCDocRef(
                    title="Troubleshooting cluster problems",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=clusters-troubleshooting",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "native_ha_overview": [
                KCDocRef(
                    title="Native HA",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=ha-native",
                    mq_versions=("9.3", "9.4"),
                ),
            ],
            "native_ha_quorum_lost": [
                KCDocRef(
                    title="Troubleshooting Native HA",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=ha-troubleshooting-native",
                    mq_versions=("9.3", "9.4"),
                ),
            ],
            "native_ha_log_replication": [
                KCDocRef(
                    title="Native HA log replication",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=native-ha-log-replication",
                    mq_versions=("9.3", "9.4"),
                ),
            ],
            "native_ha_crr": [
                KCDocRef(
                    title="Cross-region replication for Native HA",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=ha-cross-region-replication",
                    mq_versions=("9.4",),
                ),
            ],
            "rdqm_overview": [
                KCDocRef(
                    title="RDQM high availability",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=availability-rdqm-high",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "rdqm_troubleshooting": [
                KCDocRef(
                    title="Troubleshooting RDQM",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=rdqm-troubleshooting",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "rdqm_split_brain": [
                KCDocRef(
                    title="Resolving DRBD split-brain on RDQM",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=rdqm-resolving-drbd-split-brain",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "rdqm_pacemaker": [
                KCDocRef(
                    title="Pacemaker on RDQM",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=rdqm-pacemaker",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "zos_qsg_overview": [
                KCDocRef(
                    title="Queue sharing groups (z/OS)",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=zos-queue-sharing-groups",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "zos_chin": [
                KCDocRef(
                    title="The channel initiator on z/OS",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=zos-channel-initiator",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "zos_pageset": [
                KCDocRef(
                    title="Managing page sets on z/OS",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=zos-managing-page-sets",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "zos_bufferpool": [
                KCDocRef(
                    title="Buffer pools on z/OS",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=zos-buffer-pools",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "zos_cf_structure": [
                KCDocRef(
                    title="Coupling facility structures (z/OS)",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=zos-coupling-facility-structures",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "miqm_overview": [
                KCDocRef(
                    title="Multi-instance queue managers",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=availability-multi-instance-queue-managers",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
            "miqm_troubleshooting": [
                KCDocRef(
                    title="Troubleshooting multi-instance queue managers",
                    url="https://www.ibm.com/docs/en/ibm-mq/9.4?topic=availability-troubleshooting-multi-instance",
                    mq_versions=("9.2", "9.3", "9.4"),
                ),
            ],
        }

    def lookup_reason(self, reason: int, mq_version: str | None = None) -> list[KCDocRef]:
        refs = self._by_reason.get(reason, [])
        return self._filter_version(refs, mq_version)

    def lookup_amq(self, code: str, mq_version: str | None = None) -> list[KCDocRef]:
        refs = self._by_amq.get(code.upper(), [])
        return self._filter_version(refs, mq_version)

    def lookup_topic(self, topic: str, mq_version: str | None = None) -> list[KCDocRef]:
        refs = self._topics.get(topic, [])
        return self._filter_version(refs, mq_version)

    def all_refs(self) -> list[KCDocRef]:
        """Every KCDocRef in the registry, de-duplicated by URL.

        Used by the dead-link verification job and structural-validity tests.
        """
        seen: dict[str, KCDocRef] = {}
        for bucket in (self._by_reason, self._by_amq, self._topics):
            for refs in bucket.values():
                for ref in refs:
                    seen.setdefault(ref.url, ref)
        return list(seen.values())

    def reason_codes(self) -> list[int]:
        """Sorted list of every reason code covered."""
        return sorted(self._by_reason)

    def amq_codes(self) -> list[str]:
        """Sorted list of every AMQ message code covered."""
        return sorted(self._by_amq)

    @staticmethod
    def _filter_version(refs: list[KCDocRef], version: str | None) -> list[KCDocRef]:
        if not version:
            return list(refs)
        major_minor = ".".join(version.split(".")[:2])
        return [r for r in refs if major_minor in r.mq_versions] or list(refs)
