from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, computed_field

from fix_core.models.context import OwnerContext
from fix_core.models.hypothesis import HypothesisScore
from fix_core.models.result import DiagnosticResult


class SessionState(str, Enum):
    active = "active"
    completed = "completed"
    awaiting_followup = "awaiting_followup"


class SessionMode(str, Enum):
    consumer = "consumer"
    operator = "operator"      # field operator — Phase 11
    mechanic = "mechanic"      # mechanic-assisted — future


class RoutingPhase(str, Enum):
    intake = "intake"
    discriminating = "discriminating"
    committed = "committed"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageType(str, Enum):
    chat = "chat"
    safety = "safety"
    result = "result"
    followup = "followup"


class SessionMessage(BaseModel):
    id: UUID
    session_id: UUID
    created_at: datetime
    role: MessageRole
    content: str
    msg_type: MessageType = MessageType.chat


class MediaReference(BaseModel):
    """
    Reference to a file stored by the adapter's StorageProvider.

    storage_path is opaque to core — only the StorageProvider resolves it to bytes
    or a URL. Core carries it as part of the session aggregate so the repository
    can persist it; core never reads the bytes directly.
    """

    storage_path: str
    filename: str
    media_type: str          # "image/jpeg", "video/mp4", etc.
    uploaded_at: datetime


class DiagnosticSession(BaseModel):
    """
    Full session aggregate — the canonical unit of state for a diagnostic interaction.

    Rules:
    - Owned by a single OwnerContext (user_id required; org/project optional).
    - The repository always saves the full aggregate via SessionRepository.save().
      No partial column-level updates outside of save().
    - evidence_log stores EvidencePacket dicts (use EvidencePacket.model_dump() /
      EvidencePacket.model_validate() to convert).
    - media carries MediaReferences; the StorageProvider owns the bytes behind each path.
    - result is None until the session exits.
    """

    id: UUID
    owner: OwnerContext

    created_at: datetime
    updated_at: datetime
    status: SessionState = SessionState.active
    turn_count: int = 0
    answered_nodes: int = 0   # tree Q&A nodes answered; used by exit_guard

    # Vehicle
    vehicle_type: str = "car"
    vehicle_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_engine: str | None = None

    # Symptom / routing
    symptom_category: str | None = None
    initial_description: str | None = None
    current_node_id: str | None = None
    context: dict = {}
    routing_phase: RoutingPhase = RoutingPhase.committed
    selected_tree: str | None = None

    # Evidence and safety
    evidence_log: list[dict] = []          # list of EvidencePacket.model_dump()
    contradiction_flags: list[dict] = []
    safety_flags: list[dict] = []

    # LLM advisory
    shadow_hypotheses: list[dict] = []

    # Mode / heavy equipment
    session_mode: SessionMode = SessionMode.consumer
    heavy_context: dict = {}

    # Aggregate children
    messages: list[SessionMessage] = []
    hypotheses: list[HypothesisScore] = []
    result: DiagnosticResult | None = None
    media: list[MediaReference] = []

    @computed_field
    @property
    def vehicle_context(self) -> str:
        """Human-readable vehicle description, e.g. '2020 Ford F-150 5.0L V8'."""
        parts = [
            str(self.vehicle_year) if self.vehicle_year else "",
            self.vehicle_make or "",
            self.vehicle_model or "",
            self.vehicle_engine or "",
        ]
        return " ".join(p for p in parts if p).strip() or "Unknown vehicle"
