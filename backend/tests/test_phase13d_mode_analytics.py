"""
Phase 13D — Session Mode Analytics Tests.

Tests the pure-Python analysis layer in mode_analytics.py.
No DB required — all tests use in-memory row fixtures.

Test classes:
  TestComputeModeMetrics        — aggregate metric correctness per mode
  TestResolutionRate            — resolution denominator uses completed sessions only
  TestEarlyExitRate             — early-exit threshold and proxy logic
  TestRerouteRate               — rerouted flag aggregation
  TestAvgRating                 — None when no rated sessions; correct when present
  TestAnomalyFrequency          — fraction with >=1 contradiction
  TestFallbackMode              — None session_mode falls back to "consumer"
  TestDiagnosticBreakdown       — top trees, top hypotheses, unresolved clusters
  TestTopNWithResolution        — helper: top-N ordering and resolution rate
  TestUnresolvedClusters        — helper: min_count gate, sorting
  TestCompareModes              — best/worst/spread per metric
  TestModeSummaryText           — deterministic one-sentence output
  TestMinModeSessions           — modes below threshold still included
  TestHeavyEquipmentSubset      — compute_mode_metrics works on a VT-filtered slice
  TestEdgeCases                 — empty input, all-None ratings, single session
"""
from __future__ import annotations

import pytest
from app.learning.mode_analytics import (
    EARLY_EXIT_TURN_THRESHOLD,
    MIN_MODE_SESSIONS,
    TOP_N,
    ModeDiagnosticBreakdown,
    ModeMetrics,
    compare_modes,
    compute_mode_diagnostic_breakdown,
    compute_mode_metrics,
    mode_summary_text,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _row(
    *,
    mode: str = "consumer",
    vehicle_type: str = "car",
    was_resolved: bool | None = True,
    rating: int | None = None,
    contradiction_count: int = 0,
    safety_triggered: bool = False,
    turn_count: int = 10,
    rerouted: bool = False,
    selected_tree: str = "overheating",
    top_hypothesis: str = "coolant_leak",
    session_id: str = "sess-001",
) -> dict:
    return {
        "session_id": session_id,
        "session_mode": mode,
        "vehicle_type": vehicle_type,
        "was_resolved": was_resolved,
        "rating": rating,
        "contradiction_count": contradiction_count,
        "safety_triggered": safety_triggered,
        "turn_count": turn_count,
        "rerouted": rerouted,
        "selected_tree": selected_tree,
        "top_hypothesis": top_hypothesis,
        "created_at": "2026-04-06T10:00:00",
    }


# ── TestComputeModeMetrics ────────────────────────────────────────────────────

class TestComputeModeMetrics:
    def test_returns_metric_per_mode(self):
        rows = [_row(mode="consumer"), _row(mode="operator"), _row(mode="mechanic")]
        result = compute_mode_metrics(rows)
        assert set(result.keys()) == {"consumer", "operator", "mechanic"}

    def test_session_count(self):
        rows = [_row(mode="consumer"), _row(mode="consumer"), _row(mode="operator")]
        result = compute_mode_metrics(rows)
        assert result["consumer"].session_count == 2
        assert result["operator"].session_count == 1

    def test_resolution_rate_all_resolved(self):
        rows = [_row(mode="consumer", was_resolved=True)] * 4
        result = compute_mode_metrics(rows)
        assert result["consumer"].resolution_rate == 1.0

    def test_resolution_rate_partial(self):
        rows = [
            _row(mode="consumer", was_resolved=True),
            _row(mode="consumer", was_resolved=True),
            _row(mode="consumer", was_resolved=False),
            _row(mode="consumer", was_resolved=False),
        ]
        result = compute_mode_metrics(rows)
        assert result["consumer"].resolution_rate == 0.5

    def test_resolution_rate_none_resolved_is_excluded(self):
        # was_resolved=None means session not yet completed; exclude from denominator
        rows = [
            _row(mode="consumer", was_resolved=True),
            _row(mode="consumer", was_resolved=None),
        ]
        result = compute_mode_metrics(rows)
        # only 1 completed session, 1 resolved → 100%
        assert result["consumer"].resolution_rate == 1.0

    def test_contradiction_rate(self):
        rows = [
            _row(mode="consumer", contradiction_count=0),
            _row(mode="consumer", contradiction_count=4),
        ]
        result = compute_mode_metrics(rows)
        assert result["consumer"].contradiction_rate == 2.0

    def test_safety_trigger_rate(self):
        rows = [
            _row(mode="operator", safety_triggered=True),
            _row(mode="operator", safety_triggered=False),
            _row(mode="operator", safety_triggered=False),
            _row(mode="operator", safety_triggered=False),
        ]
        result = compute_mode_metrics(rows)
        assert result["operator"].safety_trigger_rate == 0.25

    def test_returns_mode_metrics_dataclass(self):
        rows = [_row(mode="mechanic")]
        result = compute_mode_metrics(rows)
        assert isinstance(result["mechanic"], ModeMetrics)
        assert result["mechanic"].mode == "mechanic"


# ── TestResolutionRate ────────────────────────────────────────────────────────

class TestResolutionRate:
    def test_zero_completed_yields_zero_rate(self):
        rows = [_row(mode="consumer", was_resolved=None)]
        result = compute_mode_metrics(rows)
        assert result["consumer"].resolution_rate == 0.0

    def test_all_unresolved(self):
        rows = [_row(mode="consumer", was_resolved=False)] * 5
        result = compute_mode_metrics(rows)
        assert result["consumer"].resolution_rate == 0.0

    def test_mixed_none_and_resolved(self):
        rows = [
            _row(mode="consumer", was_resolved=True),
            _row(mode="consumer", was_resolved=None),
            _row(mode="consumer", was_resolved=None),
        ]
        result = compute_mode_metrics(rows)
        # 1 resolved / 1 completed = 1.0
        assert result["consumer"].resolution_rate == 1.0


# ── TestEarlyExitRate ─────────────────────────────────────────────────────────

class TestEarlyExitRate:
    def test_short_resolved_session_counts(self):
        rows = [_row(mode="consumer", turn_count=EARLY_EXIT_TURN_THRESHOLD, was_resolved=True)]
        result = compute_mode_metrics(rows)
        assert result["consumer"].early_exit_rate == 1.0

    def test_long_session_not_counted(self):
        rows = [_row(mode="consumer", turn_count=EARLY_EXIT_TURN_THRESHOLD + 1, was_resolved=True)]
        result = compute_mode_metrics(rows)
        assert result["consumer"].early_exit_rate == 0.0

    def test_short_unfinished_session_not_counted(self):
        # turn_count <= threshold but was_resolved=None → not completed → excluded
        rows = [_row(mode="consumer", turn_count=1, was_resolved=None)]
        result = compute_mode_metrics(rows)
        assert result["consumer"].early_exit_rate == 0.0

    def test_mixed_early_exit(self):
        rows = [
            _row(mode="operator", turn_count=2, was_resolved=True),
            _row(mode="operator", turn_count=2, was_resolved=False),
            _row(mode="operator", turn_count=10, was_resolved=True),
        ]
        result = compute_mode_metrics(rows)
        # 2 early exits / 3 completed
        assert round(result["operator"].early_exit_rate, 4) == round(2 / 3, 4)


# ── TestRerouteRate ───────────────────────────────────────────────────────────

class TestRerouteRate:
    def test_no_reroutes(self):
        rows = [_row(mode="consumer", rerouted=False)] * 3
        result = compute_mode_metrics(rows)
        assert result["consumer"].reroute_rate == 0.0

    def test_all_rerouted(self):
        rows = [_row(mode="mechanic", rerouted=True)] * 4
        result = compute_mode_metrics(rows)
        assert result["mechanic"].reroute_rate == 1.0

    def test_partial_reroute(self):
        rows = [
            _row(mode="operator", rerouted=True),
            _row(mode="operator", rerouted=False),
        ]
        result = compute_mode_metrics(rows)
        assert result["operator"].reroute_rate == 0.5


# ── TestAvgRating ─────────────────────────────────────────────────────────────

class TestAvgRating:
    def test_none_when_no_ratings(self):
        rows = [_row(mode="consumer", rating=None)]
        result = compute_mode_metrics(rows)
        assert result["consumer"].avg_rating is None

    def test_avg_of_ratings(self):
        rows = [
            _row(mode="consumer", rating=4),
            _row(mode="consumer", rating=2),
        ]
        result = compute_mode_metrics(rows)
        assert result["consumer"].avg_rating == 3.0

    def test_single_rating(self):
        rows = [_row(mode="mechanic", rating=5)]
        result = compute_mode_metrics(rows)
        assert result["mechanic"].avg_rating == 5.0

    def test_mixed_none_and_rated(self):
        rows = [
            _row(mode="operator", rating=4),
            _row(mode="operator", rating=None),
        ]
        result = compute_mode_metrics(rows)
        assert result["operator"].avg_rating == 4.0


# ── TestAnomalyFrequency ──────────────────────────────────────────────────────

class TestAnomalyFrequency:
    def test_no_anomalies(self):
        rows = [_row(mode="consumer", contradiction_count=0)] * 5
        result = compute_mode_metrics(rows)
        assert result["consumer"].anomaly_frequency == 0.0

    def test_all_anomalies(self):
        rows = [_row(mode="consumer", contradiction_count=2)] * 4
        result = compute_mode_metrics(rows)
        assert result["consumer"].anomaly_frequency == 1.0

    def test_one_anomaly_counts_once(self):
        # High contradiction count still only counts as 1 anomaly per session
        rows = [
            _row(mode="operator", contradiction_count=10),
            _row(mode="operator", contradiction_count=0),
        ]
        result = compute_mode_metrics(rows)
        assert result["operator"].anomaly_frequency == 0.5


# ── TestFallbackMode ──────────────────────────────────────────────────────────

class TestFallbackMode:
    def test_none_mode_falls_back_to_consumer(self):
        rows = [{"session_mode": None, "was_resolved": True, "rating": None,
                 "contradiction_count": 0, "safety_triggered": False,
                 "turn_count": 10, "rerouted": False,
                 "selected_tree": "overheating", "top_hypothesis": "coolant_leak",
                 "session_id": "x", "vehicle_type": "car"}]
        result = compute_mode_metrics(rows)
        assert "consumer" in result

    def test_missing_mode_key_falls_back(self):
        rows = [{"was_resolved": True, "rating": None,
                 "contradiction_count": 0, "safety_triggered": False,
                 "turn_count": 10, "rerouted": False,
                 "selected_tree": "overheating", "top_hypothesis": "coolant_leak",
                 "session_id": "x", "vehicle_type": "car"}]
        result = compute_mode_metrics(rows)
        assert "consumer" in result


# ── TestDiagnosticBreakdown ───────────────────────────────────────────────────

class TestDiagnosticBreakdown:
    def test_returns_breakdown_dataclass(self):
        rows = [_row(mode="consumer")]
        result = compute_mode_diagnostic_breakdown(rows)
        assert isinstance(result["consumer"], ModeDiagnosticBreakdown)

    def test_top_trees_present(self):
        rows = [_row(mode="consumer", selected_tree="overheating")] * 3
        result = compute_mode_diagnostic_breakdown(rows)
        assert result["consumer"].top_trees[0]["key"] == "overheating"
        assert result["consumer"].top_trees[0]["count"] == 3

    def test_top_hypotheses_present(self):
        rows = [_row(mode="operator", top_hypothesis="clogged_injector")] * 2
        result = compute_mode_diagnostic_breakdown(rows)
        assert result["operator"].top_hypotheses[0]["key"] == "clogged_injector"

    def test_avg_contradictions_in_breakdown(self):
        rows = [
            _row(mode="mechanic", contradiction_count=2),
            _row(mode="mechanic", contradiction_count=4),
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        assert result["mechanic"].avg_contradictions == 3.0

    def test_unresolved_clusters_when_below_min_count(self):
        # Only 1 unresolved → below min_count=3 → no cluster
        rows = [_row(mode="consumer", selected_tree="overheating",
                     top_hypothesis="coolant_leak", was_resolved=False)]
        result = compute_mode_diagnostic_breakdown(rows)
        assert result["consumer"].unresolved_clusters == []

    def test_unresolved_clusters_when_above_min_count(self):
        rows = [
            _row(mode="consumer", selected_tree="overheating",
                 top_hypothesis="coolant_leak", was_resolved=False,
                 session_id=f"sess-{i}")
            for i in range(4)
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        assert len(result["consumer"].unresolved_clusters) == 1
        assert result["consumer"].unresolved_clusters[0]["tree_key"] == "overheating"


# ── TestTopNWithResolution ────────────────────────────────────────────────────

class TestTopNWithResolution:
    def test_top_n_limit(self):
        rows = [_row(mode="consumer", selected_tree=f"tree_{i}") for i in range(10)]
        result = compute_mode_diagnostic_breakdown(rows)
        assert len(result["consumer"].top_trees) <= TOP_N

    def test_ordering_by_count(self):
        rows = (
            [_row(mode="consumer", selected_tree="A")] * 5
            + [_row(mode="consumer", selected_tree="B")] * 3
            + [_row(mode="consumer", selected_tree="C")] * 1
        )
        result = compute_mode_diagnostic_breakdown(rows)
        trees = result["consumer"].top_trees
        assert trees[0]["key"] == "A"
        assert trees[1]["key"] == "B"

    def test_resolution_rate_per_tree(self):
        rows = [
            _row(mode="consumer", selected_tree="T", was_resolved=True),
            _row(mode="consumer", selected_tree="T", was_resolved=True),
            _row(mode="consumer", selected_tree="T", was_resolved=False),
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        entry = result["consumer"].top_trees[0]
        assert entry["key"] == "T"
        assert round(entry["resolution_rate"], 4) == round(2 / 3, 4)

    def test_skips_none_key(self):
        rows = [{"session_mode": "consumer", "selected_tree": None, "was_resolved": True,
                 "rating": None, "contradiction_count": 0, "safety_triggered": False,
                 "turn_count": 8, "rerouted": False, "top_hypothesis": "x",
                 "session_id": "y", "vehicle_type": "car"}]
        result = compute_mode_diagnostic_breakdown(rows)
        # None key should be skipped → empty list
        assert result["consumer"].top_trees == []


# ── TestUnresolvedClusters ────────────────────────────────────────────────────

class TestUnresolvedClusters:
    def test_only_unresolved_count(self):
        rows = [
            _row(mode="consumer", was_resolved=False, selected_tree="T", top_hypothesis="H",
                 session_id="s1"),
            _row(mode="consumer", was_resolved=False, selected_tree="T", top_hypothesis="H",
                 session_id="s2"),
            _row(mode="consumer", was_resolved=False, selected_tree="T", top_hypothesis="H",
                 session_id="s3"),
            _row(mode="consumer", was_resolved=True,  selected_tree="T", top_hypothesis="H",
                 session_id="s4"),
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        cluster = result["consumer"].unresolved_clusters[0]
        # 3 unresolved, 1 resolved — cluster should count only unresolved
        assert cluster["unresolved_count"] == 3

    def test_sample_session_ids_capped_at_3(self):
        rows = [
            _row(mode="consumer", was_resolved=False, selected_tree="T", top_hypothesis="H",
                 session_id=f"s{i}")
            for i in range(6)
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        cluster = result["consumer"].unresolved_clusters[0]
        assert len(cluster["sample_session_ids"]) == 3

    def test_sorted_by_unresolved_count_desc(self):
        rows = (
            # Cluster A: 4 unresolved
            [_row(mode="consumer", was_resolved=False, selected_tree="A",
                  top_hypothesis="H", session_id=f"a{i}") for i in range(4)]
            +
            # Cluster B: 3 unresolved
            [_row(mode="consumer", was_resolved=False, selected_tree="B",
                  top_hypothesis="H", session_id=f"b{i}") for i in range(3)]
        )
        result = compute_mode_diagnostic_breakdown(rows)
        clusters = result["consumer"].unresolved_clusters
        assert clusters[0]["tree_key"] == "A"
        assert clusters[1]["tree_key"] == "B"

    def test_unknown_placeholders_for_missing_keys(self):
        rows = [
            {"session_mode": "consumer", "selected_tree": None, "top_hypothesis": None,
             "was_resolved": False, "rating": None, "contradiction_count": 0,
             "safety_triggered": False, "turn_count": 8, "rerouted": False,
             "session_id": f"x{i}", "vehicle_type": "car"}
            for i in range(4)
        ]
        result = compute_mode_diagnostic_breakdown(rows)
        if result["consumer"].unresolved_clusters:
            c = result["consumer"].unresolved_clusters[0]
            assert c["tree_key"] == "unknown"
            assert c["hypothesis_key"] == "unknown"


# ── TestCompareModes ──────────────────────────────────────────────────────────

class TestCompareModes:
    def _make_metrics(self, consumer_rate: float = 0.8, mechanic_rate: float = 0.6):
        return {
            "consumer": ModeMetrics(
                mode="consumer",
                session_count=10,
                resolution_rate=consumer_rate,
                contradiction_rate=0.5,
                safety_trigger_rate=0.1,
                avg_rating=4.0,
                reroute_rate=0.2,
                early_exit_rate=0.3,
                anomaly_frequency=0.2,
            ),
            "mechanic": ModeMetrics(
                mode="mechanic",
                session_count=5,
                resolution_rate=mechanic_rate,
                contradiction_rate=1.5,
                safety_trigger_rate=0.0,
                avg_rating=None,
                reroute_rate=0.4,
                early_exit_rate=0.1,
                anomaly_frequency=0.4,
            ),
        }

    def test_returns_list_of_dicts(self):
        metrics = self._make_metrics()
        result = compare_modes(metrics)
        assert isinstance(result, list)
        assert all(isinstance(e, dict) for e in result)

    def test_entry_count_matches_fields(self):
        metrics = self._make_metrics()
        result = compare_modes(metrics)
        assert len(result) == 8  # 8 tracked metrics

    def test_resolution_rate_best_worst(self):
        metrics = self._make_metrics(consumer_rate=0.8, mechanic_rate=0.6)
        result = compare_modes(metrics)
        entry = next(e for e in result if e["metric"] == "resolution_rate")
        assert entry["best_mode"] == "consumer"
        assert entry["worst_mode"] == "mechanic"

    def test_contradiction_rate_lower_is_better(self):
        # consumer=0.5, mechanic=1.5 → consumer is "best" (lower)
        metrics = self._make_metrics()
        result = compare_modes(metrics)
        entry = next(e for e in result if e["metric"] == "contradiction_rate")
        assert entry["best_mode"] == "consumer"
        assert entry["worst_mode"] == "mechanic"

    def test_spread_calculation(self):
        metrics = self._make_metrics(consumer_rate=0.8, mechanic_rate=0.5)
        result = compare_modes(metrics)
        entry = next(e for e in result if e["metric"] == "resolution_rate")
        assert entry["spread"] == round(0.8 - 0.5, 4)

    def test_neutral_metric_has_no_best_worst(self):
        metrics = self._make_metrics()
        result = compare_modes(metrics)
        session_entry = next(e for e in result if e["metric"] == "session_count")
        assert session_entry["best_mode"] is None
        assert session_entry["worst_mode"] is None

    def test_all_none_rating_handled(self):
        metrics = {
            "consumer": ModeMetrics(
                mode="consumer", session_count=5, resolution_rate=0.5,
                contradiction_rate=0.5, safety_trigger_rate=0.0,
                avg_rating=None, reroute_rate=0.0,
                early_exit_rate=0.2, anomaly_frequency=0.1,
            )
        }
        result = compare_modes(metrics)
        rating_entry = next(e for e in result if e["metric"] == "avg_rating")
        assert rating_entry["best_mode"] is None
        assert rating_entry["spread"] is None

    def test_empty_input_returns_empty(self):
        assert compare_modes({}) == []

    def test_by_mode_keys_present(self):
        metrics = self._make_metrics()
        result = compare_modes(metrics)
        for entry in result:
            assert "by_mode" in entry
            assert "consumer" in entry["by_mode"]


# ── TestModeSummaryText ───────────────────────────────────────────────────────

class TestModeSummaryText:
    def _make_pair(self):
        metrics = {
            "consumer": ModeMetrics(
                mode="consumer", session_count=20, resolution_rate=0.75,
                contradiction_rate=0.4, safety_trigger_rate=0.05,
                avg_rating=4.2, reroute_rate=0.1, early_exit_rate=0.2,
                anomaly_frequency=0.15,
            )
        }
        breakdown = {
            "consumer": ModeDiagnosticBreakdown(
                mode="consumer",
                top_trees=[{"key": "overheating_heavy_equipment", "count": 5, "resolution_rate": 0.7}],
                top_hypotheses=[],
                unresolved_clusters=[],
                avg_contradictions=0.4,
                anomaly_frequency=0.15,
            )
        }
        return metrics, breakdown

    def test_returns_string_per_mode(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        assert isinstance(result["consumer"], str)

    def test_includes_session_count(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        assert "20 sessions" in result["consumer"]

    def test_includes_resolution_rate(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        assert "75%" in result["consumer"] or "resolved" in result["consumer"]

    def test_missing_mode_produces_no_sessions_message(self):
        m = {}
        b = {}
        result = mode_summary_text(m, b)
        assert "No consumer sessions" in result["consumer"]

    def test_tree_label_strips_he_suffix(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        # "overheating_heavy_equipment" → "overheating"
        assert "heavy_equipment" not in result["consumer"]

    def test_includes_rating_when_present(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        assert "4.2" in result["consumer"]

    def test_mode_title_in_summary(self):
        m, b = self._make_pair()
        result = mode_summary_text(m, b)
        assert result["consumer"].startswith("Consumer:")


# ── TestMinModeSessions ───────────────────────────────────────────────────────

class TestMinModeSessions:
    def test_single_session_mode_still_included(self):
        rows = [_row(mode="operator")]
        result = compute_mode_metrics(rows)
        assert "operator" in result
        assert result["operator"].session_count == 1

    def test_below_min_mode_sessions_constant_is_not_a_filter(self):
        # MIN_MODE_SESSIONS is documented as a flag threshold, not an exclusion filter
        assert MIN_MODE_SESSIONS == 3
        rows = [_row(mode="consumer")]
        result = compute_mode_metrics(rows)
        assert "consumer" in result


# ── TestHeavyEquipmentSubset ──────────────────────────────────────────────────

class TestHeavyEquipmentSubset:
    def test_he_rows_processed_normally(self):
        rows = [
            _row(mode="operator", vehicle_type="heavy_equipment",
                 selected_tree="hydraulic_loss_heavy_equipment"),
            _row(mode="mechanic", vehicle_type="heavy_equipment",
                 selected_tree="no_start_heavy_equipment"),
        ]
        metrics = compute_mode_metrics(rows)
        assert "operator" in metrics
        assert "mechanic" in metrics

    def test_mixed_vt_rows_all_included_in_analysis(self):
        # compute_mode_metrics doesn't filter by vehicle_type (that's the DB layer's job)
        rows = [
            _row(mode="consumer", vehicle_type="car"),
            _row(mode="consumer", vehicle_type="heavy_equipment"),
        ]
        result = compute_mode_metrics(rows)
        assert result["consumer"].session_count == 2

    def test_he_breakdown_top_trees(self):
        rows = [
            _row(mode="operator", vehicle_type="heavy_equipment",
                 selected_tree="hydraulic_loss_heavy_equipment")
        ] * 4
        result = compute_mode_diagnostic_breakdown(rows)
        assert result["operator"].top_trees[0]["key"] == "hydraulic_loss_heavy_equipment"


# ── TestEdgeCases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_rows_returns_empty_dict(self):
        assert compute_mode_metrics([]) == {}
        assert compute_mode_diagnostic_breakdown([]) == {}

    def test_single_mode_single_session(self):
        rows = [_row(mode="consumer", was_resolved=True, rating=5,
                     contradiction_count=0, safety_triggered=False)]
        result = compute_mode_metrics(rows)
        m = result["consumer"]
        assert m.session_count == 1
        assert m.resolution_rate == 1.0
        assert m.avg_rating == 5.0
        assert m.safety_trigger_rate == 0.0

    def test_all_sessions_unfinished(self):
        rows = [_row(mode="consumer", was_resolved=None)] * 5
        result = compute_mode_metrics(rows)
        assert result["consumer"].resolution_rate == 0.0
        assert result["consumer"].early_exit_rate == 0.0

    def test_zero_contradiction_count_none_treated_as_zero(self):
        rows = [{"session_mode": "consumer", "contradiction_count": None,
                 "was_resolved": True, "rating": None, "safety_triggered": False,
                 "turn_count": 8, "rerouted": False, "selected_tree": "T",
                 "top_hypothesis": "H", "session_id": "s", "vehicle_type": "car"}]
        result = compute_mode_metrics(rows)
        assert result["consumer"].contradiction_rate == 0.0

    def test_three_modes_all_computed(self):
        rows = (
            [_row(mode="consumer")] * 3
            + [_row(mode="operator")] * 2
            + [_row(mode="mechanic")] * 1
        )
        result = compute_mode_metrics(rows)
        assert len(result) == 3

    def test_compare_modes_single_mode(self):
        metrics = {
            "consumer": ModeMetrics(
                mode="consumer", session_count=5, resolution_rate=0.8,
                contradiction_rate=0.2, safety_trigger_rate=0.0,
                avg_rating=4.0, reroute_rate=0.1, early_exit_rate=0.2,
                anomaly_frequency=0.1,
            )
        }
        result = compare_modes(metrics)
        # With one mode, spread = 0 for all metrics
        for entry in result:
            if entry["spread"] is not None:
                assert entry["spread"] == 0.0
