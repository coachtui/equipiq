"""
Learning system — failure pattern analysis (Phase 10.5).

Three layers:
1. DB fetch functions   — pull structured data from diagnostic_outcomes
2. Pure analysis        — deterministic, testable without a DB
3. LLM clustering       — optional semantic layer on top of statistical clusters

All public analysis functions accept plain Python structures so they can be
unit-tested without a database.  LLM augmentation is non-fatal: if the call
fails the statistical output is returned as-is.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.learning.metrics import HypothesisMetrics

_log = get_logger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

WEAK_RESOLUTION_MIN   = 0.30   # resolution_rate below this → underperforming
WEAK_REVERSAL_MAX     = 0.30   # reversal_rate   above this → frequently wrong
WEAK_RATING_MAX       = 2.5    # avg_rating      below this → poor satisfaction
MIN_SAMPLES_FOR_WEAK  = 3      # ignore hypotheses with fewer outcomes

GAP_UNRESOLVED_MIN    = 0.40   # unresolved_rate above this → tree gap
GAP_CONTRADICTION_MIN = 1.5    # avg_contradictions above this → tree confusion
GAP_MIN_SESSIONS      = 3      # need at least this many sessions to judge a tree

SPIKE_FACTOR          = 2.0    # recent_count / historical_avg above this → trend
TREND_MIN_RECENT      = 5      # minimum recent sessions to flag a trend
TREND_LOOKBACK_WEEKS  = 8


# ── DB fetch functions ────────────────────────────────────────────────────────

async def fetch_outcome_data(
    db: AsyncSession,
    limit: int = 200,
) -> list[dict]:
    """
    Pull recent outcome rows joined with session metadata.
    Used by analyze_failure_patterns() and detect_anomaly_trends().
    """
    rows = await db.execute(text("""
        SELECT
            do.session_id,
            do.selected_tree,
            do.top_hypothesis,
            do.was_resolved,
            do.rating,
            do.contradiction_count,
            do.safety_triggered,
            ds.symptom_category,
            ds.vehicle_type,
            ds.vehicle_year,
            SUBSTRING(ds.initial_description, 1, 200) AS description
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        ORDER BY do.created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    return [dict(r) for r in rows.mappings()]


async def fetch_tree_performance(db: AsyncSession) -> list[dict]:
    """
    Per-tree aggregate: total sessions, resolution rate, contradiction rate.
    Used by detect_tree_gaps().
    """
    rows = await db.execute(text("""
        SELECT
            do.selected_tree,
            COUNT(*)                                                           AS total_sessions,
            SUM(CASE WHEN do.was_resolved = TRUE  THEN 1 ELSE 0 END)          AS resolved_count,
            SUM(CASE WHEN do.was_resolved = FALSE THEN 1 ELSE 0 END)          AS unresolved_count,
            ROUND(AVG(do.contradiction_count)::numeric, 2)                    AS avg_contradictions,
            ROUND(AVG(sf.rating)::numeric, 2)                                 AS avg_rating
        FROM diagnostic_outcomes do
        LEFT JOIN session_feedback sf ON sf.session_id = do.session_id
        WHERE do.selected_tree IS NOT NULL
        GROUP BY do.selected_tree
        ORDER BY total_sessions DESC
    """))
    return [dict(r) for r in rows.mappings()]


async def fetch_weekly_trends(
    db: AsyncSession,
    weeks: int = TREND_LOOKBACK_WEEKS,
) -> list[dict]:
    """
    Weekly session counts per symptom_category for trend detection.
    """
    rows = await db.execute(text("""
        SELECT
            DATE_TRUNC('week', do.created_at)              AS week,
            ds.symptom_category,
            COUNT(*)                                        AS session_count,
            ROUND(AVG(do.contradiction_count)::numeric, 2) AS avg_contradictions,
            SUM(CASE WHEN do.was_resolved = TRUE THEN 1 ELSE 0 END) AS resolved_count
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        WHERE do.created_at >= NOW() - (:weeks * INTERVAL '1 week')
          AND ds.symptom_category IS NOT NULL
        GROUP BY week, ds.symptom_category
        ORDER BY week DESC, session_count DESC
    """), {"weeks": weeks})
    return [
        {
            **dict(r),
            "week": r["week"].isoformat() if r["week"] else None,
        }
        for r in rows.mappings()
    ]


# ── Pure analysis — detect_weak_hypotheses ───────────────────────────────────

def detect_weak_hypotheses(
    metrics: dict[str, HypothesisMetrics],
) -> list[dict]:
    """
    Find hypotheses that are underperforming based on three independent signals:
    low resolution, high reversal, or poor user satisfaction.

    Returns list of dicts sorted by severity (worst first):
    {
        "hypothesis_id": str,
        "weaknesses":    list[str],   # which signals fired
        "severity":      float,       # 0.0–1.0 composite
        "total_cases":   int,
        "resolution_rate": float,
        "reversal_rate":   float,
        "avg_rating":      float,
    }
    """
    results: list[dict] = []

    for hyp_id, m in metrics.items():
        if m.total_cases < MIN_SAMPLES_FOR_WEAK:
            continue

        weaknesses: list[str] = []
        severity_parts: list[float] = []

        if m.resolution_rate < WEAK_RESOLUTION_MIN and m.total_cases >= 5:
            weaknesses.append(f"low resolution rate ({m.resolution_rate:.0%})")
            severity_parts.append(1.0 - m.resolution_rate)

        if m.reversal_rate >= WEAK_REVERSAL_MAX:
            weaknesses.append(f"high reversal rate ({m.reversal_rate:.0%})")
            severity_parts.append(m.reversal_rate)

        if m.avg_rating > 0 and m.avg_rating <= WEAK_RATING_MAX:
            weaknesses.append(f"low avg rating ({m.avg_rating:.1f}/5)")
            severity_parts.append((5.0 - m.avg_rating) / 5.0)

        if not weaknesses:
            continue

        severity = round(min(1.0, sum(severity_parts) / len(severity_parts)), 3)
        results.append({
            "hypothesis_id":   hyp_id,
            "weaknesses":      weaknesses,
            "severity":        severity,
            "total_cases":     m.total_cases,
            "resolution_rate": m.resolution_rate,
            "reversal_rate":   m.reversal_rate,
            "avg_rating":      m.avg_rating,
        })

    return sorted(results, key=lambda r: r["severity"], reverse=True)


# ── Pure analysis — detect_tree_gaps ─────────────────────────────────────────

def detect_tree_gaps(
    tree_performance: list[dict],
) -> list[dict]:
    """
    Identify trees with systematic coverage or quality problems.

    Returns list of dicts sorted by severity:
    {
        "tree_id":       str,
        "gap_types":     list[str],
        "severity":      float,
        "total_sessions": int,
        "unresolved_rate": float,
        "avg_contradictions": float,
        "recommendation": str,
    }
    """
    results: list[dict] = []

    for row in tree_performance:
        tree_id       = row.get("selected_tree") or row.get("tree_id", "")
        total         = int(row.get("total_sessions", 0) or 0)
        unresolved    = int(row.get("unresolved_count", 0) or 0)
        avg_contra    = float(row.get("avg_contradictions", 0) or 0.0)

        if total < GAP_MIN_SESSIONS or not tree_id:
            continue

        unresolved_rate = round(unresolved / total, 4) if total > 0 else 0.0
        gap_types: list[str] = []
        severity_parts: list[float] = []
        recommendations: list[str] = []

        if unresolved_rate >= GAP_UNRESOLVED_MIN:
            gap_types.append(f"high unresolved rate ({unresolved_rate:.0%})")
            severity_parts.append(unresolved_rate)
            recommendations.append("review tree exit conditions and hypothesis coverage")

        if avg_contra >= GAP_CONTRADICTION_MIN:
            gap_types.append(f"high avg contradictions ({avg_contra:.1f})")
            severity_parts.append(min(1.0, avg_contra / 4.0))
            recommendations.append("review question phrasing and option overlap")

        if not gap_types:
            continue

        severity = round(min(1.0, sum(severity_parts) / len(severity_parts)), 3)
        results.append({
            "tree_id":            tree_id,
            "gap_types":          gap_types,
            "severity":           severity,
            "total_sessions":     total,
            "unresolved_rate":    unresolved_rate,
            "avg_contradictions": avg_contra,
            "recommendation":     "; ".join(recommendations),
        })

    return sorted(results, key=lambda r: r["severity"], reverse=True)


# ── Pure analysis — detect_anomaly_trends ────────────────────────────────────

def detect_anomaly_trends(
    weekly_data: list[dict],
) -> list[dict]:
    """
    Detect unusual spikes in session volume or contradiction rates for each
    symptom_category by comparing the most recent week to the historical average.

    weekly_data: list of {week, symptom_category, session_count, avg_contradictions, resolved_count}

    Returns list of dicts sorted by spike_factor descending:
    {
        "symptom_category": str,
        "trend_type":       str,   # "volume_spike" | "contradiction_spike"
        "recent_count":     int,
        "historical_avg":   float,
        "spike_factor":     float,
        "week":             str,
    }
    """
    if not weekly_data:
        return []

    # Group by symptom_category, separate most-recent week from historical
    by_symptom: dict[str, list[dict]] = defaultdict(list)
    for row in weekly_data:
        cat = row.get("symptom_category")
        if cat:
            by_symptom[cat].append(row)

    # Sort each group so index 0 = most recent
    for cat in by_symptom:
        by_symptom[cat].sort(key=lambda r: r.get("week") or "", reverse=True)

    results: list[dict] = []
    for cat, rows in by_symptom.items():
        if len(rows) < 2:
            continue  # need at least recent + 1 historical week

        recent = rows[0]
        historical = rows[1:]

        recent_vol    = int(recent.get("session_count", 0) or 0)
        hist_vols     = [int(r.get("session_count", 0) or 0) for r in historical]
        hist_avg_vol  = sum(hist_vols) / len(hist_vols) if hist_vols else 0

        recent_contra = float(recent.get("avg_contradictions", 0) or 0.0)
        hist_contras  = [float(r.get("avg_contradictions", 0) or 0.0) for r in historical]
        hist_avg_contra = sum(hist_contras) / len(hist_contras) if hist_contras else 0

        # Volume spike
        if (
            recent_vol >= TREND_MIN_RECENT
            and hist_avg_vol > 0
            and recent_vol / hist_avg_vol >= SPIKE_FACTOR
        ):
            results.append({
                "symptom_category": cat,
                "trend_type":       "volume_spike",
                "recent_count":     recent_vol,
                "historical_avg":   round(hist_avg_vol, 2),
                "spike_factor":     round(recent_vol / hist_avg_vol, 2),
                "week":             recent.get("week", ""),
            })

        # Contradiction spike
        if (
            recent_vol >= TREND_MIN_RECENT
            and hist_avg_contra > 0
            and recent_contra / hist_avg_contra >= SPIKE_FACTOR
        ):
            results.append({
                "symptom_category": cat,
                "trend_type":       "contradiction_spike",
                "recent_count":     recent_vol,
                "historical_avg":   round(hist_avg_contra, 2),
                "spike_factor":     round(recent_contra / hist_avg_contra, 2),
                "week":             recent.get("week", ""),
            })

    return sorted(results, key=lambda r: r["spike_factor"], reverse=True)


# ── LLM-augmented — analyze_failure_patterns ─────────────────────────────────

def analyze_failure_patterns(
    outcome_data: list[dict],
) -> list[dict]:
    """
    Find recurring failure patterns across sessions.

    Statistical clustering is always performed.  LLM is called to add semantic
    summaries to the largest clusters; it is non-fatal if unavailable.

    outcome_data: list from fetch_outcome_data()

    Returns list of dicts:
    {
        "pattern":          str,    # cluster key
        "symptom_cluster":  list[str],
        "hypothesis_cluster": list[str],
        "env_context":      dict,   # vehicle_type distribution
        "frequency":        int,
        "resolution_rate":  float,
        "summary":          str,    # LLM or auto-generated
    }
    """
    if not outcome_data:
        return []

    # ── Statistical clustering ────────────────────────────────────────────────
    # Group by (symptom_category, top_hypothesis)
    cluster_key = lambda r: (
        r.get("symptom_category") or "unknown",
        r.get("top_hypothesis") or "unknown",
    )

    clusters: dict[tuple, list[dict]] = defaultdict(list)
    for row in outcome_data:
        clusters[cluster_key(row)].append(row)

    # Build pattern objects for clusters with >= 3 sessions
    patterns: list[dict] = []
    for (symptom, hypothesis), rows in clusters.items():
        if len(rows) < 3:
            continue

        resolved = sum(1 for r in rows if r.get("was_resolved") is True)
        resolution_rate = round(resolved / len(rows), 4)

        vt_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            vt = r.get("vehicle_type") or "unknown"
            vt_counts[vt] += 1

        patterns.append({
            "pattern":            f"{symptom}:{hypothesis}",
            "symptom_cluster":    [symptom],
            "hypothesis_cluster": [hypothesis],
            "env_context":        dict(vt_counts),
            "frequency":          len(rows),
            "resolution_rate":    resolution_rate,
            "summary":            "",   # filled by LLM below
        })

    if not patterns:
        return []

    patterns.sort(key=lambda p: p["frequency"], reverse=True)

    # ── LLM semantic summary (non-fatal) ──────────────────────────────────────
    try:
        patterns = _llm_summarize_patterns(patterns[:8], outcome_data)
    except Exception as exc:
        _log.warning("LLM pattern summarization failed (non-fatal): %s", exc)
        for p in patterns:
            if not p["summary"]:
                p["summary"] = f"{p['frequency']} sessions; {p['resolution_rate']:.0%} resolved."

    return patterns


def _llm_summarize_patterns(
    patterns: list[dict],
    outcome_data: list[dict],
) -> list[dict]:
    """
    Call LLM to add semantic summaries to the top statistical clusters.
    Returns the input patterns list unchanged if LLM fails.
    """
    try:
        from app.llm.claude import LLMServiceError, _call, _parse_json

        # Build a compact representation of the clusters
        cluster_block = "\n".join(
            f"- {p['pattern']}: {p['frequency']} sessions, "
            f"{p['resolution_rate']:.0%} resolved, "
            f"vehicles: {dict(sorted(p['env_context'].items(), key=lambda x: -x[1])[:3])}"
            for p in patterns
        )

        # Sample a few unresolved descriptions from largest cluster
        top_sym = patterns[0]["symptom_cluster"][0] if patterns else ""
        sample_descriptions = [
            r.get("description", "")[:100]
            for r in outcome_data
            if r.get("symptom_category") == top_sym
            and r.get("was_resolved") is False
            and r.get("description")
        ][:4]
        desc_block = "\n".join(f"  - {d}" for d in sample_descriptions) or "  (none available)"

        prompt = f"""You are a diagnostic system analyst reviewing failure pattern data from a vehicle diagnostic platform.

Recurring failure clusters (pattern: sessions, resolution rate, vehicle mix):
{cluster_block}

Sample unresolved descriptions from the most common cluster ({top_sym}):
{desc_block}

For each cluster, provide a one-sentence summary describing:
1. What the pattern likely means mechanically or diagnostically
2. Why the resolution rate might be high or low

Respond with ONLY valid JSON:
{{
  "summaries": {{
    "pattern_key": "one-sentence summary"
  }}
}}

pattern_key must exactly match the pattern strings above (e.g. "rough_idle:idle_control_valve").
Omit patterns you have nothing meaningful to say about.
Be specific and mechanical — no filler language."""

        raw = _call(
            max_tokens=600,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            fn_name="analyze_failure_patterns",
        )
        parsed = _parse_json(raw, "analyze_failure_patterns")
        summaries: dict[str, str] = parsed.get("summaries", {})

        for p in patterns:
            key = p["pattern"]
            if key in summaries and isinstance(summaries[key], str):
                p["summary"] = summaries[key][:400]
            if not p["summary"]:
                p["summary"] = (
                    f"{p['frequency']} sessions; "
                    f"{p['resolution_rate']:.0%} resolved."
                )

    except Exception as exc:
        _log.warning("_llm_summarize_patterns failed (non-fatal): %s", exc)
        # Fill auto-generated summaries
        for p in patterns:
            if not p["summary"]:
                p["summary"] = (
                    f"{p['frequency']} sessions; "
                    f"{p['resolution_rate']:.0%} resolved."
                )

    return patterns
