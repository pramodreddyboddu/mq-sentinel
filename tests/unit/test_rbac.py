from __future__ import annotations

import pytest

from mq_sentinel.auth.oidc import Principal
from mq_sentinel.auth.rbac import Action, AuthorizationError, authorize


def _p(*roles: str) -> Principal:
    return Principal(subject="u", tenant="t", roles=frozenset(roles))


def test_nonprod_read_cannot_access_prod() -> None:
    with pytest.raises(AuthorizationError):
        authorize(_p("nonprod-read"), Action.READ_PROD)


def test_prod_read_can_access_both() -> None:
    authorize(_p("prod-read"), Action.READ_PROD)
    authorize(_p("prod-read"), Action.READ_NONPROD)


def test_unknown_role_denied() -> None:
    with pytest.raises(AuthorizationError):
        authorize(_p("nobody"), Action.READ_NONPROD)
