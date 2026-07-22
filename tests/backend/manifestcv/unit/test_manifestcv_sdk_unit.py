# tests/backend/manifestcv/unit/test_manifestcv_sdk_unit.py
#
# app/manifestcv_sdk.py is ManifestCV's own extension surface — the
# counterpart to mystic-auth's app.sdk for glue mystic-auth has no reason
# to provide. Currently just get_user_id_by_email, the translation every
# owner-scoped ManifestCV route depends on to turn mystic-auth's
# get_current_user (email-only) into a DB user_id.
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.manifestcv_sdk import get_user_id_by_email

MODULE = "backend.app.manifestcv_sdk"


class _FakeUser:
    def __init__(self, id: int):
        self.id = id


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
    with patch(f"{MODULE}.user_crud.get_by_email", new_callable=AsyncMock, return_value=None):
        result = await get_user_id_by_email("nobody@example.com", db=None)

    assert result is None
