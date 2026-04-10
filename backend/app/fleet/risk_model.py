"""
M5: thin re-export — pure scoring logic lives in fix_core.fleet.
DB fetch logic (fetch_all_asset_risk_data) remains here; SQLAlchemy
import is deferred inside the function to keep module importable without DB.
"""

from fix_core.fleet import (
    AssetRisk,
    SERVICE_INTERVAL_HOURS,
    WEIGHTS,
    NORM,
    RISK_LEVEL_THRESHOLDS,
    _clamp,
    _risk_level,
    compute_asset_risk,
    _build_factors,
    _recommended_action,
    rank_assets_by_risk,
)

__all__ = [
    "AssetRisk",
    "SERVICE_INTERVAL_HOURS",
    "WEIGHTS",
    "NORM",
    "RISK_LEVEL_THRESHOLDS",
    "_clamp",
    "_risk_level",
    "compute_asset_risk",
    "_build_factors",
    "_recommended_action",
    "rank_assets_by_risk",
    "fetch_all_asset_risk_data",
]


async def fetch_all_asset_risk_data(
    db,
    days: int = 30,
):
    """
    Fetch session and telemetry data for all known assets in two queries.

    Session window: sessions created within the last ``days`` days, PLUS
    all sessions that are still open (status active/awaiting_followup)
    regardless of age.

    Args:
        db:   Async SQLAlchemy session.
        days: Look-back window for historical sessions (7–90).

    Returns:
        Tuple of:
          asset_ids         — all distinct asset IDs (sorted)
          sessions_by_asset — {asset_id: [session_dict, ...]}
          telemetry_by_asset — {asset_id: [telemetry_dict, ...]}
    """
    from collections import defaultdict

    from sqlalchemy import text

    assets_q = await db.execute(
        text("SELECT DISTINCT asset_id FROM asset_telemetry ORDER BY asset_id")
    )
    asset_ids = [r["asset_id"] for r in assets_q.mappings()]

    if not asset_ids:
        return [], {}, {}

    sessions_q = await db.execute(text("""
        SELECT DISTINCT ON (at.asset_id, ds.id)
            at.asset_id,
            ds.id                  AS session_id,
            ds.status,
            ds.symptom_category,
            ds.vehicle_type,
            ds.safety_flags,
            ds.context,
            ds.heavy_context,
            ds.created_at,
            do.was_resolved,
            do.safety_triggered,
            do.contradiction_count,
            do.top_hypothesis
        FROM asset_telemetry at
        JOIN diagnostic_sessions ds ON ds.id = at.linked_session_id
        LEFT JOIN diagnostic_outcomes do ON do.session_id = ds.id
        WHERE ds.created_at >= NOW() - (:days_val * INTERVAL '1 day')
           OR ds.status IN ('active', 'awaiting_followup')
        ORDER BY at.asset_id, ds.id
    """), {"days_val": days})

    sessions_by_asset: dict = defaultdict(list)
    for r in sessions_q.mappings():
        sessions_by_asset[r["asset_id"]].append({
            "session_id":          str(r["session_id"]),
            "status":              r["status"],
            "symptom_category":    r["symptom_category"],
            "vehicle_type":        r["vehicle_type"],
            "safety_flags":        r["safety_flags"] or [],
            "context":             r["context"] or {},
            "heavy_context":       r["heavy_context"] or {},
            "created_at":          r["created_at"].isoformat() if r["created_at"] else None,
            "was_resolved":        r["was_resolved"],
            "safety_triggered":    bool(r["safety_triggered"]) if r["safety_triggered"] is not None else False,
            "contradiction_count": r["contradiction_count"] or 0,
            "top_hypothesis":      r["top_hypothesis"],
        })

    tel_q = await db.execute(text("""
        SELECT asset_id, safety_alerts, received_at
        FROM asset_telemetry
        WHERE received_at >= NOW() - (:days_val * INTERVAL '1 day')
        ORDER BY asset_id, received_at DESC
    """), {"days_val": days})

    telemetry_by_asset: dict = defaultdict(list)
    for r in tel_q.mappings():
        telemetry_by_asset[r["asset_id"]].append({
            "safety_alerts": r["safety_alerts"] or [],
            "received_at":   r["received_at"].isoformat() if r["received_at"] else None,
        })

    return asset_ids, dict(sessions_by_asset), dict(telemetry_by_asset)
