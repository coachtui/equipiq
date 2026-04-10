"""
Telematics sensor normalization — pure EvidencePacket construction from sensor data.

Converts raw machine sensor readings into normalized EvidencePackets and
SafetyAlerts.  All logic is deterministic and pure Python — no DB, no LLM.

Architecture:
  1. Validate — reject obviously bad payloads (negative temp, impossible voltage)
  2. Normalize — map raw values to named signals (elevated_temp, low_voltage, …)
  3. Convert — produce EvidencePackets with source="sensor_future"
  4. Safety   — evaluate numeric thresholds → SafetyAlert objects (no LLM)
  5. Inspect  — helpers for admin/debug visibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from fix_core.orchestrator.evidence import EvidencePacket
from fix_core.orchestrator.safety import SafetyAlert


# ── Normalization thresholds ──────────────────────────────────────────────────
# All numeric thresholds are documented with units.

# Engine temperature (Celsius)
TEMP_WARNING_C: float  = 95.0    # above this → elevated_temp signal (warning)
TEMP_CRITICAL_C: float = 105.0   # above this → safety alert (critical)

# System voltage (Volts — designed for 12V base; 24V systems scale ×2)
VOLTAGE_WARNING_V: float  = 11.5   # below this → low_voltage signal (warning)
VOLTAGE_CRITICAL_V: float = 10.0   # below this → safety alert (critical)

# Hydraulic / system pressure (PSI)
PRESSURE_WARNING_PSI: float  = 1500.0  # below this → pressure_abnormal (warning)
PRESSURE_CRITICAL_PSI: float = 500.0   # below this → safety alert (critical)

# Fuel level (%)
FUEL_WARNING_PCT: float = 10.0         # below this → low_fuel signal


# ── Cross-tree affects map ────────────────────────────────────────────────────
# Maps normalized signal key → hypothesis key deltas.
# Keys that don't exist in the active session's tree are silently ignored
# by HypothesisScorer — safe to include generic cross-tree keys here.

_SIGNAL_AFFECTS: dict[str, dict[str, float]] = {
    "elevated_temp": {
        "blocked_cooler_screen": 0.15,
        "thermostat_failure":    0.15,
        "water_pump_failure":    0.10,
        "low_coolant":           0.10,
    },
    "critical_overheat": {
        "blocked_cooler_screen": 0.25,
        "thermostat_failure":    0.20,
        "water_pump_failure":    0.20,
        "low_coolant":           0.15,
        "sustained_overload":    0.15,
    },
    "low_voltage": {
        "battery_failure":   0.20,
        "alternator_failure": 0.15,
        "ground_fault":      0.10,
        "parasitic_drain":   0.10,
    },
    "critical_low_voltage": {
        "battery_failure":   0.35,
        "alternator_failure": 0.20,
        "ground_fault":      0.15,
    },
    "pressure_abnormal": {
        "failed_hydraulic_pump": 0.20,
        "low_fluid":             0.15,
        "clogged_filter":        0.10,
        "relief_valve_stuck_open": 0.10,
    },
    "critical_low_pressure": {
        "failed_hydraulic_pump": 0.35,
        "low_fluid":             0.25,
        "leaking_hose_fitting":  0.20,
    },
    "low_fuel": {
        "fuel_delivery":    0.20,
        "fuel_restriction": 0.15,
    },
    "fault_present": {},  # generic; set by fault code classification if available
}


# ── Validation result ─────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


# ── Normalized signal ─────────────────────────────────────────────────────────

NormalizedSignal = Literal[
    "elevated_temp",
    "critical_overheat",
    "low_voltage",
    "critical_low_voltage",
    "pressure_abnormal",
    "critical_low_pressure",
    "low_fuel",
    "fault_present",
]


# ── Telemetry payload ─────────────────────────────────────────────────────────

@dataclass
class TelemetryPayload:
    """Validated inbound telemetry from a field asset."""
    asset_id: str
    timestamp: datetime
    engine_temp_c: float | None = None
    voltage_v: float | None = None
    pressure_psi: float | None = None
    fuel_level_pct: float | None = None
    fault_codes: list[str] = field(default_factory=list)
    session_id: str | None = None   # optional explicit session linkage


# ── Normalization result ──────────────────────────────────────────────────────

@dataclass
class NormalizationResult:
    """Output of the full normalization pipeline for one telemetry payload."""
    asset_id: str
    timestamp: datetime
    normalized_signals: list[EvidencePacket]
    safety_alerts: list[SafetyAlert]
    raw: dict                          # original sensor values for inspection
    signal_names: list[str]            # human-readable list of what fired


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_payload(data: dict) -> ValidationResult:
    """
    Validate a raw telemetry payload dict before processing.

    Checks:
    - asset_id present and non-empty
    - timestamp parseable
    - numeric fields within physically plausible ranges
    - fault_codes is a list of strings
    """
    errors: list[str] = []

    if not data.get("asset_id") or not str(data["asset_id"]).strip():
        errors.append("asset_id is required and must be non-empty")

    ts = data.get("timestamp")
    if ts is None:
        errors.append("timestamp is required")
    else:
        try:
            if not isinstance(ts, datetime):
                datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            errors.append(f"timestamp '{ts}' is not a valid ISO-8601 datetime")

    _check_range(data, "engine_temp_c", -50.0, 300.0, "°C", errors)
    _check_range(data, "voltage_v", 0.0, 60.0, "V", errors)
    _check_range(data, "pressure_psi", 0.0, 10000.0, "PSI", errors)
    _check_range(data, "fuel_level_pct", 0.0, 100.0, "%", errors)

    fc = data.get("fault_codes")
    if fc is not None:
        if not isinstance(fc, list):
            errors.append("fault_codes must be a list")
        elif not all(isinstance(c, str) for c in fc):
            errors.append("fault_codes must contain only strings")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def _check_range(
    data: dict,
    key: str,
    lo: float,
    hi: float,
    unit: str,
    errors: list[str],
) -> None:
    val = data.get(key)
    if val is None:
        return
    try:
        fval = float(val)
    except (TypeError, ValueError):
        errors.append(f"{key} must be a number")
        return
    if not (lo <= fval <= hi):
        errors.append(f"{key} value {fval} is outside plausible range [{lo}, {hi}] {unit}")


# ─────────────────────────────────────────────────────────────────────────────
# Normalization — raw → named signals
# ─────────────────────────────────────────────────────────────────────────────

def normalize_telemetry(payload: TelemetryPayload) -> NormalizationResult:
    """
    Convert a validated TelemetryPayload into normalized EvidencePackets
    and SafetyAlerts.
    """
    packets: list[EvidencePacket] = []
    alerts: list[SafetyAlert] = []
    signal_names: list[str] = []

    raw = {
        "engine_temp_c":   payload.engine_temp_c,
        "voltage_v":       payload.voltage_v,
        "pressure_psi":    payload.pressure_psi,
        "fuel_level_pct":  payload.fuel_level_pct,
        "fault_codes":     payload.fault_codes,
    }

    # ── Engine temperature ────────────────────────────────────────────────────
    if payload.engine_temp_c is not None:
        temp = payload.engine_temp_c
        if temp >= TEMP_CRITICAL_C:
            signal_names.append("critical_overheat")
            packets.append(_make_packet(
                signal="critical_overheat",
                observation=f"Engine temperature critical: {temp:.1f}°C (threshold: {TEMP_CRITICAL_C}°C)",
                certainty=1.0,
            ))
            alerts.append(SafetyAlert(
                level="critical",
                message="Equipment shut down due to overtemperature.",
                recommended_action=(
                    "Allow the engine to cool before inspecting. "
                    "Do NOT open the radiator cap — cooling system is pressurized. "
                    "Wait at least 30 minutes. Check cooler screens and coolant level when cold. "
                    "Do not operate until the cause is identified."
                ),
            ))
        elif temp >= TEMP_WARNING_C:
            signal_names.append("elevated_temp")
            packets.append(_make_packet(
                signal="elevated_temp",
                observation=f"Engine temperature elevated: {temp:.1f}°C (threshold: {TEMP_WARNING_C}°C)",
                certainty=0.85,
            ))

    # ── Voltage ───────────────────────────────────────────────────────────────
    if payload.voltage_v is not None:
        volts = payload.voltage_v
        if volts < VOLTAGE_CRITICAL_V:
            signal_names.append("critical_low_voltage")
            packets.append(_make_packet(
                signal="critical_low_voltage",
                observation=f"System voltage critically low: {volts:.2f}V (threshold: {VOLTAGE_CRITICAL_V}V)",
                certainty=1.0,
            ))
            alerts.append(SafetyAlert(
                level="critical",
                message="Critical battery or electrical system failure detected.",
                recommended_action=(
                    "Shut down the machine. Inspect battery terminals, main fuses, and ground connections. "
                    "Do not attempt to restart — severe voltage drop can damage ECU and safety systems. "
                    "Charge or replace battery; test alternator output before restarting."
                ),
            ))
        elif volts < VOLTAGE_WARNING_V:
            signal_names.append("low_voltage")
            packets.append(_make_packet(
                signal="low_voltage",
                observation=f"System voltage low: {volts:.2f}V (threshold: {VOLTAGE_WARNING_V}V)",
                certainty=0.80,
            ))

    # ── Pressure ──────────────────────────────────────────────────────────────
    if payload.pressure_psi is not None:
        psi = payload.pressure_psi
        if psi < PRESSURE_CRITICAL_PSI:
            signal_names.append("critical_low_pressure")
            packets.append(_make_packet(
                signal="critical_low_pressure",
                observation=f"Hydraulic pressure critically low: {psi:.0f} PSI (threshold: {PRESSURE_CRITICAL_PSI} PSI)",
                certainty=1.0,
            ))
            alerts.append(SafetyAlert(
                level="critical",
                message="Hydraulic system critical pressure loss detected.",
                recommended_action=(
                    "STOP machine and lower all implements to the ground immediately. "
                    "Do not attempt hydraulic operations — loss of control is possible at this pressure. "
                    "Check fluid level, inspect for visible leaks, and call for service."
                ),
            ))
        elif psi < PRESSURE_WARNING_PSI:
            signal_names.append("pressure_abnormal")
            packets.append(_make_packet(
                signal="pressure_abnormal",
                observation=f"Hydraulic pressure abnormal: {psi:.0f} PSI (normal ≥ {PRESSURE_WARNING_PSI} PSI)",
                certainty=0.80,
            ))

    # ── Fuel level ────────────────────────────────────────────────────────────
    if payload.fuel_level_pct is not None:
        fuel = payload.fuel_level_pct
        if fuel < FUEL_WARNING_PCT:
            signal_names.append("low_fuel")
            packets.append(_make_packet(
                signal="low_fuel",
                observation=f"Fuel level low: {fuel:.1f}% (threshold: {FUEL_WARNING_PCT}%)",
                certainty=0.90,
            ))

    # ── Fault codes ───────────────────────────────────────────────────────────
    if payload.fault_codes:
        signal_names.append("fault_present")
        code_str = ", ".join(payload.fault_codes[:10])
        packets.append(_make_packet(
            signal="fault_present",
            observation=f"Fault codes present: {code_str}",
            certainty=0.95,
        ))

    alerts.sort(key=lambda a: 0 if a.level == "critical" else 1)

    return NormalizationResult(
        asset_id=payload.asset_id,
        timestamp=payload.timestamp,
        normalized_signals=packets,
        safety_alerts=alerts,
        raw=raw,
        signal_names=signal_names,
    )


def _make_packet(signal: str, observation: str, certainty: float) -> EvidencePacket:
    """Build an EvidencePacket for a normalized telemetry signal."""
    return EvidencePacket(
        source="sensor_future",
        observation=observation[:200],
        normalized_key=signal,
        certainty=certainty,
        affects=dict(_SIGNAL_AFFECTS.get(signal, {})),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Payload parsing helper
# ─────────────────────────────────────────────────────────────────────────────

def parse_payload(data: dict) -> TelemetryPayload:
    """
    Parse a validated raw dict into a TelemetryPayload.

    Assumes validate_payload() has already returned valid=True.
    """
    ts_raw = data["timestamp"]
    if isinstance(ts_raw, datetime):
        ts = ts_raw
    else:
        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return TelemetryPayload(
        asset_id=str(data["asset_id"]).strip(),
        timestamp=ts,
        engine_temp_c=float(data["engine_temp_c"]) if data.get("engine_temp_c") is not None else None,
        voltage_v=float(data["voltage_v"]) if data.get("voltage_v") is not None else None,
        pressure_psi=float(data["pressure_psi"]) if data.get("pressure_psi") is not None else None,
        fuel_level_pct=float(data["fuel_level_pct"]) if data.get("fuel_level_pct") is not None else None,
        fault_codes=[str(c) for c in data.get("fault_codes") or []],
        session_id=str(data["session_id"]) if data.get("session_id") else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inspection helpers (admin/debug visibility)
# ─────────────────────────────────────────────────────────────────────────────

def describe_normalization(result: NormalizationResult) -> dict:
    """
    Return a structured description of a normalization result for admin/debug display.
    """
    return {
        "asset_id":      result.asset_id,
        "timestamp":     result.timestamp.isoformat(),
        "signal_names":  result.signal_names,
        "raw":           result.raw,
        "evidence_packets": [
            {
                "normalized_key": p.normalized_key,
                "source":         p.source,
                "observation":    p.observation,
                "certainty":      p.certainty,
                "affects_count":  len(p.affects),
                "affects":        p.affects,
            }
            for p in result.normalized_signals
        ],
        "safety_alerts": [
            {
                "level":              a.level,
                "message":            a.message,
                "recommended_action": a.recommended_action,
            }
            for a in result.safety_alerts
        ],
        "has_critical": any(a.level == "critical" for a in result.safety_alerts),
    }


__all__ = [
    "TEMP_WARNING_C",
    "TEMP_CRITICAL_C",
    "VOLTAGE_WARNING_V",
    "VOLTAGE_CRITICAL_V",
    "PRESSURE_WARNING_PSI",
    "PRESSURE_CRITICAL_PSI",
    "FUEL_WARNING_PCT",
    "_SIGNAL_AFFECTS",
    "ValidationResult",
    "NormalizedSignal",
    "TelemetryPayload",
    "NormalizationResult",
    "validate_payload",
    "normalize_telemetry",
    "parse_payload",
    "describe_normalization",
]
