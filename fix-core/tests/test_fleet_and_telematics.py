"""
Phase M2 unit tests — fix_core.fleet and fix_core.telematics
"""
from datetime import datetime, timezone

import pytest

from fix_core.fleet.risk_model import (
    AssetRisk,
    compute_asset_risk,
    rank_assets_by_risk,
    WEIGHTS,
)
from fix_core.telematics.ingestor import (
    TelemetryPayload,
    normalize_telemetry,
    validate_payload,
    parse_payload,
    TEMP_CRITICAL_C,
    VOLTAGE_CRITICAL_V,
)


# ── Fleet Risk Model ──────────────────────────────────────────────────────────

class TestFleetRiskModel:
    def _base_session(self, **kwargs) -> dict:
        return {
            "session_id": "s1",
            "status": "completed",
            "symptom_category": "hydraulic_loss",
            "context": {},
            "heavy_context": {},
            "was_resolved": True,
            "safety_triggered": False,
            "contradiction_count": 0,
            "top_hypothesis": None,
            **kwargs,
        }

    def test_zero_risk_for_empty_inputs(self):
        result = compute_asset_risk("asset1", sessions=[], telemetry=[])
        assert result.risk_score == pytest.approx(0.0)
        assert result.risk_level == "low"

    def test_unresolved_session_raises_score(self):
        sessions = [self._base_session(status="active", was_resolved=None)]
        result = compute_asset_risk("asset1", sessions=sessions, telemetry=[])
        assert result.risk_score > 0.0

    def test_safety_triggered_raises_score(self):
        sessions = [self._base_session(safety_triggered=True)]
        result = compute_asset_risk("asset1", sessions=sessions, telemetry=[])
        assert result.component_scores["safety"] > 0.0

    def test_score_clamped_to_one(self):
        # Worst possible inputs
        sessions = [
            self._base_session(
                status="active",
                was_resolved=False,
                safety_triggered=True,
                contradiction_count=10,
            )
            for _ in range(10)
        ]
        result = compute_asset_risk("asset1", sessions=sessions, telemetry=[])
        assert result.risk_score <= 1.0

    def test_risk_level_thresholds(self):
        low_result = compute_asset_risk("a", [], [])
        assert low_result.risk_level == "low"

    def test_service_overdue_included_in_score(self):
        sessions = [self._base_session(heavy_context={
            "hours_of_operation": 600,
            "last_service_hours": 100,  # 500h gap > 250h interval
        })]
        result = compute_asset_risk("asset1", sessions=sessions, telemetry=[])
        assert result.component_scores["service"] > 0.0

    def test_weights_sum_to_one(self):
        assert sum(WEIGHTS.values()) == pytest.approx(1.0)

    def test_rank_assets_by_risk_descending(self):
        assets = [
            AssetRisk("a", 0.3, "medium", [], "", {}),
            AssetRisk("b", 0.8, "critical", [], "", {}),
            AssetRisk("c", 0.1, "low", [], "", {}),
        ]
        ranked = rank_assets_by_risk(assets)
        assert ranked[0].asset_id == "b"
        assert ranked[-1].asset_id == "c"

    def test_contributing_factors_list(self):
        sessions = [self._base_session(safety_triggered=True)]
        result = compute_asset_risk("asset1", sessions=sessions, telemetry=[])
        assert isinstance(result.contributing_factors, list)
        assert len(result.contributing_factors) <= 5

    def test_recommended_action_is_string(self):
        result = compute_asset_risk("asset1", sessions=[], telemetry=[])
        assert isinstance(result.recommended_action, str)
        assert len(result.recommended_action) > 0


# ── Telematics Ingestor ───────────────────────────────────────────────────────

class TestTelematicsIngestor:
    def _ts(self) -> datetime:
        return datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_validate_valid_payload(self):
        result = validate_payload({
            "asset_id": "EX-001",
            "timestamp": self._ts(),
            "engine_temp_c": 85.0,
        })
        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_asset_id(self):
        result = validate_payload({"timestamp": self._ts()})
        assert result.valid is False
        assert any("asset_id" in e for e in result.errors)

    def test_validate_out_of_range_temp(self):
        result = validate_payload({
            "asset_id": "EX-001",
            "timestamp": self._ts(),
            "engine_temp_c": 999.0,   # above 300°C max
        })
        assert result.valid is False

    def test_validate_fault_codes_must_be_list(self):
        result = validate_payload({
            "asset_id": "EX-001",
            "timestamp": self._ts(),
            "fault_codes": "E001",   # should be a list
        })
        assert result.valid is False

    def test_normalize_critical_temp_produces_alert(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            engine_temp_c=TEMP_CRITICAL_C + 5.0,
        )
        result = normalize_telemetry(payload)
        assert any(a.level == "critical" for a in result.safety_alerts)
        assert "critical_overheat" in result.signal_names

    def test_normalize_elevated_temp_warning_packet(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            engine_temp_c=97.0,  # above warning (95), below critical (105)
        )
        result = normalize_telemetry(payload)
        assert "elevated_temp" in result.signal_names
        assert result.safety_alerts == []

    def test_normalize_critical_voltage_alert(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            voltage_v=VOLTAGE_CRITICAL_V - 1.0,
        )
        result = normalize_telemetry(payload)
        assert any(a.level == "critical" for a in result.safety_alerts)

    def test_normalize_low_fuel_packet(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            fuel_level_pct=5.0,
        )
        result = normalize_telemetry(payload)
        assert "low_fuel" in result.signal_names
        assert result.safety_alerts == []

    def test_normalize_fault_codes_packet(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            fault_codes=["E001", "E002"],
        )
        result = normalize_telemetry(payload)
        assert "fault_present" in result.signal_names

    def test_normalize_clean_payload_no_signals(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            engine_temp_c=70.0,
            voltage_v=13.5,
            fuel_level_pct=80.0,
        )
        result = normalize_telemetry(payload)
        assert result.normalized_signals == []
        assert result.safety_alerts == []

    def test_parse_payload_string_timestamp(self):
        data = {
            "asset_id": "EX-001",
            "timestamp": "2026-01-15T10:00:00Z",
            "engine_temp_c": 85.0,
        }
        payload = parse_payload(data)
        assert payload.asset_id == "EX-001"
        assert payload.engine_temp_c == pytest.approx(85.0)
        assert payload.timestamp.tzinfo is not None

    def test_evidence_packets_have_correct_source(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            engine_temp_c=TEMP_CRITICAL_C + 5.0,
        )
        result = normalize_telemetry(payload)
        for packet in result.normalized_signals:
            assert packet.source == "sensor_future"

    def test_critical_alerts_sorted_first(self):
        payload = TelemetryPayload(
            asset_id="EX-001",
            timestamp=self._ts(),
            engine_temp_c=TEMP_CRITICAL_C + 5.0,
            voltage_v=VOLTAGE_CRITICAL_V - 1.0,
        )
        result = normalize_telemetry(payload)
        assert result.safety_alerts[0].level == "critical"
