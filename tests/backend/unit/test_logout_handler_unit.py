# tests/backend/unit/test_logout_handler_unit.py
import pytest
from unittest.mock import AsyncMock

from backend.app.auth.logout.logout_handler import logout_handler

MODULE = "backend.app.auth.logout.logout_handler"


def _set_cookie_headers(response) -> list[str]:
    return [value.decode() for key, value in response.raw_headers if key == b"set-cookie"]


@pytest.mark.asyncio
async def test_logout_without_refresh_token_returns_400(mocker):
    revoke_mock = mocker.patch(f"{MODULE}.refresh_token_service.revoke_refresh_token", new_callable=AsyncMock)

    response = await logout_handler.handle_logout(None)

    assert response.status_code == 400
    revoke_mock.assert_not_called()


@pytest.mark.asyncio
async def test_logout_with_invalid_token_returns_400_without_clearing_cookies(mocker):
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_refresh_token", new_callable=AsyncMock, return_value=False)

    response = await logout_handler.handle_logout("bad-token")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_logout_success_clears_both_cookies(mocker):
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_refresh_token", new_callable=AsyncMock, return_value=True)

    response = await logout_handler.handle_logout("valid-token")

    assert response.status_code == 200
    headers = _set_cookie_headers(response)
    assert any(h.startswith("access_token=") for h in headers)
    assert any(h.startswith("refresh_token=") for h in headers)


@pytest.mark.asyncio
async def test_logout_clears_refresh_token_cookie_with_matching_auth_path(mocker):
    # Regression guard: refresh_token is set with path="/auth"
    # (token_cookie_handler.py). A delete_cookie call without the same path
    # creates a *different* cookie the browser expires immediately, leaving
    # the real, still-valid "/auth"-scoped refresh_token cookie behind.
    mocker.patch(f"{MODULE}.refresh_token_service.revoke_refresh_token", new_callable=AsyncMock, return_value=True)

    response = await logout_handler.handle_logout("valid-token")

    headers = _set_cookie_headers(response)
    refresh_header = next(h for h in headers if h.startswith("refresh_token="))
    assert "Path=/auth" in refresh_header
