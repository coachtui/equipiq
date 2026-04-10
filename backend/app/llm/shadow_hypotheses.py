"""
Shadow Hypothesis Generator — Phase 9.5

Allows LLM to propose hypotheses not currently dominant in the tree.
Outputs are advisory only: they never modify scores or override the
deterministic engine.  The controller stores them as informational
alternatives exposed to the user as "other possibilities."
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.llm.claude import LLMServiceError, _call, _parse_json

_log = get_logger(__name__)


def generate_shadow_hypotheses(
    intake_text: str,
    evidence_log: list[dict],
    top_hypotheses: list[dict],
    symptom_category: str,
    vehicle_context: str,
) -> list[dict]:
    """
    Propose up to 3 alternative hypotheses not currently dominant in the tree.

    Args:
        intake_text:      Original user description.
        evidence_log:     Current evidence packets as dicts.
        top_hypotheses:   Current top hypotheses [{key, label, score}].
        symptom_category: Active symptom category string.
        vehicle_context:  "Year Make Model Engine" style vehicle string.

    Returns:
        list of up to 3 dicts:
        {
            "hypothesis": str,
            "confidence": float,   # 0.0–1.0
            "reasoning": str,
            "related_tree": str | None
        }

    Returns empty list on any failure — system operates without shadow hypotheses.
    """
    if not intake_text:
        return []

    top_block = "\n".join(
        f"- {h.get('label', h.get('key', ''))}: {round(h.get('score', 0) * 100)}%"
        for h in top_hypotheses[:5]
    ) or "None"

    evidence_block = "\n".join(
        f"- [{p.get('source', '?')}] {p.get('observation', '')[:120]}"
        for p in evidence_log[-6:]
    ) or "None"

    prompt = f"""Review this in-progress diagnostic session and identify any plausible causes that the current analysis may be missing or underweighting.

Vehicle: {vehicle_context}
Symptom: {symptom_category.replace('_', ' ')}
User description: "{intake_text}"

Current top hypotheses (from deterministic tree):
{top_block}

Recent evidence collected:
{evidence_block}

Identify up to 3 alternative hypotheses that:
1. Are mechanically plausible given the symptom and evidence
2. Are NOT already dominant in the current top hypotheses above
3. Could be missed by a standard tree-based diagnosis
4. If possible, map to one of: no_crank, crank_no_start, rough_idle, loss_of_power, strange_noise, visible_leak, overheating, check_engine_light, brakes, transmission, suspension, hvac

Respond with ONLY valid JSON:
{{
  "shadow_hypotheses": [
    {{
      "hypothesis": "specific cause name",
      "confidence": 0.0-1.0,
      "reasoning": "one sentence explaining why this is plausible",
      "related_tree": "symptom_category string or null"
    }}
  ]
}}

Rules:
- Maximum 3 hypotheses
- confidence: 0.6+ only with strong mechanical evidence; 0.3–0.5 for plausible but uncertain
- If no meaningful alternatives exist, return an empty array
- Do not repeat causes already in the top hypotheses list
- Be specific ("cracked intake manifold" not "intake problem")"""

    try:
        raw = _call(
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
            fn_name="generate_shadow_hypotheses",
        )
        parsed = _parse_json(raw, "generate_shadow_hypotheses")
        raw_list = parsed.get("shadow_hypotheses", [])

        validated: list[dict] = []
        for h in raw_list[:3]:
            if not isinstance(h, dict):
                continue
            hypothesis = str(h.get("hypothesis", "")).strip()[:200]
            reasoning = str(h.get("reasoning", "")).strip()[:300]
            if not hypothesis or not reasoning:
                continue
            validated.append({
                "hypothesis": hypothesis,
                "confidence": max(0.0, min(1.0, float(h.get("confidence", 0.3)))),
                "reasoning": reasoning,
                "related_tree": (
                    str(h["related_tree"]) if isinstance(h.get("related_tree"), str) else None
                ),
            })
        return validated

    except (LLMServiceError, Exception) as exc:
        _log.warning("generate_shadow_hypotheses failed (non-fatal): %s", exc)
        return []
