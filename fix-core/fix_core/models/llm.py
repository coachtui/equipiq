"""
Return type stubs for LLMProvider methods.

These models define the contract between the LLM adapter and core.
The adapter (e.g. ClaudeProvider) must return instances of these types.
Core receives them and applies their data deterministically.
"""
from __future__ import annotations

from pydantic import BaseModel

from fix_core.models.result import SynthesizedCause


class IntakeClassification(BaseModel):
    """Output of LLMProvider.intake_classify()."""

    symptom_category: str
    secondary_symptom: str | None = None
    vehicle_type: str
    vehicle_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_engine: str | None = None
    mileage_band: str = "unknown"
    climate: str = "unknown"
    usage_pattern: str = "unknown"
    saltwater_use: str = "unknown"
    storage_time: str = "unknown"
    first_start_of_season: str = "unknown"
    abs_light_on: str = "unknown"
    transmission_type: str = "unknown"
    awd_4wd: str = "unknown"
    summary: str = ""


class AnswerClassification(BaseModel):
    """
    Output of LLMProvider.classify_answer().
    Per CLAUDE.md: returns {option_key, classification_confidence, answer_reliability,
    needs_clarification}. Does not replace tree scoring — feeds the hypothesis scorer
    as a structured evidence source.
    """

    option_key: str
    classification_confidence: float
    answer_reliability: float
    needs_clarification: bool


class SynthesizedResult(BaseModel):
    """
    Output of LLMProvider.synthesize_result().

    ranked_causes: LLM-produced freeform causes (SynthesizedCause).
    next_checks: consumer-mode follow-up checks.
    fault_isolation_steps: professional-mode equivalent (mechanic/operator/HE).
    service_reference: professional-mode service manual pointer.
    """

    ranked_causes: list[SynthesizedCause]
    next_checks: list[str] = []
    fault_isolation_steps: list[str] = []
    diy_difficulty: str | None = None
    suggested_parts: list[dict] = []
    escalation_guidance: str | None = None
    confidence_level: float | None = None
    service_reference: str | None = None


class FollowupInterpretation(BaseModel):
    """Output of LLMProvider.interpret_followup()."""

    interpretation: str
    score_deltas: dict[str, float] = {}
    confidence_modifier: float = 0.5
    new_hypothesis_suggested: str | None = None


class ImageAnalysis(BaseModel):
    """Output of LLMProvider.analyze_image()."""

    interpretation: str
    score_deltas: dict[str, float] = {}
    confidence_modifier: float = 0.0
    safety_concern: str | None = None


class OBDCodeResult(BaseModel):
    """Output of LLMProvider.lookup_obd_code() — stateless, not session-bound."""

    code: str
    description: str
    likely_causes: list[str] = []
    urgency: str = "moderate"
    diy_notes: str | None = None


class HEDTCResult(BaseModel):
    """Output of LLMProvider.lookup_he_dtc() — heavy equipment fault code lookup."""

    code: str
    manufacturer: str | None = None
    description: str
    likely_causes: list[str] = []
    urgency: str = "moderate"
    service_notes: str | None = None
