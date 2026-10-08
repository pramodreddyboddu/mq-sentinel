"""Secrets backend interface. Credentials never persisted in inventory or config."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MQCredential:
    user: str
    password: str = field(repr=False)
    keystore_path: str | None = None
    keystore_password: str | None = field(default=None, repr=False)
    cert_label: str | None = None

    def __str__(self) -> str:  # defensive: never leak via str()
        return f"MQCredential(user={self.user!r}, password=<redacted>)"


class SecretsBackend(Protocol):
    def resolve(self, secret_ref: str) -> MQCredential: ...
