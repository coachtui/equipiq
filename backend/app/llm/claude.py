"""
Claude LLM integration layer.

Three jobs:
1. intake_classify   — parse user description → symptom_category + vehicle info + vehicle_type
2. rephrase_question — turn a tree question + options into natural conversational text
3. classify_answer   — map user free-text answer to a tree option key
4. synthesize_result — produce the final DiagnosticResult from scored hypotheses
5. analyze_image     — vision analysis of uploaded photo → score deltas
6. interpret_followup — user findings after diagnosis → score deltas
7. lookup_obd_code   — DTC/OBD code plain-English lookup (stateless)
8. lookup_he_dtc     — heavy equipment manufacturer fault code lookup (stateless, professional framing)
"""
from __future__ import annotations

import base64
import json
import re

import anthropic

from app.core.config import settings
from app.core.logging_config import get_logger
from app.engine.hypothesis_scorer import Hypothesis

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
_log = get_logger(__name__)


class LLMServiceError(Exception):
    """Raised when the Claude API fails or returns an unparseable response."""

    def __init__(self, message: str = "The diagnostic service is temporarily unavailable. Please try again.") -> None:
        self.message = message
        super().__init__(message)


def _call(*, model: str = "claude-sonnet-4-6", max_tokens: int, temperature: float, messages: list, fn_name: str) -> str:
    """Call the Claude API and return the response text. Raises LLMServiceError on failure."""
    try:
        msg = _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        if msg.stop_reason == "max_tokens":
            _log.error(
                "Response truncated in %s: hit max_tokens=%d (output_tokens=%d)",
                fn_name, max_tokens, msg.usage.output_tokens,
            )
            raise LLMServiceError("Diagnostic service response was incomplete. Please try again.")
        return msg.content[0].text.strip()
    except anthropic.RateLimitError:
        _log.warning("Claude API rate limit hit in %s", fn_name)
        raise LLMServiceError("Rate limit reached on the diagnostic service. Please wait a moment and try again.")
    except anthropic.APITimeoutError:
        _log.warning("Claude API timeout in %s", fn_name)
        raise LLMServiceError("The diagnostic service timed out. Please try again.")
    except anthropic.APIConnectionError:
        _log.warning("Claude API connection error in %s", fn_name)
        raise LLMServiceError("Could not reach the diagnostic service. Please check your connection and try again.")
    except anthropic.APIError as exc:
        _log.error("Claude API error in %s: %s", fn_name, exc)
        raise LLMServiceError() from exc
    except Exception as exc:
        _log.error("Unexpected error in %s: %s", fn_name, exc)
        raise LLMServiceError() from exc


def _parse_json(raw: str, fn_name: str) -> dict:
    """Strip markdown fences and parse JSON. Raises LLMServiceError on parse failure."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _log.error("JSON parse failure in %s: %s", fn_name, exc)
        raise LLMServiceError("Diagnostic service returned an unexpected response. Please try again.") from exc

SYSTEM_PROMPT = """You are a precise automotive diagnostic assistant.
Your role is to help narrow down engine, drivetrain, brake, transmission, suspension, and HVAC issues through focused questions.
Be direct, concise, and professional. Never guess or speculate beyond what evidence supports.
Only address vehicle mechanical and systems issues — politely decline anything else."""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Intake classification
# ─────────────────────────────────────────────────────────────────────────────

SYMPTOM_CATEGORIES = [
    "no_crank",
    "crank_no_start",
    "rough_idle",
    "loss_of_power",
    "strange_noise",
    "visible_leak",
    "overheating",
    "check_engine_light",
    "brakes",
    "transmission",
    "suspension",
    "hvac",
    # Phase 11/12 — heavy equipment symptom categories
    "no_start",               # heavy equipment diesel no-start (combines no_crank + crank_no_start)
    "hydraulic_loss",         # loss of hydraulic pressure or function
    "electrical_fault",       # charging system, battery, wiring, ECU faults on equipment
    "track_or_drive_issue",   # undercarriage / travel drive issues
    "abnormal_noise",         # diesel / hydraulic / mechanical noise on equipment
    "coolant_leak",           # visible coolant loss on equipment
    "implement_failure",      # specific implement / attachment not working
    "cab_electrical",         # cab HVAC, gauges, lights, pressurizer
    "fuel_contamination",     # water, diesel bug, wrong fuel, oxidation
    "unknown",
]

VEHICLE_TYPES = [
    "car", "truck", "motorcycle", "boat", "generator", "atv", "pwc", "rv",
    "heavy_equipment",  # Phase 11 — generic heavy equipment (excavators, dozers, rollers, cranes)
    "tractor",          # Phase 15C — agricultural/utility tractor (PTO, 3-point hitch)
    "excavator",        # Phase 15C — hydraulic excavator / mini-excavator
    "loader",           # Phase 15C — wheel loader / front-end loader / telescopic handler
    "skid_steer",       # Phase 15C — skid steer loader / compact track loader
    "other",
]


def intake_classify(description: str, vehicle_hint: dict | None = None) -> dict:
    """
    Parse the user's initial description.
    Returns: { symptom_category, secondary_symptom, vehicle_type, vehicle_year, vehicle_make,
               vehicle_model, vehicle_engine, mileage_band, climate, usage_pattern,
               saltwater_use, storage_time, first_start_of_season, summary }
    """
    vehicle_str = ""
    if vehicle_hint:
        parts = [str(vehicle_hint.get(k, "")) for k in ("year", "make", "model", "engine") if vehicle_hint.get(k)]
        if parts:
            vehicle_str = f"\nVehicle hint provided: {' '.join(parts)}"

    prompt = f"""Analyze this vehicle or engine problem description and extract structured information.{vehicle_str}

Description: "{description}"

Respond with ONLY valid JSON, no other text:
{{
  "symptom_category": one of {SYMPTOM_CATEGORIES},
  "secondary_symptom": one of {SYMPTOM_CATEGORIES} or null,
  "vehicle_type": one of {VEHICLE_TYPES},
  "vehicle_year": integer or null,
  "vehicle_make": string or null,
  "vehicle_model": string or null,
  "vehicle_engine": string or null,
  "mileage_band": one of ["low", "medium", "high", "unknown"],
  "climate": one of ["cold", "hot", "temperate", "unknown"],
  "usage_pattern": one of ["city", "highway", "mixed", "unknown"],
  "saltwater_use": one of ["yes", "no", "unknown"],
  "storage_time": one of ["none", "weeks", "months", "season", "unknown"],
  "first_start_of_season": one of ["yes", "no", "unknown"],
  "abs_light_on": one of ["yes", "no", "unknown"],
  "transmission_type": one of ["automatic", "manual", "cvt", "unknown"],
  "awd_4wd": one of ["yes", "no", "unknown"],
  "summary": "one sentence describing the core symptom"
}}

Symptom category definitions — passenger vehicles:
- no_crank: engine doesn't turn over at all (silent or just clicks)
- crank_no_start: engine cranks/turns over but won't fire and run
- rough_idle: engine runs but idles roughly, misfires, or stalls
- loss_of_power: engine runs but lacks power, hesitates, or surges
- strange_noise: unusual engine/drivetrain noise (knock, squeal, grind, etc.)
- visible_leak: fluid leak visible (oil, coolant, transmission fluid, etc.)
- overheating: engine temperature too high, temp warning light, steam, or coolant loss
- check_engine_light: check engine / malfunction indicator light is on (with or without drivability issues)
- brakes: brake system problem — spongy, soft, or hard pedal; pulling to one side; grinding, squealing, or metal-on-metal noise when braking; ABS light on
- transmission: transmission problem — slipping, delayed engagement, no drive or no reverse, harsh shifts, shudder, stuck in limp mode
- suspension: suspension/steering problem — clunking, excessive bounce, pulling, shimmy, uneven tire wear
- hvac: heating/ventilation/A/C problem — no cold air, no heat, weak airflow, blower issues

Symptom category definitions — heavy equipment (use these when vehicle_type is heavy_equipment, tractor, excavator, loader, or skid_steer):
- no_start: diesel-powered heavy equipment won't start at all (use instead of no_crank/crank_no_start)
- hydraulic_loss: loss of hydraulic pressure or function — implements slow/dead, travel hydraulics failed
- electrical_fault: charging system, battery, wiring harness, ECU fault on equipment
- track_or_drive_issue: undercarriage problem, track derailed/loose, machine won't travel or pulls to one side
- abnormal_noise: unusual noise from diesel engine, hydraulic pump, undercarriage, or exhaust on equipment
- coolant_leak: visible coolant loss on heavy equipment (hose, radiator, water pump, freeze plug)
- implement_failure: specific implement or attachment not working (boom, bucket, blade, forks) while other functions may be fine
- cab_electrical: cab HVAC, gauges, work lights, pressurizer, or wiper failure on enclosed-cab equipment
- fuel_contamination: bad fuel quality — water in diesel, diesel bug, wrong fuel, gelled fuel, DEF contamination

- unknown: cannot determine from description

secondary_symptom rules:
- Set to a valid symptom category only if the user clearly describes a SECOND distinct symptom alongside the primary one
- Must be different from symptom_category
- Set to null if only one symptom is described, or if the second complaint is vague/ambiguous
- Do NOT set to "unknown"

mileage_band: infer from odometer mention or vehicle age; "low" <50k mi, "medium" 50–150k, "high" >150k; "unknown" if not stated; for heavy equipment use "low"/"medium"/"high" based on service hours if mentioned
climate: infer from seasonal cues, temperature mentions, or location; "cold" if winter/freezing, "hot" if summer/desert; "unknown" if not clear
usage_pattern: "city" if stop-and-go/urban, "highway" if mostly highway miles, "mixed" if both; "unknown" if not stated; for heavy equipment: "mixed" unless clearly jobsite-specific
saltwater_use: for boats only — "yes" if saltwater/ocean/bay/salt, "no" if freshwater/lake/river/pond; "unknown" for non-boats or if not stated
storage_time: how long since the engine was last run — infer from "sat all winter", "been sitting for months", "just pulled from storage", "haven't used it since last summer"; "none" if used recently; "unknown" if not stated
first_start_of_season: "yes" if description clearly indicates first use after winter/off-season storage; "no" if used regularly; "unknown" if not clear
abs_light_on: "yes" if user mentions ABS light, anti-lock light, stability control light, or traction control light alongside brake symptoms; "no" if explicitly stated not on; "unknown" otherwise
transmission_type: "manual" if user mentions clutch, stick shift, third pedal, or manual transmission; "cvt" if explicitly mentioned; "automatic" if stated, implied, or vehicle type is boat or rv; "unknown" if not stated; for heavy equipment: "automatic" (hydrostatic or torque converter)
awd_4wd: "yes" if vehicle model or description clearly indicates AWD, 4WD, or 4x4; "no" if FWD or RWD explicitly stated; "unknown" if not stated; for heavy equipment: "yes" if tracked or all-wheel-drive equipment

Vehicle type definitions:
- car: passenger car, crossover SUV under ~6000 lbs, minivan
- truck: pickup truck, cargo van, full-size SUV, work truck
- motorcycle: two-wheeled motor vehicle, street bike, cruiser, dirt bike, scooter
- boat: marine inboard or outboard engine
- generator: standby or portable generator
- atv: ATV or UTV (all-terrain vehicle, side-by-side)
- pwc: personal watercraft (jet ski, WaveRunner, Sea-Doo)
- rv: recreational vehicle or motorhome — Class A, B, or C motorhome; do NOT classify as rv if towing a trailer
- heavy_equipment: general heavy equipment not covered by a more specific type — bulldozers/dozers, cranes, motor graders, compactors/rollers, scrapers, telehandlers, mining equipment; also use for any HE when the specific subtype is ambiguous
- tractor: agricultural or utility tractor with PTO, 3-point hitch — farm tractor, orchard tractor, compact utility tractor, row crop tractor (John Deere, Case IH, New Holland, Kubota, Massey Ferguson, etc.)
- excavator: hydraulic excavator or mini-excavator — full-size or compact, tracked; operator uses joysticks for boom/arm/bucket and swing (CAT, Deere, Komatsu, Volvo, Hitachi, Doosan, Takeuchi, Yanmar)
- loader: wheel loader or front-end loader — articulated frame, rubber-tyred, lifts with front bucket (CAT 950, Deere 544, Komatsu WA); also includes telescopic handlers / telehandlers when symptom matches
- skid_steer: skid steer loader or compact track loader (CTL) — small, enclosed-cab machine that steers by varying wheel speed; Bobcat, CAT 226D, Case SR, Deere 330G, New Holland L
- other: anything else with an engine (lawn equipment, snowmobile, etc.)"""

    raw = _call(max_tokens=550, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="intake_classify")
    return _parse_json(raw, "intake_classify")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rephrase question
# ─────────────────────────────────────────────────────────────────────────────

def rephrase_question(
    question: str,
    options: list[str],
    vehicle_context: str,
    turn: int,
    session_mode: str = "consumer",
) -> str:
    """
    Turn a raw diagnostic question + options into a natural, conversational message.
    Returns the full message to send to the user.

    session_mode:
      "consumer"  — plain language, friendly tone (default)
      "operator"  — jobsite language, physical check prompts, no jargon
      "mechanic"  — technical language, concise, spec-level detail welcome
    """
    options_block = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))

    if session_mode == "operator":
        tone_instruction = (
            "You are talking to a machine operator on a jobsite — not a mechanic. "
            "Use plain, direct language. Avoid technical jargon. "
            "Where useful, include a simple physical check they can do on the spot "
            "(e.g., 'look at the fluid level', 'listen for a click', 'check if the lever moves'). "
            "Keep it short — they are busy and may be in noisy conditions."
        )
    elif session_mode == "mechanic":
        tone_instruction = (
            "You are communicating with an experienced mechanic. "
            "Use correct technical terminology. Be precise and concise. "
            "Skip basic explanations — they know the system. "
            "Reference component names, test procedures, and specs where relevant."
        )
    else:  # consumer (default)
        tone_instruction = (
            "You are a knowledgeable mechanic helping a vehicle owner diagnose a problem. "
            "Use plain language. Be helpful, direct, and brief (1–3 sentences). "
            "Do NOT add introductory filler like 'Great question!' or 'I understand your concern.'"
        )

    prompt = f"""{tone_instruction}
Vehicle / equipment: {vehicle_context}
Turn: {turn}

Rephrase the following diagnostic question into a natural message.
Include the answer options as a numbered list at the end.

Question: {question}
Options:
{options_block}

Respond with only the rephrased message and numbered options."""

    return _call(max_tokens=350, temperature=0.3, messages=[{"role": "user", "content": prompt}], fn_name="rephrase_question")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Classify answer
# ─────────────────────────────────────────────────────────────────────────────

def classify_answer(
    question: str,
    options: list[dict],
    user_answer: str,
) -> dict:
    """
    Map user free-text answer to the closest option match key.

    Returns:
        {
          "option_key": str,
          "classification_confidence": float,  # 0.0–1.0, how certain the LLM was
          "answer_reliability": float,          # 0.0–1.0, how clear/specific the answer was
          "needs_clarification": bool           # True if the answer was vague/ambiguous
        }
    """
    options_block = "\n".join(
        f"- match_key: {opt['match']} | label: {opt['label']}"
        for opt in options
    )

    prompt = f"""Match the user's answer to the closest option and assess reliability.

Question asked: {question}
Available options:
{options_block}

User answered: "{user_answer}"

Respond with ONLY valid JSON:
{{
  "option_key": "the match_key of the best matching option",
  "classification_confidence": 0.0-1.0,
  "answer_reliability": 0.0-1.0,
  "needs_clarification": true or false
}}

Scoring guide:
- classification_confidence: how certain you are this is the right option (1.0 = unambiguous match, 0.5 = best guess)
- answer_reliability: how clear/specific the user's answer was (1.0 = direct and specific, 0.5 = vague, 0.2 = off-topic or unclear)
- needs_clarification: true if the answer was so vague you cannot confidently match it"""

    raw = _call(max_tokens=100, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="classify_answer")
    result = _parse_json(raw, "classify_answer")

    # Validate option_key against available options; fall back to first option
    valid_keys = {opt["match"] for opt in options}
    if result.get("option_key") not in valid_keys:
        result["option_key"] = options[0]["match"] if options else ""
        result["classification_confidence"] = 0.3
        result["answer_reliability"] = 0.3

    # Ensure all fields are present with sensible defaults
    result.setdefault("classification_confidence", 0.8)
    result.setdefault("answer_reliability", 0.8)
    result.setdefault("needs_clarification", False)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. Synthesize result
# ─────────────────────────────────────────────────────────────────────────────

_HE_VEHICLE_TYPES = {"heavy_equipment", "tractor", "excavator", "loader", "skid_steer"}


def synthesize_result(
    symptom_category: str,
    vehicle_context: str,
    ranked_hypotheses: list[Hypothesis],
    conversation_summary: str,
    secondary_symptom: str | None = None,
    session_mode: str = "consumer",
    vehicle_type: str = "",
) -> dict:
    """
    Generate the final diagnostic result from scored hypotheses.
    Returns a dict matching DiagnosticResultOut schema.
    Consumer mode: next_checks + diy_difficulty
    Professional mode (mechanic/operator or HE types): fault_isolation_steps + service_reference, no diy_difficulty
    """
    professional = session_mode in {"mechanic", "operator"} or vehicle_type in _HE_VEHICLE_TYPES

    # Build hypothesis context
    hyp_block = "\n".join(
        f"- {h.label} (confidence: {round(h.score * 100)}%)\n  Evidence: {'; '.join(h.evidence) if h.evidence else 'prior probability'}"
        for h in ranked_hypotheses[:5]
    )

    secondary_line = ""
    if secondary_symptom and secondary_symptom != "unknown":
        secondary_line = f"\nSecondary symptom also reported: {secondary_symptom.replace('_', ' ')}. Note whether the top diagnosis explains both."

    if professional:
        prompt = f"""You are a senior equipment technician reviewing a diagnostic session.
Vehicle/Equipment: {vehicle_context}
Symptom: {symptom_category.replace("_", " ")}{secondary_line}

Ranked hypotheses from diagnostic session:
{hyp_block}

Conversation summary: {conversation_summary}

Generate a professional technical diagnostic result. Respond with ONLY valid JSON:
{{
  "ranked_causes": [
    {{
      "cause": "cause name",
      "confidence": 0.0-1.0 (match hypothesis scores above),
      "reasoning": "one sentence technical rationale"
    }}
  ],
  "fault_isolation_steps": ["technician-level step 1", "step 2", ...],
  "suggested_parts": [
    {{"name": "part name or OEM description", "notes": "brief technical note"}}
  ],
  "escalation_guidance": "escalation condition or null",
  "service_reference": "service manual section, TSB, or bulletin reference if applicable, else null"
}}

Rules:
- Include top 3-5 causes only
- fault_isolation_steps: specific technician-level diagnostic actions in logical order (max 5); no DIY consumer framing
- suggested_parts only if confidence >= 0.5; use OEM descriptions where known
- escalation_guidance: dealer/specialist condition, or null
- service_reference: relevant manual section or TSB if known; null if uncertain
- Be precise and technically direct. No consumer DIY framing."""
    else:
        # Determine overall DIY difficulty from top hypothesis
        top = ranked_hypotheses[0] if ranked_hypotheses else None
        default_diy = top.diy_difficulty if top else "moderate"  # noqa: F841

        prompt = f"""You are a senior automotive diagnostic expert.
Vehicle: {vehicle_context}
Symptom category: {symptom_category.replace("_", " ")}{secondary_line}

Ranked hypotheses from diagnostic session:
{hyp_block}

Conversation summary: {conversation_summary}

Generate a structured diagnostic result. Respond with ONLY valid JSON:
{{
  "ranked_causes": [
    {{
      "cause": "cause name",
      "confidence": 0.0-1.0 (match hypothesis scores above),
      "reasoning": "one sentence why this is suspected"
    }}
  ],
  "next_checks": ["actionable check 1", "actionable check 2", ...],
  "diy_difficulty": one of ["easy", "moderate", "hard", "seek_mechanic"],
  "suggested_parts": [
    {{"name": "part name", "notes": "brief note"}}
  ],
  "escalation_guidance": "when to see a mechanic (or null if DIY is viable)"
}}

Rules:
- Include top 3-5 causes only
- next_checks should be specific and actionable (max 5)
- suggested_parts only if confidence >= 0.5
- escalation_guidance: include if top cause is seek_mechanic difficulty or confidence is split
- Be concise. No filler text."""

    raw = _call(max_tokens=1200, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="synthesize_result")
    result = _parse_json(raw, "synthesize_result")

    # Merge parts from top hypotheses into suggested_parts if not already included
    if ranked_hypotheses and ranked_hypotheses[0].score >= 0.5:
        existing_names = {p["name"].lower() for p in result.get("suggested_parts", [])}
        for h in ranked_hypotheses[:2]:
            for part in h.parts:
                if part["name"].lower() not in existing_names:
                    result.setdefault("suggested_parts", []).append(part)
                    existing_names.add(part["name"].lower())

    result["confidence_level"] = ranked_hypotheses[0].score if ranked_hypotheses else 0.0
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. Interpret follow-up finding
# ─────────────────────────────────────────────────────────────────────────────

def interpret_followup(
    symptom_category: str,
    vehicle_context: str,
    ranked_hypotheses: list[Hypothesis],
    next_checks: list[str],
    followup_text: str,
) -> dict:
    """
    Given what the user found after performing the suggested checks, update
    hypothesis confidence scores and return a brief interpretation.

    Returns: { score_deltas: {hypothesis_key: float}, interpretation: str }
    """
    hyp_block = "\n".join(
        f"- key: {h.key} | label: {h.label} | current_confidence: {round(h.score * 100)}%"
        for h in ranked_hypotheses[:6]
    )
    checks_block = "\n".join(f"- {c}" for c in next_checks)

    prompt = f"""You are a senior automotive diagnostic expert reviewing follow-up findings from a customer.
Vehicle: {vehicle_context}
Symptom: {symptom_category.replace("_", " ")}

Current ranked hypotheses:
{hyp_block}

Checks that were suggested:
{checks_block}

Customer's follow-up report: "{followup_text}"

Based on what the customer found, update the hypothesis confidence scores.
Respond with ONLY valid JSON:
{{
  "score_deltas": {{
    "hypothesis_key": delta_float
  }},
  "interpretation": "one or two sentences summarizing what the finding means for the diagnosis"
}}

Rules:
- Only include hypotheses whose scores should change
- Deltas should be between -0.4 and +0.4
- Positive delta = finding supports this hypothesis
- Negative delta = finding makes this hypothesis less likely
- interpretation should be plain, direct, mechanic-style language"""

    raw = _call(max_tokens=400, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="interpret_followup")
    return _parse_json(raw, "interpret_followup")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Analyze uploaded image
# ─────────────────────────────────────────────────────────────────────────────

def analyze_image(
    image_data: bytes,
    media_type: str,
    symptom_category: str,
    vehicle_context: str,
    ranked_hypotheses: list[Hypothesis],
    confidence_modifier: float = 0.8,
) -> dict:
    """
    Analyze a customer-uploaded photo using Claude vision.
    Returns: { score_deltas: {hypothesis_key: float}, interpretation: str }
    """
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    hyp_block = "\n".join(
        f"- key: {h.key} | label: {h.label} | current_confidence: {round(h.score * 100)}%"
        for h in ranked_hypotheses[:6]
    )

    raw = _call(
        max_tokens=500,
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": f"""You are a senior diagnostic expert reviewing a photo submitted by a customer.
Vehicle: {vehicle_context}
Symptom category: {symptom_category.replace("_", " ")}

Current diagnostic hypotheses:
{hyp_block}

Analyze this image and determine if it provides diagnostic evidence.
Respond with ONLY valid JSON:
{{
  "score_deltas": {{"hypothesis_key": delta_float}},
  "interpretation": "one or two sentences describing what you see and what it means for the diagnosis"
}}

Rules:
- Only include hypotheses whose scores should change based on visual evidence
- Deltas between -0.4 and +0.4
- If the image is not diagnostically useful (blurry, wrong subject, unrelated), return empty score_deltas and say so in interpretation
- Be specific about what you observe""",
                },
            ],
        }],
        fn_name="analyze_image",
    )
    result = _parse_json(raw, "analyze_image")
    if confidence_modifier != 1.0:
        result["score_deltas"] = {
            k: round(v * confidence_modifier, 4)
            for k, v in result.get("score_deltas", {}).items()
        }
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 7. OBD / DTC code lookup
# ─────────────────────────────────────────────────────────────────────────────

def lookup_obd_code(code: str, vehicle_context: str) -> dict:
    """
    Look up a DTC/OBD code and return a structured plain-English explanation.
    Returns: { code, description, severity, likely_causes, next_steps, diy_difficulty }
    severity: low | moderate | high | critical
    diy_difficulty: easy | moderate | hard | seek_mechanic
    """
    prompt = f"""You are a senior automotive diagnostic expert. A customer has an OBD-II / DTC fault code.

Code: {code}
Vehicle: {vehicle_context}

Explain this code clearly and provide actionable guidance.
Respond with ONLY valid JSON, no other text:
{{
  "code": "{code}",
  "description": "plain-English explanation of what this code means (1-2 sentences)",
  "severity": one of ["low", "moderate", "high", "critical"],
  "likely_causes": ["cause 1", "cause 2", "cause 3"],
  "next_steps": ["step 1", "step 2", "step 3"],
  "diy_difficulty": one of ["easy", "moderate", "hard", "seek_mechanic"]
}}

Severity guide:
- low: informational, safe to drive short-term (e.g. minor EVAP leak)
- moderate: address within days/weeks, may affect fuel economy or emissions
- high: address promptly, drivability impact or potential damage if ignored
- critical: stop driving or severe damage risk (e.g. misfire with catalyst damage, oil pressure)

Rules:
- likely_causes: 3-5 most common root causes in order of likelihood
- next_steps: specific diagnostic actions or repairs (not generic "see a mechanic")
- Be concise. No filler text."""

    raw = _call(max_tokens=600, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="lookup_obd_code")
    return _parse_json(raw, "lookup_obd_code")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Heavy equipment manufacturer fault code lookup
# ─────────────────────────────────────────────────────────────────────────────

def lookup_he_dtc(code: str, manufacturer: str, equipment_context: str) -> dict:
    """
    Look up a heavy equipment manufacturer fault code and return professional-framing guidance.
    Supports CAT, Deere, Komatsu, Kubota, Volvo CE, and other OEMs.
    Returns: { code, manufacturer, description, severity, likely_causes,
               isolation_steps, part_numbers, service_reference }
    severity: low | moderate | high | critical
    No diy_difficulty — results are framed for trained technicians and operators.
    """
    prompt = f"""You are a senior heavy equipment technician with expertise across CAT, John Deere, Komatsu, Kubota, Volvo CE, and other OEMs. A technician or operator has a fault code from their machine's diagnostic system.

Code: {code}
Manufacturer: {manufacturer}
Equipment: {equipment_context}

Provide professional technical guidance for this fault code.
Respond with ONLY valid JSON, no other text:
{{
  "code": "{code}",
  "manufacturer": "{manufacturer}",
  "description": "technical explanation of what this code indicates (1-2 sentences)",
  "severity": one of ["low", "moderate", "high", "critical"],
  "likely_causes": ["cause 1", "cause 2", "cause 3"],
  "isolation_steps": ["step 1", "step 2", "step 3"],
  "part_numbers": ["part description or number if known", "..."],
  "service_reference": "service manual section or bulletin reference if applicable, else null"
}}

Severity guide:
- low: informational, continue operation with monitoring
- moderate: schedule service, address within days — performance or emissions impact
- high: address promptly — potential damage or regulatory non-compliance if ignored
- critical: shut down immediately — risk of major component damage or operator safety

Rules:
- isolation_steps: specific technician-level checks in logical diagnostic order (not generic "call dealer")
- part_numbers: include OEM part descriptions if known; omit list if not applicable
- service_reference: reference service manual chapter/section or TSB number if known (null if uncertain)
- Be precise and technically accurate. No consumer-level DIY framing."""

    raw = _call(max_tokens=700, temperature=0, messages=[{"role": "user", "content": prompt}], fn_name="lookup_he_dtc")
    return _parse_json(raw, "lookup_he_dtc")
