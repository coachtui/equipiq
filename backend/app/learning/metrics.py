"""
Learning system — hypothesis performance metrics.

Aggregates diagnostic_outcomes to produce per-hypothesis performance data.
The pure _metrics_from_aggregates() function is separated for testability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class HypothesisMetrics:
    hypothesis_id: str
    total_cases: int
    resolution_rate: float   # fraction of sessions that were resolved
    reversal_rate: float     # fraction where top prediction was wrong (despite resolution)
    avg_confidence: float    # average final score for this hypothesis across sessions
    avg_rating: float        # average user rating for sessions where this was top hypothesis


# ── Pure computation (testable without DB) ────────────────────────────────────

def _metrics_from_aggregates(
    rows: list[dict[str, Any]],
    avg_confidences: dict[str, float],
) -> dict[str, HypothesisMetrics]:
    """
    Compute HypothesisMetrics from pre-aggregated query rows + JSONB averages.

    rows fields: hypothesis_id, total_cases, resolved_count, reversal_count, avg_rating
    avg_confidences: {hypothesis_id: float}
    """
    result: dict[str, HypothesisMetrics] = {}
    for r in rows:
        hyp_id = r["hypothesis_id"]
        total = int(r["total_cases"])
        resolved = int(r.get("resolved_count") or 0)
        reversals = int(r.get("reversal_count") or 0)

        result[hyp_id] = HypothesisMetrics(
            hypothesis_id=hyp_id,
            total_cases=total,
            resolution_rate=round(resolved / total, 4) if total > 0 else 0.0,
            reversal_rate=round(reversals / total, 4) if total > 0 else 0.0,
            avg_confidence=round(avg_confidences.get(hyp_id, 0.0), 4),
            avg_rating=round(float(r.get("avg_rating") or 0.0), 4),
        )
    return result


# ── DB-backed computation ─────────────────────────────────────────────────────

async def compute_hypothesis_metrics(db: AsyncSession) -> dict[str, HypothesisMetrics]:
    """
    Aggregate performance across all recorded outcomes, grouped by top_hypothesis.
    """
    agg_rows = await db.execute(text("""
        SELECT
            top_hypothesis                                                  AS hypothesis_id,
            COUNT(*)                                                        AS total_cases,
            SUM(CASE WHEN was_resolved = TRUE THEN 1 ELSE 0 END)           AS resolved_count,
            SUM(CASE
                    WHEN was_resolved = TRUE
                         AND resolution_confirmed_hypothesis IS NOT NULL
                         AND resolution_confirmed_hypothesis != top_hypothesis
                    THEN 1 ELSE 0 END)                                     AS reversal_count,
            AVG(rating)                                                     AS avg_rating
        FROM diagnostic_outcomes
        WHERE top_hypothesis IS NOT NULL
        GROUP BY top_hypothesis
    """))
    rows = [dict(r) for r in agg_rows.mappings()]

    if not rows:
        return {}

    # Fetch average confidence per hypothesis from the JSONB array
    avg_confidences = await _fetch_avg_confidences(db, [r["hypothesis_id"] for r in rows])

    return _metrics_from_aggregates(rows, avg_confidences)


async def _fetch_avg_confidences(db: AsyncSession, hypothesis_ids: list[str]) -> dict[str, float]:
    """
    Extract average final score for each hypothesis from the final_hypotheses JSONB array.
    """
    if not hypothesis_ids:
        return {}

    result = await db.execute(text("""
        SELECT
            h->>'key'             AS hypothesis_id,
            AVG((h->>'score')::float) AS avg_score
        FROM diagnostic_outcomes,
             jsonb_array_elements(final_hypotheses) AS h
        WHERE h->>'key' = ANY(:ids)
          AND top_hypothesis = h->>'key'
        GROUP BY h->>'key'
    """), {"ids": hypothesis_ids})

    return {r["hypothesis_id"]: float(r["avg_score"]) for r in result.mappings()}
