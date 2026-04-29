"""RealOIDCVerifier — JWT verification with in-memory JWKS.

Generates an RSA keypair per test, signs a JWT, validates with the verifier.
Covers: happy path, expired, wrong issuer, wrong audience, bad signature,
unknown kid, role + tenant extraction, Keycloak-style realm_access fallback.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from authlib.jose import JsonWebKey, JsonWebToken

from mq_sentinel.auth.oidc import (
    Principal,
    RealOIDCVerifier,
    TokenVerificationError,
)


@pytest.fixture
def keypair() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (private_jwk, public_jwks) — RSA 2048."""
    priv = JsonWebKey.generate_key("RSA", 2048, options={"kid": "test-kid"}, is_private=True)
    priv_jwk = priv.as_dict(is_private=True)
    pub_jwk = priv.as_dict(is_private=False)
    pub_jwk["alg"] = "RS256"
    pub_jwk["use"] = "sig"
    return priv_jwk, {"keys": [pub_jwk]}


def _sign(priv_jwk: dict[str, Any], claims: dict[str, Any]) -> str:
    header = {"alg": "RS256", "kid": priv_jwk.get("kid", "test-kid")}
    return JsonWebToken(["RS256"]).encode(header, claims, priv_jwk).decode()


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base: dict[str, Any] = {
        "iss": "https://issuer.example/",
        "aud": "mq-sentinel",
        "sub": "user-123",
        "iat": now,
        "nbf": now - 5,
        "exp": now + 600,
        "tenant": "acme",
        "roles": ["nonprod-read", "prod-read"],
    }
    base.update(overrides)
    return base


def _verifier(jwks: dict[str, Any], **overrides: Any) -> RealOIDCVerifier:
    kw: dict[str, Any] = {
        "issuer": "https://issuer.example/",
        "audience": "mq-sentinel",
        "jwks": jwks,
    }
    kw.update(overrides)
    return RealOIDCVerifier(**kw)


def test_valid_token_returns_principal_with_roles_and_tenant(
    keypair: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    priv, pub = keypair
    token = _sign(priv, _claims())
    p: Principal = _verifier(pub).verify(token)
    assert p.subject == "user-123"
    assert p.tenant == "acme"
    assert p.roles == frozenset({"nonprod-read", "prod-read"})


def test_expired_token_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    priv, pub = keypair
    now = int(time.time())
    token = _sign(priv, _claims(iat=now - 7200, nbf=now - 7200, exp=now - 3600))
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(token)


def test_wrong_issuer_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    priv, pub = keypair
    token = _sign(priv, _claims(iss="https://evil.example/"))
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(token)


def test_wrong_audience_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    priv, pub = keypair
    token = _sign(priv, _claims(aud="other-service"))
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(token)


def test_bad_signature_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    priv, pub = keypair
    token = _sign(priv, _claims())
    # Replace ~16 chars in the middle of the signature with a fixed pattern —
    # guarantees the decoded signature bytes change (a single base64 char flip
    # can hit a same-byte alphabet collision).
    head, payload, sig = token.split(".")
    if len(sig) < 32:
        pytest.skip("signature too short to mutate")
    mid = len(sig) // 2
    tampered = sig[: mid - 8] + ("A" * 16) + sig[mid + 8 :]
    assert tampered != sig
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(f"{head}.{payload}.{tampered}")


def test_unknown_kid_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    _priv, pub = keypair
    other = JsonWebKey.generate_key("RSA", 2048, options={"kid": "unknown"}, is_private=True)
    token = _sign(other.as_dict(is_private=True), _claims())
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(token)


def test_empty_token_rejected(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    _, pub = keypair
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify("")


def test_roles_csv_string_parsed(keypair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    priv, pub = keypair
    token = _sign(priv, _claims(roles="nonprod-read prod-read"))
    p = _verifier(pub).verify(token)
    assert p.roles == frozenset({"nonprod-read", "prod-read"})


def test_keycloak_realm_access_fallback(
    keypair: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    priv, pub = keypair
    claims = _claims()
    del claims["roles"]
    claims["realm_access"] = {"roles": ["admin-audit"]}
    token = _sign(priv, claims)
    p = _verifier(pub).verify(token)
    assert "admin-audit" in p.roles


def test_missing_subject_rejected(
    keypair: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    priv, pub = keypair
    claims = _claims()
    del claims["sub"]
    token = _sign(priv, claims)
    with pytest.raises(TokenVerificationError):
        _verifier(pub).verify(token)


def test_constructor_requires_jwks_or_url() -> None:
    with pytest.raises(ValueError):
        RealOIDCVerifier(issuer="x", audience="y")
