"""
Learning system — outcome recording.

record_outcome(): called when a session delivers its diagnostic result (exit action).
update_outcome_feedback(): called when user submits a rating.

Outcome rows are upserted on session_id — safe to call on follow-up results too.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.hypothesis_scorer import HypothesisScorer
from app.models.session import DiagnosticOutcome, DiagnosticSession


async def record_outcome(
    session: DiagnosticSession,
    scorer: HypothesisScorer,
    db: AsyncSession,
) -> None:
    """
    Insert or update a DiagnosticOutcome row for a session that has just delivered results.

    Does NOT set was_resolved or rating — those come from user feedback.
    Safe to call multiple times (upsert on session_id).
    """
    ranked = scorer.ranked()
    top_hypothesis = ranked[0].key if ranked else None

    evidence_log: list = list(getattr(session, "evidence_log", None) or [])
    evidence_summary = {
        "count": len(evidence_log),
        "types": list({e.get("source", "unknown") for e in evidence_log}),
    }
    contradiction_count = len(list(getattr(session, "contradiction_flags", None) or []))
    safety_triggered = len(list(getattr(session, "safety_flags", None) or [])) > 0

    final_hypotheses = scorer.to_serializable()
    selected_tree = session.selected_tree or session.symptom_category

    await db.execute(
        pg_insert(DiagnosticOutcome).values(
            session_id=session.id,
            selected_tree=selected_tree,
            final_hypotheses=final_hypotheses,
            top_hypothesis=top_hypothesis,
            evidence_summary=evidence_summary,
            contradiction_count=contradiction_count,
            safety_triggered=safety_triggered,
        ).on_conflict_do_update(
            index_elements=["session_id"],
            set_={
                "selected_tree": selected_tree,
                "final_hypotheses": final_hypotheses,
                "top_hypothesis": top_hypothesis,
                "evidence_summary": evidence_summary,
                "contradiction_count": contradiction_count,
                "safety_triggered": safety_triggered,
            },
        )
    )
    await db.flush()


async def update_outcome_feedback(
    session_id: str,
    rating: int,
    db: AsyncSession,
) -> None:
    """
    Update outcome row with user rating and inferred resolution state.

    was_resolved = True  when rating >= 4 (user confirms diagnosis helped)
    was_resolved = False when rating < 4

    When resolved, resolution_confirmed_hypothesis is set to top_hypothesis
    (implicit confirmation that the system's prediction was correct).
    When not resolved, resolution_confirmed_hypothesis is left NULL.
    """
    was_resolved = rating >= 4

    await db.execute(
        text("""
            UPDATE diagnostic_outcomes
            SET
                rating       = :rating,
                was_resolved = :was_resolved,
                resolution_confirmed_hypothesis = CASE
                    WHEN :was_resolved THEN top_hypothesis
                    ELSE NULL
                END
            WHERE session_id = :session_id
        """),
        {"rating": rating, "was_resolved": was_resolved, "session_id": session_id},
    )
    await db.flush()
