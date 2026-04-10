"""
Crank-no-start diagnostic tree — ATV/UTV variant.

ATVs are heavily carbureted (carb jets clog from ethanol and storage),
choke is frequently misused, and flooding from repeated cranking is common.
Fuel petcock vacuum failures mirror motorcycle diagnostics.
"""

CRANK_NO_START_ATV_HYPOTHESES: dict[str, dict] = {
    "stale_fuel_carb": {
        "label": "Stale fuel or gummed carburetor jets — varnish from ethanol-blend fuel during storage",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Carburetor cleaner spray", "notes": "Spray through all jets and passages; soak overnight for stubborn varnish"},
            {"name": "Carb rebuild kit (jets, needle, float needle)", "notes": "If machine sat for a season, a full carb clean or rebuild is often needed"},
            {"name": "Fresh fuel + fuel stabilizer", "notes": "Drain the tank and refill with fresh fuel; add stabilizer for future storage"},
        ],
    },
    "fouled_plug": {
        "label": "Fouled or failed spark plug",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (correct heat range)", "notes": "Pull and inspect — black/oily = flooded or rich; white = lean; cracked = replace"},
        ],
    },
    "choke_issue": {
        "label": "Choke not engaged for cold start, or stuck engaged for warm start",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Choke cable / enrichment circuit", "notes": "Cold start: choke should be ON (closed). Warm start: choke must be fully OFF — stuck choke floods engine"},
        ],
    },
    "no_fuel": {
        "label": "No fuel reaching engine — petcock closed, empty tank, or clogged fuel line",
        "prior": 0.15,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Inline fuel filter", "notes": "Replace if not serviced recently — ethanol-blend fuel leaves deposits"},
            {"name": "Petcock rebuild kit", "notes": "Vacuum petcocks fail and block fuel flow; test by switching to PRI (prime) position"},
        ],
    },
    "flooded": {
        "label": "Engine flooded from repeated cranking or stuck choke",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh spark plug", "notes": "Remove plug, crank briefly to clear cylinder, wait 10 minutes before restarting with choke OFF"},
        ],
    },
    "cdi_ignition": {
        "label": "CDI unit or ignition coil failure — no spark",
        "prior": 0.09,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Ignition coil", "notes": "Check for spark: remove plug, ground it to the frame, crank — should see strong blue spark"},
            {"name": "CDI unit / igniter module", "notes": "No spark with good coil and plug = suspect CDI; usually not repairable, replace as a unit"},
        ],
    },
}

CRANK_NO_START_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "Has the machine been sitting in storage, or was it running recently?",
        "options": [
            {
                "match": "sat_long",
                "label": "Sat for weeks or months without being run",
                "deltas": {
                    "stale_fuel_carb": +0.35,
                    "fouled_plug": +0.10,
                    "no_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
            {
                "match": "ran_recently",
                "label": "Was running fine until recently",
                "deltas": {
                    "cdi_ignition": +0.15,
                    "fouled_plug": +0.15,
                    "choke_issue": +0.10,
                    "stale_fuel_carb": -0.10,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
            {
                "match": "first_start",
                "label": "First start of the riding season / just got it",
                "deltas": {
                    "stale_fuel_carb": +0.25,
                    "no_fuel": +0.12,
                    "choke_issue": +0.12,
                    "fouled_plug": +0.10,
                },
                "eliminate": [],
                "next_node": "choke_check",
            },
        ],
    },

    "choke_check": {
        "question": "Is the engine cold or warm, and what choke position are you using?",
        "options": [
            {
                "match": "cold_choke_off",
                "label": "Cold engine — choke is in OFF or open position",
                "deltas": {
                    "choke_issue": +0.45,
                },
                "eliminate": ["flooded"],
                "next_node": "fuel_check",
            },
            {
                "match": "cold_choke_on",
                "label": "Cold engine — choke is ON (closed/enriched), cranking normally",
                "deltas": {
                    "choke_issue": -0.10,
                    "stale_fuel_carb": +0.10,
                    "no_fuel": +0.08,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "warm_choke_on",
                "label": "Warm engine — choke is still ON",
                "deltas": {
                    "choke_issue": +0.40,
                    "flooded": +0.25,
                },
                "eliminate": ["cdi_ignition"],
                "next_node": "fuel_check",
            },
            {
                "match": "choke_correct",
                "label": "Warm engine with choke OFF — correct setup",
                "deltas": {
                    "stale_fuel_carb": +0.10,
                    "fouled_plug": +0.10,
                    "cdi_ignition": +0.08,
                },
                "eliminate": ["choke_issue"],
                "next_node": "fuel_check",
            },
        ],
    },

    "fuel_check": {
        "question": "Is there fresh fuel in the tank, and is the petcock (fuel tap) set to ON or PRI?",
        "options": [
            {
                "match": "petcock_off_or_empty",
                "label": "Petcock was on OFF, or tank is empty",
                "deltas": {
                    "no_fuel": +0.60,
                },
                "eliminate": ["cdi_ignition", "flooded"],
                "next_node": None,
            },
            {
                "match": "fuel_ok",
                "label": "Fresh fuel, petcock on ON or PRI",
                "deltas": {
                    "no_fuel": -0.10,
                    "stale_fuel_carb": +0.05,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
            {
                "match": "old_fuel",
                "label": "Fuel has been in the tank for months",
                "deltas": {
                    "stale_fuel_carb": +0.25,
                    "no_fuel": +0.10,
                    "fouled_plug": +0.08,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
        ],
    },

    "spark_check": {
        "question": "Have you checked for spark? (Remove plug, ground to frame, crank — look for strong blue spark.)",
        "options": [
            {
                "match": "good_spark",
                "label": "Yes — confirmed strong blue spark",
                "deltas": {
                    "cdi_ignition": -0.30,
                    "fouled_plug": -0.10,
                    "stale_fuel_carb": +0.20,
                    "no_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "weak_no_spark",
                "label": "Weak/orange spark or no spark",
                "deltas": {
                    "cdi_ignition": +0.30,
                    "fouled_plug": +0.25,
                },
                "eliminate": ["stale_fuel_carb", "no_fuel", "choke_issue"],
                "next_node": None,
            },
            {
                "match": "not_checked",
                "label": "Haven't checked spark yet",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"choke_issue": +0.10, "stale_fuel_carb": +0.06},
        "hot": {"flooded": +0.08, "choke_issue": +0.06},
    },
    "mileage_band": {
        "high": {"cdi_ignition": +0.08, "fouled_plug": +0.06},
    },
    "storage_time": {
        "months": {"stale_fuel_carb": +0.20, "no_fuel": +0.08, "fouled_plug": +0.06},
        "season": {"stale_fuel_carb": +0.25, "no_fuel": +0.10, "fouled_plug": +0.08},
    },
    "first_start_of_season": {
        "yes": {"stale_fuel_carb": +0.18, "choke_issue": +0.08, "fouled_plug": +0.06},
    },
}

CRANK_NO_START_ATV_POST_DIAGNOSIS: list[str] = [
    "After starting, let the engine idle 5 minutes and check for stumble or surge — indicates secondary fuel delivery issues in the carb.",
    "Add fuel stabilizer to the tank at the end of every riding season to prevent carb varnish.",
    "Check the air filter — a clogged filter is often found alongside a stale-fuel carb issue on machines coming out of storage.",
]
