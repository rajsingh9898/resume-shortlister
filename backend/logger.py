import os
import logging
import json
import datetime
from logging import StreamHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "lineno": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Initialize standard Python logging
logger = logging.getLogger("talentai")
logger.setLevel(logging.INFO)

# Avoid adding duplicate handlers if imported multiple times
if not logger.handlers:
    stream_handler = StreamHandler()
    stream_handler.setFormatter(JsonFormatter())
    logger.addHandler(stream_handler)

try:
    from backend.config import settings
except ImportError:
    from config import settings

# Configure Sentry SDK if DSN is set
SENTRY_DSN = settings.SENTRY_DSN
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        logger.info("Sentry SDK successfully initialized for error monitoring.")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry SDK: {str(e)}")
else:
    logger.info("Sentry DSN not configured. Error monitoring disabled/stubbed.")
