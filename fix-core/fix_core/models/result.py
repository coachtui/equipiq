from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SynthesizedCause(BaseModel):
    """
    LLM-produced cause entry from synthesize_result().
    Freeform — cause is a descriptive string, not a tree hypothesis key.
    Stored in DiagnosticResult.ranked_causes.
    """

    cause: str
    confidence: float
    reasoning: str


class RankedCause(BaseModel):
    """
    Engine-oriented cause entry keyed to a tree hypothesis.
    Preserved for future engine-side result construction distinct from
    LLM synthesis output.
    """

    hypothesis_key: str
    label: str
    score: float
    diy_difficulty: str | None = None
    suggested_parts: list[dict] = []


class DiagnosticResult(BaseModel):
    """
    Final result produced when the session exits (early or exhausted).
    Populated by ClaudeProvider.synthesize_result() + engine state at exit.
    ranked_causes holds LLM-synthesized freeform causes (SynthesizedCause),
    not engine hypothesis keys.
    """

    id: UUID
    session_id: UUID
    created_at: datetime
    ranked_causes: list[SynthesizedCause]
    next_checks: list[str]
    diy_difficulty: str | None = None
    suggested_parts: list[dict] = []
    escalation_guidance: str | None = None
    confidence_level: float | None = None


class SessionFeedback(BaseModel):
    """User-submitted feedback on a completed session."""

    session_id: UUID
    rating: int               # 1–5
    comment: str | None = None
    created_at: datetime | None = None
