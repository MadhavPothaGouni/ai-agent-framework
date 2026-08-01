
import json
import logging
import sys
import time

_RESERVED_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()) | {
    "message",
    "asctime",
}

_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Anything passed via extra={...} that isn't a stdlib LogRecord field.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent — safe to call multiple times (e.g. once per --reload)."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root.handlers = [handler]
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)