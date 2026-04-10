"""
Heavy Equipment Context — Phase 11.

Provides the HeavyContext dataclass for capturing jobsite and operational context
from the intake form, and apply_heavy_context_priors() which translates that
context into hypothesis prior adjustments before tree traversal begins.

This module is the heavy-equipment analogue of the climate/mileage context priors
used for passenger vehicles.  Instead of odometer-based bands, heavy equipment
uses hours of operation, service intervals, environment type, and storage duration
as the primary context signals.

Usage (called from the API layer during session creation):
    ctx = HeavyContext(
        hours_of_operation=4500,
        last_service_hours=4200,
        environment="dusty",
        storage_duration=0,
        recent_work_type="earthmoving",
    )
    priors = apply_heavy_context_priors(ctx, tree_key="hydraulic_loss_heavy_equipment")
    # Returns dict of {hypothesis_key: delta} to fold into intake evidence packet
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fix_core.trees import CONTEXT_PRIORS


@dataclass
class HeavyContext:
    """Operational and environmental context for a heavy equipment session."""
    hours_of_operation: int              # total machine hours on hourmeter
    last_service_hours: int              # hourmeter reading at last PM service (0 if unknown)
    environment: Literal["dusty", "muddy", "marine", "urban"] = "urban"
    storage_duration: int = 0            # days since last operation (0 = in active use)
    recent_work_type: str = ""           # freeform: "earthmoving", "lifting", "demolition", etc.


# ── Hours-band thresholds ─────────────────────────────────────────────────────
_OVERDUE_SERVICE_HOURS: int = 250   # PM overdue if hours_of_operation > last_service + this
_LONG_STORAGE_DAYS: int = 30        # storage_duration above this triggers long-storage priors


def apply_heavy_context_priors(
    ctx: HeavyContext,
    tree_key: str,
) -> dict[str, float]:
    """
    Return a dict of {hypothesis_key: delta} adjustments derived from HeavyContext.

    These are applied as an intake evidence packet before tree traversal, giving
    the scorer a prior head start based on known operational context.

    The adjustments come from the tree's CONTEXT_PRIORS["environment"] and
    CONTEXT_PRIORS["hours_band"] sections.

    Args:
        ctx:      HeavyContext populated from intake form.
        tree_key: The resolved tree key (e.g. "hydraulic_loss_heavy_equipment").

    Returns:
        Merged dict of hypothesis deltas.  Empty dict if no applicable priors.
    """
    tree_priors = CONTEXT_PRIORS.get(tree_key, {})
    deltas: dict[str, float] = {}

    def _merge(additions: dict[str, float]) -> None:
        for k, v in additions.items():
            deltas[k] = round(deltas.get(k, 0.0) + v, 4)

    # ── Environment priors ────────────────────────────────────────────────────
    env_priors = tree_priors.get("environment", {})
    env_adjustments = env_priors.get(ctx.environment, {})
    _merge(env_adjustments)

    # ── Hours-band priors ─────────────────────────────────────────────────────
    hours_priors = tree_priors.get("hours_band", {})

    # Overdue service band
    hours_since_service = ctx.hours_of_operation - ctx.last_service_hours
    if ctx.last_service_hours > 0 and hours_since_service >= _OVERDUE_SERVICE_HOURS:
        overdue_adjustments = hours_priors.get("overdue_service", {})
        _merge(overdue_adjustments)

    # Long storage band
    if ctx.storage_duration >= _LONG_STORAGE_DAYS:
        storage_adjustments = hours_priors.get("long_storage", {})
        _merge(storage_adjustments)

    # ── Climate fallback (shared with passenger vehicle priors) ───────────────
    # Some heavy equipment trees inherit climate priors from the standard priors
    # structure.  These are not yet populated from HeavyContext but are left
    # here as a hook for when ambient temperature data becomes available.
    # (climate will come from sensor_future / telematics in a later phase)

    return deltas


# All vehicle_type values that are treated as heavy equipment for context purposes.
_HE_VEHICLE_TYPES: frozenset[str] = frozenset({
    "heavy_equipment",
    "excavator",
    "tractor",
    "loader",
    "skid_steer",
    "dozer",
    "crane",
    "grader",
    "compactor",
})


def heavy_context_from_intake(intake_data: dict) -> HeavyContext | None:
    """
    Build a HeavyContext from intake_data if the session is a heavy_equipment type.
    Returns None if the session is not heavy equipment or context data is absent.

    Handles all HE subtypes (excavator, tractor, loader, skid_steer, dozer, crane,
    grader, compactor) in addition to the base "heavy_equipment" value.

    Called by the API layer (sessions.py) during session initialisation so that
    apply_heavy_context_priors() can be folded into the intake evidence packet.
    """
    if intake_data.get("vehicle_type") not in _HE_VEHICLE_TYPES:
        return None

    ctx_raw = intake_data.get("heavy_context") or {}
    return HeavyContext(
        hours_of_operation=int(ctx_raw.get("hours_of_operation", 0)),
        last_service_hours=int(ctx_raw.get("last_service_hours", 0)),
        environment=ctx_raw.get("environment", "urban"),
        storage_duration=int(ctx_raw.get("storage_duration", 0)),
        recent_work_type=str(ctx_raw.get("recent_work_type", "")),
    )


# ── Future telematics hook (Phase 11 stub) ────────────────────────────────────

def telematics_context_hook(
    machine_id: str | None = None,
    telematics_payload: dict | None = None,
) -> HeavyContext | None:
    """
    Future hook for telematics and sensor feed integration.

    When machine telematics data becomes available (fleet management systems,
    OEM APIs, IoT sensor feeds), this function will translate that data into
    a HeavyContext.  Currently a no-op stub that returns None.

    Args:
        machine_id:          Identifier for the specific machine in the fleet.
        telematics_payload:  Raw data from the telematics provider.

    Returns:
        HeavyContext populated from telematics, or None if not yet implemented.
    """
    # TODO Phase 12+: integrate with telematics provider API
    # Planned sources: JD Link, Cat Product Link, Komatsu KOMTRAX, CNH FleetForce
    return None


def maintenance_log_hook(
    machine_id: str | None = None,
    maintenance_records: list[dict] | None = None,
) -> dict[str, int]:
    """
    Future hook for maintenance log integration.

    When maintenance records are available, this function will return
    {last_service_hours, recommended_next_service_hours} for use in
    HeavyContext construction.  Currently a no-op stub.

    Args:
        machine_id:          Identifier for the specific machine.
        maintenance_records: List of maintenance record dicts from fleet system.

    Returns:
        Dict with last_service_hours and hours_since_service keys, or empty dict.
    """
    # TODO Phase 12+: integrate with fleet maintenance log APIs
    return {}
