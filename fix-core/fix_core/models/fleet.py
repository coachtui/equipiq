from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from fix_core.models.context import OwnerContext


class FleetAsset(BaseModel):
    """A single fleet asset (vehicle or equipment) tracked by an operator."""

    id: str
    name: str
    asset_type: str          # maps to a VEHICLE_TYPES value
    owner: OwnerContext
    created_at: datetime
    metadata: dict = {}      # adapter-populated fields (serial number, location, etc.)


class FleetRiskScore(BaseModel):
    """
    Output of the fleet risk model for a single asset.

    Field names mirror fix_core.fleet.AssetRisk so the two types are
    structurally interchangeable.  Use AssetRisk for in-process computation;
    FleetRiskScore when persisting or returning from an API endpoint.
    """

    asset_id: str
    risk_score: float              # 0.0 (low risk) – 1.0 (critical)
    risk_level: str                # low | medium | high | critical
    contributing_factors: list[str] = []   # up to 5, ordered by weighted impact
    recommended_action: str = ""
    component_scores: dict[str, float] = {}  # {factor_name: weighted_contribution}
    computed_at: datetime | None = None      # set when persisted; None for in-flight
