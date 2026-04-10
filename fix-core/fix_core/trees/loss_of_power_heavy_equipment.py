"""
Loss of power diagnostic tree — heavy equipment (diesel).

Covers loss of engine output power or tractive effort: machine won't climb grades,
work cycles are sluggish, engine bogs under load, max speed reduced.

IMPORTANT: Loss of power in heavy equipment can originate from three distinct
subsystems — engine, hydraulics, or drivetrain.  This tree focuses on engine
power.  The tree_router ambiguous-pair list handles rerouting to hydraulic_loss
when hydraulic symptoms are detected during the discriminator phase.
"""

LOSS_OF_POWER_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "fuel_restriction": {
        "label": "Fuel restriction (clogged fuel filter or water in fuel)",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Primary fuel filter / water separator", "notes": "Drain water separator bowl first; replace filter element"},
            {"name": "Secondary fuel filter", "notes": "Located on injection pump or fuel rail on many diesels"},
        ],
    },
    "air_restriction": {
        "label": "Air intake restriction (clogged air filter)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter primary element", "notes": "Most machines have a restriction indicator on the air cleaner — check first"},
        ],
    },
    "turbocharger_issue": {
        "label": "Turbocharger underperforming (damaged, worn, or intercooler leak)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Turbocharger", "notes": "Check for shaft play and oil in intake tract before condemning"},
        ],
    },
    "injector_fouling": {
        "label": "Injector fouling or wear — reduced spray quality",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Fuel injectors", "notes": "Flow test and spray pattern test recommended before replacement"},
        ],
    },
    "def_exhaust_system": {
        "label": "DEF/SCR system or DPF restriction causing derate",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "engine_overload": {
        "label": "Engine operating beyond rated capacity for the work being done",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "drivetrain_drag": {
        "label": "Drivetrain drag (dragging brake, final drive issue, torque converter slipping)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

LOSS_OF_POWER_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "How does the power loss show up — does the engine bog under load, or does the machine simply move and work slower than normal even at light loads?",
        "options": [
            {
                "match": "bogs_under_load",
                "label": "Engine bogs down or nearly dies when I push it hard",
                "deltas": {
                    "fuel_restriction": +0.20,
                    "air_restriction": +0.15,
                    "turbocharger_issue": +0.10,
                    "engine_overload": +0.10,
                },
                "eliminate": [],
                "next_node": "air_filter_indicator",
            },
            {
                "match": "slow_all_conditions",
                "label": "Machine is slow and weak even at light loads",
                "deltas": {
                    "injector_fouling": +0.15,
                    "fuel_restriction": +0.15,
                    "def_exhaust_system": +0.15,
                    "drivetrain_drag": +0.10,
                },
                "eliminate": ["engine_overload"],
                "next_node": "warning_lights",
            },
            {
                "match": "derates_with_smoke",
                "label": "Machine goes into a reduced power mode (derate) — warning light on",
                "deltas": {
                    "def_exhaust_system": +0.35,
                    "turbocharger_issue": +0.10,
                },
                "eliminate": [],
                "next_node": "warning_lights",
            },
        ],
    },

    "air_filter_indicator": {
        "question": "Is there an air filter restriction indicator on the air cleaner housing, and is it showing restriction?",
        "options": [
            {
                "match": "restriction_shown",
                "label": "Yes — indicator shows restricted",
                "deltas": {
                    "air_restriction": +0.40,
                },
                "eliminate": [],
                "next_node": "smoke_color",
            },
            {
                "match": "no_restriction",
                "label": "No restriction indicated",
                "deltas": {
                    "air_restriction": -0.10,
                    "fuel_restriction": +0.10,
                },
                "eliminate": [],
                "next_node": "smoke_color",
            },
            {
                "match": "no_indicator_or_unknown",
                "label": "No indicator on this machine / not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "smoke_color",
            },
        ],
    },

    "smoke_color": {
        "question": "Is any smoke coming from the exhaust when the engine is under load?",
        "options": [
            {
                "match": "black_smoke",
                "label": "Black or dark grey smoke",
                "deltas": {
                    "air_restriction": +0.20,
                    "fuel_restriction": +0.10,
                    "turbocharger_issue": +0.15,
                    "injector_fouling": +0.10,
                },
                "eliminate": [],
                "next_node": "warning_lights",
            },
            {
                "match": "white_smoke",
                "label": "White or blue-white smoke",
                "deltas": {
                    "injector_fouling": +0.20,
                    "turbocharger_issue": +0.10,
                },
                "eliminate": ["air_restriction"],
                "next_node": "warning_lights",
            },
            {
                "match": "blue_smoke",
                "label": "Blue smoke",
                "deltas": {
                    "turbocharger_issue": +0.25,
                    "injector_fouling": +0.10,
                },
                "eliminate": [],
                "next_node": "warning_lights",
            },
            {
                "match": "no_smoke",
                "label": "No visible smoke",
                "deltas": {
                    "fuel_restriction": +0.05,
                    "drivetrain_drag": +0.05,
                    "def_exhaust_system": +0.05,
                },
                "eliminate": [],
                "next_node": "warning_lights",
            },
        ],
    },

    "warning_lights": {
        "question": "Are any warning or fault lights on the dashboard?",
        "options": [
            {
                "match": "derate_or_fault_light",
                "label": "Yes — there's a derate warning, engine fault, or emission system light",
                "deltas": {
                    "def_exhaust_system": +0.25,
                    "injector_fouling": +0.10,
                    "turbocharger_issue": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "no_lights",
                "label": "No warning lights",
                "deltas": {
                    "fuel_restriction": +0.10,
                    "air_restriction": +0.05,
                    "drivetrain_drag": +0.10,
                },
                "eliminate": ["def_exhaust_system"],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Did the power loss happen suddenly or come on gradually over time?",
        "options": [
            {
                "match": "sudden",
                "label": "Sudden — power dropped sharply or it went into derate",
                "deltas": {
                    "def_exhaust_system": +0.15,
                    "turbocharger_issue": +0.10,
                    "fuel_restriction": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "gradual",
                "label": "Gradual — got slowly worse over days or weeks",
                "deltas": {
                    "fuel_restriction": +0.15,
                    "air_restriction": +0.10,
                    "injector_fouling": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"air_restriction": +0.15, "fuel_restriction": +0.05},
        "muddy": {"fuel_restriction": +0.05},
        "marine": {},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "fuel_restriction": +0.12,
            "air_restriction": +0.10,
            "injector_fouling": +0.08,
        },
    },
}

LOSS_OF_POWER_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Black smoke under load almost always means the engine is getting insufficient air — check air filter before doing anything else.",
    "DEF/SCR derate codes will progressively reduce engine power to ~25% if unaddressed — scan the ECU for active fault codes.",
    "If power loss correlates with hydraulic functions (machine slows when using implements), the root cause may be hydraulic, not engine — see hydraulic_loss tree.",
    "Turbo inspection: with engine off and cool, check for shaft radial play (side-to-side wobble) — any visible play means the turbo is worn.",
]
