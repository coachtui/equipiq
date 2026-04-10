"""
Discriminator Question Phase — asks 1–2 high-signal questions BEFORE committing
to a tree when candidates are ambiguous.

Deterministic (no LLM).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fix_core.orchestrator.tree_router import TreeCandidate


@dataclass
class DiscriminatorQuestion:
    question: str
    # keyword groups that commit to a specific tree_id
    # each entry: (keywords_list, tree_id)
    commit_map: list[tuple[list[str], str]] = field(default_factory=list)
    fallback_tree: str = ""           # tree to commit to if no keyword matches


# ── Static discriminator library ────────────────────────────────────────────
# Keyed by frozenset of two candidate tree base names (without vehicle suffix).

def _base(tree_id: str) -> str:
    """Strip vehicle suffix: 'no_crank_motorcycle' → 'no_crank'."""
    for suffix in (
        "_motorcycle", "_truck", "_boat", "_generator", "_atv", "_pwc", "_rv",
        "_excavator", "_tractor", "_loader", "_skid_steer", "_heavy_equipment",
    ):
        if tree_id.endswith(suffix):
            return tree_id[: -len(suffix)]
    return tree_id


_DISCRIMINATOR_LIBRARY: dict[frozenset, list[DiscriminatorQuestion]] = {
    frozenset({"no_crank", "crank_no_start"}): [
        DiscriminatorQuestion(
            question=(
                "When you turn the ignition key (or press the start button), "
                "does the engine turn over with a cranking sound, "
                "or does nothing happen (silence, single click, or rapid clicking)?"
            ),
            commit_map=[
                (["cranks", "turns over", "cranking", "grinding", "trying to start", "rrr"], "crank_no_start"),
                (["nothing", "silent", "silence", "click", "clicking", "dead", "no sound", "no noise"], "no_crank"),
            ],
            fallback_tree="no_crank",
        )
    ],
    frozenset({"rough_idle", "crank_no_start"}): [
        DiscriminatorQuestion(
            question=(
                "Does the engine start and run (even if poorly), "
                "or does it crank without ever catching and running?"
            ),
            commit_map=[
                (["starts", "runs", "running", "idling", "started", "fires up", "it starts"], "rough_idle"),
                (["won't start", "doesn't start", "cranks but", "cranking but", "never starts", "no start"], "crank_no_start"),
            ],
            fallback_tree="rough_idle",
        )
    ],
    frozenset({"loss_of_power", "rough_idle"}): [
        DiscriminatorQuestion(
            question=(
                "Is the primary problem that the engine runs roughly / misfires at idle, "
                "or that it lacks power / hesitates when accelerating?"
            ),
            commit_map=[
                (["rough", "idle", "misfire", "shaking", "vibrating", "stalling", "stall"], "rough_idle"),
                (["power", "acceleration", "hesitat", "sluggish", "slow", "won't accelerate"], "loss_of_power"),
            ],
            fallback_tree="rough_idle",
        )
    ],
    frozenset({"overheating", "visible_leak"}): [
        DiscriminatorQuestion(
            question=(
                "Is the main concern a fluid leak you can see (drip, puddle, or wet spot), "
                "or is the engine running hot / temperature warning light on?"
            ),
            commit_map=[
                (["leak", "drip", "puddle", "wet", "fluid", "spot", "stain"], "visible_leak"),
                (["hot", "overheat", "temperature", "temp", "steam", "boiling", "gauge"], "overheating"),
            ],
            fallback_tree="overheating",
        )
    ],
    frozenset({"brakes", "suspension"}): [
        DiscriminatorQuestion(
            question=(
                "Is the problem primarily when braking (pedal feel, stopping distance, noise when braking), "
                "or is it a ride/handling issue (bouncing, pulling, clunking over bumps)?"
            ),
            commit_map=[
                (["brake", "pedal", "stopping", "braking", "abs", "pad"], "brakes"),
                (["bump", "bounce", "clunk", "rattle", "handling", "ride", "steering", "pull"], "suspension"),
            ],
            fallback_tree="brakes",
        )
    ],
    frozenset({"hydraulic_loss", "implement_failure"}): [
        DiscriminatorQuestion(
            question=(
                "When the problem happens — does it affect all hydraulic functions "
                "(boom, arm, bucket, swing, and travel all feel slow or weak), "
                "or is it limited to one specific function while the others still work normally?"
            ),
            commit_map=[
                (
                    ["all", "everything", "every", "both", "total", "nothing works",
                     "all functions", "all circuits", "whole machine", "entire"],
                    "hydraulic_loss",
                ),
                (
                    ["just", "only", "one", "specific", "swing only", "bucket only",
                     "single", "that one", "one function", "one circuit"],
                    "implement_failure",
                ),
            ],
            fallback_tree="hydraulic_loss",
        )
    ],
}


def get_discriminator_questions(candidates: list[TreeCandidate]) -> list[DiscriminatorQuestion]:
    """
    Return 1–2 questions that best differentiate the top two candidate trees.
    Falls back to a generic vehicle-type clarifier if the pair isn't in the library.
    """
    if len(candidates) < 2:
        return []

    top_base = _base(candidates[0].tree_id)
    second_base = _base(candidates[1].tree_id)
    key = frozenset({top_base, second_base})

    if key in _DISCRIMINATOR_LIBRARY:
        return _DISCRIMINATOR_LIBRARY[key]

    # No specific discriminator for this pair — commit to the top candidate.
    # Never expose internal tree names to the user.
    return []


def resolve_discriminator_answer(
    question: DiscriminatorQuestion,
    user_answer: str,
    candidates: list[TreeCandidate],
) -> str:
    """
    Match user's answer to one of the candidate trees.
    Returns the tree_id to commit to.
    """
    lower = user_answer.lower()

    for keywords, tree_id in question.commit_map:
        if any(kw in lower for kw in keywords):
            # Make sure the committed tree actually exists in our candidates
            candidate_ids = {c.tree_id for c in candidates}
            # Also accept base-name matches (e.g., "crank_no_start" matches "crank_no_start_motorcycle")
            for cid in candidate_ids:
                if cid == tree_id or cid.startswith(tree_id):
                    return cid
            # If exact match doesn't exist, return as-is (may be base car tree)
            return tree_id

    # No keyword match — fall back to primary candidate
    return candidates[0].tree_id
