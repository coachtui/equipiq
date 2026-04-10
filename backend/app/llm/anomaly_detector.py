"""
Anomaly Detector — Phase 9.5

Detects unusual or conflicting symptom combinations that suggest the diagnostic
session may be on the wrong track.  Used to suppress premature early exit and
trigger a targeted clarification question.

Outputs are advisory: the system remains fully functional if this call fails.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.llm.claude import LLMServiceError, _call, _parse_json

_log = get_logger(__name__)

# Severity >= this value causes early-exit suppression
ANOMALY_EXIT_THRESHOLD = 0.6

_SAFE_DEFAULT: dict = {
    "is_anomalous": False,
    "reason": "",
    "severity": 0.0,
    "suggested_action": None,
}


def detect_anomaly(
    intake_text: str,
    evidence_log: list[dict],
    top_hypotheses: list[dict],
    symptom_category: str,
    vehicle_context: str,
) -> dict:
    """
    Detect unusual or conflicting symptom combinations.

    Args:
        intake_text:      Original user description.
        evidence_log:     Current evidence packets as dicts.
        top_hypotheses:   Current top hypotheses [{key, label, score}].
        symptom_category: Active symptom category string.
        vehicle_context:  Vehicle description string.

    Returns:
        {
            "is_anomalous":    bool,
            "reason":          str,
            "severity":        float,          # 0.0–1.0
            "suggested_action": str | None     # specific clarifying question or None
        }

    Returns safe default (is_anomalous=False) on any failure.
    """
    if not intake_text or not evidence_log:
        return dict(_SAFE_DEFAULT)

    top_block = "\n".join(
        f"- {h.get('label', h.get('key', ''))}: {round(h.get('score', 0) * 100)}%"
        for h in top_hypotheses[:5]
    ) or "None"

    evidence_block = "\n".join(
        f"- [{p.get('source', '?')}] {p.get('observation', '')[:100]}"
        for p in evidence_log[-8:]
    ) or "None"

    prompt = f"""You are a diagnostic expert reviewing an in-progress session for unusual or contradictory symptom patterns.

Vehicle: {vehicle_context}
Symptom category: {symptom_category.replace('_', ' ')}
User description: "{intake_text}"

Current top hypotheses:
{top_block}

Evidence collected so far:
{evidence_block}

Assess whether this session shows an unusual or conflicting pattern suggesting:
1. The diagnosis may be on the wrong track
2. The symptom presentation is atypical in a diagnostically meaningful way
3. Multiple unrelated systems are simultaneously affected (pointing to a shared root cause)
4. The user's descriptions significantly contradict each other

Respond with ONLY valid JSON:
{{
  "is_anomalous": true or false,
  "reason": "one sentence describing the anomaly (empty string if not anomalous)",
  "severity": 0.0-1.0,
  "suggested_action": "specific clarifying question to ask the user, or null"
}}

Severity guide:
- 0.0:      no anomaly detected
- 0.1–0.3:  mild — slightly unusual but a plausible common explanation exists
- 0.4–0.59: moderate — worth a clarifying question before concluding
- 0.6–1.0:  significant — current diagnostic path is likely incomplete

Rules:
- Most sessions should NOT be anomalous — only flag genuine patterns
- is_anomalous must be false if severity < 0.4
- Do not flag anomalies for normal variation in symptom severity or user language
- suggested_action must be a specific question (e.g. "Did both the check engine and brake warning lights come on at the same time?"), not generic advice"""

    try:
        raw = _call(
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            fn_name="detect_anomaly",
        )
        result = _parse_json(raw, "detect_anomaly")

        severity = max(0.0, min(1.0, float(result.get("severity", 0.0))))
        is_anomalous = bool(result.get("is_anomalous", False)) and severity >= 0.4

        return {
            "is_anomalous": is_anomalous,
            "reason": str(result.get("reason", ""))[:500],
            "severity": severity,
            "suggested_action": (
                str(result["suggested_action"])[:400]
                if result.get("suggested_action")
                else None
            ),
        }

    except (LLMServiceError, Exception) as exc:
        _log.warning("detect_anomaly failed (non-fatal): %s", exc)
        return dict(_SAFE_DEFAULT)
