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
        }

    def lookup_reason(self, reason: int, mq_version: str | None = None) -> list[KCDocRef]:
        refs = self._by_reason.get(reason, [])
        return self._filter_version(refs, mq_version)

    def lookup_amq(self, code: str, mq_version: str | None = None) -> list[KCDocRef]:
        refs = self._by_amq.get(code.upper(), [])
        return self._filter_version(refs, mq_version)

    @staticmethod
    def _filter_version(refs: list[KCDocRef], version: str | None) -> list[KCDocRef]:
        if not version:
            return list(refs)
        major_minor = ".".join(version.split(".")[:2])
        return [r for r in refs if major_minor in r.mq_versions] or list(refs)
