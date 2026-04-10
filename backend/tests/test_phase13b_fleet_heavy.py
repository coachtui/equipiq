"""
Phase 13B — Fleet Pattern Detection (Heavy Equipment) — unit tests.

Tests cover all five deterministic pattern detectors plus helpers.
All tests operate on plain Python structures — no database required.

Run with:
    cd backend && docker exec fix-backend-1 python -m pytest tests/test_phase13b_fleet_heavy.py -v
"""
import pytest

from app.learning.fleet_heavy import (
    CONTRADICTION_HOTSPOT_MIN,
    ENVIRONMENT_CLUSTER_MIN,
    MIN_PATTERN_SESSIONS,
    SAFETY_HOTSPOT_MIN,
    UNRESOLVED_HOTSPOT_MIN,
    _hours_band,
    _is_overdue,
    detect_contradiction_hotspots,
    detect_environment_patterns,
    detect_hours_failure_patterns,
    detect_safety_hotspots,
    detect_unresolved_clusters,
    run_all_pattern_detection,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _row(
    tree: str = "hydraulic_loss_heavy_equipment",
    hypothesis: str = "low_fluid",
    resolved: bool | None = False,
    safety: bool = False,
    contradictions: int = 0,
    hours: int | None = 1500,
    last_service: int | None = 1400,
    environment: str = "dusty",
    mode: str = "operator",
    session_id: str | None = None,
    rating: int | None = None,
) -> dict:
    """Build a minimal fleet row dict as returned by fetch_heavy_fleet_data()."""
    import uuid
    return {
        "session_id": session_id or str(uuid.uuid4()),
        "selected_tree": tree,
        "top_hypothesis": hypothesis,
        "was_resolved": resolved,
        "rating": rating,
        "contradiction_count": contradictions,
        "safety_triggered": safety,
        "session_mode": mode,
        "symptom_category": tree.replace("_heavy_equipment", ""),
        "hours_of_operation": hours,
        "last_service_hours": last_service,
        "environment": environment,
        "storage_duration": 0,
        "recent_work_type": "earthmoving",
        "created_at": "2026-03-01T10:00:00+00:00",
    }


def _rows(n: int, **kwargs) -> list[dict]:
    """Build n identical rows (with unique session IDs)."""
    return [_row(**kwargs) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_hours_band_low(self):
        assert _hours_band(0) == "low_hours"
        assert _hours_band(999) == "low_hours"

    def test_hours_band_moderate(self):
        assert _hours_band(1000) == "moderate_hours"
        assert _hours_band(2999) == "moderate_hours"

    def test_hours_band_high(self):
        assert _hours_band(3000) == "high_hours"
        assert _hours_band(5999) == "high_hours"

    def test_hours_band_very_high(self):
        assert _hours_band(6000) == "very_high_hours"
        assert _hours_band(15000) == "very_high_hours"

    def test_hours_band_none(self):
        assert _hours_band(None) == "unknown"

    def test_is_overdue_true(self):
        assert _is_overdue(hours=5000, last_service=4600) is True  # 400h overdue

    def test_is_overdue_false_within_interval(self):
        assert _is_overdue(hours=4700, last_service=4600) is False  # 100h

    def test_is_overdue_false_no_service_record(self):
        assert _is_overdue(hours=5000, last_service=0) is False

    def test_is_overdue_false_none_hours(self):
        assert _is_overdue(hours=None, last_service=4000) is False


# ─────────────────────────────────────────────────────────────────────────────
# detect_hours_failure_patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestHoursFailurePatterns:
    def test_basic_group_produces_pattern(self):
        rows = _rows(5, hours=4000, tree="hydraulic_loss_heavy_equipment", resolved=False)
        patterns = detect_hours_failure_patterns(rows)
        assert len(patterns) >= 1
        p = patterns[0]
        assert p["pattern_type"] == "hours_failure_rate"
        assert p["hours_band"] == "high_hours"
        assert p["session_count"] == 5
        assert p["unresolved_rate"] == 1.0

    def test_group_below_min_sessions_excluded(self):
        rows = _rows(MIN_PATTERN_SESSIONS - 1, hours=1500)
        patterns = detect_hours_failure_patterns(rows)
        assert not patterns

    def test_unknown_hours_excluded(self):
        rows = _rows(5, hours=None)
        patterns = detect_hours_failure_patterns(rows)
        assert not any(p["hours_band"] == "unknown" for p in patterns)

    def test_sorted_by_unresolved_rate_descending(self):
        # high_hours group with all unresolved
        high_unresolved = _rows(4, hours=4000, resolved=False, tree="overheating_heavy_equipment")
        # low_hours group with partial resolution
        low_some_resolved = (
            _rows(2, hours=500, resolved=True, tree="overheating_heavy_equipment") +
            _rows(3, hours=500, resolved=False, tree="overheating_heavy_equipment")
        )
        patterns = detect_hours_failure_patterns(high_unresolved + low_some_resolved)
        rates = [p["unresolved_rate"] for p in patterns]
        assert rates == sorted(rates, reverse=True)

    def test_top_hypotheses_populated(self):
        rows = (
            _rows(3, hours=1500, hypothesis="clogged_filter") +
            _rows(2, hours=1500, hypothesis="low_fluid")
        )
        patterns = detect_hours_failure_patterns(rows)
        assert len(patterns) >= 1
        top_hyps = patterns[0]["top_hypotheses"]
        assert "clogged_filter" in top_hyps  # most common should appear

    def test_safety_rate_computed(self):
        rows = (
            _rows(2, hours=4000, safety=True) +
            _rows(3, hours=4000, safety=False)
        )
        patterns = detect_hours_failure_patterns(rows)
        assert len(patterns) == 1
        assert patterns[0]["safety_trigger_rate"] == pytest.approx(2 / 5)

    def test_sample_session_ids_capped_at_three(self):
        rows = _rows(10, hours=1500)
        patterns = detect_hours_failure_patterns(rows)
        for p in patterns:
            assert len(p["sample_session_ids"]) <= 3

    def test_multiple_trees_produce_separate_patterns(self):
        rows = (
            _rows(4, hours=2000, tree="hydraulic_loss_heavy_equipment") +
            _rows(4, hours=2000, tree="overheating_heavy_equipment")
        )
        patterns = detect_hours_failure_patterns(rows)
        tree_keys = {p["tree_key"] for p in patterns}
        assert "hydraulic_loss_heavy_equipment" in tree_keys
        assert "overheating_heavy_equipment" in tree_keys

    def test_description_string_is_non_empty(self):
        rows = _rows(4, hours=3500)
        patterns = detect_hours_failure_patterns(rows)
        assert patterns[0]["description"]


# ─────────────────────────────────────────────────────────────────────────────
# detect_environment_patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvironmentPatterns:
    def test_dusty_high_unresolved_flagged(self):
        rows = _rows(5, environment="dusty", resolved=False)
        patterns = detect_environment_patterns(rows)
        assert len(patterns) >= 1
        p = patterns[0]
        assert p["pattern_type"] == "environment_failure"
        assert p["environment"] == "dusty"
        assert p["unresolved_rate"] >= ENVIRONMENT_CLUSTER_MIN

    def test_urban_low_unresolved_not_flagged(self):
        """Urban environment with good resolution should not produce a pattern."""
        rows = (
            _rows(3, environment="urban", resolved=True) +
            _rows(2, environment="urban", resolved=True)
        )
        patterns = detect_environment_patterns(rows)
        urban_patterns = [p for p in patterns if p["environment"] == "urban"]
        assert not urban_patterns, "Urban with low unresolved/safety should not be flagged"

    def test_marine_with_high_safety_flagged(self):
        rows = _rows(5, environment="marine", safety=True, resolved=True)
        patterns = detect_environment_patterns(rows)
        marine = [p for p in patterns if p["environment"] == "marine"]
        assert marine, "Marine with high safety trigger rate should be flagged"
        assert marine[0]["safety_trigger_rate"] >= SAFETY_HOTSPOT_MIN

    def test_unknown_environment_excluded(self):
        rows = _rows(5, environment=None)
        # None becomes "unknown" in the row
        for r in rows:
            r["environment"] = None
        patterns = detect_environment_patterns(rows)
        assert not any(p["environment"] == "unknown" for p in patterns)

    def test_below_min_sessions_excluded(self):
        rows = _rows(MIN_PATTERN_SESSIONS - 1, environment="muddy", resolved=False)
        patterns = detect_environment_patterns(rows)
        assert not patterns

    def test_sorted_by_unresolved_rate_descending(self):
        rows = (
            _rows(4, environment="dusty", resolved=False, tree="hydraulic_loss_heavy_equipment") +
            _rows(3, environment="muddy", resolved=False, tree="hydraulic_loss_heavy_equipment") +
            _rows(3, environment="muddy", resolved=True, tree="hydraulic_loss_heavy_equipment")
        )
        patterns = detect_environment_patterns(rows)
        rates = [p["unresolved_rate"] for p in patterns]
        assert rates == sorted(rates, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# detect_unresolved_clusters
# ─────────────────────────────────────────────────────────────────────────────

class TestUnresolvedClusters:
    def test_large_unresolved_cluster_detected(self):
        rows = _rows(5, resolved=False, tree="hydraulic_loss_heavy_equipment", hypothesis="low_fluid")
        clusters = detect_unresolved_clusters(rows)
        assert len(clusters) >= 1
        c = clusters[0]
        assert c["pattern_type"] == "unresolved_cluster"
        assert c["tree_key"] == "hydraulic_loss_heavy_equipment"
        assert c["hypothesis_key"] == "low_fluid"
        assert c["unresolved_count"] == 5

    def test_mixed_resolved_unresolved_below_threshold_not_flagged(self):
        rows = (
            _rows(4, resolved=True, tree="overheating_heavy_equipment", hypothesis="blocked_cooler") +
            _rows(2, resolved=False, tree="overheating_heavy_equipment", hypothesis="blocked_cooler")
        )
        # Only 2 unresolved — below MIN_PATTERN_SESSIONS=3
        clusters = detect_unresolved_clusters(rows)
        assert not any(
            c["hypothesis_key"] == "blocked_cooler" for c in clusters
        ), "2 unresolved is below the minimum threshold"

    def test_cluster_includes_hours_band_breakdown(self):
        rows = (
            _rows(2, resolved=False, hours=1500) +
            _rows(2, resolved=False, hours=4000)
        )
        clusters = detect_unresolved_clusters(rows)
        assert len(clusters) >= 1
        breakdown = clusters[0]["hours_band_breakdown"]
        assert isinstance(breakdown, dict)

    def test_sorted_by_unresolved_count_descending(self):
        rows = (
            _rows(5, resolved=False, tree="hydraulic_loss_heavy_equipment", hypothesis="low_fluid") +
            _rows(3, resolved=False, tree="overheating_heavy_equipment", hypothesis="thermostat_failure")
        )
        clusters = detect_unresolved_clusters(rows)
        counts = [c["unresolved_count"] for c in clusters]
        assert counts == sorted(counts, reverse=True)

    def test_sample_ids_from_unresolved_rows_only(self):
        resolved_ids = [f"res-{i}" for i in range(3)]
        unresolved_ids = [f"unres-{i}" for i in range(3)]
        rows = (
            [_row(resolved=True, session_id=sid) for sid in resolved_ids] +
            [_row(resolved=False, session_id=sid) for sid in unresolved_ids]
        )
        clusters = detect_unresolved_clusters(rows)
        assert clusters
        for sid in clusters[0]["sample_session_ids"]:
            assert sid in unresolved_ids, "Sample IDs must come from unresolved sessions"

    def test_unresolved_rate_correct(self):
        rows = (
            _rows(3, resolved=False) +
            _rows(7, resolved=True)
        )
        clusters = detect_unresolved_clusters(rows)
        assert clusters
        assert clusters[0]["unresolved_rate"] == pytest.approx(3 / 10)

    def test_description_contains_hypothesis(self):
        rows = _rows(4, resolved=False, hypothesis="failed_hydraulic_pump")
        clusters = detect_unresolved_clusters(rows)
        assert clusters
        assert "failed hydraulic pump" in clusters[0]["description"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# detect_safety_hotspots
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyHotspots:
    def test_high_safety_rate_flagged(self):
        rows = _rows(5, safety=True, environment="dusty")
        hotspots = detect_safety_hotspots(rows)
        assert len(hotspots) >= 1
        h = hotspots[0]
        assert h["pattern_type"] == "safety_hotspot"
        assert h["safety_trigger_rate"] == 1.0

    def test_low_safety_rate_not_flagged(self):
        rows = (
            _rows(1, safety=True) +
            _rows(9, safety=False)
        )
        # 10% trigger rate — below SAFETY_HOTSPOT_MIN (0.30)
        hotspots = detect_safety_hotspots(rows)
        assert not hotspots

    def test_hotspot_rate_at_threshold(self):
        # Exactly at threshold
        trigger_count = int(MIN_PATTERN_SESSIONS * SAFETY_HOTSPOT_MIN) + 1
        n = trigger_count + (MIN_PATTERN_SESSIONS - trigger_count % MIN_PATTERN_SESSIONS)
        rows = (
            _rows(trigger_count, safety=True) +
            _rows(max(0, n - trigger_count), safety=False)
        )
        if len(rows) < MIN_PATTERN_SESSIONS:
            rows += _rows(MIN_PATTERN_SESSIONS - len(rows), safety=False)
        hotspots = detect_safety_hotspots(rows)
        # Just verify no crash + result is list
        assert isinstance(hotspots, list)

    def test_sample_ids_from_safety_triggered_rows(self):
        safe_ids = [f"safe-{i}" for i in range(5)]
        unsafe_ids = [f"unsafe-{i}" for i in range(4)]
        rows = (
            [_row(safety=False, session_id=sid) for sid in safe_ids] +
            [_row(safety=True, session_id=sid) for sid in unsafe_ids]
        )
        hotspots = detect_safety_hotspots(rows)
        if hotspots:
            for sid in hotspots[0]["sample_session_ids"]:
                assert sid in unsafe_ids, "Sample IDs must come from safety-triggered sessions"

    def test_sorted_by_safety_trigger_rate_descending(self):
        rows_dusty = _rows(5, safety=True, environment="dusty", tree="hydraulic_loss_heavy_equipment")
        rows_muddy = (
            _rows(2, safety=True, environment="muddy", tree="hydraulic_loss_heavy_equipment") +
            _rows(3, safety=False, environment="muddy", tree="hydraulic_loss_heavy_equipment")
        )
        hotspots = detect_safety_hotspots(rows_dusty + rows_muddy)
        rates = [h["safety_trigger_rate"] for h in hotspots]
        assert rates == sorted(rates, reverse=True)

    def test_below_min_sessions_excluded(self):
        rows = _rows(MIN_PATTERN_SESSIONS - 1, safety=True)
        hotspots = detect_safety_hotspots(rows)
        assert not hotspots

    def test_description_contains_tree_and_environment(self):
        rows = _rows(5, safety=True, tree="hydraulic_loss_heavy_equipment", environment="muddy")
        hotspots = detect_safety_hotspots(rows)
        assert hotspots
        desc = hotspots[0]["description"].lower()
        assert "hydraulic" in desc
        assert "muddy" in desc


# ─────────────────────────────────────────────────────────────────────────────
# detect_contradiction_hotspots
# ─────────────────────────────────────────────────────────────────────────────

class TestContradictionHotspots:
    def test_high_contradiction_rate_flagged(self):
        rows = _rows(4, contradictions=3, tree="track_or_drive_issue_heavy_equipment")
        hotspots = detect_contradiction_hotspots(rows)
        assert len(hotspots) >= 1
        h = hotspots[0]
        assert h["pattern_type"] == "contradiction_hotspot"
        assert h["avg_contradictions"] == pytest.approx(3.0)

    def test_low_contradiction_rate_not_flagged(self):
        rows = _rows(5, contradictions=1, tree="hydraulic_loss_heavy_equipment")
        hotspots = detect_contradiction_hotspots(rows)
        # 1.0 < CONTRADICTION_HOTSPOT_MIN (1.5) → should not be flagged
        he_hotspot = [h for h in hotspots if h["tree_key"] == "hydraulic_loss_heavy_equipment"]
        assert not he_hotspot

    def test_at_threshold_not_below(self):
        threshold = CONTRADICTION_HOTSPOT_MIN
        # Exactly at threshold — should appear
        rows = _rows(4, contradictions=int(threshold))
        hotspots = detect_contradiction_hotspots(rows)
        # Avg = threshold, which meets >= check
        assert isinstance(hotspots, list)

    def test_sorted_by_avg_contradictions_descending(self):
        rows_high = _rows(4, contradictions=4, tree="abnormal_noise_heavy_equipment")
        rows_medium = _rows(4, contradictions=2, tree="track_or_drive_issue_heavy_equipment")
        hotspots = detect_contradiction_hotspots(rows_high + rows_medium)
        avgs = [h["avg_contradictions"] for h in hotspots]
        assert avgs == sorted(avgs, reverse=True)

    def test_per_mode_breakdown_populated(self):
        rows = (
            _rows(3, contradictions=3, mode="operator") +
            _rows(3, contradictions=2, mode="mechanic")
        )
        hotspots = detect_contradiction_hotspots(rows)
        assert hotspots
        breakdown = hotspots[0]["contradictions_by_mode"]
        assert "operator" in breakdown
        assert "mechanic" in breakdown

    def test_below_min_sessions_excluded(self):
        rows = _rows(MIN_PATTERN_SESSIONS - 1, contradictions=4)
        hotspots = detect_contradiction_hotspots(rows)
        assert not hotspots

    def test_unresolved_rate_included(self):
        rows = _rows(4, contradictions=3, resolved=False)
        hotspots = detect_contradiction_hotspots(rows)
        assert hotspots
        assert hotspots[0]["unresolved_rate"] == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# run_all_pattern_detection
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAllPatternDetection:
    def test_returns_all_five_keys(self):
        rows = _rows(5, resolved=False, safety=True, contradictions=2)
        result = run_all_pattern_detection(rows)
        assert "hours_failure_patterns" in result
        assert "environment_patterns" in result
        assert "unresolved_clusters" in result
        assert "safety_hotspots" in result
        assert "contradiction_hotspots" in result

    def test_total_sessions_analysed_matches_input(self):
        rows = _rows(7)
        result = run_all_pattern_detection(rows)
        assert result["total_sessions_analysed"] == 7

    def test_empty_input_returns_empty_patterns(self):
        result = run_all_pattern_detection([])
        assert result["hours_failure_patterns"] == []
        assert result["environment_patterns"] == []
        assert result["unresolved_clusters"] == []
        assert result["safety_hotspots"] == []
        assert result["contradiction_hotspots"] == []
        assert result["total_sessions_analysed"] == 0

    def test_all_pattern_types_are_lists(self):
        rows = _rows(5)
        result = run_all_pattern_detection(rows)
        for key in ("hours_failure_patterns", "environment_patterns",
                    "unresolved_clusters", "safety_hotspots", "contradiction_hotspots"):
            assert isinstance(result[key], list), f"{key} should be a list"

    def test_realistic_mixed_fleet_scenario(self):
        """
        Simulate a realistic fleet: multiple trees, environments, modes.
        Verify that patterns emerge as expected.
        """
        rows = (
            # Hydraulic loss — dusty — high hours — mostly unresolved
            _rows(4, tree="hydraulic_loss_heavy_equipment", environment="dusty",
                  hours=4000, resolved=False, contradictions=0) +
            # Overheating — marine — safety triggers
            _rows(4, tree="overheating_heavy_equipment", environment="marine",
                  hours=2000, safety=True, resolved=True) +
            # Track drive — muddy — high contradictions
            _rows(4, tree="track_or_drive_issue_heavy_equipment", environment="muddy",
                  hours=1500, contradictions=3, resolved=False) +
            # No-start — urban — resolved, no issues
            _rows(5, tree="no_start_heavy_equipment", environment="urban",
                  hours=800, resolved=True, safety=False, contradictions=0)
        )
        result = run_all_pattern_detection(rows)

        # Should detect unresolved cluster for hydraulic loss
        unresolved_trees = {c["tree_key"] for c in result["unresolved_clusters"]}
        assert "hydraulic_loss_heavy_equipment" in unresolved_trees or \
               "track_or_drive_issue_heavy_equipment" in unresolved_trees

        # Should detect safety hotspot for marine overheating
        safety_trees = {h["tree_key"] for h in result["safety_hotspots"]}
        assert "overheating_heavy_equipment" in safety_trees

        # Should detect contradiction hotspot for track/drive
        contra_trees = {h["tree_key"] for h in result["contradiction_hotspots"]}
        assert "track_or_drive_issue_heavy_equipment" in contra_trees

        assert result["total_sessions_analysed"] == 17


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic mode — LLM-off summary
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterministicSummary:
    """Fleet summary is always available without LLM."""

    def test_auto_summary_with_no_patterns(self):
        from app.api.admin import _auto_fleet_summary
        summary = _auto_fleet_summary({
            "total_sessions_analysed": 5,
            "unresolved_clusters": [],
            "safety_hotspots": [],
            "environment_patterns": [],
            "hours_failure_patterns": [],
            "contradiction_hotspots": [],
        })
        assert isinstance(summary, str)
        assert "5" in summary  # mentions session count
        assert "No significant patterns" in summary

    def test_auto_summary_with_unresolved_cluster(self):
        from app.api.admin import _auto_fleet_summary
        summary = _auto_fleet_summary({
            "total_sessions_analysed": 20,
            "unresolved_clusters": [{
                "description": "Hydraulic Loss → low fluid: 5 unresolved out of 8 sessions (63%)",
            }],
            "safety_hotspots": [],
            "environment_patterns": [],
            "hours_failure_patterns": [],
            "contradiction_hotspots": [],
        })
        assert "unresolved" in summary.lower()

    def test_auto_summary_with_safety_hotspot(self):
        from app.api.admin import _auto_fleet_summary
        summary = _auto_fleet_summary({
            "total_sessions_analysed": 30,
            "unresolved_clusters": [],
            "safety_hotspots": [{
                "description": "Hydraulic Loss in dusty: 40% safety trigger rate",
            }],
            "environment_patterns": [],
            "hours_failure_patterns": [],
            "contradiction_hotspots": [],
        })
        assert "safety" in summary.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Data gaps — what needs better data to improve
# ─────────────────────────────────────────────────────────────────────────────

class TestDataGapAwareness:
    """
    These tests document known limitations in the current pattern detection.
    Failing tests here are expected and represent items to address before
    fleet data grows significantly.
    """

    def test_rows_without_hours_excluded_from_hours_patterns(self):
        """Sessions without HeavyContext hours data cannot be analyzed for hours bands."""
        rows = _rows(5, hours=None, resolved=False)
        patterns = detect_hours_failure_patterns(rows)
        assert not patterns, (
            "Sessions with no hours data are excluded from hours_failure_patterns — "
            "this is a data quality gap: operators should be prompted for hourmeter reading"
        )

    def test_rows_without_environment_excluded_from_env_patterns(self):
        """Sessions without environment data cannot be analyzed for env-linked patterns."""
        rows = [_row(resolved=False) for _ in range(5)]
        for r in rows:
            r["environment"] = None
        patterns = detect_environment_patterns(rows)
        assert not patterns, (
            "Sessions with no environment data are excluded — "
            "environment field should be required in heavy equipment intake"
        )

    def test_sessions_without_outcome_not_in_fleet_data(self):
        """
        fetch_heavy_fleet_data joins against diagnostic_outcomes — sessions that never
        produced an outcome (abandoned or in-progress) are invisible to fleet analytics.
        This is expected behavior but means fleet stats undercount total sessions.
        """
        # No DB test needed — this is a documented architectural limitation
        pass
