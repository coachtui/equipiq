from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

EvidenceSource = Literal[
    "intake",
    "user_text",
    "image",
    "obd",
    "manual_test",
    "operator_observation",
    "manual_check",
    "sensor_future",
]


class EvidencePacket(BaseModel):
    """
    Normalized evidence unit. Every input that affects hypothesis scores is
    wrapped in an EvidencePacket before being applied and stored in the session's
    evidence_log. Mirrors the dataclass in backend/app/diagnostics/orchestrator/evidence.py
    — this Pydantic version is the canonical core representation.

    certainty: 0.0–1.0 confidence that this observation is accurate.
    affects:   {hypothesis_key: score_delta} — applied scaled by certainty.
    """

    source: EvidenceSource
    observation: str
    normalized_key: str
    certainty: float
    affects: dict[str, float] = {}

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: dict) -> "EvidencePacket":
        return cls(**d)
