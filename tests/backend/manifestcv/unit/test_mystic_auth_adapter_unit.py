# tests/backend/manifestcv/unit/test_mystic_auth_adapter_unit.py
#
# mystic_auth_adapter is the only door ManifestCV's own feature code is
# allowed to use into mystic-auth's identity system (see
# backend/app/mystic_auth_adapter/__init__.py). These tests pin down its
# two responsibilities: re-exporting mystic-auth's get_current_user
# unchanged, and resolving a DB user id from an email — the translation
# every owner-scoped ManifestCV route depends on.
import pytest
from unittest.mock import AsyncMock

from backend.app.mystic_auth_adapter import get_current_user, get_user_id_by_email
from backend.app.mystic_auth_adapter.current_user import get_current_user as current_user_direct
from backend.app.auth.current_user.current_user_dependency import get_current_user as mystic_get_current_user

MODULE = "backend.app.mystic_auth_adapter.user_lookup"


class _FakeUser:
    def __init__(self, id: int):
        self.id = id


def test_get_current_user_is_mystic_auths_own_dependency_unchanged():
    # The adapter must not wrap/reimplement authentication — it re-exports
    # mystic-auth's exact dependency object, so every mystic-auth session/
    # cookie/token behavior applies identically to ManifestCV routes.
    assert get_current_user is mystic_get_current_user
    assert current_user_direct is mystic_get_current_user


@pytest.mark.asyncio
async def test_get_user_id_by_email_resolves_id_for_known_user(mocker):
    mocker.patch(f"{MODULE}.user_crud.get_by_email", new_callable=AsyncMock, return_value=_FakeUser(id=42))

    result = await get_user_id_by_email("user@example.com", db=None)

    assert result == 42


@pytest.mark.asyncio
async def test_get_user_id_by_email_returns_none_for_unknown_user():
    # No mock override needed for user_crud here beyond returning None —
    # a caller whose email doesn't resolve to a row must get None, not an
    # exception, so route handlers can turn it into a 404 (see
    # api/application_routes/application_routes.py's _current_user_id).
    from unittest.mock import patch

    with patch(f"{MODULE}.user_crud.get_by_email", new_callable=AsyncMock, return_value=None):
        result = await get_user_id_by_email("nobody@example.com", db=None)

    assert result is None
