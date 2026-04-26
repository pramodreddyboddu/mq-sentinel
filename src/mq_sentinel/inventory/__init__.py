"""Queue Manager inventory (pluggable backend)."""

from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory, InventoryRegistry

__all__ = ["InMemoryInventory", "InventoryRegistry", "QMEntry", "Topology"]
