"""Inventory registry protocol + in-memory impl for dev/test."""

from __future__ import annotations

from typing import Protocol

from mq_sentinel.inventory.models import QMEntry


class InventoryRegistry(Protocol):
    def get(self, qm_name: str) -> QMEntry: ...
    def list_for_tenant(self, tenant: str) -> list[QMEntry]: ...


class InMemoryInventory:
    def __init__(self, entries: list[QMEntry] | None = None) -> None:
        self._entries: dict[str, QMEntry] = {e.qm_name: e for e in (entries or [])}

    def get(self, qm_name: str) -> QMEntry:
        try:
            return self._entries[qm_name]
        except KeyError as exc:
            raise LookupError(f"QM {qm_name!r} not in inventory") from exc

    def list_for_tenant(self, tenant: str) -> list[QMEntry]:
        return [e for e in self._entries.values() if e.tenant == tenant]


def load_from_yaml(path: str) -> InMemoryInventory:
    """Load inventory from a YAML file (useful for ConfigMap mounts in K8s)."""
    import yaml
    from mq_sentinel.inventory.models import QMEntry

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    entries = [QMEntry(**item) for item in data.get("qms", [])]
    return InMemoryInventory(entries)


def load_from_multiple(paths: list[str]) -> InMemoryInventory:
    """Load and merge inventory from multiple YAML files (for large org fleets)."""
    import yaml
    from mq_sentinel.inventory.models import QMEntry

    all_entries = []
    for path in paths:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        all_entries.extend([QMEntry(**item) for item in data.get("qms", [])])

    return InMemoryInventory(all_entries)
