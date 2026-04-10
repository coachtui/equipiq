from __future__ import annotations

from pydantic import BaseModel, field_validator


class HypothesisScore(BaseModel):
    """
    Live score for a single diagnostic hypothesis within a session.

    score is clamped to [0, 1] — absolute confidence signal, never normalized.
    evidence carries human-readable notes from each Q&A step that affected the score.
    """

    key: str
    label: str
    score: float
    eliminated: bool = False
    evidence: list[str] = []
    diy_difficulty: str = "moderate"
    parts: list[dict] = []

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class HypothesisRanking(BaseModel):
    """Ordered snapshot of hypotheses at a point in time."""

    ranked: list[HypothesisScore]
    top_key: str | None
    top_score: float | None
    lead_margin: float | None   # top_score - second_score
