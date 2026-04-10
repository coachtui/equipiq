from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

SafetySeverity = Literal["warning", "critical"]


class SafetyAlert(BaseModel):
    """
    Safety interruption fired when dangerous conditions are detected.

    critical — stop immediately; session flow is interrupted; user must acknowledge.
    warning  — proceed with caution; displayed prominently but does not block flow.

    Mirrors the dataclass in backend/app/diagnostics/orchestrator/safety.py.
    """

    level: SafetySeverity
    message: str
    recommended_action: str

    def to_dict(self) -> dict:
        return self.model_dump()
