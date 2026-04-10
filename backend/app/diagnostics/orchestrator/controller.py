"""
Orchestrator Controller — the single entry point for all user-input processing.

This controller wraps the existing diagnostic engine and adds:
  - Evidence packet construction
  - Safety interruption
  - Contradiction detection
  - Discriminator routing phase
  - Exit guard enforcement
  - Event emission at safety interrupts and session exits

The controller does NOT touch the database; all persistence is handled by the
API layer (sessions.py).  The controller receives and returns plain Python
dicts / dataclasses so it can be unit-tested without a database.

Typical call from sessions.py:
    result = await controller.process_message(session, user_text, scorer, emitter=emitter)
"""

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from fix_core.models.session import DiagnosticSession, RoutingPhase

from app.diagnostics.orchestrator.contradictions import Contradiction, detect_contradictions, merge_flags
from app.diagnostics.orchestrator.discriminator import (
    DiscriminatorQuestion,
    get_discriminator_questions,
    resolve_discriminator_answer,
)
from app.diagnostics.orchestrator.evidence import EvidencePacket, build_from_classification
from app.diagnostics.orchestrator.exit_guard import can_exit, exit_reason
from app.diagnostics.orchestrator.safety import SafetyAlert, evaluate_safety
from app.diagnostics.orchestrator.tree_router import TreeCandidate, rank_candidate_trees, should_use_discriminator
from app.engine.diagnostic_engine import DiagnosticEngine
from app.engine.hypothesis_scorer import HypothesisScorer
from app.engine.trees import TREES


# ── Controller result ────────────────────────────────────────────────────────

@dataclass
class ControllerResult:
    """Everything the API layer needs to respond to the user and persist state."""
    action: Literal[
        "ask_discriminator",   # routing phase — return a discriminator question
        "commit_tree",         # routing phase resolved — initialise tree, return first Q
        "ask_question",        # normal Q&A — return next tree question
        "safety_interrupt",    # safety alert fired — return alert, require ack
        "clarify",             # contradiction detected — return clarification prompt
        "exit",                # tree complete / early exit — produce result
    ]
    # Populated for ask_question / ask_discriminator / clarify
    next_node_id: str | None = None
    question_text: str | None = None          # raw (pre-rephrase) question text
    question_options: list[str] | None = None # option labels for rephrasing

    # Populated for commit_tree
    committed_tree: str | None = None

    # Populated for safety_interrupt
    safety_alerts: list[SafetyAlert] = field(default_factory=list)

    # Populated for clarify
    contradictions: list[Contradiction] = field(default_factory=list)

    # Always populated
    new_evidence_packets: list[EvidencePacket] = field(default_factory=list)
    updated_contradiction_flags: list[dict] = field(default_factory=list)
    updated_safety_flags: list[dict] = field(default_factory=list)
    score_deltas: dict[str, float] = field(default_factory=dict)  # net deltas to apply
    answer_reliability: float = 1.0
    exit_blocked_reason: str | None = None    # why early exit was blocked (logging)


# ── Main entry point ─────────────────────────────────────────────────────────

async def process_message(
    session: DiagnosticSession,
    user_text: str,
    scorer: HypothesisScorer,
    classify_result: dict | None = None,
    emitter: Any | None = None,
) -> ControllerResult:
    """
    Process a user message through the full orchestration pipeline.

    Args:
        session:         Canonical session aggregate (fix_core DiagnosticSession).
        user_text:       Raw user message text.
        scorer:          Live HypothesisScorer (already loaded with current scores).
        classify_result: Pre-computed classify_answer result dict (option_key,
                         classification_confidence, answer_reliability, needs_clarification).
                         Pass None if we are in the discriminator routing phase.
        emitter:         EventEmitter to fire at safety interrupts and session exits.
                         Pass None (or NoOpEventEmitter) when no event bus is wired.

    Returns:
        ControllerResult indicating what the API layer should do next.
    """
    session_id = str(session.id)
    user_id = str(session.owner.user_id)

    async def _emit(name: str, payload: dict[str, Any]) -> None:
        if emitter is not None:
            await emitter.emit(name, payload)

    result = ControllerResult(
        action="ask_question",
        updated_contradiction_flags=list(session.contradiction_flags),
        updated_safety_flags=list(session.safety_flags),
    )

    # ── Step 1: Safety check (always first) ─────────────────────────────────
    new_alerts = evaluate_safety([user_text], session.safety_flags)
    if new_alerts:
        result.updated_safety_flags = list(session.safety_flags) + [a.to_dict() for a in new_alerts]
        critical_alerts = [a for a in new_alerts if a.level == "critical"]
        if critical_alerts:
            result.action = "safety_interrupt"
            result.safety_alerts = critical_alerts
            await _emit("fix.safety.alert", {
                "session_id": session_id,
                "user_id": user_id,
                "severity": "critical",
                "message": critical_alerts[0].message,
            })
            return result
        # Non-critical (warnings) — record but don't interrupt
        result.safety_alerts = new_alerts

    # ── Step 2: Discriminator routing phase ──────────────────────────────────
    if session.routing_phase == RoutingPhase.discriminating:
        candidates: list[TreeCandidate] = session.context.get("discriminator_candidates", [])
        # Deserialise if stored as dicts
        if candidates and isinstance(candidates[0], dict):
            candidates = [TreeCandidate(**c) for c in candidates]

        disc_questions: list[DiscriminatorQuestion] = get_discriminator_questions(candidates)
        if disc_questions:
            committed = resolve_discriminator_answer(disc_questions[0], user_text, candidates)
        else:
            committed = candidates[0].tree_id if candidates else (session.selected_tree or "")

        result.action = "commit_tree"
        result.committed_tree = committed
        return result

    # ── Step 3: Build evidence packet from Q&A answer ────────────────────────
    if classify_result is None:
        # Shouldn't happen in committed phase, but guard
        return result

    option_key = classify_result.get("option_key", "")
    answer_reliability = float(classify_result.get("answer_reliability", 1.0))
    result.answer_reliability = answer_reliability

    selected_tree = session.selected_tree or ""
    current_node_id = session.current_node_id or "start"

    # Get the option dict from the current tree node for delta info
    engine = DiagnosticEngine(selected_tree)
    node = engine.get_node(current_node_id)
    matched_option = None
    if node:
        for opt in node.get("options", []):
            if opt["match"] == option_key:
                matched_option = opt
                break
    if matched_option is None and node and node.get("options"):
        matched_option = node["options"][0]

    raw_deltas: dict[str, float] = {}
    option_label = option_key
    if matched_option:
        raw_deltas = matched_option.get("deltas", {})
        option_label = matched_option.get("label", option_key)

    # Scale deltas by answer_reliability (< 0.5 = half impact)
    effective_deltas = {
        k: round(v * answer_reliability, 4) for k, v in raw_deltas.items()
    }
    result.score_deltas = effective_deltas

    packet = build_from_classification(
        option_key=option_key,
        option_label=option_label,
        deltas=raw_deltas,
        answer_reliability=answer_reliability,
        user_text=user_text,
    )
    result.new_evidence_packets = [packet]

    # ── Step 4: Update evidence log & detect contradictions ──────────────────
    updated_evidence = list(session.evidence_log) + [packet.to_dict()]

    # Serialise current hypothesis state for cross-check
    hyp_state = {
        k: {"score": h.score, "eliminated": h.eliminated}
        for k, h in scorer.hypotheses.items()
    }
    new_contradictions = detect_contradictions(updated_evidence, current_hypotheses=hyp_state)
    result.updated_contradiction_flags = merge_flags(session.contradiction_flags, new_contradictions)
    result.contradictions = new_contradictions

    # ── Step 5: Determine next node (do NOT call engine.advance — scoring is
    #            the caller's responsibility to avoid double-application)
    tree = TREES.get(selected_tree, {})
    next_node: str | None = None
    tree_says_stop: bool = True
    if matched_option:
        next_node = matched_option.get("next_node")
        if next_node and next_node in tree:
            tree_says_stop = False
    result.next_node_id = next_node

    # ── Step 6: Check if clarification is needed ─────────────────────────────
    blocking_contradictions = [c for c in new_contradictions if c.severity >= 0.5]
    if blocking_contradictions and not classify_result.get("needs_clarification"):
        result.action = "clarify"
        return result

    if classify_result.get("needs_clarification") and answer_reliability < 0.5:
        result.action = "clarify"
        return result

    # ── Step 7: Exit guard ───────────────────────────────────────────────────
    answered_after = session.answered_nodes + 1

    if tree_says_stop:
        # Tree is exhausted or option has no next_node — respect tree structure
        # but still enforce minimum node count
        if answered_after < 2:
            # Very early tree exit (only 1-2 answers) — keep going if possible
            if next_node is None:
                result.action = "exit"
                await _emit("fix.session.completed", {
                    "session_id": session_id,
                    "user_id": user_id,
                    "vehicle_type": session.vehicle_type,
                    "outcome": scorer.ranked()[0].key if scorer.ranked() else None,
                })
                return result
        result.action = "exit"
        await _emit("fix.session.completed", {
            "session_id": session_id,
            "user_id": user_id,
            "vehicle_type": session.vehicle_type,
            "outcome": scorer.ranked()[0].key if scorer.ranked() else None,
        })
        return result

    # Check exit guard before returning next question
    if can_exit(
        scorer=scorer,
        answered_nodes=answered_after,
        evidence_log=updated_evidence,
        contradiction_flags=result.updated_contradiction_flags,
    ):
        result.action = "exit"
        await _emit("fix.session.completed", {
            "session_id": session_id,
            "user_id": user_id,
            "vehicle_type": session.vehicle_type,
            "outcome": scorer.ranked()[0].key if scorer.ranked() else None,
        })
        return result
    else:
        blocked = exit_reason(
            scorer=scorer,
            answered_nodes=answered_after,
            evidence_log=updated_evidence,
            contradiction_flags=result.updated_contradiction_flags,
        )
        result.exit_blocked_reason = blocked

    # ── Step 8: Return next question ─────────────────────────────────────────
    if next_node and next_node in TREES.get(selected_tree, {}):
        next_node_obj = engine.get_node(next_node)
        if next_node_obj:
            result.action = "ask_question"
            result.next_node_id = next_node
            result.question_text = next_node_obj["question"]
            result.question_options = [opt["label"] for opt in next_node_obj["options"]]
    else:
        result.action = "exit"
        await _emit("fix.session.completed", {
            "session_id": session_id,
            "user_id": user_id,
            "vehicle_type": session.vehicle_type,
            "outcome": scorer.ranked()[0].key if scorer.ranked() else None,
        })

    return result


# ── Session initialisation helper ────────────────────────────────────────────

def initialise_routing(intake_data: dict) -> dict:
    """
    Called once at session creation.  Returns a dict of orchestrator fields
    to store on the session:

        routing_phase: "candidate" | "committed"
        selected_tree: str
        discriminator_candidates: list[dict]  (stored in context)
        discriminator_question: str | None
    """
    candidates = rank_candidate_trees(intake_data)

    if not candidates:
        return {
            "routing_phase": "committed",
            "selected_tree": intake_data.get("tree_key", ""),
            "discriminator_candidates": [],
            "discriminator_question": None,
        }

    if should_use_discriminator(candidates):
        disc_questions = get_discriminator_questions(candidates)
        question_text = disc_questions[0].question if disc_questions else None
        return {
            "routing_phase": "candidate",
            "selected_tree": candidates[0].tree_id,   # tentative
            "discriminator_candidates": [
                {"tree_id": c.tree_id, "score": c.score, "reasons": c.reasons}
                for c in candidates
            ],
            "discriminator_question": question_text,
        }

    return {
        "routing_phase": "committed",
        "selected_tree": candidates[0].tree_id,
        "discriminator_candidates": [],
        "discriminator_question": None,
    }
