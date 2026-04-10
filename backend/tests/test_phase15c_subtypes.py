"""
Phase 15C tests — HE subtype trees and fallback routing.

Tests:
  - All 8 new tree files importable with 4 required exports
  - All 8 trees registered in TREES, HYPOTHESES, CONTEXT_PRIORS, POST_DIAGNOSIS
  - resolve_tree_key resolves to subtype-specific tree when available
  - resolve_tree_key falls back to heavy_equipment tree when no subtype tree exists
  - resolve_tree_key falls back to base tree when no HE tree exists
  - intake_classify VEHICLE_TYPES includes all 4 new subtypes
  - Each tree has valid structure (nodes with questions, options, deltas)
  - _HE_SUBTYPES in __init__.py contains all 4 subtypes
"""
import pytest


# ── Import trees ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module_name,expected_exports", [
    ("no_start_tractor", [
        "NO_START_TRACTOR_TREE", "NO_START_TRACTOR_HYPOTHESES",
        "NO_START_TRACTOR_CONTEXT_PRIORS", "NO_START_TRACTOR_POST_DIAGNOSIS",
    ]),
    ("hydraulic_loss_tractor", [
        "HYDRAULIC_LOSS_TRACTOR_TREE", "HYDRAULIC_LOSS_TRACTOR_HYPOTHESES",
        "HYDRAULIC_LOSS_TRACTOR_CONTEXT_PRIORS", "HYDRAULIC_LOSS_TRACTOR_POST_DIAGNOSIS",
    ]),
    ("no_start_excavator", [
        "NO_START_EXCAVATOR_TREE", "NO_START_EXCAVATOR_HYPOTHESES",
        "NO_START_EXCAVATOR_CONTEXT_PRIORS", "NO_START_EXCAVATOR_POST_DIAGNOSIS",
    ]),
    ("hydraulic_loss_excavator", [
        "HYDRAULIC_LOSS_EXCAVATOR_TREE", "HYDRAULIC_LOSS_EXCAVATOR_HYPOTHESES",
        "HYDRAULIC_LOSS_EXCAVATOR_CONTEXT_PRIORS", "HYDRAULIC_LOSS_EXCAVATOR_POST_DIAGNOSIS",
    ]),
    ("no_start_loader", [
        "NO_START_LOADER_TREE", "NO_START_LOADER_HYPOTHESES",
        "NO_START_LOADER_CONTEXT_PRIORS", "NO_START_LOADER_POST_DIAGNOSIS",
    ]),
    ("hydraulic_loss_loader", [
        "HYDRAULIC_LOSS_LOADER_TREE", "HYDRAULIC_LOSS_LOADER_HYPOTHESES",
        "HYDRAULIC_LOSS_LOADER_CONTEXT_PRIORS", "HYDRAULIC_LOSS_LOADER_POST_DIAGNOSIS",
    ]),
    ("no_start_skid_steer", [
        "NO_START_SKID_STEER_TREE", "NO_START_SKID_STEER_HYPOTHESES",
        "NO_START_SKID_STEER_CONTEXT_PRIORS", "NO_START_SKID_STEER_POST_DIAGNOSIS",
    ]),
    ("hydraulic_loss_skid_steer", [
        "HYDRAULIC_LOSS_SKID_STEER_TREE", "HYDRAULIC_LOSS_SKID_STEER_HYPOTHESES",
        "HYDRAULIC_LOSS_SKID_STEER_CONTEXT_PRIORS", "HYDRAULIC_LOSS_SKID_STEER_POST_DIAGNOSIS",
    ]),
])
def test_tree_module_exports(module_name, expected_exports):
    """Each tree module exports all 4 required symbols."""
    import importlib
    mod = importlib.import_module(f"app.engine.trees.{module_name}")
    for export in expected_exports:
        assert hasattr(mod, export), f"{export} missing from {module_name}"


# ── Registry ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("key", [
    "no_start_tractor", "hydraulic_loss_tractor",
    "no_start_excavator", "hydraulic_loss_excavator",
    "no_start_loader", "hydraulic_loss_loader",
    "no_start_skid_steer", "hydraulic_loss_skid_steer",
])
def test_trees_registered_in_all_dicts(key):
    """All 8 new trees are registered in all 4 registry dicts."""
    from app.engine.trees import TREES, HYPOTHESES, CONTEXT_PRIORS, POST_DIAGNOSIS
    assert key in TREES, f"{key} missing from TREES"
    assert key in HYPOTHESES, f"{key} missing from HYPOTHESES"
    assert key in CONTEXT_PRIORS, f"{key} missing from CONTEXT_PRIORS"
    assert key in POST_DIAGNOSIS, f"{key} missing from POST_DIAGNOSIS"


# ── resolve_tree_key ──────────────────────────────────────────────────────────

def test_resolve_tree_key_direct_hit():
    """resolve_tree_key returns exact match when subtype tree exists."""
    from app.engine.trees import resolve_tree_key
    assert resolve_tree_key("no_start", "tractor") == "no_start_tractor"
    assert resolve_tree_key("hydraulic_loss", "excavator") == "hydraulic_loss_excavator"
    assert resolve_tree_key("no_start", "loader") == "no_start_loader"
    assert resolve_tree_key("hydraulic_loss", "skid_steer") == "hydraulic_loss_skid_steer"


def test_resolve_tree_key_falls_back_to_he():
    """resolve_tree_key falls back to heavy_equipment tree for unrecognized symptom on subtype."""
    from app.engine.trees import resolve_tree_key
    # overheating_tractor doesn't exist → should get overheating_heavy_equipment
    key = resolve_tree_key("overheating", "tractor")
    assert key == "overheating_heavy_equipment", f"Expected overheating_heavy_equipment, got {key}"

    key = resolve_tree_key("electrical_fault", "excavator")
    assert key == "electrical_fault_heavy_equipment", f"Expected electrical_fault_heavy_equipment, got {key}"


def test_resolve_tree_key_falls_back_to_base():
    """resolve_tree_key falls back to base symptom tree for non-HE vehicle with no variant."""
    from app.engine.trees import resolve_tree_key
    # pwc has no brakes tree → falls back to base brakes
    key = resolve_tree_key("brakes", "pwc")
    assert key == "brakes", f"Expected base brakes tree, got {key}"


def test_resolve_tree_key_he_subtype_not_base():
    """HE subtypes never accidentally fall back to car/base tree for HE symptoms."""
    from app.engine.trees import resolve_tree_key
    # hydraulic_loss_tractor exists — should not fall back
    key = resolve_tree_key("hydraulic_loss", "tractor")
    assert key == "hydraulic_loss_tractor"
    assert "heavy_equipment" not in key


def test_he_subtypes_set():
    """_HE_SUBTYPES set contains all 4 new subtypes."""
    from app.engine.trees import _HE_SUBTYPES
    for subtype in ("tractor", "excavator", "loader", "skid_steer"):
        assert subtype in _HE_SUBTYPES, f"{subtype} missing from _HE_SUBTYPES"


# ── Tree structure validation ─────────────────────────────────────────────────

@pytest.mark.parametrize("tree_key", [
    "no_start_tractor", "hydraulic_loss_tractor",
    "no_start_excavator", "hydraulic_loss_excavator",
    "no_start_loader", "hydraulic_loss_loader",
    "no_start_skid_steer", "hydraulic_loss_skid_steer",
])
def test_tree_structure_valid(tree_key):
    """Each tree has a 'start' node with 'question', 'options', each option has required keys."""
    from app.engine.trees import TREES
    tree = TREES[tree_key]
    assert "start" in tree, f"{tree_key} missing 'start' node"
    start = tree["start"]
    assert "question" in start, f"{tree_key} start node missing 'question'"
    assert "options" in start, f"{tree_key} start node missing 'options'"
    assert len(start["options"]) >= 2, f"{tree_key} start node needs at least 2 options"
    for opt in start["options"]:
        assert "match" in opt, f"{tree_key} option missing 'match'"
        assert "label" in opt, f"{tree_key} option missing 'label'"
        assert "deltas" in opt, f"{tree_key} option missing 'deltas'"
        assert "next_node" in opt, f"{tree_key} option missing 'next_node'"


@pytest.mark.parametrize("tree_key", [
    "no_start_tractor", "hydraulic_loss_tractor",
    "no_start_excavator", "hydraulic_loss_excavator",
    "no_start_loader", "hydraulic_loss_loader",
    "no_start_skid_steer", "hydraulic_loss_skid_steer",
])
def test_hypotheses_have_required_keys(tree_key):
    """Each hypothesis dict has label, prior, diy_difficulty, parts."""
    from app.engine.trees import HYPOTHESES
    hyps = HYPOTHESES[tree_key]
    assert len(hyps) >= 4, f"{tree_key} needs at least 4 hypotheses"
    for key, h in hyps.items():
        assert "label" in h, f"{tree_key}:{key} missing label"
        assert "prior" in h, f"{tree_key}:{key} missing prior"
        assert "diy_difficulty" in h, f"{tree_key}:{key} missing diy_difficulty"
        assert "parts" in h, f"{tree_key}:{key} missing parts"
        assert 0.0 <= h["prior"] <= 1.0, f"{tree_key}:{key} prior out of range"


@pytest.mark.parametrize("tree_key", [
    "no_start_tractor", "hydraulic_loss_tractor",
    "no_start_excavator", "hydraulic_loss_excavator",
    "no_start_loader", "hydraulic_loss_loader",
    "no_start_skid_steer", "hydraulic_loss_skid_steer",
])
def test_post_diagnosis_non_empty(tree_key):
    """Each POST_DIAGNOSIS list has at least 3 entries."""
    from app.engine.trees import POST_DIAGNOSIS
    tips = POST_DIAGNOSIS[tree_key]
    assert len(tips) >= 3, f"{tree_key} POST_DIAGNOSIS needs at least 3 tips"
    for tip in tips:
        assert isinstance(tip, str) and len(tip) > 10, f"{tree_key} tip too short"


# ── intake_classify VEHICLE_TYPES ─────────────────────────────────────────────

def test_vehicle_types_includes_new_subtypes():
    """VEHICLE_TYPES in claude.py includes tractor, excavator, loader, skid_steer."""
    from app.llm.claude import VEHICLE_TYPES
    for vt in ("tractor", "excavator", "loader", "skid_steer"):
        assert vt in VEHICLE_TYPES, f"{vt} missing from VEHICLE_TYPES"
