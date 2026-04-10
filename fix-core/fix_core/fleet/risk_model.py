"""
Fleet Asset Risk Model — Phase 16.

Deterministic, weighted, explainable risk scoring for fleet assets.
No LLM involvement. All inputs are structured evidence.

Scoring formula
---------------
risk_score =
    0.30 × unresolved_score    — open or confirmed-unresolved sessions (norm: 5)
  + 0.20 × repeat_score        — same symptom recurring          (norm: 4 repeats)
  + 0.15 × contradiction_score — avg contradictions/session       (norm: 3)
  + 0.20 × safety_score        — safety triggers + critical alerts (norm: 3)
  + 0.05 × anomaly_score       — anomaly-flagged sessions / total
  + 0.05 × telematics_score    — readings with abnormal signals   (norm: 5)
  + 0.05 × service_score       — binary: 1 if >SERVICE_INTERVAL_HOURS since service

All components independently clamped to [0, 1].
Final score clamped to [0, 1] and rounded to 4 decimal places.

Weights sum to 1.0.

Risk levels
-----------
  0.00 – 0.25  →  low
  0.25 – 0.50  →  medium
  0.50 – 0.75  →  high
  0.75 – 1.00  →  critical

NOTE: from __future__ import annotations intentionally omitted here —
this module is imported by FastAPI route files where PEP 563 deferred
evaluation causes type resolution failures with SQLAlchemy text() params.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field


# ── Configuration ─────────────────────────────────────────────────────────────

#: Standard heavy equipment service interval (hours).
SERVICE_INTERVAL_HOURS: int = 250

#: Scoring weights — must sum to 1.0.
WEIGHTS: dict[str, float] = {
    "unresolved":    0.30,
    "repeat":        0.20,
    "contradiction": 0.15,
    "safety":        0.20,
    "anomaly":       0.05,
    "telematics":    0.05,
    "service":       0.05,
}

#: Normalization denominators — value at which a factor reaches its full score.
NORM: dict[str, float] = {
    "unresolved":    5.0,   # 5+ unresolved sessions → score 1.0
    "repeat":        3.0,   # 4+ same-symptom sessions (excess of 1) → score 1.0
    "contradiction": 3.0,   # avg 3+ contradictions/session → score 1.0
    "safety":        3.0,   # 3+ safety events → score 1.0
    "telematics":    5.0,   # 5+ readings with alerts → score 1.0
}

#: Score thresholds for risk level labels (descending order, first match wins).
RISK_LEVEL_THRESHOLDS: list[tuple[float, str]] = [
    (0.75, "critical"),
    (0.50, "high"),
    (0.25, "medium"),
    (0.00, "low"),
]


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class AssetRisk:
    """Risk assessment for a single fleet asset."""

    asset_id: str
    risk_score: float              # 0.0 – 1.0, rounded to 4dp
    risk_level: str                # low | medium | high | critical
    contributing_factors: list[str]  # up to 5, ordered by weighted impact
    recommended_action: str
    component_scores: dict[str, float] = field(default_factory=dict)
    # component_scores keys: unresolved, repeat, contradiction,
    #   safety, anomaly, telematics, service
    # Values are the WEIGHTED contribution (weight × normalised sub-score).


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def _risk_level(score: float) -> str:
    for threshold, label in RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "low"


# ── Core scoring (pure — no DB) ───────────────────────────────────────────────

def compute_asset_risk(
    asset_id: str,
    sessions: list[dict],
    telemetry: list[dict],
) -> AssetRisk:
    """
    Compute risk score for a single asset.

    Pure function — no DB access.  Inputs are plain Python dicts.

    Args:
        asset_id:   Asset identifier string.
        sessions:   List of session dicts.  Each must contain:
                      session_id, status, symptom_category, context (dict),
                      heavy_context (dict), was_resolved (bool|None),
                      safety_triggered (bool), contradiction_count (int),
                      top_hypothesis (str|None).
        telemetry:  List of telemetry dicts.  Each must contain:
                      safety_alerts (list[dict]), received_at (str|None).
                    Each safety_alert dict should have "severity" and "message".

    Returns:
        AssetRisk dataclass with score, level, factors, action,
        and per-component weighted scores.
    """
    n = len(sessions)

    # ── A. Unresolved sessions ────────────────────────────────────────────────
    # A session is unresolved if it is still open OR outcome confirms unresolved.
    unresolved_count = sum(
        1 for s in sessions
        if s.get("status") in ("active", "awaiting_followup")
        or s.get("was_resolved") is False
    )
    unresolved_norm = _clamp(unresolved_count / NORM["unresolved"])

    # ── B. Repeat failures (same symptom) ─────────────────────────────────────
    symptoms = [s["symptom_category"] for s in sessions if s.get("symptom_category")]
    symptom_counts = Counter(symptoms)
    max_repeat = max(symptom_counts.values(), default=0)
    top_symptom = symptom_counts.most_common(1)[0][0] if symptom_counts else None
    # Score 0 for first occurrence; rises from the second repeat onward.
    repeat_norm = _clamp((max_repeat - 1) / NORM["repeat"]) if max_repeat > 1 else 0.0

    # ── C. Contradiction rate ─────────────────────────────────────────────────
    avg_contradictions = (
        sum(s.get("contradiction_count") or 0 for s in sessions) / n if n else 0.0
    )
    contradiction_norm = _clamp(avg_contradictions / NORM["contradiction"])

    # ── D. Safety events ──────────────────────────────────────────────────────
    session_safety_count = sum(1 for s in sessions if s.get("safety_triggered"))
    tel_critical_count = sum(
        1 for t in telemetry
        if any(
            (a.get("severity") or "").lower() == "critical"
            for a in (t.get("safety_alerts") or [])
        )
    )
    total_safety = session_safety_count + tel_critical_count
    safety_norm = _clamp(total_safety / NORM["safety"])

    # ── E. Anomaly rate ───────────────────────────────────────────────────────
    anomaly_sessions = sum(
        1 for s in sessions
        if (s.get("context") or {}).get("last_anomaly")
    )
    anomaly_norm = _clamp(anomaly_sessions / n) if n else 0.0

    # ── F. Telematics abnormal readings ───────────────────────────────────────
    tel_abnormal = sum(1 for t in telemetry if (t.get("safety_alerts") or []))
    telematics_norm = _clamp(tel_abnormal / NORM["telematics"])

    # ── G. Service overdue ────────────────────────────────────────────────────
    service_overdue = False
    service_gap_hours = 0
    for s in sessions:
        hc = s.get("heavy_context") or {}
        hours = hc.get("hours_of_operation")
        last_service = hc.get("last_service_hours")
        if hours and last_service is not None and last_service > 0:
            gap = int(hours) - int(last_service)
            if gap >= SERVICE_INTERVAL_HOURS:
                service_overdue = True
                service_gap_hours = max(service_gap_hours, gap)
    service_norm = 1.0 if service_overdue else 0.0

    # ── Weighted component scores ─────────────────────────────────────────────
    component_scores = {
        "unresolved":    round(WEIGHTS["unresolved"]    * unresolved_norm,    4),
        "repeat":        round(WEIGHTS["repeat"]        * repeat_norm,        4),
        "contradiction": round(WEIGHTS["contradiction"] * contradiction_norm, 4),
        "safety":        round(WEIGHTS["safety"]        * safety_norm,        4),
        "anomaly":       round(WEIGHTS["anomaly"]       * anomaly_norm,       4),
        "telematics":    round(WEIGHTS["telematics"]    * telematics_norm,    4),
        "service":       round(WEIGHTS["service"]       * service_norm,       4),
    }

    risk_score = round(_clamp(sum(component_scores.values())), 4)
    risk_level = _risk_level(risk_score)

    contributing_factors = _build_factors(
        component_scores=component_scores,
        unresolved_count=unresolved_count,
        max_repeat=max_repeat,
        top_symptom=top_symptom,
        avg_contradictions=avg_contradictions,
        session_safety_count=session_safety_count,
        tel_critical_count=tel_critical_count,
        anomaly_sessions=anomaly_sessions,
        tel_abnormal=tel_abnormal,
        service_overdue=service_overdue,
        service_gap_hours=service_gap_hours,
    )

    recommended_action = _recommended_action(
        tel_critical_count=tel_critical_count,
        session_safety_count=session_safety_count,
        unresolved_count=unresolved_count,
        max_repeat=max_repeat,
        top_symptom=top_symptom,
        service_overdue=service_overdue,
        avg_contradictions=avg_contradictions,
        tel_abnormal=tel_abnormal,
        risk_score=risk_score,
    )

    return AssetRisk(
        asset_id=asset_id,
        risk_score=risk_score,
        risk_level=risk_level,
        contributing_factors=contributing_factors,
        recommended_action=recommended_action,
        component_scores=component_scores,
    )


def _build_factors(
    *,
    component_scores: dict[str, float],
    unresolved_count: int,
    max_repeat: int,
    top_symptom: str | None,
    avg_contradictions: float,
    session_safety_count: int,
    tel_critical_count: int,
    anomaly_sessions: int,
    tel_abnormal: int,
    service_overdue: bool,
    service_gap_hours: int,
) -> list[str]:
    """
    Build human-readable contributing factor strings ordered by weighted impact.
    Returns up to 5 factors.
    """
    items: list[tuple[float, str]] = []

    if unresolved_count > 0:
        noun = "session" if unresolved_count == 1 else "sessions"
        items.append((
            component_scores["unresolved"],
            f"{unresolved_count} unresolved {noun}",
        ))

    if max_repeat > 1 and top_symptom:
        label = top_symptom.replace("_", " ")
        items.append((
            component_scores["repeat"],
            f"{max_repeat}× {label} reported (recurring failure)",
        ))

    if session_safety_count > 0 or tel_critical_count > 0:
        parts: list[str] = []
        if session_safety_count > 0:
            noun = "trigger" if session_safety_count == 1 else "triggers"
            parts.append(f"{session_safety_count} session safety {noun}")
        if tel_critical_count > 0:
            noun = "alert" if tel_critical_count == 1 else "alerts"
            parts.append(f"{tel_critical_count} critical sensor {noun}")
        items.append((component_scores["safety"], "; ".join(parts)))

    if avg_contradictions >= 0.5:
        items.append((
            component_scores["contradiction"],
            f"avg {avg_contradictions:.1f} diagnostic contradictions/session",
        ))

    if service_overdue:
        items.append((
            component_scores["service"],
            f"service overdue — {service_gap_hours}h since last "
            f"(interval: {SERVICE_INTERVAL_HOURS}h)",
        ))

    if anomaly_sessions > 0:
        noun = "session" if anomaly_sessions == 1 else "sessions"
        items.append((
            component_scores["anomaly"],
            f"{anomaly_sessions} {noun} with anomaly flags",
        ))

    if tel_abnormal > 0:
        noun = "reading" if tel_abnormal == 1 else "readings"
        items.append((
            component_scores["telematics"],
            f"{tel_abnormal} telemetry {noun} with abnormal signals",
        ))

    items.sort(key=lambda x: x[0], reverse=True)
    return [desc for _, desc in items[:5]]


def _recommended_action(
    *,
    tel_critical_count: int,
    session_safety_count: int,
    unresolved_count: int,
    max_repeat: int,
    top_symptom: str | None,
    service_overdue: bool,
    avg_contradictions: float,
    tel_abnormal: int,
    risk_score: float,
) -> str:
    """
    Determine recommended action from dominant risk factors.
    Priority-ordered — first matching rule wins.
    Traceable: each rule maps directly to one or more input conditions.
    """
    if tel_critical_count > 0:
        return "Immediate stop — critical sensor alert detected"

    if session_safety_count > 0:
        return "Immediate inspection required — safety risk detected in diagnostic session"

    if unresolved_count >= 2 and max_repeat >= 2 and top_symptom:
        label = top_symptom.replace("_", " ")
        noun = "session" if unresolved_count == 1 else "sessions"
        return (
            f"Escalate to mechanic — recurring {label} issue, "
            f"{unresolved_count} {noun} unresolved"
        )

    if unresolved_count >= 3:
        return f"Escalate to mechanic — {unresolved_count} unresolved diagnostic sessions"

    if service_overdue and max_repeat >= 2:
        return "Schedule urgent service — overdue maintenance and recurring fault"

    if service_overdue:
        return "Schedule service — maintenance interval exceeded"

    if max_repeat >= 2 and top_symptom:
        label = top_symptom.replace("_", " ")
        return f"Re-investigate {label} — recurring issue with {max_repeat} sessions"

    if avg_contradictions >= 1.5:
        return (
            "Request diagnostic review — repeated contradictions indicate "
            "complex or multi-system fault"
        )

    if tel_abnormal >= 3:
        return "Monitor sensors — elevated telemetry alerts across recent readings"

    if risk_score > 0.0:
        return "Monitor — asset shows elevated risk signals; schedule inspection when possible"

    return "No immediate action required"


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_assets_by_risk(asset_risks: list[AssetRisk]) -> list[AssetRisk]:
    """Return assets sorted by risk_score descending (highest risk first)."""
    return sorted(asset_risks, key=lambda a: a.risk_score, reverse=True)


