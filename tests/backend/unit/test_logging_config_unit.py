# tests/backend/unit/test_logging_config_unit.py
#
# Regression guard: the access-log TimedRotatingFileHandler was previously
# constructed with backupCount=0, which is TimedRotatingFileHandler's own
# signal to never prune rotated files (not "keep zero backups") — access.log.*
# grew without bound on a long-running deployment.
import logging

from logging.handlers import TimedRotatingFileHandler

from backend.app.logging.logging_config import get_logger, get_startup_logger


def test_access_log_handler_has_a_bounded_retention_window():
    logger = get_logger("test_logging_config_retention")

    rotating_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert rotating_handlers, "expected a TimedRotatingFileHandler on the access log"
    assert rotating_handlers[0].backupCount > 0


def test_get_logger_routine_info_only_reaches_the_file_handler_not_the_terminal():
    # The whole point of the split: routine per-request INFO logging must
    # stay out of the terminal (see get_logger()'s own docstring) — only
    # WARNING and up should reach its StreamHandler.
    logger = get_logger("test_logging_config_stream_level")

    stream_handlers = [h for h in logger.handlers if type(h) is logging.StreamHandler]
    assert stream_handlers, "expected a StreamHandler on the regular logger"
    assert stream_handlers[0].level == logging.WARNING


def test_get_startup_logger_info_reaches_the_terminal():
    # Regression guard: a one-time, boot-relevant fact (e.g. whether
    # optional error monitoring is enabled) must be visible in `docker
    # compose logs` at INFO — unlike get_logger()'s routine INFO, which is
    # deliberately file-only.
    logger = get_startup_logger("test_logging_config_startup_stream_level")

    stream_handlers = [h for h in logger.handlers if type(h) is logging.StreamHandler]
    assert stream_handlers, "expected a StreamHandler on the startup logger"
    assert stream_handlers[0].level == logging.INFO


def test_get_startup_logger_has_no_file_handler():
    # Startup facts are few and meant to be seen immediately — they don't
    # need (and shouldn't get) the same rotating file sink as routine
    # per-request access logs.
    logger = get_startup_logger("test_logging_config_startup_no_file")

    rotating_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert not rotating_handlers
