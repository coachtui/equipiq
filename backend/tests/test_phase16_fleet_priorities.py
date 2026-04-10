"""
Phase 16 — Fleet Prioritization Layer — unit tests.

All tests operate on plain Python structures.  No database required.

Run with:
    cd backend && docker exec fix-backend-1 python -m pytest tests/test_phase16_fleet_priorities.py -v
"""
import pytest

from app.fleet.risk_model import (
    SERVICE_INTERVAL_HOURS,
    WEIGHTS,
    AssetRisk,
    _build_factors,
    _recommended_action,
    _risk_level,
    compute_asset_risk,
    rank_assets_by_risk,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / builders
# ─────────────────────────────────────────────────────────────────────────────

def _session(
    *,
    status: str = "complete",
    symptom: str = "hydraulic_loss",
    was_resolved: bool | None = True,
    safety_triggered: bool = False,
    contradictions: int = 0,
    hours: int | None = None,
    last_service: int | None = None,
    has_anomaly: bool = False,
) -> dict:
    hc = {}
    if hours is not None:
        hc["hours_of_operation"] = hours
    if last_service is not None:
        hc["last_service_hours"] = last_service
    return {
        "session_id": "test-session",
        "status": status,
        "symptom_category": symptom,
        "vehicle_type": "heavy_equipment",
        "safety_flags": [],
        "context": {"last_anomaly": {"severity": 0.8}} if has_anomaly else {},
        "heavy_context": hc,
        "created_at": "2026-04-01T00:00:00",
        "was_resolved": was_resolved,
        "safety_triggered": safety_triggered,
        "contradiction_count": contradictions,
        "top_hypothesis": "test_hypothesis",
    }


def _tel(*, has_critical: bool = False, has_warning: bool = False) -> dict:
    alerts = []
    if has_critical:
        alerts.append({"severity": "critical", "message": "engine overtemp"})
    if has_warning:
        alerts.append({"severity": "warning", "message": "low voltage"})
    return {"safety_alerts": alerts, "received_at": "2026-04-07T00:00:00"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk level mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskLevel:
    def test_zero_is_low(self):
        assert _risk_level(0.0) == "low"

    def test_low_boundary(self):
        assert _risk_level(0.24) == "low"

    def test_medium_boundary(self):
        assert _risk_level(0.25) == "medium"

    def test_medium_upper(self):
        assert _risk_level(0.499) == "medium"

    def test_high_boundary(self):
        assert _risk_level(0.50) == "high"

    def test_high_upper(self):
        assert _risk_level(0.749) == "high"

    def test_critical_boundary(self):
        assert _risk_level(0.75) == "critical"

    def test_critical_max(self):
        assert _risk_level(1.0) == "critical"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Individual factor scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestFactorScoring:
    def test_no_sessions_zero_score(self):
        risk = compute_asset_risk("A1", [], [])
        assert risk.risk_score == 0.0
        assert risk.risk_level == "low"

    def test_unresolved_open_session_raises_score(self):
        sessions = [_session(status="active", was_resolved=None)]
        risk = compute_asset_risk("A1", sessions, [])
        # unresolved_count=1, score = 0.30 * (1/5) = 0.06
        assert risk.component_scores["unresolved"] == pytest.approx(0.06, abs=0.001)
        assert risk.risk_score > 0.0

    def test_five_unresolved_maxes_unresolved_component(self):
        sessions = [_session(status="active", was_resolved=None) for _ in range(5)]
        risk = compute_asset_risk("A1", sessions, [])
        # unresolved_norm = 1.0, weighted = 0.30
        assert risk.component_scores["unresolved"] == pytest.approx(WEIGHTS["unresolved"], abs=0.001)

    def test_more_than_five_unresolved_clamped(self):
        sessions = [_session(status="active", was_resolved=None) for _ in range(10)]
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["unresolved"] == pytest.approx(WEIGHTS["unresolved"], abs=0.001)

    def test_single_symptom_no_repeat_score(self):
        sessions = [_session(symptom="hydraulic_loss")]
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["repeat"] == 0.0

    def test_two_same_symptom_raises_repeat_score(self):
        sessions = [_session(symptom="hydraulic_loss")] * 2
        risk = compute_asset_risk("A1", sessions, [])
        # repeat_norm = (2-1)/3 = 0.333, weighted = 0.20 * 0.333 ≈ 0.0667
        assert risk.component_scores["repeat"] > 0.0

    def test_four_same_symptom_maxes_repeat_component(self):
        sessions = [_session(symptom="hydraulic_loss")] * 4
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["repeat"] == pytest.approx(WEIGHTS["repeat"], abs=0.001)

    def test_safety_triggered_session_raises_safety_score(self):
        sessions = [_session(safety_triggered=True)]
        risk = compute_asset_risk("A1", sessions, [])
        # safety_norm = 1/3 ≈ 0.333, weighted = 0.20 * 0.333 ≈ 0.0667
        assert risk.component_scores["safety"] > 0.0

    def test_critical_telemetry_contributes_safety_score(self):
        risk = compute_asset_risk("A1", [], [_tel(has_critical=True)])
        assert risk.component_scores["safety"] > 0.0

    def test_warning_telemetry_not_critical_no_safety_score(self):
        # Warning-level alerts do NOT count toward safety_score; they count as
        # tel_abnormal (telematics score), not critical events.
        risk = compute_asset_risk("A1", [], [_tel(has_warning=True)])
        assert risk.component_scores["safety"] == 0.0

    def test_warning_telemetry_raises_telematics_score(self):
        risk = compute_asset_risk("A1", [], [_tel(has_warning=True)])
        assert risk.component_scores["telematics"] > 0.0

    def test_contradictions_raise_contradiction_score(self):
        sessions = [_session(contradictions=3)]
        risk = compute_asset_risk("A1", sessions, [])
        # avg_contra = 3, contradiction_norm = 1.0, weighted = 0.15
        assert risk.component_scores["contradiction"] == pytest.approx(WEIGHTS["contradiction"], abs=0.001)

    def test_anomaly_session_raises_anomaly_score(self):
        sessions = [_session(has_anomaly=True)]
        risk = compute_asset_risk("A1", sessions, [])
        # anomaly_norm = 1/1 = 1.0, weighted = 0.05
        assert risk.component_scores["anomaly"] == pytest.approx(WEIGHTS["anomaly"], abs=0.001)

    def test_service_overdue_raises_service_score(self):
        sessions = [_session(hours=1500, last_service=1000)]
        risk = compute_asset_risk("A1", sessions, [])
        # gap = 500 >= SERVICE_INTERVAL_HOURS(250) → overdue
        assert risk.component_scores["service"] == pytest.approx(WEIGHTS["service"], abs=0.001)

    def test_service_not_overdue_zero_service_score(self):
        sessions = [_session(hours=1100, last_service=1000)]
        risk = compute_asset_risk("A1", sessions, [])
        # gap = 100 < 250 → not overdue
        assert risk.component_scores["service"] == 0.0

    def test_service_overdue_exact_threshold(self):
        sessions = [_session(hours=1250, last_service=1000)]
        risk = compute_asset_risk("A1", sessions, [])
        # gap = 250 >= 250 → overdue
        assert risk.component_scores["service"] == pytest.approx(WEIGHTS["service"], abs=0.001)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Score normalization and clamping
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalization:
    def test_score_bounded_above(self):
        # Worst possible asset — every factor maxed
        sessions = (
            [_session(status="active", was_resolved=None, safety_triggered=True,
                      contradictions=5, has_anomaly=True, symptom="hydraulic_loss",
                      hours=5000, last_service=1000)] * 10
        )
        telemetry = [_tel(has_critical=True)] * 10
        risk = compute_asset_risk("A1", sessions, telemetry)
        assert risk.risk_score <= 1.0

    def test_score_bounded_below(self):
        risk = compute_asset_risk("A1", [], [])
        assert risk.risk_score >= 0.0

    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_score_is_deterministic(self):
        sessions = [_session(status="active"), _session(safety_triggered=True)]
        r1 = compute_asset_risk("A1", sessions, [_tel(has_warning=True)])
        r2 = compute_asset_risk("A1", sessions, [_tel(has_warning=True)])
        assert r1.risk_score == r2.risk_score

    def test_score_rounded_to_4dp(self):
        sessions = [_session(contradictions=1)]
        risk = compute_asset_risk("A1", sessions, [])
        assert len(str(risk.risk_score).split(".")[-1]) <= 4

    def test_component_scores_sum_equals_total(self):
        sessions = [_session(status="active"), _session(safety_triggered=True)]
        risk = compute_asset_risk("A1", sessions, [_tel(has_warning=True)])
        assert sum(risk.component_scores.values()) == pytest.approx(risk.risk_score, abs=0.001)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Priority ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestPriorityRanking:
    def _make_risk(self, asset_id: str, score: float) -> AssetRisk:
        level = _risk_level(score)
        return AssetRisk(
            asset_id=asset_id,
            risk_score=score,
            risk_level=level,
            contributing_factors=[],
            recommended_action="",
        )

    def test_rank_descending(self):
        risks = [
            self._make_risk("A", 0.3),
            self._make_risk("B", 0.9),
            self._make_risk("C", 0.6),
        ]
        ranked = rank_assets_by_risk(risks)
        scores = [r.risk_score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_highest_risk_first(self):
        risks = [
            self._make_risk("low", 0.1),
            self._make_risk("critical", 0.9),
            self._make_risk("medium", 0.4),
        ]
        ranked = rank_assets_by_risk(risks)
        assert ranked[0].asset_id == "critical"
        assert ranked[-1].asset_id == "low"

    def test_single_asset_ranks_correctly(self):
        risks = [self._make_risk("only", 0.5)]
        ranked = rank_assets_by_risk(risks)
        assert len(ranked) == 1
        assert ranked[0].asset_id == "only"

    def test_empty_list(self):
        assert rank_assets_by_risk([]) == []

    def test_all_zero_scores(self):
        risks = [self._make_risk(str(i), 0.0) for i in range(3)]
        ranked = rank_assets_by_risk(risks)
        assert all(r.risk_score == 0.0 for r in ranked)

    def test_higher_risk_asset_ranks_above_lower(self):
        sessions_high = [
            _session(status="active"), _session(safety_triggered=True),
            _session(symptom="hydraulic_loss"), _session(symptom="hydraulic_loss"),
        ]
        sessions_low = [_session(was_resolved=True)]
        high = compute_asset_risk("HIGH", sessions_high, [_tel(has_critical=True)])
        low = compute_asset_risk("LOW", sessions_low, [])
        ranked = rank_assets_by_risk([low, high])
        assert ranked[0].asset_id == "HIGH"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Explainability — contributing factors
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainability:
    def test_no_risk_no_factors(self):
        risk = compute_asset_risk("A1", [], [])
        assert risk.contributing_factors == []

    def test_unresolved_appears_in_factors(self):
        sessions = [_session(status="active")]
        risk = compute_asset_risk("A1", sessions, [])
        assert any("unresolved" in f for f in risk.contributing_factors)

    def test_repeat_symptom_appears_in_factors(self):
        sessions = [_session(symptom="hydraulic_loss")] * 3
        risk = compute_asset_risk("A1", sessions, [])
        assert any("hydraulic loss" in f for f in risk.contributing_factors)

    def test_safety_trigger_appears_in_factors(self):
        sessions = [_session(safety_triggered=True)]
        risk = compute_asset_risk("A1", sessions, [])
        assert any("safety" in f.lower() for f in risk.contributing_factors)

    def test_service_overdue_appears_in_factors(self):
        sessions = [_session(hours=2000, last_service=1000)]
        risk = compute_asset_risk("A1", sessions, [])
        assert any("service overdue" in f for f in risk.contributing_factors)

    def test_max_five_factors(self):
        sessions = (
            [_session(status="active", safety_triggered=True, contradictions=3,
                      has_anomaly=True, symptom="hydraulic_loss", hours=2000,
                      last_service=1000)] * 4
        )
        telemetry = [_tel(has_critical=True), _tel(has_warning=True)] * 3
        risk = compute_asset_risk("A1", sessions, telemetry)
        assert len(risk.contributing_factors) <= 5

    def test_factors_ordered_by_impact(self):
        # Safety (0.20 weight) should outrank telematics (0.05 weight)
        # when both are at similar normalised levels.
        sessions = [_session(safety_triggered=True)]
        telemetry = [_tel(has_warning=True)]
        risk = compute_asset_risk("A1", sessions, telemetry)
        safety_idx = next(
            (i for i, f in enumerate(risk.contributing_factors) if "safety" in f.lower()), None
        )
        tel_idx = next(
            (i for i, f in enumerate(risk.contributing_factors) if "telemetry" in f.lower()), None
        )
        if safety_idx is not None and tel_idx is not None:
            assert safety_idx < tel_idx


# ─────────────────────────────────────────────────────────────────────────────
# 6. Recommended actions
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendedAction:
    def _action(self, **kwargs) -> str:
        defaults = dict(
            tel_critical_count=0,
            session_safety_count=0,
            unresolved_count=0,
            max_repeat=0,
            top_symptom=None,
            service_overdue=False,
            avg_contradictions=0.0,
            tel_abnormal=0,
            risk_score=0.0,
        )
        defaults.update(kwargs)
        return _recommended_action(**defaults)

    def test_critical_telemetry_highest_priority(self):
        action = self._action(
            tel_critical_count=1,
            session_safety_count=1,
            unresolved_count=5,
            risk_score=1.0,
        )
        assert "Immediate stop" in action

    def test_session_safety_second_priority(self):
        action = self._action(session_safety_count=1, risk_score=0.5)
        assert "Immediate inspection" in action

    def test_escalate_when_recurring_and_unresolved(self):
        action = self._action(
            unresolved_count=2, max_repeat=2, top_symptom="hydraulic_loss"
        )
        assert "Escalate" in action
        assert "hydraulic loss" in action

    def test_escalate_high_unresolved_count(self):
        action = self._action(unresolved_count=3)
        assert "Escalate" in action

    def test_service_overdue_and_repeat(self):
        action = self._action(service_overdue=True, max_repeat=2, top_symptom="no_start")
        assert "urgent service" in action.lower()

    def test_service_overdue_alone(self):
        action = self._action(service_overdue=True)
        assert "Schedule service" in action

    def test_repeat_without_unresolved(self):
        action = self._action(max_repeat=2, top_symptom="no_start")
        assert "Re-investigate" in action
        assert "no start" in action

    def test_high_contradictions(self):
        action = self._action(avg_contradictions=2.0)
        assert "contradiction" in action.lower()

    def test_elevated_telemetry_alerts(self):
        action = self._action(tel_abnormal=3)
        assert "sensor" in action.lower()

    def test_no_risk_no_action(self):
        action = self._action()
        assert "No immediate action" in action

    def test_action_traceable_to_input(self):
        # Safety input → safety action (not a generic message)
        sessions = [_session(safety_triggered=True)]
        risk = compute_asset_risk("A1", sessions, [])
        assert "inspection" in risk.recommended_action.lower() or "stop" in risk.recommended_action.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Behaviour with missing / partial data
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingData:
    def test_no_heavy_context_no_service_score(self):
        sessions = [_session()]  # no hours or last_service
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["service"] == 0.0

    def test_session_with_null_was_resolved(self):
        sessions = [_session(was_resolved=None, status="complete")]
        risk = compute_asset_risk("A1", sessions, [])
        # was_resolved=None + status=complete → not unresolved
        assert risk.component_scores["unresolved"] == 0.0

    def test_session_with_no_symptom_no_repeat_score(self):
        sessions = [
            {**_session(), "symptom_category": None},
            {**_session(), "symptom_category": None},
        ]
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["repeat"] == 0.0

    def test_empty_safety_alerts_list(self):
        risk = compute_asset_risk("A1", [], [{"safety_alerts": [], "received_at": None}])
        assert risk.component_scores["safety"] == 0.0
        assert risk.component_scores["telematics"] == 0.0

    def test_none_safety_alerts(self):
        risk = compute_asset_risk("A1", [], [{"safety_alerts": None, "received_at": None}])
        assert risk.component_scores["safety"] == 0.0

    def test_no_telemetry_zero_tel_scores(self):
        sessions = [_session()]
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["telematics"] == 0.0

    def test_last_service_zero_not_overdue(self):
        # last_service_hours = 0 means unknown / not set; should not flag overdue
        sessions = [_session(hours=1000, last_service=0)]
        risk = compute_asset_risk("A1", sessions, [])
        assert risk.component_scores["service"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 8. API endpoint registered
# ─────────────────────────────────────────────────────────────────────────────

def test_priorities_endpoint_registered():
    from app.main import app
    routes = {r.path for r in app.routes}
    assert "/api/fleet/priorities" in routes


def test_priorities_requires_auth():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/api/fleet/priorities")
    assert res.status_code in (401, 403)
