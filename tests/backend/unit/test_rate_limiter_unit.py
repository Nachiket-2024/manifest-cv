# tests/backend/unit/test_rate_limiter.py
import pytest
from unittest.mock import AsyncMock

from backend.app.auth.security.rate_limiter_service import rate_limiter_service

MODULE = "backend.app.auth.security.rate_limiter_service"


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    """Duck-typed stand-in for fastapi.Request — the decorator only reads
    `.client.host`, and locates it via the `request` kwarg (not isinstance),
    so a real Request (whose `.client` is a read-only computed property) is
    unnecessary and awkward to construct here."""

    def __init__(self, ip):
        self.client = _FakeClient(ip)


def _make_request(ip="1.2.3.4"):
    return _FakeRequest(ip)


@pytest.mark.asyncio
async def test_rate_limited_allows_request_within_ip_limit(mocker):
    mocker.patch(f"{MODULE}.redis_client.get", new_callable=AsyncMock, return_value=None)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)

    @rate_limiter_service.rate_limited("test_endpoint")
    async def handler(request):
        return "ok"

    result = await handler(request=_make_request())

    assert result == "ok"


@pytest.mark.asyncio
async def test_rate_limited_blocks_when_ip_limit_exceeded(mocker):
    mocker.patch(
        f"{MODULE}.redis_client.get",
        new_callable=AsyncMock,
        return_value=rate_limiter_service.MAX_REQUESTS_PER_WINDOW,
    )

    @rate_limiter_service.rate_limited("test_endpoint")
    async def handler(request):
        return "ok"

    response = await handler(request=_make_request())

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_blocks_when_account_limit_exceeded_even_under_ip_limit(mocker):
    # Simulate a distributed attack: every individual IP is fresh (under the
    # per-IP limit) but all requests target the same account, which is what
    # a per-IP-only limiter is blind to.
    async def fake_get(key):
        if ":account:" in key:
            return rate_limiter_service.MAX_REQUESTS_PER_WINDOW
        return None

    mocker.patch(f"{MODULE}.redis_client.get", side_effect=fake_get)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)

    class _Payload:
        email = "victim@example.com"

    @rate_limiter_service.rate_limited("test_endpoint", account_key_func=lambda kwargs: kwargs["payload"].email)
    async def handler(request, payload):
        return "ok"

    response = await handler(request=_make_request(ip="9.9.9.9"), payload=_Payload())

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_ip_and_account_keys_are_independent(mocker):
    recorded_keys = []

    async def fake_get(key):
        recorded_keys.append(key)
        return None

    mocker.patch(f"{MODULE}.redis_client.get", side_effect=fake_get)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)

    class _Payload:
        email = "user@example.com"

    @rate_limiter_service.rate_limited("test_endpoint", account_key_func=lambda kwargs: kwargs["payload"].email)
    async def handler(request, payload):
        return "ok"

    await handler(request=_make_request(ip="5.5.5.5"), payload=_Payload())

    assert "test_endpoint:ip:5.5.5.5" in recorded_keys
    assert "test_endpoint:account:user@example.com" in recorded_keys


@pytest.mark.asyncio
async def test_rate_limited_account_extractor_failure_does_not_break_request(mocker):
    mocker.patch(f"{MODULE}.redis_client.get", new_callable=AsyncMock, return_value=None)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)

    def broken_extractor(kwargs):
        raise KeyError("payload")

    @rate_limiter_service.rate_limited("test_endpoint", account_key_func=broken_extractor)
    async def handler(request):
        return "ok"

    result = await handler(request=_make_request())

    assert result == "ok"


@pytest.mark.asyncio
async def test_rate_limited_account_extractor_failure_is_logged(mocker):
    # A silently-skipped account_key_func failure means per-account
    # brute-force protection quietly stops applying with no signal that
    # anything changed — this must be logged so it's visible.
    mocker.patch(f"{MODULE}.redis_client.get", new_callable=AsyncMock, return_value=None)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)
    warning_mock = mocker.patch(f"{MODULE}.logger.warning")

    def broken_extractor(kwargs):
        raise KeyError("payload")

    @rate_limiter_service.rate_limited("test_endpoint", account_key_func=broken_extractor)
    async def handler(request):
        return "ok"

    await handler(request=_make_request())

    warning_mock.assert_called_once()
    assert "test_endpoint" in warning_mock.call_args.args


@pytest.mark.asyncio
async def test_record_request_fails_closed_on_redis_exception(mocker):
    # Deliberate, documented tradeoff (see docs/security/decisions.md): a
    # Redis outage must deny the request rather than silently allow it — the
    # safer default for an auth-focused template, even though it means a
    # Redis outage takes down every rate-limited route, not just caching.
    mocker.patch(f"{MODULE}.redis_client.get", side_effect=ConnectionError("redis unreachable"))
    error_mock = mocker.patch(f"{MODULE}.logger.error")

    allowed = await rate_limiter_service.record_request("some:key")

    assert allowed is False
    error_mock.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limited_returns_429_on_redis_outage_rather_than_letting_request_through(mocker):
    mocker.patch(f"{MODULE}.redis_client.get", side_effect=ConnectionError("redis unreachable"))

    @rate_limiter_service.rate_limited("test_endpoint")
    async def handler(request):
        return "ok"

    response = await handler(request=_make_request())

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_skips_account_check_when_extractor_returns_none(mocker):
    get_mock = mocker.patch(f"{MODULE}.redis_client.get", new_callable=AsyncMock, return_value=None)
    mocker.patch(f"{MODULE}.redis_client.set", new_callable=AsyncMock)

    @rate_limiter_service.rate_limited("test_endpoint", account_key_func=lambda kwargs: None)
    async def handler(request):
        return "ok"

    result = await handler(request=_make_request())

    assert result == "ok"
    # Only the IP key should have been checked — no ":account:" lookup at all
    assert all(":account:" not in call.args[0] for call in get_mock.call_args_list)
