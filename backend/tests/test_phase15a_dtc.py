"""
Phase 15A tests — Heavy Equipment DTC Lookup endpoint.

Tests:
  - Valid HE fault codes: CAT, Deere, Komatsu, Kubota formats
  - Invalid/empty codes rejected with 400
  - Response structure matches HEDTCLookupResponse (no diy_difficulty)
  - Rate limit config exists
  - Router registered in main app
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

MOCK_DTC_RESULT = {
    "code": "E030",
    "manufacturer": "CAT",
    "description": "Engine over-temperature fault — coolant temperature exceeded threshold.",
    "severity": "high",
    "likely_causes": [
        "Low coolant level",
        "Failed water pump",
        "Clogged radiator core",
    ],
    "isolation_steps": [
        "Check coolant level in expansion tank",
        "Inspect radiator for debris blockage",
        "Test water pump flow with pressure gauge",
    ],
    "part_numbers": ["Coolant (OEM spec)", "Water pump assembly"],
    "service_reference": "CAT SEBU8325, Section 8-3",
}


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


# ── Router registration ───────────────────────────────────────────────────────

def test_dtc_router_registered(client):
    """DTC router is registered — endpoint responds (not 404)."""
    with patch("app.api.dtc.lookup_he_dtc", return_value=MOCK_DTC_RESULT):
        res = client.post("/api/dtc/lookup", json={"code": "E030", "manufacturer": "CAT"})
    assert res.status_code != 404, "DTC router not registered in main.py"


# ── Valid codes ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code,manufacturer", [
    ("E030", "CAT"),
    ("523778.09", "Deere"),
    ("CA390", "Komatsu"),
    ("E2-01", "Kubota"),
    ("ACM 1234.31", "Volvo"),
])
def test_valid_dtc_codes(client, code, manufacturer):
    """Valid HE fault codes return 200 with correct structure."""
    with patch("app.api.dtc.lookup_he_dtc", return_value={**MOCK_DTC_RESULT, "code": code, "manufacturer": manufacturer}):
        res = client.post("/api/dtc/lookup", json={"code": code, "manufacturer": manufacturer})
    assert res.status_code == 200
    data = res.json()
    # Required fields
    assert "code" in data
    assert "manufacturer" in data
    assert "description" in data
    assert "severity" in data
    assert "likely_causes" in data
    assert "isolation_steps" in data
    assert "part_numbers" in data
    # Must NOT have diy_difficulty
    assert "diy_difficulty" not in data, "HE DTC response must not include diy_difficulty"


def test_dtc_with_equipment_context(client):
    """Equipment context is passed to LLM function."""
    with patch("app.api.dtc.lookup_he_dtc") as mock_fn:
        mock_fn.return_value = MOCK_DTC_RESULT
        res = client.post("/api/dtc/lookup", json={
            "code": "E030",
            "manufacturer": "CAT",
            "equipment": {"model": "336 GC", "hours": 4500, "engine": "C9.3"},
        })
    assert res.status_code == 200
    # Verify LLM was called with equipment context string
    call_args = mock_fn.call_args
    equipment_context = call_args[0][2]  # third positional arg
    assert "336 GC" in equipment_context or "4500" in equipment_context


# ── Invalid codes ─────────────────────────────────────────────────────────────

def test_empty_code_rejected(client):
    """Empty code string returns 400."""
    res = client.post("/api/dtc/lookup", json={"code": "", "manufacturer": "CAT"})
    assert res.status_code == 400


def test_empty_manufacturer_rejected(client):
    """Empty manufacturer string returns 400."""
    res = client.post("/api/dtc/lookup", json={"code": "E030", "manufacturer": ""})
    assert res.status_code == 400


def test_whitespace_code_rejected(client):
    """Whitespace-only code returns 400."""
    res = client.post("/api/dtc/lookup", json={"code": "   ", "manufacturer": "CAT"})
    assert res.status_code == 400


# ── Severity values ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("severity", ["low", "moderate", "high", "critical"])
def test_valid_severity_values(client, severity):
    """All four severity values are accepted in the response."""
    with patch("app.api.dtc.lookup_he_dtc", return_value={**MOCK_DTC_RESULT, "severity": severity}):
        res = client.post("/api/dtc/lookup", json={"code": "E030", "manufacturer": "CAT"})
    assert res.status_code == 200
    assert res.json()["severity"] == severity


# ── Config ────────────────────────────────────────────────────────────────────

def test_rate_limit_config_exists():
    """rate_limit_dtc_lookup is defined in Settings."""
    from app.core.config import settings
    assert hasattr(settings, "rate_limit_dtc_lookup"), "rate_limit_dtc_lookup missing from config"
    assert settings.rate_limit_dtc_lookup, "rate_limit_dtc_lookup is empty"


# ── LLM function ─────────────────────────────────────────────────────────────

def test_lookup_he_dtc_function_exists():
    """lookup_he_dtc is importable from app.llm.claude."""
    from app.llm.claude import lookup_he_dtc
    assert callable(lookup_he_dtc)


def test_lookup_he_dtc_signature():
    """lookup_he_dtc accepts code, manufacturer, equipment_context."""
    import inspect
    from app.llm.claude import lookup_he_dtc
    sig = inspect.signature(lookup_he_dtc)
    params = list(sig.parameters.keys())
    assert "code" in params
    assert "manufacturer" in params
    assert "equipment_context" in params


# ── Service reference is optional ────────────────────────────────────────────

def test_service_reference_can_be_null(client):
    """service_reference field can be null in response."""
    result = {**MOCK_DTC_RESULT, "service_reference": None}
    with patch("app.api.dtc.lookup_he_dtc", return_value=result):
        res = client.post("/api/dtc/lookup", json={"code": "E030", "manufacturer": "CAT"})
    assert res.status_code == 200
    assert res.json()["service_reference"] is None
