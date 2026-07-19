# tests/backend/unit/test_logging_config_unit.py
#
# Regression guard: the access-log TimedRotatingFileHandler was previously
# constructed with backupCount=0, which is TimedRotatingFileHandler's own
# signal to never prune rotated files (not "keep zero backups") — access.log.*
# grew without bound on a long-running deployment.
from logging.handlers import TimedRotatingFileHandler

from backend.app.logging.logging_config import get_logger


def test_access_log_handler_has_a_bounded_retention_window():
    logger = get_logger("test_logging_config_retention")

    rotating_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert rotating_handlers, "expected a TimedRotatingFileHandler on the access log"
    assert rotating_handlers[0].backupCount > 0
