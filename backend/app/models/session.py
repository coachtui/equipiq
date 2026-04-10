from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    status: Mapped[str] = mapped_column(Text, default="active")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)

    vehicle_year: Mapped[int | None] = mapped_column(Integer)
    vehicle_make: Mapped[str | None] = mapped_column(Text)
    vehicle_model: Mapped[str | None] = mapped_column(Text)
    vehicle_engine: Mapped[str | None] = mapped_column(Text)
    vehicle_type: Mapped[str] = mapped_column(Text, default="car")

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    symptom_category: Mapped[str | None] = mapped_column(Text)
    initial_description: Mapped[str | None] = mapped_column(Text)
    current_node_id: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Phase 9 — Orchestration layer fields
    routing_phase: Mapped[str] = mapped_column(Text, default="committed")
    selected_tree: Mapped[str | None] = mapped_column(Text)
    evidence_log: Mapped[list] = mapped_column(JSONB, default=list)
    contradiction_flags: Mapped[list] = mapped_column(JSONB, default=list)
    safety_flags: Mapped[list] = mapped_column(JSONB, default=list)

    # Phase 9.5 — LLM augmentation fields
    shadow_hypotheses: Mapped[list] = mapped_column(JSONB, default=list)

    # Phase 12 — Heavy equipment and session mode
    session_mode: Mapped[str] = mapped_column(Text, default="consumer")
    heavy_context: Mapped[dict] = mapped_column(JSONB, default=dict)

    # No back_populates — avoids async lazy-load errors when adding child rows
    messages: Mapped[list["SessionMessage"]] = relationship(
        "SessionMessage", order_by="SessionMessage.created_at", lazy="raise"
    )
    hypotheses: Mapped[list["SessionHypothesis"]] = relationship(
        "SessionHypothesis", lazy="raise"
    )
    result: Mapped["DiagnosticResult | None"] = relationship(
        "DiagnosticResult", uselist=False, lazy="raise"
    )


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    msg_type: Mapped[str] = mapped_column(Text, default="chat")

    __table_args__ = (
        Index("idx_session_messages_session_id", "session_id", "created_at"),
    )


class SessionHypothesis(Base):
    __tablename__ = "session_hypotheses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    hypothesis_key: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    eliminated: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)

    __table_args__ = (
        Index("idx_session_hypotheses_session_id", "session_id"),
    )


class DiagnosticResult(Base):
    __tablename__ = "diagnostic_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ranked_causes: Mapped[list] = mapped_column(JSONB)
    next_checks: Mapped[list] = mapped_column(JSONB)
    diy_difficulty: Mapped[str | None] = mapped_column(Text)
    suggested_parts: Mapped[list] = mapped_column(JSONB, default=list)
    escalation_guidance: Mapped[str | None] = mapped_column(Text)
    confidence_level: Mapped[float | None] = mapped_column(Float)


class MediaAttachment(Base):
    __tablename__ = "media_attachments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    file_type: Mapped[str] = mapped_column(Text)
    storage_path: Mapped[str] = mapped_column(Text)
    vision_analysis: Mapped[dict | None] = mapped_column(JSONB)
    confidence_modifier: Mapped[float] = mapped_column(Float, default=0.0)


class SessionFeedback(Base):
    __tablename__ = "session_feedback"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# ── Phase 10: Learning System ─────────────────────────────────────────────────

class DiagnosticOutcome(Base):
    """Per-session outcome record. Populated at result delivery; updated on feedback."""
    __tablename__ = "diagnostic_outcomes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), unique=True
    )
    selected_tree: Mapped[str | None] = mapped_column(Text)
    final_hypotheses: Mapped[list] = mapped_column(JSONB, default=list)
    top_hypothesis: Mapped[str | None] = mapped_column(Text)
    was_resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolution_confirmed_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    contradiction_count: Mapped[int] = mapped_column(Integer, default=0)
    safety_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ApprovedWeightAdjustment(Base):
    """Admin-approved multipliers applied to hypothesis priors at session creation."""
    __tablename__ = "approved_weight_adjustments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    hypothesis_id: Mapped[str] = mapped_column(Text, unique=True)
    multiplier: Mapped[float] = mapped_column(Float)
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(server_default=func.now())
