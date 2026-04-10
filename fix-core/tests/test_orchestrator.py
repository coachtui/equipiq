"""
Phase M2 unit tests — fix_core.orchestrator
"""
import pytest

from fix_core.orchestrator.evidence import (
    EvidencePacket,
    build_from_classification,
    build_from_image,
    build_from_followup,
    build_intake_packet,
    evidence_type_count,
    scale_affects,
)
from fix_core.orchestrator.safety import SafetyAlert, evaluate_safety, has_critical_alert
from fix_core.orchestrator.contradictions import (
    Contradiction,
    detect_contradictions,
    merge_flags,
)
from fix_core.orchestrator.tree_router import (
    TreeCandidate,
    rank_candidate_trees,
    should_use_discriminator,
    combine_candidates,
)
from fix_core.orchestrator.discriminator import (
    get_discriminator_questions,
    resolve_discriminator_answer,
)
from fix_core.orchestrator.exit_guard import can_exit, exit_reason
from fix_core.engine.hypothesis_scorer import HypothesisScorer


# ── Evidence ──────────────────────────────────────────────────────────────────

class TestEvidence:
    def test_build_from_classification(self):
        p = build_from_classification(
            option_key="yes",
            option_label="Yes",
            deltas={"dead_battery": 0.2},
            answer_reliability=0.85,
            user_text="Yes it clicks",
        )
        assert p.source == "user_text"
        assert p.normalized_key == "yes"
        assert p.certainty == pytest.approx(0.85)
        assert p.affects["dead_battery"] == pytest.approx(0.2)

    def test_scale_affects(self):
        p = EvidencePacket(
            source="user_text",
            observation="test",
            normalized_key="k",
            certainty=0.5,
            affects={"h1": 0.4, "h2": -0.2},
        )
        scaled = scale_affects(p)
        assert scaled["h1"] == pytest.approx(0.2)
        assert scaled["h2"] == pytest.approx(-0.1)

    def test_build_from_image(self):
        p = build_from_image(
            interpretation="Leaking coolant hose visible",
            score_deltas={"coolant_leak": 0.3},
            confidence_modifier=0.7,
        )
        assert p.source == "image"
        assert p.normalized_key == "image_analysis"

    def test_build_intake_packet(self):
        p = build_intake_packet("Engine won't start", {"dead_battery": 0.1})
        assert p.source == "intake"
        assert p.certainty == 1.0

    def test_evidence_type_count(self):
        log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
            {"source": "user_text", "affects": {}},  # duplicate type
            {"source": "image", "affects": {}},
        ]
        assert evidence_type_count(log) == 3

    def test_roundtrip_via_dict(self):
        p = build_from_followup(
            interpretation="Checked battery — it was dead",
            score_deltas={"dead_battery": 0.3},
            user_text="I checked the battery and it was dead",
        )
        d = p.to_dict()
        p2 = EvidencePacket.from_dict(d)
        assert p2.source == p.source
        assert p2.affects == p.affects


# ── Safety ────────────────────────────────────────────────────────────────────

class TestSafety:
    def test_fuel_leak_triggers_critical(self):
        alerts = evaluate_safety(["I can smell fuel leaking from the engine"])
        assert len(alerts) > 0
        assert any(a.level == "critical" for a in alerts)

    def test_safe_input_no_alerts(self):
        alerts = evaluate_safety(["The engine is making a ticking noise at idle"])
        assert alerts == []

    def test_smoke_triggers_warning_or_critical(self):
        alerts = evaluate_safety(["There is smoke coming from under the hood"])
        assert len(alerts) > 0

    def test_has_critical_alert_true(self):
        flags = [{"level": "critical", "message": "Fuel leak"}]
        assert has_critical_alert(flags) is True

    def test_has_critical_alert_false(self):
        flags = [{"level": "warning", "message": "Elevated temp"}]
        assert has_critical_alert(flags) is False

    def test_has_critical_alert_empty(self):
        assert has_critical_alert([]) is False


# ── Contradictions ────────────────────────────────────────────────────────────

class TestContradictions:
    def test_no_contradictions_simple_log(self):
        log = [
            {"source": "intake", "observation": "won't start", "affects": {"dead_battery": 0.2}},
            {"source": "user_text", "observation": "clicks", "affects": {"dead_battery": 0.15}},
        ]
        result = detect_contradictions(log)
        assert result == []

    def test_score_reversal_detected(self):
        # Strongly support then strongly contradict the same hypothesis
        log = [
            {"source": "intake", "affects": {"dead_battery": 0.30}},
            {"source": "user_text", "affects": {"dead_battery": 0.25}},
            {"source": "image", "affects": {"dead_battery": -0.30}},
            {"source": "manual_test", "affects": {"dead_battery": -0.25}},
        ]
        result = detect_contradictions(log)
        types = [c.type for c in result]
        assert "score_reversal" in types

    def test_contradiction_severity_in_range(self):
        log = [
            {"source": "intake", "affects": {"x": 0.30}},
            {"source": "image", "affects": {"x": -0.30}},
        ]
        result = detect_contradictions(log)
        for c in result:
            assert 0.0 <= c.severity <= 1.0

    def test_merge_flags_deduplicates(self):
        c = Contradiction(type="score_reversal", description="dup", severity=0.5)
        existing = [c.to_dict()]
        merged = merge_flags(existing, [c])
        assert len(merged) == 1  # not duplicated


# ── Tree Router ───────────────────────────────────────────────────────────────

class TestTreeRouter:
    def test_rank_returns_candidates(self):
        intake = {"symptom_category": "no_crank", "vehicle_type": "car"}
        candidates = rank_candidate_trees(intake)
        assert len(candidates) >= 1
        assert candidates[0].tree_id == "no_crank"

    def test_vehicle_specific_tree_ranked_first(self):
        intake = {"symptom_category": "no_crank", "vehicle_type": "motorcycle"}
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "no_crank_motorcycle"

    def test_unknown_symptom_returns_empty(self):
        intake = {"symptom_category": "completely_unknown", "vehicle_type": "car"}
        candidates = rank_candidate_trees(intake)
        assert candidates == []

    def test_should_use_discriminator_false_when_one_candidate(self):
        candidates = [TreeCandidate("no_crank", 1.0, [])]
        assert should_use_discriminator(candidates) is False

    def test_should_use_discriminator_false_when_top_score_high(self):
        candidates = [
            TreeCandidate("no_crank", 0.95, []),
            TreeCandidate("crank_no_start", 0.60, []),
        ]
        assert should_use_discriminator(candidates) is False

    def test_should_use_discriminator_true_when_ambiguous(self):
        candidates = [
            TreeCandidate("no_crank", 0.75, []),
            TreeCandidate("crank_no_start", 0.60, []),
        ]
        assert should_use_discriminator(candidates) is True

    def test_combine_candidates_preserves_primary(self):
        deterministic = [
            TreeCandidate("no_crank", 0.80, ["primary"]),
            TreeCandidate("crank_no_start", 0.60, ["secondary"]),
        ]
        llm_hints = [{"tree_id": "crank_no_start", "confidence": 0.9, "reasoning": "LLM says so"}]
        combined = combine_candidates(deterministic, llm_hints)
        assert combined[0].tree_id == "no_crank"


# ── Discriminator ─────────────────────────────────────────────────────────────

class TestDiscriminator:
    def test_no_questions_for_single_candidate(self):
        candidates = [TreeCandidate("no_crank", 1.0, [])]
        assert get_discriminator_questions(candidates) == []

    def test_questions_for_known_ambiguous_pair(self):
        candidates = [
            TreeCandidate("no_crank", 0.80, []),
            TreeCandidate("crank_no_start", 0.60, []),
        ]
        questions = get_discriminator_questions(candidates)
        assert len(questions) > 0
        assert questions[0].question != ""

    def test_resolve_answer_cranks_commits_to_crank_no_start(self):
        candidates = [
            TreeCandidate("no_crank", 0.80, []),
            TreeCandidate("crank_no_start", 0.60, []),
        ]
        questions = get_discriminator_questions(candidates)
        assert len(questions) > 0
        committed = resolve_discriminator_answer(
            questions[0], "It cranks and turns over but won't fire", candidates
        )
        assert "crank_no_start" in committed

    def test_resolve_answer_silent_commits_to_no_crank(self):
        candidates = [
            TreeCandidate("no_crank", 0.80, []),
            TreeCandidate("crank_no_start", 0.60, []),
        ]
        questions = get_discriminator_questions(candidates)
        committed = resolve_discriminator_answer(
            questions[0], "Nothing happens — complete silence", candidates
        )
        assert "no_crank" in committed


# ── Exit Guard ────────────────────────────────────────────────────────────────

class TestExitGuard:
    def _make_high_confidence_scorer(self) -> HypothesisScorer:
        hyp_def = {
            "dead_battery": {"label": "Dead battery", "prior": 0.9},
            "starter_motor": {"label": "Starter", "prior": 0.1},
        }
        return HypothesisScorer(hyp_def)

    def test_exit_blocked_insufficient_nodes(self):
        scorer = self._make_high_confidence_scorer()
        evidence_log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
        ]
        # Only 2 answered nodes — MIN_NODES is 3
        assert can_exit(scorer, answered_nodes=2, evidence_log=evidence_log, contradiction_flags=[]) is False

    def test_exit_blocked_insufficient_evidence_types(self):
        scorer = self._make_high_confidence_scorer()
        evidence_log = [
            {"source": "intake", "affects": {}},
            {"source": "intake", "affects": {}},  # same type, only 1 distinct
        ]
        assert can_exit(scorer, answered_nodes=5, evidence_log=evidence_log, contradiction_flags=[]) is False

    def test_exit_blocked_by_contradiction(self):
        scorer = self._make_high_confidence_scorer()
        evidence_log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
        ]
        contradiction_flags = [{"severity": 0.7, "description": "conflict"}]
        assert can_exit(scorer, answered_nodes=5, evidence_log=evidence_log, contradiction_flags=contradiction_flags) is False

    def test_exit_allowed_all_conditions_met(self):
        scorer = self._make_high_confidence_scorer()
        evidence_log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
        ]
        # 3+ nodes, 2 evidence types, no blocking contradictions, high scorer scores
        assert can_exit(scorer, answered_nodes=4, evidence_log=evidence_log, contradiction_flags=[]) is True

    def test_exit_reason_returns_string_when_blocked(self):
        scorer = self._make_high_confidence_scorer()
        reason = exit_reason(scorer, answered_nodes=1, evidence_log=[], contradiction_flags=[])
        assert reason is not None
        assert isinstance(reason, str)

    def test_exit_reason_none_when_allowed(self):
        scorer = self._make_high_confidence_scorer()
        evidence_log = [
            {"source": "intake", "affects": {}},
            {"source": "user_text", "affects": {}},
        ]
        reason = exit_reason(scorer, answered_nodes=4, evidence_log=evidence_log, contradiction_flags=[])
        assert reason is None
