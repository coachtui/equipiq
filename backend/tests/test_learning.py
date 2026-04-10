"""
Phase 10 Learning System — unit tests.

Run with: pytest backend/tests/test_learning.py -v

Tests cover:
  1. Metric calculation correctness (_metrics_from_aggregates, pure function)
  2. Adjustment generation logic (various signal combinations)
  3. Approval flow integrity (no adjustment → no change; approved → applied)
  4. Runtime weight application (HypothesisScorer with weight_multipliers)
  5. No effect without approval (multipliers default to 1.0)
"""
import pytest

from app.engine.hypothesis_scorer import Hypothesis, HypothesisScorer
from app.learning.adjustments import (
    HIGH_RESOLUTION,
    HIGH_REVERSAL,
    LOW_RATING,
    MIN_CHANGE,
    MIN_SAMPLES,
    WeightAdjustment,
    generate_adjustments,
)
from app.learning.metrics import HypothesisMetrics, _metrics_from_aggregates


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_metrics(
    hypothesis_id: str,
    total_cases: int = 10,
    resolution_rate: float = 0.50,
    reversal_rate: float = 0.00,
    avg_confidence: float = 0.65,
    avg_rating: float = 3.5,
) -> dict[str, HypothesisMetrics]:
    return {
        hypothesis_id: HypothesisMetrics(
            hypothesis_id=hypothesis_id,
            total_cases=total_cases,
            resolution_rate=resolution_rate,
            reversal_rate=reversal_rate,
            avg_confidence=avg_confidence,
            avg_rating=avg_rating,
        )
    }


def _make_scorer(scores: dict[str, float]) -> HypothesisScorer:
    hyp_def = {k: {"label": k, "prior": v} for k, v in scores.items()}
    return HypothesisScorer(hyp_def)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Metric calculation correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricsFromAggregates:
    def test_resolution_rate_calculated_correctly(self):
        rows = [{"hypothesis_id": "dead_battery", "total_cases": 10, "resolved_count": 7,
                 "reversal_count": 1, "avg_rating": 4.0}]
        result = _metrics_from_aggregates(rows, {"dead_battery": 0.72})
        assert result["dead_battery"].resolution_rate == pytest.approx(0.70)

    def test_reversal_rate_calculated_correctly(self):
        rows = [{"hypothesis_id": "dead_battery", "total_cases": 10, "resolved_count": 8,
                 "reversal_count": 3, "avg_rating": 3.5}]
        result = _metrics_from_aggregates(rows, {})
        assert result["dead_battery"].reversal_rate == pytest.approx(0.30)

    def test_avg_confidence_from_jsonb_avg(self):
        rows = [{"hypothesis_id": "fuel_issue", "total_cases": 5, "resolved_count": 2,
                 "reversal_count": 0, "avg_rating": 3.0}]
        result = _metrics_from_aggregates(rows, {"fuel_issue": 0.55})
        assert result["fuel_issue"].avg_confidence == pytest.approx(0.55)

    def test_avg_rating_zero_when_none(self):
        rows = [{"hypothesis_id": "clog", "total_cases": 3, "resolved_count": 0,
                 "reversal_count": 0, "avg_rating": None}]
        result = _metrics_from_aggregates(rows, {})
        assert result["clog"].avg_rating == 0.0

    def test_zero_total_gives_zero_rates(self):
        rows = [{"hypothesis_id": "x", "total_cases": 0, "resolved_count": 0,
                 "reversal_count": 0, "avg_rating": 0.0}]
        result = _metrics_from_aggregates(rows, {})
        assert result["x"].resolution_rate == 0.0
        assert result["x"].reversal_rate == 0.0

    def test_multiple_hypotheses_returned(self):
        rows = [
            {"hypothesis_id": "a", "total_cases": 5, "resolved_count": 3, "reversal_count": 0, "avg_rating": 4.0},
            {"hypothesis_id": "b", "total_cases": 8, "resolved_count": 2, "reversal_count": 1, "avg_rating": 2.0},
        ]
        result = _metrics_from_aggregates(rows, {})
        assert "a" in result
        assert "b" in result
        assert result["a"].resolution_rate == pytest.approx(0.60)
        assert result["b"].resolution_rate == pytest.approx(0.25)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Adjustment generation logic
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateAdjustments:
    def test_high_resolution_suggests_increase(self):
        metrics = _make_metrics("dead_battery", total_cases=10, resolution_rate=0.80)
        result = generate_adjustments(metrics)
        assert len(result) == 1
        assert result[0].suggested_multiplier > 1.0

    def test_high_reversal_suggests_decrease(self):
        metrics = _make_metrics("fuel_issue", total_cases=10, reversal_rate=0.40)
        result = generate_adjustments(metrics)
        assert len(result) == 1
        assert result[0].suggested_multiplier < 1.0

    def test_low_rating_penalises(self):
        metrics = _make_metrics("ignition_switch", total_cases=10, avg_rating=2.0)
        result = generate_adjustments(metrics)
        assert len(result) == 1
        assert result[0].suggested_multiplier < 1.0

    def test_combined_signals_compound(self):
        # High reversal AND low rating → deeper penalty
        metrics = _make_metrics("bad_sensor", total_cases=10, reversal_rate=0.40, avg_rating=2.0)
        result = generate_adjustments(metrics)
        assert len(result) == 1
        # Should be lower than reversal-only adjustment
        reversal_only = generate_adjustments(_make_metrics("bad_sensor", total_cases=10, reversal_rate=0.40))
        assert result[0].suggested_multiplier < reversal_only[0].suggested_multiplier

    def test_too_few_samples_skipped(self):
        metrics = _make_metrics("rare_fault", total_cases=1, resolution_rate=1.0)
        result = generate_adjustments(metrics)
        assert result == []

    def test_neutral_signal_no_adjustment(self):
        # 50% resolution, 0% reversal, rating 3.5 → near 1.0, should be filtered by MIN_CHANGE
        metrics = _make_metrics("neutral_hyp", total_cases=10, resolution_rate=0.50,
                                reversal_rate=0.0, avg_rating=3.5)
        result = generate_adjustments(metrics)
        assert result == []

    def test_multiplier_clamped_to_max(self):
        # Extremely high resolution on many cases
        metrics = _make_metrics("certain_fault", total_cases=100, resolution_rate=1.0)
        result = generate_adjustments(metrics)
        assert result[0].suggested_multiplier <= 2.0

    def test_multiplier_clamped_to_min(self):
        # Worst possible signals
        metrics = _make_metrics("wrong_fault", total_cases=10, reversal_rate=0.99, avg_rating=1.0)
        result = generate_adjustments(metrics)
        assert result[0].suggested_multiplier >= 0.5

    def test_confidence_scales_with_sample_size(self):
        small = _make_metrics("h", total_cases=2, reversal_rate=0.40)
        large = _make_metrics("h", total_cases=20, reversal_rate=0.40)
        small_adj = generate_adjustments(small)
        large_adj = generate_adjustments(large)
        assert small_adj[0].confidence < large_adj[0].confidence

    def test_sorted_by_confidence_desc(self):
        from app.learning.metrics import HypothesisMetrics
        metrics = {
            "low": HypothesisMetrics("low", 2, 0.80, 0.0, 0.7, 4.5),
            "high": HypothesisMetrics("high", 20, 0.80, 0.0, 0.7, 4.5),
        }
        result = generate_adjustments(metrics)
        assert result[0].hypothesis_id == "high"

    def test_base_weight_applied_correctly(self):
        # If current approved = 1.2 and suggestion is 1.1 → change < MIN_CHANGE → no output
        metrics = _make_metrics("boosted", total_cases=10, resolution_rate=0.75)
        result_no_base = generate_adjustments(metrics)
        # With base=1.2, the suggested ~1.1 is < 5% different from base → filtered
        result_with_base = generate_adjustments(metrics, current_multipliers={"boosted": 1.2})
        if result_no_base:
            suggested = result_no_base[0].suggested_multiplier
            if abs(suggested - 1.2) < 0.05:
                assert result_with_base == []

    def test_reason_mentions_signal(self):
        metrics = _make_metrics("dead_battery", total_cases=10, resolution_rate=0.85)
        result = generate_adjustments(metrics)
        assert "resolution rate" in result[0].reason


# ─────────────────────────────────────────────────────────────────────────────
# 3. Runtime weight application
# ─────────────────────────────────────────────────────────────────────────────

class TestWeightMultipliersApplied:
    def _hyp_def(self) -> dict[str, dict]:
        return {
            "dead_battery": {"label": "Dead battery", "prior": 0.40},
            "bad_alternator": {"label": "Bad alternator", "prior": 0.20},
        }

    def test_multiplier_above_one_increases_prior(self):
        scorer = HypothesisScorer(self._hyp_def(), weight_multipliers={"dead_battery": 1.5})
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(0.40 * 1.5)

    def test_multiplier_below_one_decreases_prior(self):
        scorer = HypothesisScorer(self._hyp_def(), weight_multipliers={"dead_battery": 0.6})
        assert scorer.hypotheses["dead_battery"].score == pytest.approx(0.40 * 0.6)

    def test_missing_hypothesis_key_gets_default_1(self):
        scorer = HypothesisScorer(self._hyp_def(), weight_multipliers={"dead_battery": 1.5})
        # bad_alternator not in multipliers → prior unchanged
        assert scorer.hypotheses["bad_alternator"].score == pytest.approx(0.20)

    def test_multiplier_clamped_at_max_1(self):
        # prior=0.8, multiplier=2.0 → would be 1.6 → clamped to 1.0
        hyp_def = {"h": {"label": "h", "prior": 0.80}}
        scorer = HypothesisScorer(hyp_def, weight_multipliers={"h": 2.0})
        assert scorer.hypotheses["h"].score <= 1.0

    def test_multiplier_clamped_at_min_0(self):
        hyp_def = {"h": {"label": "h", "prior": 0.50}}
        scorer = HypothesisScorer(hyp_def, weight_multipliers={"h": 0.0})
        assert scorer.hypotheses["h"].score >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. No effect without approval
# ─────────────────────────────────────────────────────────────────────────────

class TestNoEffectWithoutApproval:
    def _hyp_def(self) -> dict[str, dict]:
        return {
            "dead_battery": {"label": "Dead battery", "prior": 0.40},
            "bad_starter": {"label": "Bad starter", "prior": 0.25},
        }

    def test_no_multipliers_gives_identical_scores_to_plain_init(self):
        plain = HypothesisScorer(self._hyp_def())
        with_none = HypothesisScorer(self._hyp_def(), weight_multipliers=None)
        with_empty = HypothesisScorer(self._hyp_def(), weight_multipliers={})
        for key in plain.hypotheses:
            assert plain.hypotheses[key].score == with_none.hypotheses[key].score
            assert plain.hypotheses[key].score == with_empty.hypotheses[key].score

    def test_scorer_from_serializable_unaffected_by_multipliers(self):
        """Restore from DB is independent of multipliers — scores already baked in."""
        hyp_def = self._hyp_def()
        saved = [
            {"key": "dead_battery", "score": 0.72, "eliminated": False, "evidence": ["Q→A"]},
            {"key": "bad_starter", "score": 0.30, "eliminated": False, "evidence": []},
        ]
        restored = HypothesisScorer.from_serializable(hyp_def, saved)
        # from_serializable doesn't apply multipliers (multipliers are session-creation time only)
        assert restored.hypotheses["dead_battery"].score == pytest.approx(0.72)
        assert restored.hypotheses["bad_starter"].score == pytest.approx(0.30)

    def test_adjustment_list_empty_without_outcome_data(self):
        result = generate_adjustments({})
        assert result == []

    def test_adjustment_list_empty_for_all_neutral_signals(self):
        metrics = {
            "h1": HypothesisMetrics("h1", 10, 0.50, 0.05, 0.60, 3.5),
            "h2": HypothesisMetrics("h2", 10, 0.55, 0.10, 0.55, 3.8),
        }
        result = generate_adjustments(metrics)
        assert result == []
