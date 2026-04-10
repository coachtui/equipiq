"""
Hydraulic loss diagnostic tree — tractor (agricultural/utility).

Tractor hydraulic systems serve: 3-point hitch lift, remote cylinders for
implements, power steering, and (on some models) transmission clutching.
Loss of hydraulic function manifests as: 3-point hitch won't raise, remote
outlets with no flow, power steering heavy, or hitch drops under load.
"""

HYDRAULIC_LOSS_TRACTOR_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level (often shared sump with transmission)",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic / transmission fluid (OEM specification)", "notes": "Many tractors use a shared hydraulic/transmission sump — do NOT use engine oil or generic ATF unless OEM spec permits"},
        ],
    },
    "clogged_filter": {
        "label": "Clogged hydraulic filter or strainer (bypass mode)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic filter element (return line)", "notes": "Change per OEM hours spec — commonly 250–500 hours on agricultural tractors"},
            {"name": "Suction strainer (in sump)", "notes": "Located in the transmission/hydraulic sump — clean with each major fluid change"},
        ],
    },
    "failed_hydraulic_pump": {
        "label": "Failed hydraulic pump (gear pump or variable displacement)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Hydraulic pump", "notes": "Confirm by pressure test at pump outlet before condemning — typical spec 2000–2800 PSI"},
        ],
    },
    "control_valve_fault": {
        "label": "Hitch control valve or draft control linkage fault",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hitch control valve / draft control spring", "notes": "Draft control springs and pins wear — inspect before ordering valve"},
        ],
    },
    "cylinder_seal_leak": {
        "label": "Cylinder seal failure — hitch drifts down under load (internal leak)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Lift cylinder seal kit (OEM)", "notes": "Confirm by isolating cylinder from circuit with load — drift confirms internal leak"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "External hydraulic hose or fitting leak",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly", "notes": "Match OEM pressure rating; use crimped fittings"},
        ],
    },
    "relief_valve_fault": {
        "label": "Relief valve set too low or stuck open",
        "prior": 0.03,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

HYDRAULIC_LOSS_TRACTOR_TREE: dict[str, dict] = {
    "start": {
        "question": "Which hydraulic function is affected — 3-point hitch, remote outlets (for implements), power steering, or all hydraulics?",
        "options": [
            {
                "match": "three_point_only",
                "label": "Only the 3-point hitch — won't raise or drifts down",
                "deltas": {
                    "control_valve_fault": +0.20,
                    "cylinder_seal_leak": +0.20,
                    "failed_hydraulic_pump": -0.10,
                    "low_fluid": -0.05,
                },
                "eliminate": ["leaking_hose_fitting"],
                "next_node": "hitch_detail",
            },
            {
                "match": "all_functions_slow",
                "label": "All hydraulic functions are weak or slow",
                "deltas": {
                    "low_fluid": +0.20,
                    "clogged_filter": +0.20,
                    "failed_hydraulic_pump": +0.15,
                },
                "eliminate": ["cylinder_seal_leak"],
                "next_node": "fluid_level",
            },
            {
                "match": "total_loss",
                "label": "Total loss — nothing moves, no hitch, no remotes",
                "deltas": {
                    "failed_hydraulic_pump": +0.25,
                    "low_fluid": +0.15,
                    "clogged_filter": +0.10,
                    "relief_valve_fault": +0.08,
                },
                "eliminate": ["cylinder_seal_leak", "control_valve_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "steering_heavy",
                "label": "Power steering is very heavy — other functions seem okay",
                "deltas": {
                    "low_fluid": +0.20,
                    "failed_hydraulic_pump": +0.15,
                    "clogged_filter": +0.10,
                },
                "eliminate": ["cylinder_seal_leak", "control_valve_fault"],
                "next_node": "fluid_level",
            },
        ],
    },

    "hitch_detail": {
        "question": "Does the hitch raise but then slowly drop (drift) under load, or does it not raise at all?",
        "options": [
            {
                "match": "drifts_down",
                "label": "Hitch raises but slowly drifts down under load or at rest",
                "deltas": {
                    "cylinder_seal_leak": +0.35,
                    "control_valve_fault": +0.15,
                    "low_fluid": -0.10,
                    "failed_hydraulic_pump": -0.15,
                },
                "eliminate": ["relief_valve_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "wont_raise",
                "label": "Hitch does not raise at all",
                "deltas": {
                    "control_valve_fault": +0.25,
                    "low_fluid": +0.15,
                    "clogged_filter": +0.12,
                    "failed_hydraulic_pump": +0.10,
                },
                "eliminate": ["cylinder_seal_leak"],
                "next_node": "fluid_level",
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic / transmission sump level using the dipstick or sight glass. What is the level?",
        "options": [
            {
                "match": "low",
                "label": "Level is low or below minimum mark",
                "deltas": {
                    "low_fluid": +0.45,
                    "leaking_hose_fitting": +0.10,
                },
                "eliminate": [],
                "next_node": "visual_leak",
            },
            {
                "match": "ok",
                "label": "Level is within the normal range",
                "deltas": {
                    "low_fluid": -0.15,
                    "clogged_filter": +0.10,
                    "failed_hydraulic_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "filter_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure where to check or can't access right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "filter_service",
            },
        ],
    },

    "visual_leak": {
        "question": "Is there visible hydraulic fluid leaking — under the tractor, on the hitch arms, or around any lines or connections?",
        "options": [
            {
                "match": "visible_leak",
                "label": "Yes — I can see fluid dripping or puddling",
                "deltas": {
                    "leaking_hose_fitting": +0.35,
                    "cylinder_seal_leak": +0.15,
                },
                "eliminate": ["clogged_filter", "relief_valve_fault"],
                "next_node": None,
            },
            {
                "match": "no_visible_leak",
                "label": "No visible external leak",
                "deltas": {
                    "clogged_filter": +0.12,
                    "failed_hydraulic_pump": +0.10,
                    "cylinder_seal_leak": +0.08,
                },
                "eliminate": ["leaking_hose_fitting"],
                "next_node": None,
            },
        ],
    },

    "filter_service": {
        "question": "When was the hydraulic filter last changed, and are you aware of any recent blockage or contamination?",
        "options": [
            {
                "match": "overdue",
                "label": "Overdue — hasn't been changed in a long time",
                "deltas": {
                    "clogged_filter": +0.30,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recent",
                "label": "Changed recently per the service schedule",
                "deltas": {
                    "clogged_filter": -0.10,
                    "failed_hydraulic_pump": +0.10,
                    "control_valve_fault": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HYDRAULIC_LOSS_TRACTOR_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"clogged_filter": +0.12, "failed_hydraulic_pump": +0.05},
        "muddy": {"clogged_filter": +0.08, "leaking_hose_fitting": +0.05},
        "cold": {"low_fluid": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "clogged_filter": +0.18,
            "failed_hydraulic_pump": +0.08,
            "cylinder_seal_leak": +0.05,
        },
    },
}

HYDRAULIC_LOSS_TRACTOR_POST_DIAGNOSIS: list[str] = [
    "Tractor hydraulic/transmission sump: most utility tractors share a single sump for hydraulics AND the transmission — use ONLY the OEM-specified fluid type. Wrong fluid causes rapid pump and seal damage.",
    "3-point hitch drift test: raise the hitch fully, kill the engine, and place a load on the arms. Drift within 1 inch per minute usually indicates worn hitch valve or lift cylinder seal — not pump failure.",
    "Filter bypass indicator: if equipped, a red indicator on the filter head means the element is bypassed — change immediately and check for debris in the element.",
    "Never run the hydraulic system low on fluid — air ingestion can happen within seconds and causes pump cavitation damage that requires full pump replacement.",
    "Remote outlet failure: if remotes have no flow but hitch works, the issue is specific to the remote control valve or its detent mechanism — check the individual valve section for spool sticking.",
]
