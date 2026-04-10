import logging
from typing import Any

_event_logger = logging.getLogger("fix.events")


class NoOpEventEmitter:
    """Fire-and-forget no-op event emitter. Used in tests."""

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        pass


class LoggingEventEmitter:
    """
    Logs events at INFO level via the 'fix.events' logger.

    Use in development and staging. Replace with QueueEventEmitter (Redis/SQS)
    for async consumers in production — same interface, no call-site changes.
    """

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        _event_logger.info("event=%s payload=%s", event_name, payload)
