"""
Phase 15B tests — Professional result card mode.

Tests:
  - synthesize_result called with session_mode and vehicle_type params
  - Professional prompt triggered for mechanic, operator, HE vehicle types
  - Consumer prompt used for consumer mode with car/truck
  - _format_result_text renders Fault Isolation Steps for professional sessions
  - _format_result_text suppresses DIY difficulty for professional sessions
  - _format_result_text renders Next Checks and DIY for consumer sessions
  - service_reference rendered when present in professional mode
  - DiagnosticResultOut has fault_isolation_steps and service_reference fields
"""
import pytest
from unittest.mock import MagicMock, patch


# ── DiagnosticResultOut schema ────────────────────────────────────────────────

def test_diagnostic_result_out_has_new_fields():
    """DiagnosticResultOut includes fault_isolation_steps and service_reference."""
    from app.api.sessions import DiagnosticResultOut
    import inspect
    fields = DiagnosticResultOut.model_fields
    assert "fault_isolation_steps" in fields, "fault_isolation_steps missing from DiagnosticResultOut"
    assert "service_reference" in fields, "service_reference missing from DiagnosticResultOut"


def test_diagnostic_result_out_defaults():
    """fault_isolation_steps defaults to [] and service_reference to None."""
    from app.api.sessions import DiagnosticResultOut
    out = DiagnosticResultOut(
        ranked_causes=[],
        suggested_parts=[],
        escalation_guidance=None,
        confidence_level=0.5,
    )
    assert out.fault_isolation_steps == []
    assert out.service_reference is None
    assert out.next_checks == []
    assert out.diy_difficulty is None


# ── synthesize_result signature ───────────────────────────────────────────────

def test_synthesize_result_has_mode_params():
    """synthesize_result accepts session_mode and vehicle_type parameters."""
    import inspect
    from app.llm.claude import synthesize_result
    sig = inspect.signature(synthesize_result)
    params = list(sig.parameters.keys())
    assert "session_mode" in params, "session_mode param missing from synthesize_result"
    assert "vehicle_type" in params, "vehicle_type param missing from synthesize_result"


def test_synthesize_result_defaults_to_consumer():
    """synthesize_result defaults to consumer mode."""
    import inspect
    from app.llm.claude import synthesize_result
    sig = inspect.signature(synthesize_result)
    assert sig.parameters["session_mode"].default == "consumer"
    assert sig.parameters["vehicle_type"].default == ""


# ── _format_result_text: consumer mode ───────────────────────────────────────

def _make_result(**kwargs):
    from app.api.sessions import DiagnosticResultOut, RankedCause
    defaults = dict(
        ranked_causes=[RankedCause(cause="Weak battery", confidence=0.82, reasoning="Voltage dropped under load")],
        next_checks=["Check battery voltage under load", "Inspect cable terminals"],
        diy_difficulty="easy",
        suggested_parts=[],
        escalation_guidance=None,
        confidence_level=0.82,
        fault_isolation_steps=[],
        service_reference=None,
    )
    defaults.update(kwargs)
    return DiagnosticResultOut(**defaults)


def test_format_result_consumer_shows_next_checks():
    """Consumer mode renders Next Checks section."""
    from app.api.sessions import _format_result_text
    result = _make_result()
    text = _format_result_text(result, session_mode="consumer", vehicle_type="car")
    assert "**Next Checks:**" in text
    assert "Check battery voltage under load" in text


def test_format_result_consumer_shows_diy_difficulty():
    """Consumer mode renders DIY Difficulty label."""
    from app.api.sessions import _format_result_text
    result = _make_result(diy_difficulty="moderate")
    text = _format_result_text(result, session_mode="consumer", vehicle_type="car")
    assert "DIY Difficulty" in text or "Moderate DIY" in text


def test_format_result_consumer_no_fault_isolation():
    """Consumer mode does NOT render Fault Isolation Steps."""
    from app.api.sessions import _format_result_text
    result = _make_result(fault_isolation_steps=["Step 1"])
    text = _format_result_text(result, session_mode="consumer", vehicle_type="car")
    assert "Fault Isolation Steps" not in text


# ── _format_result_text: professional mode ───────────────────────────────────

@pytest.mark.parametrize("session_mode,vehicle_type", [
    ("mechanic", "car"),
    ("operator", "heavy_equipment"),
    ("consumer", "heavy_equipment"),
    ("consumer", "tractor"),
    ("consumer", "excavator"),
    ("consumer", "loader"),
    ("consumer", "skid_steer"),
    ("mechanic", "tractor"),
])
def test_format_result_professional_shows_fault_isolation(session_mode, vehicle_type):
    """Professional mode renders Fault Isolation Steps."""
    from app.api.sessions import _format_result_text
    result = _make_result(
        next_checks=[],
        diy_difficulty=None,
        fault_isolation_steps=["Check pilot pressure at manifold", "Test solenoid voltage"],
    )
    text = _format_result_text(result, session_mode=session_mode, vehicle_type=vehicle_type)
    assert "**Fault Isolation Steps:**" in text
    assert "Check pilot pressure" in text


def test_format_result_professional_no_diy_label():
    """Professional mode does NOT render DIY Difficulty."""
    from app.api.sessions import _format_result_text
    result = _make_result(diy_difficulty="easy", fault_isolation_steps=["Step 1"])
    text = _format_result_text(result, session_mode="mechanic", vehicle_type="heavy_equipment")
    assert "DIY Difficulty" not in text
    assert "Easy DIY" not in text


def test_format_result_professional_no_next_checks():
    """Professional mode does NOT render Next Checks section."""
    from app.api.sessions import _format_result_text
    result = _make_result(
        next_checks=["Consumer step"],
        fault_isolation_steps=["Tech step"],
    )
    text = _format_result_text(result, session_mode="mechanic", vehicle_type="car")
    assert "**Next Checks:**" not in text
    assert "Consumer step" not in text


def test_format_result_professional_shows_service_reference():
    """Professional mode renders Service Reference when present."""
    from app.api.sessions import _format_result_text
    result = _make_result(
        fault_isolation_steps=["Step 1"],
        service_reference="SEBU8325, Section 8-3",
    )
    text = _format_result_text(result, session_mode="mechanic", vehicle_type="heavy_equipment")
    assert "Service Reference" in text
    assert "SEBU8325" in text


def test_format_result_professional_no_service_reference_if_none():
    """Professional mode omits Service Reference when None."""
    from app.api.sessions import _format_result_text
    result = _make_result(fault_isolation_steps=["Step 1"], service_reference=None)
    text = _format_result_text(result, session_mode="mechanic", vehicle_type="heavy_equipment")
    assert "Service Reference" not in text


def test_format_result_professional_escalation_label():
    """Professional mode uses 'Escalation:' not 'When to see a mechanic:'."""
    from app.api.sessions import _format_result_text
    result = _make_result(
        fault_isolation_steps=["Step 1"],
        escalation_guidance="Refer to dealer for ECU reprogramming",
    )
    text = _format_result_text(result, session_mode="mechanic", vehicle_type="heavy_equipment")
    assert "**Escalation:**" in text
    assert "When to see a mechanic" not in text


# ── _HE_VEHICLE_TYPES constant ────────────────────────────────────────────────

def test_he_vehicle_types_includes_subtypes():
    """_HE_VEHICLE_TYPES_RESULT includes all 5 HE types."""
    from app.api.sessions import _HE_VEHICLE_TYPES_RESULT
    for vt in ("heavy_equipment", "tractor", "excavator", "loader", "skid_steer"):
        assert vt in _HE_VEHICLE_TYPES_RESULT, f"{vt} missing from _HE_VEHICLE_TYPES_RESULT"
