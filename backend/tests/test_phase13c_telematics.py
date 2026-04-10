"""
Phase 13C — Telematics Hook (Sensor Evidence) — unit tests.

Tests cover the pure Python ingestor layer:
  1. Validation — range checks, required fields, type checks
  2. Normalization — thresholds map to correct signal names
  3. Evidence conversion — correct EvidencePackets produced
  4. Safety hooks — numeric thresholds fire correct SafetyAlerts
  5. Admin inspection — describe_normalization output structure
  6. Partial payloads — missing fields handled gracefully
  7. Evidence packet integrity — source, certainty, affects

All tests are DB-free — pure Python.

Run with:
    docker exec fix-backend-1 python -m pytest tests/test_phase13c_telematics.py -v
"""
from datetime import datetime, timezone

import pytest

from app.telematics.ingestor import (
    FUEL_WARNING_PCT,
    PRESSURE_CRITICAL_PSI,
    PRESSURE_WARNING_PSI,
    TEMP_CRITICAL_C,
    TEMP_WARNING_C,
    VOLTAGE_CRITICAL_V,
    VOLTAGE_WARNING_V,
    NormalizationResult,
    TelemetryPayload,
    describe_normalization,
    normalize_telemetry,
    parse_payload,
    validate_payload,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_TS = "2026-04-06T10:30:00Z"
_DT = datetime(2026, 4, 6, 10, 30, 0, tzinfo=timezone.utc)


def _payload(**kwargs) -> dict:
    """Build a minimal valid telemetry payload dict."""
    base = {"asset_id": "CAT-336-001", "timestamp": _TS}
    base.update(kwargs)
    return base


def _parsed(**kwargs) -> TelemetryPayload:
    """Build a parsed TelemetryPayload directly."""
    return TelemetryPayload(
        asset_id="CAT-336-001",
        timestamp=_DT,
        **kwargs,
    )


def _normalize(**kwargs) -> NormalizationResult:
    """Build and normalize a payload in one step."""
    return normalize_telemetry(_parsed(**kwargs))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_full_payload(self):
        result = validate_payload(_payload(
            engine_temp_c=98.5,
            voltage_v=13.8,
            pressure_psi=2950,
            fuel_level_pct=65.0,
            fault_codes=["P0192"],
        ))
        assert result.valid
        assert not result.errors

    def test_valid_minimal_payload(self):
        result = validate_payload(_payload())
        assert result.valid

    def test_missing_asset_id_fails(self):
        result = validate_payload({"timestamp": _TS})
        assert not result.valid
        assert any("asset_id" in e for e in result.errors)

    def test_empty_asset_id_fails(self):
        result = validate_payload({"asset_id": "  ", "timestamp": _TS})
        assert not result.valid

    def test_missing_timestamp_fails(self):
        result = validate_payload({"asset_id": "CAT-001"})
        assert not result.valid
        assert any("timestamp" in e for e in result.errors)

    def test_invalid_timestamp_fails(self):
        result = validate_payload(_payload(timestamp="not-a-date"))
        assert not result.valid

    def test_engine_temp_out_of_range_fails(self):
        result = validate_payload(_payload(engine_temp_c=500.0))
        assert not result.valid

    def test_engine_temp_negative_fails(self):
        result = validate_payload(_payload(engine_temp_c=-100.0))
        assert not result.valid

    def test_voltage_negative_fails(self):
        result = validate_payload(_payload(voltage_v=-1.0))
        assert not result.valid

    def test_voltage_above_max_fails(self):
        result = validate_payload(_payload(voltage_v=100.0))
        assert not result.valid

    def test_pressure_negative_fails(self):
        result = validate_payload(_payload(pressure_psi=-10.0))
        assert not result.valid

    def test_fuel_above_100_fails(self):
        result = validate_payload(_payload(fuel_level_pct=101.0))
        assert not result.valid

    def test_fuel_exactly_100_valid(self):
        result = validate_payload(_payload(fuel_level_pct=100.0))
        assert result.valid

    def test_fault_codes_not_list_fails(self):
        result = validate_payload(_payload(fault_codes="P0192"))
        assert not result.valid

    def test_fault_codes_non_string_list_fails(self):
        result = validate_payload(_payload(fault_codes=[123, 456]))
        assert not result.valid

    def test_fault_codes_empty_list_valid(self):
        result = validate_payload(_payload(fault_codes=[]))
        assert result.valid

    def test_multiple_errors_all_reported(self):
        result = validate_payload({"asset_id": "", "timestamp": "bad"})
        assert len(result.errors) >= 2

    def test_none_optional_fields_valid(self):
        result = validate_payload(_payload(engine_temp_c=None, voltage_v=None))
        assert result.valid


# ─────────────────────────────────────────────────────────────────────────────
# 2. Normalization — signal detection
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizationSignals:
    """Signal names map correctly to sensor thresholds."""

    def test_normal_all_values_no_signals(self):
        result = _normalize(
            engine_temp_c=85.0,      # normal
            voltage_v=13.8,          # normal
            pressure_psi=3000.0,     # normal
            fuel_level_pct=60.0,     # normal
        )
        assert result.signal_names == []
        assert not result.normalized_signals
        assert not result.safety_alerts

    def test_elevated_temp_fires_warning_signal(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 1)
        assert "elevated_temp" in result.signal_names
        assert "critical_overheat" not in result.signal_names

    def test_critical_temp_fires_critical_signal(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 1)
        assert "critical_overheat" in result.signal_names
        assert "elevated_temp" not in result.signal_names

    def test_exactly_at_warning_temp_fires_elevated(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C)
        assert "elevated_temp" in result.signal_names

    def test_exactly_at_critical_temp_fires_critical(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C)
        assert "critical_overheat" in result.signal_names

    def test_low_voltage_warning_signal(self):
        result = _normalize(voltage_v=VOLTAGE_WARNING_V - 0.5)
        assert "low_voltage" in result.signal_names
        assert "critical_low_voltage" not in result.signal_names

    def test_critical_low_voltage_signal(self):
        result = _normalize(voltage_v=VOLTAGE_CRITICAL_V - 0.5)
        assert "critical_low_voltage" in result.signal_names
        assert "low_voltage" not in result.signal_names

    def test_pressure_abnormal_signal(self):
        result = _normalize(pressure_psi=PRESSURE_WARNING_PSI - 100)
        assert "pressure_abnormal" in result.signal_names
        assert "critical_low_pressure" not in result.signal_names

    def test_critical_low_pressure_signal(self):
        result = _normalize(pressure_psi=PRESSURE_CRITICAL_PSI - 100)
        assert "critical_low_pressure" in result.signal_names
        assert "pressure_abnormal" not in result.signal_names

    def test_low_fuel_signal(self):
        result = _normalize(fuel_level_pct=FUEL_WARNING_PCT - 1)
        assert "low_fuel" in result.signal_names

    def test_fault_codes_present_fires_signal(self):
        result = _normalize(fault_codes=["P0192", "P0087"])
        assert "fault_present" in result.signal_names

    def test_empty_fault_codes_no_signal(self):
        result = _normalize(fault_codes=[])
        assert "fault_present" not in result.signal_names

    def test_no_sensors_provided_no_signals(self):
        result = _normalize()
        assert result.signal_names == []

    def test_multiple_signals_from_multiple_sensors(self):
        result = _normalize(
            engine_temp_c=TEMP_WARNING_C + 5,
            voltage_v=VOLTAGE_WARNING_V - 1,
            pressure_psi=PRESSURE_WARNING_PSI - 100,
            fault_codes=["P0192"],
        )
        assert "elevated_temp" in result.signal_names
        assert "low_voltage" in result.signal_names
        assert "pressure_abnormal" in result.signal_names
        assert "fault_present" in result.signal_names
        assert len(result.signal_names) == 4


# ─────────────────────────────────────────────────────────────────────────────
# 3. Evidence packet structure
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidencePackets:
    """EvidencePackets produced from sensor data have correct structure."""

    def test_sensor_source_on_all_packets(self):
        result = _normalize(
            engine_temp_c=TEMP_WARNING_C + 5,
            voltage_v=VOLTAGE_WARNING_V - 1,
        )
        for packet in result.normalized_signals:
            assert packet.source == "sensor_future", (
                f"Sensor packet must have source='sensor_future', got '{packet.source}'"
            )

    def test_observation_contains_raw_value(self):
        temp = TEMP_WARNING_C + 5
        result = _normalize(engine_temp_c=temp)
        assert result.normalized_signals
        obs = result.normalized_signals[0].observation
        assert str(round(temp, 1)) in obs or str(temp) in obs

    def test_warning_signal_certainty_below_1(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        pkt = result.normalized_signals[0]
        assert pkt.certainty < 1.0
        assert pkt.certainty > 0.5

    def test_critical_signal_certainty_is_1(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        pkt = next(p for p in result.normalized_signals if p.normalized_key == "critical_overheat")
        assert pkt.certainty == pytest.approx(1.0)

    def test_elevated_temp_affects_overheating_hypotheses(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        pkt = result.normalized_signals[0]
        affects = pkt.affects
        assert "thermostat_failure" in affects or "blocked_cooler_screen" in affects, (
            "elevated_temp should affect overheating-related hypothesis keys"
        )

    def test_low_voltage_affects_electrical_hypotheses(self):
        result = _normalize(voltage_v=VOLTAGE_WARNING_V - 1)
        pkt = next(p for p in result.normalized_signals if p.normalized_key == "low_voltage")
        assert "battery_failure" in pkt.affects or "alternator_failure" in pkt.affects

    def test_pressure_abnormal_affects_hydraulic_hypotheses(self):
        result = _normalize(pressure_psi=PRESSURE_WARNING_PSI - 100)
        pkt = next(p for p in result.normalized_signals if p.normalized_key == "pressure_abnormal")
        assert "failed_hydraulic_pump" in pkt.affects or "low_fluid" in pkt.affects

    def test_fault_present_packet_has_code_in_observation(self):
        result = _normalize(fault_codes=["P0192", "P0087"])
        pkt = next(p for p in result.normalized_signals if p.normalized_key == "fault_present")
        assert "P0192" in pkt.observation

    def test_affects_values_are_floats_in_0_1(self):
        result = _normalize(
            engine_temp_c=TEMP_CRITICAL_C + 5,
            voltage_v=VOLTAGE_CRITICAL_V - 1,
            pressure_psi=PRESSURE_CRITICAL_PSI - 100,
        )
        for pkt in result.normalized_signals:
            for key, delta in pkt.affects.items():
                assert 0.0 <= delta <= 1.0, (
                    f"Affects delta for {key} = {delta} is outside [0, 1]"
                )

    def test_normalized_key_matches_signal_name(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        for pkt in result.normalized_signals:
            assert pkt.normalized_key in result.signal_names

    def test_packets_can_be_serialized_to_dict(self):
        """EvidencePackets from telemetry must be storable as JSON (to_dict)."""
        result = _normalize(
            engine_temp_c=TEMP_WARNING_C + 5,
            fault_codes=["P0192"],
        )
        for pkt in result.normalized_signals:
            d = pkt.to_dict()
            assert isinstance(d, dict)
            assert "source" in d
            assert "normalized_key" in d
            assert "certainty" in d
            assert "affects" in d


# ─────────────────────────────────────────────────────────────────────────────
# 4. Safety hooks — numeric threshold alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyHooks:
    """Safety alerts fire from sensor values without text pattern matching."""

    def test_critical_overheat_fires_critical_alert(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert critical, "Critical temp should fire a critical safety alert"
        assert any("overtemperature" in a.message.lower() or "overheat" in a.message.lower()
                   for a in critical)

    def test_elevated_temp_no_critical_alert(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert not critical, "Warning-level temp should not fire a critical alert"

    def test_critical_voltage_fires_critical_alert(self):
        result = _normalize(voltage_v=VOLTAGE_CRITICAL_V - 1)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert critical
        assert any("electrical" in a.message.lower() or "battery" in a.message.lower()
                   for a in critical)

    def test_low_voltage_warning_no_critical_alert(self):
        result = _normalize(voltage_v=VOLTAGE_WARNING_V - 0.5)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert not critical

    def test_critical_pressure_fires_critical_alert(self):
        result = _normalize(pressure_psi=PRESSURE_CRITICAL_PSI - 100)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert critical
        assert any("hydraulic" in a.message.lower() or "pressure" in a.message.lower()
                   for a in critical)

    def test_pressure_abnormal_no_critical_alert(self):
        result = _normalize(pressure_psi=PRESSURE_WARNING_PSI - 100)
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert not critical

    def test_critical_alerts_sorted_before_warnings(self):
        # Trigger both critical (temp) and no warnings — just verify critical comes first
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        if len(result.safety_alerts) > 1:
            levels = [a.level for a in result.safety_alerts]
            # Critical should appear before warning
            if "warning" in levels:
                critical_idx = levels.index("critical")
                warning_idx = levels.index("warning")
                assert critical_idx < warning_idx

    def test_safety_alert_has_recommended_action(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        for alert in result.safety_alerts:
            assert alert.recommended_action, "Safety alert must include recommended_action"
            assert len(alert.recommended_action) > 20

    def test_multiple_critical_conditions_all_fire(self):
        """All three critical conditions at once → three critical alerts."""
        result = _normalize(
            engine_temp_c=TEMP_CRITICAL_C + 5,
            voltage_v=VOLTAGE_CRITICAL_V - 1,
            pressure_psi=PRESSURE_CRITICAL_PSI - 100,
        )
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert len(critical) == 3, (
            f"Three simultaneous critical conditions should each fire, got {len(critical)}"
        )

    def test_alert_to_dict_matches_existing_format(self):
        """SafetyAlert.to_dict() must match the format expected by session safety_flags."""
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        for alert in result.safety_alerts:
            d = alert.to_dict()
            assert "level" in d
            assert "message" in d
            assert "recommended_action" in d
            assert d["level"] in ("warning", "critical")

    def test_no_safety_alerts_for_normal_values(self):
        result = _normalize(
            engine_temp_c=85.0,
            voltage_v=13.8,
            pressure_psi=3000.0,
            fuel_level_pct=60.0,
        )
        assert not result.safety_alerts

    def test_fault_codes_alone_do_not_fire_safety_alert(self):
        """Fault code presence creates evidence but not an automatic critical alert."""
        result = _normalize(fault_codes=["P0192"])
        critical = [a for a in result.safety_alerts if a.level == "critical"]
        assert not critical, "Fault code presence alone must not auto-fire critical alert"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Parse payload
# ─────────────────────────────────────────────────────────────────────────────

class TestParsePayload:
    def test_iso_timestamp_with_z_parsed(self):
        p = parse_payload(_payload(timestamp="2026-04-06T10:30:00Z"))
        assert p.timestamp.tzinfo is not None

    def test_iso_timestamp_with_offset_parsed(self):
        p = parse_payload(_payload(timestamp="2026-04-06T10:30:00+00:00"))
        assert p.timestamp.tzinfo is not None

    def test_asset_id_stripped(self):
        p = parse_payload(_payload(asset_id="  CAT-336  "))
        assert p.asset_id == "CAT-336"

    def test_numeric_fields_converted_to_float(self):
        p = parse_payload(_payload(engine_temp_c="98.5", voltage_v="13.8"))
        assert isinstance(p.engine_temp_c, float)
        assert isinstance(p.voltage_v, float)

    def test_optional_session_id_parsed(self):
        p = parse_payload(_payload(session_id="abc-123"))
        assert p.session_id == "abc-123"

    def test_no_session_id_is_none(self):
        p = parse_payload(_payload())
        assert p.session_id is None

    def test_fault_codes_converted_to_strings(self):
        p = parse_payload(_payload(fault_codes=["P0192", "P0087"]))
        assert all(isinstance(c, str) for c in p.fault_codes)

    def test_missing_optional_fields_are_none(self):
        p = parse_payload(_payload())
        assert p.engine_temp_c is None
        assert p.voltage_v is None
        assert p.pressure_psi is None
        assert p.fuel_level_pct is None
        assert p.fault_codes == []


# ─────────────────────────────────────────────────────────────────────────────
# 6. Describe normalization (admin/debug visibility)
# ─────────────────────────────────────────────────────────────────────────────

class TestDescribeNormalization:
    def test_returns_all_required_keys(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        desc = describe_normalization(result)
        required = {"asset_id", "timestamp", "signal_names", "raw",
                    "evidence_packets", "safety_alerts", "has_critical"}
        assert required.issubset(desc.keys())

    def test_raw_values_preserved(self):
        result = _normalize(engine_temp_c=102.5, voltage_v=13.8, fuel_level_pct=55.0)
        desc = describe_normalization(result)
        assert desc["raw"]["engine_temp_c"] == pytest.approx(102.5)
        assert desc["raw"]["voltage_v"] == pytest.approx(13.8)
        assert desc["raw"]["fuel_level_pct"] == pytest.approx(55.0)

    def test_evidence_packets_list_matches_signal_count(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5, voltage_v=VOLTAGE_WARNING_V - 1)
        desc = describe_normalization(result)
        assert len(desc["evidence_packets"]) == len(result.normalized_signals)

    def test_each_packet_entry_has_required_keys(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        desc = describe_normalization(result)
        for entry in desc["evidence_packets"]:
            assert "normalized_key" in entry
            assert "source" in entry
            assert "observation" in entry
            assert "certainty" in entry
            assert "affects" in entry

    def test_has_critical_false_when_no_critical(self):
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        desc = describe_normalization(result)
        assert desc["has_critical"] is False

    def test_has_critical_true_when_critical(self):
        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        desc = describe_normalization(result)
        assert desc["has_critical"] is True

    def test_no_signals_produces_empty_lists(self):
        result = _normalize(engine_temp_c=80.0)
        desc = describe_normalization(result)
        assert desc["signal_names"] == []
        assert desc["evidence_packets"] == []
        assert desc["safety_alerts"] == []
        assert desc["has_critical"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 7. Evidence integration — packets compatible with session evidence_log
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceIntegration:
    """Verify that telemetry packets can be appended to existing session evidence logs."""

    def test_telemetry_packets_add_sensor_future_source_type(self):
        """Appending telemetry packets increases evidence type count."""
        from app.diagnostics.orchestrator.evidence import evidence_type_count

        existing = [
            {"source": "intake",    "normalized_key": "intake", "certainty": 1.0, "affects": {}},
            {"source": "user_text", "normalized_key": "q1",     "certainty": 0.9, "affects": {}},
        ]
        result = _normalize(engine_temp_c=TEMP_WARNING_C + 5)
        sensor_dicts = [p.to_dict() for p in result.normalized_signals]
        combined = existing + sensor_dicts

        count = evidence_type_count(combined)
        assert count == 3, (
            f"intake + user_text + sensor_future = 3 evidence types, got {count}"
        )

    def test_telemetry_affects_match_real_hypothesis_keys_in_overheating_tree(self):
        """
        Hypothesis keys in telemetry affects must exist in the overheating tree.
        Only matching keys will have effect when applied — non-matching are ignored.
        """
        from app.engine.trees import HYPOTHESES

        result = _normalize(engine_temp_c=TEMP_CRITICAL_C + 5)
        critical_pkt = next(
            (p for p in result.normalized_signals if p.normalized_key == "critical_overheat"),
            None
        )
        assert critical_pkt, "Should have a critical_overheat packet"

        overheating_hyp_keys = set(HYPOTHESES["overheating_heavy_equipment"].keys())
        affects_keys = set(critical_pkt.affects.keys())

        # At least some affects keys should exist in the overheating tree
        overlap = affects_keys & overheating_hyp_keys
        assert overlap, (
            f"critical_overheat affects {affects_keys} has no overlap with "
            f"overheating_heavy_equipment hypotheses {overheating_hyp_keys}"
        )

    def test_hydraulic_pressure_affects_match_hydraulic_tree(self):
        from app.engine.trees import HYPOTHESES

        result = _normalize(pressure_psi=PRESSURE_CRITICAL_PSI - 100)
        critical_pkt = next(
            (p for p in result.normalized_signals if p.normalized_key == "critical_low_pressure"),
            None
        )
        assert critical_pkt

        hydraulic_hyp_keys = set(HYPOTHESES["hydraulic_loss_heavy_equipment"].keys())
        overlap = set(critical_pkt.affects.keys()) & hydraulic_hyp_keys
        assert overlap, "critical_low_pressure affects should match hydraulic_loss hypothesis keys"

    def test_voltage_affects_match_electrical_tree(self):
        from app.engine.trees import HYPOTHESES

        result = _normalize(voltage_v=VOLTAGE_CRITICAL_V - 1)
        pkt = next(
            (p for p in result.normalized_signals if p.normalized_key == "critical_low_voltage"),
            None
        )
        assert pkt

        electrical_hyp_keys = set(HYPOTHESES["electrical_fault_heavy_equipment"].keys())
        overlap = set(pkt.affects.keys()) & electrical_hyp_keys
        assert overlap, "critical_low_voltage affects should match electrical_fault hypothesis keys"


# ─────────────────────────────────────────────────────────────────────────────
# 8. _SIGNAL_AFFECTS integrity — every hypothesis key must exist in ≥1 tree
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalAffectsIntegrity:
    """
    Every hypothesis key referenced in _SIGNAL_AFFECTS must exist in at least
    one tree's HYPOTHESES dict.  This prevents silent no-ops when telemetry
    evidence is applied to a session scorer.
    """

    def test_all_signal_affects_keys_in_at_least_one_tree(self):
        from app.engine.trees import HYPOTHESES
        from app.telematics.ingestor import _SIGNAL_AFFECTS

        # Collect every hypothesis key across all trees
        all_hyp_keys: set[str] = set()
        for tree_hyps in HYPOTHESES.values():
            all_hyp_keys.update(tree_hyps.keys())

        orphaned: dict[str, list[str]] = {}
        for signal, affects in _SIGNAL_AFFECTS.items():
            missing = [k for k in affects if k not in all_hyp_keys]
            if missing:
                orphaned[signal] = missing

        assert not orphaned, (
            f"_SIGNAL_AFFECTS references hypothesis keys that exist in no tree:\n"
            + "\n".join(f"  {sig}: {keys}" for sig, keys in orphaned.items())
        )

    def test_fault_present_empty_affects_is_intentional(self):
        """fault_present has no static affects — it's populated by DTC classification."""
        from app.telematics.ingestor import _SIGNAL_AFFECTS

        assert _SIGNAL_AFFECTS["fault_present"] == {}, (
            "fault_present must have empty affects (populated dynamically by DTC lookup)"
        )
