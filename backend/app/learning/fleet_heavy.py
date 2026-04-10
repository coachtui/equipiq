"""
Fleet Pattern Detection — Heavy Equipment (Phase 13B).

Three layers (mirrors patterns.py architecture):
1. DB fetch     — pull heavy equipment sessions with HeavyContext fields
2. Pure analysis — deterministic pattern detection, testable without DB
3. LLM summary  — optional semantic layer (non-fatal if unavailable)

Patterns detected:
  hours_failure_rate  — failure / unresolved rate by machine hours band
  environment_failure — environment-correlated failure clusters
  unresolved_cluster  — groups of unresolved sessions sharing a tree + hypothesis
  safety_hotspot      — trees / environments with elevated safety trigger rates
  contradiction_hotspot — trees with high contradiction rates (diagnostic ambiguity)
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger

_log = get_logger(__name__)


# ── Hours-band thresholds ─────────────────────────────────────────────────────

HOURS_BANDS: list[tuple[int, int, str]] = [
    (0,    999,   "low_hours"),        # new / lightly used
    (1000, 2999,  "moderate_hours"),
    (3000, 5999,  "high_hours"),
    (6000, 99999, "very_high_hours"),  # high-hours machines
]

# ── Pattern detection thresholds ─────────────────────────────────────────────

MIN_PATTERN_SESSIONS: int = 3          # ignore groups smaller than this
UNRESOLVED_HOTSPOT_MIN: float = 0.50   # unresolved rate above this = hotspot
SAFETY_HOTSPOT_MIN: float = 0.30       # safety trigger rate above this = hotspot
CONTRADICTION_HOTSPOT_MIN: float = 1.5 # avg contradictions above this = hotspot
ENVIRONMENT_CLUSTER_MIN: float = 0.40  # unresolved rate above this for env patterns


# ─────────────────────────────────────────────────────────────────────────────
# DB fetch functions
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_heavy_fleet_data(
    db: AsyncSession,
    limit: int = 500,
    session_mode: str | None = None,
) -> list[dict]:
    """
    Pull heavy equipment outcome rows with HeavyContext fields.

    Joins diagnostic_outcomes with diagnostic_sessions to extract:
    - outcome metrics (hypothesis, resolution, contradictions, safety)
    - HeavyContext JSONB fields (hours, environment, service state, work type)
    - session mode and timestamp

    Args:
        db:           Async database session.
        limit:        Max rows to return.
        session_mode: Optional filter — "consumer", "operator", or "mechanic".

    Returns:
        List of flat dicts, one per heavy equipment session with outcome data.
    """
    mode_filter = "AND ds.session_mode = :session_mode" if session_mode else ""
    rows = await db.execute(text(f"""
        SELECT
            do.session_id,
            do.selected_tree,
            do.top_hypothesis,
            do.was_resolved,
            do.rating,
            do.contradiction_count,
            do.safety_triggered,
            ds.session_mode,
            ds.symptom_category,
            (ds.heavy_context->>'hours_of_operation')::integer   AS hours_of_operation,
            (ds.heavy_context->>'last_service_hours')::integer   AS last_service_hours,
            ds.heavy_context->>'environment'                     AS environment,
            (ds.heavy_context->>'storage_duration')::integer     AS storage_duration,
            ds.heavy_context->>'recent_work_type'                AS recent_work_type,
            do.created_at
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        WHERE ds.vehicle_type = 'heavy_equipment'
          AND do.selected_tree IS NOT NULL
          {mode_filter}
        ORDER BY do.created_at DESC
        LIMIT :limit
    """), {"limit": limit, "session_mode": session_mode} if session_mode else {"limit": limit})

    return [
        {
            **dict(r),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows.mappings()
    ]


async def fetch_heavy_fleet_summary(db: AsyncSession) -> dict:
    """
    High-level summary counts for the admin fleet overview panel.

    Returns:
        {
            total_sessions, resolved_count, unresolved_count, safety_triggered_count,
            avg_contradictions, avg_rating,
            by_mode:        {mode: count},
            by_environment: {env: count},
            by_tree:        [{selected_tree, count, resolution_rate, safety_rate}],
        }
    """
    summary_row = await db.execute(text("""
        SELECT
            COUNT(*)                                                     AS total_sessions,
            SUM(CASE WHEN do.was_resolved = TRUE  THEN 1 ELSE 0 END)    AS resolved_count,
            SUM(CASE WHEN do.was_resolved = FALSE THEN 1 ELSE 0 END)    AS unresolved_count,
            SUM(CASE WHEN do.safety_triggered     THEN 1 ELSE 0 END)    AS safety_triggered_count,
            ROUND(AVG(do.contradiction_count)::numeric, 2)              AS avg_contradictions,
            ROUND(AVG(sf.rating)::numeric, 2)                           AS avg_rating
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        LEFT JOIN session_feedback sf ON sf.session_id = do.session_id
        WHERE ds.vehicle_type = 'heavy_equipment'
    """))
    s = dict(summary_row.mappings().one())

    mode_rows = await db.execute(text("""
        SELECT ds.session_mode, COUNT(*) AS cnt
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        WHERE ds.vehicle_type = 'heavy_equipment'
        GROUP BY ds.session_mode
        ORDER BY cnt DESC
    """))
    by_mode = {r["session_mode"]: int(r["cnt"]) for r in mode_rows.mappings()}

    env_rows = await db.execute(text("""
        SELECT
            COALESCE(ds.heavy_context->>'environment', 'unknown') AS environment,
            COUNT(*) AS cnt
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        WHERE ds.vehicle_type = 'heavy_equipment'
        GROUP BY environment
        ORDER BY cnt DESC
    """))
    by_environment = {r["environment"]: int(r["cnt"]) for r in env_rows.mappings()}

    tree_rows = await db.execute(text("""
        SELECT
            do.selected_tree,
            COUNT(*)                                                      AS cnt,
            ROUND(
                SUM(CASE WHEN do.was_resolved = TRUE THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0),
                4
            ) AS resolution_rate,
            ROUND(
                SUM(CASE WHEN do.safety_triggered THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0),
                4
            ) AS safety_rate
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        WHERE ds.vehicle_type = 'heavy_equipment'
          AND do.selected_tree IS NOT NULL
        GROUP BY do.selected_tree
        ORDER BY cnt DESC
    """))
    by_tree = [
        {
            "selected_tree": r["selected_tree"],
            "count": int(r["cnt"]),
            "resolution_rate": float(r["resolution_rate"]) if r["resolution_rate"] is not None else None,
            "safety_rate": float(r["safety_rate"]) if r["safety_rate"] is not None else None,
        }
        for r in tree_rows.mappings()
    ]

    return {
        "total_sessions":         int(s["total_sessions"] or 0),
        "resolved_count":         int(s["resolved_count"] or 0),
        "unresolved_count":       int(s["unresolved_count"] or 0),
        "safety_triggered_count": int(s["safety_triggered_count"] or 0),
        "avg_contradictions":     float(s["avg_contradictions"]) if s["avg_contradictions"] else 0.0,
        "avg_rating":             float(s["avg_rating"]) if s["avg_rating"] else None,
        "by_mode":                by_mode,
        "by_environment":         by_environment,
        "by_tree":                by_tree,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pure analysis — deterministic, testable without DB
# ─────────────────────────────────────────────────────────────────────────────

def _hours_band(hours: int | None) -> str:
    """Return the hours-band label for a given hourmeter reading."""
    if hours is None:
        return "unknown"
    for lo, hi, label in HOURS_BANDS:
        if lo <= hours <= hi:
            return label
    return "very_high_hours"


def _is_overdue(hours: int | None, last_service: int | None) -> bool:
    """Return True if machine is >250 hours past last service."""
    if hours is None or last_service is None or last_service == 0:
        return False
    return (hours - last_service) >= 250


def detect_hours_failure_patterns(rows: list[dict]) -> list[dict]:
    """
    Group sessions by (hours_band, selected_tree) and compute failure metrics.

    High failure rates at specific hours bands indicate wear-related or
    maintenance-interval-related failure modes.

    Args:
        rows: List of flat dicts from fetch_heavy_fleet_data().

    Returns:
        List of pattern dicts sorted by unresolved_rate descending.
        Each dict:
        {
            "pattern_type":        "hours_failure_rate",
            "tree_key":            str,
            "hours_band":          str,
            "session_count":       int,
            "unresolved_rate":     float,
            "avg_contradictions":  float,
            "safety_trigger_rate": float,
            "top_hypotheses":      list[str],
            "description":         str,
            "sample_session_ids":  list[str],
        }
    """
    # Group by (hours_band, tree_key)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        band = _hours_band(row.get("hours_of_operation"))
        tree = row.get("selected_tree") or "unknown"
        groups[(band, tree)].append(row)

    results: list[dict] = []
    for (band, tree), group in groups.items():
        if len(group) < MIN_PATTERN_SESSIONS or band == "unknown":
            continue

        n = len(group)
        unresolved = sum(1 for r in group if r.get("was_resolved") is False)
        safety_triggered = sum(1 for r in group if r.get("safety_triggered"))
        avg_contra = sum(r.get("contradiction_count") or 0 for r in group) / n
        unresolved_rate = round(unresolved / n, 4)
        safety_rate = round(safety_triggered / n, 4)

        # Top hypotheses (up to 3)
        hyp_counts: dict[str, int] = defaultdict(int)
        for r in group:
            hyp = r.get("top_hypothesis")
            if hyp:
                hyp_counts[hyp] += 1
        top_hyps = sorted(hyp_counts, key=lambda k: -hyp_counts[k])[:3]

        results.append({
            "pattern_type":        "hours_failure_rate",
            "tree_key":            tree,
            "hours_band":          band,
            "session_count":       n,
            "unresolved_rate":     unresolved_rate,
            "avg_contradictions":  round(avg_contra, 2),
            "safety_trigger_rate": safety_rate,
            "top_hypotheses":      top_hyps,
            "description": (
                f"{tree.replace('_heavy_equipment', '').replace('_', ' ').title()} "
                f"in {band.replace('_', ' ')} machines: "
                f"{n} sessions, {unresolved_rate:.0%} unresolved"
            ),
            "sample_session_ids":  [r["session_id"] for r in group[:3]],
        })

    return sorted(results, key=lambda r: r["unresolved_rate"], reverse=True)


def detect_environment_patterns(rows: list[dict]) -> list[dict]:
    """
    Group sessions by (environment, selected_tree) and find environment-linked failures.

    Environments with disproportionately high unresolved or safety rates
    indicate that the tree doesn't adequately weight environment-specific causes.

    Args:
        rows: List of flat dicts from fetch_heavy_fleet_data().

    Returns:
        List of pattern dicts for environment-linked failure clusters,
        sorted by unresolved_rate descending.
    """
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        env = row.get("environment") or "unknown"
        tree = row.get("selected_tree") or "unknown"
        groups[(env, tree)].append(row)

    results: list[dict] = []
    for (env, tree), group in groups.items():
        if len(group) < MIN_PATTERN_SESSIONS or env == "unknown":
            continue

        n = len(group)
        unresolved = sum(1 for r in group if r.get("was_resolved") is False)
        safety_triggered = sum(1 for r in group if r.get("safety_triggered"))
        avg_contra = sum(r.get("contradiction_count") or 0 for r in group) / n
        unresolved_rate = round(unresolved / n, 4)
        safety_rate = round(safety_triggered / n, 4)

        if unresolved_rate < ENVIRONMENT_CLUSTER_MIN and safety_rate < SAFETY_HOTSPOT_MIN:
            continue  # not notable

        hyp_counts: dict[str, int] = defaultdict(int)
        for r in group:
            hyp = r.get("top_hypothesis")
            if hyp:
                hyp_counts[hyp] += 1
        top_hyps = sorted(hyp_counts, key=lambda k: -hyp_counts[k])[:3]

        results.append({
            "pattern_type":        "environment_failure",
            "tree_key":            tree,
            "environment":         env,
            "session_count":       n,
            "unresolved_rate":     unresolved_rate,
            "avg_contradictions":  round(avg_contra, 2),
            "safety_trigger_rate": safety_rate,
            "top_hypotheses":      top_hyps,
            "description": (
                f"{tree.replace('_heavy_equipment', '').replace('_', ' ').title()} "
                f"in {env} environment: "
                f"{n} sessions, {unresolved_rate:.0%} unresolved, "
                f"{safety_rate:.0%} safety triggers"
            ),
            "sample_session_ids":  [r["session_id"] for r in group[:3]],
        })

    return sorted(results, key=lambda r: r["unresolved_rate"], reverse=True)


def detect_unresolved_clusters(rows: list[dict]) -> list[dict]:
    """
    Find clusters of unresolved sessions sharing the same (tree, hypothesis).

    These clusters represent diagnostic blind spots — the system routes to the
    right tree and picks a top hypothesis, but operators are not getting resolution.

    Args:
        rows: List of flat dicts from fetch_heavy_fleet_data().

    Returns:
        List of cluster dicts sorted by unresolved_count descending.
    """
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        tree = row.get("selected_tree") or "unknown"
        hyp = row.get("top_hypothesis") or "unknown"
        groups[(tree, hyp)].append(row)

    results: list[dict] = []
    for (tree, hyp), group in groups.items():
        unresolved = [r for r in group if r.get("was_resolved") is False]
        if len(unresolved) < MIN_PATTERN_SESSIONS:
            continue

        n = len(group)
        unresolved_rate = round(len(unresolved) / n, 4)
        avg_contra = sum(r.get("contradiction_count") or 0 for r in group) / n

        # Summarise hours bands of unresolved sessions
        band_counts: dict[str, int] = defaultdict(int)
        for r in unresolved:
            band_counts[_hours_band(r.get("hours_of_operation"))] += 1

        results.append({
            "pattern_type":       "unresolved_cluster",
            "tree_key":           tree,
            "hypothesis_key":     hyp,
            "session_count":      n,
            "unresolved_count":   len(unresolved),
            "unresolved_rate":    unresolved_rate,
            "avg_contradictions": round(avg_contra, 2),
            "hours_band_breakdown": dict(band_counts),
            "description": (
                f"{tree.replace('_heavy_equipment', '').replace('_', ' ').title()} → "
                f"{hyp.replace('_', ' ')}: "
                f"{len(unresolved)} unresolved out of {n} sessions "
                f"({unresolved_rate:.0%})"
            ),
            "sample_session_ids": [r["session_id"] for r in unresolved[:3]],
        })

    return sorted(results, key=lambda r: r["unresolved_count"], reverse=True)


def detect_safety_hotspots(rows: list[dict]) -> list[dict]:
    """
    Find trees and environments where safety alerts fire at elevated rates.

    A safety hotspot means operators are routinely entering dangerous conditions
    before the diagnostic runs — may indicate that safety pre-screening is needed
    at intake, or that the tree's instructions are leading operators into hazards.

    Args:
        rows: List of flat dicts from fetch_heavy_fleet_data().

    Returns:
        List of hotspot dicts sorted by safety_trigger_rate descending.
    """
    # Group by (tree, environment)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        tree = row.get("selected_tree") or "unknown"
        env = row.get("environment") or "unknown"
        groups[(tree, env)].append(row)

    results: list[dict] = []
    for (tree, env), group in groups.items():
        if len(group) < MIN_PATTERN_SESSIONS:
            continue

        n = len(group)
        safety_count = sum(1 for r in group if r.get("safety_triggered"))
        safety_rate = round(safety_count / n, 4)

        if safety_rate < SAFETY_HOTSPOT_MIN:
            continue

        avg_contra = sum(r.get("contradiction_count") or 0 for r in group) / n
        unresolved = sum(1 for r in group if r.get("was_resolved") is False)

        results.append({
            "pattern_type":        "safety_hotspot",
            "tree_key":            tree,
            "environment":         env,
            "session_count":       n,
            "safety_triggered_count": safety_count,
            "safety_trigger_rate": safety_rate,
            "unresolved_rate":     round(unresolved / n, 4),
            "avg_contradictions":  round(avg_contra, 2),
            "description": (
                f"Safety alerts triggered in {safety_rate:.0%} of "
                f"{tree.replace('_heavy_equipment', '').replace('_', ' ').title()} "
                f"sessions in {env} environment ({safety_count}/{n} sessions)"
            ),
            "sample_session_ids":  [r["session_id"] for r in group if r.get("safety_triggered")][:3],
        })

    return sorted(results, key=lambda r: r["safety_trigger_rate"], reverse=True)


def detect_contradiction_hotspots(rows: list[dict]) -> list[dict]:
    """
    Find trees with elevated average contradiction rates.

    High contradictions within a tree indicate that operator answers are
    internally inconsistent — possible causes: confusing question phrasing,
    questions asked in wrong order, or multi-failure modes the tree doesn't
    handle well.

    Args:
        rows: List of flat dicts from fetch_heavy_fleet_data().

    Returns:
        List of hotspot dicts sorted by avg_contradictions descending.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        tree = row.get("selected_tree") or "unknown"
        groups[tree].append(row)

    results: list[dict] = []
    for tree, group in groups.items():
        if len(group) < MIN_PATTERN_SESSIONS:
            continue

        n = len(group)
        avg_contra = sum(r.get("contradiction_count") or 0 for r in group) / n
        if avg_contra < CONTRADICTION_HOTSPOT_MIN:
            continue

        unresolved = sum(1 for r in group if r.get("was_resolved") is False)

        # Break down by mode — mechanic contradictions are different from operator
        mode_contra: dict[str, float] = {}
        by_mode: dict[str, list[dict]] = defaultdict(list)
        for r in group:
            by_mode[r.get("session_mode") or "unknown"].append(r)
        for mode, mode_rows in by_mode.items():
            mode_contra[mode] = round(
                sum(r.get("contradiction_count") or 0 for r in mode_rows) / len(mode_rows), 2
            )

        results.append({
            "pattern_type":         "contradiction_hotspot",
            "tree_key":             tree,
            "session_count":        n,
            "avg_contradictions":   round(avg_contra, 2),
            "unresolved_rate":      round(unresolved / n, 4),
            "contradictions_by_mode": mode_contra,
            "description": (
                f"{tree.replace('_heavy_equipment', '').replace('_', ' ').title()}: "
                f"avg {avg_contra:.1f} contradictions/session "
                f"({unresolved}/{n} unresolved)"
            ),
            "sample_session_ids":  [r["session_id"] for r in group[:3]],
        })

    return sorted(results, key=lambda r: r["avg_contradictions"], reverse=True)


def run_all_pattern_detection(rows: list[dict]) -> dict:
    """
    Run all five pattern detectors on the fleet data.

    Deterministic. Accepts plain Python structures — no DB required.

    Returns:
        {
            "hours_failure_patterns":    list[dict],
            "environment_patterns":      list[dict],
            "unresolved_clusters":       list[dict],
            "safety_hotspots":           list[dict],
            "contradiction_hotspots":    list[dict],
            "total_sessions_analysed":   int,
        }
    """
    return {
        "hours_failure_patterns":  detect_hours_failure_patterns(rows),
        "environment_patterns":    detect_environment_patterns(rows),
        "unresolved_clusters":     detect_unresolved_clusters(rows),
        "safety_hotspots":         detect_safety_hotspots(rows),
        "contradiction_hotspots":  detect_contradiction_hotspots(rows),
        "total_sessions_analysed": len(rows),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM-augmented summary (non-fatal)
# ─────────────────────────────────────────────────────────────────────────────

def generate_fleet_summary(patterns: dict) -> str:
    """
    Optionally call LLM to generate a human-readable fleet summary from pattern data.

    LLM may only summarise — it cannot alter scores, add hypotheses, or
    change any pattern data. Returns a plain string summary.

    Non-fatal: returns an auto-generated summary if LLM is unavailable.

    Args:
        patterns: Output from run_all_pattern_detection().

    Returns:
        A summary string for admin display.
    """
    unresolved = patterns.get("unresolved_clusters", [])
    safety = patterns.get("safety_hotspots", [])
    env = patterns.get("environment_patterns", [])
    hours = patterns.get("hours_failure_patterns", [])
    contradiction = patterns.get("contradiction_hotspots", [])
    total = patterns.get("total_sessions_analysed", 0)

    # Auto-generated summary (always available as fallback)
    parts: list[str] = [f"Fleet analysis based on {total} heavy equipment sessions."]

    if unresolved:
        top_cluster = unresolved[0]
        parts.append(
            f"Highest unresolved cluster: {top_cluster['tree_key'].replace('_heavy_equipment', '').replace('_', ' ')} "
            f"→ {top_cluster.get('hypothesis_key', '?').replace('_', ' ')} "
            f"({top_cluster['unresolved_count']} unresolved sessions)."
        )

    if safety:
        top_safety = safety[0]
        parts.append(
            f"Safety hotspot: {top_safety['tree_key'].replace('_heavy_equipment', '').replace('_', ' ')} "
            f"in {top_safety.get('environment', '?')} environment "
            f"({top_safety['safety_trigger_rate']:.0%} safety trigger rate)."
        )

    if not unresolved and not safety and not env and not hours:
        parts.append("No significant patterns detected in current data window.")

    auto_summary = " ".join(parts)

    # Try LLM augmentation
    try:
        from app.llm.claude import LLMServiceError, _call, _parse_json

        cluster_block = "\n".join(
            f"- {c['description']}"
            for c in (unresolved + safety + env)[:6]
        ) or "(no patterns detected)"

        prompt = f"""You are an analyst reviewing fleet diagnostic data for heavy construction equipment.

Data summary ({total} sessions):
{cluster_block}

Provide a 2–3 sentence summary for a fleet manager covering:
1. The most critical diagnostic pattern
2. Any safety concern worth immediate attention
3. One actionable recommendation

Be direct, factual, and field-practical. No filler language.
Respond with ONLY valid JSON: {{"summary": "..."}}"""

        raw = _call(
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            fn_name="generate_fleet_summary",
        )
        parsed = _parse_json(raw, "generate_fleet_summary")
        summary = parsed.get("summary", "").strip()
        if summary and len(summary) > 20:
            return summary[:800]

    except Exception as exc:
        _log.warning("generate_fleet_summary LLM call failed (non-fatal): %s", exc)

    return auto_summary
