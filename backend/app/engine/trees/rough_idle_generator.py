"""
Rough idle / surging diagnostic tree — generator variant.

Generator "rough idle" includes: engine surging (RPM hunting up and down),
unsteady output frequency/voltage, rough running at no-load, and stalling
at idle. Governor hunting is particularly common on generators.
"""

ROUGH_IDLE_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "governor_hunting": {
        "label": "Governor surging — RPM hunting up and down due to governor spring or linkage issue",
        "prior": 0.25,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Governor spring", "notes": "Weak or stretched spring causes RPM to oscillate. Small spring, cheap part — inspect and replace if it has lost tension."},
            {"name": "Governor linkage kit", "notes": "Check for worn pivot points, binding, or incorrect linkage adjustment. Linkage must move freely."},
        ],
    },
    "dirty_pilot_jet": {
        "label": "Clogged carburetor pilot (idle) jet — lean idle causing surge or rough idle",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Carburetor cleaner spray", "notes": "Spray directly into pilot jet passage. Jet orifice is very small — even partial blockage causes lean surge."},
            {"name": "Carburetor rebuild kit", "notes": "Includes pilot jet, main jet, float needle, and gaskets"},
        ],
    },
    "stale_fuel": {
        "label": "Stale or water-contaminated fuel causing lean/inconsistent burn",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh gasoline", "notes": "Drain tank and carb bowl completely before adding fresh fuel. Non-ethanol fuel preferred for generators."},
        ],
    },
    "spark_plug_fouled": {
        "label": "Fouled or worn spark plug causing misfires and rough running",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (per generator manual)", "notes": "Inspect for carbon fouling, oil fouling, or worn electrode. Replace and regap."},
        ],
    },
    "air_leak": {
        "label": "Air leak at carburetor intake gasket or throttle shaft causing lean rough idle",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Carburetor intake gasket", "notes": "Spray carburetor cleaner around the carb mounting flange while engine runs — RPM change indicates a leak"},
            {"name": "Throttle shaft seal", "notes": "Worn throttle shaft allows air bypass; common on high-hour carbs"},
        ],
    },
    "valve_clearance": {
        "label": "Incorrect valve clearance (high-hour engines) causing rough combustion",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Feeler gauge set", "notes": "Check and adjust intake and exhaust valve clearance per service manual"},
        ],
    },
    "low_fuel_level": {
        "label": "Low fuel level causing intermittent fuel starvation and surging",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh gasoline", "notes": "Fuel pickup tube may suck air if tank is nearly empty. Refill and test."},
        ],
    },
}

ROUGH_IDLE_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe what the engine is doing?",
        "options": [
            {
                "match": "surging_hunting",
                "label": "Surging — RPM cycles up and down rhythmically (hunting)",
                "deltas": {
                    "governor_hunting": +0.30,
                    "dirty_pilot_jet": +0.15,
                    "stale_fuel": +0.10,
                    "low_fuel_level": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_freshness",
            },
            {
                "match": "rough_misfiring",
                "label": "Rough and misfiring — uneven, bumpy, not rhythmic surging",
                "deltas": {
                    "spark_plug_fouled": +0.25,
                    "dirty_pilot_jet": +0.15,
                    "valve_clearance": +0.10,
                    "governor_hunting": -0.10,
                },
                "eliminate": [],
                "next_node": "fuel_freshness",
            },
            {
                "match": "stalling_at_idle",
                "label": "Stalls or dies at idle, runs ok when throttled up",
                "deltas": {
                    "dirty_pilot_jet": +0.35,
                    "air_leak": +0.15,
                    "governor_hunting": -0.10,
                },
                "eliminate": [],
                "next_node": "fuel_freshness",
            },
        ],
    },

    "fuel_freshness": {
        "question": "How old is the fuel in the tank and when was the carburetor last cleaned?",
        "options": [
            {
                "match": "old_fuel_dirty_carb",
                "label": "Fuel is 60+ days old and/or carb hasn't been cleaned in over a year",
                "deltas": {
                    "stale_fuel": +0.25,
                    "dirty_pilot_jet": +0.20,
                },
                "eliminate": [],
                "next_node": "spark_plug_age",
            },
            {
                "match": "fresh_fuel_recent_service",
                "label": "Fresh fuel and recently serviced carburetor",
                "deltas": {
                    "stale_fuel": -0.15,
                    "dirty_pilot_jet": -0.10,
                    "governor_hunting": +0.15,
                    "air_leak": +0.10,
                    "valve_clearance": +0.10,
                },
                "eliminate": [],
                "next_node": "spark_plug_age",
            },
            {
                "match": "unknown_fuel",
                "label": "Not sure",
                "deltas": {
                    "stale_fuel": +0.05,
                },
                "eliminate": [],
                "next_node": "spark_plug_age",
            },
        ],
    },

    "spark_plug_age": {
        "question": "When was the spark plug last replaced?",
        "options": [
            {
                "match": "old_plug",
                "label": "Never replaced, or over 100 hours ago",
                "deltas": {
                    "spark_plug_fouled": +0.25,
                },
                "eliminate": [],
                "next_node": "governor_check",
            },
            {
                "match": "recent_plug",
                "label": "Replaced recently",
                "deltas": {
                    "spark_plug_fouled": -0.15,
                    "governor_hunting": +0.10,
                    "dirty_pilot_jet": +0.05,
                },
                "eliminate": [],
                "next_node": "governor_check",
            },
            {
                "match": "unknown_plug",
                "label": "Not sure",
                "deltas": {
                    "spark_plug_fouled": +0.05,
                },
                "eliminate": [],
                "next_node": "governor_check",
            },
        ],
    },

    "governor_check": {
        "question": "Does the engine rhythmically hunt (RPM cycles up and down), hold a steady rough idle, or tend to stall when a load is applied?",
        "options": [
            {
                "match": "hunting_rhythmic",
                "label": "Rhythmic hunting — RPM cycles up and down steadily",
                "deltas": {
                    "governor_hunting": +0.30,
                    "dirty_pilot_jet": +0.05,
                    "stale_fuel": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "steady_rough",
                "label": "Steady rough idle — not rhythmic, just rough and uneven",
                "deltas": {
                    "dirty_pilot_jet": +0.20,
                    "spark_plug_fouled": +0.15,
                    "valve_clearance": +0.10,
                    "governor_hunting": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "stalls_under_load",
                "label": "Runs at idle but stalls or dies when a load is applied",
                "deltas": {
                    "air_leak": +0.20,
                    "dirty_pilot_jet": +0.15,
                    "governor_hunting": +0.10,
                    "stale_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"governor_hunting": +0.06, "stale_fuel": +0.04},
    },
    "storage_time": {
        "months": {"dirty_pilot_jet": +0.15, "stale_fuel": +0.10},
        "season": {"dirty_pilot_jet": +0.18, "stale_fuel": +0.12, "spark_plug_fouled": +0.06},
    },
    "first_start_of_season": {
        "yes": {"dirty_pilot_jet": +0.12, "stale_fuel": +0.08},
    },
    "mileage_band": {
        "high": {"valve_clearance": +0.08, "governor_hunting": +0.06},
    },
}

ROUGH_IDLE_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After carburetor service, confirm the governor linkage moves freely end-to-end before reassembly.",
    "Set idle RPM to spec (typically 3,600 RPM for 60 Hz output) using a tachometer — off-spec idle causes output frequency drift.",
]
