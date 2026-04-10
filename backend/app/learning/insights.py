"""
Learning system — LLM-powered insight synthesis (Phase 10.5).

Takes structured outputs from patterns.py and produces a ranked list of
human-readable insights with non-binding suggested actions.

All suggestions must go through the existing admin approval flow before
affecting any runtime behavior.  This module never mutates weights, trees,
or routing logic.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.llm.claude import LLMServiceError, _call, _parse_json

_log = get_logger(__name__)

# Max insights returned to avoid overwhelming the admin dashboard
MAX_INSIGHTS = 10


def generate_insights(
    weak_hypotheses: list[dict],
    failure_patterns: list[dict],
    tree_gaps: list[dict],
    anomaly_trends: list[dict],
    metrics_summary: dict,
) -> list[dict]:
    """
    LLM synthesizes all structured analysis outputs into a prioritised list
    of actionable insights for admin review.

    Args:
        weak_hypotheses:  output of detect_weak_hypotheses()
        failure_patterns: output of analyze_failure_patterns()
        tree_gaps:        output of detect_tree_gaps()
        anomaly_trends:   output of detect_anomaly_trends()
        metrics_summary:  dict with total_cases, total_hypotheses, etc.

    Returns:
        list of up to MAX_INSIGHTS dicts:
        {
            "type":             "critical" | "warning" | "opportunity",
            "title":            str,
            "description":      str,
            "affected":         list[str],   # tree or hypothesis IDs
            "suggested_action": str,         # non-binding
            "priority":         int,         # 1 (highest) – 5 (lowest)
        }

    Returns empty list on any LLM failure — deterministic outputs are still
    available directly from the calling endpoint.
    """
    if not any([weak_hypotheses, failure_patterns, tree_gaps, anomaly_trends]):
        return []

    # ── Build compact context for the LLM ────────────────────────────────────

    weak_block = _format_section(
        "Underperforming hypotheses",
        [
            f"- {w['hypothesis_id']}: {'; '.join(w['weaknesses'])} "
            f"(severity={w['severity']:.2f}, n={w['total_cases']})"
            for w in weak_hypotheses[:6]
        ],
    )

    patterns_block = _format_section(
        "Recurring failure patterns",
        [
            f"- {p['pattern']}: {p['frequency']} sessions, "
            f"{p['resolution_rate']:.0%} resolved — {p['summary']}"
            for p in failure_patterns[:5]
        ],
    )

    gaps_block = _format_section(
        "Tree gaps",
        [
            f"- {g['tree_id']}: {'; '.join(g['gap_types'])} "
            f"(severity={g['severity']:.2f}, {g['total_sessions']} sessions)"
            for g in tree_gaps[:5]
        ],
    )

    trends_block = _format_section(
        "Anomaly trends (recent vs historical)",
        [
            f"- {t['symptom_category']} {t['trend_type']}: "
            f"{t['recent_count']} recent vs avg {t['historical_avg']:.1f} "
            f"(spike x{t['spike_factor']:.1f})"
            for t in anomaly_trends[:5]
        ],
    )

    summary_block = (
        f"Total outcomes analysed: {metrics_summary.get('total_cases', 0)}, "
        f"hypotheses tracked: {metrics_summary.get('total_hypotheses', 0)}."
    )

    prompt = f"""You are a diagnostic platform analyst reviewing system performance data.

{summary_block}

{weak_block}

{patterns_block}

{gaps_block}

{trends_block}

Generate up to {MAX_INSIGHTS} prioritised insights for the admin team.

Each insight should:
1. Identify a specific, actionable problem or opportunity
2. Explain what the data suggests is happening
3. Propose a concrete (non-binding) improvement action
4. Indicate which trees or hypotheses are affected

Respond with ONLY valid JSON:
{{
  "insights": [
    {{
      "type":             "critical" | "warning" | "opportunity",
      "title":            "short title (max 60 chars)",
      "description":      "2-3 sentences: what the data shows and why it matters",
      "affected":         ["tree_id or hypothesis_id"],
      "suggested_action": "specific, actionable suggestion (non-binding)",
      "priority":         1-5
    }}
  ]
}}

Insight type guide:
- critical:     data shows a clear failure that is degrading diagnostic accuracy now
- warning:      data shows a developing problem that should be addressed soon
- opportunity:  data shows where the system could improve with targeted changes

Priority: 1 = address immediately, 5 = low priority / nice to have.

Rules:
- Be specific — reference actual hypothesis IDs, tree names, rates from the data
- Suggested actions must go through admin approval — do NOT suggest automatic changes
- Maximum {MAX_INSIGHTS} insights; fewer is better if the data doesn't support more
- If the data shows no meaningful issues, return an empty array"""

    try:
        raw = _call(
            max_tokens=1200,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
            fn_name="generate_insights",
        )
        parsed = _parse_json(raw, "generate_insights")
        raw_insights = parsed.get("insights", [])

        validated: list[dict] = []
        valid_types = {"critical", "warning", "opportunity"}
        for item in raw_insights[:MAX_INSIGHTS]:
            if not isinstance(item, dict):
                continue
            insight_type = str(item.get("type", "warning"))
            if insight_type not in valid_types:
                insight_type = "warning"
            title = str(item.get("title", ""))[:80]
            description = str(item.get("description", ""))[:600]
            if not title or not description:
                continue
            affected = item.get("affected", [])
            if not isinstance(affected, list):
                affected = []
            affected = [str(a)[:100] for a in affected[:10]]
            priority = int(item.get("priority", 3))
            priority = max(1, min(5, priority))
            validated.append({
                "type":             insight_type,
                "title":            title,
                "description":      description,
                "affected":         affected,
                "suggested_action": str(item.get("suggested_action", ""))[:400],
                "priority":         priority,
            })

        return sorted(validated, key=lambda x: x["priority"])

    except (LLMServiceError, Exception) as exc:
        _log.warning("generate_insights failed (non-fatal): %s", exc)
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_section(title: str, lines: list[str]) -> str:
    if not lines:
        return f"{title}:\n  (none)"
    return f"{title}:\n" + "\n".join(lines)
