"""
Hypothesis scorer — manages and updates hypothesis scores based on tree traversal.
Scores are clamped to [0, 1] after each update.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fix_core.models.hypothesis import HypothesisScore


@dataclass
class Hypothesis:
    key: str
    label: str
    score: float
    eliminated: bool = False
    evidence: list[str] = field(default_factory=list)
    diy_difficulty: str = "moderate"
    parts: list[dict] = field(default_factory=list)


class HypothesisScorer:
    def __init__(
        self,
        hypotheses_def: dict[str, dict],
        weight_multipliers: dict[str, float] | None = None,
    ) -> None:
        """
        weight_multipliers: admin-approved {hypothesis_key: multiplier} map.
        Applied to each hypothesis prior at init time only.
        Default multiplier = 1.0 (no effect). Clamped to [0, 1] after application.
        """
        _mult = weight_multipliers or {}
        self.hypotheses: dict[str, Hypothesis] = {
            key: Hypothesis(
                key=key,
                label=data["label"],
                score=min(1.0, max(0.0, data["prior"] * _mult.get(key, 1.0))),
                diy_difficulty=data.get("diy_difficulty", "moderate"),
                parts=data.get("parts", []),
            )
            for key, data in hypotheses_def.items()
        }

    def apply_option(self, option: dict, question_text: str, answer_label: str) -> None:
        evidence_note = f"Q: {question_text} → A: {answer_label}"

        # Apply score deltas
        for key, delta in option.get("deltas", {}).items():
            if key in self.hypotheses and not self.hypotheses[key].eliminated:
                h = self.hypotheses[key]
                h.score = max(0.0, min(1.0, h.score + delta))
                if delta != 0:
                    h.evidence.append(evidence_note)

        # Eliminate hypotheses
        for key in option.get("eliminate", []):
            if key in self.hypotheses:
                self.hypotheses[key].eliminated = True
                self.hypotheses[key].score = 0.0

    def ranked(self) -> list[Hypothesis]:
        """Return non-eliminated hypotheses sorted by score descending."""
        return sorted(
            [h for h in self.hypotheses.values() if not h.eliminated],
            key=lambda h: h.score,
            reverse=True,
        )

    def top_confidence(self) -> float:
        ranked = self.ranked()
        return ranked[0].score if ranked else 0.0

    def confidence_lead(self) -> float:
        """How much the top hypothesis leads the second."""
        ranked = self.ranked()
        if len(ranked) < 2:
            return ranked[0].score if ranked else 0.0
        return ranked[0].score - ranked[1].score

    def should_exit_early(self, threshold: float = 0.75, min_lead: float = 0.20) -> bool:
        return self.top_confidence() >= threshold and self.confidence_lead() >= min_lead

    def to_serializable(self) -> list[dict]:
        return [
            {
                "key": h.key,
                "label": h.label,
                "score": round(h.score, 3),
                "eliminated": h.eliminated,
                "evidence": h.evidence,
                "diy_difficulty": h.diy_difficulty,
                "parts": h.parts,
            }
            for h in self.hypotheses.values()
        ]

    @classmethod
    def from_serializable(
        cls, hypotheses_def: dict[str, dict], saved: list[dict]
    ) -> "HypothesisScorer":
        scorer = cls(hypotheses_def)
        saved_by_key = {item["key"]: item for item in saved}
        for key, h in scorer.hypotheses.items():
            if key in saved_by_key:
                s = saved_by_key[key]
                h.score = s["score"]
                h.eliminated = s["eliminated"]
                h.evidence = s["evidence"]
        return scorer

    # ── Pydantic model conversion bridge ──────────────────────────────────────

    def to_hypothesis_scores(self) -> list["HypothesisScore"]:
        """
        Convert internal Hypothesis dataclasses to HypothesisScore Pydantic models
        for storage in DiagnosticSession.hypotheses (session aggregate).

        Call this before saving session state so the repository receives typed models
        that will be serialized as list[dict] by the Pydantic layer.
        """
        from fix_core.models.hypothesis import HypothesisScore  # local to avoid circular

        return [
            HypothesisScore(
                key=h.key,
                label=h.label,
                score=round(h.score, 3),
                eliminated=h.eliminated,
                evidence=list(h.evidence),
                diy_difficulty=h.diy_difficulty,
                parts=list(h.parts),
            )
            for h in self.hypotheses.values()
        ]

    @classmethod
    def from_hypothesis_scores(
        cls,
        hypotheses_def: dict[str, dict],
        scores: "list[HypothesisScore]",
        weight_multipliers: dict[str, float] | None = None,
    ) -> "HypothesisScorer":
        """
        Restore a HypothesisScorer from the HypothesisScore Pydantic models stored
        in DiagnosticSession.hypotheses.

        Use this when resuming a session — load the session from the repo, then call
        this to reconstruct a live scorer ready for the next tree step.

        weight_multipliers: pass the same multipliers used at session creation so the
        scorer is constructed in the correct context before saved scores are applied.
        Saved scores always take precedence over the init-time computed values.
        """
        scorer = cls(hypotheses_def, weight_multipliers=weight_multipliers)
        scores_by_key = {s.key: s for s in scores}
        for key, h in scorer.hypotheses.items():
            if key in scores_by_key:
                s = scores_by_key[key]
                h.score = s.score
                h.eliminated = s.eliminated
                h.evidence = list(s.evidence)
        return scorer
