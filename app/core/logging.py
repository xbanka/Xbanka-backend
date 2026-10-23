import contextvars
import json
import logging
import logging.config
import re
from datetime import datetime, timezone

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

LOCAL_ENVIRONMENTS = {"local", "dev", "development"}

SENSITIVE_KEYS = (
    "password",
    "passwd",
    "token",
    "authorization",
    "secret",
    "api_key",
    "apikey",
    "cookie",
    "account_number",
    "bvn",
)

REDACTED = "***"

# Matches `key=value`, `key: value` and `"key": "value"` inside free text.
_KEY_PATTERN = "|".join(SENSITIVE_KEYS)
_TEXT_REDACT_RE = re.compile(
    rf"""(?ix)
    (["']?(?:\w*(?:{_KEY_PATTERN})\w*)["']?\s*[:=]\s*)
    (?:Bearer\s+)?
    (["']?)[^\s,"'}}&]+\2
    """
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")

# LogRecord attributes that are not user-supplied `extra` fields.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


def _is_sensitive(key: str) -> bool:
    key = key.lower()
    return any(s in key for s in SENSITIVE_KEYS)


def redact(value):
    """Mask sensitive values in dicts/lists/strings, recursively."""
    if isinstance(value, dict):
        return {
            k: REDACTED if isinstance(k, str) and _is_sensitive(k) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = _BEARER_RE.sub(f"Bearer {REDACTED}", value)
        return _TEXT_REDACT_RE.sub(lambda m: f"{m.group(1)}{REDACTED}", value)
    return value


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        current = request_id_ctx.get()
        if current != "-" or not hasattr(record, "request_id"):
            record.request_id = current
        return True


class RedactionFilter(logging.Filter):
    """Masks secrets in the message, its args and any `extra` fields."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact(record.getMessage())
            record.args = None
        except Exception:
            pass
        for key in set(vars(record)) - _RESERVED:
            value = getattr(record, key)
            setattr(
                record, key, REDACTED if _is_sensitive(key) else redact(value)
            )
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key in set(vars(record)) - _RESERVED:
            payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(environment: str, level: str = "INFO") -> None:
    json_logs = environment.lower() not in LOCAL_ENVIRONMENTS
    level = level.upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": RequestIdFilter},
                "redact": {"()": RedactionFilter},
            },
            "formatters": {
                "json": {"()": JsonFormatter},
                "text": {
                    "format": "%(asctime)s %(levelname)-8s [%(request_id)s] "
                    "%(name)s: %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json" if json_logs else "text",
                    "filters": ["request_id", "redact"],
                }
            },
            "root": {"level": level, "handlers": ["console"]},
            "loggers": {
                # Route uvicorn's own records through our handler. The access
                # log is replaced by RequestLoggingMiddleware.
                "uvicorn": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.error": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": True},
                "sqlalchemy.engine": {"level": "WARNING"},
                "httpx": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
                "urllib3": {"level": "WARNING"},
                "botocore": {"level": "WARNING"},
                "boto3": {"level": "WARNING"},
            },
        }
    )
