"""
Overheating diagnostic tree — heavy equipment (diesel).

Covers engine overtemperature events on diesel-powered construction equipment.
Heavy equipment overheating differs from passenger vehicles:
  - Debris-blocked cooling screens are a primary cause on jobsites
  - Machines frequently run at sustained high load with no rest
  - Pressurized cooling systems — opening radiator cap hot is a serious injury risk
  - Machines may derate or shut down automatically on overtemp

Safety: severe overheating with steam/pressure release is handled by the
safety layer BEFORE this tree runs.
"""

OVERHEATING_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "blocked_cooler_screen": {
        "label": "Debris-blocked cooler or radiator screen (dirt, chaff, leaves, dust)",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "low_coolant": {
        "label": "Low coolant level (leak or evaporation)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant (OEM spec — check for organic acid or silicate type)", "notes": "Do NOT open radiator cap hot — risk of severe burns"},
        ],
    },
    "thermostat_failure": {
        "label": "Failed thermostat (stuck closed)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Thermostat and gasket", "notes": "Replace the full kit — never run without a thermostat"},
        ],
    },
    "water_pump_failure": {
        "label": "Failed water pump (impeller wear or bearing failure)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump assembly", "notes": "Check for weep hole leakage and bearing noise before condemning pump"},
        ],
    },
    "cooling_fan_issue": {
        "label": "Hydraulic or mechanical cooling fan not engaging or damaged",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fan clutch or hydraulic fan motor", "notes": "Many machines use hydraulic fan drives — check fan speed at operating temp"},
        ],
    },
    "head_gasket_failure": {
        "label": "Head gasket failure or internal coolant leak",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "sustained_overload": {
        "label": "Engine sustained at over-capacity load for extended period",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [],
    },
}

OVERHEATING_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "How serious is the overheating right now?",
        "options": [
            {
                "match": "warning_light_only",
                "label": "Temperature warning light came on but machine seems to be running",
                "deltas": {
                    "blocked_cooler_screen": +0.15,
                    "low_coolant": +0.10,
                    "cooling_fan_issue": +0.10,
                    "sustained_overload": +0.10,
                },
                "eliminate": [],
                "next_node": "cooler_screen",
            },
            {
                "match": "machine_shutdown",
                "label": "Machine shut itself down or went into protection mode",
                "deltas": {
                    "blocked_cooler_screen": +0.15,
                    "low_coolant": +0.15,
                    "thermostat_failure": +0.10,
                    "water_pump_failure": +0.10,
                },
                "eliminate": ["sustained_overload"],
                "next_node": "cooler_screen",
            },
            {
                "match": "steam_or_boiling",
                "label": "Steam coming from engine compartment or fluid boiling",
                "deltas": {
                    "low_coolant": +0.25,
                    "head_gasket_failure": +0.20,
                    "water_pump_failure": +0.10,
                },
                "eliminate": ["blocked_cooler_screen", "sustained_overload"],
                "next_node": "cooler_screen",
            },
        ],
    },

    "cooler_screen": {
        "question": "Look at the front or sides of the machine where the radiator or oil cooler screens are visible — are they packed with debris, dirt, or plant material?",
        "options": [
            {
                "match": "screen_clogged",
                "label": "Yes — visibly dirty, clogged, or packed with material",
                "deltas": {
                    "blocked_cooler_screen": +0.45,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "screen_clean",
                "label": "Screens look clear and clean",
                "deltas": {
                    "blocked_cooler_screen": -0.20,
                    "low_coolant": +0.10,
                    "thermostat_failure": +0.10,
                    "water_pump_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "cant_see",
                "label": "Can't access or see the screens",
                "deltas": {},
                "eliminate": [],
                "next_node": "coolant_level",
            },
        ],
    },

    "coolant_level": {
        "question": "Is it safe to check the coolant level now? (Engine must be OFF and cool — NEVER open the radiator cap on a hot engine.) What does it show?",
        "options": [
            {
                "match": "coolant_low",
                "label": "Engine is cool — coolant is below minimum or reservoir is empty",
                "deltas": {
                    "low_coolant": +0.40,
                    "head_gasket_failure": +0.10,
                },
                "eliminate": [],
                "next_node": "work_conditions",
            },
            {
                "match": "coolant_normal",
                "label": "Engine is cool — coolant level looks normal",
                "deltas": {
                    "low_coolant": -0.15,
                    "thermostat_failure": +0.15,
                    "blocked_cooler_screen": +0.10,
                    "cooling_fan_issue": +0.10,
                },
                "eliminate": [],
                "next_node": "work_conditions",
            },
            {
                "match": "engine_still_hot",
                "label": "Engine is still hot — can't safely check yet",
                "deltas": {},
                "eliminate": [],
                "next_node": "work_conditions",
            },
        ],
    },

    "work_conditions": {
        "question": "What was the machine doing just before the overheating started?",
        "options": [
            {
                "match": "heavy_continuous_load",
                "label": "Working hard continuously — pushing, digging, or lifting at near full capacity",
                "deltas": {
                    "sustained_overload": +0.25,
                    "blocked_cooler_screen": +0.10,
                    "cooling_fan_issue": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "normal_load",
                "label": "Normal operation, not unusually heavy work",
                "deltas": {
                    "blocked_cooler_screen": +0.15,
                    "thermostat_failure": +0.15,
                    "water_pump_failure": +0.10,
                },
                "eliminate": ["sustained_overload"],
                "next_node": "onset",
            },
            {
                "match": "idling_or_light",
                "label": "Idling or very light work",
                "deltas": {
                    "cooling_fan_issue": +0.25,
                    "thermostat_failure": +0.15,
                    "blocked_cooler_screen": -0.10,
                },
                "eliminate": ["sustained_overload"],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Has the machine overheated before, or is this the first time?",
        "options": [
            {
                "match": "recurring",
                "label": "It has happened before — recurring problem",
                "deltas": {
                    "thermostat_failure": +0.15,
                    "head_gasket_failure": +0.10,
                    "water_pump_failure": +0.10,
                    "blocked_cooler_screen": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "first_time",
                "label": "First time this has happened",
                "deltas": {
                    "blocked_cooler_screen": +0.15,
                    "low_coolant": +0.10,
                    "sustained_overload": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"blocked_cooler_screen": +0.20},
        "muddy": {"blocked_cooler_screen": +0.10, "low_coolant": +0.05},
        "marine": {"low_coolant": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "thermostat_failure": +0.08,
            "water_pump_failure": +0.08,
            "blocked_cooler_screen": +0.10,
        },
    },
}

OVERHEATING_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "NEVER open the radiator cap while the engine is hot — coolant is under pressure and will spray at near 100°C. Wait at least 30 minutes after shutdown.",
    "Clean cooler screens daily on dusty or high-debris jobsites — this is a top cause of overheating and a simple preventive task.",
    "If overheating recurs after checking fluid and screens: perform a combustion gas test on the coolant to rule out head gasket before replacing thermostat or pump.",
    "Hydraulic oil coolers are often in-line with the engine radiator — blocked hydraulic coolers can also cause engine overheating.",
]
