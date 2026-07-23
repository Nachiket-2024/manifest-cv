import logging
import os

from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import json as jsonlogger

from ..core.settings import settings
from .correlation_id_middleware import request_id_ctx_var


class RequestIdFilter(logging.Filter):
    """Injects the current request's correlation ID (if any) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class HealthCheckFilter(logging.Filter):
    """Hide Docker healthcheck requests from terminal access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health/ready" not in record.getMessage()


def _resolve_log_dir() -> str:
    log_dir = settings.LOG_DIR
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', log_dir)
    return log_dir


def _build_file_handler(formatter: logging.Formatter, request_id_filter: logging.Filter):
    """Builds the rotating access-log file handler. Returns None instead of
    raising if the log directory can't be created or written to, so callers
    can fall back to stdout-only logging rather than crash at import time."""
    try:
        log_dir = _resolve_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        access_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, 'access.log'),
            when="midnight",
            interval=1,
            # backupCount=0 previously meant "never delete a rotated file" —
            # not "keep no backups" (TimedRotatingFileHandler's own
            # semantics: 0 disables pruning entirely) — so access.log.* grew
            # unbounded on a long-running deployment. 30 days is a
            # reasonable default retention window for access logs.
            backupCount=30
        )
    except OSError:
        return None
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)
    access_handler.addFilter(request_id_filter)
    return access_handler


def get_logger(name: str = "base_logger") -> logging.Logger:
    """
    Returns a logger configured with:
    - JSON formatted rotating file logs
    - base_logger INFO logs stored in files only
    - warnings/errors visible in Docker terminal
    - Uvicorn access logs visible except health checks

    File logging is best-effort: if the log directory isn't writable (e.g. a
    fresh checkout without a pre-created logs/ dir, or a read-only
    filesystem), this falls back to stdout-only logging instead of raising.
    """

    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s'
        )

        request_id_filter = RequestIdFilter()

        access_handler = _build_file_handler(formatter, request_id_filter)
        if access_handler is not None:
            logger.addHandler(access_handler)

        stream_handler = logging.StreamHandler()
        # If the file handler couldn't be created, stdout is the only output
        # left — keep it at INFO instead of WARNING so logs aren't silently
        # dropped rather than just relocated.
        stream_handler.setLevel(logging.INFO if access_handler is None else logging.WARNING)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(request_id_filter)

        logger.addHandler(stream_handler)

    # Uvicorn access logs in terminal, but hide healthcheck spam
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_access_logger.addFilter(HealthCheckFilter())
    uvicorn_access_logger.propagate = True

    return logger


def get_startup_logger(name: str = "startup") -> logging.Logger:
    """
    Returns a logger for one-time, boot-relevant facts (e.g. whether an
    optional subsystem like error monitoring is enabled) that should be
    visible in `docker compose logs`/the terminal immediately — unlike
    get_logger()'s INFO level, which is deliberately file-only there to
    keep the terminal free of routine per-request noise (see its own
    docstring). Fires once per process start (or once per reload in dev
    with `--reload`, same as uvicorn's own startup lines), never per
    request, so promoting it to the terminal doesn't reintroduce that noise.

    Use sparingly — a handful of startup facts an operator would want to
    see without opening a log file, not a general substitute for
    get_logger(). Still structured JSON via the same formatter, so log
    aggregation tooling parses it identically either way.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)

    return logger