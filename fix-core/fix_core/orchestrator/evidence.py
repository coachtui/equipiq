"""
Evidence Engine — standardizes all diagnostic inputs into structured evidence packets.

Every input that affects hypothesis scores (Q&A answers, image analysis, OBD codes,
follow-up findings) is wrapped in an EvidencePacket before being applied.  The packet
is stored in the session's evidence_log JSONB column so the orchestrator can reason
across all collected evidence.
"""
from __future__ import annotations

# EvidencePacket is the Pydantic model from fix_core.models.evidence.
# It is the single canonical representation — no dataclass duplicate here.
from fix_core.models.evidence import EvidencePacket  # noqa: F401  (re-exported)


def scale_affects(packet: EvidencePacket) -> dict[str, float]:
    """Return score deltas scaled by the packet's certainty."""
    return {k: round(v * packet.certainty, 4) for k, v in packet.affects.items()}


def build_from_classification(
    *,
    option_key: str,
    option_label: str,
    deltas: dict[str, float],
    answer_reliability: float,
    user_text: str,
) -> EvidencePacket:
    """Build an EvidencePacket from a classified Q&A answer."""
    return EvidencePacket(
        source="user_text",
        observation=user_text[:200],
        normalized_key=option_key,
        certainty=answer_reliability,
        affects=deltas,
    )


def build_from_image(
    *,
    interpretation: str,
    score_deltas: dict[str, float],
    confidence_modifier: float,
) -> EvidencePacket:
    """Build an EvidencePacket from an image/video analysis result."""
    return EvidencePacket(
        source="image",
        observation=interpretation[:200],
        normalized_key="image_analysis",
        certainty=confidence_modifier,
        affects=score_deltas,
    )


def build_from_followup(
    *,
    interpretation: str,
    score_deltas: dict[str, float],
    user_text: str,
) -> EvidencePacket:
    """Build an EvidencePacket from a follow-up finding."""
    return EvidencePacket(
        source="manual_test",
        observation=user_text[:200],
        normalized_key="followup_finding",
        certainty=0.85,  # manual tests are fairly reliable
        affects=score_deltas,
    )


def build_from_operator_observation(
    *,
    observation: str,
    normalized_key: str,
    score_deltas: dict[str, float],
    certainty: float = 0.80,
) -> EvidencePacket:
    """
    Build an EvidencePacket from an operator physical observation (Phase 11).

    Operator observations (e.g., "fluid on ground", "smoke color", "screen clogged")
    are treated with slightly lower certainty than a mechanic's manual test but higher
    than free-text user input, because they are prompted physical checks.
    """
    return EvidencePacket(
        source="operator_observation",
        observation=observation[:200],
        normalized_key=normalized_key,
        certainty=certainty,
        affects=score_deltas,
    )


def build_from_manual_check(
    *,
    check_description: str,
    normalized_key: str,
    score_deltas: dict[str, float],
    certainty: float = 0.90,
) -> EvidencePacket:
    """
    Build an EvidencePacket from a deliberate manual test (Phase 11).

    Manual checks (e.g., voltage measurement, pressure test, filter inspection)
    are high-reliability evidence — treated similarly to manual_test but explicitly
    labelled for operator-guided workflows.
    """
    return EvidencePacket(
        source="manual_check",
        observation=check_description[:200],
        normalized_key=normalized_key,
        certainty=certainty,
        affects=score_deltas,
    )


def build_sensor_placeholder(
    *,
    sensor_type: str,
    raw_value: str,
    normalized_key: str,
) -> EvidencePacket:
    """
    Build a placeholder EvidencePacket for future sensor/telematics data (Phase 11).

    This stub preserves the evidence log slot so that future sensor integration
    can populate it with real deltas.  Certainty is 0.0 until real sensor data
    is available — effectively a no-op on hypothesis scoring.
    """
    return EvidencePacket(
        source="sensor_future",
        observation=f"[sensor:{sensor_type}] raw={raw_value}",
        normalized_key=normalized_key,
        certainty=0.0,
        affects={},
    )


def build_intake_packet(description: str, context_priors_applied: dict[str, float]) -> EvidencePacket:
    """Build the initial evidence packet from intake classification."""
    return EvidencePacket(
        source="intake",
        observation=description[:200],
        normalized_key="intake_description",
        certainty=1.0,
        affects=context_priors_applied,
    )


def evidence_type_count(evidence_log: list[dict]) -> int:
    """Count distinct evidence source types in the log."""
    return len({e.get("source") for e in evidence_log})
