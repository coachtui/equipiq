# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.safety import SafetyAlert, evaluate_safety, has_critical_alert

__all__ = ["SafetyAlert", "evaluate_safety", "has_critical_alert"]
