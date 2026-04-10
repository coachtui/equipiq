"""
Overheating diagnostic tree — PWC (personal watercraft) variant.

Water-cooled exhaust system cooling is unique to PWCs — a blocked
exhaust cooling circuit can cause the rubber exhaust hose to melt
or catch fire inside the hull. Running the PWC beached or out of water
(even briefly) destroys the impeller rubber and water pump seals.
"""

OVERHEATING_PWC_HYPOTHESES: dict[str, dict] = {
    "water_intake_clogged": {
        "label": "Clogged water intake — weeds, debris, or sand blocking cooling water supply",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "The PWC draws cooling water through the pump intake. Weeds or debris blocking the intake starves the cooling system. Clear the intake grate and flush with fresh water."},
        ],
    },
    "ran_beached": {
        "label": "Ran out of water or beached — sand/air ingestion destroys pump and seals",
        "prior": 0.22,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Impeller seal kit", "notes": "Running even briefly out of water melts the wear ring and destroys pump seals. Do not restart until fully inspected."},
            {"name": "Exhaust hose / water-cooled exhaust system", "notes": "A beached PWC can melt or char the exhaust hose from lack of cooling water — inspect the full exhaust run"},
        ],
    },
    "thermostat_stuck": {
        "label": "Thermostat stuck closed — coolant not reaching heat exchanger",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Thermostat (check OEM spec)", "notes": "Closed-loop cooled PWCs (closed hull design) have a thermostat — stuck closed prevents heat from being transferred to the lake/river water"},
        ],
    },
    "exhaust_cooling_blocked": {
        "label": "Exhaust water jacket clogged — cooling water not flowing through exhaust manifold",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust manifold / water-cooled exhaust elbow", "notes": "Calcium deposits and corrosion block the water passages in water-cooled exhaust systems. Flush with flush attachment after every saltwater ride."},
        ],
    },
    "low_coolant": {
        "label": "Low coolant — closed-loop cooling system loss (closed-loop models only)",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant (distilled water + PWC-compatible coolant)", "notes": "Closed-loop systems (Sea-Doo RXP/RXT, some Yamahas) have a coolant reservoir — open-loop models use raw lake/river water and have no coolant"},
        ],
    },
    "temp_sensor_fault": {
        "label": "Faulty temperature sensor — false overheat warning without actual overheating",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Engine coolant temperature sensor", "notes": "If the engine feels cool to the touch but the gauge shows overheating, the sensor may be faulty. Verify with a scan tool before condemning the cooling system."},
        ],
    },
}

OVERHEATING_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "What were the conditions when overheating occurred — normal riding, shallow water, or after the nose was out of water?",
        "options": [
            {
                "match": "beached_shallow",
                "label": "PWC was beached, grounded, or nose was pointing up out of water",
                "deltas": {
                    "ran_beached": +0.70,
                },
                "eliminate": ["thermostat_stuck", "low_coolant", "temp_sensor_fault"],
                "next_node": "intake_check",
            },
            {
                "match": "weedy_water",
                "label": "Normal riding but in weedy, shallow, or debris-filled water",
                "deltas": {
                    "water_intake_clogged": +0.55,
                    "exhaust_cooling_blocked": +0.10,
                },
                "eliminate": ["ran_beached", "low_coolant"],
                "next_node": "intake_check",
            },
            {
                "match": "normal_conditions",
                "label": "Normal open water riding — no unusual conditions",
                "deltas": {
                    "thermostat_stuck": +0.25,
                    "exhaust_cooling_blocked": +0.20,
                    "water_intake_clogged": +0.15,
                    "low_coolant": +0.10,
                },
                "eliminate": ["ran_beached"],
                "next_node": "intake_check",
            },
        ],
    },

    "intake_check": {
        "question": "Is there any weeds, sand, or debris in the intake grate or pump tunnel?",
        "options": [
            {
                "match": "intake_blocked",
                "label": "Yes — intake or pump is packed with weeds or debris",
                "deltas": {
                    "water_intake_clogged": +0.65,
                },
                "eliminate": ["thermostat_stuck", "low_coolant", "temp_sensor_fault"],
                "next_node": None,
            },
            {
                "match": "intake_clear",
                "label": "Intake is clear",
                "deltas": {
                    "water_intake_clogged": -0.20,
                    "thermostat_stuck": +0.15,
                    "exhaust_cooling_blocked": +0.12,
                },
                "eliminate": [],
                "next_node": "cooling_flow_check",
            },
        ],
    },

    "cooling_flow_check": {
        "question": "Does the tell-tale water stream (pee hole) produce a steady stream when running?",
        "options": [
            {
                "match": "no_telltale",
                "label": "Little or no water from the tell-tale / pee hole",
                "deltas": {
                    "water_intake_clogged": +0.20,
                    "thermostat_stuck": +0.20,
                    "exhaust_cooling_blocked": +0.15,
                },
                "eliminate": ["temp_sensor_fault", "low_coolant"],
                "next_node": "coolant_check",
            },
            {
                "match": "telltale_ok",
                "label": "Normal steady stream from the tell-tale",
                "deltas": {
                    "water_intake_clogged": -0.15,
                    "thermostat_stuck": -0.10,
                    "exhaust_cooling_blocked": -0.10,
                    "temp_sensor_fault": +0.20,
                    "low_coolant": +0.15,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
        ],
    },

    "coolant_check": {
        "question": "Is this a closed-loop cooled model, and if so, what is the coolant level?",
        "options": [
            {
                "match": "closed_loop_low",
                "label": "Closed-loop model — coolant reservoir is low or empty",
                "deltas": {
                    "low_coolant": +0.55,
                },
                "eliminate": ["water_intake_clogged", "ran_beached"],
                "next_node": None,
            },
            {
                "match": "closed_loop_ok",
                "label": "Closed-loop model — coolant level is normal",
                "deltas": {
                    "thermostat_stuck": +0.20,
                    "exhaust_cooling_blocked": +0.15,
                    "temp_sensor_fault": +0.15,
                    "low_coolant": -0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "open_loop",
                "label": "Open-loop model (uses raw water for cooling) — no coolant reservoir",
                "deltas": {
                    "low_coolant": -0.30,
                    "thermostat_stuck": +0.15,
                    "exhaust_cooling_blocked": +0.15,
                },
                "eliminate": ["low_coolant"],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"exhaust_cooling_blocked": +0.15, "water_intake_clogged": +0.08, "thermostat_stuck": +0.06},
    },
    "mileage_band": {
        "high": {"exhaust_cooling_blocked": +0.10, "thermostat_stuck": +0.08},
    },
    "storage_time": {
        "months": {"thermostat_stuck": +0.06},
        "season": {"thermostat_stuck": +0.08, "exhaust_cooling_blocked": +0.06},
    },
    "first_start_of_season": {
        "yes": {"thermostat_stuck": +0.06, "water_intake_clogged": +0.05},
    },
    "climate": {
        "hot": {"water_intake_clogged": +0.06, "ran_beached": +0.05},
    },
}

OVERHEATING_PWC_POST_DIAGNOSIS: list[str] = [
    "After any overheating event, flush the entire cooling system with fresh water using a flush adapter before the next ride.",
    "For saltwater use, flush with fresh water after every single ride — calcium deposits in the exhaust water jacket are cumulative and eventually block cooling entirely.",
    "Never run a PWC on the trailer to 'test' it — even 30 seconds without water will melt pump seals and the wear ring.",
]
