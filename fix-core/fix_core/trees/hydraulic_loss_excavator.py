"""
Hydraulic loss diagnostic tree — excavator (hydraulic excavator, mini-excavator).

Excavator hydraulic loss presents as: slow/no boom or arm movement, bucket
won't curl or extend, swing motor failure, travel motor failure, or total loss.
Excavators use a load-sensing tandem pump system — understanding which circuit
is affected narrows the diagnosis significantly.
"""

HYDRAULIC_LOSS_EXCAVATOR_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic fluid (OEM specification)", "notes": "Check OEM spec carefully — ISO 46 or 68 viscosity is typical; do NOT mix grades"},
        ],
    },
    "clogged_filter": {
        "label": "Clogged hydraulic return filter or suction strainer",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic return filter element", "notes": "Change every 500–1000 hours or per OEM schedule; inspect element for metal debris"},
        ],
    },
    "failed_main_pump": {
        "label": "Failed main hydraulic pump (tandem piston pump)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Main hydraulic pump assembly", "notes": "Very expensive — confirm with full pressure test at pump ports before ordering"},
        ],
    },
    "pilot_circuit_fault": {
        "label": "Pilot circuit failure — all functions locked (no pilot pressure to main control valve)",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot pump", "notes": "Separate small gear pump — test pilot pressure (typically 500–600 PSI)"},
            {"name": "Pilot enable solenoid valve", "notes": "Check voltage at solenoid with gate lever up; no voltage = wiring or controller fault"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "Hydraulic hose or fitting leak (external)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly (OEM routing)", "notes": "Match spiral braid count and working pressure rating exactly"},
        ],
    },
    "swing_motor_failure": {
        "label": "Swing motor failure (swing-only loss with boom/arm/travel working)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Swing motor and brake assembly", "notes": "Confirm swing brake release pressure before condemning motor"},
        ],
    },
    "relief_valve_fault": {
        "label": "Work-port relief valve stuck open — function moves but extremely weak",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

HYDRAULIC_LOSS_EXCAVATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "Which functions are affected — boom/arm/bucket, swing, travel, or everything?",
        "options": [
            {
                "match": "all_functions",
                "label": "All functions — nothing responds or everything is extremely slow",
                "deltas": {
                    "low_fluid": +0.18,
                    "clogged_filter": +0.15,
                    "failed_main_pump": +0.18,
                    "pilot_circuit_fault": +0.20,
                },
                "eliminate": ["swing_motor_failure"],
                "next_node": "fluid_level",
            },
            {
                "match": "boom_arm_bucket_slow",
                "label": "Boom, arm, or bucket is slow or weak — swing and travel may be OK",
                "deltas": {
                    "low_fluid": +0.15,
                    "clogged_filter": +0.12,
                    "relief_valve_fault": +0.15,
                    "failed_main_pump": +0.10,
                },
                "eliminate": ["swing_motor_failure", "pilot_circuit_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "swing_only",
                "label": "Swing only — boom/arm/bucket and travel work fine",
                "deltas": {
                    "swing_motor_failure": +0.55,
                    "pilot_circuit_fault": -0.15,
                    "low_fluid": -0.10,
                },
                "eliminate": ["failed_main_pump", "clogged_filter", "relief_valve_fault"],
                "next_node": None,
            },
            {
                "match": "travel_only",
                "label": "Travel motors only — machine won't move but everything else works",
                "deltas": {
                    "relief_valve_fault": +0.20,
                    "leaking_hose_fitting": +0.15,
                    "pilot_circuit_fault": +0.10,
                },
                "eliminate": ["swing_motor_failure", "low_fluid"],
                "next_node": "fluid_level",
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic fluid level in the sight glass or via the dipstick. What is the level?",
        "options": [
            {
                "match": "low",
                "label": "Level is below the minimum mark",
                "deltas": {
                    "low_fluid": +0.45,
                    "leaking_hose_fitting": +0.12,
                },
                "eliminate": [],
                "next_node": "visible_leak",
            },
            {
                "match": "ok",
                "label": "Level is within the normal range",
                "deltas": {
                    "low_fluid": -0.15,
                    "clogged_filter": +0.10,
                    "failed_main_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "pilot_check",
            },
            {
                "match": "not_sure",
                "label": "Can't check or don't know where the sight glass is",
                "deltas": {},
                "eliminate": [],
                "next_node": "pilot_check",
            },
        ],
    },

    "visible_leak": {
        "question": "Is there visible hydraulic fluid leaking from a hose, fitting, cylinder, or the pump area?",
        "options": [
            {
                "match": "visible_leak",
                "label": "Yes — I can see active fluid leaking",
                "deltas": {
                    "leaking_hose_fitting": +0.40,
                },
                "eliminate": ["failed_main_pump", "swing_motor_failure", "pilot_circuit_fault"],
                "next_node": None,
            },
            {
                "match": "no_leak",
                "label": "No visible external leak",
                "deltas": {
                    "clogged_filter": +0.12,
                    "failed_main_pump": +0.10,
                },
                "eliminate": ["leaking_hose_fitting"],
                "next_node": "pilot_check",
            },
        ],
    },

    "pilot_check": {
        "question": "With the machine running and gate lever UP, do any joystick movements respond — even a very little bit of movement in any function?",
        "options": [
            {
                "match": "nothing_responds",
                "label": "Absolutely nothing responds to any control input",
                "deltas": {
                    "pilot_circuit_fault": +0.45,
                    "failed_main_pump": +0.10,
                },
                "eliminate": ["swing_motor_failure", "relief_valve_fault"],
                "next_node": None,
            },
            {
                "match": "some_response",
                "label": "Some functions respond at least a little",
                "deltas": {
                    "pilot_circuit_fault": -0.20,
                    "clogged_filter": +0.15,
                    "relief_valve_fault": +0.12,
                    "failed_main_pump": +0.10,
                },
                "eliminate": [],
                "next_node": "filter_service",
            },
        ],
    },

    "filter_service": {
        "question": "When was the hydraulic return filter last changed, and have you noticed any metal debris or dark fluid?",
        "options": [
            {
                "match": "overdue_or_debris",
                "label": "Overdue, or there was debris / dark fluid in the filter",
                "deltas": {
                    "clogged_filter": +0.25,
                    "failed_main_pump": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recent_clean",
                "label": "Changed recently, fluid looked clean",
                "deltas": {
                    "clogged_filter": -0.10,
                    "failed_main_pump": +0.12,
                    "relief_valve_fault": +0.10,
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

HYDRAULIC_LOSS_EXCAVATOR_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"clogged_filter": +0.12, "failed_main_pump": +0.05},
        "muddy": {"clogged_filter": +0.08, "leaking_hose_fitting": +0.08},
        "marine": {"leaking_hose_fitting": +0.05, "clogged_filter": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "clogged_filter": +0.18,
            "failed_main_pump": +0.10,
        },
    },
}

HYDRAULIC_LOSS_EXCAVATOR_POST_DIAGNOSIS: list[str] = [
    "Pilot circuit test: with engine running and gate lever raised, check pilot pressure at the pilot manifold (typical spec 500–600 PSI). Zero pilot pressure = pilot pump failure or pilot enable solenoid not energized.",
    "Never perform hydraulic work on an excavator with the boom raised — the boom WILL fall if hydraulic pressure is lost. Always lower to ground and relieve all circuit pressure before disconnecting any line.",
    "Main pump diagnosis: total or near-total hydraulic loss with adequate fluid level and clean filter strongly suggests main pump — but confirm with pressure gauge at pump outlet ports before removal.",
    "Metal debris in the filter element: indicates internal component wear (pump or motor failure). Do not just change the filter — flush the system and identify the debris source before returning to service.",
    "Swing motor brake: the swing brake releases automatically on a pressure signal. If the swing won't move under power but there is no lock-out switch active, check brake release pressure at the swing motor port.",
]
