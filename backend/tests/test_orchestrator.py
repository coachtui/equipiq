"""
Phase 9 Orchestration Layer — unit tests.

Run with: pytest backend/tests/test_orchestrator.py -v

Tests cover:
  1. Misclassification recovery (wrong initial tree → corrected via discriminator)
  2. Early exit blocked due to insufficient evidence
  3. Contradiction detection triggers clarification
  4. Safety alert interrupts flow (critical)
  5. Evidence packets properly update scores
  6. Discriminator question resolution
  7. Tree candidate ranking
  8. Answer reliability scaling
"""
import pytest

from app.diagnostics.orchestrator.contradictions import Contradiction, detect_contradictions, merge_flags
from app.diagnostics.orchestrator.discriminator import (
    DiscriminatorQuestion,
    get_discriminator_questions,
    resolve_discriminator_answer,
)
from app.diagnostics.orchestrator.evidence import (
    EvidencePacket,
    build_from_classification,
    build_from_image,
    build_from_followup,
    build_intake_packet,
    evidence_type_count,
    scale_affects,
)
from app.diagnostics.orchestrator.exit_guard import MIN_NODES, can_exit, exit_reason
from app.diagnostics.orchestrator.safety import SafetyAlert, evaluate_safety
from app.diagnostics.orchestrator.tree_router import (
    TreeCandidate,
    rank_candidate_trees,
    should_use_discriminator,
)
from app.engine.hypothesis_scorer import Hypothesis, HypothesisScorer


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_scorer(scores: dict[str, float]) -> HypothesisScorer:
    """Build a minimal scorer from a {key: score} dict."""
    hyp_def = {k: {"label": k, "prior": v} for k, v in scores.items()}
    return HypothesisScorer(hyp_def)


def _evidence_log(*sources: str) -> list[dict]:
    """Quick helper: build a minimal evidence log with given source types."""
    return [{"source": s, "observation": s, "normalized_key": s, "certainty": 1.0, "affects": {}} for s in sources]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tree candidate ranking & misclassification recovery
# ─────────────────────────────────────────────────────────────────────────────

class TestTreeRouter:
    def test_primary_candidate_selected_for_known_vehicle(self):
        intake = {"symptom_category": "no_crank", "vehicle_type": "car", "vehicle_make": "Toyota"}
        candidates = rank_candidate_trees(intake)
        assert len(candidates) >= 1
        assert candidates[0].tree_id == "no_crank"
        assert candidates[0].score >= 0.90

    def test_vehicle_specific_tree_selected(self):
        intake = {"symptom_category": "no_crank", "vehicle_type": "motorcycle", "vehicle_make": "Honda"}
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "no_crank_motorcycle"

    def test_secondary_symptom_adds_candidate(self):
        intake = {
            "symptom_category": "no_crank",
            "vehicle_type": "car",
            "vehicle_make": "Ford",
            "secondary_symptom": "crank_no_start",
        }
        candidates = rank_candidate_trees(intake)
        tree_ids = [c.tree_id for c in candidates]
        assert "no_crank" in tree_ids
        assert "crank_no_start" in tree_ids

    def test_primary_score_penalised_with_secondary(self):
        intake_with = {"symptom_category": "no_crank", "vehicle_type": "car", "vehicle_make": "Ford", "secondary_symptom": "crank_no_start"}
        intake_without = {"symptom_category": "no_crank", "vehicle_type": "car", "vehicle_make": "Ford"}
        with_sec = rank_candidate_trees(intake_with)
        without_sec = rank_candidate_trees(intake_without)
        assert with_sec[0].score < without_sec[0].score

    def test_no_discriminator_for_clear_intake(self):
        intake = {"symptom_category": "overheating", "vehicle_type": "boat", "vehicle_make": "Sea Ray"}
        candidates = rank_candidate_trees(intake)
        assert not should_use_discriminator(candidates)

    def test_discriminator_triggered_for_ambiguous_vehicle(self):
        intake = {"symptom_category": "no_crank", "vehicle_type": "other", "secondary_symptom": "crank_no_start"}
        candidates = rank_candidate_trees(intake)
        assert should_use_discriminator(candidates)

    def test_empty_for_unknown_symptom(self):
        intake = {"symptom_category": "unknown", "vehicle_type": "car"}
        candidates = rank_candidate_trees(intake)
        assert candidates == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. Discriminator question resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscriminator:
    def _make_candidates(self, tree_a: str, tree_b: str) -> list[TreeCandidate]:
        return [
            TreeCandidate(tree_id=tree_a, score=0.75, reasons=["primary"]),
            TreeCandidate(tree_id=tree_b, score=0.45, reasons=["secondary"]),
        ]

    def test_questions_generated_for_known_pair(self):
        candidates = self._make_candidates("no_crank", "crank_no_start")
        questions = get_discriminator_questions(candidates)
        assert len(questions) >= 1
        assert "crank" in questions[0].question.lower()

    def test_answer_commits_to_correct_tree_cranks(self):
        candidates = self._make_candidates("no_crank", "crank_no_start")
        questions = get_discriminator_questions(candidates)
        committed = resolve_discriminator_answer(questions[0], "it cranks but won't start", candidates)
        assert committed == "crank_no_start"

    def test_answer_commits_to_correct_tree_silent(self):
        candidates = self._make_candidates("no_crank", "crank_no_start")
        questions = get_discriminator_questions(candidates)
        committed = resolve_discriminator_answer(questions[0], "completely silent, nothing happens", candidates)
        assert committed == "no_crank"

    def test_fallback_to_primary_for_unknown_answer(self):
        candidates = self._make_candidates("no_crank", "crank_no_start")
        questions = get_discriminator_questions(candidates)
        committed = resolve_discriminator_answer(questions[0], "I don't know", candidates)
        assert committed == "no_crank"  # primary (first) candidate

    def test_generic_fallback_question_for_unknown_pair(self):
        candidates = self._make_candidates("check_engine_light", "hvac")
        questions = get_discriminator_questions(candidates)
        assert len(questions) == 1
        assert "check engine light" in questions[0].question.lower() or "hvac" in questions[0].question.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Evidence packets
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidence:
    def test_build_from_classification(self):
        packet = build_from_classification(
            option_key="cranks_ok",
            option_label="Engine cranks normally",
            deltas={"dead_battery": -0.30, "fuel_issue": 0.15},
            answer_reliability=0.9,
            user_text="yeah it cranks fine",
        )
        assert packet.source == "user_text"
        assert packet.certainty == 0.9
        assert packet.affects["dead_battery"] == -0.30

    def test_scale_affects_by_certainty(self):
        packet = EvidencePacket(
            source="user_text",
            observation="vague answer",
            normalized_key="q1",
            certainty=0.4,
            affects={"dead_battery": 0.20},
        )
        scaled = scale_affects(packet)
        assert abs(scaled["dead_battery"] - 0.08) < 0.001

    def test_build_from_image(self):
        packet = build_from_image(
            interpretation="Corroded battery terminals visible",
            score_deltas={"battery_corrosion": 0.25},
            confidence_modifier=0.8,
        )
        assert packet.source == "image"
        assert packet.certainty == 0.8

    def test_evidence_type_count(self):
        log = _evidence_log("intake", "user_text", "user_text", "image")
        assert evidence_type_count(log) == 3  # intake, user_text, image

    def test_evidence_serialisation_roundtrip(self):
        original = build_from_followup(
            interpretation="Battery voltage confirmed low",
            score_deltas={"dead_battery": 0.30},
            user_text="I tested it and it's 11.2 volts",
        )
        restored = EvidencePacket.from_dict(original.to_dict())
        assert restored.source == original.source
        assert restored.affects == original.affects


# ─────────────────────────────────────────────────────────────────────────────
# 4. Early exit guard — exit blocked
# ─────────────────────────────────────────────────────────────────────────────

class TestExitGuard:
    def _passing_scorer(self) -> HypothesisScorer:
        return _make_scorer({"dead_battery": 0.80, "faulty_starter": 0.55, "other": 0.10})

    def test_exit_allowed_when_all_conditions_met(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("intake", "user_text")
        assert can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=[])

    def test_exit_blocked_insufficient_nodes(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=2, evidence_log=evidence, contradiction_flags=[])

    def test_exit_blocked_insufficient_evidence_types(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("user_text")  # only 1 type
        assert not can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=[])

    def test_exit_blocked_low_top_score(self):
        scorer = _make_scorer({"dead_battery": 0.60, "faulty_starter": 0.40})
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=[])

    def test_exit_blocked_insufficient_lead(self):
        scorer = _make_scorer({"dead_battery": 0.76, "faulty_starter": 0.72})  # lead = 0.04
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=[])

    def test_exit_blocked_active_contradiction(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("intake", "user_text")
        contradictions = [{"type": "score_reversal", "description": "conflict", "severity": 0.7}]
        assert not can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=contradictions)

    def test_exit_allowed_with_low_severity_contradiction(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("intake", "user_text")
        # Severity below CONTRADICTION_BLOCK_SEVERITY (0.5)
        contradictions = [{"type": "score_reversal", "description": "minor", "severity": 0.3}]
        assert can_exit(scorer, answered_nodes=3, evidence_log=evidence, contradiction_flags=contradictions)

    def test_exit_reason_reports_blocking_condition(self):
        scorer = self._passing_scorer()
        evidence = _evidence_log("intake", "user_text")
        reason = exit_reason(scorer, answered_nodes=1, evidence_log=evidence, contradiction_flags=[])
        assert reason is not None
        assert "1" in reason  # mentions node count


# ─────────────────────────────────────────────────────────────────────────────
# 5. Contradiction detection
# ─────────────────────────────────────────────────────────────────────────────

class TestContradictions:
    def test_score_reversal_detected(self):
        evidence = [
            {"source": "user_text", "observation": "a", "normalized_key": "q1", "certainty": 1.0,
             "affects": {"dead_battery": 0.25}},
            {"source": "manual_test", "observation": "b", "normalized_key": "q2", "certainty": 1.0,
             "affects": {"dead_battery": -0.30}},
        ]
        contradictions = detect_contradictions(evidence)
        assert any(c.type == "score_reversal" for c in contradictions)

    def test_no_contradiction_for_consistent_evidence(self):
        evidence = [
            {"source": "user_text", "observation": "a", "normalized_key": "q1", "certainty": 1.0,
             "affects": {"dead_battery": 0.20}},
            {"source": "user_text", "observation": "b", "normalized_key": "q2", "certainty": 1.0,
             "affects": {"dead_battery": 0.15}},
        ]
        contradictions = detect_contradictions(evidence)
        assert not any(c.type == "score_reversal" for c in contradictions)

    def test_image_vs_verbal_conflict_detected(self):
        evidence = [
            {"source": "user_text", "observation": "battery is fine", "normalized_key": "q1",
             "certainty": 1.0, "affects": {"dead_battery": -0.25}},
            {"source": "image", "observation": "corroded terminals", "normalized_key": "img",
             "certainty": 0.8, "affects": {"dead_battery": 0.30}},
        ]
        contradictions = detect_contradictions(evidence)
        types = [c.type for c in contradictions]
        assert "image_vs_verbal" in types

    def test_eliminated_hypothesis_boost_detected(self):
        evidence = [
            {"source": "manual_test", "observation": "battery tested good", "normalized_key": "q1",
             "certainty": 1.0, "affects": {"dead_battery": 0.35}},
        ]
        hyp_state = {"dead_battery": {"score": 0.0, "eliminated": True}}
        contradictions = detect_contradictions(evidence, current_hypotheses=hyp_state)
        assert any(c.type == "eliminated_boost" for c in contradictions)

    def test_merge_flags_no_duplicates(self):
        existing = [{"type": "score_reversal", "description": "existing conflict", "severity": 0.6}]
        new_contradiction = Contradiction(type="score_reversal", description="existing conflict", severity=0.6)
        merged = merge_flags(existing, [new_contradiction])
        assert len(merged) == 1  # no duplicate


# ─────────────────────────────────────────────────────────────────────────────
# 6. Safety alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestSafety:
    def test_fuel_leak_triggers_critical(self):
        alerts = evaluate_safety(["there's a gasoline leak under the car"])
        assert any(a.level == "critical" for a in alerts)

    def test_fire_triggers_critical(self):
        alerts = evaluate_safety(["flames are coming from under the hood"])
        assert any(a.level == "critical" for a in alerts)

    def test_overheating_with_steam_triggers_critical(self):
        alerts = evaluate_safety(["steam coming from overheating engine"])
        assert any(a.level == "critical" for a in alerts)

    def test_brake_failure_triggers_critical(self):
        alerts = evaluate_safety(["brakes failed completely"])
        assert any(a.level == "critical" for a in alerts)

    def test_overheating_alone_triggers_warning(self):
        alerts = evaluate_safety(["temperature gauge is in the red, engine overheating"])
        levels = {a.level for a in alerts}
        assert "warning" in levels
        assert "critical" not in levels

    def test_normal_text_no_alerts(self):
        alerts = evaluate_safety(["car won't start, engine cranks but doesn't fire"])
        assert alerts == []

    def test_existing_alerts_not_duplicated(self):
        first = evaluate_safety(["fuel is leaking"])
        assert len(first) >= 1
        second = evaluate_safety(["fuel is leaking"], existing_safety_flags=[a.to_dict() for a in first])
        assert second == []

    def test_electrical_smoke_triggers_critical(self):
        alerts = evaluate_safety(["smoke coming from the wiring harness"])
        assert any(a.level == "critical" for a in alerts)

    def test_critical_sorted_before_warning(self):
        alerts = evaluate_safety([
            "engine is overheating and there is fire coming from under the hood"
        ])
        if len(alerts) >= 2:
            assert alerts[0].level == "critical"

    def test_safety_alert_serialisation(self):
        alert = SafetyAlert(
            level="critical",
            message="Fuel leak detected.",
            recommended_action="Stop driving immediately.",
        )
        d = alert.to_dict()
        assert d["level"] == "critical"
        assert "Fuel leak" in d["message"]
