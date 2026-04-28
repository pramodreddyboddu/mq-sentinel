"""OIDC token verification (JWT via JWKS).

Two implementations:
- StubOIDCVerifier: dev-only, refuses production.
- RealOIDCVerifier: authlib-based JWKS verification with caching.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from authlib.jose import JsonWebKey, JsonWebToken  # type: ignore[import-untyped]
from authlib.jose.errors import JoseError  # type: ignore[import-untyped]


class TokenVerificationError(PermissionError):
    """Raised on any token validation failure. Never echoes the token back."""


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
            raise TokenVerificationError("empty token")
        return self._principal


_DEFAULT_ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "ES384", "PS256")


class RealOIDCVerifier:
    """Production OIDC verifier.

    Validates JWT signature, exp, nbf, iss, aud against a JWKS (fetched from
    `jwks_url` or supplied directly via `jwks` for tests / air-gapped use).
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        jwks: dict[str, Any] | None = None,
        roles_claim: str = "roles",
        tenant_claim: str = "tenant",
        leeway_seconds: int = 30,
        cache_ttl_seconds: int = 600,
        http_client: httpx.Client | None = None,
        allowed_algorithms: tuple[str, ...] = _DEFAULT_ALGORITHMS,
    ) -> None:
        if not jwks_url and not jwks:
            raise ValueError("either jwks_url or jwks must be provided")
        if not issuer or not audience:
            raise ValueError("issuer and audience are required")
        self._issuer = issuer
        self._audience = audience
        self._jwks_url = jwks_url
        self._roles_claim = roles_claim
        self._tenant_claim = tenant_claim
        self._leeway = leeway_seconds
        self._ttl = cache_ttl_seconds
        self._algorithms = list(allowed_algorithms)
        self._jwt = JsonWebToken(self._algorithms)
        self._lock = threading.Lock()
        self._cached_jwks: dict[str, Any] | None = jwks
        self._cached_at: float = time.monotonic() if jwks else 0.0
        self._http = http_client or httpx.Client(timeout=5.0)

    def verify(self, token: str) -> Principal:
        if not token or not isinstance(token, str):
            raise TokenVerificationError("missing token")
        try:
            jwks = self._get_jwks()
            key = self._select_key(token, jwks)
            claims = self._jwt.decode(
                token,
                key,
                claims_options=self._claims_options(),
            )
            claims.validate(leeway=self._leeway)
        except (JoseError, ValueError, KeyError) as exc:
            raise TokenVerificationError(
                f"token verification failed: {type(exc).__name__}"
            ) from None

        subject = str(claims.get("sub") or "")
        if not subject:
            raise TokenVerificationError("token missing 'sub' claim")
        tenant = claims.get(self._tenant_claim)
        roles = self._extract_roles(claims)
        return Principal(
            subject=subject,
            tenant=str(tenant) if tenant is not None else None,
            roles=frozenset(roles),
            claims=dict(claims),
        )

    # --- internals ---------------------------------------------------------

    def _claims_options(self) -> dict[str, Any]:
        return {
            "iss": {"essential": True, "value": self._issuer},
            "aud": {"essential": True, "value": self._audience},
            "exp": {"essential": True},
        }

    def _get_jwks(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if self._cached_jwks is not None and (now - self._cached_at) < self._ttl:
                return self._cached_jwks
            if not self._jwks_url:
                if self._cached_jwks is None:
                    raise TokenVerificationError("no JWKS available")
                return self._cached_jwks
            try:
                response = self._http.get(self._jwks_url)
                response.raise_for_status()
                self._cached_jwks = response.json()
                self._cached_at = now
            except (httpx.HTTPError, ValueError) as exc:
                if self._cached_jwks is not None:
                    return self._cached_jwks  # serve stale on transient errors
                raise TokenVerificationError(f"JWKS fetch failed: {type(exc).__name__}") from None
            return self._cached_jwks

    def _select_key(self, token: str, jwks: dict[str, Any]) -> Any:
        try:
            header = self._jwt._jws.deserialize_header(token.split(".")[0].encode())
        except Exception:  # noqa: BLE001 — bad token shape
            # Fall back to letting authlib pick a key.
            return JsonWebKey.import_key_set(jwks)
        kid = header.get("kid") if isinstance(header, dict) else None
        if not kid:
            return JsonWebKey.import_key_set(jwks)
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                if k.get("alg") and k["alg"] not in self._algorithms:
                    raise TokenVerificationError("disallowed signing algorithm")
                return JsonWebKey.import_key(k)
        raise TokenVerificationError("no matching JWK for token kid")

    def _extract_roles(self, claims: dict[str, Any]) -> list[str]:
        raw = claims.get(self._roles_claim)
        if isinstance(raw, list):
            return [str(r) for r in raw if isinstance(r, str)]
        if isinstance(raw, str):
            # Common pattern: space-separated scope or csv role list.
            return [r for r in raw.replace(",", " ").split() if r]
        # Keycloak realm_access fallback
        realm = claims.get("realm_access")
        if isinstance(realm, dict):
            inner = realm.get("roles")
            if isinstance(inner, list):
                return [str(r) for r in inner if isinstance(r, str)]
        return []
