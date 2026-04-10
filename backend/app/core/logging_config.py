"""
Structured logging setup.

Call configure_logging() once at app startup (in main.py).
Use get_logger(__name__) in any module for a named logger.

Log format: timestamp | level | logger | request_id | message [key=value ...]
request_id is a per-request UUID stored in a contextvars.ContextVar.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rid = request_id_var.get("-")
        ts = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        base = f"{ts} | {record.levelname:<8} | {record.name} | {rid} | {record.getMessage()}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. uvicorn already set up handlers)
    handler = logging.StreamHandler()
    handler.setFormatter(_StructuredFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


class RequestLoggingMiddleware:
    """ASGI middleware: assigns request_id, logs method+path+status+duration."""

    def __init__(self, app) -> None:
        self.app = app
        self._log = get_logger("fix.request")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = new_request_id()
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            self._log.info(
                "%s %s → %s  %dms",
                method,
                path,
                status_code,
                duration_ms,
            )
            request_id_var.reset(token)
