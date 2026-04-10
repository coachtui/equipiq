"""
Evidence Extractor — Phase 9.5

Extracts structured evidence signals from messy free-text user input.
Normalizes vague language into structured observation dicts suitable for
the evidence log.  Extracted packets carry no score deltas — they enrich
the evidence log for anomaly detection and future contradiction analysis.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.llm.claude import LLMServiceError, _call, _parse_json

_log = get_logger(__name__)

# Minimum description length to bother extracting signals
_MIN_INPUT_LEN = 20


def extract_evidence(
    text_input: str,
    symptom_category: str,
    vehicle_context: str,
) -> list[dict]:
    """
    Extract structured diagnostic signals from user text.

    Args:
        text_input:       Raw user description.
        symptom_category: Active symptom category string.
        vehicle_context:  Vehicle description string.

    Returns:
        list of up to 4 evidence observation dicts:
        {
            "observation":    str,   # normalized description
            "normalized_key": str,   # stable snake_case identifier
            "certainty":      float, # 0.0–1.0
            "affects":        {},    # always empty — no score impact at extraction
            "ambiguous":      bool   # True if observation could have multiple meanings
        }

    Returns empty list on any failure — intake_packet in evidence_log is sufficient.
    """
    if not text_input or len(text_input.strip()) < _MIN_INPUT_LEN:
        return []

    prompt = f"""Extract structured diagnostic signals from this vehicle problem description.

Vehicle: {vehicle_context}
Symptom category: {symptom_category.replace('_', ' ')}
User description: "{text_input}"

Extract up to 4 specific, observable signals mentioned in the description.
Each signal must be a concrete, normalized observation — not a hypothesis or cause.

Good examples:
- "engine cranks but does not fire" → observation: "engine cranks without starting", key: "cranks_no_start", certainty: 0.95
- "sometimes starts fine" → observation: "intermittent failure to start", key: "intermittent_no_start", certainty: 0.7, ambiguous: true
- "smoke from under hood" → observation: "smoke visible from engine bay", key: "engine_bay_smoke", certainty: 0.9
- "makes a clicking sound" → observation: "clicking noise on startup", key: "clicking_on_startup", certainty: 0.85

Respond with ONLY valid JSON:
{{
  "signals": [
    {{
      "observation": "normalized description of what was observed",
      "normalized_key": "snake_case_max_30_chars",
      "certainty": 0.0-1.0,
      "ambiguous": true or false
    }}
  ]
}}

Rules:
- Maximum 4 signals
- Only extract what is explicitly stated or strongly implied
- normalized_key: lowercase snake_case, max 30 characters, no spaces or special chars
- certainty: 0.85–0.95 for explicit clear statements; 0.5–0.7 for implied; 0.3 for vague
- ambiguous: true if the observation could reasonably mean different things
- Do NOT infer causes — only describe what the user observed or reported
- If the description contains no extractable concrete signals, return empty array"""

    try:
        raw = _call(
            max_tokens=400,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            fn_name="extract_evidence",
        )
        parsed = _parse_json(raw, "extract_evidence")
        raw_list = parsed.get("signals", [])

        validated: list[dict] = []
        seen_keys: set[str] = set()
        for s in raw_list[:4]:
            if not isinstance(s, dict):
                continue
            obs = str(s.get("observation", "")).strip()[:200]
            key = (
                str(s.get("normalized_key", ""))
                .strip()[:30]
                .lower()
                .replace(" ", "_")
            )
            # Strip non-alphanumeric/underscore characters
            key = "".join(c for c in key if c.isalnum() or c == "_")
            if not obs or not key or key in seen_keys:
                continue
            seen_keys.add(key)
            validated.append({
                "observation": obs,
                "normalized_key": key,
                "certainty": max(0.0, min(1.0, float(s.get("certainty", 0.5)))),
                "affects": {},
                "ambiguous": bool(s.get("ambiguous", False)),
            })
        return validated

    except (LLMServiceError, Exception) as exc:
        _log.warning("extract_evidence failed (non-fatal): %s", exc)
        return []
