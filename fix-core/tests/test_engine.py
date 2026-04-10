"""
Phase M2 unit tests — fix_core.engine

Tests run directly against fix_core imports. No database, no FastAPI, no Anthropic SDK.
"""
import pytest

from fix_core.engine.hypothesis_scorer import Hypothesis, HypothesisScorer
from fix_core.engine.diagnostic_engine import DiagnosticEngine
from fix_core.engine.context_heavy import (
    HeavyContext,
    apply_heavy_context_priors,
    heavy_context_from_intake,
)
from fix_core.trees import TREES, HYPOTHESES, CONTEXT_PRIORS, resolve_tree_key


# ── HypothesisScorer ──────────────────────────────────────────────────────────

class TestHypothesisScorer:
    def _make_scorer(self) -> HypothesisScorer:
        hyp_def = {
            "dead_battery": {"label": "Dead battery", "prior": 0.4},
            "starter_motor": {"label": "Starter motor failure", "prior": 0.3},
            "bad_ground":   {"label": "Bad ground connection", "prior": 0.2},
        }
        return HypothesisScorer(hyp_def)

    def test_initial_scores(self):
        scorer = self._make_scorer()
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(0.4)
        assert scorer.hypotheses["starter_motor"].score == pytest.approx(0.3)

    def test_score_clamped_at_one(self):
        scorer = self._make_scorer()
        option = {"deltas": {"dead_battery": 2.0}, "eliminate": []}
        scorer.apply_option(option, "Does it crank?", "No")
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(1.0)

    def test_score_clamped_at_zero(self):
        scorer = self._make_scorer()
        option = {"deltas": {"dead_battery": -5.0}, "eliminate": []}
        scorer.apply_option(option, "Does it crank?", "Yes")
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(0.0)

    def test_eliminate(self):
        scorer = self._make_scorer()
        option = {"deltas": {}, "eliminate": ["dead_battery"]}
        scorer.apply_option(option, "Battery voltage?", "13.2V")
        assert scorer.hypotheses["dead_battery"].eliminated is True
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(0.0)

    def test_ranked_excludes_eliminated(self):
        scorer = self._make_scorer()
        option = {"deltas": {}, "eliminate": ["dead_battery"]}
        scorer.apply_option(option, "q", "a")
        ranked = scorer.ranked()
        keys = [h.key for h in ranked]
        assert "dead_battery" not in keys

    def test_top_confidence(self):
        scorer = self._make_scorer()
        assert scorer.top_confidence() == pytest.approx(0.4)

    def test_early_exit_not_triggered_at_default_threshold(self):
        scorer = self._make_scorer()
        # Prior scores are 0.4, 0.3, 0.2 — not enough for early exit
        assert scorer.should_exit_early() is False

    def test_early_exit_triggered(self):
        scorer = self._make_scorer()
        option = {"deltas": {"dead_battery": 0.50}, "eliminate": []}
        scorer.apply_option(option, "q", "a")
        # dead_battery now 0.9, lead over starter_motor (0.3) = 0.6 → threshold met
        assert scorer.should_exit_early() is True

    def test_weight_multiplier_applied_at_init(self):
        hyp_def = {"a": {"label": "A", "prior": 0.5}}
        scorer = HypothesisScorer(hyp_def, weight_multipliers={"a": 1.5})
        # 0.5 × 1.5 = 0.75, clamped to [0,1]
        assert scorer.hypotheses["a"].score == pytest.approx(0.75)

    def test_weight_multiplier_clamped(self):
        hyp_def = {"a": {"label": "A", "prior": 0.8}}
        scorer = HypothesisScorer(hyp_def, weight_multipliers={"a": 2.0})
        # 0.8 × 2.0 = 1.6 → clamped to 1.0
        assert scorer.hypotheses["a"].score == pytest.approx(1.0)

    def test_serialization_roundtrip(self):
        scorer = self._make_scorer()
        option = {"deltas": {"dead_battery": 0.2}, "eliminate": ["bad_ground"]}
        scorer.apply_option(option, "q", "a")
        saved = scorer.to_serializable()

        scorer2 = HypothesisScorer.from_serializable(
            {"dead_battery": {"label": "Dead battery", "prior": 0.4},
             "starter_motor": {"label": "Starter motor failure", "prior": 0.3},
             "bad_ground": {"label": "Bad ground connection", "prior": 0.2}},
            saved,
        )
        assert scorer2.hypotheses["dead_battery"].score == pytest.approx(
            scorer.hypotheses["dead_battery"].score
        )
        assert scorer2.hypotheses["bad_ground"].eliminated is True


# ── DiagnosticEngine ──────────────────────────────────────────────────────────

class TestDiagnosticEngine:
    def test_invalid_tree_raises(self):
        with pytest.raises(ValueError, match="No diagnostic tree"):
            DiagnosticEngine("not_a_real_tree")

    def test_loads_known_tree(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        assert engine.tree_key == key

    def test_first_node_is_start(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        assert engine.first_node() == "start"

    def test_get_node_returns_dict(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        node = engine.get_node("start")
        assert node is not None
        assert "question" in node
        assert "options" in node

    def test_option_labels_non_empty(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        labels = engine.option_labels("start")
        assert len(labels) > 0

    def test_classify_answer_by_option_key(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        node = engine.get_node("start")
        first_option = node["options"][0]
        match_key = first_option["match"]
        result = engine.classify_answer("start", "anything", matched_option_key=match_key)
        assert result is not None
        assert result["match"] == match_key

    def test_classify_answer_digit_fallback(self):
        key = next(iter(TREES))
        engine = DiagnosticEngine(key)
        node = engine.get_node("start")
        result = engine.classify_answer("start", "1")
        assert result == node["options"][0]


# ── Trees ─────────────────────────────────────────────────────────────────────

class TestTrees:
    def test_tree_count(self):
        assert len(TREES) == 91

    def test_all_trees_have_start_node(self):
        missing = [k for k, v in TREES.items() if "start" not in v]
        assert missing == [], f"Trees missing start node: {missing}"

    def test_all_hypotheses_have_prior(self):
        for tree_key, hyps in HYPOTHESES.items():
            for hyp_key, hyp in hyps.items():
                assert "prior" in hyp, f"{tree_key}.{hyp_key} missing prior"
                assert 0.0 <= hyp["prior"] <= 1.0, (
                    f"{tree_key}.{hyp_key} prior {hyp['prior']} out of [0,1]"
                )

    def test_resolve_tree_key_exact_match(self):
        assert resolve_tree_key("no_crank", "car") == "no_crank"

    def test_resolve_tree_key_vehicle_specific(self):
        result = resolve_tree_key("no_crank", "motorcycle")
        assert result == "no_crank_motorcycle"

    def test_resolve_tree_key_he_fallback(self):
        # excavator-specific no_start tree may not exist; falls back to heavy_equipment
        result = resolve_tree_key("no_start", "excavator")
        assert result in TREES

    def test_resolve_tree_key_unknown_vehicle(self):
        # Unknown vehicle type falls back to base symptom tree
        result = resolve_tree_key("no_crank", "hovercraft")
        assert result == "no_crank"


# ── HeavyContext ───────────────────────────────────────────────────────────────

class TestHeavyContext:
    def test_apply_priors_returns_dict(self):
        ctx = HeavyContext(
            hours_of_operation=1000,
            last_service_hours=900,
            environment="dusty",
        )
        # Use a known heavy equipment tree key
        he_trees = [k for k in TREES if "heavy_equipment" in k or "excavator" in k]
        if he_trees:
            result = apply_heavy_context_priors(ctx, he_trees[0])
            assert isinstance(result, dict)

    def test_apply_priors_empty_for_unknown_tree(self):
        ctx = HeavyContext(hours_of_operation=100, last_service_hours=50)
        result = apply_heavy_context_priors(ctx, "nonexistent_tree")
        assert result == {}

    def test_heavy_context_from_intake_non_he(self):
        result = heavy_context_from_intake({"vehicle_type": "car"})
        assert result is None

    def test_heavy_context_from_intake_he(self):
        result = heavy_context_from_intake({
            "vehicle_type": "heavy_equipment",
            "heavy_context": {"hours_of_operation": 500, "last_service_hours": 250},
        })
        assert result is not None
        assert result.hours_of_operation == 500
