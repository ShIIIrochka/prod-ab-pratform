from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import sys

from typing import Any


_RESERVED_RECORD_KEYS: set[str] = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "stacklevel",
}


class JsonFormatter(logging.Formatter):
    """Форматтер, выводящий записи логов в виде одной JSON-строки."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        timestamp = _dt.datetime.fromtimestamp(
            record.created, tz=_dt.UTC
        ).isoformat()

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_KEYS:
                continue
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Инициализировать единый формат логов для всего приложения.

    По умолчанию включает JSON-формат. Для локальной отладки можно
    задать LOG_FORMAT=plain, чтобы получать человекочитаемый текст.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()

    handler = logging.StreamHandler(stream=sys.stdout)

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )

    root.addHandler(handler)
    root.setLevel(log_level)
