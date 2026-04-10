"""
Overheating diagnostic tree — motorcycle variant.

Key branch: air-cooled vs liquid-cooled. Air-cooled bikes cannot lose coolant
but overheat from oil issues, restricted airflow, or extended idling in traffic.
Liquid-cooled bikes share failure modes with cars but have simpler systems.
"""

OVERHEATING_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "coolant_low": {
        "label": "Low coolant level (liquid-cooled bikes only — leak or evaporation)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Motorcycle coolant (50/50 with distilled water)", "notes": "Do not use tap water. Check radiator cap spec for correct mix."},
            {"name": "Cooling system pressure test kit", "notes": "Find the source of the leak before refilling"},
        ],
    },
    "thermostat_stuck": {
        "label": "Stuck thermostat blocking coolant flow (liquid-cooled bikes)",
        "prior": 0.13,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Motorcycle thermostat", "notes": "Match OEM temperature rating; usually inexpensive — replace proactively"},
            {"name": "Thermostat O-ring / gasket", "notes": "Replace seal whenever thermostat housing is opened"},
        ],
    },
    "water_pump_fail": {
        "label": "Failed water pump impeller or seal (liquid-cooled bikes)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump kit (impeller, seal, O-ring)", "notes": "Some bikes require partial engine disassembly — consult service manual"},
        ],
    },
    "fan_fault": {
        "label": "Cooling fan not activating at idle (liquid-cooled bikes with electric fan)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant temperature switch / thermo switch", "notes": "Triggers the fan relay at operating temp; test continuity at temp"},
            {"name": "Fan relay", "notes": "Swap relay before replacing fan motor"},
            {"name": "Fan motor assembly", "notes": "Test with direct 12V connection before replacing"},
        ],
    },
    "oil_low": {
        "label": "Low or degraded engine oil — critical for air-cooled bikes where oil is the primary coolant",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Engine oil (correct grade for your motorcycle)", "notes": "Air-cooled bikes run hotter — use the grade specified in the owner's manual. Check level warm."},
            {"name": "Oil filter", "notes": "Replace with every oil change"},
        ],
    },
    "head_gasket": {
        "label": "Blown head gasket (combustion gas entering coolant or oil)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Head gasket combustion leak test kit", "notes": "Blue fluid turns yellow/green if combustion gases are present in coolant"},
        ],
    },
    "air_filter_blocked": {
        "label": "Severely blocked air filter restricting cooling airflow over air-cooled fins",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter element", "notes": "A clogged filter also richens the mixture, adding heat to the combustion cycle"},
        ],
    },
    "riding_conditions": {
        "label": "Heat soak from riding conditions — extended idling, slow traffic, or no airflow (air-cooled bikes especially)",
        "prior": 0.15,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Oil cooler (aftermarket)", "notes": "Effective for city riders on air-cooled bikes suffering heat soak in traffic"},
            {"name": "Cooling fin cleaning brush", "notes": "Mud and debris packed between fins drastically reduces heat dissipation"},
        ],
    },
}

OVERHEATING_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "Is your motorcycle air-cooled or liquid-cooled (does it have a radiator)?",
        "options": [
            {
                "match": "liquid_cooled",
                "label": "Liquid-cooled — has a radiator",
                "deltas": {
                    "coolant_low": +0.15,
                    "thermostat_stuck": +0.10,
                    "water_pump_fail": +0.10,
                    "fan_fault": +0.10,
                    "oil_low": -0.05,
                    "air_filter_blocked": -0.05,
                    "riding_conditions": -0.10,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "air_cooled",
                "label": "Air-cooled — no radiator, just cooling fins",
                "deltas": {
                    "oil_low": +0.20,
                    "riding_conditions": +0.15,
                    "air_filter_blocked": +0.10,
                },
                "eliminate": ["coolant_low", "thermostat_stuck", "water_pump_fail", "fan_fault"],
                "next_node": "oil_level",
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "overheat_symptom",
            },
        ],
    },

    "coolant_level": {
        "question": "Check the coolant overflow reservoir when the engine is cold. What is the level?",
        "options": [
            {
                "match": "level_low_or_empty",
                "label": "Low or empty — below the MIN mark",
                "deltas": {
                    "coolant_low": +0.30,
                    "head_gasket": +0.10,
                    "water_pump_fail": +0.05,
                },
                "eliminate": [],
                "next_node": "fan_running",
            },
            {
                "match": "level_ok",
                "label": "Correct — between MIN and MAX marks",
                "deltas": {
                    "coolant_low": -0.20,
                    "thermostat_stuck": +0.15,
                    "fan_fault": +0.10,
                    "water_pump_fail": +0.10,
                },
                "eliminate": [],
                "next_node": "fan_running",
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "fan_running",
            },
        ],
    },

    "fan_running": {
        "question": "When the engine reaches operating temperature, does the cooling fan kick on automatically?",
        "options": [
            {
                "match": "fan_yes",
                "label": "Yes — fan spins up when hot",
                "deltas": {
                    "fan_fault": -0.30,
                    "thermostat_stuck": +0.15,
                    "water_pump_fail": +0.10,
                },
                "eliminate": [],
                "next_node": "exhaust_check",
            },
            {
                "match": "fan_no",
                "label": "No — fan never runs even when engine is hot",
                "deltas": {
                    "fan_fault": +0.40,
                    "thermostat_stuck": -0.05,
                },
                "eliminate": [],
                "next_node": "exhaust_check",
            },
            {
                "match": "fan_unknown",
                "label": "Not sure / haven't checked",
                "deltas": {},
                "eliminate": [],
                "next_node": "exhaust_check",
            },
        ],
    },

    "exhaust_check": {
        "question": "Is there white or sweet-smelling smoke coming from the exhaust?",
        "options": [
            {
                "match": "white_smoke",
                "label": "Yes — white or sweet-smelling exhaust smoke",
                "deltas": {
                    "head_gasket": +0.35,
                    "coolant_low": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_white_smoke",
                "label": "No unusual exhaust smoke",
                "deltas": {
                    "head_gasket": -0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "exhaust_unknown",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "oil_level": {
        "question": "Check the engine oil level (sight glass or dipstick per your manual, engine warm, bike upright). What do you see?",
        "options": [
            {
                "match": "oil_low",
                "label": "Low — below the minimum mark",
                "deltas": {
                    "oil_low": +0.40,
                    "riding_conditions": +0.05,
                },
                "eliminate": [],
                "next_node": "idle_conditions",
            },
            {
                "match": "oil_ok_but_dark",
                "label": "Level is fine but oil is very dark / overdue for a change",
                "deltas": {
                    "oil_low": +0.15,
                    "riding_conditions": +0.10,
                },
                "eliminate": [],
                "next_node": "idle_conditions",
            },
            {
                "match": "oil_ok",
                "label": "Level and condition look fine",
                "deltas": {
                    "oil_low": -0.25,
                    "riding_conditions": +0.15,
                    "air_filter_blocked": +0.10,
                    "head_gasket": +0.10,
                },
                "eliminate": [],
                "next_node": "idle_conditions",
            },
        ],
    },

    "idle_conditions": {
        "question": "When does the overheating happen?",
        "options": [
            {
                "match": "slow_traffic_idle",
                "label": "Mainly at low speed, stopped in traffic, or extended idling",
                "deltas": {
                    "riding_conditions": +0.30,
                    "air_filter_blocked": +0.05,
                    "head_gasket": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "even_at_speed",
                "label": "Even at highway speeds with airflow",
                "deltas": {
                    "riding_conditions": -0.20,
                    "oil_low": +0.15,
                    "air_filter_blocked": +0.10,
                    "head_gasket": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "when_unknown",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "overheat_symptom": {
        "question": "What made you think the engine is overheating?",
        "options": [
            {
                "match": "temp_warning",
                "label": "Temperature warning light or high gauge reading",
                "deltas": {
                    "thermostat_stuck": +0.05,
                    "coolant_low": +0.05,
                    "oil_low": +0.05,
                    "fan_fault": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "steam_smell",
                "label": "Steam, boiling coolant, or sweet smell",
                "deltas": {
                    "coolant_low": +0.25,
                    "head_gasket": +0.15,
                    "riding_conditions": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "power_loss_shutdown",
                "label": "Sudden power loss or engine shut down from heat",
                "deltas": {
                    "oil_low": +0.20,
                    "coolant_low": +0.10,
                    "riding_conditions": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"coolant_low": +0.08, "fan_fault": +0.06, "riding_conditions": +0.10},
        "cold": {"thermostat_stuck": +0.08},
    },
    "mileage_band": {
        "high": {"water_pump_fail": +0.08, "head_gasket": +0.06},
    },
    "storage_time": {
        "months": {"coolant_low": +0.08, "thermostat_stuck": +0.06},
        "season": {"coolant_low": +0.10, "thermostat_stuck": +0.08, "water_pump_fail": +0.06},
    },
    "first_start_of_season": {
        "yes": {"coolant_low": +0.08, "thermostat_stuck": +0.06},
    },
}

OVERHEATING_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After fixing the cooling system, flush and refill with fresh coolant — overheating events degrade the coolant inhibitors.",
    "Check the radiator cap pressure rating — a weak cap allows coolant to boil at lower temperatures.",
]
