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
