from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from fix_core.models.context import OwnerContext
from fix_core.models.session import DiagnosticSession


@runtime_checkable
class SessionRepository(Protocol):
    """
    Persistence contract for DiagnosticSession aggregates.

    Rules:
    - save() always receives the full DiagnosticSession aggregate. Adapters must
      not apply partial column-level updates outside of this method.
    - get() returns None (not raises) when the session does not exist or does not
      belong to the given context.
    - DiagnosticSession.media (list[MediaReference]) carries storage_path values
      that the adapter persists alongside the session. The repository does NOT call
      StorageProvider — it only persists the storage_path strings.
    - Implementations must enforce that context.user_id (and, for AIGACP,
      context.org_id / context.project_id) matches the persisted session ownership
      before returning data. Return None rather than raise on ownership mismatch
      (prevents session ID enumeration).
    """

    async def get(self, session_id: UUID, context: OwnerContext) -> DiagnosticSession | None:
        """Load a session by ID. Returns None if not found or not owned by context."""
        ...

    async def save(self, session: DiagnosticSession) -> None:
        """
        Persist the full session aggregate, including messages, hypotheses,
        result, evidence_log, safety_flags, contradiction_flags, and media references.
        """
        ...

    async def list(self, context: OwnerContext) -> list[DiagnosticSession]:
        """Return all sessions owned by context, ordered by updated_at desc."""
        ...

    async def delete(self, session_id: UUID, context: OwnerContext) -> None:
        """Delete a session. No-op if not found or not owned by context."""
        ...
