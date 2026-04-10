"""
Track or drive issue diagnostic tree — heavy equipment.

Covers mobility and undercarriage problems: machine won't travel, pulls to one
side, tracks slipping, excessive undercarriage noise or wear, drive system faults.

Applicable to: track excavators, bulldozers, crawlers, rubber-track equipment
(skid steers, compact track loaders) and wheeled equipment with drivetrain issues.

Questions split early by equipment type (tracked vs wheeled) since the failure
modes are substantially different.
"""

TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "track_tension": {
        "label": "Improper track tension (too loose — derailing; too tight — excess wear)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "drive_sprocket_worn": {
        "label": "Drive sprocket worn or damaged",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Drive sprocket (OEM spec for machine model)", "notes": "Sprocket and track should be replaced together at the same wear interval"},
        ],
    },
    "idler_or_roller_failure": {
        "label": "Front idler, carrier roller, or track roller failure",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "final_drive_seal_leak": {
        "label": "Final drive oil seal leak — oil loss leading to bearing failure",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "travel_motor_failure": {
        "label": "Hydraulic travel motor failure or valve fault",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "brake_dragging": {
        "label": "Parking or service brake dragging / not fully releasing",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "hydraulic_pilot_pressure": {
        "label": "Low pilot pressure preventing travel motor engagement",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "rubber_track_damage": {
        "label": "Rubber track damage, delamination, or broken guide lugs (rubber-track machines)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Rubber track (match machine make, model, and track width)", "notes": "Check idler and roller condition before installing new track"},
        ],
    },
}

TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "What type of drive system does this machine have?",
        "options": [
            {
                "match": "steel_tracks",
                "label": "Steel tracks (crawler excavator, bulldozer, crawler loader)",
                "deltas": {
                    "track_tension": +0.10,
                    "drive_sprocket_worn": +0.05,
                    "idler_or_roller_failure": +0.05,
                    "rubber_track_damage": -0.15,
                },
                "eliminate": ["rubber_track_damage"],
                "next_node": "symptom_type",
            },
            {
                "match": "rubber_tracks",
                "label": "Rubber tracks (skid steer, compact track loader, mini excavator)",
                "deltas": {
                    "rubber_track_damage": +0.20,
                    "track_tension": +0.10,
                    "drive_sprocket_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "symptom_type",
            },
            {
                "match": "wheeled",
                "label": "Wheeled machine (wheel loader, motor grader, wheeled excavator)",
                "deltas": {
                    "brake_dragging": +0.15,
                    "travel_motor_failure": +0.10,
                    "final_drive_seal_leak": +0.10,
                    "track_tension": -0.20,
                    "drive_sprocket_worn": -0.15,
                    "idler_or_roller_failure": -0.15,
                    "rubber_track_damage": -0.20,
                },
                "eliminate": ["track_tension", "drive_sprocket_worn", "rubber_track_damage"],
                "next_node": "symptom_type",
            },
        ],
    },

    "symptom_type": {
        "question": "What is the main drive symptom?",
        "options": [
            {
                "match": "no_travel_at_all",
                "label": "Machine won't move at all in any direction",
                "deltas": {
                    "travel_motor_failure": +0.25,
                    "hydraulic_pilot_pressure": +0.20,
                    "brake_dragging": +0.15,
                },
                "eliminate": ["track_tension", "rubber_track_damage"],
                "next_node": "visual_check",
            },
            {
                "match": "pulls_to_one_side",
                "label": "Machine pulls or drifts to one side while traveling",
                "deltas": {
                    "travel_motor_failure": +0.25,
                    "brake_dragging": +0.20,
                    "final_drive_seal_leak": +0.10,
                },
                "eliminate": ["hydraulic_pilot_pressure", "rubber_track_damage"],
                "next_node": "visual_check",
            },
            {
                "match": "track_derailed",
                "label": "Track has come off or is derailing",
                "deltas": {
                    "track_tension": +0.45,
                    "idler_or_roller_failure": +0.15,
                    "drive_sprocket_worn": +0.10,
                },
                "eliminate": ["travel_motor_failure", "brake_dragging", "hydraulic_pilot_pressure"],
                "next_node": "track_visible_check",
            },
            {
                "match": "slow_or_reduced_travel",
                "label": "Machine moves but is slower than normal or lacks pushing power",
                "deltas": {
                    "travel_motor_failure": +0.15,
                    "hydraulic_pilot_pressure": +0.10,
                    "final_drive_seal_leak": +0.10,
                    "brake_dragging": +0.10,
                },
                "eliminate": [],
                "next_node": "visual_check",
            },
            {
                "match": "noise_only",
                "label": "Machine travels but makes abnormal noise in the undercarriage",
                "deltas": {
                    "idler_or_roller_failure": +0.25,
                    "drive_sprocket_worn": +0.20,
                    "final_drive_seal_leak": +0.15,
                },
                "eliminate": ["travel_motor_failure", "hydraulic_pilot_pressure"],
                "next_node": "track_visible_check",
            },
        ],
    },

    "track_visible_check": {
        "question": "Walk around the undercarriage — can you see any of the following: oil leaking from the final drive hub, a derailed or sagging track, or broken/missing track pads or guide lugs?",
        "options": [
            {
                "match": "final_drive_oil_leak",
                "label": "Oil leaking from the final drive hub or wheel",
                "deltas": {
                    "final_drive_seal_leak": +0.45,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "track_sag_or_loose",
                "label": "Track looks saggy, loose, or has derailed",
                "deltas": {
                    "track_tension": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "rubber_track_damaged",
                "label": "Rubber track is visibly damaged, delaminated, or has broken lugs",
                "deltas": {
                    "rubber_track_damage": +0.45,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "nothing_obvious",
                "label": "Nothing obviously wrong visually",
                "deltas": {
                    "travel_motor_failure": +0.10,
                    "brake_dragging": +0.10,
                    "idler_or_roller_failure": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "visual_check": {
        "question": "Is the machine currently safe to operate at low speed for a short test? If yes, when you attempt to travel, do the implements (boom/bucket) still respond normally?",
        "options": [
            {
                "match": "implements_ok_travel_bad",
                "label": "Yes, implements work fine — only travel is affected",
                "deltas": {
                    "travel_motor_failure": +0.25,
                    "brake_dragging": +0.15,
                    "final_drive_seal_leak": +0.10,
                },
                "eliminate": ["hydraulic_pilot_pressure"],
                "next_node": "track_visible_check",
            },
            {
                "match": "both_slow_or_dead",
                "label": "Both travel and implements are slow or not working",
                "deltas": {
                    "hydraulic_pilot_pressure": +0.30,
                    "travel_motor_failure": -0.10,
                },
                "eliminate": ["brake_dragging"],
                "next_node": "track_visible_check",
            },
            {
                "match": "not_safe_to_test",
                "label": "Not safe to operate right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "track_visible_check",
            },
        ],
    },
}

TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"idler_or_roller_failure": +0.05, "drive_sprocket_worn": +0.05},
        "muddy": {"track_tension": +0.08, "rubber_track_damage": +0.05},
        "marine": {},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "final_drive_seal_leak": +0.10,
            "idler_or_roller_failure": +0.08,
            "drive_sprocket_worn": +0.08,
        },
    },
}

TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Track adjustment: measure sag at midpoint between front idler and first carrier roller. Most OEM specs call for 1–2 inches (25–50mm) of sag for steel tracks.",
    "A machine that pulls sharply to one side at full travel speed is dangerous — do not operate on roads or near edges until the cause is found.",
    "Final drive oil: check levels at OEM intervals. Running low causes rapid bearing and gear wear; milky oil indicates water ingress.",
    "Rubber track guide lugs must seat fully in drive sprocket pockets — if they're skipping, the track is too loose or the sprocket is worn.",
]
