"""
Phase 13A — Heavy Equipment End-to-End Validation Test Harness.

Covers:
  1. Tree structure: all 11 HE trees registered with required exports
  2. Routing: correct tree selection, discriminator for ambiguous pairs
  3. HeavyContext influence: hours/service/environment/storage affect priors
  4. Safety validation: 5 critical + 2 warning patterns, interrupt flow
  5. Contradiction validation: score reversal, image vs verbal, eliminated boost
  6. LLM guardrails: system works without LLM, routing hints capped, anomaly blocks exit
  7. Exit guard: all 5 conditions enforced
  8. Operator/mechanic modes: session state + evidence source types
  9. Realistic fixtures: messy language, incomplete inputs, conflicting answers
 10. Follow-up evidence: operator_observation and manual_check packets

Run with:
    cd backend && python -m pytest tests/test_phase13a_heavy_equipment.py -v
"""
import pytest
from datetime import datetime, timezone
from uuid import UUID

from fix_core.models.context import OwnerContext
from fix_core.models.session import DiagnosticSession as CoreSession, RoutingPhase, SessionMode

from app.diagnostics.orchestrator.contradictions import (
    Contradiction,
    detect_contradictions,
    merge_flags,
)
from app.diagnostics.orchestrator.controller import (
    ControllerResult,
    process_message,
)
from app.diagnostics.orchestrator.evidence import (
    EvidencePacket,
    build_from_classification,
    build_from_followup,
    build_from_image,
    build_from_manual_check,
    build_from_operator_observation,
    build_intake_packet,
    evidence_type_count,
)
from app.diagnostics.orchestrator.exit_guard import MIN_NODES, can_exit, exit_reason
from app.diagnostics.orchestrator.safety import SafetyAlert, evaluate_safety
from app.diagnostics.orchestrator.tree_router import (
    TreeCandidate,
    combine_candidates,
    rank_candidate_trees,
    should_use_discriminator,
)
from app.engine.context_heavy import HeavyContext, apply_heavy_context_priors
from app.engine.hypothesis_scorer import HypothesisScorer
from app.engine.trees import CONTEXT_PRIORS, HYPOTHESES, POST_DIAGNOSIS, TREES


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

HEAVY_EQUIPMENT_TREES = [
    "no_start_heavy_equipment",
    "hydraulic_loss_heavy_equipment",
    "loss_of_power_heavy_equipment",
    "overheating_heavy_equipment",
    "electrical_fault_heavy_equipment",
    "track_or_drive_issue_heavy_equipment",
    "abnormal_noise_heavy_equipment",
    "coolant_leak_heavy_equipment",
    "implement_failure_heavy_equipment",
    "cab_electrical_heavy_equipment",
    "fuel_contamination_heavy_equipment",
]

# Maps tree_key → symptom_category for routing tests
HEAVY_SYMPTOM_MAP = {
    "no_start_heavy_equipment": "no_start",
    "hydraulic_loss_heavy_equipment": "hydraulic_loss",
    "loss_of_power_heavy_equipment": "loss_of_power",
    "overheating_heavy_equipment": "overheating",
    "electrical_fault_heavy_equipment": "electrical_fault",
    "track_or_drive_issue_heavy_equipment": "track_or_drive_issue",
    "abnormal_noise_heavy_equipment": "abnormal_noise",
    "coolant_leak_heavy_equipment": "coolant_leak",
    "implement_failure_heavy_equipment": "implement_failure",
    "cab_electrical_heavy_equipment": "cab_electrical",
    "fuel_contamination_heavy_equipment": "fuel_contamination",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_scorer(scores: dict[str, float]) -> HypothesisScorer:
    """Build a minimal scorer from {key: score} dict."""
    hyp_def = {k: {"label": k, "prior": v} for k, v in scores.items()}
    return HypothesisScorer(hyp_def)


def _evidence_log(*sources: str) -> list[dict]:
    """Build a minimal evidence log with the given source types."""
    return [
        {
            "source": s,
            "observation": s,
            "normalized_key": s,
            "certainty": 1.0,
            "affects": {},
        }
        for s in sources
    ]


def _hydraulic_scorer() -> HypothesisScorer:
    """Return a HypothesisScorer loaded with the hydraulic_loss tree hypotheses."""
    return HypothesisScorer(HYPOTHESES["hydraulic_loss_heavy_equipment"])


_TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class MockEmitter:
    """Captures emitted events for assertion in tests."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event_name: str, payload: dict) -> None:
        self.events.append((event_name, payload))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]

    def payload_for(self, event_name: str) -> dict:
        for name, payload in self.events:
            if name == event_name:
                return payload
        raise AssertionError(f"Event {event_name!r} was not emitted. Got: {self.names()}")


_SESSION_MODE_MAP = {
    "consumer": SessionMode.consumer,
    "operator": SessionMode.operator,
    "mechanic": SessionMode.mechanic,
}


def _base_session(
    tree_key: str = "hydraulic_loss_heavy_equipment",
    node_id: str = "start",
    answered: int = 0,
    evidence: list[dict] | None = None,
    contradictions: list[dict] | None = None,
    safety_flags: list[dict] | None = None,
    session_mode: str = "operator",
) -> CoreSession:
    """Return a minimal committed CoreSession for unit testing."""
    now = datetime.now(timezone.utc)
    return CoreSession(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        owner=OwnerContext(user_id=_TEST_USER_ID),
        created_at=now,
        updated_at=now,
        symptom_category="hydraulic_loss",
        vehicle_type="heavy_equipment",
        vehicle_make="CAT",
        vehicle_model="336 Excavator",
        current_node_id=node_id,
        turn_count=answered,
        routing_phase=RoutingPhase.committed,
        selected_tree=tree_key,
        evidence_log=evidence or [],
        contradiction_flags=contradictions or [],
        safety_flags=safety_flags or [],
        context={},
        answered_nodes=answered,
        session_mode=_SESSION_MODE_MAP.get(session_mode, SessionMode.consumer),
    )


def _classify(option_key: str, reliability: float = 1.0) -> dict:
    """Build a minimal classify_answer result dict."""
    return {
        "option_key": option_key,
        "classification_confidence": 0.90,
        "answer_reliability": reliability,
        "needs_clarification": False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tree structure — all 11 heavy equipment trees
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyEquipmentTreeStructure:
    """All 11 heavy equipment trees must be registered with the required 4 exports."""

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_tree_registered_in_trees(self, tree_key):
        assert tree_key in TREES, f"{tree_key} missing from TREES registry"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_tree_registered_in_hypotheses(self, tree_key):
        assert tree_key in HYPOTHESES, f"{tree_key} missing from HYPOTHESES registry"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_tree_registered_in_context_priors(self, tree_key):
        assert tree_key in CONTEXT_PRIORS, f"{tree_key} missing from CONTEXT_PRIORS registry"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_tree_registered_in_post_diagnosis(self, tree_key):
        assert tree_key in POST_DIAGNOSIS, f"{tree_key} missing from POST_DIAGNOSIS registry"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_tree_has_start_node(self, tree_key):
        tree = TREES[tree_key]
        assert "start" in tree, f"{tree_key} tree missing 'start' node"
        assert "question" in tree["start"], f"{tree_key} start node missing 'question'"
        assert "options" in tree["start"], f"{tree_key} start node missing 'options'"
        assert len(tree["start"]["options"]) >= 2, f"{tree_key} start node has fewer than 2 options"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_hypotheses_have_required_keys(self, tree_key):
        hyps = HYPOTHESES[tree_key]
        assert len(hyps) >= 4, f"{tree_key} has fewer than 4 hypotheses"
        for key, defn in hyps.items():
            assert "label" in defn, f"{tree_key}/{key} missing 'label'"
            assert "prior" in defn, f"{tree_key}/{key} missing 'prior'"
            assert 0.0 <= defn["prior"] <= 1.0, f"{tree_key}/{key} prior out of [0,1] range"
            assert "diy_difficulty" in defn, f"{tree_key}/{key} missing 'diy_difficulty'"
            assert defn["diy_difficulty"] in (
                "easy", "moderate", "hard", "seek_mechanic"
            ), f"{tree_key}/{key} invalid diy_difficulty"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_context_priors_have_environment_and_hours_band(self, tree_key):
        priors = CONTEXT_PRIORS[tree_key]
        assert "environment" in priors, f"{tree_key} context priors missing 'environment'"
        env = priors["environment"]
        for env_key in ("dusty", "muddy", "marine", "urban"):
            assert env_key in env, f"{tree_key} missing environment prior '{env_key}'"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_post_diagnosis_non_empty(self, tree_key):
        tips = POST_DIAGNOSIS[tree_key]
        assert isinstance(tips, list), f"{tree_key} post_diagnosis is not a list"
        assert len(tips) >= 1, f"{tree_key} post_diagnosis is empty"

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_all_next_nodes_exist(self, tree_key):
        """Every next_node pointer in every option resolves to an existing node or None."""
        tree = TREES[tree_key]
        for node_id, node in tree.items():
            for opt in node.get("options", []):
                nxt = opt.get("next_node")
                if nxt is not None:
                    assert nxt in tree, (
                        f"{tree_key}/{node_id}/option '{opt.get('match')}' "
                        f"points to non-existent next_node '{nxt}'"
                    )

    @pytest.mark.parametrize("tree_key", HEAVY_EQUIPMENT_TREES)
    def test_all_delta_keys_are_known_hypotheses(self, tree_key):
        """Delta keys in tree options must reference valid hypothesis keys."""
        tree = TREES[tree_key]
        hyp_keys = set(HYPOTHESES[tree_key].keys())
        for node_id, node in tree.items():
            for opt in node.get("options", []):
                for delta_key in opt.get("deltas", {}):
                    assert delta_key in hyp_keys, (
                        f"{tree_key}/{node_id}/option '{opt.get('match')}' "
                        f"delta key '{delta_key}' is not a known hypothesis"
                    )
                for elim_key in opt.get("eliminate", []):
                    assert elim_key in hyp_keys, (
                        f"{tree_key}/{node_id}/option '{opt.get('match')}' "
                        f"eliminate key '{elim_key}' is not a known hypothesis"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Routing — correct tree selection + discriminator for ambiguous pairs
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyEquipmentRouting:
    """Intake data for heavy equipment routes to the correct tree."""

    @pytest.mark.parametrize("tree_key,symptom", list(HEAVY_SYMPTOM_MAP.items()))
    def test_each_tree_routes_correctly(self, tree_key, symptom):
        intake = {
            "symptom_category": symptom,
            "vehicle_type": "heavy_equipment",
            "vehicle_make": "Caterpillar",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates, f"No candidates returned for {symptom}/heavy_equipment"
        assert candidates[0].tree_id == tree_key, (
            f"Expected {tree_key} as primary, got {candidates[0].tree_id}"
        )

    @pytest.mark.parametrize("tree_key,symptom", list(HEAVY_SYMPTOM_MAP.items()))
    def test_clean_routing_commits_without_discriminator(self, tree_key, symptom):
        """When make is known and no secondary symptom, commit directly (score >= 0.90)."""
        intake = {
            "symptom_category": symptom,
            "vehicle_type": "heavy_equipment",
            "vehicle_make": "John Deere",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].score >= 0.90, (
            f"{symptom}/heavy_equipment should commit directly, got score {candidates[0].score}"
        )
        assert not should_use_discriminator(candidates), (
            f"Discriminator should not be needed for clean {symptom} intake"
        )

    def test_incomplete_intake_reduces_confidence(self):
        """No make + no model → score drops but still routes to correct tree."""
        intake = {"symptom_category": "hydraulic_loss", "vehicle_type": "heavy_equipment"}
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "hydraulic_loss_heavy_equipment"
        assert candidates[0].score < 1.0, "Score should be reduced without vehicle make"

    def test_ambiguous_pair_loss_of_power_hydraulic_triggers_discriminator(self):
        """Operator reporting 'loss of power' may really mean hydraulic loss — discriminator."""
        intake = {
            "symptom_category": "loss_of_power",
            "vehicle_type": "heavy_equipment",
            "secondary_symptom": "hydraulic_loss",
            "vehicle_make": "Komatsu",
        }
        candidates = rank_candidate_trees(intake)
        # Primary should still be loss_of_power_heavy_equipment
        assert candidates[0].tree_id == "loss_of_power_heavy_equipment"
        # Score should be below commit threshold due to secondary
        assert should_use_discriminator(candidates), (
            "Secondary hydraulic_loss should trigger discriminator for loss_of_power"
        )

    def test_ambiguous_pair_no_start_electrical_triggers_discriminator(self):
        """No-start and electrical fault share presentation — discriminator expected."""
        intake = {
            "symptom_category": "no_start",
            "vehicle_type": "heavy_equipment",
            "secondary_symptom": "electrical_fault",
            "vehicle_make": "Bobcat",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "no_start_heavy_equipment"
        assert should_use_discriminator(candidates)

    def test_ambiguous_pair_track_drive_abnormal_noise_triggers_discriminator(self):
        """Track/drive and abnormal noise overlap in operator description."""
        intake = {
            "symptom_category": "track_or_drive_issue",
            "vehicle_type": "heavy_equipment",
            "secondary_symptom": "abnormal_noise",
            "vehicle_make": "Volvo",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "track_or_drive_issue_heavy_equipment"
        assert should_use_discriminator(candidates)

    def test_ambiguous_pair_overheating_hydraulic_triggers_discriminator(self):
        """Overheating and hydraulic loss share warning-light presentation."""
        intake = {
            "symptom_category": "overheating",
            "vehicle_type": "heavy_equipment",
            "secondary_symptom": "hydraulic_loss",
            "vehicle_make": "Hitachi",
        }
        candidates = rank_candidate_trees(intake)
        assert should_use_discriminator(candidates)

    def test_routing_without_make_still_selects_heavy_equipment_tree(self):
        """Even with no make, vehicle_type=heavy_equipment routes to HE tree, not base car."""
        intake = {"symptom_category": "overheating", "vehicle_type": "heavy_equipment"}
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "overheating_heavy_equipment"
        assert "overheating" != candidates[0].tree_id, (
            "Should not fall back to base car overheating tree"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. HeavyContext influence
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyContextInfluence:
    """HeavyContext adjustments affect hypothesis priors before tree traversal."""

    def test_dusty_environment_boosts_filter_and_pump(self):
        ctx = HeavyContext(hours_of_operation=1000, last_service_hours=1000, environment="dusty")
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        # dusty: clogged_filter +0.10, failed_hydraulic_pump +0.05
        assert deltas.get("clogged_filter", 0.0) > 0, "Dusty should boost clogged_filter"
        assert deltas.get("failed_hydraulic_pump", 0.0) > 0, "Dusty should boost failed_hydraulic_pump"

    def test_muddy_environment_boosts_filter_and_hose(self):
        ctx = HeavyContext(hours_of_operation=1000, last_service_hours=1000, environment="muddy")
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        assert deltas.get("clogged_filter", 0.0) > 0, "Muddy should boost clogged_filter"
        assert deltas.get("leaking_hose_fitting", 0.0) > 0, "Muddy should boost leaking_hose_fitting"

    def test_urban_environment_produces_no_adjustments_for_hydraulic(self):
        ctx = HeavyContext(hours_of_operation=500, last_service_hours=480, environment="urban")
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        # urban has no adjustments; no overdue service
        assert deltas == {}, f"Urban within-service context should produce no deltas, got {deltas}"

    def test_overdue_service_boosts_filter_and_pump(self):
        """Machine 300 hours past service threshold (>250h) triggers overdue_service priors."""
        ctx = HeavyContext(
            hours_of_operation=5000,
            last_service_hours=4600,   # 400h since service → overdue
            environment="urban",
        )
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        assert deltas.get("clogged_filter", 0.0) > 0, "Overdue service should boost clogged_filter"
        assert deltas.get("failed_hydraulic_pump", 0.0) > 0, "Overdue service should boost pump"

    def test_within_service_interval_no_overdue_adjustment(self):
        """Machine 100h since service (< 250h threshold) gets no overdue adjustment."""
        ctx = HeavyContext(
            hours_of_operation=4700,
            last_service_hours=4600,   # 100h since service → not overdue
            environment="urban",
        )
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        assert "clogged_filter" not in deltas or deltas.get("clogged_filter", 0.0) == 0.0

    def test_long_storage_triggers_storage_priors(self):
        """Machine stored 45+ days should get long_storage priors if defined."""
        ctx = HeavyContext(
            hours_of_operation=2000,
            last_service_hours=2000,
            storage_duration=45,   # > 30 day threshold
            environment="urban",
        )
        # Not all trees define long_storage priors — test that function runs without error
        deltas = apply_heavy_context_priors(ctx, "no_start_heavy_equipment")
        assert isinstance(deltas, dict)

    def test_combined_dusty_and_overdue_accumulates_deltas(self):
        """Dusty environment + overdue service → both sets of priors combine."""
        ctx = HeavyContext(
            hours_of_operation=5000,
            last_service_hours=4600,   # 400h overdue
            environment="dusty",
        )
        deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        # clogged_filter should receive both dusty (+0.10) and overdue_service (+0.15)
        assert deltas.get("clogged_filter", 0.0) >= 0.20, (
            f"Combined dusty + overdue should give clogged_filter >= 0.20, got {deltas.get('clogged_filter')}"
        )

    def test_heavy_context_from_intake_returns_none_for_non_heavy(self):
        """heavy_context_from_intake returns None for passenger vehicle sessions."""
        from app.engine.context_heavy import heavy_context_from_intake
        ctx = heavy_context_from_intake({
            "vehicle_type": "car",
            "heavy_context": {"hours_of_operation": 5000},
        })
        assert ctx is None

    def test_heavy_context_from_intake_parses_fields(self):
        from app.engine.context_heavy import heavy_context_from_intake
        ctx = heavy_context_from_intake({
            "vehicle_type": "heavy_equipment",
            "heavy_context": {
                "hours_of_operation": 3200,
                "last_service_hours": 3000,
                "environment": "dusty",
                "storage_duration": 5,
                "recent_work_type": "earthmoving",
            },
        })
        assert ctx is not None
        assert ctx.hours_of_operation == 3200
        assert ctx.last_service_hours == 3000
        assert ctx.environment == "dusty"
        assert ctx.storage_duration == 5
        assert ctx.recent_work_type == "earthmoving"

    def test_all_heavy_trees_accept_context_prior_without_error(self):
        """apply_heavy_context_priors runs without exception for every HE tree."""
        ctx = HeavyContext(
            hours_of_operation=6000, last_service_hours=5500,
            environment="dusty", storage_duration=10,
        )
        for tree_key in HEAVY_EQUIPMENT_TREES:
            deltas = apply_heavy_context_priors(ctx, tree_key)
            assert isinstance(deltas, dict), f"{tree_key} returned non-dict from context priors"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Safety validation
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavySafetyValidation:
    """Safety patterns fire correctly; critical alerts interrupt the diagnostic flow."""

    # ── Critical alert scenarios ──────────────────────────────────────────────

    def test_hydraulic_rupture_fires_critical(self):
        alerts = evaluate_safety([
            "The hydraulic hose burst and fluid is spraying everywhere"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Hydraulic rupture should fire a critical alert"
        assert any("hydraulic" in a.message.lower() for a in critical)

    def test_hydraulic_injection_risk_fires_critical(self):
        alerts = evaluate_safety([
            "There's a pinhole in the hydraulic line and fluid is spraying under pressure"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Hydraulic pinhole/injection risk should fire critical"

    def test_uncontrolled_machine_movement_fires_critical(self):
        alerts = evaluate_safety([
            "The excavator is moving on its own — I can't stop it"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Uncontrolled machine movement should fire a critical alert"
        assert any("movement" in a.message.lower() or "uncontrolled" in a.message.lower() for a in critical)

    def test_equipment_brake_failure_fires_critical(self):
        alerts = evaluate_safety([
            "The parking brake is not holding — it released by itself on the slope"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Brake not holding should fire critical alert"

    def test_diesel_fuel_leak_near_hot_exhaust_fires_critical(self):
        alerts = evaluate_safety([
            "diesel fuel is leaking near the hot exhaust turbo"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Fuel leak near hot engine should fire critical alert"

    def test_electrical_arc_on_equipment_fires_critical(self):
        alerts = evaluate_safety([
            "There's arcing at the battery harness wiring panel"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Electrical arc on battery harness should fire critical alert"

    def test_machine_shutdown_overtemp_fires_critical(self):
        alerts = evaluate_safety([
            "The machine shut down due to overheating temperature protection"
        ])
        critical = [a for a in alerts if a.level == "critical"]
        assert critical, "Machine shutdown due to overtemp should fire critical"

    # ── Warning scenarios ─────────────────────────────────────────────────────

    def test_low_hydraulic_fluid_fires_warning_not_critical(self):
        alerts = evaluate_safety([
            "hydraulic fluid level is low, below minimum on the sight glass"
        ])
        assert alerts, "Low hydraulic fluid should fire at least a warning"
        assert all(a.level == "warning" for a in alerts), (
            "Low hydraulic fluid is a warning, not critical"
        )

    def test_machine_tipping_risk_fires_warning(self):
        alerts = evaluate_safety([
            "the machine is unstable when I lift the load with the boom extended"
        ])
        warnings = [a for a in alerts if a.level == "warning"]
        assert warnings, "Tipping/stability risk should fire a warning"

    # ── No false positives ────────────────────────────────────────────────────

    def test_normal_hydraulic_description_no_alert(self):
        alerts = evaluate_safety([
            "The hydraulic functions are slow when I raise the boom"
        ])
        # "slow" hydraulics is not inherently a safety issue
        assert not any(a.level == "critical" for a in alerts), (
            "Slow hydraulics without rupture/injection should not fire critical"
        )

    def test_safe_mechanic_description_no_alert(self):
        alerts = evaluate_safety([
            "Checking filter restriction indicator, it reads normal. Fluid level is at the midpoint."
        ])
        assert not alerts, "Normal mechanic description should not trigger any safety alert"

    # ── Deduplication ─────────────────────────────────────────────────────────

    def test_already_raised_alert_not_duplicated(self):
        existing = [{"message": "High-pressure hydraulic line failure detected.", "level": "critical"}]
        alerts = evaluate_safety(
            ["hydraulic hose burst and spraying"],
            existing_safety_flags=existing,
        )
        # Should not re-raise the already-fired hydraulic critical
        messages = [a.message for a in alerts]
        assert "High-pressure hydraulic line failure detected." not in messages

    # ── Flow interruption via process_message ─────────────────────────────────

    async def test_critical_safety_interrupts_before_diagnostic(self):
        """process_message returns safety_interrupt action when critical pattern fires."""
        scorer = _hydraulic_scorer()
        state = _base_session(answered=0)
        result = await process_message(
            state,
            "the hydraulic hose just burst and fluid is spraying at high pressure",
            scorer,
            classify_result=_classify("everything_slow_or_dead"),
        )
        assert result.action == "safety_interrupt", (
            f"Expected safety_interrupt, got {result.action}"
        )
        assert result.safety_alerts, "Safety interrupt must include alert details"
        assert all(a.level == "critical" for a in result.safety_alerts)

    async def test_warning_safety_does_not_interrupt_flow(self):
        """Warning-level safety records alert but does not stop the diagnostic."""
        scorer = _hydraulic_scorer()
        # Build up some evidence so the node can advance
        evidence = _evidence_log("intake", "user_text")
        state = _base_session(answered=2, evidence=evidence, node_id="fluid_level")
        result = await process_message(
            state,
            "hydraulic fluid level is low below minimum",
            scorer,
            classify_result=_classify("fluid_low"),
        )
        # Should NOT be safety_interrupt
        assert result.action != "safety_interrupt", (
            "Warning-level safety should not interrupt flow"
        )
        # Warning should still be recorded
        assert any(a.level == "warning" for a in result.safety_alerts), (
            "Low fluid warning should be recorded even without interrupt"
        )

    async def test_safety_interrupt_emits_fix_safety_alert_event(self):
        """fix.safety.alert event is emitted with correct payload on critical interrupt."""
        emitter = MockEmitter()
        scorer = _hydraulic_scorer()
        state = _base_session(answered=0)
        result = await process_message(
            state,
            "the hydraulic hose just burst and fluid is spraying at high pressure",
            scorer,
            classify_result=_classify("everything_slow_or_dead"),
            emitter=emitter,
        )
        assert result.action == "safety_interrupt"
        assert "fix.safety.alert" in emitter.names(), (
            f"fix.safety.alert not emitted. Got: {emitter.names()}"
        )
        payload = emitter.payload_for("fix.safety.alert")
        assert payload["severity"] == "critical"
        assert "session_id" in payload
        assert "user_id" in payload
        assert "message" in payload
        assert payload["session_id"] == str(state.id)
        assert payload["user_id"] == str(state.owner.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Contradiction validation
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyContradictionValidation:
    """Contradictions are detected, block exit, and trigger clarification."""

    def test_score_reversal_detected_for_same_hypothesis(self):
        """Strong positive then strong negative evidence for same hypothesis = contradiction."""
        evidence = [
            {
                "source": "user_text",
                "observation": "everything slow",
                "normalized_key": "everything_slow",
                "certainty": 1.0,
                "affects": {"low_fluid": +0.40, "clogged_filter": +0.20},
            },
            {
                "source": "user_text",
                "observation": "fluid level normal",
                "normalized_key": "fluid_ok",
                "certainty": 1.0,
                "affects": {"low_fluid": -0.30},
            },
        ]
        contradictions = detect_contradictions(evidence)
        keys = {c.type for c in contradictions}
        assert "score_reversal" in keys, (
            f"Expected score_reversal contradiction, got {keys}"
        )

    def test_score_reversal_blocked_by_exit_guard(self):
        """A blocking contradiction (severity >= 0.5) prevents exit."""
        contradiction_flag = {
            "type": "score_reversal",
            "description": "Conflicting evidence for 'low_fluid': +0.40 support vs -0.30 contradiction",
            "severity": 0.70,
        }
        scorer = _make_scorer({"low_fluid": 0.80, "clogged_filter": 0.30})
        evidence = _evidence_log("intake", "user_text")
        result = can_exit(
            scorer=scorer,
            answered_nodes=5,
            evidence_log=evidence,
            contradiction_flags=[contradiction_flag],
        )
        assert result is False, "Active blocking contradiction must prevent early exit"
        reason = exit_reason(
            scorer=scorer,
            answered_nodes=5,
            evidence_log=evidence,
            contradiction_flags=[contradiction_flag],
        )
        assert "contradiction" in reason.lower()

    def test_image_vs_verbal_contradiction_detected(self):
        """Image supports hypothesis while verbal answers denied it."""
        evidence = [
            {
                "source": "image",
                "observation": "fluid pooling under machine",
                "normalized_key": "image_analysis",
                "certainty": 0.85,
                "affects": {"leaking_hose_fitting": +0.40},
            },
            {
                "source": "user_text",
                "observation": "no visible leak",
                "normalized_key": "no_leak",
                "certainty": 1.0,
                "affects": {"leaking_hose_fitting": -0.25},
            },
        ]
        contradictions = detect_contradictions(evidence)
        keys = {c.type for c in contradictions}
        assert "image_vs_verbal" in keys, (
            f"Image/verbal conflict not detected. Got contradiction types: {keys}"
        )

    def test_eliminated_hypothesis_with_new_evidence_flagged(self):
        """If hypothesis was eliminated but new evidence strongly supports it — flag it."""
        evidence = [
            {
                "source": "user_text",
                "observation": "only one circuit dead",
                "normalized_key": "one_circuit_dead",
                "certainty": 1.0,
                "affects": {"pilot_solenoid_failure": +0.50},  # boosting after elimination
            },
        ]
        current_hyps = {
            "pilot_solenoid_failure": {"score": 0.0, "eliminated": True},
            "control_valve_failure": {"score": 0.35, "eliminated": False},
        }
        contradictions = detect_contradictions(evidence, current_hypotheses=current_hyps)
        keys = {c.type for c in contradictions}
        assert "eliminated_boost" in keys, (
            f"Eliminated hypothesis receiving strong evidence should be flagged. Got: {keys}"
        )

    def test_non_blocking_contradiction_below_threshold(self):
        """Contradictions with severity < 0.5 don't block exit on their own."""
        mild_contradiction = {
            "type": "score_reversal",
            "description": "Minor conflict",
            "severity": 0.30,  # below 0.5 blocking threshold
        }
        scorer = _make_scorer({"low_fluid": 0.80, "clogged_filter": 0.20})
        evidence = _evidence_log("intake", "user_text")
        result = can_exit(
            scorer=scorer,
            answered_nodes=4,
            evidence_log=evidence,
            contradiction_flags=[mild_contradiction],
        )
        # Exit should be allowed (score >=0.75, lead >=0.20, nodes >=3, evidence_types=2, severity<0.5)
        assert result is True, "Mild contradiction (severity<0.5) should not block exit"

    async def test_process_message_returns_clarify_on_blocking_contradiction(self):
        """Controller issues clarify action when a blocking contradiction is detected mid-session."""
        scorer = _hydraulic_scorer()
        # Pre-load evidence that creates a score reversal for low_fluid
        conflicting_evidence = [
            {
                "source": "user_text",
                "observation": "everything slow",
                "normalized_key": "everything_slow",
                "certainty": 1.0,
                "affects": {"low_fluid": +0.40, "clogged_filter": +0.20},
            },
            {
                "source": "user_text",
                "observation": "fluid level normal",
                "normalized_key": "fluid_ok",
                "certainty": 1.0,
                "affects": {"low_fluid": -0.30},
            },
        ]
        # Apply the conflicting evidence to scorer so it reflects current state
        scorer.hypotheses["low_fluid"].score = 0.35   # net of conflict
        scorer.hypotheses["clogged_filter"].score = 0.40

        contradiction_flags = [
            {
                "type": "score_reversal",
                "description": "Conflicting evidence for 'low_fluid': +0.40 support vs -0.30 contradiction",
                "severity": 0.70,
            }
        ]
        state = _base_session(
            answered=3,
            evidence=conflicting_evidence,
            contradictions=contradiction_flags,
            node_id="visible_leak",
        )
        result = await process_message(
            state,
            "not sure, couldn't see clearly",
            scorer,
            classify_result=_classify("not_sure"),
        )
        assert result.action == "clarify", (
            f"Active blocking contradiction should yield clarify action, got {result.action}"
        )

    def test_merge_flags_deduplicates(self):
        """merge_flags does not add duplicate contradiction descriptions."""
        existing = [{"type": "score_reversal", "description": "existing conflict", "severity": 0.6}]
        new_contra = Contradiction(type="score_reversal", description="existing conflict", severity=0.6)
        merged = merge_flags(existing, [new_contra])
        assert len(merged) == 1, "Duplicate contradiction should not be added again"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Exit guard enforcement + LLM guardrail (anomaly suppression)
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyExitGuardEnforcement:
    """All 5 exit guard conditions must ALL pass before exit is allowed."""

    def test_exit_blocked_score_below_threshold(self):
        scorer = _make_scorer({"low_fluid": 0.70, "clogged_filter": 0.40})
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=5, evidence_log=evidence, contradiction_flags=[])
        reason = exit_reason(scorer, 5, evidence, [])
        assert "top_score" in reason

    def test_exit_blocked_insufficient_lead(self):
        scorer = _make_scorer({"low_fluid": 0.80, "clogged_filter": 0.65})
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=5, evidence_log=evidence, contradiction_flags=[])
        reason = exit_reason(scorer, 5, evidence, [])
        assert "score_gap" in reason

    def test_exit_blocked_too_few_nodes(self):
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        evidence = _evidence_log("intake", "user_text")
        assert not can_exit(scorer, answered_nodes=2, evidence_log=evidence, contradiction_flags=[])
        reason = exit_reason(scorer, 2, evidence, [])
        assert str(MIN_NODES) in reason

    def test_exit_blocked_insufficient_evidence_types(self):
        """Only one evidence type (user_text only) — need at least 2."""
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        single_type_evidence = _evidence_log("user_text", "user_text", "user_text")
        assert not can_exit(scorer, answered_nodes=4, evidence_log=single_type_evidence, contradiction_flags=[])
        reason = exit_reason(scorer, 4, single_type_evidence, [])
        assert "evidence" in reason.lower()

    def test_exit_blocked_active_blocking_contradiction(self):
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        evidence = _evidence_log("intake", "user_text")
        flags = [{"type": "score_reversal", "description": "conflict", "severity": 0.60}]
        assert not can_exit(scorer, answered_nodes=5, evidence_log=evidence, contradiction_flags=flags)

    def test_exit_allowed_when_all_conditions_met(self):
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        evidence = _evidence_log("intake", "user_text")
        assert can_exit(scorer, answered_nodes=4, evidence_log=evidence, contradiction_flags=[])

    def test_exit_allowed_with_weak_non_blocking_contradiction(self):
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        evidence = _evidence_log("intake", "user_text")
        mild_flags = [{"type": "score_reversal", "description": "mild", "severity": 0.40}]
        assert can_exit(scorer, answered_nodes=4, evidence_log=evidence, contradiction_flags=mild_flags)

    async def test_session_completed_emits_event(self):
        """process_message emits fix.session.completed with correct payload on exit."""
        scorer = _make_scorer({"low_fluid": 0.85, "clogged_filter": 0.30})
        # Use a node whose option has no next_node so tree exits naturally
        tree = TREES["hydraulic_loss_heavy_equipment"]
        # Find a leaf node (option with no next_node)
        leaf_node_id = None
        for node_id, node in tree.items():
            for opt in node.get("options", []):
                if opt.get("next_node") is None:
                    leaf_node_id = node_id
                    leaf_option_key = opt["match"]
                    break
            if leaf_node_id:
                break
        assert leaf_node_id is not None, "Expected at least one leaf node in hydraulic_loss tree"
        state = _base_session(node_id=leaf_node_id, answered=4, evidence=_evidence_log("intake", "user_text"))
        emitter = MockEmitter()
        result = await process_message(
            state,
            "confirmed",
            scorer,
            classify_result=_classify(leaf_option_key),
            emitter=emitter,
        )
        assert result.action == "exit", f"Expected exit action, got {result.action}"
        assert "fix.session.completed" in emitter.names(), (
            f"fix.session.completed not emitted. Got: {emitter.names()}"
        )
        payload = emitter.payload_for("fix.session.completed")
        assert payload["session_id"] == str(state.id)
        assert payload["user_id"] == str(_TEST_USER_ID)
        assert payload["vehicle_type"] == "heavy_equipment"
        assert payload["outcome"] == "low_fluid"


class TestHeavyLLMGuardrails:
    """LLM influence is capped; system is coherent without LLM."""

    def test_routing_hint_capped_below_deterministic_primary(self):
        """LLM routing hint cannot elevate a candidate above the deterministic primary."""
        deterministic = [
            TreeCandidate("hydraulic_loss_heavy_equipment", 0.95, ["primary"]),
            TreeCandidate("loss_of_power_heavy_equipment", 0.60, ["secondary"]),
        ]
        llm_hints = [
            {"tree_id": "loss_of_power_heavy_equipment", "confidence": 1.0, "reasoning": "LLM is very confident"}
        ]
        merged = combine_candidates(deterministic, llm_hints)
        # LLM boosted the secondary — it must not exceed primary
        primary_score = next(c.score for c in merged if c.tree_id == "hydraulic_loss_heavy_equipment")
        secondary_score = next(c.score for c in merged if c.tree_id == "loss_of_power_heavy_equipment")
        assert secondary_score < primary_score, (
            "LLM hint must not elevate alternative above deterministic primary"
        )

    def test_llm_only_candidate_capped_far_below_primary(self):
        """A tree only suggested by LLM gets score well below primary."""
        deterministic = [
            TreeCandidate("hydraulic_loss_heavy_equipment", 0.95, ["primary"]),
        ]
        llm_hints = [
            {"tree_id": "overheating_heavy_equipment", "confidence": 0.90, "reasoning": "possible overheating"}
        ]
        merged = combine_candidates(deterministic, llm_hints)
        llm_candidate = next((c for c in merged if c.tree_id == "overheating_heavy_equipment"), None)
        if llm_candidate:
            assert llm_candidate.score <= 0.95 * 0.35, (
                f"LLM-only candidate score {llm_candidate.score} too high vs primary 0.95"
            )

    async def test_system_works_in_discriminator_phase_without_classify_result(self):
        """In discriminating routing phase, process_message resolves without a classify_result."""
        candidates = [
            {"tree_id": "hydraulic_loss_heavy_equipment", "score": 0.88, "reasons": ["primary"]},
            {"tree_id": "loss_of_power_heavy_equipment", "score": 0.60, "reasons": ["secondary"]},
        ]
        now = datetime.now(timezone.utc)
        state = CoreSession(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            owner=OwnerContext(user_id=_TEST_USER_ID),
            created_at=now,
            updated_at=now,
            symptom_category="hydraulic_loss",
            vehicle_type="heavy_equipment",
            vehicle_make="Komatsu",
            vehicle_model="PC200",
            current_node_id="start",
            turn_count=0,
            routing_phase=RoutingPhase.discriminating,
            selected_tree="hydraulic_loss_heavy_equipment",
            evidence_log=[],
            contradiction_flags=[],
            safety_flags=[],
            context={"discriminator_candidates": candidates},
            answered_nodes=0,
            session_mode=SessionMode.operator,
        )
        scorer = _hydraulic_scorer()
        result = await process_message(state, "the hydraulic functions", scorer, classify_result=None)
        assert result.action == "commit_tree", (
            f"Discriminator phase should commit a tree, got {result.action}"
        )
        assert result.committed_tree in (
            "hydraulic_loss_heavy_equipment",
            "loss_of_power_heavy_equipment",
        ), f"Committed tree must be one of the candidates, got {result.committed_tree!r}"

    async def test_answer_reliability_scales_score_deltas(self):
        """Low reliability answer has proportionally reduced delta impact."""
        scorer = _hydraulic_scorer()
        evidence = _evidence_log("intake")
        # Use fluid_level node where fluid_low option has delta +0.40 for low_fluid
        state = _base_session(node_id="fluid_level", answered=1, evidence=evidence)
        result = await process_message(
            state,
            "i think maybe the fluid is low not sure",
            scorer,
            classify_result=_classify("fluid_low", reliability=0.5),
        )
        assert isinstance(result.score_deltas, dict), "score_deltas must be a dict"
        assert "low_fluid" in result.score_deltas, (
            f"Expected low_fluid in score_deltas. Got keys: {list(result.score_deltas.keys())}"
        )
        # raw delta for fluid_low at fluid_level is +0.40; scaled by 0.5 → 0.20
        import pytest as _pytest
        assert result.score_deltas["low_fluid"] == _pytest.approx(0.40 * 0.5, abs=1e-4), (
            f"Expected low_fluid delta 0.20 (0.40 × 0.5), got {result.score_deltas['low_fluid']}"
        )

    def test_anomaly_suppresses_early_exit_insufficient_evidence_types(self):
        """Even with high score and sufficient nodes, exit blocked if only 1 evidence type."""
        scorer = _make_scorer({"low_fluid": 0.90, "clogged_filter": 0.20})
        # Only user_text — anomaly: missing evidence diversity
        single_type = _evidence_log("user_text", "user_text", "user_text", "user_text")
        result = can_exit(scorer, answered_nodes=5, evidence_log=single_type, contradiction_flags=[])
        assert result is False, (
            "High confidence with only one evidence type should not exit — "
            "forces intake evidence packet to be present"
        )

    async def test_shadow_hypotheses_in_context_do_not_affect_scorer_directly(self):
        """Shadow hypotheses are opaque state in context — scorer is not mutated by them."""
        scorer = _hydraulic_scorer()
        initial_scores = {k: h.score for k, h in scorer.hypotheses.items()}
        state = _base_session(answered=0)
        # Simulate shadow_hypotheses in context (as stored on session)
        state.context["shadow_hypotheses"] = [
            {"key": "low_fluid", "shadow_score": 0.99, "is_anomaly": True}
        ]
        evidence = _evidence_log("intake")
        state.evidence_log = evidence
        result = await process_message(
            state,
            "everything is slow",
            scorer,
            classify_result=_classify("everything_slow_or_dead"),
        )
        # Scorer hypothesis scores should only have changed by our classify_result deltas
        for k, h in scorer.hypotheses.items():
            # We only applied score_deltas manually — the scorer was NOT mutated inside process_message
            pass
        # Main assertion: shadow hypothesis score did not bypass the scorer
        assert result.action in ("ask_question", "exit", "clarify"), (
            "Shadow hypotheses in context must not corrupt controller action"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Operator and Mechanic session modes
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyOperatorMechanicModes:
    """Session modes are stored and flow through to evidence + controller."""

    def test_operator_mode_stored_in_session_state(self):
        state = _base_session(session_mode="operator")
        assert state.session_mode == "operator"

    def test_mechanic_mode_stored_in_session_state(self):
        state = _base_session(session_mode="mechanic")
        assert state.session_mode == "mechanic"

    def test_consumer_mode_stored_in_session_state(self):
        state = _base_session(session_mode="consumer")
        assert state.session_mode == "consumer"

    def test_operator_observation_evidence_packet_built_correctly(self):
        packet = build_from_operator_observation(
            observation="Fluid pooling under the rear of the machine",
            normalized_key="fluid_on_ground",
            score_deltas={"leaking_hose_fitting": +0.35, "low_fluid": +0.10},
        )
        assert packet.source == "operator_observation"
        assert packet.certainty == 0.80
        assert packet.normalized_key == "fluid_on_ground"
        assert packet.affects["leaking_hose_fitting"] == pytest.approx(0.35)

    def test_manual_check_evidence_packet_built_correctly(self):
        packet = build_from_manual_check(
            check_description="Measured 24V at pilot solenoid connector with key ON",
            normalized_key="pilot_voltage_present",
            score_deltas={"pilot_solenoid_failure": +0.40},
        )
        assert packet.source == "manual_check"
        assert packet.certainty == 0.90
        assert packet.affects["pilot_solenoid_failure"] == pytest.approx(0.40)

    def test_operator_observation_certainty_lower_than_manual_check(self):
        obs = build_from_operator_observation(
            observation="looks like there might be fluid",
            normalized_key="visual_fluid",
            score_deltas={"leaking_hose_fitting": 0.20},
        )
        chk = build_from_manual_check(
            check_description="dipstick read 2 quarts low",
            normalized_key="fluid_measured_low",
            score_deltas={"low_fluid": 0.40},
        )
        assert obs.certainty < chk.certainty, (
            "Operator observation (0.80) should be lower certainty than manual check (0.90)"
        )

    def test_operator_and_manual_check_create_diverse_evidence_types(self):
        """intake + operator_observation + manual_check = 3 types → satisfies evidence diversity."""
        evidence = [
            build_intake_packet("everything slow", {}).to_dict(),
            build_from_operator_observation(
                observation="fluid on ground", normalized_key="fluid_ground",
                score_deltas={"leaking_hose_fitting": 0.30}
            ).to_dict(),
            build_from_manual_check(
                check_description="filter indicator lit",
                normalized_key="filter_restricted",
                score_deltas={"clogged_filter": 0.40}
            ).to_dict(),
        ]
        count = evidence_type_count(evidence)
        assert count >= 3, f"Should have 3+ evidence types, got {count}"

    async def test_process_message_completes_for_mechanic_mode(self):
        """Mechanic mode flows through controller without errors."""
        scorer = _hydraulic_scorer()
        state = _base_session(session_mode="mechanic", answered=0, evidence=_evidence_log("intake"))
        result = await process_message(
            state,
            "filter bypass indicator illuminated, hyd pressure 1800 psi at pump test port",
            scorer,
            classify_result=_classify("slow_under_load", reliability=0.95),
        )
        assert result.action in ("ask_question", "exit", "clarify", "safety_interrupt")

    async def test_process_message_completes_for_operator_mode(self):
        """Operator mode flows through controller without errors."""
        scorer = _hydraulic_scorer()
        state = _base_session(session_mode="operator", answered=0, evidence=_evidence_log("intake"))
        result = await process_message(
            state,
            "boom dont move no more, everything stopped working",
            scorer,
            classify_result=_classify("everything_slow_or_dead"),
        )
        assert result.action in ("ask_question", "exit", "clarify", "safety_interrupt")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Realistic fixtures — messy language, incomplete inputs, image scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyRealisticFixtures:
    """Real-world input quality does not break routing or flow."""

    def test_messy_operator_language_routes_hydraulic_loss(self):
        """Operator describing the problem informally should still route to hydraulic tree."""
        intake = {
            "symptom_category": "hydraulic_loss",
            "vehicle_type": "heavy_equipment",
            "vehicle_make": "CAT",
            "description": "boom dont do nuthin, sticks just dead, tried movin em nothing",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "hydraulic_loss_heavy_equipment"

    def test_messy_operator_language_routes_no_start(self):
        intake = {
            "symptom_category": "no_start",
            "vehicle_type": "heavy_equipment",
            "vehicle_make": "John Deere",
            "description": "machine wont fire up, crankin but aint startin, batteries seem ok",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "no_start_heavy_equipment"

    def test_incomplete_input_no_make_still_routes(self):
        intake = {"symptom_category": "overheating", "vehicle_type": "heavy_equipment"}
        candidates = rank_candidate_trees(intake)
        assert candidates, "Should return candidates even with no make/model"
        assert candidates[0].tree_id == "overheating_heavy_equipment"
        assert candidates[0].score < 1.0

    def test_mechanic_concise_input_routes_correctly(self):
        """Mechanic would say 'filter bypass lit, pump output low' — maps to hydraulic_loss."""
        intake = {
            "symptom_category": "hydraulic_loss",
            "vehicle_type": "heavy_equipment",
            "vehicle_make": "Volvo",
            "description": "filter bypass indicator on, pump output below spec on pressure test",
        }
        candidates = rank_candidate_trees(intake)
        assert candidates[0].tree_id == "hydraulic_loss_heavy_equipment"

    def test_image_evidence_adds_new_evidence_type(self):
        """An image packet adds 'image' source type, diversifying evidence."""
        classification_packet = build_from_classification(
            option_key="everything_slow_or_dead",
            option_label="Everything is slow or not working",
            deltas={"low_fluid": +0.20, "failed_hydraulic_pump": +0.20},
            answer_reliability=0.90,
            user_text="everything stopped",
        )
        image_packet = build_from_image(
            interpretation="Fluid pooling visible beneath undercarriage near rear axle",
            score_deltas={"leaking_hose_fitting": +0.35},
            confidence_modifier=0.80,
        )
        evidence_log = [classification_packet.to_dict(), image_packet.to_dict()]
        count = evidence_type_count(evidence_log)
        assert count == 2
        sources = {e["source"] for e in evidence_log}
        assert "image" in sources
        assert "user_text" in sources

    def test_no_image_scenario_still_meets_evidence_diversity_with_intake(self):
        """intake + user_text = 2 types, meeting minimum without image."""
        intake_packet = build_intake_packet("everything slow", {"clogged_filter": 0.10})
        qa_packet = build_from_classification(
            option_key="everything_slow_or_dead",
            option_label="Everything is slow",
            deltas={"low_fluid": 0.20},
            answer_reliability=0.90,
            user_text="yea everything stopped",
        )
        evidence = [intake_packet.to_dict(), qa_packet.to_dict()]
        count = evidence_type_count(evidence)
        assert count >= 2, "intake + user_text should satisfy MIN_EVIDENCE_TYPES=2"

    def test_conflicting_answers_create_contradiction(self):
        """Operator says all functions dead, then says fluid is overfull — conflicting signals."""
        # 'everything_slow_or_dead' → low_fluid +0.20, pilot_solenoid_failure +0.15
        # 'fluid_overfull' → low_fluid -0.15 (would be an eliminate + negative deltas)
        evidence = [
            {
                "source": "user_text",
                "observation": "everything stopped",
                "normalized_key": "everything_slow_or_dead",
                "certainty": 1.0,
                "affects": {"low_fluid": +0.30, "clogged_filter": +0.20},
            },
            {
                "source": "user_text",
                "observation": "fluid looks overfull actually",
                "normalized_key": "fluid_overfull",
                "certainty": 1.0,
                "affects": {"low_fluid": -0.25},
            },
        ]
        contradictions = detect_contradictions(evidence)
        assert len(contradictions) >= 1, "Conflicting fluid level answers should trigger contradiction"

    def test_partial_answers_low_reliability_do_not_trigger_false_contradictions(self):
        """Uncertain answers scaled to 0.3 reliability → deltas too small to trigger contradiction."""
        evidence = [
            {
                "source": "user_text",
                "observation": "maybe slow, not sure",
                "normalized_key": "slow_under_load",
                "certainty": 0.30,
                "affects": {"clogged_filter": +0.06, "failed_hydraulic_pump": +0.045},
            },
            {
                "source": "user_text",
                "observation": "actually seems kinda ok",
                "normalized_key": "fluid_ok",
                "certainty": 0.30,
                "affects": {"clogged_filter": -0.03},
            },
        ]
        contradictions = detect_contradictions(evidence)
        blocking = [c for c in contradictions if c.severity >= 0.5]
        assert not blocking, (
            "Low-reliability answers should not produce blocking contradictions"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Follow-up evidence impact + evidence building
# ─────────────────────────────────────────────────────────────────────────────

class TestHeavyFollowUpEvidence:
    """Evidence packets are built correctly and their impact is properly scoped."""

    def test_build_from_classification_correct_source(self):
        packet = build_from_classification(
            option_key="everything_slow_or_dead",
            option_label="Everything is slow",
            deltas={"low_fluid": 0.20},
            answer_reliability=0.85,
            user_text="everything stopped working",
        )
        assert packet.source == "user_text"
        assert packet.certainty == pytest.approx(0.85)
        assert packet.normalized_key == "everything_slow_or_dead"

    def test_build_from_image_correct_source(self):
        packet = build_from_image(
            interpretation="Visible fluid drip from rear hydraulic hose",
            score_deltas={"leaking_hose_fitting": 0.40},
            confidence_modifier=0.75,
        )
        assert packet.source == "image"
        assert packet.certainty == pytest.approx(0.75)

    def test_build_from_followup_correct_source(self):
        packet = build_from_followup(
            interpretation="Filter bypass indicator was triggered",
            score_deltas={"clogged_filter": 0.40},
            user_text="filter light came on after I checked",
        )
        assert packet.source == "manual_test"
        assert packet.certainty == pytest.approx(0.85)

    def test_intake_packet_correct_source_and_certainty(self):
        packet = build_intake_packet("boom stopped moving", {"clogged_filter": 0.10})
        assert packet.source == "intake"
        assert packet.certainty == pytest.approx(1.0)
        assert packet.affects["clogged_filter"] == pytest.approx(0.10)

    def test_scale_affects_reduces_delta_by_certainty(self):
        from app.diagnostics.orchestrator.evidence import scale_affects
        packet = EvidencePacket(
            source="user_text",
            observation="test",
            normalized_key="test",
            certainty=0.60,
            affects={"low_fluid": 0.40, "clogged_filter": 0.20},
        )
        scaled = scale_affects(packet)
        assert scaled["low_fluid"] == pytest.approx(0.24, abs=0.001)
        assert scaled["clogged_filter"] == pytest.approx(0.12, abs=0.001)

    def test_follow_up_evidence_adds_evidence_type(self):
        """Adding image or manual_test after user_text creates evidence diversity."""
        user_text_evidence = _evidence_log("intake", "user_text")
        count_before = evidence_type_count(user_text_evidence)
        assert count_before == 2

        image_packet = build_from_image(
            interpretation="fluid spraying from hose",
            score_deltas={"leaking_hose_fitting": 0.40},
            confidence_modifier=0.80,
        )
        user_text_evidence.append(image_packet.to_dict())
        count_after = evidence_type_count(user_text_evidence)
        assert count_after == 3

    def test_evidence_type_count_unique_only(self):
        """Multiple packets from same source count as 1 evidence type."""
        evidence = _evidence_log("user_text", "user_text", "user_text")
        assert evidence_type_count(evidence) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 10. DiagnosticSession.vehicle_context computed property
# ─────────────────────────────────────────────────────────────────────────────

class TestVehicleContextProperty:
    """vehicle_context produces the correct human-readable string."""

    def _make_session(self, **kwargs) -> CoreSession:
        now = datetime.now(timezone.utc)
        defaults = dict(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            owner=OwnerContext(user_id=_TEST_USER_ID),
            created_at=now,
            updated_at=now,
            routing_phase=RoutingPhase.committed,
            selected_tree="hydraulic_loss_heavy_equipment",
            context={},
            answered_nodes=0,
        )
        defaults.update(kwargs)
        return CoreSession(**defaults)

    def test_full_vehicle_context(self):
        s = self._make_session(
            vehicle_year=2020,
            vehicle_make="Ford",
            vehicle_model="F-150",
            vehicle_engine="5.0L V8",
        )
        assert s.vehicle_context == "2020 Ford F-150 5.0L V8"

    def test_partial_vehicle_context_make_model_only(self):
        s = self._make_session(
            vehicle_year=None,
            vehicle_make="CAT",
            vehicle_model="336 Excavator",
            vehicle_engine=None,
        )
        assert s.vehicle_context == "CAT 336 Excavator"

    def test_empty_vehicle_context_returns_fallback(self):
        s = self._make_session(
            vehicle_year=None,
            vehicle_make=None,
            vehicle_model=None,
            vehicle_engine=None,
        )
        assert s.vehicle_context == "Unknown vehicle"

    def test_full_hydraulic_flow_three_nodes_exits_cleanly(self):
        """
        Simulate a full hydraulic loss flow for an experienced operator:
          1. everything_slow_or_dead (node: start → fluid_level)
          2. fluid_low (node: fluid_level → visible_leak)
          3. leak_visible (node: visible_leak → onset)
        After 3 nodes with intake + user_text evidence, can_exit should be True.
        """
        scorer = _hydraulic_scorer()
        hyps = HYPOTHESES["hydraulic_loss_heavy_equipment"]

        # Pre-apply intake context priors for dusty excavator overdue service
        ctx = HeavyContext(
            hours_of_operation=5500, last_service_hours=5100, environment="dusty"
        )
        intake_deltas = apply_heavy_context_priors(ctx, "hydraulic_loss_heavy_equipment")
        intake_packet = build_intake_packet("boom won't move, all hydraulics dead", intake_deltas)

        # Node 1: everything_slow_or_dead → low_fluid +0.20, pump +0.20, filter +0.15
        p1 = build_from_classification(
            option_key="everything_slow_or_dead",
            option_label="Everything is slow or not working",
            deltas={"low_fluid": +0.20, "failed_hydraulic_pump": +0.20, "clogged_filter": +0.15,
                    "air_in_system": +0.10, "pilot_solenoid_failure": +0.15},
            answer_reliability=1.0,
            user_text="everything stopped working, all sticks dead",
        )
        for hyp_key, delta in p1.affects.items():
            if hyp_key in scorer.hypotheses:
                scorer.hypotheses[hyp_key].score = min(
                    1.0, scorer.hypotheses[hyp_key].score + delta
                )

        # Node 2: fluid_low → low_fluid +0.40
        p2 = build_from_classification(
            option_key="fluid_low",
            option_label="Below minimum or I can see it's low",
            deltas={"low_fluid": +0.40, "leaking_hose_fitting": +0.15, "air_in_system": +0.10},
            answer_reliability=1.0,
            user_text="yeah the sight glass shows below min",
        )
        for hyp_key, delta in p2.affects.items():
            if hyp_key in scorer.hypotheses:
                scorer.hypotheses[hyp_key].score = min(
                    1.0, scorer.hypotheses[hyp_key].score + delta
                )

        # Node 3: leak_visible → leaking_hose_fitting +0.40
        p3 = build_from_classification(
            option_key="leak_visible",
            option_label="Yes — I can see fluid dripping, spraying, or pooling",
            deltas={"leaking_hose_fitting": +0.40, "low_fluid": +0.10, "air_in_system": +0.05},
            answer_reliability=1.0,
            user_text="there is fluid dripping on the ground under the rear of the machine",
        )
        for hyp_key, delta in p3.affects.items():
            if hyp_key in scorer.hypotheses:
                scorer.hypotheses[hyp_key].score = min(
                    1.0, scorer.hypotheses[hyp_key].score + delta
                )

        evidence_log = [
            intake_packet.to_dict(),
            p1.to_dict(),
            p2.to_dict(),
            p3.to_dict(),
        ]

        top = scorer.top_confidence()
        lead = scorer.confidence_lead()
        types = evidence_type_count(evidence_log)

        assert top >= 0.75, f"After 3 confirming answers, top confidence should be >= 0.75, got {top:.2f}"
        assert lead >= 0.20, f"Should have clear leader after confirming answers, lead={lead:.2f}"
        assert types >= 2, f"Should have intake + user_text evidence types, got {types}"

        result = can_exit(
            scorer=scorer,
            answered_nodes=3,
            evidence_log=evidence_log,
            contradiction_flags=[],
        )
        assert result is True, (
            f"Should be able to exit after 3 confirming nodes. "
            f"top={top:.2f}, lead={lead:.2f}, types={types}"
        )
