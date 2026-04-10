"""
ClaudeProvider — implements fix_core.interfaces.LLMProvider by wrapping
the synchronous functions in app.llm.claude via asyncio.to_thread.

Signature notes
───────────────
Not all interface signatures align perfectly with claude.py. Where they
diverge, translation happens here rather than touching claude.py or fix_core.

• classify_answer  — interface passes hypotheses; claude.py ignores them (unused).
• rephrase_question — interface uses VehicleContext object; claude.py needs a str
  plus turn/session_mode. ClaudeProvider extracts the str and defaults the rest.
  Callers that need full context should continue to call claude.py directly.
• synthesize_result / interpret_followup / analyze_image — significant arg
  mismatches; not wrapped here. sessions.py calls claude.py directly for those.
• lookup_obd_code / lookup_he_dtc — field-name translation needed (dict → model).
"""
from __future__ import annotations

import asyncio

import app.llm.claude as _claude
from fix_core.models.hypothesis import HypothesisScore
from fix_core.models.llm import (
    AnswerClassification,
    FollowupInterpretation,
    HEDTCResult,
    ImageAnalysis,
    IntakeClassification,
    OBDCodeResult,
    SynthesizedResult,
)
from fix_core.models.result import SynthesizedCause
from fix_core.models.session import DiagnosticSession
from fix_core.models.vehicle import VehicleContext


class ClaudeProvider:
    """
    Async adapter over app.llm.claude sync functions.

    Satisfies the fix_core.interfaces.LLMProvider Protocol for the methods
    where the signature alignment is sufficient. See module docstring for
    partial-coverage methods.
    """

    # ── Intake ────────────────────────────────────────────────────────────────

    async def intake_classify(
        self,
        description: str,
        vehicle_hint: dict | None = None,
    ) -> IntakeClassification:
        raw = await asyncio.to_thread(_claude.intake_classify, description, vehicle_hint)
        return IntakeClassification(**{
            k: raw.get(k)
            for k in IntakeClassification.model_fields
            if raw.get(k) is not None
        })

    # ── Answer classification ─────────────────────────────────────────────────

    async def classify_answer(
        self,
        question: str,
        options: dict,
        user_answer: str,
        hypotheses: list[HypothesisScore],
    ) -> AnswerClassification:
        """
        Map free-text answer to a tree option key.

        hypotheses is accepted per interface but not forwarded — claude.py
        determines the option match from the question + options alone.
        """
        raw = await asyncio.to_thread(
            _claude.classify_answer, question, options, user_answer
        )
        return AnswerClassification(
            option_key=raw.get("option_key", ""),
            classification_confidence=float(raw.get("classification_confidence", 0.8)),
            answer_reliability=float(raw.get("answer_reliability", 0.8)),
            needs_clarification=bool(raw.get("needs_clarification", False)),
        )

    # ── Question rephrasing ───────────────────────────────────────────────────

    async def rephrase_question(
        self,
        question: str,
        options: dict,
        vehicle_context: VehicleContext,
        turn: int = 0,
        session_mode: str = "consumer",
    ) -> str:
        """
        Rephrase a raw tree question to conversational language.

        options: dict keyed by match_key → {label, ...} OR list[str] of labels.
        vehicle_context: VehicleContext object OR pre-formatted vehicle string.
        turn/session_mode: forwarded to claude.py to calibrate framing.
        """
        if isinstance(options, dict):
            labels = [v["label"] if isinstance(v, dict) else str(v) for v in options.values()]
        else:
            labels = list(options)

        if isinstance(vehicle_context, str):
            vc_str = vehicle_context
        else:
            vc_str = " ".join(filter(None, [
                str(vehicle_context.vehicle_year) if vehicle_context.vehicle_year else "",
                vehicle_context.vehicle_make or "",
                vehicle_context.vehicle_model or "",
                vehicle_context.vehicle_engine or "",
            ])).strip() or "Unknown vehicle"

        return await asyncio.to_thread(
            _claude.rephrase_question,
            question, labels, vc_str,
            turn=turn, session_mode=session_mode,
        )

    # ── Stateless lookups ─────────────────────────────────────────────────────

    async def lookup_obd_code(self, code: str, vehicle_type: str) -> OBDCodeResult:
        """
        Stateless OBD code lookup.

        claude.py returns {code, description, severity, likely_causes,
        next_steps, diy_difficulty}; OBDCodeResult expects {code, description,
        likely_causes, urgency, diy_notes}. Translation applied here.
        """
        raw = await asyncio.to_thread(_claude.lookup_obd_code, code, vehicle_type)
        return OBDCodeResult(
            code=raw.get("code", code),
            description=raw.get("description", ""),
            likely_causes=raw.get("likely_causes", []),
            urgency=raw.get("severity", "moderate"),      # severity → urgency
            diy_notes=raw.get("diy_difficulty"),          # closest field
        )

    async def lookup_he_dtc(
        self,
        code: str,
        manufacturer: str | None,
        equipment_type: str | None,
    ) -> HEDTCResult:
        """
        Stateless heavy equipment fault code lookup.

        claude.py returns {code, manufacturer, description, severity,
        likely_causes, isolation_steps, part_numbers, service_reference};
        HEDTCResult expects {code, manufacturer, description, likely_causes,
        urgency, service_notes}.
        """
        raw = await asyncio.to_thread(
            _claude.lookup_he_dtc,
            code,
            manufacturer or "",
            equipment_type or "",
        )
        return HEDTCResult(
            code=raw.get("code", code),
            manufacturer=raw.get("manufacturer"),
            description=raw.get("description", ""),
            likely_causes=raw.get("likely_causes", []),
            urgency=raw.get("severity", "moderate"),       # severity → urgency
            service_notes=raw.get("service_reference"),   # service_reference → service_notes
        )

    # ── Synthesis ─────────────────────────────────────────────────────────────

    async def synthesize_result(
        self,
        session: DiagnosticSession,
        hypotheses: list[HypothesisScore],
    ) -> SynthesizedResult:
        """
        Produce a structured diagnostic result from scored hypotheses.

        hypotheses may be list[HypothesisScore] or list[Hypothesis] (a superset).
        claude.py accesses h.label, h.score, h.evidence, h.diy_difficulty, h.parts.
        HypothesisScore lacks diy_difficulty and parts — pass scorer.ranked() from
        call sites that have the scorer available to preserve those fields.

        Builds conversation_summary from session.messages (last 8).
        Extracts secondary_symptom from session.context.
        """
        msgs = session.messages[-8:]
        conversation_summary = "\n".join(
            f"{m.role.value}: {m.content}" for m in msgs
        )
        secondary_symptom = (session.context or {}).get("secondary_symptom")

        raw = await asyncio.to_thread(
            _claude.synthesize_result,
            session.symptom_category or "",
            session.vehicle_context,
            hypotheses,
            conversation_summary,
            secondary_symptom,
            session.session_mode.value,
            session.vehicle_type or "",
        )

        return SynthesizedResult(
            ranked_causes=[
                SynthesizedCause(
                    cause=c.get("cause", ""),
                    confidence=float(c.get("confidence", 0.0)),
                    reasoning=c.get("reasoning", ""),
                )
                for c in raw.get("ranked_causes", [])
            ],
            next_checks=raw.get("next_checks", []),
            fault_isolation_steps=raw.get("fault_isolation_steps", []),
            diy_difficulty=raw.get("diy_difficulty"),
            suggested_parts=raw.get("suggested_parts", []),
            escalation_guidance=raw.get("escalation_guidance"),
            confidence_level=raw.get("confidence_level"),
            service_reference=raw.get("service_reference"),
        )

    # ── Follow-up interpretation ──────────────────────────────────────────────

    async def interpret_followup(
        self,
        user_finding: str,
        session: DiagnosticSession,
    ) -> FollowupInterpretation:
        """
        Interpret user findings after initial diagnosis.

        Derives ranked_hypotheses from session.hypotheses (sorted by score desc)
        and next_checks from session.result.next_checks. claude.py only uses
        h.key, h.label, h.score — HypothesisScore satisfies that contract.
        """
        ranked_hyps = sorted(session.hypotheses, key=lambda h: h.score, reverse=True)
        next_checks: list[str] = session.result.next_checks if session.result else []
        raw = await asyncio.to_thread(
            _claude.interpret_followup,
            session.symptom_category or "",
            session.vehicle_context,
            ranked_hyps,
            next_checks,
            user_finding,
        )
        return FollowupInterpretation(
            interpretation=raw.get("interpretation", ""),
            score_deltas=raw.get("score_deltas", {}),
        )

    # ── Image analysis ────────────────────────────────────────────────────────

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

        vehicle_context may be a VehicleContext object or a pre-formatted string
        (consistent with rephrase_question's handling).
        ranked_hypotheses: list of objects with .key, .label, .score — both
        Hypothesis and HypothesisScore satisfy that contract.
        """
        if isinstance(vehicle_context, str):
            vc_str = vehicle_context
        else:
            vc_str = " ".join(filter(None, [
                str(vehicle_context.vehicle_year) if vehicle_context.vehicle_year else "",
                vehicle_context.vehicle_make or "",
                vehicle_context.vehicle_model or "",
                vehicle_context.vehicle_engine or "",
            ])).strip() or "Unknown vehicle"

        raw = await asyncio.to_thread(
            _claude.analyze_image,
            image_data=image_bytes,
            media_type=media_type,
            symptom_category=symptom_category,
            vehicle_context=vc_str,
            ranked_hypotheses=ranked_hypotheses or [],
            confidence_modifier=confidence_modifier,
        )
        return ImageAnalysis(
            interpretation=raw.get("interpretation", ""),
            score_deltas=raw.get("score_deltas", {}),
            confidence_modifier=float(raw.get("confidence_modifier", confidence_modifier)),
            safety_concern=raw.get("safety_concern"),
        )
