"""Role-based access control. Scopes are (role, action, environment)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mq_sentinel.auth.oidc import Principal


class Action(StrEnum):
    READ_NONPROD = "read:nonprod"
    READ_PROD = "read:prod"
    AUDIT_VIEW = "audit:view"


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    grants: frozenset[Action]


_ROLES: dict[str, Role] = {
    "nonprod-read": Role("nonprod-read", frozenset({Action.READ_NONPROD})),
    "prod-read": Role("prod-read", frozenset({Action.READ_NONPROD, Action.READ_PROD})),
    "admin-audit": Role(
        "admin-audit",
        frozenset({Action.READ_NONPROD, Action.READ_PROD, Action.AUDIT_VIEW}),
    ),
}


class AuthorizationError(PermissionError):
    """Raised when a principal lacks the required action."""


def authorize(principal: Principal, action: Action) -> None:
    allowed: set[Action] = set()
    for role_name in principal.roles:
        role = _ROLES.get(role_name)
        if role is not None:
            allowed.update(role.grants)
    if action not in allowed:
        raise AuthorizationError(
            f"principal {principal.subject!r} lacks required action {action.value!r}"
        )
