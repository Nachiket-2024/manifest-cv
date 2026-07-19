# tests/backend/unit/test_email_tasks_unit.py
#
# Regression guard for email delivery reliability: send_email_task previously
# caught every exception and returned False, which SimpleRetryMiddleware
# never sees (it only reacts to a raised exception) — so a transient SMTP
# failure silently dropped the email with no retry. The fix makes the task
# raise on failure (after logging) so the middleware can re-enqueue it, up
# to max_retries, while every attempt still leaves a full traceback in the
# logs.
import pytest
from unittest.mock import AsyncMock, patch

from redis.exceptions import ResponseError
from taskiq import SimpleRetryMiddleware

from backend.app.taskiq_tasks.email_tasks import send_email_task, broker

MODULE = "backend.app.taskiq_tasks.email_tasks"


@pytest.mark.asyncio
async def test_send_email_task_returns_true_on_success(mocker):
    mocker.patch(f"{MODULE}.email_sender.send", new_callable=AsyncMock)

    result = await send_email_task(to_email="user@example.com", subject="Hi", body="Body")

    assert result is True


@pytest.mark.asyncio
async def test_send_email_task_logs_and_reraises_on_send_failure(mocker):
    mocker.patch(f"{MODULE}.email_sender.send", new_callable=AsyncMock, side_effect=RuntimeError("SMTP down"))
    error_mock = mocker.patch(f"{MODULE}.logger.error")

    with pytest.raises(RuntimeError):
        await send_email_task(to_email="user@example.com", subject="Hi", body="Body")

    error_mock.assert_called_once()


def test_broker_has_retry_middleware_configured():
    assert any(isinstance(m, SimpleRetryMiddleware) for m in broker.middlewares)


def test_send_email_task_is_labeled_to_retry_on_error():
    assert send_email_task.labels.get("retry_on_error") is True
    assert send_email_task.labels.get("max_retries") == 3


def test_broker_uses_mkstream_for_deterministic_group_creation():
    """taskiq spawns multiple worker processes (default: 2), each independently
    calling broker.startup() on a fresh Redis instance. mkstream=True makes the
    stream + consumer group creation a single atomic XGROUP CREATE ... MKSTREAM,
    so there's no window where the stream exists but the group doesn't (or vice
    versa) for a concurrent XREADGROUP to race against."""
    assert broker.mkstream is True


@pytest.mark.asyncio
async def test_broker_startup_survives_concurrent_group_creation_race():
    """Regression guard for the fresh-Redis startup race previously documented
    in docs/concerns/README.md. Every worker process calls
    broker.startup() -> XGROUP CREATE ... MKSTREAM independently; Redis raises
    BUSYGROUP for whichever process loses that race. The broker must swallow
    it (not propagate) so a losing process doesn't crash-loop."""
    with patch("taskiq_redis.redis_broker.Redis") as redis_cls:
        redis_conn = AsyncMock()
        redis_conn.xgroup_create = AsyncMock(
            side_effect=ResponseError("BUSYGROUP Consumer Group name already exists")
        )
        redis_cls.return_value.__aenter__.return_value = redis_conn

        await broker._declare_consumer_group()  # must not raise
