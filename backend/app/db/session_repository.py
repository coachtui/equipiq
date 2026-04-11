"""
PostgresSessionRepository — implements fix_core.interfaces.SessionRepository
against an async SQLAlchemy session.

Aggregate save strategy:
  1. Upsert diagnostic_sessions main row (all scalar + JSONB columns).
  2. Hypotheses — DELETE all for session, then INSERT current set.
     Small set (< 20), idempotent, avoids needing a unique constraint.
  3. Messages — INSERT … ON CONFLICT (id) DO NOTHING.
     Append-only; existing messages are skipped by PK conflict.
  4. DiagnosticResult — upserted when session.result is not None.
     ranked_causes are serialised as SynthesizedCause dicts (cause/confidence/reasoning).
     Conflict key is session_id (one result per session).
"""
from __future__ import annotations

from datetime import datetime, timezone


def _naive_utc(dt: datetime) -> datetime:
    """Strip tzinfo for TIMESTAMP WITHOUT TIME ZONE columns."""
    if dt is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

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
from app.models.session import (
    DiagnosticResult as OrmDiagnosticResult,
    DiagnosticSession as OrmSession,
    SessionHypothesis,
    SessionMessage,
)

# ORM status → CoreSession SessionState (ORM uses "complete", core uses "completed")
_STATUS_TO_CORE = {"complete": "completed"}
# CoreSession SessionState → ORM status
_STATUS_TO_ORM = {"completed": "complete"}


def _safe_msg_type(raw: str | None) -> MessageType:
    """Map ORM msg_type string to fix_core MessageType, falling back to chat."""
    try:
        return MessageType(raw or "chat")
    except ValueError:
        return MessageType.chat


def _orm_to_core(orm: OrmSession) -> CoreSession:
    """Convert a fully-loaded OrmSession to a CoreSession aggregate."""
    orm_status = _STATUS_TO_CORE.get(orm.status or "active", orm.status or "active")
    try:
        status = SessionState(orm_status)
    except ValueError:
        status = SessionState.active

    try:
        routing_phase = RoutingPhase(orm.routing_phase or "committed")
    except ValueError:
        routing_phase = RoutingPhase.committed

    try:
        session_mode = SessionMode(getattr(orm, "session_mode", "consumer") or "consumer")
    except ValueError:
        session_mode = SessionMode.consumer

    turn_count = orm.turn_count or 0

    hypotheses = [
        HypothesisScore(
            key=h.hypothesis_key,
            label=h.hypothesis_key,   # label comes from tree definition; placeholder for repo
            score=h.score,
            eliminated=h.eliminated,
            evidence=list(h.evidence or []),
        )
        for h in (orm.hypotheses or [])
    ]

    messages = [
        CoreSessionMessage(
            id=UUID(m.id),
            session_id=UUID(m.session_id),
            created_at=m.created_at,
            role=MessageRole(m.role),
            content=m.content,
            msg_type=_safe_msg_type(m.msg_type),
        )
        for m in (orm.messages or [])
    ]

    result: CoreDiagnosticResult | None = None
    if orm.result is not None:
        raw_causes = orm.result.ranked_causes or []
        ranked_causes = [
            SynthesizedCause(
                cause=c.get("cause", ""),
                confidence=float(c.get("confidence", 0.0)),
                reasoning=c.get("reasoning", ""),
            )
            for c in raw_causes
            if isinstance(c, dict)
        ]
        result = CoreDiagnosticResult(
            id=UUID(orm.result.id),
            session_id=UUID(orm.id),
            created_at=orm.result.created_at,
            ranked_causes=ranked_causes,
            next_checks=list(orm.result.next_checks or []),
            diy_difficulty=orm.result.diy_difficulty,
            suggested_parts=list(orm.result.suggested_parts or []),
            escalation_guidance=orm.result.escalation_guidance,
            confidence_level=orm.result.confidence_level,
        )

    user_id_str = orm.user_id or "00000000-0000-0000-0000-000000000000"
    try:
        user_uuid = UUID(user_id_str)
    except (ValueError, AttributeError):
        user_uuid = UUID("00000000-0000-0000-0000-000000000000")

    return CoreSession(
        id=UUID(orm.id),
        owner=OwnerContext(user_id=user_uuid),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        status=status,
        turn_count=turn_count,
        answered_nodes=max(0, turn_count - 1),
        vehicle_type=orm.vehicle_type or "car",
        vehicle_year=orm.vehicle_year,
        vehicle_make=orm.vehicle_make,
        vehicle_model=orm.vehicle_model,
        vehicle_engine=orm.vehicle_engine,
        symptom_category=orm.symptom_category,
        initial_description=getattr(orm, "initial_description", None),
        current_node_id=orm.current_node_id,
        context=dict(orm.context or {}),
        routing_phase=routing_phase,
        selected_tree=orm.selected_tree,
        evidence_log=list(orm.evidence_log or []),
        contradiction_flags=list(orm.contradiction_flags or []),
        safety_flags=list(orm.safety_flags or []),
        shadow_hypotheses=list(getattr(orm, "shadow_hypotheses", None) or []),
        session_mode=session_mode,
        heavy_context=dict(getattr(orm, "heavy_context", None) or {}),
        messages=messages,
        hypotheses=hypotheses,
        result=result,
    )


class PostgresSessionRepository:
    """
    Implements fix_core.interfaces.SessionRepository via async SQLAlchemy.

    Ownership is enforced in get(): returns None (not raises) when session
    does not exist or does not belong to context.user_id, preventing session
    ID enumeration per CLAUDE.md security standard.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID, context: OwnerContext) -> CoreSession | None:
        """Load session by ID + ownership check. Returns None on miss or wrong owner."""
        stmt = (
            select(OrmSession)
            .where(OrmSession.id == str(session_id))
            .where(OrmSession.user_id == str(context.user_id))
            .options(
                selectinload(OrmSession.messages),
                selectinload(OrmSession.hypotheses),
                selectinload(OrmSession.result),
            )
        )
        row = (await self._db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _orm_to_core(row)

    async def save(self, session: CoreSession) -> None:
        """
        Persist the full session aggregate.

        Upserts the main session row, replaces all hypotheses (DELETE + INSERT),
        and appends any new messages (INSERT … ON CONFLICT (id) DO NOTHING).
        DiagnosticResult rows are NOT touched here — see module docstring.
        """
        status_str = _STATUS_TO_ORM.get(session.status.value, session.status.value)

        # 1. Upsert main session row
        await self._db.execute(
            pg_insert(OrmSession)
            .values(
                id=str(session.id),
                user_id=str(session.owner.user_id),
                created_at=_naive_utc(session.created_at),
                updated_at=_naive_utc(session.updated_at),
                status=status_str,
                turn_count=session.turn_count,
                vehicle_year=session.vehicle_year,
                vehicle_make=session.vehicle_make,
                vehicle_model=session.vehicle_model,
                vehicle_engine=session.vehicle_engine,
                vehicle_type=session.vehicle_type,
                symptom_category=session.symptom_category,
                initial_description=session.initial_description,
                current_node_id=session.current_node_id,
                context=session.context,
                routing_phase=session.routing_phase.value,
                selected_tree=session.selected_tree,
                evidence_log=session.evidence_log,
                contradiction_flags=session.contradiction_flags,
                safety_flags=session.safety_flags,
                shadow_hypotheses=session.shadow_hypotheses,
                session_mode=session.session_mode.value,
                heavy_context=session.heavy_context,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "updated_at": func.now(),
                    "status": status_str,
                    "turn_count": session.turn_count,
                    "current_node_id": session.current_node_id,
                    "routing_phase": session.routing_phase.value,
                    "selected_tree": session.selected_tree,
                    "evidence_log": session.evidence_log,
                    "contradiction_flags": session.contradiction_flags,
                    "safety_flags": session.safety_flags,
                    "shadow_hypotheses": session.shadow_hypotheses,
                    "context": session.context,
                    "symptom_category": session.symptom_category,
                },
            )
        )

        # 2. Hypotheses — replace entire set (DELETE + INSERT)
        if session.hypotheses:
            await self._db.execute(
                delete(SessionHypothesis).where(
                    SessionHypothesis.session_id == str(session.id)
                )
            )
            for h in session.hypotheses:
                await self._db.execute(
                    insert(SessionHypothesis).values(
                        session_id=str(session.id),
                        hypothesis_key=h.key,
                        score=h.score,
                        eliminated=h.eliminated,
                        evidence=list(h.evidence),
                    )
                )

        # 3. Messages — append-only via PK conflict
        for msg in session.messages:
            await self._db.execute(
                pg_insert(SessionMessage)
                .values(
                    id=str(msg.id),
                    session_id=str(session.id),
                    created_at=_naive_utc(msg.created_at),
                    role=msg.role.value,
                    content=msg.content,
                    msg_type=msg.msg_type.value,
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )

        # 4. DiagnosticResult — upsert when present (one result per session)
        if session.result is not None:
            serialised_causes = [sc.model_dump() for sc in session.result.ranked_causes]
            await self._db.execute(
                pg_insert(OrmDiagnosticResult)
                .values(
                    id=str(session.result.id),
                    session_id=str(session.id),
                    created_at=_naive_utc(session.result.created_at),
                    ranked_causes=serialised_causes,
                    next_checks=session.result.next_checks,
                    diy_difficulty=session.result.diy_difficulty,
                    suggested_parts=session.result.suggested_parts,
                    escalation_guidance=session.result.escalation_guidance,
                    confidence_level=session.result.confidence_level,
                )
                .on_conflict_do_update(
                    index_elements=["session_id"],
                    set_={
                        "ranked_causes": serialised_causes,
                        "next_checks": session.result.next_checks,
                        "diy_difficulty": session.result.diy_difficulty,
                        "suggested_parts": session.result.suggested_parts,
                        "escalation_guidance": session.result.escalation_guidance,
                        "confidence_level": session.result.confidence_level,
                    },
                )
            )

        await self._db.commit()

    async def list(self, context: OwnerContext) -> list[CoreSession]:
        """Return all sessions for context, ordered by updated_at desc."""
        from sqlalchemy import desc
        stmt = (
            select(OrmSession)
            .where(OrmSession.user_id == str(context.user_id))
            .order_by(desc(OrmSession.updated_at))
            .options(
                selectinload(OrmSession.messages),
                selectinload(OrmSession.hypotheses),
                selectinload(OrmSession.result),
            )
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return [_orm_to_core(r) for r in rows]

    async def delete(self, session_id: UUID, context: OwnerContext) -> None:
        """Delete session if owned by context. No-op if not found or wrong owner."""
        from sqlalchemy import delete as sql_delete
        await self._db.execute(
            sql_delete(OrmSession)
            .where(OrmSession.id == str(session_id))
            .where(OrmSession.user_id == str(context.user_id))
        )
        await self._db.commit()
