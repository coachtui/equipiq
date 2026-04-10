"""
Cross-Tree Routing Hints — Phase 9.5

LLM suggests alternative or supporting trees based on free-text intake language.
Must NOT override deterministic ranking — provides a secondary signal only.
Maximum influence is capped at 25% when merged with deterministic candidates.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.llm.claude import LLMServiceError, _call, _parse_json

_log = get_logger(__name__)

# Known tree identifiers LLM may suggest
_VALID_TREES: frozenset[str] = frozenset({
    "no_crank", "crank_no_start", "rough_idle", "loss_of_power",
    "strange_noise", "visible_leak", "overheating", "check_engine_light",
    "brakes", "transmission", "suspension", "hvac",
})


def suggest_tree_candidates(
    intake_text: str,
    symptom_category: str,
    vehicle_context: str,
    existing_candidates: list[dict],
) -> list[dict]:
    """
    LLM suggests alternative or supporting diagnostic trees.

    Args:
        intake_text:          Original user description.
        symptom_category:     Primary symptom already classified.
        vehicle_context:      Vehicle description string.
        existing_candidates:  Deterministic candidates as dicts [{tree_id, score, reasons}].

    Returns:
        list of up to 2 dicts: [{tree_id: str, confidence: float, reasoning: str}]

    Returns empty list on any failure — deterministic routing proceeds unchanged.
    """
    if not intake_text:
        return []

    existing_ids = {c.get("tree_id") for c in existing_candidates}
    existing_block = "\n".join(
        f"- {c.get('tree_id', '?')} (score: {c.get('score', 0):.2f})"
        for c in existing_candidates
    ) or "None"

    prompt = f"""You are a diagnostic routing expert. Review this vehicle problem description and suggest any additional diagnostic trees that may be relevant beyond what the automated system already selected.

Vehicle: {vehicle_context}
Primary symptom classified: {symptom_category.replace('_', ' ')}
User description: "{intake_text}"

Already selected by deterministic system:
{existing_block}

Available diagnostic trees: {sorted(_VALID_TREES)}

Suggest up to 2 additional trees that may be relevant based on what the user described.
Only suggest trees NOT already in the existing list.
Only suggest if there is clear textual evidence in the description.

Respond with ONLY valid JSON:
{{
  "candidates": [
    {{
      "tree_id": "exact tree name from available list",
      "confidence": 0.0-1.0,
      "reasoning": "one sentence citing specific words or phrases from the description"
    }}
  ]
}}

Rules:
- Only suggest trees with clear textual evidence (confidence > 0.4)
- Return empty array if no additional trees are clearly warranted
- tree_id must exactly match one of the available trees
- Do not suggest trees already in the existing list
- Do not guess — only act on explicit signals in the user's words"""

    try:
        raw = _call(
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            fn_name="suggest_tree_candidates",
        )
        parsed = _parse_json(raw, "suggest_tree_candidates")
        raw_list = parsed.get("candidates", [])

        validated: list[dict] = []
        for c in raw_list[:2]:
            if not isinstance(c, dict):
                continue
            tree_id = str(c.get("tree_id", "")).strip()
            if tree_id not in _VALID_TREES or tree_id in existing_ids:
                continue
            conf = max(0.0, min(1.0, float(c.get("confidence", 0.3))))
            if conf < 0.4:
                continue
            validated.append({
                "tree_id": tree_id,
                "confidence": conf,
                "reasoning": str(c.get("reasoning", ""))[:200],
            })
        return validated

    except (LLMServiceError, Exception) as exc:
        _log.warning("suggest_tree_candidates failed (non-fatal): %s", exc)
        return []
