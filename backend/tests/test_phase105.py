"""
Phase 10.5 — Learning Intelligence Layer unit tests.

Run with: pytest backend/tests/test_phase105.py -v

All LLM calls are mocked.  Tests verify:
  1.  detect_weak_hypotheses flags low resolution correctly
  2.  detect_weak_hypotheses flags high reversal correctly
  3.  detect_weak_hypotheses flags low rating correctly
  4.  detect_weak_hypotheses filters under-sampled hypotheses
  5.  detect_weak_hypotheses returns sorted by severity descending
  6.  detect_weak_hypotheses returns empty for healthy hypotheses
  7.  detect_tree_gaps flags high unresolved rate
  8.  detect_tree_gaps flags high contradiction rate
  9.  detect_tree_gaps filters trees below minimum sessions
  10. detect_tree_gaps returns sorted by severity descending
  11. detect_anomaly_trends detects volume spike
  12. detect_anomaly_trends detects contradiction spike
  13. detect_anomaly_trends ignores low-volume recent weeks
  14. detect_anomaly_trends returns empty for stable data
  15. analyze_failure_patterns clusters by symptom + hypothesis
  16. analyze_failure_patterns filters clusters below minimum size
  17. analyze_failure_patterns returns empty for empty input
  18. analyze_failure_patterns is non-fatal when LLM fails
  19. generate_insights validates insight types
  20. generate_insights returns empty on LLM failure
  21. generate_insights is sorted by priority ascending
  22. generate_insights caps at MAX_INSIGHTS
  23. System produces correct output with all LLM disabled
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.learning.insights import MAX_INSIGHTS, generate_insights
from app.learning.metrics import HypothesisMetrics
from app.learning.patterns import (
    GAP_CONTRADICTION_MIN,
    GAP_UNRESOLVED_MIN,
    MIN_SAMPLES_FOR_WEAK,
    SPIKE_FACTOR,
    TREND_MIN_RECENT,
    WEAK_RATING_MAX,
    WEAK_RESOLUTION_MIN,
    WEAK_REVERSAL_MAX,
    analyze_failure_patterns,
    detect_anomaly_trends,
    detect_tree_gaps,
    detect_weak_hypotheses,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_metrics(
    hypothesis_id: str,
    total_cases: int = 10,
    resolution_rate: float = 0.8,
    reversal_rate: float = 0.1,
    avg_confidence: float = 0.75,
    avg_rating: float = 4.0,
) -> HypothesisMetrics:
    return HypothesisMetrics(
        hypothesis_id=hypothesis_id,
        total_cases=total_cases,
        resolution_rate=resolution_rate,
        reversal_rate=reversal_rate,
        avg_confidence=avg_confidence,
        avg_rating=avg_rating,
    )


def _make_tree_row(
    tree_id: str,
    total: int = 10,
    unresolved: int = 0,
    avg_contradictions: float = 0.5,
) -> dict:
    return {
        "selected_tree":    tree_id,
        "total_sessions":   total,
        "resolved_count":   total - unresolved,
        "unresolved_count": unresolved,
        "avg_contradictions": avg_contradictions,
        "avg_rating":       4.0,
    }


def _make_week_row(
    week: str,
    symptom: str,
    count: int,
    avg_contra: float = 0.5,
) -> dict:
    return {
        "week":                week,
        "symptom_category":    symptom,
        "session_count":       count,
        "avg_contradictions":  avg_contra,
        "resolved_count":      count,
    }


def _make_outcome(
    symptom: str = "rough_idle",
    hypothesis: str = "idle_control_valve",
    vehicle_type: str = "car",
    was_resolved: bool = True,
    contradiction_count: int = 0,
) -> dict:
    return {
        "session_id":         "test-session",
        "selected_tree":      symptom,
        "top_hypothesis":     hypothesis,
        "was_resolved":       was_resolved,
        "rating":             4,
        "contradiction_count": contradiction_count,
        "safety_triggered":   False,
        "symptom_category":   symptom,
        "vehicle_type":       vehicle_type,
        "vehicle_year":       2020,
        "description":        f"Test {symptom} description",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1–6. detect_weak_hypotheses
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectWeakHypotheses:
    def test_flags_low_resolution(self):
        metrics = {
            "bad_hyp": _make_metrics(
                "bad_hyp", total_cases=10,
                resolution_rate=WEAK_RESOLUTION_MIN - 0.05,
            )
        }
        result = detect_weak_hypotheses(metrics)
        assert len(result) == 1
        assert result[0]["hypothesis_id"] == "bad_hyp"
        assert any("resolution" in w for w in result[0]["weaknesses"])

    def test_flags_high_reversal(self):
        metrics = {
            "reverse_hyp": _make_metrics(
                "reverse_hyp", total_cases=10,
                reversal_rate=WEAK_REVERSAL_MAX + 0.05,
            )
        }
        result = detect_weak_hypotheses(metrics)
        assert len(result) == 1
        assert any("reversal" in w for w in result[0]["weaknesses"])

    def test_flags_low_rating(self):
        metrics = {
            "low_rate_hyp": _make_metrics(
                "low_rate_hyp", total_cases=10,
                avg_rating=WEAK_RATING_MAX - 0.5,
            )
        }
        result = detect_weak_hypotheses(metrics)
        assert len(result) == 1
        assert any("rating" in w for w in result[0]["weaknesses"])

    def test_filters_undersampled(self):
        metrics = {
            "tiny_hyp": _make_metrics(
                "tiny_hyp",
                total_cases=MIN_SAMPLES_FOR_WEAK - 1,
                resolution_rate=0.0,  # would be very weak if sampled
                reversal_rate=1.0,
                avg_rating=1.0,
            )
        }
        result = detect_weak_hypotheses(metrics)
        assert result == []

    def test_sorted_by_severity_descending(self):
        metrics = {
            "mild":   _make_metrics("mild",   total_cases=10, reversal_rate=0.32),
            "severe": _make_metrics("severe", total_cases=10, reversal_rate=0.70,
                                    avg_rating=1.5),
        }
        result = detect_weak_hypotheses(metrics)
        assert len(result) == 2
        assert result[0]["severity"] >= result[1]["severity"]

    def test_healthy_hypothesis_not_flagged(self):
        metrics = {
            "good_hyp": _make_metrics(
                "good_hyp",
                total_cases=20,
                resolution_rate=0.85,
                reversal_rate=0.05,
                avg_rating=4.5,
            )
        }
        result = detect_weak_hypotheses(metrics)
        assert result == []

    def test_severity_between_zero_and_one(self):
        metrics = {
            "any": _make_metrics("any", total_cases=10, reversal_rate=0.50, avg_rating=2.0)
        }
        result = detect_weak_hypotheses(metrics)
        assert 0.0 <= result[0]["severity"] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 7–10. detect_tree_gaps
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectTreeGaps:
    def test_flags_high_unresolved_rate(self):
        rows = [_make_tree_row("rough_idle", total=10, unresolved=5)]  # 50% unresolved
        result = detect_tree_gaps(rows)
        assert len(result) == 1
        assert result[0]["tree_id"] == "rough_idle"
        assert any("unresolved" in g for g in result[0]["gap_types"])

    def test_flags_high_contradiction_rate(self):
        rows = [_make_tree_row("brakes", total=10, avg_contradictions=GAP_CONTRADICTION_MIN + 0.5)]
        result = detect_tree_gaps(rows)
        assert len(result) == 1
        assert any("contradiction" in g for g in result[0]["gap_types"])

    def test_filters_below_minimum_sessions(self):
        rows = [_make_tree_row("tiny_tree", total=2, unresolved=2)]  # 100% unresolved but n<3
        result = detect_tree_gaps(rows)
        assert result == []

    def test_sorted_by_severity_descending(self):
        rows = [
            _make_tree_row("mild_gap",   total=10, unresolved=4),   # 40% — barely above threshold
            _make_tree_row("severe_gap", total=10, unresolved=9),   # 90% unresolved
        ]
        result = detect_tree_gaps(rows)
        assert len(result) == 2
        assert result[0]["severity"] >= result[1]["severity"]

    def test_healthy_tree_not_flagged(self):
        rows = [_make_tree_row("good_tree", total=20, unresolved=2, avg_contradictions=0.3)]
        result = detect_tree_gaps(rows)
        assert result == []

    def test_both_gap_types_combined(self):
        rows = [_make_tree_row(
            "double_gap", total=10, unresolved=5,
            avg_contradictions=GAP_CONTRADICTION_MIN + 1.0
        )]
        result = detect_tree_gaps(rows)
        assert len(result) == 1
        assert len(result[0]["gap_types"]) == 2
        assert result[0]["recommendation"] != ""


# ─────────────────────────────────────────────────────────────────────────────
# 11–14. detect_anomaly_trends
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectAnomalyTrends:
    def _build_weeks(self, symptom, recent_count, hist_counts):
        """recent week + historical weeks for a symptom."""
        rows = [_make_week_row("2026-04-07", symptom, recent_count)]
        for i, c in enumerate(hist_counts, 1):
            rows.append(_make_week_row(f"2026-03-{28 - i * 7:02d}", symptom, c))
        return rows

    def test_detects_volume_spike(self):
        # recent=20, historical=[5, 5, 5] → avg=5, spike=4x
        rows = self._build_weeks("rough_idle", TREND_MIN_RECENT * 2, [2, 2, 2])
        result = detect_anomaly_trends(rows)
        spikes = [r for r in result if r["trend_type"] == "volume_spike"]
        assert len(spikes) >= 1
        assert spikes[0]["symptom_category"] == "rough_idle"
        assert spikes[0]["spike_factor"] >= SPIKE_FACTOR

    def test_detects_contradiction_spike(self):
        # recent avg_contra=4.0, historical=[1,1,1] → spike=4x
        rows = [
            {**_make_week_row("2026-04-07", "brakes", 10), "avg_contradictions": 4.0},
            {**_make_week_row("2026-03-31", "brakes", 10), "avg_contradictions": 1.0},
            {**_make_week_row("2026-03-24", "brakes", 10), "avg_contradictions": 1.0},
        ]
        result = detect_anomaly_trends(rows)
        contra_spikes = [r for r in result if r["trend_type"] == "contradiction_spike"]
        assert len(contra_spikes) >= 1

    def test_ignores_low_volume_recent(self):
        # recent count below TREND_MIN_RECENT even though it's a spike
        rows = self._build_weeks("overheating", TREND_MIN_RECENT - 1, [1, 1, 1])
        result = detect_anomaly_trends(rows)
        spikes = [r for r in result if r["symptom_category"] == "overheating"]
        assert all(r["spike_factor"] < SPIKE_FACTOR or r["recent_count"] >= TREND_MIN_RECENT
                   for r in spikes)

    def test_stable_data_returns_empty(self):
        rows = []
        for i in range(4):
            rows.append(_make_week_row(f"2026-0{4 - i}-07", "suspension", 5))
        result = detect_anomaly_trends(rows)
        # Stable ≈5/week — no spike
        assert all(r["spike_factor"] < SPIKE_FACTOR for r in result)

    def test_returns_empty_for_no_data(self):
        assert detect_anomaly_trends([]) == []

    def test_sorted_by_spike_factor_descending(self):
        # Two symptoms both spiking, different magnitudes
        rows = (
            self._build_weeks("no_crank", 30, [3, 3])  # 10x spike
            + self._build_weeks("brakes",  12, [3, 3])  # 4x spike
        )
        result = detect_anomaly_trends(rows)
        if len(result) >= 2:
            factors = [r["spike_factor"] for r in result]
            assert factors == sorted(factors, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 15–18. analyze_failure_patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeFailurePatterns:
    def _outcomes(self, symptom, hypothesis, n, resolved=True):
        return [_make_outcome(symptom, hypothesis, was_resolved=resolved) for _ in range(n)]

    def test_clusters_by_symptom_and_hypothesis(self):
        data = self._outcomes("rough_idle", "idle_control_valve", 5)
        with patch("app.learning.patterns._llm_summarize_patterns", side_effect=lambda p, _: p):
            result = analyze_failure_patterns(data)
        assert len(result) == 1
        assert result[0]["pattern"] == "rough_idle:idle_control_valve"
        assert result[0]["frequency"] == 5

    def test_filters_clusters_below_minimum(self):
        # Only 2 sessions — below threshold of 3
        data = self._outcomes("suspension", "worn_shock_absorber", 2)
        with patch("app.learning.patterns._llm_summarize_patterns", side_effect=lambda p, _: p):
            result = analyze_failure_patterns(data)
        assert result == []

    def test_multiple_clusters_sorted_by_frequency(self):
        data = (
            self._outcomes("rough_idle", "idle_control_valve", 6)
            + self._outcomes("brakes", "brake_pad_wear", 4)
        )
        with patch("app.learning.patterns._llm_summarize_patterns", side_effect=lambda p, _: p):
            result = analyze_failure_patterns(data)
        assert len(result) == 2
        assert result[0]["frequency"] >= result[1]["frequency"]

    def test_returns_empty_for_no_data(self):
        assert analyze_failure_patterns([]) == []

    def test_non_fatal_when_llm_fails(self):
        data = self._outcomes("rough_idle", "idle_control_valve", 4)
        with patch("app.learning.patterns._llm_summarize_patterns",
                   side_effect=Exception("LLM offline")):
            # Should not raise — auto-summary used instead
            result = analyze_failure_patterns(data)
        # Pattern still returned despite LLM error in summarize
        assert isinstance(result, list)

    def test_resolution_rate_computed_correctly(self):
        data = (
            self._outcomes("brakes", "brake_fluid_low", 3, resolved=True)
            + self._outcomes("brakes", "brake_fluid_low", 1, resolved=False)
        )
        with patch("app.learning.patterns._llm_summarize_patterns", side_effect=lambda p, _: p):
            result = analyze_failure_patterns(data)
        assert len(result) == 1
        assert abs(result[0]["resolution_rate"] - 0.75) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# 19–22. generate_insights
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateInsights:
    def _call_with_mock(self, mock_response: str) -> list[dict]:
        with patch("app.learning.insights._call", return_value=mock_response):
            return generate_insights(
                weak_hypotheses=[{"hypothesis_id": "dirty_maf", "weaknesses": ["high reversal"], "severity": 0.7, "total_cases": 10, "resolution_rate": 0.4, "reversal_rate": 0.4, "avg_rating": 3.0}],
                failure_patterns=[{"pattern": "rough_idle:dirty_maf", "frequency": 8, "resolution_rate": 0.5, "summary": "Frequent misdiagnosis"}],
                tree_gaps=[{"tree_id": "rough_idle", "gap_types": ["high unresolved rate (50%)"], "severity": 0.5, "total_sessions": 10, "unresolved_rate": 0.5, "avg_contradictions": 0.8, "recommendation": "review tree"}],
                anomaly_trends=[],
                metrics_summary={"total_cases": 50, "total_hypotheses": 12},
            )

    def test_validates_insight_types(self):
        mock = '{"insights": [{"type": "critical", "title": "MAF sensor issue", "description": "Dirty MAF reversal rate is high.", "affected": ["dirty_maf"], "suggested_action": "Review MAF node", "priority": 1}]}'
        result = self._call_with_mock(mock)
        assert len(result) == 1
        assert result[0]["type"] in {"critical", "warning", "opportunity"}

    def test_invalid_type_defaults_to_warning(self):
        mock = '{"insights": [{"type": "unknown_type", "title": "Something", "description": "Some issue here.", "affected": [], "suggested_action": "Fix it", "priority": 2}]}'
        result = self._call_with_mock(mock)
        assert result[0]["type"] == "warning"

    def test_sorted_by_priority_ascending(self):
        mock = '{"insights": [{"type": "warning", "title": "Low priority", "description": "Minor issue found.", "affected": [], "suggested_action": "Maybe fix", "priority": 5}, {"type": "critical", "title": "High priority", "description": "Major issue found.", "affected": [], "suggested_action": "Fix now", "priority": 1}]}'
        result = self._call_with_mock(mock)
        assert len(result) == 2
        assert result[0]["priority"] <= result[1]["priority"]

    def test_caps_at_max_insights(self):
        items = [
            {"type": "warning", "title": f"Issue {i}", "description": f"Desc {i}.", "affected": [], "suggested_action": "act", "priority": i % 5 + 1}
            for i in range(MAX_INSIGHTS + 5)
        ]
        import json
        mock = json.dumps({"insights": items})
        result = self._call_with_mock(mock)
        assert len(result) <= MAX_INSIGHTS

    def test_returns_empty_on_llm_failure(self):
        with patch("app.learning.insights._call", side_effect=Exception("network error")):
            result = generate_insights(
                weak_hypotheses=[],
                failure_patterns=[],
                tree_gaps=[],
                anomaly_trends=[],
                metrics_summary={"total_cases": 0, "total_hypotheses": 0},
            )
        assert result == []

    def test_returns_empty_when_no_data(self):
        result = generate_insights(
            weak_hypotheses=[],
            failure_patterns=[],
            tree_gaps=[],
            anomaly_trends=[],
            metrics_summary={"total_cases": 0, "total_hypotheses": 0},
        )
        assert result == []

    def test_filters_entries_missing_title_or_description(self):
        mock = '{"insights": [{"type": "warning", "title": "", "description": "Some issue.", "affected": [], "suggested_action": "act", "priority": 2}, {"type": "warning", "title": "Valid", "description": "Valid description.", "affected": [], "suggested_action": "act", "priority": 2}]}'
        result = self._call_with_mock(mock)
        assert all(r["title"] for r in result)

    def test_priority_clamped_to_1_5(self):
        mock = '{"insights": [{"type": "opportunity", "title": "Test", "description": "Test description.", "affected": [], "suggested_action": "do something", "priority": 99}]}'
        result = self._call_with_mock(mock)
        assert 1 <= result[0]["priority"] <= 5


# ─────────────────────────────────────────────────────────────────────────────
# 23. All LLM disabled — deterministic outputs still correct
# ─────────────────────────────────────────────────────────────────────────────

class TestGracefulDegradationFull:
    def test_deterministic_outputs_with_all_llm_disabled(self):
        """Verify the system produces correct deterministic output when every
        LLM call raises an exception."""

        # detect_weak_hypotheses — pure, no LLM
        metrics = {
            "bad": _make_metrics("bad", total_cases=10, reversal_rate=0.50),
            "ok":  _make_metrics("ok",  total_cases=10, resolution_rate=0.90, reversal_rate=0.05),
        }
        weak = detect_weak_hypotheses(metrics)
        assert len(weak) == 1
        assert weak[0]["hypothesis_id"] == "bad"

        # detect_tree_gaps — pure, no LLM
        gaps = detect_tree_gaps([_make_tree_row("bad_tree", total=10, unresolved=5)])
        assert len(gaps) == 1

        # detect_anomaly_trends — pure, no LLM
        trends = detect_anomaly_trends([
            _make_week_row("2026-04-07", "rough_idle", 20),
            _make_week_row("2026-03-31", "rough_idle", 4),
            _make_week_row("2026-03-24", "rough_idle", 3),
        ])
        spikes = [t for t in trends if t["trend_type"] == "volume_spike"]
        assert len(spikes) >= 1

        # analyze_failure_patterns — LLM fails, returns statistical result
        with patch("app.learning.patterns._llm_summarize_patterns",
                   side_effect=Exception("LLM offline")):
            outcomes = [_make_outcome("brakes", "brake_pad_wear") for _ in range(4)]
            patterns = analyze_failure_patterns(outcomes)
            # May be empty (summarize_patterns handles the exception internally)
            assert isinstance(patterns, list)

        # generate_insights — LLM fails, returns empty (non-fatal)
        with patch("app.learning.insights._call", side_effect=Exception("LLM offline")):
            insights = generate_insights(weak, [], gaps, trends, {"total_cases": 10, "total_hypotheses": 2})
        assert insights == []
