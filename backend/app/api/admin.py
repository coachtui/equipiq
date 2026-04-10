"""
Admin analytics API.

All endpoints require is_admin=True on the authenticated user.
No user-facing data — internal tooling only.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_admin_user
from app.engine.trees import TREES
from app.learning.adjustments import generate_adjustments
from app.learning.fleet_heavy import (
    fetch_heavy_fleet_data,
    fetch_heavy_fleet_summary,
    generate_fleet_summary,
    run_all_pattern_detection,
)
from app.learning.mode_analytics import (
    compute_mode_diagnostic_breakdown,
    compute_mode_metrics,
    compare_modes,
    fetch_mode_outcome_data,
    mode_summary_text,
)
from app.learning.insights import generate_insights
from app.learning.metrics import compute_hypothesis_metrics
from app.learning.patterns import (
    analyze_failure_patterns,
    detect_anomaly_trends,
    detect_tree_gaps,
    detect_weak_hypotheses,
    fetch_outcome_data,
    fetch_tree_performance,
    fetch_weekly_trends,
)
from app.learning.weights import get_approved_multipliers
from app.models.session import ApprovedWeightAdjustment

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Overview stats ────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Overall numbers: sessions, users, feedback, this-week activity."""
    rows = await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM diagnostic_sessions)                        AS total_sessions,
            (SELECT COUNT(*) FROM users)                                      AS total_users,
            (SELECT COUNT(*) FROM session_feedback)                           AS rated_sessions,
            (SELECT ROUND(AVG(rating)::numeric, 2) FROM session_feedback)     AS avg_rating,
            (SELECT COUNT(*) FROM diagnostic_sessions
             WHERE created_at >= NOW() - INTERVAL '7 days')                   AS sessions_this_week,
            (SELECT COUNT(*) FROM diagnostic_sessions
             WHERE status IN ('complete', 'awaiting_followup'))               AS completed_sessions
    """))
    row = rows.mappings().one()
    return {
        "total_sessions": int(row["total_sessions"] or 0),
        "total_users": int(row["total_users"] or 0),
        "rated_sessions": int(row["rated_sessions"] or 0),
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else None,
        "sessions_this_week": int(row["sessions_this_week"] or 0),
        "completed_sessions": int(row["completed_sessions"] or 0),
    }


# ── Sessions over time ────────────────────────────────────────────────────────

@router.get("/sessions_over_time")
async def sessions_over_time(
    days: int = 30,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Daily session counts for the past N days."""
    rows = await db.execute(
        text("""
            SELECT
                DATE(created_at AT TIME ZONE 'UTC') AS day,
                COUNT(*)                             AS count
            FROM diagnostic_sessions
            WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY day
            ORDER BY day
        """),
        {"days": days},
    )

    data = [{"day": str(r["day"]), "count": int(r["count"])} for r in rows.mappings()]
    return {"days": days, "data": data}


# ── Top diagnoses ─────────────────────────────────────────────────────────────

@router.get("/top_diagnoses")
async def top_diagnoses(
    limit: int = 20,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Top symptom_category × vehicle_type combos by session count."""
    rows = await db.execute(text("""
        SELECT
            COALESCE(symptom_category, 'unknown') AS symptom_category,
            COALESCE(vehicle_type, 'car')         AS vehicle_type,
            COUNT(*)                              AS session_count,
            ROUND(AVG(f.rating)::numeric, 2)      AS avg_rating,
            COUNT(f.id)                           AS rated_count
        FROM diagnostic_sessions ds
        LEFT JOIN session_feedback f ON f.session_id = ds.id
        WHERE ds.symptom_category IS NOT NULL
        GROUP BY symptom_category, vehicle_type
        ORDER BY session_count DESC
        LIMIT :limit
    """).bindparams(limit=limit))

    data = [
        {
            "symptom_category": r["symptom_category"],
            "vehicle_type": r["vehicle_type"],
            "session_count": int(r["session_count"]),
            "avg_rating": float(r["avg_rating"]) if r["avg_rating"] else None,
            "rated_count": int(r["rated_count"]),
        }
        for r in rows.mappings()
    ]
    return {"data": data}


# ── Feedback review ───────────────────────────────────────────────────────────

@router.get("/feedback")
async def get_feedback(
    limit: int = 30,
    comments_only: bool = False,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Recent feedback entries. comments_only=true filters to entries with text."""
    comment_filter = "AND f.comment IS NOT NULL AND TRIM(f.comment) != ''" if comments_only else ""
    rows = await db.execute(text(f"""
        SELECT
            f.session_id,
            f.rating,
            f.comment,
            f.created_at,
            ds.symptom_category,
            ds.vehicle_type,
            ds.vehicle_year,
            ds.vehicle_make,
            ds.vehicle_model
        FROM session_feedback f
        JOIN diagnostic_sessions ds ON ds.id = f.session_id
        WHERE 1=1 {comment_filter}
        ORDER BY f.created_at DESC
        LIMIT :limit
    """).bindparams(limit=limit))

    data = [
        {
            "session_id": r["session_id"],
            "rating": int(r["rating"]),
            "comment": r["comment"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "symptom_category": r["symptom_category"],
            "vehicle_type": r["vehicle_type"],
            "vehicle_year": r["vehicle_year"],
            "vehicle_make": r["vehicle_make"],
            "vehicle_model": r["vehicle_model"],
        }
        for r in rows.mappings()
    ]

    # Rating distribution
    dist_rows = await db.execute(text("""
        SELECT rating, COUNT(*) AS count
        FROM session_feedback
        GROUP BY rating
        ORDER BY rating
    """))
    distribution = {int(r["rating"]): int(r["count"]) for r in dist_rows.mappings()}

    return {"data": data, "distribution": distribution}


# ── Tree coverage ─────────────────────────────────────────────────────────────

@router.get("/coverage")
async def get_coverage(
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Matrix of symptom × vehicle_type showing:
    - has_tree: whether a dedicated tree exists
    - session_count: how many sessions used that combo
    """
    SYMPTOMS = [
        "no_crank", "crank_no_start", "loss_of_power", "rough_idle",
        "strange_noise", "visible_leak", "overheating", "check_engine_light",
        "brakes", "transmission", "suspension", "hvac",
    ]
    VEHICLE_TYPES = ["car", "truck", "motorcycle", "boat", "generator", "atv", "pwc", "rv"]

    # Session counts per combo
    rows = await db.execute(text("""
        SELECT
            COALESCE(symptom_category, 'unknown') AS symptom_category,
            COALESCE(vehicle_type, 'car')         AS vehicle_type,
            COUNT(*) AS count
        FROM diagnostic_sessions
        WHERE symptom_category IS NOT NULL
        GROUP BY symptom_category, vehicle_type
    """))
    counts: dict[tuple, int] = {
        (r["symptom_category"], r["vehicle_type"]): int(r["count"])
        for r in rows.mappings()
    }

    matrix = []
    for symptom in SYMPTOMS:
        row = {"symptom": symptom, "vehicles": {}}
        for vt in VEHICLE_TYPES:
            tree_key = f"{symptom}_{vt}" if vt != "car" else symptom
            has_tree = tree_key in TREES
            row["vehicles"][vt] = {
                "has_tree": has_tree,
                "session_count": counts.get((symptom, vt), 0),
            }
        matrix.append(row)

    return {"symptoms": SYMPTOMS, "vehicle_types": VEHICLE_TYPES, "matrix": matrix}


# ── Phase 10: Learning system ─────────────────────────────────────────────────

class ApproveAdjustmentRequest(BaseModel):
    multiplier: float = Field(..., ge=0.5, le=2.0)


@router.get("/learning/metrics")
async def get_learning_metrics(
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Raw hypothesis performance metrics across all recorded outcomes."""
    metrics = await compute_hypothesis_metrics(db)
    return {
        "total_hypotheses": len(metrics),
        "metrics": {hyp_id: asdict(m) for hyp_id, m in metrics.items()},
    }


@router.get("/learning/adjustments")
async def list_learning_adjustments(
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Compute suggested weight adjustments from current outcome data.

    Returns each adjustment alongside:
    - the underlying metrics
    - the current approved multiplier (if any)
    - sample session IDs for manual inspection

    Adjustments are suggestions only — no effect until approved.
    """
    metrics = await compute_hypothesis_metrics(db)
    approved = await get_approved_multipliers(db)
    adjustments = generate_adjustments(metrics, current_multipliers=approved)

    # Pull sample session IDs for each hypothesis (up to 3 per hypothesis)
    samples_query = await db.execute(text("""
        SELECT top_hypothesis, session_id
        FROM (
            SELECT top_hypothesis, session_id,
                   ROW_NUMBER() OVER (PARTITION BY top_hypothesis ORDER BY created_at DESC) AS rn
            FROM diagnostic_outcomes
            WHERE top_hypothesis IS NOT NULL
        ) sub
        WHERE rn <= 3
    """))
    samples: dict[str, list[str]] = {}
    for r in samples_query.mappings():
        hyp = r["top_hypothesis"]
        samples.setdefault(hyp, []).append(r["session_id"])

    result = []
    for adj in adjustments:
        m = metrics.get(adj.hypothesis_id)
        result.append({
            "hypothesis_id": adj.hypothesis_id,
            "base_weight": adj.base_weight,
            "suggested_multiplier": adj.suggested_multiplier,
            "confidence": adj.confidence,
            "reason": adj.reason,
            "metrics": asdict(m) if m else None,
            "current_approved_multiplier": approved.get(adj.hypothesis_id, 1.0),
            "is_approved": adj.hypothesis_id in approved,
            "sample_session_ids": samples.get(adj.hypothesis_id, []),
        })

    return {"count": len(result), "adjustments": result}


@router.post("/learning/adjustments/{hypothesis_id}/approve")
async def approve_adjustment(
    hypothesis_id: str,
    req: ApproveAdjustmentRequest,
    current_admin: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Approve a weight adjustment for a hypothesis.

    The multiplier will be applied to that hypothesis's prior at the start of
    new sessions. Existing sessions are unaffected.

    Approved multiplier is clamped to [0.5, 2.0] by the DB constraint.
    """
    await db.execute(
        pg_insert(ApprovedWeightAdjustment).values(
            hypothesis_id=hypothesis_id,
            multiplier=req.multiplier,
            approved_by=current_admin.email,
        ).on_conflict_do_update(
            index_elements=["hypothesis_id"],
            set_={
                "multiplier": req.multiplier,
                "approved_by": current_admin.email,
                "approved_at": text("NOW()"),
            },
        )
    )
    await db.commit()
    return {
        "hypothesis_id": hypothesis_id,
        "multiplier": req.multiplier,
        "approved_by": current_admin.email,
        "status": "approved",
    }


@router.get("/learning/insights")
async def get_learning_insights(
    use_llm: bool = True,
    data_limit: int = 200,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Phase 10.5 — Intelligent learning analysis.

    Runs four analysis passes on outcome data and (optionally) calls the LLM
    to synthesise a prioritised list of insights for admin review.

    All outputs are read-only advisory information.  Nothing in this endpoint
    changes weights, trees, or routing.  Suggested actions must still go
    through the existing approve endpoint.

    Query params:
      use_llm=true   (default) — include LLM pattern summaries and insights
      use_llm=false            — return deterministic analysis only (faster)
      data_limit=200           — max outcome rows to analyse
    """
    from datetime import datetime, timezone

    # ── 1. Load base metrics ──────────────────────────────────────────────────
    metrics = await compute_hypothesis_metrics(db)
    metrics_summary = {
        "total_hypotheses": len(metrics),
        "total_cases": sum(m.total_cases for m in metrics.values()),
    }

    # ── 2. Fetch raw data for pattern / gap / trend analysis ─────────────────
    outcome_data     = await fetch_outcome_data(db, limit=data_limit)
    tree_performance = await fetch_tree_performance(db)
    weekly_data      = await fetch_weekly_trends(db)

    # ── 3. Deterministic analysis (always runs) ───────────────────────────────
    weak_hypotheses = detect_weak_hypotheses(metrics)
    tree_gaps       = detect_tree_gaps(tree_performance)
    anomaly_trends  = detect_anomaly_trends(weekly_data)

    # ── 4. LLM-augmented analysis (use_llm=true, non-fatal) ──────────────────
    if use_llm:
        failure_patterns = analyze_failure_patterns(outcome_data)
        insights         = generate_insights(
            weak_hypotheses=weak_hypotheses,
            failure_patterns=failure_patterns,
            tree_gaps=tree_gaps,
            anomaly_trends=anomaly_trends,
            metrics_summary=metrics_summary,
        )
    else:
        failure_patterns = []
        insights         = []

    return {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "data_window":     {"outcome_rows": len(outcome_data), "limit": data_limit},
        "use_llm":         use_llm,
        "metrics_summary": metrics_summary,
        "weak_hypotheses": weak_hypotheses,
        "failure_patterns": failure_patterns,
        "tree_gaps":        tree_gaps,
        "anomaly_trends":   anomaly_trends,
        "insights":         insights,
    }


@router.post("/learning/adjustments/{hypothesis_id}/reject")
async def reject_adjustment(
    hypothesis_id: str,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Remove an approved adjustment, reverting to multiplier = 1.0 (base prior).
    Safe to call even if the hypothesis has no approved adjustment.
    """
    await db.execute(
        delete(ApprovedWeightAdjustment).where(
            ApprovedWeightAdjustment.hypothesis_id == hypothesis_id
        )
    )
    await db.commit()
    return {"hypothesis_id": hypothesis_id, "status": "rejected", "effective_multiplier": 1.0}


# ── Phase 13B — Heavy Equipment Fleet Analytics ───────────────────────────────

@router.get("/fleet/heavy_equipment")
async def get_heavy_fleet_overview(
    session_mode: str | None = None,
    limit: int = 100,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Heavy equipment fleet session view with HeavyContext fields.

    Returns summary stats + filtered session list for the admin fleet panel.

    Query params:
      session_mode: filter by "consumer", "operator", or "mechanic" (optional)
      limit:        max rows in session list (default 100)
    """
    from datetime import datetime, timezone

    summary = await fetch_heavy_fleet_summary(db)
    sessions = await fetch_heavy_fleet_data(db, limit=limit, session_mode=session_mode)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter": {"session_mode": session_mode},
        "summary": summary,
        "sessions": sessions,
    }


@router.get("/fleet/heavy_equipment/patterns")
async def get_heavy_fleet_patterns(
    use_llm: bool = True,
    limit: int = 500,
    session_mode: str | None = None,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Phase 13B — Heavy equipment fleet pattern detection.

    Runs five deterministic pattern detectors on heavy equipment outcome data:
      1. hours_failure_patterns  — failure rates by machine hours band
      2. environment_patterns    — environment-linked failure clusters
      3. unresolved_clusters     — hypothesis + tree clusters with high unresolved rates
      4. safety_hotspots         — trees/environments with elevated safety trigger rates
      5. contradiction_hotspots  — trees with high internal contradiction rates

    All pattern detection is deterministic.  LLM is used only to generate a
    human-readable summary (use_llm=false skips this).

    Query params:
      use_llm:      include LLM fleet summary (default true)
      limit:        max outcome rows to analyse (default 500)
      session_mode: filter by "consumer", "operator", or "mechanic" (optional)
    """
    from datetime import datetime, timezone

    rows = await fetch_heavy_fleet_data(db, limit=limit, session_mode=session_mode)
    patterns = run_all_pattern_detection(rows)

    fleet_summary = generate_fleet_summary(patterns) if use_llm else _auto_fleet_summary(patterns)

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "data_window":   {"session_rows": len(rows), "limit": limit},
        "filter":        {"session_mode": session_mode},
        "use_llm":       use_llm,
        "fleet_summary": fleet_summary,
        **patterns,
    }


# ── Phase 13C — Telematics admin visibility ───────────────────────────────────

@router.get("/telematics/recent")
async def get_recent_telemetry(
    limit: int = 50,
    asset_id: str | None = None,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Admin view: recent telemetry readings across all assets (or filtered by asset_id).

    Returns raw values, signal names, safety alert counts, and session linkage.
    Use this for debugging: inspect what sensor data has been ingested and how
    it was normalized before being applied to diagnostic sessions.
    """
    from datetime import datetime, timezone

    asset_filter = "AND asset_id = :asset_id" if asset_id else ""
    rows = await db.execute(text(f"""
        SELECT
            id, asset_id, received_at, telemetry_ts,
            engine_temp_c, voltage_v, pressure_psi, fuel_level_pct, fault_codes,
            normalized_signals, safety_alerts, linked_session_id
        FROM asset_telemetry
        WHERE 1=1 {asset_filter}
        ORDER BY received_at DESC
        LIMIT :limit
    """), {"limit": limit, "asset_id": asset_id} if asset_id else {"limit": limit})

    readings = [
        {
            "telemetry_id":     r["id"],
            "asset_id":         r["asset_id"],
            "received_at":      r["received_at"].isoformat() if r["received_at"] else None,
            "telemetry_ts":     r["telemetry_ts"].isoformat() if r["telemetry_ts"] else None,
            "raw": {
                "engine_temp_c":  float(r["engine_temp_c"]) if r["engine_temp_c"] is not None else None,
                "voltage_v":      float(r["voltage_v"]) if r["voltage_v"] is not None else None,
                "pressure_psi":   float(r["pressure_psi"]) if r["pressure_psi"] is not None else None,
                "fuel_level_pct": float(r["fuel_level_pct"]) if r["fuel_level_pct"] is not None else None,
                "fault_codes":    r["fault_codes"] or [],
            },
            "signal_names":    [s["normalized_key"] for s in (r["normalized_signals"] or [])],
            "safety_count":    len([a for a in (r["safety_alerts"] or []) if a.get("level") == "critical"]),
            "linked_session_id": r["linked_session_id"],
        }
        for r in rows.mappings()
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter":       {"asset_id": asset_id},
        "count":        len(readings),
        "readings":     readings,
    }


# ── Phase 13D — Session Mode Analytics ───────────────────────────────────────

@router.get("/analytics/by_mode")
async def get_analytics_by_mode(
    vehicle_type: str | None = None,
    limit: int = 1000,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Phase 13D — Per-mode aggregate metrics and diagnostic breakdown.

    Returns metrics, diagnostic breakdown, and one-sentence summaries for each
    session mode (consumer, operator, mechanic).

    Query params:
      vehicle_type: optional filter (e.g. "heavy_equipment")
      limit:        max outcome rows to analyse (default 1000)
    """
    from datetime import datetime, timezone

    rows = await fetch_mode_outcome_data(db, vehicle_type=vehicle_type, limit=limit)
    metrics = compute_mode_metrics(rows)
    breakdown = compute_mode_diagnostic_breakdown(rows)
    summaries = mode_summary_text(metrics, breakdown)

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "filter":        {"vehicle_type": vehicle_type},
        "data_window":   {"outcome_rows": len(rows), "limit": limit},
        "summaries":     summaries,
        "metrics":       {mode: asdict(m) for mode, m in metrics.items()},
        "breakdown":     {mode: asdict(b) for mode, b in breakdown.items()},
    }


@router.get("/analytics/mode_comparison")
async def get_mode_comparison(
    vehicle_type: str | None = None,
    limit: int = 1000,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Phase 13D — Side-by-side mode comparison across all tracked metrics.

    For each metric: value per mode, best mode, worst mode, and spread.
    Useful for admin spot-checks — e.g., "which mode has the highest unresolved rate?"

    Query params:
      vehicle_type: optional filter (e.g. "heavy_equipment")
      limit:        max outcome rows to analyse (default 1000)
    """
    from datetime import datetime, timezone

    rows = await fetch_mode_outcome_data(db, vehicle_type=vehicle_type, limit=limit)
    metrics = compute_mode_metrics(rows)
    comparison = compare_modes(metrics)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter":       {"vehicle_type": vehicle_type},
        "data_window":  {"outcome_rows": len(rows), "limit": limit},
        "modes_present": list(metrics.keys()),
        "comparison":   comparison,
    }


def _auto_fleet_summary(patterns: dict) -> str:
    """Deterministic fleet summary when use_llm=false."""
    total = patterns.get("total_sessions_analysed", 0)
    unresolved = patterns.get("unresolved_clusters", [])
    safety = patterns.get("safety_hotspots", [])
    parts = [f"Fleet analysis: {total} heavy equipment sessions."]
    if unresolved:
        parts.append(
            f"{len(unresolved)} unresolved cluster(s) detected. "
            f"Largest: {unresolved[0]['description']}"
        )
    if safety:
        parts.append(
            f"{len(safety)} safety hotspot(s) detected. "
            f"Highest rate: {safety[0]['description']}"
        )
    if not unresolved and not safety:
        parts.append("No significant patterns in current data window.")
    return " ".join(parts)
