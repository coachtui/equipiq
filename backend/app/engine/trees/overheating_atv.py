"""
Overheating diagnostic tree — ATV/UTV variant.

Mud-packed radiator is the dominant ATV overheating cause — not present
in any other vehicle tree. Low-speed trail riding with no airflow is also
a common compounding factor. Air-cooled ATVs don't have a coolant system
but can overheat from lean fuel mixture or oil starvation.
"""

OVERHEATING_ATV_HYPOTHESES: dict[str, dict] = {
    "mud_packed_radiator": {
        "label": "Mud or debris packed in radiator fins — blocking airflow",
        "prior": 0.32,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Rinse the radiator fins from behind (rear to front) with low-pressure water. High pressure damages fins. This is the most common ATV overheat cause."},
        ],
    },
    "coolant_low": {
        "label": "Low coolant — loss from slow leak or evaporation",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant (50/50 premixed or concentrate + distilled water)", "notes": "Check the overflow reservoir and the radiator fill point. Do NOT open radiator cap on a hot engine."},
            {"name": "Radiator cap (correct pressure rating)", "notes": "A weak cap lets coolant boil at lower temperatures — test cap with a tester"},
        ],
    },
    "thermostat_stuck": {
        "label": "Thermostat stuck closed — coolant not circulating to radiator",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Thermostat (correct temp range for the engine)", "notes": "Quick test: cold engine overheats fast but upper radiator hose stays cold = stuck thermostat blocking flow"},
        ],
    },
    "low_speed_no_airflow": {
        "label": "Insufficient airflow at low speed — slow trail riding or idling",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Cooling fan (if equipped)", "notes": "Liquid-cooled ATVs have an electric fan — verify it kicks on when the temperature gauge rises. A failed fan causes overheating at idle."},
        ],
    },
    "water_pump_fail": {
        "label": "Failing water pump — reduced coolant flow",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Water pump impeller kit", "notes": "Coolant dripping from weep hole = water pump seal failure. Impellers corrode on machines used in salty or silty water."},
        ],
    },
    "head_gasket": {
        "label": "Head gasket failure — combustion gases entering cooling system",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Block test kit / combustion leak tester", "notes": "Bubbles in radiator or milky oil confirms head gasket. Stop riding immediately — continued use causes more damage."},
        ],
    },
}

OVERHEATING_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "What kind of riding were you doing when it overheated — slow trail riding, mud, or normal speed?",
        "options": [
            {
                "match": "mud_slow_trail",
                "label": "Slow trails or mud — low speed, limited airflow",
                "deltas": {
                    "mud_packed_radiator": +0.30,
                    "low_speed_no_airflow": +0.25,
                    "coolant_low": +0.10,
                },
                "eliminate": [],
                "next_node": "radiator_check",
            },
            {
                "match": "normal_speed",
                "label": "Normal trail or road speed — not particularly slow",
                "deltas": {
                    "coolant_low": +0.20,
                    "thermostat_stuck": +0.20,
                    "mud_packed_radiator": +0.10,
                    "water_pump_fail": +0.10,
                },
                "eliminate": ["low_speed_no_airflow"],
                "next_node": "radiator_check",
            },
            {
                "match": "high_load",
                "label": "Heavy load — towing, hauling, or hill climbing in heat",
                "deltas": {
                    "coolant_low": +0.20,
                    "mud_packed_radiator": +0.15,
                    "head_gasket": +0.10,
                    "water_pump_fail": +0.10,
                },
                "eliminate": [],
                "next_node": "radiator_check",
            },
        ],
    },

    "radiator_check": {
        "question": "Has the radiator been inspected for mud or debris packing in the fins?",
        "options": [
            {
                "match": "radiator_caked",
                "label": "Yes — radiator fins are packed with mud or debris",
                "deltas": {
                    "mud_packed_radiator": +0.65,
                },
                "eliminate": ["thermostat_stuck", "water_pump_fail", "head_gasket"],
                "next_node": None,
            },
            {
                "match": "radiator_clean",
                "label": "Radiator fins are clean and clear",
                "deltas": {
                    "mud_packed_radiator": -0.25,
                    "thermostat_stuck": +0.15,
                    "coolant_low": +0.10,
                    "water_pump_fail": +0.10,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
            {
                "match": "not_checked",
                "label": "Haven't looked at it yet",
                "deltas": {
                    "mud_packed_radiator": +0.10,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
        ],
    },

    "coolant_check": {
        "question": "What is the coolant level in the overflow reservoir (when engine is cold)?",
        "options": [
            {
                "match": "coolant_low",
                "label": "Below the MIN mark or reservoir is empty",
                "deltas": {
                    "coolant_low": +0.45,
                    "head_gasket": +0.15,
                },
                "eliminate": [],
                "next_node": "fan_check",
            },
            {
                "match": "coolant_ok",
                "label": "Coolant level is normal",
                "deltas": {
                    "coolant_low": -0.15,
                    "thermostat_stuck": +0.20,
                    "water_pump_fail": +0.15,
                    "mud_packed_radiator": +0.10,
                },
                "eliminate": [],
                "next_node": "fan_check",
            },
            {
                "match": "coolant_milky",
                "label": "Coolant is milky or has oil floating in it",
                "deltas": {
                    "head_gasket": +0.70,
                },
                "eliminate": ["mud_packed_radiator", "low_speed_no_airflow", "thermostat_stuck"],
                "next_node": None,
            },
        ],
    },

    "fan_check": {
        "question": "Does the electric cooling fan turn on when the temperature gauge rises?",
        "options": [
            {
                "match": "fan_not_running",
                "label": "Fan doesn't seem to turn on — doesn't spin when hot",
                "deltas": {
                    "low_speed_no_airflow": +0.40,
                },
                "eliminate": ["mud_packed_radiator"],
                "next_node": None,
            },
            {
                "match": "fan_ok",
                "label": "Fan runs correctly",
                "deltas": {
                    "low_speed_no_airflow": -0.10,
                    "thermostat_stuck": +0.10,
                    "water_pump_fail": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_fan",
                "label": "This ATV is air-cooled — no fan or radiator",
                "deltas": {
                    "low_speed_no_airflow": +0.10,
                    "coolant_low": -0.30,
                    "thermostat_stuck": -0.30,
                    "water_pump_fail": -0.30,
                    "mud_packed_radiator": -0.30,
                },
                "eliminate": ["coolant_low", "thermostat_stuck", "water_pump_fail", "mud_packed_radiator"],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"coolant_low": +0.08, "low_speed_no_airflow": +0.08, "mud_packed_radiator": +0.06},
        "cold": {"thermostat_stuck": +0.08},
    },
    "mileage_band": {
        "high": {"water_pump_fail": +0.10, "head_gasket": +0.08},
    },
    "storage_time": {
        "months": {"coolant_low": +0.08, "thermostat_stuck": +0.06},
        "season": {"coolant_low": +0.10, "thermostat_stuck": +0.08},
    },
    "first_start_of_season": {
        "yes": {"coolant_low": +0.08, "thermostat_stuck": +0.06},
    },
}

OVERHEATING_ATV_POST_DIAGNOSIS: list[str] = [
    "After resolving the overheat, do a 15-minute ride and monitor temperature — a second overheat event points to head gasket even if the first cause was fixed.",
    "At the start of every season, flush and replace coolant — glycol degrades over time and reduces boiling point protection.",
    "Install radiator guards if riding in heavy brush or mud — bent fins from debris contact are a common slow-onset restriction cause.",
]
