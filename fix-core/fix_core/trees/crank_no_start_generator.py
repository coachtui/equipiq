"""
Cranks but won't start diagnostic tree — generator variant.

Engine rotates when pulled or electric start engages, but won't fire and run.
Stale/varnished fuel and carburetor gum are by far the most common causes
on generators that sit between uses.
"""

CRANK_NO_START_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "stale_fuel_carb": {
        "label": "Stale fuel or varnished carburetor jet — ethanol gum blocking fuel delivery",
        "prior": 0.35,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh gasoline (non-ethanol preferred for small engines)", "notes": "Drain old fuel completely. Old fuel can varnish in 30–60 days in a carburetor bowl."},
            {"name": "Carburetor cleaner spray", "notes": "Spray into carb throat and pilot jet passage; also soak float bowl if accessible"},
            {"name": "Carburetor rebuild kit", "notes": "Includes main jet, pilot jet, float needle, and gaskets — often under $10"},
            {"name": "Fuel stabilizer", "notes": "Add before every storage period; prevents varnish formation"},
        ],
    },
    "choke_position": {
        "label": "Choke not fully closed for cold start",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Cold starts require FULL choke (closed). Set choke lever to CHOKE position before first pull. Open gradually once engine fires."},
        ],
    },
    "spark_plug_fouled": {
        "label": "Fouled or worn spark plug — no or weak spark",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (check generator manual for correct type)", "notes": "Most small engines use a Champion RJ19LM or NGK BPR6ES equivalent — confirm with manual"},
            {"name": "Spark plug gap tool", "notes": "Set gap to spec — typically 0.030\" (0.76mm) for most small engines"},
        ],
    },
    "low_oil_shutoff": {
        "label": "Low oil auto-shutoff activated — engine will crank but not fire",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Engine oil", "notes": "Some generators crank but refuse to fire (not just refuse to crank) when oil is low. Check dipstick first."},
        ],
    },
    "air_filter_blocked": {
        "label": "Severely clogged air filter causing over-rich, flooded condition",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter element (foam or paper, per generator model)", "notes": "A completely clogged filter prevents adequate air entry — engine floods instead of starting"},
        ],
    },
    "ignition_coil": {
        "label": "Failed or cracked ignition coil — no spark at plug",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Ignition coil (armature)", "notes": "Test with a spark tester tool before replacing. Set air gap to 0.010\" when installing."},
        ],
    },
    "flooded_engine": {
        "label": "Flooded engine — too much fuel in cylinder from repeated failed starts",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Remove spark plug, pull cord several times to clear cylinder. Let sit 15 min with plug out. Reinstall and try with choke OPEN."},
        ],
    },
}

CRANK_NO_START_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "How long has the generator been sitting unused, and was fuel left in the tank?",
        "options": [
            {
                "match": "long_storage_fuel_in",
                "label": "Sitting 30+ days (or over a season) with fuel left in it",
                "deltas": {
                    "stale_fuel_carb": +0.35,
                    "spark_plug_fouled": +0.05,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
            {
                "match": "long_storage_no_fuel",
                "label": "Sitting 30+ days but tank was drained before storage",
                "deltas": {
                    "stale_fuel_carb": +0.10,
                    "spark_plug_fouled": +0.10,
                    "ignition_coil": +0.05,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
            {
                "match": "used_recently",
                "label": "Was running fine recently — sudden failure",
                "deltas": {
                    "stale_fuel_carb": -0.15,
                    "low_oil_shutoff": +0.15,
                    "spark_plug_fouled": +0.10,
                    "ignition_coil": +0.05,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
        ],
    },

    "choke_check": {
        "question": "Is the choke set correctly for a cold start? (Should be FULLY CLOSED / CHOKE position for a cold engine.)",
        "options": [
            {
                "match": "choke_correct",
                "label": "Yes — choke is fully closed for cold start",
                "deltas": {
                    "choke_position": -0.15,
                    "stale_fuel_carb": +0.05,
                    "spark_plug_fouled": +0.05,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
            {
                "match": "choke_open",
                "label": "Choke was open (RUN position) — engine may be cold",
                "deltas": {
                    "choke_position": +0.40,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
            {
                "match": "not_sure_choke",
                "label": "Not sure where choke is set",
                "deltas": {
                    "choke_position": +0.15,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
        ],
    },

    "oil_level": {
        "question": "Is the engine oil level correct? (Check dipstick — many generators refuse to start when oil is low.)",
        "options": [
            {
                "match": "oil_low_or_unchecked",
                "label": "Low or haven't checked",
                "deltas": {
                    "low_oil_shutoff": +0.35,
                },
                "eliminate": [],
                "next_node": "spark_test",
            },
            {
                "match": "oil_ok",
                "label": "Oil level is correct",
                "deltas": {
                    "low_oil_shutoff": -0.10,
                    "stale_fuel_carb": +0.05,
                    "spark_plug_fouled": +0.05,
                },
                "eliminate": [],
                "next_node": "spark_test",
            },
        ],
    },

    "spark_test": {
        "question": "Remove the spark plug and ground it against the engine block. Do you see a strong blue spark when you pull the cord?",
        "options": [
            {
                "match": "no_spark",
                "label": "No spark or very weak/orange spark",
                "deltas": {
                    "spark_plug_fouled": +0.30,
                    "ignition_coil": +0.20,
                    "stale_fuel_carb": -0.10,
                    "choke_position": -0.10,
                },
                "eliminate": ["flooded_engine"],
                "next_node": None,
            },
            {
                "match": "good_spark",
                "label": "Strong blue spark — ignition is good",
                "deltas": {
                    "spark_plug_fouled": -0.20,
                    "ignition_coil": -0.20,
                    "stale_fuel_carb": +0.20,
                    "air_filter_blocked": +0.10,
                    "flooded_engine": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "plug_wet",
                "label": "Plug is wet with fuel (flooded)",
                "deltas": {
                    "flooded_engine": +0.40,
                    "choke_position": +0.15,
                    "stale_fuel_carb": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cant_test",
                "label": "Can't test right now",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"choke_position": +0.10, "spark_plug_fouled": +0.06},
    },
    "storage_time": {
        "weeks": {"stale_fuel_carb": +0.08, "choke_position": +0.04},
        "months": {"stale_fuel_carb": +0.15, "air_filter_blocked": +0.08, "ignition_coil": +0.04},
        "season": {"stale_fuel_carb": +0.18, "air_filter_blocked": +0.10, "spark_plug_fouled": +0.06},
    },
    "first_start_of_season": {
        "yes": {"stale_fuel_carb": +0.12, "choke_position": +0.08, "low_oil_shutoff": +0.05},
    },
    "mileage_band": {
        "high": {"ignition_coil": +0.06, "spark_plug_fouled": +0.06},
    },
}

CRANK_NO_START_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After the generator starts, load-test it with a known good load — some carb issues only show up under load.",
    "Add fuel stabilizer to the fresh fuel and run it through the carb for 5 minutes before storing again.",
]
