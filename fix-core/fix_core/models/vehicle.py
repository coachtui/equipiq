from __future__ import annotations

from pydantic import BaseModel

VEHICLE_TYPES: list[str] = [
    "car",
    "truck",
    "motorcycle",
    "boat",
    "generator",
    "atv",
    "pwc",
    "rv",
    "heavy_equipment",
    "tractor",
    "excavator",
    "loader",
    "skid_steer",
    "other",
]


class VehicleContext(BaseModel):
    """Basic vehicle identity fields extracted at intake."""

    vehicle_type: str
    vehicle_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_engine: str | None = None


class HeavyEquipmentContext(BaseModel):
    """
    Extended context for heavy equipment sessions (Phase 11+).
    Carried in DiagnosticSession.heavy_context when session_mode == "operator".
    """

    equipment_type: str | None = None        # "excavator", "dozer", "loader", etc.
    manufacturer: str | None = None
    model_number: str | None = None
    service_hours: int | None = None
    operator_name: str | None = None
    jobsite_location: str | None = None
    fault_codes: list[str] = []
    last_service_date: str | None = None
    hydraulic_system: str | None = None
    engine_manufacturer: str | None = None
