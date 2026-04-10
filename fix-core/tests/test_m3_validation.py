"""
M3 validation tests — verify the M3 changes hold before M4 begins.

Covers:
  1. Core Pydantic model round-trips
  2. HypothesisScorer conversion bridge (to/from_hypothesis_scores)
  3. Session-level exit-guard helpers (can_exit_from_session / exit_reason_from_session)
  4. Evidence and safety normalization — both dict and Pydantic object inputs
  5. Heavy equipment subtype handling
  6. Full DiagnosticSession aggregate persistence shape
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from fix_core.engine.context_heavy import (
    HeavyContext,
    _HE_VEHICLE_TYPES,
    apply_heavy_context_priors,
    heavy_context_from_intake,
)
from fix_core.engine.hypothesis_scorer import HypothesisScorer
from fix_core.models.context import OwnerContext
from fix_core.models.evidence import EvidencePacket
from fix_core.models.hypothesis import HypothesisScore
from fix_core.models.result import DiagnosticResult, RankedCause
from fix_core.models.safety import SafetyAlert
from fix_core.models.session import (
    DiagnosticSession,
    MediaReference,
    MessageRole,
    MessageType,
    SessionMessage,
    SessionMode,
    SessionState,
)
from fix_core.orchestrator.contradictions import detect_contradictions, merge_flags, Contradiction
from fix_core.orchestrator.evidence import (
    build_from_classification,
    evidence_type_count,
)
from fix_core.orchestrator.exit_guard import (
    can_exit,
    can_exit_from_session,
    exit_reason,
    exit_reason_from_session,
)
from fix_core.orchestrator.safety import evaluate_safety
from fix_core.trees import TREES


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_session(**overrides) -> DiagnosticSession:
    sid = uuid4()
    base = dict(
        id=sid,
        owner=OwnerContext(user_id=uuid4()),
        created_at=_now(),
        updated_at=_now(),
        answered_nodes=4,
        evidence_log=[
            {"source": "intake", "observation": "won't start", "normalized_key": "intake_description", "certainty": 1.0, "affects": {}},
            {"source": "user_text", "observation": "clicks", "normalized_key": "click_noise", "certainty": 0.8, "affects": {"dead_battery": 0.15}},
        ],
        contradiction_flags=[],
        safety_flags=[],
    )
    base.update(overrides)
    return DiagnosticSession(**base)


def _make_high_scorer() -> HypothesisScorer:
    return HypothesisScorer({
        "dead_battery": {"label": "Dead battery", "prior": 0.9},
        "starter_motor": {"label": "Starter motor", "prior": 0.1},
    })


# ── 1. Core model round-trips ──────────────────────────────────────────────────

class TestModelRoundTrips:

    def test_owner_context_roundtrip(self):
        uid, oid = uuid4(), uuid4()
        ctx = OwnerContext(user_id=uid, org_id=oid, source="standalone")
        d = ctx.model_dump()
        ctx2 = OwnerContext.model_validate(d)
        assert ctx2.user_id == uid
        assert ctx2.org_id == oid
        assert ctx2.source == "standalone"
        assert ctx2.project_id is None

    def test_owner_context_minimal_roundtrip(self):
        ctx = OwnerContext(user_id=uuid4())
        d = ctx.model_dump()
        ctx2 = OwnerContext.model_validate(d)
        assert ctx2.org_id is None
        assert ctx2.asset_id is None

    def test_hypothesis_score_roundtrip(self):
        h = HypothesisScore(
            key="dead_battery", label="Dead battery", score=0.72,
            eliminated=False, evidence=["Q: Does it crank? → A: No"],
            diy_difficulty="easy", parts=[{"name": "Battery", "price": 120}],
        )
        d = h.model_dump()
        h2 = HypothesisScore.model_validate(d)
        assert h2.key == "dead_battery"
        assert h2.score == pytest.approx(0.72)
        assert h2.evidence == ["Q: Does it crank? → A: No"]
        assert h2.parts[0]["name"] == "Battery"

    def test_hypothesis_score_clamping_above(self):
        h = HypothesisScore(key="k", label="L", score=1.8)
        assert h.score == pytest.approx(1.0)

    def test_hypothesis_score_clamping_below(self):
        h = HypothesisScore(key="k", label="L", score=-0.5)
        assert h.score == pytest.approx(0.0)

    def test_evidence_packet_roundtrip_via_to_dict(self):
        ep = EvidencePacket(
            source="user_text",
            observation="engine clicks when turning key",
            normalized_key="click_on_crank",
            certainty=0.85,
            affects={"dead_battery": 0.2, "starter_motor": 0.1},
        )
        d = ep.to_dict()
        ep2 = EvidencePacket.from_dict(d)
        assert ep2.source == ep.source
        assert ep2.normalized_key == ep.normalized_key
        assert ep2.certainty == pytest.approx(0.85)
        assert ep2.affects == ep.affects

    def test_evidence_packet_roundtrip_via_model_validate(self):
        ep = EvidencePacket(
            source="image", observation="visible battery corrosion",
            normalized_key="image_analysis", certainty=0.7, affects={"dead_battery": 0.15},
        )
        d = ep.model_dump()
        ep2 = EvidencePacket.model_validate(d)
        assert ep2 == ep

    def test_safety_alert_roundtrip(self):
        sa = SafetyAlert(
            level="critical",
            message="Fuel leak or vapor detected.",
            recommended_action="Turn off the engine immediately.",
        )
        d = sa.to_dict()
        sa2 = SafetyAlert.model_validate(d)
        assert sa2.level == "critical"
        assert sa2.message == sa.message
        assert sa2.recommended_action == sa.recommended_action

    def test_safety_alert_warning_roundtrip(self):
        sa = SafetyAlert(level="warning", message="Overheating.", recommended_action="Pull over.")
        d = sa.to_dict()
        sa2 = SafetyAlert.model_validate(d)
        assert sa2.level == "warning"

    def test_media_reference_roundtrip(self):
        mr = MediaReference(
            storage_path="/uploads/test.jpg",
            filename="test.jpg",
            media_type="image/jpeg",
            uploaded_at=_now(),
        )
        d = mr.model_dump()
        mr2 = MediaReference.model_validate(d)
        assert mr2.storage_path == "/uploads/test.jpg"
        assert mr2.media_type == "image/jpeg"

    def test_diagnostic_result_roundtrip(self):
        result = DiagnosticResult(
            id=uuid4(),
            session_id=uuid4(),
            created_at=_now(),
            ranked_causes=[
                RankedCause(hypothesis_key="dead_battery", label="Dead battery", score=0.82, diy_difficulty="easy"),
            ],
            next_checks=["Check battery voltage", "Test alternator"],
            confidence_level=0.82,
        )
        d = result.model_dump()
        result2 = DiagnosticResult.model_validate(d)
        assert result2.id == result.id
        assert result2.ranked_causes[0].hypothesis_key == "dead_battery"
        assert result2.confidence_level == pytest.approx(0.82)

    def test_diagnostic_session_minimal_roundtrip(self):
        session = _make_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.id == session.id
        assert session2.answered_nodes == 4
        assert session2.owner.user_id == session.owner.user_id

    def test_diagnostic_session_status_enum_survives(self):
        session = _make_session(status=SessionState.completed)
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.status == SessionState.completed


# ── 2. HypothesisScorer conversion bridge ─────────────────────────────────────

class TestScorerConversionBridge:

    def _make_scorer_with_state(self) -> HypothesisScorer:
        hyp_def = {
            "dead_battery": {"label": "Dead battery", "prior": 0.4},
            "starter_motor": {"label": "Starter motor", "prior": 0.3},
            "bad_ground": {"label": "Bad ground", "prior": 0.2},
        }
        scorer = HypothesisScorer(hyp_def)
        scorer.apply_option(
            {"deltas": {"dead_battery": 0.3, "starter_motor": -0.1}, "eliminate": ["bad_ground"]},
            "Does it crank at all?", "Complete silence",
        )
        return scorer, hyp_def

    def test_to_hypothesis_scores_returns_pydantic_models(self):
        scorer, _ = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        assert all(isinstance(s, HypothesisScore) for s in scores)

    def test_to_hypothesis_scores_count_matches(self):
        scorer, _ = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        assert len(scores) == 3  # all hypotheses, including eliminated

    def test_to_hypothesis_scores_scores_preserved(self):
        scorer, _ = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        by_key = {s.key: s for s in scores}
        assert by_key["dead_battery"].score == pytest.approx(0.7)
        assert by_key["starter_motor"].score == pytest.approx(0.2)

    def test_to_hypothesis_scores_elimination_preserved(self):
        scorer, _ = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        by_key = {s.key: s for s in scores}
        assert by_key["bad_ground"].eliminated is True
        assert by_key["bad_ground"].score == pytest.approx(0.0)
        assert by_key["dead_battery"].eliminated is False

    def test_to_hypothesis_scores_evidence_preserved(self):
        scorer, _ = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        by_key = {s.key: s for s in scores}
        assert len(by_key["dead_battery"].evidence) == 1
        assert "Does it crank" in by_key["dead_battery"].evidence[0]

    def test_from_hypothesis_scores_restores_top_confidence(self):
        scorer, hyp_def = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        restored = HypothesisScorer.from_hypothesis_scores(hyp_def, scores)
        assert restored.top_confidence() == pytest.approx(scorer.top_confidence())

    def test_from_hypothesis_scores_restores_ranking(self):
        scorer, hyp_def = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        restored = HypothesisScorer.from_hypothesis_scores(hyp_def, scores)
        orig_ranked = [h.key for h in scorer.ranked()]
        rest_ranked = [h.key for h in restored.ranked()]
        assert orig_ranked == rest_ranked

    def test_from_hypothesis_scores_restores_elimination(self):
        scorer, hyp_def = self._make_scorer_with_state()
        scores = scorer.to_hypothesis_scores()
        restored = HypothesisScorer.from_hypothesis_scores(hyp_def, scores)
        assert restored.hypotheses["bad_ground"].eliminated is True
        # eliminated hyp excluded from ranked()
        assert "bad_ground" not in [h.key for h in restored.ranked()]

    def test_full_roundtrip_via_session(self):
        """Simulate session save → restore cycle through HypothesisScore."""
        scorer, hyp_def = self._make_scorer_with_state()
        # Simulate storing in session
        scores = scorer.to_hypothesis_scores()
        session = _make_session(hypotheses=scores)
        # Simulate restoring from session
        restored = HypothesisScorer.from_hypothesis_scores(hyp_def, session.hypotheses)
        assert restored.top_confidence() == pytest.approx(scorer.top_confidence())
        assert restored.should_exit_early() == scorer.should_exit_early()

    def test_from_hypothesis_scores_with_weight_multipliers(self):
        """Weight multipliers are applied at init; from_hypothesis_scores overrides to saved values."""
        hyp_def = {"k": {"label": "K", "prior": 0.5}}
        scores = [HypothesisScore(key="k", label="K", score=0.9)]
        scorer = HypothesisScorer.from_hypothesis_scores(hyp_def, scores, weight_multipliers={"k": 2.0})
        # Saved score (0.9) should override the init-time weight-multiplied value
        assert scorer.hypotheses["k"].score == pytest.approx(0.9)


# ── 3. Session helper tests ────────────────────────────────────────────────────

class TestSessionExitHelpers:

    def test_can_exit_from_session_matches_direct_call(self):
        session = _make_session()
        scorer = _make_high_scorer()
        direct = can_exit(
            scorer,
            answered_nodes=session.answered_nodes,
            evidence_log=session.evidence_log,
            contradiction_flags=session.contradiction_flags,
        )
        via_session = can_exit_from_session(session, scorer)
        assert direct == via_session

    def test_exit_reason_from_session_matches_direct_call(self):
        session = _make_session(answered_nodes=1, evidence_log=[])
        scorer = _make_high_scorer()
        direct = exit_reason(
            scorer,
            answered_nodes=session.answered_nodes,
            evidence_log=session.evidence_log,
            contradiction_flags=session.contradiction_flags,
        )
        via_session = exit_reason_from_session(session, scorer)
        assert direct == via_session

    def test_can_exit_from_session_allowed_when_all_conditions_met(self):
        session = _make_session()  # 4 nodes, 2 evidence types, no contradictions
        scorer = _make_high_scorer()
        assert can_exit_from_session(session, scorer) is True

    def test_can_exit_from_session_blocked_by_insufficient_nodes(self):
        session = _make_session(answered_nodes=2)
        scorer = _make_high_scorer()
        assert can_exit_from_session(session, scorer) is False

    def test_can_exit_from_session_blocked_by_insufficient_evidence_types(self):
        session = _make_session(
            answered_nodes=5,
            evidence_log=[
                {"source": "intake", "affects": {}},
                {"source": "intake", "affects": {}},  # same type
            ],
        )
        scorer = _make_high_scorer()
        assert can_exit_from_session(session, scorer) is False

    def test_can_exit_from_session_blocked_by_contradiction(self):
        session = _make_session(
            contradiction_flags=[{"severity": 0.7, "description": "reversal conflict"}],
        )
        scorer = _make_high_scorer()
        assert can_exit_from_session(session, scorer) is False

    def test_exit_reason_from_session_returns_none_when_allowed(self):
        session = _make_session()
        scorer = _make_high_scorer()
        assert exit_reason_from_session(session, scorer) is None

    def test_exit_reason_from_session_describes_block(self):
        session = _make_session(answered_nodes=1, evidence_log=[])
        scorer = _make_high_scorer()
        reason = exit_reason_from_session(session, scorer)
        assert reason is not None
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_custom_thresholds_propagated(self):
        """Threshold overrides passed to the helper reach can_exit."""
        session = _make_session()
        scorer = _make_high_scorer()  # top=0.9, lead=0.8
        # Very high threshold — should block
        assert can_exit_from_session(session, scorer, score_threshold=0.99) is False
        # Low threshold — should allow
        assert can_exit_from_session(session, scorer, score_threshold=0.5, lead_threshold=0.1) is True


# ── 4. Evidence and safety normalization tests ─────────────────────────────────

class TestNormalizationPaths:

    # ── contradiction detection ──

    def test_contradiction_detects_reversal_with_dicts(self):
        log = [
            {"source": "intake", "affects": {"dead_battery": 0.30}},
            {"source": "user_text", "affects": {"dead_battery": 0.25}},
            {"source": "image", "affects": {"dead_battery": -0.30}},
            {"source": "manual_test", "affects": {"dead_battery": -0.25}},
        ]
        result = detect_contradictions(log)
        assert any(c.type == "score_reversal" for c in result)

    def test_contradiction_detects_reversal_with_pydantic_objects(self):
        log = [
            EvidencePacket(source="intake", observation="won't start", normalized_key="no_start", certainty=1.0, affects={"dead_battery": 0.30}),
            EvidencePacket(source="user_text", observation="clicks", normalized_key="click", certainty=0.8, affects={"dead_battery": 0.25}),
            EvidencePacket(source="image", observation="new battery", normalized_key="visual", certainty=0.9, affects={"dead_battery": -0.30}),
            EvidencePacket(source="manual_test", observation="12.6V", normalized_key="voltage_ok", certainty=0.95, affects={"dead_battery": -0.25}),
        ]
        result = detect_contradictions(log)
        assert any(c.type == "score_reversal" for c in result)

    def test_contradiction_mixed_input_produces_same_result(self):
        """Dict and Pydantic object inputs for the same data should produce equal results."""
        affects = {"dead_battery": 0.30}
        log_dicts = [
            {"source": "intake", "observation": "won't start", "normalized_key": "x", "certainty": 1.0, "affects": affects},
            {"source": "image", "observation": "new battery", "normalized_key": "y", "certainty": 0.9, "affects": {"dead_battery": -0.30}},
        ]
        log_pydantic = [
            EvidencePacket(source="intake", observation="won't start", normalized_key="x", certainty=1.0, affects=affects),
            EvidencePacket(source="image", observation="new battery", normalized_key="y", certainty=0.9, affects={"dead_battery": -0.30}),
        ]
        result_dicts = detect_contradictions(log_dicts)
        result_pydantic = detect_contradictions(log_pydantic)
        assert len(result_dicts) == len(result_pydantic)
        assert {c.type for c in result_dicts} == {c.type for c in result_pydantic}

    # ── evidence type counting ──

    def test_evidence_type_count_distinct_sources(self):
        log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
            {"source": "user_text", "affects": {}},  # duplicate
            {"source": "image", "affects": {}},
        ]
        assert evidence_type_count(log) == 3

    def test_evidence_type_count_single_source(self):
        log = [{"source": "intake", "affects": {}}] * 5
        assert evidence_type_count(log) == 1

    def test_evidence_type_count_empty(self):
        assert evidence_type_count([]) == 0

    # ── safety deduplication ──

    def test_safety_dedupe_existing_message_not_repeated(self):
        existing = [{"level": "critical", "message": "Fuel leak or vapor detected.", "recommended_action": "Stop"}]
        alerts = evaluate_safety(["I can smell fuel leaking"], existing_safety_flags=existing)
        assert all(a.message != "Fuel leak or vapor detected." for a in alerts)

    def test_safety_dedupe_new_message_added(self):
        existing = [{"level": "critical", "message": "Fuel leak or vapor detected.", "recommended_action": "Stop"}]
        alerts = evaluate_safety(["There is smoke coming from under the hood"], existing_safety_flags=existing)
        # Smoke should fire a different alert (not already in existing)
        assert len(alerts) > 0

    def test_safety_returns_pydantic_alerts(self):
        alerts = evaluate_safety(["Fuel is leaking from the engine"])
        assert all(isinstance(a, SafetyAlert) for a in alerts)
        assert all(hasattr(a, "to_dict") for a in alerts)

    # ── session serialization path ──

    def test_evidence_packet_stores_and_recovers_as_dict_in_session(self):
        packet = build_from_classification(
            option_key="no_crank",
            option_label="Nothing happens",
            deltas={"dead_battery": 0.2},
            answer_reliability=0.85,
            user_text="Nothing happens when I turn the key",
        )
        d = packet.to_dict()
        assert isinstance(d, dict)
        assert d["source"] == "user_text"
        recovered = EvidencePacket.from_dict(d)
        assert recovered.affects == packet.affects
        assert recovered.certainty == pytest.approx(0.85)

    def test_safety_alert_dict_in_session_has_critical_alert(self):
        from fix_core.orchestrator.safety import has_critical_alert
        alerts = evaluate_safety(["Fuel is leaking from the engine"])
        safety_flags = [a.to_dict() for a in alerts]
        assert has_critical_alert(safety_flags) is True

    def test_contradiction_merge_deduplicates(self):
        c = Contradiction(type="score_reversal", description="conflict on dead_battery", severity=0.6)
        existing = [c.to_dict()]
        merged = merge_flags(existing, [c])
        assert len(merged) == 1


# ── 5. Heavy equipment subtype tests ──────────────────────────────────────────

class TestHESubtypes:

    _ALL_HE_SUBTYPES = ["heavy_equipment", "excavator", "tractor", "loader", "skid_steer"]

    def test_all_he_subtypes_produce_heavy_context(self):
        for subtype in self._ALL_HE_SUBTYPES:
            result = heavy_context_from_intake({
                "vehicle_type": subtype,
                "heavy_context": {"hours_of_operation": 500, "last_service_hours": 200},
            })
            assert result is not None, f"{subtype} should produce HeavyContext"

    def test_heavy_context_hours_preserved(self):
        for subtype in self._ALL_HE_SUBTYPES:
            result = heavy_context_from_intake({
                "vehicle_type": subtype,
                "heavy_context": {"hours_of_operation": 1000, "last_service_hours": 750},
            })
            assert result.hours_of_operation == 1000
            assert result.last_service_hours == 750

    def test_non_he_vehicle_types_return_none(self):
        for vtype in ["car", "truck", "motorcycle", "boat", "generator", "atv", "pwc", "rv"]:
            result = heavy_context_from_intake({"vehicle_type": vtype})
            assert result is None, f"{vtype} should not produce HeavyContext"

    def test_he_vehicle_types_set_contains_all_subtypes(self):
        expected = {"heavy_equipment", "excavator", "tractor", "loader", "skid_steer"}
        assert expected.issubset(_HE_VEHICLE_TYPES)

    def test_he_vehicle_types_set_excludes_passenger(self):
        assert "car" not in _HE_VEHICLE_TYPES
        assert "motorcycle" not in _HE_VEHICLE_TYPES

    def test_dozer_in_he_vehicle_types(self):
        """Extra subtypes added in M3 are present."""
        assert "dozer" in _HE_VEHICLE_TYPES

    def test_missing_heavy_context_key_defaults_gracefully(self):
        result = heavy_context_from_intake({"vehicle_type": "excavator"})
        assert result is not None
        assert result.hours_of_operation == 0
        assert result.last_service_hours == 0

    def test_apply_priors_for_overdue_service(self):
        he_trees = [k for k in TREES if "heavy_equipment" in k]
        if not he_trees:
            pytest.skip("No heavy_equipment trees found")
        ctx = HeavyContext(hours_of_operation=600, last_service_hours=100)  # 500h overdue
        result = apply_heavy_context_priors(ctx, he_trees[0])
        assert isinstance(result, dict)

    def test_apply_priors_empty_for_unknown_tree(self):
        ctx = HeavyContext(hours_of_operation=100, last_service_hours=50)
        result = apply_heavy_context_priors(ctx, "totally_unknown_tree")
        assert result == {}

    @pytest.mark.parametrize("subtype", ["excavator", "tractor", "loader", "skid_steer"])
    def test_subtype_specific_tree_exists(self, subtype: str):
        from fix_core.trees import resolve_tree_key
        # Each subtype should resolve to a specific no_start tree
        result = resolve_tree_key("no_start", subtype)
        assert result in TREES, f"Expected no_start_{subtype} to exist in TREES"


# ── 6. Full DiagnosticSession aggregate persistence shape ─────────────────────

class TestSessionPersistenceShape:

    def _make_full_session(self) -> DiagnosticSession:
        sid = uuid4()
        uid = uuid4()
        now = _now()

        return DiagnosticSession(
            id=sid,
            owner=OwnerContext(user_id=uid, org_id=uuid4(), source="standalone"),
            created_at=now,
            updated_at=now,
            status=SessionState.completed,
            session_mode=SessionMode.operator,
            turn_count=5,
            answered_nodes=4,
            vehicle_type="excavator",
            vehicle_year=2019,
            vehicle_make="Caterpillar",
            symptom_category="hydraulic_loss",
            initial_description="No lift power on bucket",
            selected_tree="hydraulic_loss_excavator",
            evidence_log=[
                {"source": "intake", "observation": "no lift", "normalized_key": "intake_description", "certainty": 1.0, "affects": {}},
                {"source": "user_text", "observation": "pump noisy", "normalized_key": "pump_noise", "certainty": 0.8, "affects": {"failed_hydraulic_pump": 0.2}},
                {"source": "image", "observation": "hose sweat", "normalized_key": "image_analysis", "certainty": 0.75, "affects": {"leaking_hose_fitting": 0.15}},
            ],
            safety_flags=[{"level": "warning", "message": "Low hydraulic fluid level detected.", "recommended_action": "Check fluid"}],
            contradiction_flags=[],
            hypotheses=[
                HypothesisScore(key="failed_hydraulic_pump", label="Failed pump", score=0.78),
                HypothesisScore(key="clogged_filter", label="Clogged filter", score=0.35, eliminated=False),
                HypothesisScore(key="leaking_hose_fitting", label="Leaking hose", score=0.25),
            ],
            messages=[
                SessionMessage(
                    id=uuid4(), session_id=sid, created_at=now,
                    role=MessageRole.user, content="No lift power",
                    msg_type=MessageType.chat,
                ),
                SessionMessage(
                    id=uuid4(), session_id=sid, created_at=now,
                    role=MessageRole.assistant, content="I'll help diagnose that.",
                    msg_type=MessageType.chat,
                ),
            ],
            result=DiagnosticResult(
                id=uuid4(),
                session_id=sid,
                created_at=now,
                ranked_causes=[
                    RankedCause(hypothesis_key="failed_hydraulic_pump", label="Failed pump", score=0.78),
                ],
                next_checks=["Check pump output pressure"],
                confidence_level=0.78,
            ),
            media=[
                MediaReference(
                    storage_path="/uploads/excavator-hose.jpg",
                    filename="excavator-hose.jpg",
                    media_type="image/jpeg",
                    uploaded_at=now,
                ),
            ],
        )

    def test_full_session_roundtrip(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.id == session.id

    def test_answered_nodes_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.answered_nodes == 4

    def test_evidence_log_shape_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert len(session2.evidence_log) == 3
        assert all(isinstance(e, dict) for e in session2.evidence_log)
        assert session2.evidence_log[0]["source"] == "intake"

    def test_hypotheses_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert len(session2.hypotheses) == 3
        scores = {h.key: h.score for h in session2.hypotheses}
        assert scores["failed_hydraulic_pump"] == pytest.approx(0.78)

    def test_safety_flags_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert len(session2.safety_flags) == 1
        assert session2.safety_flags[0]["level"] == "warning"

    def test_messages_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert len(session2.messages) == 2
        assert session2.messages[0].content == "No lift power"

    def test_media_references_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert len(session2.media) == 1
        assert session2.media[0].storage_path == "/uploads/excavator-hose.jpg"

    def test_result_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.result is not None
        assert session2.result.ranked_causes[0].hypothesis_key == "failed_hydraulic_pump"
        assert session2.result.confidence_level == pytest.approx(0.78)

    def test_owner_context_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.owner.user_id == session.owner.user_id
        assert session2.owner.source == "standalone"

    def test_session_mode_preserved(self):
        session = self._make_full_session()
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)
        assert session2.session_mode == SessionMode.operator

    def test_dict_is_json_serializable(self):
        """model_dump() output must be JSON-serializable (no UUID/datetime objects)."""
        import json
        session = self._make_full_session()
        d = session.model_dump(mode="json")
        # Should not raise
        json_str = json.dumps(d)
        assert len(json_str) > 0

    def test_scorer_conversion_persisted_in_session(self):
        """Full scorer → session → restored scorer cycle."""
        hyp_def = {
            "failed_hydraulic_pump": {"label": "Failed pump", "prior": 0.4},
            "clogged_filter": {"label": "Clogged filter", "prior": 0.3},
            "leaking_hose_fitting": {"label": "Leaking hose", "prior": 0.2},
        }
        scorer = HypothesisScorer(hyp_def)
        scorer.apply_option({"deltas": {"failed_hydraulic_pump": 0.35}, "eliminate": []}, "Pressure test?", "Low output")

        # Simulate storing in session
        session = _make_session(hypotheses=scorer.to_hypothesis_scores())
        d = session.model_dump()
        session2 = DiagnosticSession.model_validate(d)

        # Restore scorer from session
        restored = HypothesisScorer.from_hypothesis_scores(hyp_def, session2.hypotheses)
        assert restored.top_confidence() == pytest.approx(scorer.top_confidence())
        assert restored.ranked()[0].key == "failed_hydraulic_pump"
