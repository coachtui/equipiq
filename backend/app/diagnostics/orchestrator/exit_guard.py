# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.exit_guard import (
    MIN_NODES,
    MIN_EVIDENCE_TYPES,
    CONTRADICTION_BLOCK_SEVERITY,
    can_exit,
    exit_reason,
    can_exit_from_session,
    exit_reason_from_session,
)

__all__ = [
    "MIN_NODES",
    "MIN_EVIDENCE_TYPES",
    "CONTRADICTION_BLOCK_SEVERITY",
    "can_exit",
    "exit_reason",
    "can_exit_from_session",
    "exit_reason_from_session",
]
