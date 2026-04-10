# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.contradictions import Contradiction, detect_contradictions, merge_flags

__all__ = ["Contradiction", "detect_contradictions", "merge_flags"]
