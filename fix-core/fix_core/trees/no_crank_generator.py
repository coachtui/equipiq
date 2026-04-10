"""
No-crank diagnostic tree — generator variant.

Generators often sit unused for months, making stale fuel and low-oil
auto-shutoff the dominant failure modes. This tree also handles both
electric-start and pull-start (recoil) generators.
"""

NO_CRANK_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "low_oil_shutoff": {
        "label": "Low oil auto-shutoff activated — engine locked out by low-oil sensor",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Engine oil (correct grade for generator)", "notes": "Check dipstick BEFORE anything else. Most generators won't crank at all when oil level is below the sensor threshold."},
        ],
    },
    "dead_battery": {
        "label": "Dead battery (electric-start generators only)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Generator battery (small AGM, typically 12V 7–18Ah)", "notes": "Generator batteries discharge quickly in storage; trickle-charge or replace if 3+ years old"},
            {"name": "Battery tender / trickle charger", "notes": "Keep battery maintained between uses"},
        ],
    },
    "stale_fuel_gummed": {
        "label": "Stale or varnished fuel preventing engine from being primed / fuel from reaching cylinder",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh gasoline (non-ethanol preferred)", "notes": "Drain old fuel completely; ethanol-blend fuel degrades in as little as 30 days in a generator tank"},
            {"name": "Fuel stabilizer", "notes": "Add to tank before storage — eliminates gumming for 12–24 months"},
        ],
    },
    "recoil_cord_fault": {
        "label": "Broken or jammed recoil pull-cord (pull-start generators only)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Recoil starter assembly", "notes": "Often cheaper to replace the whole recoil assembly than repair the spring/cord individually"},
        ],
    },
    "failed_starter_motor": {
        "label": "Failed starter motor or solenoid (electric-start generators)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter solenoid", "notes": "A single click with no crank = solenoid likely passing, starter may be bad; no click = solenoid or wiring"},
            {"name": "Starter motor", "notes": "Bench-test with direct 12V before purchasing replacement"},
        ],
    },
    "choke_position": {
        "label": "Choke in wrong position preventing fuel delivery",
        "prior": 0.07,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Set choke to FULL CLOSED (choke on) for cold starts; move to open/run after engine fires. Consult the generator's manual."},
        ],
    },
    "seized_engine": {
        "label": "Seized engine from running without oil or prolonged storage",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil", "notes": "Remove spark plug, pour a small amount of oil into the cylinder, let soak 1 hour, try pulling cord gently to check for rotation"},
        ],
    },
}

NO_CRANK_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "First check: is the engine oil level correct? (Check dipstick or sight glass — most generators will not crank at all when oil is low.)",
        "options": [
            {
                "match": "oil_low",
                "label": "Oil is low or I haven't checked yet",
                "deltas": {
                    "low_oil_shutoff": +0.40,
                },
                "eliminate": [],
                "next_node": "start_type",
            },
            {
                "match": "oil_ok",
                "label": "Oil level is correct",
                "deltas": {
                    "low_oil_shutoff": -0.20,
                    "dead_battery": +0.10,
                    "stale_fuel_gummed": +0.10,
                    "recoil_cord_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "start_type",
            },
        ],
    },

    "start_type": {
        "question": "Does this generator have electric start (key/button) or pull-start (recoil cord) only?",
        "options": [
            {
                "match": "electric_start",
                "label": "Electric start (key or push button)",
                "deltas": {
                    "dead_battery": +0.15,
                    "failed_starter_motor": +0.05,
                    "recoil_cord_fault": -0.10,
                },
                "eliminate": [],
                "next_node": "storage_duration",
            },
            {
                "match": "pull_start_only",
                "label": "Pull-start / recoil cord only",
                "deltas": {
                    "recoil_cord_fault": +0.20,
                    "dead_battery": -0.20,
                    "failed_starter_motor": -0.10,
                },
                "eliminate": ["dead_battery", "failed_starter_motor"],
                "next_node": "storage_duration",
            },
            {
                "match": "both",
                "label": "Both electric start and pull cord",
                "deltas": {},
                "eliminate": [],
                "next_node": "storage_duration",
            },
        ],
    },

    "storage_duration": {
        "question": "How long has the generator been sitting unused?",
        "options": [
            {
                "match": "over_30_days",
                "label": "More than 30 days (or fuel was left in tank over winter)",
                "deltas": {
                    "stale_fuel_gummed": +0.30,
                    "dead_battery": +0.10,
                    "seized_engine": +0.05,
                },
                "eliminate": [],
                "next_node": "cord_condition",
            },
            {
                "match": "used_recently",
                "label": "Used within the last 30 days",
                "deltas": {
                    "stale_fuel_gummed": -0.15,
                    "dead_battery": +0.10,
                    "recoil_cord_fault": +0.05,
                    "failed_starter_motor": +0.05,
                },
                "eliminate": [],
                "next_node": "cord_condition",
            },
            {
                "match": "unknown_storage",
                "label": "Not sure — unknown history",
                "deltas": {
                    "stale_fuel_gummed": +0.10,
                },
                "eliminate": [],
                "next_node": "cord_condition",
            },
        ],
    },

    "cord_condition": {
        "question": "If it's a pull-start: when you pull the cord, does the engine turn over smoothly, or does the cord not retract / feel stuck?",
        "options": [
            {
                "match": "cord_stuck_or_broken",
                "label": "Cord won't pull, is broken, or doesn't retract",
                "deltas": {
                    "recoil_cord_fault": +0.45,
                    "seized_engine": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cord_ok_engine_turns",
                "label": "Cord pulls fine / engine rotates, but won't start",
                "deltas": {
                    "recoil_cord_fault": -0.20,
                    "stale_fuel_gummed": +0.10,
                    "choke_position": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "electric_start_no_click",
                "label": "Electric start only — pressing button produces nothing at all",
                "deltas": {
                    "dead_battery": +0.30,
                    "failed_starter_motor": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "electric_start_click",
                "label": "Electric start — click but no crank",
                "deltas": {
                    "failed_starter_motor": +0.30,
                    "dead_battery": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"dead_battery": +0.08, "choke_position": +0.06, "stale_fuel_gummed": +0.05},
    },
    "storage_time": {
        "months": {"stale_fuel_gummed": +0.15, "dead_battery": +0.10, "choke_position": +0.06},
        "season": {"stale_fuel_gummed": +0.20, "dead_battery": +0.12, "choke_position": +0.08},
    },
    "first_start_of_season": {
        "yes": {"stale_fuel_gummed": +0.15, "dead_battery": +0.10, "choke_position": +0.08},
    },
}

NO_CRANK_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, drain and replace the engine oil if the generator sat for a season — old oil acidifies during storage.",
    "Check the spark plug and replace it as a first-season maintenance item even if it wasn't the root cause.",
]
