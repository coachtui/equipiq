"""
Hydraulic loss diagnostic tree — skid steer loader (compact track loader included).

Skid steer hydraulic systems power: lift arms, bucket/attachment tilt, and
auxiliary hydraulics (for attachments like augers, grapples, cold planers).
Skid steers also have hydrostatic drive motors (separate circuit) —
travel loss is diagnosed here if hydraulics are confirmed OK.
"""

HYDRAULIC_LOSS_SKID_STEER_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic fluid (OEM specification)", "notes": "Skid steers often use a combined hydraulic/hydrostatic reservoir — check OEM spec"},
        ],
    },
    "clogged_filter": {
        "label": "Clogged hydraulic return filter or case drain filter",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic return filter element", "notes": "Change per OEM schedule — typically 250–500 hours on compact machines"},
            {"name": "Case drain filter (if equipped)", "notes": "Often overlooked — located in the hydrostatic pump case drain line"},
        ],
    },
    "failed_hydraulic_pump": {
        "label": "Failed main hydraulic (implement) pump",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Implement hydraulic pump", "notes": "Confirm pressure test before condemning — Bobcat/CAT/Deere all have known service procedures"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "Hydraulic hose or fitting leak",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly", "notes": "Inspect boom pivot hoses carefully — they flex constantly and crack early"},
        ],
    },
    "auxiliary_valve_fault": {
        "label": "Auxiliary hydraulic valve fault — attachment has no flow",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Auxiliary control valve / solenoid", "notes": "Check that auxiliary flow is enabled via the control panel and test solenoid voltage"},
        ],
    },
    "hydrostatic_drive_fault": {
        "label": "Hydrostatic drive motor or pump fault — machine won't travel but lift/tilt works",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Hydrostatic pump or drive motor", "notes": "Skid steer hydrostatic systems are very expensive — confirm with charge pressure test first"},
        ],
    },
    "relief_valve_fault": {
        "label": "System relief valve stuck open — weak under load",
        "prior": 0.03,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

HYDRAULIC_LOSS_SKID_STEER_TREE: dict[str, dict] = {
    "start": {
        "question": "What is not working — lift arms, bucket/tilt, attachment (auxiliary), travel, or everything?",
        "options": [
            {
                "match": "all_implements_slow",
                "label": "All implements slow or dead — lift and tilt both affected",
                "deltas": {
                    "low_fluid": +0.20,
                    "clogged_filter": +0.20,
                    "failed_hydraulic_pump": +0.18,
                },
                "eliminate": ["auxiliary_valve_fault", "hydrostatic_drive_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "auxiliary_only",
                "label": "Auxiliary (attachment) has no flow — lift and tilt work fine",
                "deltas": {
                    "auxiliary_valve_fault": +0.55,
                    "failed_hydraulic_pump": -0.15,
                    "low_fluid": -0.10,
                },
                "eliminate": ["hydrostatic_drive_fault", "relief_valve_fault"],
                "next_node": "auxiliary_detail",
            },
            {
                "match": "travel_only",
                "label": "Machine won't drive — lifts and tilts are fine",
                "deltas": {
                    "hydrostatic_drive_fault": +0.50,
                    "failed_hydraulic_pump": -0.10,
                    "low_fluid": +0.10,
                },
                "eliminate": ["auxiliary_valve_fault", "clogged_filter"],
                "next_node": "fluid_level",
            },
            {
                "match": "weak_under_load",
                "label": "Everything works but stalls under load or with heavy attachment",
                "deltas": {
                    "clogged_filter": +0.20,
                    "relief_valve_fault": +0.18,
                    "failed_hydraulic_pump": +0.15,
                    "low_fluid": +0.12,
                },
                "eliminate": ["auxiliary_valve_fault", "hydrostatic_drive_fault"],
                "next_node": "fluid_level",
            },
        ],
    },

    "auxiliary_detail": {
        "question": "Is auxiliary flow enabled on the control panel (some machines require a button or switch to activate high flow)? And is the attachment properly connected to both couplers?",
        "options": [
            {
                "match": "aux_not_enabled",
                "label": "Flow was not enabled on the panel — just enabled it",
                "deltas": {
                    "auxiliary_valve_fault": +0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "enabled_no_flow",
                "label": "Flow is enabled on the panel but attachment still has no flow",
                "deltas": {
                    "auxiliary_valve_fault": +0.50,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "coupler_issue",
                "label": "Not sure the couplers are fully connected to the attachment",
                "deltas": {
                    "auxiliary_valve_fault": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic fluid level in the reservoir (often at the rear of the machine). What is the level?",
        "options": [
            {
                "match": "low",
                "label": "Level is at or below the minimum mark",
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
                    "clogged_filter": +0.12,
                    "failed_hydraulic_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "filter_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure where to check or can't access",
                "deltas": {},
                "eliminate": [],
                "next_node": "filter_service",
            },
        ],
    },

    "visible_leak": {
        "question": "Is there visible hydraulic fluid leaking from hoses, fittings, or around the cylinders?",
        "options": [
            {
                "match": "leak_visible",
                "label": "Yes — fluid is actively leaking from somewhere",
                "deltas": {
                    "leaking_hose_fitting": +0.45,
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
        "question": "When was the hydraulic filter last changed, and has the fluid appeared normal (no foam, discoloration, or metallic debris)?",
        "options": [
            {
                "match": "overdue_or_bad",
                "label": "Filter overdue or fluid looks dark / foamy / has debris",
                "deltas": {
                    "clogged_filter": +0.30,
                    "failed_hydraulic_pump": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recent_clean",
                "label": "Filter recently changed, fluid looked clean",
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

HYDRAULIC_LOSS_SKID_STEER_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"clogged_filter": +0.12, "failed_hydraulic_pump": +0.05},
        "muddy": {"clogged_filter": +0.08, "leaking_hose_fitting": +0.10},
        "cold": {"low_fluid": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "clogged_filter": +0.18,
            "failed_hydraulic_pump": +0.08,
        },
        "long_storage": {
            "low_fluid": +0.08,
            "leaking_hose_fitting": +0.05,
        },
    },
}

HYDRAULIC_LOSS_SKID_STEER_POST_DIAGNOSIS: list[str] = [
    "Auxiliary hydraulic check sequence: (1) ensure the attachment is fully connected on both quick couplers, (2) verify high-flow or auxiliary enable button is activated on the panel, (3) test solenoid voltage at the auxiliary valve — no voltage with button pressed = wiring or control panel fault.",
    "Skid steer boom hoses pivot at the lift arm pin with every cycle — inspect these first for cracking or chafing. They are the most common leak point on high-hour machines.",
    "Combined hydraulic/hydrostatic reservoir: check the OEM service manual — some machines share fluid for both implement hydraulics and drive. Low fluid can cause simultaneous implement and drive complaints.",
    "Hydrostatic drive diagnosis: if implements work but travel is lost, check charge pressure (typically 200–300 PSI). Low charge pressure = charge pump failure. Adequate charge pressure with no drive = drive pump or motor failure.",
    "Case drain filter (if equipped): located in the hydrostatic pump case drain return line. A bypassed case drain filter causes accelerated pump wear — it is often omitted from service intervals on older machines.",
]
