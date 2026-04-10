"""
Phase 9.5 — LLM Augmentation Layer unit tests.

Run with: pytest backend/tests/test_phase95.py -v

All LLM calls are mocked.  Tests verify:
  1.  Shadow hypotheses return valid structure and respect max count
  2.  Shadow hypotheses return empty list when LLM fails
  3.  Routing hints filter invalid / duplicate tree IDs
  4.  Routing hints return empty list when LLM fails
  5.  Evidence extractor returns normalized signals
  6.  Evidence extractor deduplicates normalized_key collisions
  7.  Evidence extractor returns empty list when LLM fails
  8.  Anomaly detector returns safe default when LLM fails
  9.  Anomaly detector enforces severity >= 0.4 for is_anomalous
  10. Anomaly detector respects ANOMALY_EXIT_THRESHOLD constant
  11. combine_candidates keeps deterministic primary dominant
  12. combine_candidates caps LLM-only candidate score
  13. combine_candidates boosts existing candidate modestly
  14. combine_candidates ignores hints for unknown trees
  15. System works with all LLM functions disabled
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.diagnostics.orchestrator.tree_router import (
    TreeCandidate,
    combine_candidates,
    should_use_discriminator,
)
from app.llm.anomaly_detector import ANOMALY_EXIT_THRESHOLD, detect_anomaly
from app.llm.evidence_extractor import extract_evidence
from app.llm.routing_hints import suggest_tree_candidates
from app.llm.shadow_hypotheses import generate_shadow_hypotheses


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _evidence_log(*sources: str) -> list[dict]:
    return [
        {"source": s, "observation": s, "normalized_key": s, "certainty": 0.9, "affects": {}}
        for s in sources
    ]


def _top_hyp(*pairs: tuple[str, float]) -> list[dict]:
    return [{"key": k, "label": k.replace("_", " "), "score": s} for k, s in pairs]


# ─────────────────────────────────────────────────────────────────────────────
# 1–2. Shadow hypothesis generator
# ─────────────────────────────────────────────────────────────────────────────

class TestShadowHypotheses:
    def test_returns_valid_structure(self):
        mock_response = '{"shadow_hypotheses": [{"hypothesis": "Cracked vacuum hose", "confidence": 0.6, "reasoning": "Fits the intermittent stall pattern", "related_tree": "rough_idle"}]}'
        with patch("app.llm.shadow_hypotheses._call", return_value=mock_response):
            result = generate_shadow_hypotheses(
                intake_text="Car stalls intermittently at idle",
                evidence_log=_evidence_log("intake", "user_text"),
                top_hypotheses=_top_hyp(("dirty_maf", 0.7), ("idle_control_valve", 0.5)),
                symptom_category="rough_idle",
                vehicle_context="2018 Honda Civic 1.5T",
            )
        assert len(result) == 1
        assert result[0]["hypothesis"] == "Cracked vacuum hose"
        assert 0.0 <= result[0]["confidence"] <= 1.0
        assert isinstance(result[0]["reasoning"], str)
        assert result[0]["related_tree"] == "rough_idle"

    def test_caps_at_three_hypotheses(self):
        many = [
            {"hypothesis": f"Cause {i}", "confidence": 0.5, "reasoning": "reason", "related_tree": None}
            for i in range(6)
        ]
        mock_response = f'{{"shadow_hypotheses": {__import__("json").dumps(many)}}}'
        with patch("app.llm.shadow_hypotheses._call", return_value=mock_response):
            result = generate_shadow_hypotheses(
                intake_text="engine won't start",
                evidence_log=_evidence_log("intake"),
                top_hypotheses=[],
                symptom_category="crank_no_start",
                vehicle_context="2015 Ford F-150",
            )
        assert len(result) <= 3

    def test_returns_empty_on_llm_failure(self):
        with patch("app.llm.shadow_hypotheses._call", side_effect=Exception("network error")):
            result = generate_shadow_hypotheses(
                intake_text="car won't start",
                evidence_log=_evidence_log("intake"),
                top_hypotheses=[],
                symptom_category="crank_no_start",
                vehicle_context="Unknown vehicle",
            )
        assert result == []

    def test_returns_empty_for_blank_intake(self):
        result = generate_shadow_hypotheses(
            intake_text="",
            evidence_log=[],
            top_hypotheses=[],
            symptom_category="unknown",
            vehicle_context="Unknown",
        )
        assert result == []

    def test_filters_incomplete_entries(self):
        mock_response = '{"shadow_hypotheses": [{"hypothesis": "", "confidence": 0.5, "reasoning": "something"}, {"hypothesis": "Real cause", "confidence": 0.6, "reasoning": "valid reasoning", "related_tree": null}]}'
        with patch("app.llm.shadow_hypotheses._call", return_value=mock_response):
            result = generate_shadow_hypotheses(
                intake_text="noise when braking",
                evidence_log=_evidence_log("intake"),
                top_hypotheses=[],
                symptom_category="brakes",
                vehicle_context="2020 Toyota Camry",
            )
        # Empty-hypothesis entry filtered out
        assert all(r["hypothesis"] for r in result)


# ─────────────────────────────────────────────────────────────────────────────
# 3–4. Routing hints
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingHints:
    def test_returns_valid_tree_candidate(self):
        mock_response = '{"candidates": [{"tree_id": "transmission", "confidence": 0.65, "reasoning": "User mentions slipping gears"}]}'
        with patch("app.llm.routing_hints._call", return_value=mock_response):
            result = suggest_tree_candidates(
                intake_text="car slips gears and won't start sometimes",
                symptom_category="rough_idle",
                vehicle_context="2017 Chevy Silverado",
                existing_candidates=[{"tree_id": "rough_idle", "score": 0.85, "reasons": []}],
            )
        assert len(result) == 1
        assert result[0]["tree_id"] == "transmission"
        assert result[0]["confidence"] >= 0.4

    def test_filters_invalid_tree_id(self):
        mock_response = '{"candidates": [{"tree_id": "invented_tree", "confidence": 0.8, "reasoning": "exists"}]}'
        with patch("app.llm.routing_hints._call", return_value=mock_response):
            result = suggest_tree_candidates(
                intake_text="engine problem",
                symptom_category="rough_idle",
                vehicle_context="2015 Honda CR-V",
                existing_candidates=[],
            )
        assert result == []

    def test_does_not_duplicate_existing_candidates(self):
        mock_response = '{"candidates": [{"tree_id": "rough_idle", "confidence": 0.9, "reasoning": "same tree"}]}'
        with patch("app.llm.routing_hints._call", return_value=mock_response):
            result = suggest_tree_candidates(
                intake_text="rough idle problem",
                symptom_category="rough_idle",
                vehicle_context="2019 Nissan Altima",
                existing_candidates=[{"tree_id": "rough_idle", "score": 1.0, "reasons": []}],
            )
        assert result == []

    def test_filters_low_confidence(self):
        mock_response = '{"candidates": [{"tree_id": "brakes", "confidence": 0.2, "reasoning": "vague"}]}'
        with patch("app.llm.routing_hints._call", return_value=mock_response):
            result = suggest_tree_candidates(
                intake_text="noise when driving",
                symptom_category="strange_noise",
                vehicle_context="2020 Hyundai Elantra",
                existing_candidates=[],
            )
        assert result == []

    def test_returns_empty_on_llm_failure(self):
        with patch("app.llm.routing_hints._call", side_effect=Exception("timeout")):
            result = suggest_tree_candidates(
                intake_text="car won't start",
                symptom_category="crank_no_start",
                vehicle_context="Unknown",
                existing_candidates=[],
            )
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 5–7. Evidence extractor
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceExtractor:
    def test_returns_valid_signals(self):
        mock_response = '{"signals": [{"observation": "engine cranks without starting", "normalized_key": "cranks_no_start", "certainty": 0.95, "ambiguous": false}]}'
        with patch("app.llm.evidence_extractor._call", return_value=mock_response):
            result = extract_evidence(
                text_input="car turns over but won't fire",
                symptom_category="crank_no_start",
                vehicle_context="2016 Toyota Corolla",
            )
        assert len(result) == 1
        assert result[0]["normalized_key"] == "cranks_no_start"
        assert result[0]["affects"] == {}  # never modifies scores
        assert 0.0 <= result[0]["certainty"] <= 1.0
        assert isinstance(result[0]["ambiguous"], bool)

    def test_deduplicates_keys(self):
        duplicate = [
            {"observation": "obs1", "normalized_key": "same_key", "certainty": 0.9, "ambiguous": False},
            {"observation": "obs2", "normalized_key": "same_key", "certainty": 0.7, "ambiguous": False},
        ]
        import json
        mock_response = json.dumps({"signals": duplicate})
        with patch("app.llm.evidence_extractor._call", return_value=mock_response):
            result = extract_evidence(
                text_input="engine won't start and makes noise",
                symptom_category="crank_no_start",
                vehicle_context="2018 Ford Focus",
            )
        keys = [r["normalized_key"] for r in result]
        assert len(keys) == len(set(keys))

    def test_caps_at_four_signals(self):
        import json
        many = [
            {"observation": f"obs {i}", "normalized_key": f"obs_{i}", "certainty": 0.8, "ambiguous": False}
            for i in range(8)
        ]
        mock_response = json.dumps({"signals": many})
        with patch("app.llm.evidence_extractor._call", return_value=mock_response):
            result = extract_evidence(
                text_input="complex multi-symptom problem description with many details",
                symptom_category="unknown",
                vehicle_context="Unknown vehicle",
            )
        assert len(result) <= 4

    def test_returns_empty_on_llm_failure(self):
        with patch("app.llm.evidence_extractor._call", side_effect=Exception("error")):
            result = extract_evidence(
                text_input="car makes a strange noise when accelerating",
                symptom_category="strange_noise",
                vehicle_context="2014 BMW 328i",
            )
        assert result == []

    def test_skips_short_input(self):
        result = extract_evidence("car", "unknown", "Unknown")
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 8–10. Anomaly detector
# ─────────────────────────────────────────────────────────────────────────────

class TestAnomalyDetector:
    def test_returns_safe_default_on_failure(self):
        with patch("app.llm.anomaly_detector._call", side_effect=Exception("network error")):
            result = detect_anomaly(
                intake_text="car won't start",
                evidence_log=_evidence_log("intake", "user_text"),
                top_hypotheses=_top_hyp(("dead_battery", 0.8)),
                symptom_category="no_crank",
                vehicle_context="2019 Toyota Camry",
            )
        assert result["is_anomalous"] is False
        assert result["severity"] == 0.0
        assert result["suggested_action"] is None

    def test_returns_safe_default_when_no_evidence(self):
        result = detect_anomaly(
            intake_text="car won't start",
            evidence_log=[],
            top_hypotheses=[],
            symptom_category="no_crank",
            vehicle_context="Unknown",
        )
        assert result["is_anomalous"] is False

    def test_enforces_severity_threshold_for_anomalous(self):
        # LLM says is_anomalous=True but severity=0.2 — should be overridden to False
        mock_response = '{"is_anomalous": true, "reason": "mild issue", "severity": 0.2, "suggested_action": null}'
        with patch("app.llm.anomaly_detector._call", return_value=mock_response):
            result = detect_anomaly(
                intake_text="car stalls sometimes",
                evidence_log=_evidence_log("intake"),
                top_hypotheses=_top_hyp(("fuel_pump", 0.6)),
                symptom_category="rough_idle",
                vehicle_context="2015 Honda Civic",
            )
        assert result["is_anomalous"] is False

    def test_anomaly_detected_at_or_above_threshold(self):
        mock_response = '{"is_anomalous": true, "reason": "brake and engine light both on", "severity": 0.7, "suggested_action": "Ask if both lights came on at the same time"}'
        with patch("app.llm.anomaly_detector._call", return_value=mock_response):
            result = detect_anomaly(
                intake_text="brakes feel soft and check engine light is on",
                evidence_log=_evidence_log("intake", "user_text", "image"),
                top_hypotheses=_top_hyp(("brake_fluid_low", 0.7)),
                symptom_category="brakes",
                vehicle_context="2017 Ford Escape",
            )
        assert result["is_anomalous"] is True
        assert result["severity"] >= ANOMALY_EXIT_THRESHOLD
        assert isinstance(result["suggested_action"], str)

    def test_anomaly_exit_threshold_constant(self):
        # Threshold should be >= 0.5 to avoid suppressing too many exits
        assert ANOMALY_EXIT_THRESHOLD >= 0.5
        assert ANOMALY_EXIT_THRESHOLD <= 0.9


# ─────────────────────────────────────────────────────────────────────────────
# 11–14. combine_candidates
# ─────────────────────────────────────────────────────────────────────────────

class TestCombineCandidates:
    def _make_det(self, *pairs: tuple[str, float]) -> list[TreeCandidate]:
        return [TreeCandidate(tree_id=t, score=s, reasons=[f"det:{t}"]) for t, s in pairs]

    def test_deterministic_primary_stays_dominant(self):
        det = self._make_det(("crank_no_start", 0.95), ("no_crank", 0.40))
        hints = [{"tree_id": "no_crank", "confidence": 0.99, "reasoning": "LLM very confident"}]
        merged = combine_candidates(det, hints)
        assert merged[0].tree_id == "crank_no_start"
        assert merged[0].score >= merged[1].score

    def test_llm_only_candidate_score_capped(self):
        det = self._make_det(("crank_no_start", 0.90))
        hints = [{"tree_id": "rough_idle", "confidence": 1.0, "reasoning": "LLM hint"}]
        merged = combine_candidates(det, hints)
        llm_cand = next((c for c in merged if c.tree_id == "rough_idle"), None)
        assert llm_cand is not None
        # LLM-only score must be below 35% of deterministic primary
        assert llm_cand.score < det[0].score * 0.40

    def test_boost_to_existing_candidate_is_modest(self):
        original_score = 0.50
        det = self._make_det(("crank_no_start", 0.85), ("no_crank", original_score))
        hints = [{"tree_id": "no_crank", "confidence": 0.9, "reasoning": "LLM boost"}]
        merged = combine_candidates(det, hints)
        boosted = next(c for c in merged if c.tree_id == "no_crank")
        # Should be a small boost, not a large one
        assert boosted.score > original_score
        assert boosted.score < det[0].score  # must not surpass primary

    def test_ignores_unknown_trees(self):
        det = self._make_det(("rough_idle", 0.90))
        hints = [{"tree_id": "invented_symptom", "confidence": 0.9, "reasoning": "fake"}]
        merged = combine_candidates(det, hints)
        assert all(c.tree_id != "invented_symptom" for c in merged)
        assert len(merged) == 1

    def test_caps_at_three_candidates(self):
        det = self._make_det(
            ("rough_idle", 0.90),
            ("loss_of_power", 0.50),
        )
        hints = [
            {"tree_id": "crank_no_start", "confidence": 0.7, "reasoning": "hint 1"},
            {"tree_id": "no_crank", "confidence": 0.65, "reasoning": "hint 2"},
            {"tree_id": "overheating", "confidence": 0.55, "reasoning": "hint 3"},
        ]
        merged = combine_candidates(det, hints)
        assert len(merged) <= 3

    def test_returns_sorted_descending(self):
        det = self._make_det(("brakes", 0.75), ("suspension", 0.45))
        hints = [{"tree_id": "transmission", "confidence": 0.6, "reasoning": "hint"}]
        merged = combine_candidates(det, hints)
        scores = [c.score for c in merged]
        assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 15. System operates normally when all LLM augmentation functions are disabled
# ─────────────────────────────────────────────────────────────────────────────

class TestGracefulDegradation:
    """Verify every Phase 9.5 function returns a safe, non-breaking value on failure."""

    def test_all_functions_degrade_gracefully(self):
        side_effect = Exception("LLM offline")

        with patch("app.llm.shadow_hypotheses._call", side_effect=side_effect):
            assert generate_shadow_hypotheses("text", [], [], "rough_idle", "vehicle") == []

        with patch("app.llm.routing_hints._call", side_effect=side_effect):
            assert suggest_tree_candidates("text", "rough_idle", "vehicle", []) == []

        with patch("app.llm.evidence_extractor._call", side_effect=side_effect):
            assert extract_evidence("text that is long enough to pass the length check", "rough_idle", "vehicle") == []

        with patch("app.llm.anomaly_detector._call", side_effect=side_effect):
            result = detect_anomaly("text", [{"source": "intake"}], [], "rough_idle", "vehicle")
            assert result["is_anomalous"] is False
            assert result["severity"] == 0.0
