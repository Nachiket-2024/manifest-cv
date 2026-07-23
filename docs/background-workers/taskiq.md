# Background Workers (Taskiq)

## Purpose

Offloads slow, failure-prone I/O — sending email via SMTP — off the request/response cycle, so a signup/verification/password-reset request returns immediately instead of blocking on a mail server round trip.

## Architecture

`backend/mystic_auth/taskiq_tasks/email_tasks.py` defines a single [Taskiq](https://taskiq-python.github.io/) broker:

```python
broker: AsyncBroker = RedisStreamBroker(url=settings.REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(redis_url=settings.REDIS_URL)
)

@broker.task
async def send_email_task(to_email: str, subject: str, body: str, is_html: bool = True) -> bool:
    ...
```

Redis is both the broker (a Redis Stream) and the result backend — no separate message-queue infrastructure. The `taskiq_worker` container consumes the same broker, running from the identical `docker/backend.Dockerfile` image as the `backend` service, just with a different `command:` (`taskiq worker mystic_auth.taskiq_tasks.email_tasks:broker`, no `--reload` — the worker doesn't need file-watch) — see [Backend Architecture](../architecture/backend.md) for why one image serves three roles (`backend`, `taskiq_worker`, `alembic`).

## Tasks

| Task | Enqueued from | Purpose |
|---|---|---|
| `send_email_task(to_email, subject, body, is_html=True)` | `auth/verify_account/account_verification_service.py`, `auth/password_logic/password_reset_service.py` | Sends the verification email and the password-reset email via Gmail SMTP (`aiosmtplib`) |

`send_email_task` itself doesn't talk to SMTP directly — it delegates to `emails/email_sender.py::email_sender` (an `EmailSender` protocol with one concrete `SMTPEmailSender` implementation). This is a thin seam, not a plugin system: swapping providers (e.g. SES, SendGrid, Postmark) means writing one new class and pointing `email_sender` at it, without touching the Taskiq task or its callers.

Both call sites build the HTML body via `emails/email_template_service.py::render_transactional_email` (a shared template with the app name/support address baked in from settings), then enqueue with `.kiq(...)`:

```python
await send_email_task.kiq(
    to_email=user.email,
    subject="Verify your account",
    body=render_transactional_email(...),
)
```

`.kiq()` returns as soon as the task is enqueued in Redis — the caller (the signup/password-reset request handler) does not wait for the email to actually send.

## Configuration

| Setting | Purpose |
|---|---|
| `REDIS_URL` | Broker + result backend connection |
| `FROM_EMAIL` | SMTP "From" address, also the account authenticating to the SMTP server |
| `GMAIL_APP_PASSWORD` | App password for the `FROM_EMAIL` account (Gmail requires a per-app password for SMTP with 2FA enabled) |
| `SUPPORT_EMAIL` | Optional; used as the email's `Reply-To`, falls back to `FROM_EMAIL` if unset |
| `SMTP_HOST` / `SMTP_PORT` | Optional; default to `smtp.gmail.com`/`587`. Override to point `SMTPEmailSender` at a different SMTP provider |
| `APP_NAME` | Required; product name used in the email template's branding |

## Failure handling and retries

The broker runs `taskiq.SimpleRetryMiddleware`, and `send_email_task` is labeled `retry_on_error=True, max_retries=3`. On failure, `send_email_task` logs the full traceback and **raises** (rather than swallowing the exception) — this is what lets the middleware see the failure and re-enqueue the task immediately (no backoff/delay — see the note below), up to 3 attempts total. A transient SMTP failure (a momentary Gmail outage, a network blip) now gets retried automatically instead of silently dropping the email.

A permanent failure (e.g. bad SMTP credentials) still exhausts all 3 attempts — each attempt logs its own traceback, and the middleware itself logs a final "Maximum retries count is reached" warning, so the failure is visible in logs even though nothing pages an operator automatically. No dead-letter queue or external alerting is configured — an operator watching logs would see it, but nothing pages anyone automatically. Left as a deployment-specific follow-up, since this template doesn't assume a specific alerting stack.

**Why no delay between retries**: `taskiq.SmartRetryMiddleware` supports exponential backoff, but only actually delays a retry when a `schedule_source` (a `TaskiqScheduler`) is configured — without one, its "delay" is a no-op label, which would be misleading to add. This project doesn't run a `TaskiqScheduler` (there's nothing else that needs one), so `SimpleRetryMiddleware`'s immediate re-enqueue is the correct, honest choice for the one task this app has.

## Startup on a fresh Redis instance

A prior pass observed `taskiq_worker` crash-looping for ~30-60s against a brand-new Redis instance (`NOGROUP` errors from `XREADGROUP`) and tracked it as a known, self-healing limitation. Re-investigated during a later QA pass by reading `taskiq_redis`'s actual source (pinned `taskiq-redis==1.2.3`) and reproducing against a genuinely fresh Redis container:

- `RedisStreamBroker.startup()` eagerly runs `XGROUP CREATE ... MKSTREAM` (atomically creating both the stream and the consumer group) and is `await`ed by taskiq's own `Receiver.listen()` *before* the read loop starts — so by the time any process calls `XREADGROUP`, its own consumer group is guaranteed to already exist.
- With 2 worker processes (`WorkerArgs.workers` default) both calling `startup()` independently, whichever process loses the `XGROUP CREATE` race gets a `BUSYGROUP` error, which the broker explicitly catches and logs at `debug` level — never propagated, never fatal.
- Reproduced live against a fresh Redis container (`docker compose up -d postgres redis` on a volume with no prior Redis state, then `docker compose up -d taskiq_worker`): 0 restarts, consumer group present with both worker processes registered, no `NOGROUP` errors in logs.

The race does not reproduce with the currently pinned dependency versions. Locked in with regression tests in `tests/backend/unit/test_email_tasks_unit.py` (`test_broker_uses_mkstream_for_deterministic_group_creation`, `test_broker_startup_survives_concurrent_group_creation_race`) guarding the specific mechanism (`mkstream=True` + graceful `BUSYGROUP` handling) that prevents it, so a future `taskiq-redis` upgrade that regresses this behavior would be caught.

## Testing

`tests/backend/unit/test_email_tasks_unit.py` exercises `send_email_task` directly: the success path, the failure-raises-for-retry path, that the broker's retry middleware and the task's `retry_on_error`/`max_retries` labels are actually configured, and the fresh-Redis startup race guard above. The call sites (`account_verification_service.py`, `password_reset_service.py`) are separately tested with `send_email_task.kiq` mocked/patched. See [Testing Overview](../testing/overview.md).

## Troubleshooting

- **Worker not picking up tasks**: confirm `taskiq_worker` can reach `REDIS_URL` — same Redis instance the `backend` container uses. `docker compose logs taskiq_worker` shows task consumption.
- **Emails not arriving**: check `GMAIL_APP_PASSWORD` is a valid App Password (not the account password) and that "Less secure app access" / App Passwords are enabled on the sending Google account; check `docker compose logs taskiq_worker` for the logged traceback (`send_email_task` logs every failure with `logger.error`).
