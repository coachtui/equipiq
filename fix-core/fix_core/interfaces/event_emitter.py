from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventEmitter(Protocol):
    """
    Contract for platform event emission.

    Standalone adapter: NoOpEventEmitter — emits nothing. Standalone Fix has no
    platform event bus.

    AIGACP adapter: PlatformEventEmitter — forwards events to the AIGACP event bus.
    Currently defined events:
      - "fix.session.completed"  payload: {user_id, session_id, outcome, vehicle_type}
      - "fix.safety.alert"       payload: {user_id, session_id, severity, alert_type}

    Core calls emit() after significant state transitions. The call is fire-and-forget;
    core does not await event delivery or handle emitter errors.
    """

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """
        Emit a named event with the given payload.
        Must not raise. Implementations should swallow errors and log locally.
        """
        ...
