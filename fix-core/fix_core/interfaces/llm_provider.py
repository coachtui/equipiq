from __future__ import annotations

from typing import Protocol, runtime_checkable

from fix_core.models.llm import (
    AnswerClassification,
    FollowupInterpretation,
    HEDTCResult,
    ImageAnalysis,
    IntakeClassification,
    OBDCodeResult,
    SynthesizedResult,
)
from fix_core.models.hypothesis import HypothesisScore
from fix_core.models.session import DiagnosticSession
from fix_core.models.vehicle import VehicleContext


@runtime_checkable
class LLMProvider(Protocol):
    """
    Contract for the LLM integration layer.

    Core calls these methods; the adapter supplies the implementation (e.g.
    ClaudeProvider backed by the Anthropic SDK). Core has no knowledge of which
    model, API key, or SDK is used.

    All methods are async. Implementations must raise a provider-specific error
    (e.g. LLMServiceError) on failure — core does not catch raw SDK errors.

    Per CLAUDE.md: LLM outputs are structured evidence or routing hints. They do
    not replace deterministic scoring. The seven functions below are the approved
    set; lookup_he_dtc is the eighth, approved for heavy equipment workflows.
    New functions require explicit approval before being added here.
    """

    async def intake_classify(
        self,
        description: str,
        vehicle_hint: dict | None = None,
    ) -> IntakeClassification:
        """
        Parse the user's initial symptom description.
        Returns structured intake fields (symptom_category, vehicle_type, etc.).
        """
        ...

    async def rephrase_question(
        self,
        question: str,
        options: dict,
        vehicle_context: VehicleContext,
        turn: int = 0,
        session_mode: str = "consumer",
    ) -> str:
        """
        Rephrase a raw tree question into natural conversational language.
        Returns the rephrased question string only.

        turn: current question depth (0-indexed); used by the LLM to calibrate detail level.
        session_mode: "consumer" | "mechanic" | "operator" — controls framing.
        Defaults are backward compatible with callers that omit these params.
        """
        ...

    async def classify_answer(
        self,
        question: str,
        options: dict,
        user_answer: str,
        hypotheses: list[HypothesisScore],
    ) -> AnswerClassification:
        """
        Map free-text user answer to a tree option key.
        Returns {option_key, classification_confidence, answer_reliability,
        needs_clarification}. Does NOT replace tree scoring.
        """
        ...

    async def synthesize_result(
        self,
        session: DiagnosticSession,
        hypotheses: list[HypothesisScore],
    ) -> SynthesizedResult:
        """
        Produce a human-readable diagnostic result from scored hypotheses.
        Returns structured result data consumed by DiagnosticResult.
        """
        ...

    async def interpret_followup(
        self,
        user_finding: str,
        session: DiagnosticSession,
    ) -> FollowupInterpretation:
        """
        Interpret user findings after initial diagnosis.
        Returns score deltas and a plain-language interpretation.
        """
        ...

    async def analyze_image(
        self,
        image_bytes: bytes,
        vehicle_context: VehicleContext,
        media_type: str = "image/jpeg",
        symptom_category: str = "",
        ranked_hypotheses: list | None = None,
        confidence_modifier: float = 1.0,
    ) -> ImageAnalysis:
        """
        Vision analysis of an uploaded photo or video frame.
        Returns score deltas and a plain-language interpretation.
        Receives raw bytes — storage resolution is the adapter's responsibility.

        media_type: MIME type of the image bytes (e.g. "image/jpeg", "image/png").
        symptom_category: active diagnostic category, forwarded to the LLM for context.
        ranked_hypotheses: current scored hypotheses; LLM uses key/label/score only.
        confidence_modifier: scalar applied to returned score_deltas (0.0–1.0).
        """
        ...

    async def lookup_obd_code(
        self,
        code: str,
        vehicle_type: str,
    ) -> OBDCodeResult:
        """
        Stateless DTC/OBD code lookup. Not session-bound.
        Returns plain-English description, likely causes, and urgency.
        """
        ...

    async def lookup_he_dtc(
        self,
        code: str,
        manufacturer: str | None,
        equipment_type: str | None,
    ) -> HEDTCResult:
        """
        Stateless heavy equipment manufacturer fault code lookup.
        Not session-bound. Professional framing for operator/mechanic context.
        """
        ...
