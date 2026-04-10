"""
Fleet operator dashboard API — Phase 15D.

Endpoints:
  GET /api/fleet/assets                   — list all known assets with status summary
  GET /api/fleet/asset/{asset_id}/history — recent sessions for a specific asset
  GET /api/fleet/summary                  — aggregate fleet health summary

Access: requires is_operator=True OR is_admin=True (enforced by get_fleet_user dep).

NOTE: from __future__ import annotations intentionally omitted here.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_fleet_user

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


# ── Asset list ────────────────────────────────────────────────────────────────

@router.get("/assets")
async def list_fleet_assets(
    _: CurrentUser = Depends(get_fleet_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List all assets that have ever sent telemetry, with a status summary.

    Returns per asset:
      - asset_id
      - last_seen: most recent telemetry timestamp
      - session_count: number of diagnostic sessions linked to this asset
      - last_symptom: symptom_category from most recent linked session
      - last_top_cause: top_cause from most recent completed session
      - open_sessions: count of active or awaiting_followup sessions
      - last_safety_alerts: safety alerts from most recent telemetry reading
    """
    # Distinct assets with their most recent telemetry reading
    assets_q = await db.execute(text("""
        SELECT
            at.asset_id,
            MAX(at.received_at)                         AS last_seen,
            COUNT(DISTINCT ds.id)                       AS session_count,
            COUNT(DISTINCT CASE
                WHEN ds.status IN ('active', 'awaiting_followup') THEN ds.id
            END)                                        AS open_sessions
        FROM asset_telemetry at
        LEFT JOIN diagnostic_sessions ds ON ds.id = at.linked_session_id
        GROUP BY at.asset_id
        ORDER BY MAX(at.received_at) DESC
    """))
    asset_rows = assets_q.mappings().all()

    if not asset_rows:
        return []

    # For each asset, fetch the most recent linked session details and latest safety alerts
    results = []
    for row in asset_rows:
        asset_id = row["asset_id"]

        # Most recent session linked to this asset
        session_q = await db.execute(text("""
            SELECT ds.symptom_category, ds.status, ds.context, ds.vehicle_type
            FROM diagnostic_sessions ds
            JOIN asset_telemetry at ON at.linked_session_id = ds.id
            WHERE at.asset_id = :asset_id
            ORDER BY ds.created_at DESC
            LIMIT 1
        """), {"asset_id": asset_id})
        session_row = session_q.mappings().first()

        last_symptom = None
        last_top_cause = None
        vehicle_type = None
        if session_row:
            last_symptom = session_row["symptom_category"]
            vehicle_type = session_row["vehicle_type"]
            ctx = session_row["context"] or {}
            last_top_cause = ctx.get("top_cause")

        # Most recent telemetry safety alerts
        tel_q = await db.execute(text("""
            SELECT safety_alerts
            FROM asset_telemetry
            WHERE asset_id = :asset_id
            ORDER BY received_at DESC
            LIMIT 1
        """), {"asset_id": asset_id})
        tel_row = tel_q.mappings().first()
        last_safety_alerts = (tel_row["safety_alerts"] or []) if tel_row else []

        results.append({
            "asset_id": asset_id,
            "vehicle_type": vehicle_type,
            "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
            "session_count": row["session_count"],
            "open_sessions": row["open_sessions"],
            "last_symptom": last_symptom,
            "last_top_cause": last_top_cause,
            "last_safety_alerts": last_safety_alerts,
        })

    return results


# ── Asset history ─────────────────────────────────────────────────────────────

@router.get("/asset/{asset_id}/history")
async def get_asset_history(
    asset_id: str,
    limit: int = 20,
    _: CurrentUser = Depends(get_fleet_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Recent diagnostic sessions for a specific asset, most recent first.

    Returns:
      - asset_id
      - sessions: list of { session_id, symptom_category, vehicle_type, status,
                            top_cause, created_at, turn_count }
    """
    if limit < 1 or limit > 100:
        limit = 20

    rows_q = await db.execute(text("""
        SELECT DISTINCT ON (ds.id)
            ds.id             AS session_id,
            ds.symptom_category,
            ds.vehicle_type,
            ds.status,
            ds.context        AS ctx,
            ds.created_at,
            ds.turn_count
        FROM diagnostic_sessions ds
        JOIN asset_telemetry at ON at.linked_session_id = ds.id
        WHERE at.asset_id = :asset_id
        ORDER BY ds.id, ds.created_at DESC
        LIMIT :lim
    """), {"asset_id": asset_id, "lim": limit})
    rows = rows_q.mappings().all()

    sessions = []
    for r in rows:
        ctx = r["ctx"] or {}
        sessions.append({
            "session_id": r["session_id"],
            "symptom_category": r["symptom_category"],
            "vehicle_type": r["vehicle_type"],
            "status": r["status"],
            "top_cause": ctx.get("top_cause"),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "turn_count": r["turn_count"],
        })

    # Sort by created_at descending
    sessions.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return {"asset_id": asset_id, "sessions": sessions}


# ── Fleet summary ─────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_fleet_summary(
    _: CurrentUser = Depends(get_fleet_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Aggregate fleet health summary.

    Returns:
      - total_assets: count of distinct asset_ids with telemetry
      - active_issues: count of sessions in active/awaiting_followup linked to assets
      - top_faults: list of { cause, count } for the top 10 most common top_cause values
    """
    counts_q = await db.execute(text("""
        SELECT
            COUNT(DISTINCT at.asset_id)  AS total_assets,
            COUNT(DISTINCT CASE
                WHEN ds.status IN ('active', 'awaiting_followup') THEN ds.id
            END)                         AS active_issues
        FROM asset_telemetry at
        LEFT JOIN diagnostic_sessions ds ON ds.id = at.linked_session_id
    """))
    counts = counts_q.mappings().first()

    top_faults_q = await db.execute(text("""
        SELECT
            ds.context->>'top_cause' AS cause,
            COUNT(*)                 AS cnt
        FROM diagnostic_sessions ds
        JOIN asset_telemetry at ON at.linked_session_id = ds.id
        WHERE ds.context->>'top_cause' IS NOT NULL
          AND ds.status = 'awaiting_followup'
        GROUP BY ds.context->>'top_cause'
        ORDER BY cnt DESC
        LIMIT 10
    """))
    top_faults = [
        {"cause": r["cause"], "count": r["cnt"]}
        for r in top_faults_q.mappings().all()
    ]

    return {
        "total_assets": counts["total_assets"] if counts else 0,
        "active_issues": counts["active_issues"] if counts else 0,
        "top_faults": top_faults,
    }


# ── Asset priority ranking ─────────────────────────────────────────────────────

@router.get("/priorities")
async def get_fleet_priorities(
    days: int = 30,
    _: CurrentUser = Depends(get_fleet_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Return all assets ranked by operational risk, highest risk first.

    Risk is computed deterministically from:
      - Unresolved / open sessions     (weight 0.30)
      - Repeat failures (same symptom) (weight 0.20)
      - Safety events                  (weight 0.20)
      - Contradiction rate             (weight 0.15)
      - Anomaly flags                  (weight 0.05)
      - Telemetry abnormal readings    (weight 0.05)
      - Service overdue                (weight 0.05)

    No LLM involved. All scoring is traceable to inputs.

    Query params:
      days (int, 7–90, default 30): look-back window for session history.
    """
    from app.fleet.risk_model import (
        compute_asset_risk,
        fetch_all_asset_risk_data,
        rank_assets_by_risk,
    )

    if not (7 <= days <= 90):
        days = 30

    asset_ids, sessions_by_asset, telemetry_by_asset = await fetch_all_asset_risk_data(
        db, days=days
    )

    risks = [
        compute_asset_risk(
            asset_id=aid,
            sessions=sessions_by_asset.get(aid, []),
            telemetry=telemetry_by_asset.get(aid, []),
        )
        for aid in asset_ids
    ]

    ranked = rank_assets_by_risk(risks)

    return [
        {
            "asset_id":             r.asset_id,
            "risk_score":           r.risk_score,
            "risk_level":           r.risk_level,
            "contributing_factors": r.contributing_factors,
            "recommended_action":   r.recommended_action,
            "component_scores":     r.component_scores,
        }
        for r in ranked
    ]
