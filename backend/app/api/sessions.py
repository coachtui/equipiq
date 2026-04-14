"""
Session API — handles the full diagnostic conversation lifecycle.

POST /api/sessions              Create session + return first question
POST /api/sessions/{id}/message Send answer + get next question or result
GET  /api/sessions/{id}         Get session state
"""
import logging
import os
import subprocess
import tempfile
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datetime import datetime, timezone

from fix_core.models.context import OwnerContext
from fix_core.models.hypothesis import HypothesisScore
from fix_core.models.result import DiagnosticResult as CoreDiagnosticResult, SynthesizedCause
from fix_core.models.session import (
    DiagnosticSession as CoreSession,
    MessageRole,
    MessageType,
    RoutingPhase,
    SessionMessage as CoreSessionMessage,
    SessionMode,
    SessionState,
)

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.events import LoggingEventEmitter
from app.db.session_repository import PostgresSessionRepository
from app.llm.claude_provider import ClaudeProvider as _ClaudeProvider
from app.core.rate_limit import limiter
from app.diagnostics.orchestrator.controller import ControllerResult, initialise_routing, process_message
from app.diagnostics.orchestrator.evidence import build_intake_packet
from app.diagnostics.orchestrator.safety import evaluate_safety
from app.engine.context_heavy import HeavyContext, apply_heavy_context_priors
from app.engine.diagnostic_engine import DiagnosticEngine
from app.engine.hypothesis_scorer import HypothesisScorer
from app.engine.trees import CONTEXT_PRIORS, HYPOTHESES, POST_DIAGNOSIS, TREES, resolve_tree_key
from app.learning.outcomes import record_outcome, update_outcome_feedback
from app.learning.weights import get_approved_multipliers
from app.llm.anomaly_detector import ANOMALY_EXIT_THRESHOLD, detect_anomaly
from app.llm.evidence_extractor import extract_evidence
from app.llm.routing_hints import suggest_tree_candidates
from app.llm.shadow_hypotheses import generate_shadow_hypotheses
from app.models.session import (
    DiagnosticSession as OrmSession,
    MediaAttachment,
    SessionFeedback,
    SessionHypothesis,
    SessionMessage,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class VehicleInput(BaseModel):
    year: int | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None


class HeavyEquipmentContextInput(BaseModel):
    hours_of_operation: int | None = None
    last_service_hours: int | None = None
    environment: str | None = None          # dusty | muddy | marine | urban
    storage_duration: int | None = None     # days since last use
    recent_work_type: str | None = None


class CreateSessionRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=2000)
    vehicle: VehicleInput | None = None
    heavy_context: HeavyEquipmentContextInput | None = None
    session_mode: str = "consumer"          # consumer | operator | mechanic


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class RankedCause(BaseModel):
    cause: str
    confidence: float
    reasoning: str


class SuggestedPart(BaseModel):
    name: str
    notes: str = ""


class DiagnosticResultOut(BaseModel):
    ranked_causes: list[RankedCause]
    next_checks: list[str] = []
    diy_difficulty: str | None = None
    suggested_parts: list[SuggestedPart]
    escalation_guidance: str | None
    confidence_level: float
    post_diagnosis: list[str] = []
    fault_isolation_steps: list[str] = []
    service_reference: str | None = None


class MessageResponse(BaseModel):
    session_id: str
    message: str
    msg_type: str   # "question" | "result" | "error" | "safety" | "clarify"
    turn: int
    result: DiagnosticResultOut | None = None
    safety_alerts: list[dict] | None = None         # Phase 9: populated when safety interrupt fires
    shadow_hypotheses: list[dict] | None = None     # Phase 9.5: LLM alternative possibilities


class SessionStateResponse(BaseModel):
    session_id: str
    status: str
    turn_count: int
    symptom_category: str | None
    vehicle_type: str = "car"
    vehicle: VehicleInput
    messages: list[dict]
    result: DiagnosticResultOut | None = None


class SessionSummary(BaseModel):
    session_id: str
    created_at: str
    status: str
    symptom_category: str | None
    vehicle_year: int | None
    vehicle_make: str | None
    vehicle_model: str | None
    vehicle_type: str = "car"
    excerpt: str  # first user message, truncated
    top_cause: str | None = None  # top ranked cause from most recent result


class CompleteSessionResponse(BaseModel):
    session_id: str
    status: str


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    session_id: str
    rating: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — use core insert/update to avoid ORM lazy-load on relationships
# ─────────────────────────────────────────────────────────────────────────────

def _vehicle_context(session: OrmSession) -> str:
    parts = [str(session.vehicle_year or ""), session.vehicle_make or "",
             session.vehicle_model or "", session.vehicle_engine or ""]
    joined = " ".join(p for p in parts if p)
    return joined.strip() or "Unknown vehicle"


async def _load_session(db: AsyncSession, session_id: str) -> OrmSession | None:
    result = await db.execute(
        select(OrmSession)
        .where(OrmSession.id == session_id)
        .options(
            selectinload(OrmSession.messages),
            selectinload(OrmSession.hypotheses),
            selectinload(OrmSession.result),
        )
    )
    return result.scalar_one_or_none()


def _get_tree_key(session: OrmSession) -> str:
    """Return the resolved tree key for a session, with fallback for legacy sessions."""
    stored = (session.context or {}).get("tree_key")
    if stored and stored in TREES:
        return stored
    # Fallback: old sessions without tree_key in context
    return session.symptom_category or "unknown"


def _get_scorer(session: OrmSession) -> HypothesisScorer:
    tree_key = _get_tree_key(session)
    if tree_key not in HYPOTHESES:
        raise HTTPException(400, f"No hypothesis set for tree key: {tree_key}")
    saved = [
        {"key": h.hypothesis_key, "score": h.score, "eliminated": h.eliminated, "evidence": h.evidence}
        for h in session.hypotheses
    ]
    return HypothesisScorer.from_serializable(HYPOTHESES[tree_key], saved)


# Module-level provider (stateless — safe as singleton)
_provider = _ClaudeProvider()


def _make_message(
    session_id: uuid.UUID,
    role: MessageRole,
    content: str,
    msg_type: MessageType,
) -> CoreSessionMessage:
    """Create a new CoreSessionMessage with a fresh UUID and current timestamp."""
    return CoreSessionMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        created_at=datetime.now(timezone.utc),
        role=role,
        content=content,
        msg_type=msg_type,
    )


class _OutcomeAdaptor:
    """
    Duck-type shim allowing record_outcome() to accept CoreSession.
    record_outcome() accesses only these five attributes.
    """
    def __init__(self, s: CoreSession) -> None:
        self.id = str(s.id)
        self.evidence_log = s.evidence_log
        self.contradiction_flags = s.contradiction_flags
        self.safety_flags = s.safety_flags
        self.selected_tree = s.selected_tree
        self.symptom_category = s.symptom_category


async def _build_result_core(
    db: AsyncSession,
    core_session: CoreSession,
    scorer: HypothesisScorer,
) -> DiagnosticResultOut:
    """
    Build the diagnostic result using a CoreSession aggregate.

    Side-effects on core_session (all picked up by caller's repo.save()):
      - core_session.result   → CoreDiagnosticResult (persisted by repo.save())
      - core_session.status   → SessionState.awaiting_followup
      - core_session.context  → adds "top_cause" key

    Calls record_outcome() via _OutcomeAdaptor duck type.
    DiagnosticResult persistence is owned by repo.save() — no direct SQL here.
    """
    tree_key = (core_session.context or {}).get("tree_key", core_session.symptom_category or "")
    ranked = scorer.ranked()  # list[Hypothesis] — has parts + diy_difficulty for claude.py

    synth = await _provider.synthesize_result(core_session, ranked)

    db_next_checks = synth.fault_isolation_steps or synth.next_checks

    # Preserve existing result id on re-synthesis; generate fresh id for new results
    result_id = core_session.result.id if core_session.result is not None else uuid.uuid4()
    core_session.result = CoreDiagnosticResult(
        id=result_id,
        session_id=core_session.id,
        created_at=datetime.now(timezone.utc),
        ranked_causes=synth.ranked_causes,
        next_checks=db_next_checks,
        diy_difficulty=synth.diy_difficulty,
        suggested_parts=synth.suggested_parts,
        escalation_guidance=synth.escalation_guidance,
        confidence_level=synth.confidence_level,
    )

    top_cause = synth.ranked_causes[0].cause if synth.ranked_causes else None
    core_session.context = {**(core_session.context or {}), "top_cause": top_cause}
    core_session.status = SessionState.awaiting_followup

    # Phase 10: record outcome using duck-type adaptor
    await record_outcome(_OutcomeAdaptor(core_session), scorer, db)

    return DiagnosticResultOut(
        ranked_causes=[
            RankedCause(cause=sc.cause, confidence=sc.confidence, reasoning=sc.reasoning)
            for sc in synth.ranked_causes
        ],
        next_checks=synth.next_checks,
        diy_difficulty=synth.diy_difficulty,
        suggested_parts=[SuggestedPart(**p) if isinstance(p, dict) else p for p in synth.suggested_parts],
        escalation_guidance=synth.escalation_guidance,
        confidence_level=synth.confidence_level or 0.0,
        fault_isolation_steps=synth.fault_isolation_steps,
        service_reference=synth.service_reference,
        post_diagnosis=POST_DIAGNOSIS.get(tree_key, []),
    )


async def _handle_followup_core(
    session_id: str,
    content: str,
    core_session: CoreSession,
    repo: PostgresSessionRepository,
    db: AsyncSession,
) -> MessageResponse:
    """Handle a follow-up message after initial diagnosis, using CoreSession + repo."""
    turn = core_session.turn_count + 1
    _sid = UUID(session_id)

    core_session.messages.append(
        _make_message(_sid, MessageRole.user, content, MessageType.chat)
    )

    # Build scorer from core_session.hypotheses
    tree_key = (core_session.context or {}).get(
        "tree_key", core_session.selected_tree or core_session.symptom_category or ""
    )
    if tree_key not in HYPOTHESES:
        raise HTTPException(400, f"No hypothesis set for tree key: {tree_key}")
    saved_hyps = [
        {"key": h.key, "score": h.score, "eliminated": h.eliminated, "evidence": h.evidence}
        for h in core_session.hypotheses
    ]
    scorer = HypothesisScorer.from_serializable(HYPOTHESES[tree_key], saved_hyps)

    followup_result = await _provider.interpret_followup(content, core_session)

    deltas: dict[str, float] = followup_result.score_deltas
    for key, delta in deltas.items():
        if key in scorer.hypotheses and not scorer.hypotheses[key].eliminated:
            h = scorer.hypotheses[key]
            h.score = max(0.0, min(1.0, h.score + delta))
            h.evidence.append(f"Follow-up: {content[:80]}")

    core_session.hypotheses = [
        HypothesisScore(
            key=h.key, label=h.label, score=h.score,
            eliminated=h.eliminated, evidence=list(h.evidence),
        )
        for h in scorer.hypotheses.values()
    ]

    from app.diagnostics.orchestrator.contradictions import detect_contradictions, merge_flags
    from app.diagnostics.orchestrator.evidence import build_from_followup
    followup_packet = build_from_followup(
        interpretation=followup_result.interpretation,
        score_deltas=deltas,
        user_text=content,
    )
    updated_evidence = list(core_session.evidence_log) + [followup_packet.to_dict()]
    hyp_state = {k: {"score": h.score, "eliminated": h.eliminated} for k, h in scorer.hypotheses.items()}
    new_contradictions = detect_contradictions(updated_evidence, current_hypotheses=hyp_state)
    updated_contradictions = merge_flags(list(core_session.contradiction_flags), new_contradictions)

    core_session.evidence_log = updated_evidence
    core_session.contradiction_flags = updated_contradictions
    core_session.turn_count = turn

    interpretation = followup_result.interpretation or "Got it. Updating the diagnosis based on your findings."
    refined = await _build_result_core(db, core_session, scorer)
    result_text = _format_result_text(refined, session_mode=core_session.session_mode.value, vehicle_type=core_session.vehicle_type or "")

    core_session.messages.append(_make_message(_sid, MessageRole.assistant, interpretation, MessageType.chat))
    core_session.messages.append(_make_message(_sid, MessageRole.assistant, result_text, MessageType.result))

    await repo.save(core_session)

    return MessageResponse(
        session_id=session_id,
        message=interpretation,
        msg_type="result",
        turn=turn,
        result=refined,
    )


async def _upsert_hypothesis(db: AsyncSession, session_id: str, scorer: HypothesisScorer) -> None:
    """Insert or update all hypotheses for a session."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    for h in scorer.hypotheses.values():
        stmt = pg_insert(SessionHypothesis).values(
            session_id=session_id,
            hypothesis_key=h.key,
            score=h.score,
            eliminated=h.eliminated,
            evidence=h.evidence,
        ).on_conflict_do_update(
            index_elements=["session_id", "hypothesis_key"],
            set_={"score": h.score, "eliminated": h.eliminated, "evidence": h.evidence},
        )
        await db.execute(stmt)
    await db.flush()


async def _add_message(db: AsyncSession, session_id: str, role: str, content: str, msg_type: str = "chat") -> None:
    await db.execute(
        insert(SessionMessage).values(
            session_id=session_id, role=role, content=content, msg_type=msg_type
        )
    )
    await db.flush()


# _build_result() removed — replaced by _build_result_core() above (CoreSession-based).
# All exit paths in send_message() now use _build_result_core().


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_session_create)
async def create_session(
    request: Request,
    req: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    vehicle_hint = req.vehicle.model_dump() if req.vehicle else None
    classified = await _provider.intake_classify(req.description, vehicle_hint)

    symptom_category = classified.symptom_category or "unknown"
    vehicle_type = classified.vehicle_type or "car"

    if symptom_category not in TREES and symptom_category != "unknown":
        # resolve_tree_key will handle unsupported category below
        pass

    if symptom_category == "unknown" or (symptom_category not in TREES and f"{symptom_category}_{vehicle_type}" not in TREES):
        if symptom_category == "unknown":
            detail = (
                "I wasn't able to identify a clear engine or drivetrain symptom from your description. "
                "Try describing what the engine or machine does (or doesn't do) more specifically — "
                "for example: 'won't start', 'starts but feels weak', 'rough idle', or 'knocking noise'."
            )
        else:
            readable = symptom_category.replace("_", " ")
            detail = (
                f"I recognized this as a '{readable}' issue, but that diagnostic tree isn't available yet. "
                f"Currently supported: no crank, crank no start, rough idle, loss of power, "
                f"strange noise, visible leak, overheating, check engine light, brakes, "
                f"transmission, suspension, and HVAC. More symptom types are coming soon."
            )
        return MessageResponse(
            session_id="",
            message=detail,
            msg_type="error",
            turn=0,
        )

    tree_key = resolve_tree_key(symptom_category, vehicle_type)

    # Phase 9: run orchestrator routing to determine if discriminator is needed
    _routing = initialise_routing({**classified.model_dump(), "tree_key": tree_key})
    routing_phase: str = _routing["routing_phase"]
    selected_tree: str = _routing["selected_tree"] or tree_key
    discriminator_candidates: list = _routing["discriminator_candidates"]
    discriminator_question: str | None = _routing["discriminator_question"]

    # Phase 9.5: merge LLM routing hints with deterministic candidates (non-fatal)
    _vctx_for_hints = " ".join(filter(None, [
        str(classified.vehicle_year or ""),
        classified.vehicle_make or "",
        classified.vehicle_model or "",
        classified.vehicle_engine or "",
    ])).strip() or "Unknown vehicle"
    try:
        from app.diagnostics.orchestrator.discriminator import get_discriminator_questions as _get_disc_qs
        from app.diagnostics.orchestrator.tree_router import (
            TreeCandidate as _TC,
            combine_candidates,
            should_use_discriminator as _should_disc,
        )
        _llm_hints = suggest_tree_candidates(
            req.description, symptom_category, _vctx_for_hints, discriminator_candidates
        )
        if _llm_hints and discriminator_candidates:
            _det_objs = [_TC(**c) for c in discriminator_candidates]
            _merged = combine_candidates(_det_objs, _llm_hints)
            discriminator_candidates = [
                {"tree_id": c.tree_id, "score": c.score, "reasons": c.reasons}
                for c in _merged
            ]
            if _should_disc(_merged):
                _disc_q = _get_disc_qs(_merged)
                if _disc_q:
                    routing_phase = "candidate"
                    selected_tree = _merged[0].tree_id
                    discriminator_question = _disc_q[0].question
            elif routing_phase == "candidate":
                routing_phase = "committed"
                selected_tree = _merged[0].tree_id
                discriminator_question = None
    except Exception:
        pass  # deterministic routing unchanged

    # Phase 9: safety check on intake description
    intake_safety = evaluate_safety([req.description])
    safety_flags_init: list = [a.to_dict() for a in intake_safety]

    secondary_symptom = classified.secondary_symptom
    # Validate: must be a known category, different from primary, and not "unknown"
    if secondary_symptom and (secondary_symptom == symptom_category or secondary_symptom == "unknown" or secondary_symptom not in HYPOTHESES):
        secondary_symptom = None

    _valid_context_values = {"low", "medium", "high", "cold", "hot", "temperate", "city", "highway", "mixed"}
    mileage_band = classified.mileage_band if classified.mileage_band in _valid_context_values else None
    climate = classified.climate if classified.climate in _valid_context_values else None
    usage_pattern = classified.usage_pattern if classified.usage_pattern in _valid_context_values else None

    _valid_saltwater = {"yes", "no"}
    _valid_storage = {"none", "weeks", "months", "season"}
    _valid_season_start = {"yes", "no"}
    saltwater_use = classified.saltwater_use if classified.saltwater_use in _valid_saltwater else None
    storage_time = classified.storage_time if classified.storage_time in _valid_storage else None
    first_start_of_season = classified.first_start_of_season if classified.first_start_of_season in _valid_season_start else None

    _valid_abs = {"yes", "no"}
    _valid_trans_type = {"automatic", "manual", "cvt"}
    _valid_awd = {"yes", "no"}
    abs_light_on = classified.abs_light_on if classified.abs_light_on in _valid_abs else None
    transmission_type = classified.transmission_type if classified.transmission_type in _valid_trans_type else None
    awd_4wd = classified.awd_4wd if classified.awd_4wd in _valid_awd else None

    # Validate and normalise session_mode
    _valid_modes = {"consumer", "operator", "mechanic"}
    session_mode = req.session_mode if req.session_mode in _valid_modes else "consumer"

    # Build heavy_context dict for storage and prior application
    _heavy_ctx_dict: dict = {}
    if vehicle_type == "heavy_equipment" and req.heavy_context:
        _hci = req.heavy_context
        _heavy_ctx_dict = {k: v for k, v in _hci.model_dump().items() if v is not None}

    # Generate session ID upfront — no DB flush needed
    session_id = str(uuid.uuid4())
    _csid = UUID(session_id)
    _now = datetime.now(timezone.utc)

    try:
        _rp = RoutingPhase(routing_phase)
    except ValueError:
        _rp = RoutingPhase.committed
    try:
        _sm = SessionMode(session_mode)
    except ValueError:
        _sm = SessionMode.consumer

    vehicle_year = classified.vehicle_year or (req.vehicle.year if req.vehicle else None)
    vehicle_make = classified.vehicle_make or (req.vehicle.make if req.vehicle else None)
    vehicle_model = classified.vehicle_model or (req.vehicle.model if req.vehicle else None)
    vehicle_engine = classified.vehicle_engine or (req.vehicle.engine if req.vehicle else None)

    core_session = CoreSession(
        id=_csid,
        owner=OwnerContext(user_id=UUID(current_user.id)),
        created_at=_now,
        updated_at=_now,
        status=SessionState.active,
        turn_count=1,
        answered_nodes=0,
        vehicle_type=vehicle_type,
        vehicle_year=vehicle_year,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        vehicle_engine=vehicle_engine,
        symptom_category=symptom_category,
        initial_description=req.description,
        current_node_id="start",
        routing_phase=_rp,
        selected_tree=selected_tree,
        evidence_log=[],
        contradiction_flags=[],
        safety_flags=safety_flags_init,
        shadow_hypotheses=[],
        session_mode=_sm,
        heavy_context=_heavy_ctx_dict,
        context={
            "tree_key": tree_key,
            "secondary_symptom": secondary_symptom,
            "mileage_band": mileage_band,
            "climate": climate,
            "usage_pattern": usage_pattern,
            "saltwater_use": saltwater_use,
            "storage_time": storage_time,
            "first_start_of_season": first_start_of_season,
            "abs_light_on": abs_light_on,
            "transmission_type": transmission_type,
            "awd_4wd": awd_4wd,
            "discriminator_candidates": discriminator_candidates,
        },
    )

    # Phase 10: apply any admin-approved weight multipliers to priors
    _approved_multipliers = await get_approved_multipliers(db)
    scorer = HypothesisScorer(HYPOTHESES[selected_tree], weight_multipliers=_approved_multipliers)

    # Apply cross-tree prior boost: hypotheses that appear in both trees get +0.05
    if secondary_symptom:
        secondary_tree_key = resolve_tree_key(secondary_symptom, vehicle_type)
        secondary_hyp_keys = set(HYPOTHESES.get(secondary_tree_key, {}).keys())
        for h in scorer.hypotheses.values():
            if h.key in secondary_hyp_keys and not h.eliminated:
                h.score = min(1.0, h.score + 0.05)
                h.evidence.append(f"Secondary symptom: {secondary_symptom.replace('_', ' ')}")

    # Apply context priors if this tree has them
    context_prior_deltas: dict[str, float] = {}
    tree_context_priors = CONTEXT_PRIORS.get(selected_tree, {})
    if tree_context_priors:
        context_fields = {
            "climate": climate,
            "mileage_band": mileage_band,
            "usage_pattern": usage_pattern,
            "saltwater_use": saltwater_use,
            "storage_time": storage_time,
            "first_start_of_season": first_start_of_season,
            "abs_light_on": abs_light_on,
            "transmission_type": transmission_type,
            "awd_4wd": awd_4wd,
        }
        for field_name, field_value in context_fields.items():
            if field_value and field_name in tree_context_priors:
                field_deltas = tree_context_priors[field_name].get(field_value, {})
                for hyp_key, delta in field_deltas.items():
                    if hyp_key in scorer.hypotheses and not scorer.hypotheses[hyp_key].eliminated:
                        h = scorer.hypotheses[hyp_key]
                        h.score = max(0.0, min(1.0, h.score + delta))
                        h.evidence.append(f"Context ({field_name}={field_value}): prior adjusted")
                        context_prior_deltas[hyp_key] = context_prior_deltas.get(hyp_key, 0.0) + delta

    # Apply heavy equipment context priors (hours-band + environment)
    if vehicle_type == "heavy_equipment" and _heavy_ctx_dict:
        _hctx = HeavyContext(
            hours_of_operation=_heavy_ctx_dict.get("hours_of_operation", 0),
            last_service_hours=_heavy_ctx_dict.get("last_service_hours", 0),
            environment=_heavy_ctx_dict.get("environment", "urban"),
            storage_duration=_heavy_ctx_dict.get("storage_duration", 0),
            recent_work_type=_heavy_ctx_dict.get("recent_work_type", ""),
        )
        _heavy_deltas = apply_heavy_context_priors(_hctx, selected_tree)
        for hyp_key, delta in _heavy_deltas.items():
            if hyp_key in scorer.hypotheses and not scorer.hypotheses[hyp_key].eliminated:
                h = scorer.hypotheses[hyp_key]
                h.score = max(0.0, min(1.0, h.score + delta))
                h.evidence.append("Heavy equipment context prior adjusted")
                context_prior_deltas[hyp_key] = context_prior_deltas.get(hyp_key, 0.0) + delta

    # Phase 9: build intake evidence packet
    intake_packet = build_intake_packet(req.description, context_prior_deltas)
    initial_evidence_log = [intake_packet.to_dict()]

    # Phase 9.5: extract structured signals from intake text and append to evidence log
    try:
        _extracted = extract_evidence(req.description, symptom_category, _vctx_for_hints)
        for _sig in _extracted:
            initial_evidence_log.append({
                "source": "intake",
                "observation": _sig["observation"],
                "normalized_key": _sig["normalized_key"],
                "certainty": _sig["certainty"],
                "affects": {},
            })
    except Exception:
        pass  # intake_packet is sufficient

    core_session.hypotheses = [
        HypothesisScore(
            key=h.key, label=h.label, score=h.score,
            eliminated=h.eliminated, evidence=list(h.evidence),
        )
        for h in scorer.hypotheses.values()
    ]
    core_session.evidence_log = initial_evidence_log
    core_session.messages.append(
        _make_message(_csid, MessageRole.user, req.description, MessageType.chat)
    )

    _repo = PostgresSessionRepository(db)

    # Phase 9: if routing_phase == "candidate", ask discriminator question first
    if routing_phase == "candidate" and discriminator_question:
        core_session.messages.append(
            _make_message(_csid, MessageRole.assistant, discriminator_question, MessageType.chat)
        )
        await _repo.save(core_session)
        return MessageResponse(
            session_id=session_id,
            message=discriminator_question,
            msg_type="question",
            turn=1,
            safety_alerts=[a.to_dict() for a in intake_safety] if intake_safety else None,
        )

    # Normal path: get and rephrase first tree question
    engine = DiagnosticEngine(selected_tree)
    node = engine.get_node("start")
    first_q = await _provider.rephrase_question(
        question=node["question"],
        options=[opt["label"] for opt in node["options"]],
        vehicle_context=core_session.vehicle_context,
        turn=1,
        session_mode=session_mode,
    )

    core_session.messages.append(
        _make_message(_csid, MessageRole.assistant, first_q, MessageType.chat)
    )
    await _repo.save(core_session)

    return MessageResponse(
        session_id=session_id,
        message=first_q,
        msg_type="question",
        turn=1,
        safety_alerts=[a.to_dict() for a in intake_safety] if intake_safety else None,
    )


@router.post("/{session_id}/message", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_session_message)
async def send_message(
    request: Request,
    session_id: str,
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = PostgresSessionRepository(db)
    owner_ctx = OwnerContext(user_id=UUID(current_user.id))

    core_session = await repo.get(UUID(session_id), owner_ctx)
    if core_session is None:
        raise HTTPException(404, "Session not found")

    _sid = UUID(session_id)

    # ── Status routing ────────────────────────────────────────────────────────
    if core_session.status in (SessionState.awaiting_followup, SessionState.completed):
        return await _handle_followup_core(session_id, req.content, core_session, repo, db)
    if core_session.status != SessionState.active:
        raise HTTPException(400, f"Session is {core_session.status.value}")

    turn = core_session.turn_count + 1

    core_session.messages.append(
        _make_message(_sid, MessageRole.user, req.content, MessageType.chat)
    )

    # ── Discriminator routing phase ───────────────────────────────────────────
    if core_session.routing_phase == RoutingPhase.discriminating:
        from app.diagnostics.orchestrator.discriminator import get_discriminator_questions, resolve_discriminator_answer
        from app.diagnostics.orchestrator.tree_router import TreeCandidate

        candidates_raw = (core_session.context or {}).get("discriminator_candidates", [])
        candidates = [TreeCandidate(**c) for c in candidates_raw] if candidates_raw else []

        disc_questions = get_discriminator_questions(candidates)
        if disc_questions and candidates:
            committed_tree = resolve_discriminator_answer(disc_questions[0], req.content, candidates)
        else:
            committed_tree = core_session.selected_tree

        if committed_tree not in HYPOTHESES:
            committed_tree = core_session.selected_tree

        _disc_multipliers = await get_approved_multipliers(db)
        new_scorer = HypothesisScorer(HYPOTHESES[committed_tree], weight_multipliers=_disc_multipliers)

        tree_cp = CONTEXT_PRIORS.get(committed_tree, {})
        ctx = core_session.context or {}
        for field_name in ("climate", "mileage_band", "usage_pattern", "saltwater_use", "storage_time", "first_start_of_season", "abs_light_on", "transmission_type", "awd_4wd"):
            field_value = ctx.get(field_name)
            if field_value and field_name in tree_cp:
                for hyp_key, delta in tree_cp[field_name].get(field_value, {}).items():
                    if hyp_key in new_scorer.hypotheses and not new_scorer.hypotheses[hyp_key].eliminated:
                        h = new_scorer.hypotheses[hyp_key]
                        h.score = max(0.0, min(1.0, h.score + delta))
                        h.evidence.append(f"Context ({field_name}={field_value}): prior adjusted")

        core_session.routing_phase = RoutingPhase.committed
        core_session.selected_tree = committed_tree
        core_session.context = {**ctx, "tree_key": committed_tree}
        core_session.turn_count = turn
        core_session.hypotheses = [
            HypothesisScore(
                key=h.key, label=h.label, score=h.score,
                eliminated=h.eliminated, evidence=list(h.evidence),
            )
            for h in new_scorer.hypotheses.values()
        ]

        engine = DiagnosticEngine(committed_tree)
        node = engine.get_node("start")
        first_q = await _provider.rephrase_question(
            question=node["question"],
            options=[opt["label"] for opt in node["options"]],
            vehicle_context=core_session.vehicle_context,
            turn=turn,
            session_mode=core_session.session_mode.value,
        )
        core_session.messages.append(
            _make_message(_sid, MessageRole.assistant, first_q, MessageType.chat)
        )
        await repo.save(core_session)

        return MessageResponse(
            session_id=session_id,
            message=first_q,
            msg_type="question",
            turn=turn,
        )

    # ── Committed phase — normal Q&A with orchestration ──────────────────────
    tree_key = (core_session.context or {}).get("tree_key", core_session.selected_tree or core_session.symptom_category or "")
    if tree_key not in HYPOTHESES:
        raise HTTPException(400, f"No hypothesis set for tree key: {tree_key}")

    engine = DiagnosticEngine(tree_key)

    saved_hyps = [
        {"key": h.key, "score": h.score, "eliminated": h.eliminated, "evidence": h.evidence}
        for h in core_session.hypotheses
    ]
    scorer = HypothesisScorer.from_serializable(HYPOTHESES[tree_key], saved_hyps)

    current_node = core_session.current_node_id or "start"
    node = engine.get_node(current_node)

    # classify_answer via ClaudeProvider — returns AnswerClassification model
    classify_result_model = await _provider.classify_answer(
        question=node["question"],
        options=node["options"],   # list[dict] at runtime — ClaudeProvider forwards to claude.py
        user_answer=req.content,
        hypotheses=[],             # interface param; not used by claude.py
    )
    classify_result = classify_result_model.model_dump()  # dict for process_message()
    matched_key = classify_result["option_key"]

    # Run orchestrator
    orch_result: ControllerResult = await process_message(
        session=core_session,
        user_text=req.content,
        scorer=scorer,
        classify_result=classify_result,
        emitter=LoggingEventEmitter(),
    )

    # Update evidence/safety/contradiction state on core_session
    updated_evidence = list(core_session.evidence_log) + [p.to_dict() for p in orch_result.new_evidence_packets]
    core_session.evidence_log = updated_evidence
    core_session.contradiction_flags = orch_result.updated_contradiction_flags
    core_session.safety_flags = orch_result.updated_safety_flags

    # ── Safety interrupt ──────────────────────────────────────────────────────
    if orch_result.action == "safety_interrupt":
        alert_texts = [f"⚠️ **{a.message}**\n\n{a.recommended_action}" for a in orch_result.safety_alerts]
        safety_msg = "\n\n---\n\n".join(alert_texts)
        core_session.messages.append(
            _make_message(_sid, MessageRole.assistant, safety_msg, MessageType.safety)
        )
        core_session.turn_count = turn
        await repo.save(core_session)
        return MessageResponse(
            session_id=session_id,
            message=safety_msg,
            msg_type="safety",
            turn=turn,
            safety_alerts=[a.to_dict() for a in orch_result.safety_alerts],
        )

    # Apply option to scorer with reliability scaling
    answer_reliability = orch_result.answer_reliability
    _option = None
    for opt in node.get("options", []):
        if opt["match"] == matched_key:
            _option = opt
            break
    if _option is None and node.get("options"):
        _option = node["options"][0]

    if _option:
        scorer.apply_option(_option, node["question"], _option.get("label", matched_key))
        if answer_reliability < 1.0:
            for hyp_key, full_delta in _option.get("deltas", {}).items():
                if hyp_key in scorer.hypotheses and not scorer.hypotheses[hyp_key].eliminated:
                    h = scorer.hypotheses[hyp_key]
                    correction = full_delta * (answer_reliability - 1.0)
                    if correction != 0:
                        h.score = max(0.0, min(1.0, h.score + correction))

    # Update hypotheses on core_session from scorer
    core_session.hypotheses = [
        HypothesisScore(
            key=h.key, label=h.label, score=h.score,
            eliminated=h.eliminated, evidence=list(h.evidence),
        )
        for h in scorer.hypotheses.values()
    ]

    next_node = orch_result.next_node_id
    core_session.current_node_id = next_node
    core_session.turn_count = turn

    # ── Clarification needed ──────────────────────────────────────────────────
    if orch_result.action == "clarify":
        if orch_result.contradictions:
            clarify_msg = (
                "A couple of your answers are pointing in different directions — "
                "I want to make sure I understand the situation correctly before going further. "
                "Could you walk me through what you observed, step by step?"
            )
        else:
            clarify_msg = "Could you describe that a bit more specifically so I can give you the most accurate diagnosis?"
        core_session.messages.append(
            _make_message(_sid, MessageRole.assistant, clarify_msg, MessageType.chat)
        )
        await repo.save(core_session)
        return MessageResponse(
            session_id=session_id,
            message=clarify_msg,
            msg_type="clarify",
            turn=turn,
        )

    if turn >= settings.max_turns:
        orch_result.action = "exit"

    # ── Phase 9.5: anomaly detection — suppress early exit if anomalous ───────
    _is_early_exit = (
        orch_result.action == "exit"
        and orch_result.next_node_id is not None
        and turn < settings.max_turns
    )
    if _is_early_exit:
        try:
            _ranked_for_anomaly = [
                {"key": h.key, "label": h.label, "score": h.score}
                for h in scorer.ranked()[:5]
            ]
            _anomaly = detect_anomaly(
                intake_text=core_session.initial_description or "",
                evidence_log=updated_evidence,
                top_hypotheses=_ranked_for_anomaly,
                symptom_category=core_session.symptom_category or "",
                vehicle_context=core_session.vehicle_context,
            )
            if _anomaly["is_anomalous"] and _anomaly["severity"] >= ANOMALY_EXIT_THRESHOLD:
                orch_result.action = "clarify"
                _anomaly_q = (
                    _anomaly.get("suggested_action")
                    or "I noticed an unusual pattern in your description. Could you clarify the sequence of symptoms?"
                )
                core_session.context = {**(core_session.context or {}), "last_anomaly": _anomaly}
                core_session.messages.append(
                    _make_message(_sid, MessageRole.assistant, _anomaly_q, MessageType.chat)
                )
                await repo.save(core_session)
                return MessageResponse(
                    session_id=session_id,
                    message=_anomaly_q,
                    msg_type="clarify",
                    turn=turn,
                )
        except Exception:
            pass  # anomaly check failed — exit proceeds normally

    # ── Phase 9.5: shadow hypotheses (generated every 3 turns and at exit) ────
    _shadow: list[dict] = []
    if orch_result.action == "exit" or turn % 3 == 0:
        try:
            _shadow = generate_shadow_hypotheses(
                intake_text=core_session.initial_description or "",
                evidence_log=updated_evidence,
                top_hypotheses=[
                    {"key": h.key, "label": h.label, "score": h.score}
                    for h in scorer.ranked()[:5]
                ],
                symptom_category=core_session.symptom_category or "",
                vehicle_context=core_session.vehicle_context,
            )
            if _shadow:
                core_session.shadow_hypotheses = _shadow
        except Exception:
            pass  # non-fatal

    # ── Exit ──────────────────────────────────────────────────────────────────
    if orch_result.action == "exit":
        result_out = await _build_result_core(db, core_session, scorer)
        result_text = _format_result_text(result_out, session_mode=core_session.session_mode.value, vehicle_type=core_session.vehicle_type or "")
        core_session.messages.append(
            _make_message(_sid, MessageRole.assistant, result_text, MessageType.result)
        )
        await repo.save(core_session)
        return MessageResponse(
            session_id=session_id,
            message=result_text,
            msg_type="result",
            turn=turn,
            result=result_out,
            shadow_hypotheses=_shadow or None,
        )

    # ── Next question ─────────────────────────────────────────────────────────
    next_node_obj = engine.get_node(next_node) if next_node else None
    if not next_node_obj:
        # Tree exhausted — deliver result
        result_out = await _build_result_core(db, core_session, scorer)
        result_text = _format_result_text(result_out, session_mode=core_session.session_mode.value, vehicle_type=core_session.vehicle_type or "")
        core_session.messages.append(
            _make_message(_sid, MessageRole.assistant, result_text, MessageType.result)
        )
        await repo.save(core_session)
        return MessageResponse(
            session_id=session_id,
            message=result_text,
            msg_type="result",
            turn=turn,
            result=result_out,
        )

    next_q = await _provider.rephrase_question(
        question=next_node_obj["question"],
        options=[opt["label"] for opt in next_node_obj["options"]],
        vehicle_context=core_session.vehicle_context,
        turn=turn,
        session_mode=core_session.session_mode.value,
    )
    core_session.messages.append(
        _make_message(_sid, MessageRole.assistant, next_q, MessageType.chat)
    )
    await repo.save(core_session)

    return MessageResponse(
        session_id=session_id,
        message=next_q,
        msg_type="question",
        turn=turn,
        safety_alerts=[a.to_dict() for a in orch_result.safety_alerts] if orch_result.safety_alerts else None,
        shadow_hypotheses=_shadow or None,
    )


_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}


def _store_upload_file(file_data: bytes, session_id: str, ext: str) -> str:
    """Write upload bytes to the configured upload directory and return the path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    storage_path = os.path.join(settings.upload_dir, f"{session_id}_{uuid.uuid4().hex}{ext}")
    with open(storage_path, "wb") as fh:
        fh.write(file_data)
    return storage_path


@router.post("/{session_id}/image", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_session_image)
async def upload_image(
    request: Request,
    session_id: str,
    file: UploadFile = File(...),
    confidence_modifier: float = Form(default=0.8),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    repo = PostgresSessionRepository(db)
    owner_ctx = OwnerContext(user_id=UUID(current_user.id))
    core_session = await repo.get(UUID(session_id), owner_ctx)
    if core_session is None:
        raise HTTPException(404, "Session not found")
    if core_session.status.value not in ("active", "awaiting_followup"):
        raise HTTPException(400, f"Session is {core_session.status.value}")

    confidence_modifier = max(0.0, min(1.0, confidence_modifier))

    content_type = file.content_type or ""
    if content_type not in _IMAGE_TYPES and content_type not in _VIDEO_TYPES:
        raise HTTPException(400, f"Unsupported file type: {content_type}. Accepted: JPEG, PNG, GIF, WebP, MP4, MOV, AVI, WebM.")
    file_category = "image" if content_type in _IMAGE_TYPES else "video"

    file_data = await file.read()
    if len(file_data) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large (max {settings.max_file_size_mb} MB)")

    ext = os.path.splitext(file.filename or "")[1] or (".jpg" if file_category == "image" else ".mp4")
    storage_path = _store_upload_file(file_data, session_id, ext)

    # For video: extract a single keyframe via ffmpeg
    if file_category == "video":
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            raise HTTPException(422, "Video uploads require ffmpeg, which is not installed on this server.")
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "input_video")
            frame_path = os.path.join(tmpdir, "keyframe.jpg")
            with open(video_path, "wb") as fv:
                fv.write(file_data)
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", "-q:v", "2", frame_path],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0 or not os.path.exists(frame_path):
                raise HTTPException(422, "Could not extract a frame from the video. The file may be corrupt or unsupported.")
            with open(frame_path, "rb") as ff:
                image_data = ff.read()
        vision_media_type = "image/jpeg"
    else:
        image_data = file_data
        vision_media_type = content_type

    # Reconstruct scorer from core session state
    tree_key = (core_session.context or {}).get("tree_key", core_session.symptom_category or "")
    if tree_key not in HYPOTHESES:
        raise HTTPException(400, f"No hypothesis set for tree key: {tree_key}")
    saved_hyps = [
        {"key": h.key, "score": h.score, "eliminated": h.eliminated, "evidence": h.evidence}
        for h in core_session.hypotheses
    ]
    scorer = HypothesisScorer.from_serializable(HYPOTHESES[tree_key], saved_hyps)

    vision_result = await _provider.analyze_image(
        image_bytes=image_data,
        vehicle_context=core_session.vehicle_context,
        media_type=vision_media_type,
        symptom_category=core_session.symptom_category or "",
        ranked_hypotheses=scorer.ranked(),
        confidence_modifier=confidence_modifier,
    )

    # Persist media attachment (not in core model — direct insert before repo.save commit)
    await db.execute(
        insert(MediaAttachment).values(
            session_id=session_id,
            file_type=file_category,
            storage_path=storage_path,
            vision_analysis=vision_result.model_dump(),
            confidence_modifier=confidence_modifier,
        )
    )

    deltas: dict[str, float] = vision_result.score_deltas
    label = "Video" if file_category == "video" else "Image"
    for key, delta in deltas.items():
        if key in scorer.hypotheses and not scorer.hypotheses[key].eliminated:
            h = scorer.hypotheses[key]
            h.score = max(0.0, min(1.0, h.score + delta))
            h.evidence.append(f"{label}: {vision_result.interpretation[:80]}")

    core_session.hypotheses = [
        HypothesisScore(
            key=h.key, label=h.label, score=h.score,
            eliminated=h.eliminated, evidence=list(h.evidence),
        )
        for h in scorer.hypotheses.values()
    ]

    # Phase 9: evidence packet + contradictions + safety — all via core_session
    from app.diagnostics.orchestrator.evidence import build_from_image
    from app.diagnostics.orchestrator.contradictions import detect_contradictions, merge_flags
    from app.diagnostics.orchestrator.safety import evaluate_safety as _eval_safety
    img_packet = build_from_image(
        interpretation=vision_result.interpretation,
        score_deltas=deltas,
        confidence_modifier=confidence_modifier,
    )
    updated_img_evidence = list(core_session.evidence_log) + [img_packet.to_dict()]
    hyp_state_img = {k: {"score": h.score, "eliminated": h.eliminated} for k, h in scorer.hypotheses.items()}
    img_contradictions = detect_contradictions(updated_img_evidence, current_hypotheses=hyp_state_img)
    updated_img_contradictions = merge_flags(list(core_session.contradiction_flags), img_contradictions)

    img_safety = _eval_safety([vision_result.interpretation], list(core_session.safety_flags))
    updated_img_safety = list(core_session.safety_flags) + [a.to_dict() for a in img_safety]

    core_session.evidence_log = updated_img_evidence
    core_session.contradiction_flags = updated_img_contradictions
    core_session.safety_flags = updated_img_safety
    core_session.turn_count = core_session.turn_count + 1

    interpretation = vision_result.interpretation or f"{label} received — no clear diagnostic evidence found."
    image_url = f"/uploads/{os.path.basename(storage_path)}"
    user_msg_content = image_url if file_category == "image" else f"[{label} uploaded]"
    _sid = UUID(session_id)
    core_session.messages.append(_make_message(_sid, MessageRole.user, user_msg_content, MessageType.chat))
    core_session.messages.append(_make_message(_sid, MessageRole.assistant, interpretation, MessageType.chat))

    await repo.save(core_session)

    return MessageResponse(
        session_id=session_id,
        message=interpretation,
        msg_type="chat",
        turn=core_session.turn_count,
    )


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return recent sessions for the authenticated user, ordered by most recently updated."""
    from sqlalchemy import desc
    result = await db.execute(
        select(OrmSession)
        .options(selectinload(OrmSession.messages))
        .where(OrmSession.user_id == current_user.id)
        .order_by(desc(OrmSession.updated_at))
        .limit(limit)
    )
    sessions = result.scalars().all()

    summaries = []
    for s in sessions:
        # First user message as excerpt
        first_user = next((m for m in s.messages if m.role == "user"), None)
        excerpt = (first_user.content[:80] + "…") if first_user and len(first_user.content) > 80 else (first_user.content if first_user else "")
        summaries.append(SessionSummary(
            session_id=s.id,
            created_at=s.created_at.isoformat(),
            status=s.status,
            symptom_category=s.symptom_category,
            vehicle_year=s.vehicle_year,
            vehicle_make=s.vehicle_make,
            vehicle_model=s.vehicle_model,
            vehicle_type=s.vehicle_type or "car",
            excerpt=excerpt,
            top_cause=s.context.get("top_cause") if s.context else None,
        ))
    return summaries


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    session = await _load_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")

    result_out = None
    if session.result:
        r = session.result
        tree_key = _get_tree_key(session)
        result_out = DiagnosticResultOut(
            ranked_causes=r.ranked_causes,
            next_checks=r.next_checks,
            diy_difficulty=r.diy_difficulty,
            suggested_parts=r.suggested_parts or [],
            escalation_guidance=r.escalation_guidance,
            confidence_level=r.confidence_level or 0.0,
            post_diagnosis=POST_DIAGNOSIS.get(tree_key, []),
        )

    return SessionStateResponse(
        session_id=session.id,
        status=session.status,
        turn_count=session.turn_count,
        symptom_category=session.symptom_category,
        vehicle_type=session.vehicle_type or "car",
        vehicle=VehicleInput(
            year=session.vehicle_year,
            make=session.vehicle_make,
            model=session.vehicle_model,
            engine=session.vehicle_engine,
        ),
        messages=[
            {"role": m.role, "content": m.content, "type": m.msg_type}
            for m in session.messages
        ],
        result=result_out,
    )


@router.patch("/{session_id}/complete", response_model=CompleteSessionResponse)
async def complete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mark a session as resolved by the user."""
    session = await _load_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")
    if session.status not in ("active", "awaiting_followup"):
        raise HTTPException(400, f"Session cannot be marked complete from status: {session.status}")
    await db.execute(
        update(OrmSession)
        .where(OrmSession.id == session_id)
        .values(status="complete")
    )
    await db.commit()
    return CompleteSessionResponse(session_id=session_id, status="complete")


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete a session and all its data, including uploaded files on disk."""
    session = await _load_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")

    # Remove uploaded media files from disk before cascade delete
    media_result = await db.execute(
        select(MediaAttachment).where(MediaAttachment.session_id == session_id)
    )
    for attachment in media_result.scalars().all():
        if attachment.storage_path and os.path.exists(attachment.storage_path):
            try:
                os.remove(attachment.storage_path)
            except OSError:
                pass  # best-effort cleanup

    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(OrmSession).where(OrmSession.id == session_id)
    )
    await db.commit()


@router.post("/{session_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    session_id: str,
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Submit or update a 1–5 star rating for a session's diagnosis."""
    session = await _load_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    await db.execute(
        pg_insert(SessionFeedback).values(
            session_id=session_id,
            rating=req.rating,
            comment=req.comment,
        ).on_conflict_do_update(
            index_elements=["session_id"],
            set_={"rating": req.rating, "comment": req.comment},
        )
    )
    # Phase 10: propagate rating to outcome row for learning metrics
    await update_outcome_feedback(session_id, req.rating, db)
    await db.commit()
    return FeedbackResponse(session_id=session_id, rating=req.rating)


# ─────────────────────────────────────────────────────────────────────────────
# Result formatting
# ─────────────────────────────────────────────────────────────────────────────

_PROFESSIONAL_MODES = {"mechanic", "operator"}
_HE_VEHICLE_TYPES_RESULT = {"heavy_equipment", "tractor", "excavator", "loader", "skid_steer"}


def _format_result_text(result: DiagnosticResultOut, session_mode: str = "consumer", vehicle_type: str = "") -> str:
    professional = session_mode in _PROFESSIONAL_MODES or vehicle_type in _HE_VEHICLE_TYPES_RESULT
    lines = ["**Diagnostic Results**\n"]

    lines.append("**Likely Causes:**")
    for i, cause in enumerate(result.ranked_causes, 1):
        pct = int(cause.confidence * 100)
        lines.append(f"{i}. {cause.cause} ({pct}% confidence)")
        lines.append(f"   {cause.reasoning}")

    if professional:
        if result.fault_isolation_steps:
            lines.append("\n**Fault Isolation Steps:**")
            for step in result.fault_isolation_steps:
                lines.append(f"- {step}")
    else:
        if result.next_checks:
            lines.append("\n**Next Checks:**")
            for check in result.next_checks:
                lines.append(f"- {check}")

        if result.diy_difficulty:
            diy_labels = {
                "easy": "Easy DIY",
                "moderate": "Moderate DIY",
                "hard": "Difficult DIY",
                "seek_mechanic": "Seek a Mechanic",
            }
            lines.append(f"\n**DIY Difficulty:** {diy_labels.get(result.diy_difficulty, result.diy_difficulty)}")

    if result.suggested_parts:
        lines.append("\n**Parts:**")
        for part in result.suggested_parts:
            note = f" — {part.notes}" if part.notes else ""
            lines.append(f"- {part.name}{note}")

    if result.escalation_guidance:
        label = "**Escalation:**" if professional else "**When to see a mechanic:**"
        lines.append(f"\n{label} {result.escalation_guidance}")

    if professional and result.service_reference:
        lines.append(f"\n**Service Reference:** {result.service_reference}")

    return "\n".join(lines)
