# M4: thin re-export — implementation lives in fix_core
from fix_core.engine.context_heavy import (
    HeavyContext,
    apply_heavy_context_priors,
    heavy_context_from_intake,
    telematics_context_hook,
    maintenance_log_hook,
    _HE_VEHICLE_TYPES,
    _OVERDUE_SERVICE_HOURS,
    _LONG_STORAGE_DAYS,
)

__all__ = [
    "HeavyContext",
    "apply_heavy_context_priors",
    "heavy_context_from_intake",
    "telematics_context_hook",
    "maintenance_log_hook",
]
