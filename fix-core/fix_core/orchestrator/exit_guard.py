"""
Early Exit Guard — replaces the raw should_exit_early() check with a multi-condition
gate that prevents false-confidence exits.

Conditions required (ALL must be true):
  1. top_score >= threshold (configurable, default from settings)
  2. score_gap >= threshold (configurable, default from settings)
  3. answered_nodes >= MIN_NODES (at least 3 Q&A answers)
  4. evidence_types >= MIN_EVIDENCE_TYPES (at least 2 distinct evidence sources)
  5. no ACTIVE contradiction flags with severity >= CONTRADICTION_BLOCK_SEVERITY
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fix_core.orchestrator.evidence import evidence_type_count
from fix_core.engine.hypothesis_scorer import HypothesisScorer

if TYPE_CHECKING:
    from fix_core.models.session import DiagnosticSession

MIN_NODES: int = 3
MIN_EVIDENCE_TYPES: int = 2
CONTRADICTION_BLOCK_SEVERITY: float = 0.5


def can_exit(
    scorer: HypothesisScorer,
    answered_nodes: int,
    evidence_log: list[dict],
    contradiction_flags: list[dict],
    *,
    score_threshold: float = 0.75,
    lead_threshold: float = 0.20,
) -> bool:
    """
    Return True only when ALL exit conditions are satisfied.

    Args:
        scorer:              Current hypothesis scorer state.
        answered_nodes:      Number of tree Q&A nodes already answered in this session.
        evidence_log:        Serialized EvidencePackets from session.evidence_log.
        contradiction_flags: Serialized Contradictions from session.contradiction_flags.
        score_threshold:     Minimum score for top hypothesis (default 0.75).
        lead_threshold:      Minimum gap over second hypothesis (default 0.20).
    """
    # 1. Score conditions
    if scorer.top_confidence() < score_threshold:
        return False
    if scorer.confidence_lead() < lead_threshold:
        return False

    # 2. Minimum answered nodes
    if answered_nodes < MIN_NODES:
        return False

    # 3. Minimum evidence types
    if evidence_type_count(evidence_log) < MIN_EVIDENCE_TYPES:
        return False

    # 4. No blocking contradictions
    for flag in contradiction_flags:
        if flag.get("severity", 0.0) >= CONTRADICTION_BLOCK_SEVERITY:
            return False

    return True


def exit_reason(
    scorer: HypothesisScorer,
    answered_nodes: int,
    evidence_log: list[dict],
    contradiction_flags: list[dict],
    *,
    score_threshold: float = 0.75,
    lead_threshold: float = 0.20,
) -> str | None:
    """
    Return a human-readable reason why exit is blocked, or None if exit is allowed.
    Used for debugging / logging only.
    """
    if scorer.top_confidence() < score_threshold:
        return f"top_score {scorer.top_confidence():.2f} < {score_threshold}"
    if scorer.confidence_lead() < lead_threshold:
        return f"score_gap {scorer.confidence_lead():.2f} < {lead_threshold}"
    if answered_nodes < MIN_NODES:
        return f"only {answered_nodes}/{MIN_NODES} nodes answered"
    if evidence_type_count(evidence_log) < MIN_EVIDENCE_TYPES:
        types = {e.get("source") for e in evidence_log}
        return f"evidence types {types} < {MIN_EVIDENCE_TYPES} required"
    for flag in contradiction_flags:
        if flag.get("severity", 0.0) >= CONTRADICTION_BLOCK_SEVERITY:
            return f"active contradiction: {flag.get('description', 'unknown')}"
    return None


# ── Session-level helpers ──────────────────────────────────────────────────────


def can_exit_from_session(
    session: "DiagnosticSession",
    scorer: HypothesisScorer,
    *,
    score_threshold: float = 0.75,
    lead_threshold: float = 0.20,
) -> bool:
    """
    Convenience wrapper that reads exit inputs from a DiagnosticSession aggregate.

    Prefer this over calling can_exit() directly in controller / use-case code
    so that the session field names are not scattered across callers.
    """
    return can_exit(
        scorer=scorer,
        answered_nodes=session.answered_nodes,
        evidence_log=session.evidence_log,
        contradiction_flags=session.contradiction_flags,
        score_threshold=score_threshold,
        lead_threshold=lead_threshold,
    )


def exit_reason_from_session(
    session: "DiagnosticSession",
    scorer: HypothesisScorer,
    *,
    score_threshold: float = 0.75,
    lead_threshold: float = 0.20,
) -> str | None:
    """
    Convenience wrapper that reads exit inputs from a DiagnosticSession aggregate.
    Returns a human-readable block reason, or None if exit is allowed.
    """
    return exit_reason(
        scorer=scorer,
        answered_nodes=session.answered_nodes,
        evidence_log=session.evidence_log,
        contradiction_flags=session.contradiction_flags,
        score_threshold=score_threshold,
        lead_threshold=lead_threshold,
    )
