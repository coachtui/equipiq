"""
Session Mode Analytics — Phase 13D.

Exposes behavioural differences across consumer, operator, and mechanic sessions.

Three layers (mirrors patterns.py and fleet_heavy.py):
1. DB fetch     — pull outcome rows enriched with session_mode and context fields
2. Pure analysis — deterministic metric computation, testable without DB
3. Comparison   — side-by-side mode diff for admin inspection

Metrics tracked per mode:
  session_count, resolution_rate, contradiction_rate, safety_trigger_rate,
  avg_rating, reroute_rate, early_exit_rate

Diagnostic breakdown per mode:
  top_trees, top_hypotheses, unresolved_clusters, anomaly_frequency

Heavy equipment subset: all functions accept an optional vehicle_type filter.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_MODES: tuple[str, ...] = ("consumer", "operator", "mechanic")

# Proxy threshold: a "short" session that likely hit the early-exit path
EARLY_EXIT_TURN_THRESHOLD: int = 4

# Minimum sessions to produce meaningful per-mode output
MIN_MODE_SESSIONS: int = 3

# Top-N for tree and hypothesis breakdowns
TOP_N: int = 5


# ── DB fetch ──────────────────────────────────────────────────────────────────

async def fetch_mode_outcome_data(
    db: AsyncSession,
    vehicle_type: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    """
    Pull outcome rows enriched with session_mode, turn_count, and routing context.

    Includes all three modes.  Optionally filter to a single vehicle_type
    (e.g., "heavy_equipment" for the HE subset).

    Returns flat dicts with:
      session_id, session_mode, vehicle_type, symptom_category,
      selected_tree, top_hypothesis, was_resolved, rating,
      contradiction_count, safety_triggered, turn_count, rerouted,
      created_at
    """
    vt_filter = "AND ds.vehicle_type = :vehicle_type" if vehicle_type else ""

    rows = await db.execute(text(f"""
        SELECT
            do.session_id,
            ds.session_mode,
            ds.vehicle_type,
            ds.symptom_category,
            do.selected_tree,
            do.top_hypothesis,
            do.was_resolved,
            do.rating,
            do.contradiction_count,
            do.safety_triggered,
            ds.turn_count,
            -- rerouted proxy: context had >=2 discriminator candidates
            CASE
                WHEN jsonb_array_length(ds.context->'discriminator_candidates') >= 2
                THEN TRUE ELSE FALSE
            END AS rerouted,
            do.created_at
        FROM diagnostic_outcomes do
        JOIN diagnostic_sessions ds ON ds.id = do.session_id
        LEFT JOIN session_feedback sf ON sf.session_id = do.session_id
        WHERE ds.session_mode IS NOT NULL
          {vt_filter}
        ORDER BY do.created_at DESC
        LIMIT :limit
    """), {"limit": limit, "vehicle_type": vehicle_type} if vehicle_type else {"limit": limit})

    return [
        {
            **dict(r),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows.mappings()
    ]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ModeMetrics:
    """Aggregate metrics for one session mode."""
    mode: str
    session_count: int
    resolution_rate: float          # was_resolved=True / sessions_with_feedback
    contradiction_rate: float       # avg contradictions per session
    safety_trigger_rate: float      # safety_triggered=True / total
    avg_rating: float | None        # None if no rated sessions
    reroute_rate: float             # sessions that went through discriminator / total
    early_exit_rate: float          # sessions with turn_count <= threshold / completed
    anomaly_frequency: float        # fraction with ≥1 contradiction


@dataclass
class ModeDiagnosticBreakdown:
    """Tree and hypothesis breakdown for one session mode."""
    mode: str
    top_trees: list[dict] = field(default_factory=list)
    top_hypotheses: list[dict] = field(default_factory=list)
    unresolved_clusters: list[dict] = field(default_factory=list)
    avg_contradictions: float = 0.0
    anomaly_frequency: float = 0.0


# ── Pure analysis — compute_mode_metrics ─────────────────────────────────────

def compute_mode_metrics(rows: list[dict]) -> dict[str, ModeMetrics]:
    """
    Compute aggregate metrics for each session mode from outcome rows.

    Args:
        rows: List of flat dicts from fetch_mode_outcome_data().

    Returns:
        Dict keyed by session_mode with ModeMetrics values.
        Modes with fewer than MIN_MODE_SESSIONS rows are included but flagged.
    """
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        mode = r.get("session_mode") or "consumer"
        by_mode[mode].append(r)

    result: dict[str, ModeMetrics] = {}
    for mode, group in by_mode.items():
        n = len(group)
        resolved = sum(1 for r in group if r.get("was_resolved") is True)
        rated = [r for r in group if r.get("rating") is not None]
        safety = sum(1 for r in group if r.get("safety_triggered"))
        rerouted = sum(1 for r in group if r.get("rerouted"))
        early_exit = sum(
            1 for r in group
            if (r.get("turn_count") or 0) <= EARLY_EXIT_TURN_THRESHOLD
            and r.get("was_resolved") is not None
        )
        completed = sum(1 for r in group if r.get("was_resolved") is not None)
        contra_total = sum(r.get("contradiction_count") or 0 for r in group)
        anomalies = sum(1 for r in group if (r.get("contradiction_count") or 0) >= 1)

        result[mode] = ModeMetrics(
            mode=mode,
            session_count=n,
            resolution_rate=round(resolved / completed, 4) if completed > 0 else 0.0,
            contradiction_rate=round(contra_total / n, 4) if n > 0 else 0.0,
            safety_trigger_rate=round(safety / n, 4) if n > 0 else 0.0,
            avg_rating=round(sum(r["rating"] for r in rated) / len(rated), 4) if rated else None,
            reroute_rate=round(rerouted / n, 4) if n > 0 else 0.0,
            early_exit_rate=round(early_exit / completed, 4) if completed > 0 else 0.0,
            anomaly_frequency=round(anomalies / n, 4) if n > 0 else 0.0,
        )

    return result


# ── Pure analysis — compute_mode_diagnostic_breakdown ────────────────────────

def compute_mode_diagnostic_breakdown(
    rows: list[dict],
) -> dict[str, ModeDiagnosticBreakdown]:
    """
    Compute per-mode diagnostic breakdown: top trees, top hypotheses,
    unresolved clusters, and contradiction metrics.

    Args:
        rows: List of flat dicts from fetch_mode_outcome_data().

    Returns:
        Dict keyed by session_mode with ModeDiagnosticBreakdown values.
    """
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        mode = r.get("session_mode") or "consumer"
        by_mode[mode].append(r)

    result: dict[str, ModeDiagnosticBreakdown] = {}
    for mode, group in by_mode.items():
        n = len(group)
        contra_total = sum(r.get("contradiction_count") or 0 for r in group)
        anomalies = sum(1 for r in group if (r.get("contradiction_count") or 0) >= 1)

        result[mode] = ModeDiagnosticBreakdown(
            mode=mode,
            top_trees=_top_n_with_resolution(group, "selected_tree"),
            top_hypotheses=_top_n_with_resolution(group, "top_hypothesis"),
            unresolved_clusters=_unresolved_clusters_for_mode(group),
            avg_contradictions=round(contra_total / n, 4) if n > 0 else 0.0,
            anomaly_frequency=round(anomalies / n, 4) if n > 0 else 0.0,
        )

    return result


def _top_n_with_resolution(rows: list[dict], key: str, n: int = TOP_N) -> list[dict]:
    """
    Count rows by `key`, compute per-value resolution rate, return top N by count.
    """
    counts: dict[str, int] = defaultdict(int)
    resolved: dict[str, int] = defaultdict(int)
    for r in rows:
        val = r.get(key)
        if not val:
            continue
        counts[val] += 1
        if r.get("was_resolved") is True:
            resolved[val] += 1

    entries = [
        {
            "key": val,
            "count": cnt,
            "resolution_rate": round(resolved[val] / cnt, 4) if cnt > 0 else 0.0,
        }
        for val, cnt in counts.items()
    ]
    return sorted(entries, key=lambda e: e["count"], reverse=True)[:n]


def _unresolved_clusters_for_mode(rows: list[dict], min_count: int = 3) -> list[dict]:
    """
    Find (tree, hypothesis) pairs with ≥ min_count unresolved sessions.
    """
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        tree = r.get("selected_tree") or "unknown"
        hyp = r.get("top_hypothesis") or "unknown"
        if r.get("was_resolved") is False:
            groups[(tree, hyp)].append(r)

    clusters = [
        {
            "tree_key":        tree,
            "hypothesis_key":  hyp,
            "unresolved_count": len(group),
            "sample_session_ids": [r["session_id"] for r in group[:3]],
        }
        for (tree, hyp), group in groups.items()
        if len(group) >= min_count
    ]
    return sorted(clusters, key=lambda c: c["unresolved_count"], reverse=True)


# ── Mode comparison ───────────────────────────────────────────────────────────

def compare_modes(
    metrics_by_mode: dict[str, ModeMetrics],
) -> list[dict]:
    """
    Produce a structured side-by-side comparison of all modes.

    For each metric, identifies which mode performs best/worst and
    the relative difference between modes.

    Args:
        metrics_by_mode: Output from compute_mode_metrics().

    Returns:
        List of comparison entries, one per metric:
        {
            "metric":     str,
            "by_mode":    {mode: value},
            "best_mode":  str | None,   # mode with highest value (or lowest for bad metrics)
            "worst_mode": str | None,
            "spread":     float,        # max - min across modes
        }
    """
    if not metrics_by_mode:
        return []

    # Metrics where higher = better
    higher_is_better = {
        "resolution_rate", "avg_rating",
    }
    # Metrics where lower = better
    lower_is_better = {
        "contradiction_rate", "safety_trigger_rate", "anomaly_frequency",
    }
    # Neutral / informational
    neutral = {
        "session_count", "reroute_rate", "early_exit_rate",
    }

    _fields = [
        "session_count", "resolution_rate", "contradiction_rate",
        "safety_trigger_rate", "avg_rating", "reroute_rate",
        "early_exit_rate", "anomaly_frequency",
    ]

    comparisons: list[dict] = []
    for field_name in _fields:
        by_mode: dict[str, float | None] = {}
        for mode, m in metrics_by_mode.items():
            val = getattr(m, field_name, None)
            by_mode[mode] = val

        # Skip if all None
        non_null = {k: v for k, v in by_mode.items() if v is not None}
        if not non_null:
            comparisons.append({
                "metric": field_name,
                "by_mode": by_mode,
                "best_mode": None,
                "worst_mode": None,
                "spread": None,
            })
            continue

        spread = round(max(non_null.values()) - min(non_null.values()), 4)

        if field_name in higher_is_better:
            best = max(non_null, key=lambda k: non_null[k])
            worst = min(non_null, key=lambda k: non_null[k])
        elif field_name in lower_is_better:
            best = min(non_null, key=lambda k: non_null[k])
            worst = max(non_null, key=lambda k: non_null[k])
        else:
            best = worst = None

        comparisons.append({
            "metric":    field_name,
            "by_mode":   by_mode,
            "best_mode": best,
            "worst_mode": worst,
            "spread":    spread,
        })

    return comparisons


# ── Summary helper ────────────────────────────────────────────────────────────

def mode_summary_text(
    metrics: dict[str, ModeMetrics],
    breakdown: dict[str, ModeDiagnosticBreakdown],
) -> dict[str, str]:
    """
    Return a one-sentence summary per mode for quick admin scanning.
    Purely deterministic — no LLM.
    """
    summaries: dict[str, str] = {}
    for mode in VALID_MODES:
        m = metrics.get(mode)
        b = breakdown.get(mode)
        if m is None:
            summaries[mode] = f"No {mode} sessions recorded."
            continue

        top_tree = b.top_trees[0]["key"] if b and b.top_trees else "unknown"
        top_tree_label = top_tree.replace("_heavy_equipment", "").replace("_", " ")

        parts = [
            f"{m.session_count} sessions",
            f"{m.resolution_rate:.0%} resolved",
            f"{m.contradiction_rate:.1f} contradictions/session avg",
        ]
        if m.avg_rating:
            parts.append(f"avg rating {m.avg_rating:.1f}/5")
        parts.append(f"top symptom: {top_tree_label}")

        summaries[mode] = f"{mode.title()}: " + ", ".join(parts) + "."

    return summaries
