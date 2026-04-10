# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.evidence import (
    EvidencePacket,
    scale_affects,
    build_from_classification,
    build_from_image,
    build_from_followup,
    build_from_operator_observation,
    build_from_manual_check,
    build_sensor_placeholder,
    build_intake_packet,
    evidence_type_count,
)

__all__ = [
    "EvidencePacket",
    "scale_affects",
    "build_from_classification",
    "build_from_image",
    "build_from_followup",
    "build_from_operator_observation",
    "build_from_manual_check",
    "build_sensor_placeholder",
    "build_intake_packet",
    "evidence_type_count",
]
