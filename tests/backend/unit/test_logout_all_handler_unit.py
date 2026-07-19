# tests/backend/unit/test_logout_all_handler_unit.py
import pytest
from unittest.mock import AsyncMock

from backend.app.auth.logout_all.logout_all_handler import logout_all_handler

MODULE = "backend.app.auth.logout_all.logout_all_handler"


def _set_cookie_headers(response) -> list[str]:
    return [value.decode() for key, value in response.raw_headers if key == b"set-cookie"]


@pytest.mark.asyncio
async def test_logout_all_without_refresh_token_returns_400(mocker):
    verify_mock = mocker.patch(f"{MODULE}.jwt_service.verify_token", new_callable=AsyncMock)

    response = await logout_all_handler.handle_logout_all(None)

    assert response.status_code == 400
    verify_mock.assert_not_called()


@pytest.mark.asyncio
async def test_logout_all_with_invalid_token_returns_400(mocker):
    mocker.patch(f"{MODULE}.jwt_service.verify_token", new_callable=AsyncMock, return_value=None)

    response = await logout_all_handler.handle_logout_all("bad-token")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_logout_all_with_no_active_sessions_returns_400(mocker):
    mocker.patch(
        f"{MODULE}.jwt_service.verify_token", new_callable=AsyncMock, return_value={"email": "user@example.com"}
    )
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_all_tokens_for_user", new_callable=AsyncMock, return_value=0)

    response = await logout_all_handler.handle_logout_all("valid-token")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_logout_all_success_clears_both_cookies(mocker):
    mocker.patch(
        f"{MODULE}.jwt_service.verify_token", new_callable=AsyncMock, return_value={"email": "user@example.com"}
    )
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_all_tokens_for_user", new_callable=AsyncMock, return_value=3)

    response = await logout_all_handler.handle_logout_all("valid-token")

    assert response.status_code == 200
    headers = _set_cookie_headers(response)
    assert any(h.startswith("access_token=") for h in headers)
    assert any(h.startswith("refresh_token=") for h in headers)


@pytest.mark.asyncio
async def test_logout_all_clears_refresh_token_cookie_with_matching_auth_path(mocker):
    # Same regression guard as logout_handler: the delete must specify
    # path="/auth" to actually clear the cookie token_cookie_handler set.
    mocker.patch(
        f"{MODULE}.jwt_service.verify_token", new_callable=AsyncMock, return_value={"email": "user@example.com"}
    )
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_all_tokens_for_user", new_callable=AsyncMock, return_value=1)

    response = await logout_all_handler.handle_logout_all("valid-token")

    headers = _set_cookie_headers(response)
    refresh_header = next(h for h in headers if h.startswith("refresh_token="))
    assert "Path=/auth" in refresh_header
