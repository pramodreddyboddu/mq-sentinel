"""OIDC token verification (JWT via JWKS). Interface + stub implementation.

Phase 1 supplies the interface and an HS-less stub for local dev. The production
implementation uses authlib's JWKSClient against the configured issuer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant: str | None
    roles: frozenset[str] = field(default_factory=frozenset)
    claims: dict[str, object] = field(default_factory=dict)


class OIDCVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class StubOIDCVerifier:
    """Dev-only verifier. Refuses to run in prod (see config.assert_production_safe)."""

    def __init__(self, *, subject: str = "local-dev", roles: frozenset[str] | None = None) -> None:
        self._principal = Principal(
            subject=subject,
            tenant="local",
            roles=roles or frozenset({"nonprod-read"}),
        )

    def verify(self, token: str) -> Principal:
        if not token:
            raise PermissionError("empty token")
        return self._principal
