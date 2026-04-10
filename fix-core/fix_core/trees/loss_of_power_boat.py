"""
Loss of power diagnostic tree — boat / marine variant.

Marine "loss of power" includes: engine not reaching WOT RPM, top-end speed
reduction, propeller-related power loss, and cavitation. Fouled bottom paint,
propeller damage, and air entering the fuel system are unique marine causes.
"""

LOSS_OF_POWER_BOAT_HYPOTHESES: dict[str, dict] = {
    "prop_damage": {
        "label": "Propeller damage — bent blade, nicked edge, or wrong pitch causing power loss",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Propeller (correct diameter and pitch for engine)", "notes": "Even a minor nick or bent blade significantly reduces efficiency. Have prop inspected and repaired by a prop shop, or replace."},
            {"name": "Prop pitch check", "notes": "Wrong pitch = engine either over-revs (too little pitch) or can't reach WOT RPM (too much pitch)"},
        ],
    },
    "fouled_bottom": {
        "label": "Fouled hull — heavy barnacle or algae growth creating drag and robbing speed",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Antifouling bottom paint", "notes": "Growth on the hull and running gear creates enormous drag. Even light grass fouling can cost 20–30% of top speed."},
        ],
    },
    "water_in_fuel": {
        "label": "Water in fuel — phase-separated ethanol fuel or tank contamination",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel/water separator filter", "notes": "Cloudy or milky fuel in the filter bowl confirms water contamination. Replace filter and drain tank if heavily contaminated."},
        ],
    },
    "fuel_restriction": {
        "label": "Fuel restriction — clogged fuel filter, carb jet, or restricted fuel flow under WOT",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Inline fuel filter", "notes": "A partially clogged filter may supply enough fuel at idle but starve the engine at WOT"},
            {"name": "Carburetor main jet", "notes": "Partially varnished main jet causes WOT power drop while idle seems normal"},
        ],
    },
    "cavitation": {
        "label": "Cavitation — air or exhaust gas entering the prop zone, causing thrust loss",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts unless cavitation plate is damaged)", "notes": "Symptoms: sudden RPM rise without speed gain, especially in turns. Check cavitation plate for damage and anti-ventilation plate alignment."},
        ],
    },
    "fouled_lower_unit": {
        "label": "Weeds, fishing line, or rope wrapped around prop shaft or lower unit",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(Remove foreign material)", "notes": "Inspect the prop shaft, prop hub, and lower unit for wrapped debris. Fishing line can cut through seals if not removed."},
        ],
    },
    "engine_misfiring": {
        "label": "Engine misfiring — fouled spark plugs or ignition issue reducing cylinder count",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine spark plugs (full set)", "notes": "Inspect for fouling, water damage, or worn electrodes. Replace as a complete set."},
        ],
    },
    "overheat_derate": {
        "label": "Engine overheating triggering RPM/power reduction — overheating protection active",
        "prior": 0.02,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(Address overheating cause)", "notes": "If the temperature gauge is elevated, the engine may be limiting power to prevent damage. Address the overheating root cause."},
        ],
    },
}

LOSS_OF_POWER_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "How does the power loss present itself?",
        "options": [
            {
                "match": "cant_reach_wot",
                "label": "Engine won't reach normal WOT RPM — peaks below the normal range",
                "deltas": {
                    "prop_damage": +0.20,
                    "fuel_restriction": +0.15,
                    "water_in_fuel": +0.10,
                    "fouled_lower_unit": +0.10,
                    "cavitation": -0.05,
                },
                "eliminate": [],
                "next_node": "recent_incident",
            },
            {
                "match": "speed_reduced_same_rpm",
                "label": "Speed is much slower than usual at the same RPM",
                "deltas": {
                    "fouled_bottom": +0.30,
                    "prop_damage": +0.20,
                    "fouled_lower_unit": +0.15,
                    "cavitation": +0.05,
                    "fuel_restriction": -0.05,
                },
                "eliminate": [],
                "next_node": "recent_incident",
            },
            {
                "match": "sudden_rpM_spike",
                "label": "Sudden RPM spike without speed gain (engine races, no thrust)",
                "deltas": {
                    "cavitation": +0.40,
                    "prop_damage": +0.25,
                    "fouled_lower_unit": +0.10,
                    "fouled_bottom": -0.10,
                },
                "eliminate": [],
                "next_node": "recent_incident",
            },
        ],
    },

    "recent_incident": {
        "question": "Has there been any recent impact, grounding, or known encounter with debris (rope, weeds, logs)?",
        "options": [
            {
                "match": "yes_impact",
                "label": "Yes — hit something, grounded, or ran through weeds/debris",
                "deltas": {
                    "prop_damage": +0.30,
                    "fouled_lower_unit": +0.20,
                    "cavitation": +0.10,
                },
                "eliminate": [],
                "next_node": "prop_inspection",
            },
            {
                "match": "no_incident",
                "label": "No — gradual power loss, no known impact",
                "deltas": {
                    "fouled_bottom": +0.20,
                    "water_in_fuel": +0.10,
                    "fuel_restriction": +0.10,
                    "prop_damage": -0.10,
                    "fouled_lower_unit": -0.05,
                },
                "eliminate": [],
                "next_node": "prop_inspection",
            },
        ],
    },

    "prop_inspection": {
        "question": "Can you inspect the propeller? Look for nicked, bent, or missing blade material.",
        "options": [
            {
                "match": "prop_damaged",
                "label": "Propeller is visibly damaged — nicked, bent, or material missing",
                "deltas": {
                    "prop_damage": +0.45,
                    "cavitation": +0.10,
                },
                "eliminate": [],
                "next_node": "hull_fouling",
            },
            {
                "match": "prop_ok",
                "label": "Propeller looks undamaged",
                "deltas": {
                    "prop_damage": -0.20,
                    "fouled_bottom": +0.10,
                    "water_in_fuel": +0.10,
                    "fuel_restriction": +0.10,
                    "engine_misfiring": +0.05,
                },
                "eliminate": [],
                "next_node": "hull_fouling",
            },
            {
                "match": "prop_wrapped",
                "label": "Rope, line, or weeds wrapped around prop shaft",
                "deltas": {
                    "fouled_lower_unit": +0.70,
                },
                "eliminate": ["fouled_bottom", "water_in_fuel", "fuel_restriction", "engine_misfiring"],
                "next_node": None,
            },
        ],
    },

    "hull_fouling": {
        "question": "When was the hull last cleaned or painted? Is there visible growth on the bottom?",
        "options": [
            {
                "match": "fouled_hull",
                "label": "Heavy growth or not cleaned in the current season",
                "deltas": {
                    "fouled_bottom": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "clean_hull",
                "label": "Recently cleaned and painted — hull is clean",
                "deltas": {
                    "fouled_bottom": -0.20,
                    "water_in_fuel": +0.10,
                    "fuel_restriction": +0.10,
                    "engine_misfiring": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "hull_unknown",
                "label": "Not sure / can't check right now",
                "deltas": {
                    "fouled_bottom": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_BOAT_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"fouled_bottom": +0.08, "engine_misfiring": +0.06},
    },
    "storage_time": {
        "months": {"water_in_fuel": +0.10, "fuel_restriction": +0.08},
        "season": {"water_in_fuel": +0.12, "fuel_restriction": +0.10, "engine_misfiring": +0.06},
    },
    "first_start_of_season": {
        "yes": {"water_in_fuel": +0.10, "fuel_restriction": +0.08, "fouled_lower_unit": +0.04},
    },
    "mileage_band": {
        "high": {"engine_misfiring": +0.08, "overheat_derate": +0.04},
    },
}

LOSS_OF_POWER_BOAT_POST_DIAGNOSIS: list[str] = [
    "After prop repair, sea trial at WOT to confirm the engine reaches its rated RPM range — this confirms correct pitch.",
    "If the hull was fouled, check the lower unit and impeller for debris wrapping at the same time.",
]
