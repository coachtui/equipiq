from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class OwnerContext(BaseModel):
    """
    Identifies who owns a diagnostic session.

    Rules:
    - Core uses only user_id. All other fields are for adapter use (persistence
      filtering, access control, multi-tenancy).
    - org_id / project_id are populated by the AIGACP adapter; standalone leaves them None.
    - asset_id is set when a session is explicitly bound to a fleet asset.
    - source is for observability only — must never be used to branch diagnostic logic.
    - Do NOT add fields here without an explicit design decision. This is not a
      general-purpose bag; every field has a documented purpose.
    """

    user_id: UUID
    org_id: UUID | None = None
    project_id: UUID | None = None
    asset_id: str | None = None
    source: str | None = None  # "standalone" | "aigacp" — observability only
