"""
Crank-no-start diagnostic tree — motorcycle variant.

Key differences from car tree: petcock (fuel tap) is a common gotcha,
carburetors are far more prevalent than on modern cars, CDI/ignition modules
fail more often, and flooding is common on choke-equipped carb bikes.
"""

CRANK_NO_START_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "no_fuel": {
        "label": "No fuel reaching engine — petcock closed, empty tank, or clogged fuel line",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Inline fuel filter", "notes": "Replace if not serviced in 2+ years; especially important on ethanol-blend fuel"},
            {"name": "Petcock rebuild kit", "notes": "Vacuum petcocks can fail and block fuel flow; test by switching to PRI (prime) position"},
        ],
    },
    "clogged_carb": {
        "label": "Clogged carburetor or injector — varnish from stale fuel blocking jets",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Carburetor cleaner spray", "notes": "Spray through all jets and passages; soak overnight for stubborn varnish"},
            {"name": "Carb rebuild kit (jets, needle, float needle)", "notes": "If bike sat for months, a full clean or rebuild is often needed"},
        ],
    },
    "fouled_spark_plug": {
        "label": "Fouled or failed spark plug",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (correct heat range for engine)", "notes": "Pull and inspect — black/oily = rich/flooding; white = lean; cracked = replace"},
            {"name": "Spark plug wire / cap", "notes": "Check for cracks or corrosion at the boot; single-cylinder bikes only have one to check"},
        ],
    },
    "choke_issue": {
        "label": "Choke not engaged (cold start) or stuck engaged (warm start)",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Enrichment circuit / choke cable", "notes": "Cold engine: ensure choke is ON. Warm engine: ensure choke is fully OFF — stuck choke floods engine"},
        ],
    },
    "cdi_ignition": {
        "label": "CDI unit, ignition coil, or igniter failure — no spark",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Ignition coil", "notes": "Test spark: remove plug, ground it against engine, crank — should have strong blue spark"},
            {"name": "CDI / igniter module", "notes": "No spark with good coil and plug wires = suspect CDI; often not repairable, replace"},
        ],
    },
    "intake_boot_crack": {
        "label": "Cracked intake boot or air leak between carb/throttle body and airbox",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intake boot / carb manifold", "notes": "Lean misfires, hard starting, and surge at idle; spray carb cleaner around boot while running (idle change = leak)"},
        ],
    },
    "flooded": {
        "label": "Engine flooded — too much fuel in cylinder from repeated cranking or stuck choke",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh spark plug", "notes": "Remove plug, crank to blow fuel out, wait 10 minutes before reinstalling; disable choke for restart attempt"},
        ],
    },
}

CRANK_NO_START_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "Is the engine cranking (turning over) when you press the starter? And does it crank at normal speed?",
        "options": [
            {
                "match": "cranks_normal",
                "label": "Yes — cranks at normal speed but won't fire",
                "deltas": {
                    "no_fuel": +0.10,
                    "fouled_spark_plug": +0.10,
                    "clogged_carb": +0.10,
                    "cdi_ignition": +0.10,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_slow",
                "label": "Cranks but slowly — laboring",
                "deltas": {
                    "no_fuel": +0.05,
                    "fouled_spark_plug": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
        ],
    },

    "fuel_check": {
        "question": "Does the tank have fuel, and is the petcock (fuel tap) set to ON or RES?",
        "options": [
            {
                "match": "fuel_ok",
                "label": "Yes — tank has fuel and petcock is on ON or RES",
                "deltas": {
                    "no_fuel": -0.10,
                    "clogged_carb": +0.10,
                    "fouled_spark_plug": +0.10,
                },
                "eliminate": [],
                "next_node": "recent_storage",
            },
            {
                "match": "petcock_off_or_empty",
                "label": "Petcock was on OFF, or tank is empty / very low",
                "deltas": {
                    "no_fuel": +0.55,
                },
                "eliminate": ["cdi_ignition", "intake_boot_crack", "flooded"],
                "next_node": None,
            },
            {
                "match": "vacuum_petcock",
                "label": "It has a vacuum petcock (no manual ON/OFF) — not sure if it's working",
                "deltas": {
                    "no_fuel": +0.25,
                },
                "eliminate": [],
                "next_node": "recent_storage",
            },
        ],
    },

    "recent_storage": {
        "question": "Has the bike been sitting for an extended period (weeks or months), or was it running fine recently?",
        "options": [
            {
                "match": "sat_long_time",
                "label": "Sat for weeks or months without being started",
                "deltas": {
                    "clogged_carb": +0.35,
                    "no_fuel": +0.10,
                    "fouled_spark_plug": +0.10,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
            {
                "match": "ran_recently",
                "label": "Was running fine until recently",
                "deltas": {
                    "cdi_ignition": +0.15,
                    "fouled_spark_plug": +0.15,
                    "choke_issue": +0.10,
                    "clogged_carb": -0.10,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
            {
                "match": "never_started",
                "label": "Never started since I got it / recent work done",
                "deltas": {
                    "clogged_carb": +0.15,
                    "no_fuel": +0.15,
                    "intake_boot_crack": +0.15,
                    "choke_issue": +0.10,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
        ],
    },

    "spark_check": {
        "question": "Have you checked for spark? (Remove plug, ground it against the engine, crank — you should see a strong blue spark.)",
        "options": [
            {
                "match": "good_spark",
                "label": "Yes — confirmed good strong blue spark",
                "deltas": {
                    "cdi_ignition": -0.30,
                    "fouled_spark_plug": -0.10,
                    "clogged_carb": +0.20,
                    "no_fuel": +0.10,
                    "choke_issue": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "weak_or_no_spark",
                "label": "Weak/orange spark or no spark at all",
                "deltas": {
                    "cdi_ignition": +0.30,
                    "fouled_spark_plug": +0.20,
                },
                "eliminate": ["clogged_carb", "no_fuel", "choke_issue", "intake_boot_crack"],
                "next_node": None,
            },
            {
                "match": "not_checked",
                "label": "Haven't checked spark",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"choke_issue": +0.10, "clogged_carb": +0.06},
        "hot": {"flooded": +0.08, "choke_issue": +0.06},
    },
    "mileage_band": {
        "high": {"cdi_ignition": +0.08, "intake_boot_crack": +0.06},
    },
    "storage_time": {
        "months": {"clogged_carb": +0.15, "no_fuel": +0.08},
        "season": {"clogged_carb": +0.18, "no_fuel": +0.10, "fouled_spark_plug": +0.06},
    },
    "first_start_of_season": {
        "yes": {"clogged_carb": +0.12, "fouled_spark_plug": +0.06},
    },
}

CRANK_NO_START_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After starting, let the bike idle 5 minutes and check for any new stumble or surging — may indicate secondary fuel delivery issues.",
    "If the carb was cleaned, replace the petcock fuel filter screen and inline filter at the same time.",
    "Check valve clearance if the bike has over 20,000 miles and clearance hasn't been checked recently.",
]
