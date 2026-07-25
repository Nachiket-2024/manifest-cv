import logging
import os
from logging.handlers import TimedRotatingFileHandler

from pythonjsonlogger import jsonlogger

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


LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
ACCESS_LOG_PATH = os.path.join(LOG_DIR, 'access.log')


def get_logger(name: str = "base_logger") -> logging.Logger:
    """
    Returns a logger configured with:
    - JSON formatted rotating file logs
    - base_logger INFO logs stored in files only
    - warnings/errors visible in Docker terminal
    - Uvicorn access logs visible except health checks
    """

    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s'
        )

        request_id_filter = RequestIdFilter()

        access_handler = TimedRotatingFileHandler(
            ACCESS_LOG_PATH,
            when="midnight",
            interval=1,
            # backupCount=0 previously meant "never delete a rotated file" —
            # not "keep no backups" (TimedRotatingFileHandler's own
            # semantics: 0 disables pruning entirely) — so access.log.* grew
            # unbounded on a long-running deployment. 30 days is a
            # reasonable default retention window for access logs.
            backupCount=30
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(formatter)
        access_handler.addFilter(request_id_filter)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(request_id_filter)

        logger.addHandler(access_handler)
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