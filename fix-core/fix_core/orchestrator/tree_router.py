"""
Tree Candidate Ranking Layer — replaces single-tree selection with ranked candidates.

Deterministic (no LLM).  Uses symptom classification output, vehicle type, and
context signals to score the top 3 candidate trees.  The orchestrator uses this
ranking to decide whether to commit immediately or enter a discriminator phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fix_core.trees import HYPOTHESES, TREES, resolve_tree_key

# Commit immediately when primary candidate score >= this threshold.
COMMIT_THRESHOLD = 0.90

# Symptoms that have high overlap / are easy to confuse — trigger discriminator
# even when secondary_symptom isn't present.
_AMBIGUOUS_PAIRS: set[frozenset[str]] = {
    frozenset({"no_crank", "crank_no_start"}),
    frozenset({"rough_idle", "crank_no_start"}),
    frozenset({"loss_of_power", "rough_idle"}),
    frozenset({"overheating", "visible_leak"}),
    frozenset({"brakes", "suspension"}),
    # Phase 11 — heavy equipment pairs
    # Loss of power in heavy equipment often presents as hydraulic loss (operator
    # conflates engine power with hydraulic response)
    frozenset({"loss_of_power", "hydraulic_loss"}),
    # Electrical fault can masquerade as no_start (safety interlock vs battery)
    frozenset({"no_start", "electrical_fault"}),
    # Track/drive noise overlaps with abnormal_noise reports
    frozenset({"track_or_drive_issue", "abnormal_noise"}),
    # Overheating and hydraulic loss share warning-light presentation
    frozenset({"overheating", "hydraulic_loss"}),
}


@dataclass
class TreeCandidate:
    tree_id: str
    score: float
    reasons: list[str] = field(default_factory=list)


def rank_candidate_trees(intake_data: dict) -> list[TreeCandidate]:
    """
    Return up to 3 candidate trees ranked by likelihood.
    Deterministic — no LLM calls.

    Scoring:
      1.0   — Primary tree (exact symptom + vehicle type match with known vehicle)
      0.85  — Primary tree when vehicle info is sparse or vehicle_type is 'other'
      0.60  — Secondary-symptom alternative tree
      0.40  — Base car tree when vehicle-specific tree was selected
      0.30  — Confusable-pair alternative (when symptom is ambiguous)
    """
    symptom = intake_data.get("symptom_category", "unknown")
    vehicle_type = intake_data.get("vehicle_type", "car") or "car"
    secondary = intake_data.get("secondary_symptom")
    vehicle_make = intake_data.get("vehicle_make")
    vehicle_model = intake_data.get("vehicle_model")

    candidates: list[TreeCandidate] = []
    seen: set[str] = set()

    def _add(tree_id: str, score: float, reasons: list[str]) -> None:
        if tree_id in seen or tree_id not in TREES:
            return
        seen.add(tree_id)
        candidates.append(TreeCandidate(tree_id=tree_id, score=score, reasons=reasons))

    # ── Primary candidate ────────────────────────────────────────────────────
    primary_key = resolve_tree_key(symptom, vehicle_type)
    if primary_key not in TREES:
        return []

    # Score the primary based on how much we know
    primary_score = 1.0
    primary_reasons = [f"Primary symptom: {symptom.replace('_', ' ')}"]

    if vehicle_type not in ("car",):
        primary_reasons.append(f"Vehicle type: {vehicle_type}")

    if vehicle_type == "other":
        primary_score -= 0.15
        primary_reasons.append("Vehicle type unspecified — lower confidence")
    elif not vehicle_make and not vehicle_model:
        primary_score -= 0.10
        primary_reasons.append("No vehicle make/model provided")

    # Penalise for secondary symptom (adds ambiguity)
    if secondary and secondary not in ("unknown", None) and secondary != symptom:
        primary_score -= 0.12
        primary_reasons.append(f"Secondary symptom present: {secondary.replace('_', ' ')}")

    _add(primary_key, round(primary_score, 3), primary_reasons)

    # ── Secondary-symptom alternative ───────────────────────────────────────
    if secondary and secondary not in ("unknown", None) and secondary != symptom:
        secondary_key = resolve_tree_key(secondary, vehicle_type)
        if secondary_key in HYPOTHESES:
            _add(
                secondary_key,
                0.60,
                [
                    f"Alternative: secondary symptom is '{secondary.replace('_', ' ')}'",
                    f"Vehicle type: {vehicle_type}",
                ],
            )

    # ── Confusable-pair alternative ──────────────────────────────────────────
    for pair in _AMBIGUOUS_PAIRS:
        if symptom in pair:
            other = next(s for s in pair if s != symptom)
            alt_key = resolve_tree_key(other, vehicle_type)
            if alt_key in TREES:
                _add(
                    alt_key,
                    0.30,
                    [f"Possible confusion: '{symptom}' is sometimes misidentified as '{other}'"],
                )

    # ── Base car fallback (when vehicle-specific tree was selected) ───────────
    if vehicle_type not in ("car", "other") and symptom in TREES:
        base_key = symptom
        _add(base_key, 0.40, ["Base car tree (fallback if vehicle type is wrong)"])

    return sorted(candidates, key=lambda c: c.score, reverse=True)[:3]


def should_use_discriminator(candidates: list[TreeCandidate]) -> bool:
    """
    Return True if the top candidate's score is below the commit threshold
    AND there is at least one meaningful alternative.
    """
    if not candidates:
        return False
    if candidates[0].score >= COMMIT_THRESHOLD:
        return False
    if len(candidates) < 2:
        return False
    # Only discriminate if the runner-up is meaningful (score >= 0.30)
    return candidates[1].score >= 0.30


# LLM influence cap — keeps deterministic primary dominant
_LLM_WEIGHT = 0.25


def combine_candidates(
    deterministic: list[TreeCandidate],
    llm_hints: list[dict],
    weight_llm: float = _LLM_WEIGHT,
) -> list[TreeCandidate]:
    """
    Merge LLM routing hints with deterministic candidates.

    Rules:
    - LLM influence is capped at weight_llm (default 0.25).
    - The deterministic primary candidate always stays dominant.
    - LLM can slightly boost an existing lower-ranked candidate.
    - LLM can introduce a new candidate, but its score is capped well below
      the deterministic primary.

    Args:
        deterministic: Ranked list from rank_candidate_trees().
        llm_hints:     list of {tree_id, confidence, reasoning} from LLM.
        weight_llm:    Maximum fractional LLM influence (default 0.25).

    Returns:
        Merged, re-sorted list capped at 3 candidates.
    """
    # Build working copy keyed by tree_id
    merged: dict[str, TreeCandidate] = {
        c.tree_id: TreeCandidate(c.tree_id, c.score, list(c.reasons))
        for c in deterministic
    }

    primary_score = deterministic[0].score if deterministic else 1.0

    for hint in llm_hints:
        tree_id = hint.get("tree_id", "")
        llm_conf = float(hint.get("confidence", 0.0))
        reasoning = str(hint.get("reasoning", ""))[:80]
        if not tree_id or tree_id not in TREES:
            continue

        if tree_id in merged:
            # Small boost to existing candidate — cap at 95% of primary
            boost = llm_conf * weight_llm * 0.15
            candidate = merged[tree_id]
            candidate.score = min(round(candidate.score + boost, 3), primary_score * 0.95)
            candidate.reasons.append(f"LLM hint: {reasoning}")
        else:
            # New LLM-only candidate — cap well below deterministic primary
            llm_score = min(round(llm_conf * weight_llm, 3), primary_score * 0.35)
            merged[tree_id] = TreeCandidate(
                tree_id=tree_id,
                score=llm_score,
                reasons=[f"LLM routing hint: {reasoning}"],
            )

    return sorted(merged.values(), key=lambda c: c.score, reverse=True)[:3]
