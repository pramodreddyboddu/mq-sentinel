"""Tamper-evident audit log: hash-chained append-only JSONL."""

from mq_sentinel.audit.logger import AuditEvent, AuditLogger, verify_chain

__all__ = ["AuditEvent", "AuditLogger", "verify_chain"]
