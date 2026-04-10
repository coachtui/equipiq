"""
Hydraulic loss diagnostic tree — loader (wheel loader, front-end loader).

Loader hydraulic circuits power: lift arms, bucket curl/dump, steering (often
a dedicated circuit), and optional attachments. Loss of function can be
total, selective (one circuit), or a gradual performance drop under load.
"""

HYDRAULIC_LOSS_LOADER_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic fluid (OEM specification)", "notes": "Large loaders have separate hydraulic and transmission circuits — check the correct reservoir"},
        ],
    },
    "clogged_filter": {
        "label": "Clogged hydraulic return filter or suction strainer",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic return filter element", "notes": "Change per OEM schedule — typically 500 hours on loaders"},
        ],
    },
    "failed_hydraulic_pump": {
        "label": "Failed main hydraulic pump",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Main hydraulic pump", "notes": "Confirm pressure test at pump outlet before ordering — very expensive component"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "External hydraulic hose or fitting leak",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly (OEM routing)", "notes": "Loaders have long boom-to-frame hose runs — inspect full length"},
        ],
    },
    "lift_cylinder_seal": {
        "label": "Lift arm cylinder seal failure — boom drifts down under load",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Lift cylinder seal kit", "notes": "Confirm by holding raised boom under load — steady drift = cylinder leak, not pump"},
        ],
    },
    "control_valve_fault": {
        "label": "Control valve spool sticking or solenoid failure",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Control valve section", "notes": "Check solenoid voltage and manual operation of spool before condemning valve body"},
        ],
    },
    "relief_valve_fault": {
        "label": "System or work-port relief valve stuck open",
        "prior": 0.04,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

HYDRAULIC_LOSS_LOADER_TREE: dict[str, dict] = {
    "start": {
        "question": "Which loader function is affected — lift arms, bucket, steering, or everything?",
        "options": [
            {
                "match": "all_slow_or_dead",
                "label": "All functions slow or dead — nothing moves normally",
                "deltas": {
                    "low_fluid": +0.20,
                    "clogged_filter": +0.18,
                    "failed_hydraulic_pump": +0.20,
                    "relief_valve_fault": +0.08,
                },
                "eliminate": ["lift_cylinder_seal"],
                "next_node": "fluid_level",
            },
            {
                "match": "lift_only",
                "label": "Lift arms only — won't raise or drifts down; bucket works",
                "deltas": {
                    "lift_cylinder_seal": +0.30,
                    "control_valve_fault": +0.20,
                    "low_fluid": -0.05,
                },
                "eliminate": ["failed_hydraulic_pump", "clogged_filter"],
                "next_node": "lift_detail",
            },
            {
                "match": "steering_heavy",
                "label": "Steering is very heavy — lift and bucket still work",
                "deltas": {
                    "low_fluid": +0.20,
                    "failed_hydraulic_pump": +0.15,
                    "clogged_filter": +0.10,
                },
                "eliminate": ["lift_cylinder_seal"],
                "next_node": "fluid_level",
            },
            {
                "match": "weak_under_load",
                "label": "Functions work but stall or slow significantly under load",
                "deltas": {
                    "clogged_filter": +0.18,
                    "failed_hydraulic_pump": +0.18,
                    "relief_valve_fault": +0.15,
                    "low_fluid": +0.10,
                },
                "eliminate": ["lift_cylinder_seal"],
                "next_node": "fluid_level",
            },
        ],
    },

    "lift_detail": {
        "question": "Do the lift arms raise and then drift down slowly, or do they not raise at all?",
        "options": [
            {
                "match": "drifts_down",
                "label": "Arms raise but drift down on their own under load",
                "deltas": {
                    "lift_cylinder_seal": +0.40,
                    "control_valve_fault": +0.10,
                },
                "eliminate": ["failed_hydraulic_pump", "clogged_filter", "relief_valve_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "wont_raise",
                "label": "Arms will not raise at all",
                "deltas": {
                    "control_valve_fault": +0.25,
                    "low_fluid": +0.12,
                    "failed_hydraulic_pump": +0.10,
                },
                "eliminate": ["lift_cylinder_seal"],
                "next_node": "fluid_level",
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic reservoir sight glass or dipstick. What is the fluid level?",
        "options": [
            {
                "match": "low",
                "label": "Level is at or below the minimum mark",
                "deltas": {
                    "low_fluid": +0.45,
                    "leaking_hose_fitting": +0.10,
                },
                "eliminate": [],
                "next_node": "visible_leak",
            },
            {
                "match": "ok",
                "label": "Level is within normal range",
                "deltas": {
                    "low_fluid": -0.15,
                    "clogged_filter": +0.12,
                    "failed_hydraulic_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "filter_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure or can't access",
                "deltas": {},
                "eliminate": [],
                "next_node": "filter_service",
            },
        ],
    },

    "visible_leak": {
        "question": "Walk around the loader — is there visible hydraulic fluid dripping from hoses, boom cylinders, or fittings?",
        "options": [
            {
                "match": "leak_visible",
                "label": "Yes — I can see active leaking",
                "deltas": {
                    "leaking_hose_fitting": +0.40,
                    "lift_cylinder_seal": +0.10,
                },
                "eliminate": ["failed_hydraulic_pump", "clogged_filter"],
                "next_node": None,
            },
            {
                "match": "no_leak",
                "label": "No visible external leak",
                "deltas": {
                    "clogged_filter": +0.12,
                    "failed_hydraulic_pump": +0.10,
                },
                "eliminate": ["leaking_hose_fitting"],
                "next_node": "filter_service",
            },
        ],
    },

    "filter_service": {
        "question": "When was the hydraulic filter last changed, and has the fluid looked normal (no dark color, foam, or metallic sheen)?",
        "options": [
            {
                "match": "overdue_or_bad_fluid",
                "label": "Filter overdue, or fluid looks dark / foamy / metallic",
                "deltas": {
                    "clogged_filter": +0.28,
                    "failed_hydraulic_pump": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recent_clean",
                "label": "Filter recently changed, fluid looks clean",
                "deltas": {
                    "clogged_filter": -0.10,
                    "failed_hydraulic_pump": +0.12,
                    "relief_valve_fault": +0.08,
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

HYDRAULIC_LOSS_LOADER_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"clogged_filter": +0.12, "failed_hydraulic_pump": +0.05},
        "muddy": {"clogged_filter": +0.08, "leaking_hose_fitting": +0.08},
        "cold": {"low_fluid": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "clogged_filter": +0.18,
            "failed_hydraulic_pump": +0.08,
            "lift_cylinder_seal": +0.05,
        },
    },
}

HYDRAULIC_LOSS_LOADER_POST_DIAGNOSIS: list[str] = [
    "Loader lift drift test: raise the boom to full height, kill the engine, and watch for 5 minutes under a full bucket load. Drift indicates cylinder seal failure or control valve leak — not pump failure.",
    "Hydraulic reservoir location varies: compact loaders often have the reservoir low and accessible; large wheel loaders may have it elevated behind the cab — check OEM documentation for location and fill procedure.",
    "Foam or milky fluid indicates air or water contamination — air ingestion damages the pump rapidly. Identify the source (usually a loose suction fitting or low fluid causing the strainer to draw air) before refilling.",
    "Large loaders with separate hydraulic and steering circuits: steering pressure is maintained by an accumulator on some models — a sudden hard steering complaint can occur even with adequate main circuit pressure.",
    "If the control valve solenoid is suspect: with the engine running, use a test light or voltmeter at each solenoid connector — energized solenoid but no movement = spool sticking. No voltage = trace the circuit back to the switch or controller.",
]
