"""
Loss of power / output diagnostic tree — generator variant.

Generator "loss of power" means: engine bogs under load, won't maintain
rated wattage, output voltage drops, or runs but can't handle connected load.
"""

LOSS_OF_POWER_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "load_overload": {
        "label": "Generator overloaded — connected load exceeds rated wattage",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Calculate total wattage of all connected devices. Check surge wattage (motors need 2–3x running watts to start). Disconnect loads and reconnect one at a time."},
        ],
    },
    "air_filter_clogged": {
        "label": "Clogged air filter restricting airflow and reducing power",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter element (foam or paper per model)", "notes": "Clean foam filters with dish soap and water; dry completely before reinstalling. Replace paper filters."},
        ],
    },
    "fuel_restriction": {
        "label": "Fuel restriction — clogged fuel filter, varnished carb main jet, or kinked fuel line",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "In-line fuel filter", "notes": "Inexpensive and easy to replace; check for debris or discoloration"},
            {"name": "Carburetor main jet", "notes": "Partially clogged main jet causes power drop under load; clean or replace"},
        ],
    },
    "spark_plug_worn": {
        "label": "Worn or fouled spark plug — reduced combustion efficiency",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (per generator manual)", "notes": "Replace at manufacturer interval (typically every 100 hours). Check gap."},
        ],
    },
    "governor_fault": {
        "label": "Governor not responding — engine surges or won't maintain RPM under load",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Governor spring", "notes": "A weak or stretched governor spring causes RPM to drop under load; check linkage for binding or wear"},
            {"name": "Governor arm assembly", "notes": "Check for loose or worn pivot points on governor linkage"},
        ],
    },
    "stale_fuel": {
        "label": "Degraded fuel — phase separation or water contamination reducing energy content",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh gasoline", "notes": "Ethanol-blend fuel can separate and absorb water; use non-ethanol fuel in generators when possible"},
            {"name": "Fuel treatment / stabilizer", "notes": "Add to fresh fuel for storage"},
        ],
    },
    "valve_clearance": {
        "label": "Excessive valve clearance (high-hour engines) reducing compression and power",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Feeler gauge set", "notes": "Check and adjust intake and exhaust valve clearance per service manual (typically every 300 hours)"},
        ],
    },
}

LOSS_OF_POWER_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "What happens when you connect your load?",
        "options": [
            {
                "match": "bogs_then_recovers",
                "label": "Engine bogs briefly under load then recovers",
                "deltas": {
                    "governor_fault": +0.25,
                    "air_filter_clogged": +0.10,
                    "fuel_restriction": +0.10,
                    "load_overload": -0.05,
                },
                "eliminate": [],
                "next_node": "load_check",
            },
            {
                "match": "bogs_stays_bogged",
                "label": "Engine bogs and stays slow / almost stalls",
                "deltas": {
                    "load_overload": +0.20,
                    "fuel_restriction": +0.15,
                    "air_filter_clogged": +0.10,
                    "spark_plug_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "load_check",
            },
            {
                "match": "no_output_power",
                "label": "Engine runs fine but no or low electrical output",
                "deltas": {
                    "governor_fault": -0.05,
                    "load_overload": -0.10,
                    "spark_plug_worn": -0.05,
                },
                "eliminate": [],
                "next_node": "load_check",
            },
        ],
    },

    "load_check": {
        "question": "What is the approximate total wattage of everything you have connected?",
        "options": [
            {
                "match": "load_near_or_over_rated",
                "label": "At or near the generator's rated wattage (or I'm not sure)",
                "deltas": {
                    "load_overload": +0.30,
                },
                "eliminate": [],
                "next_node": "air_filter_check",
            },
            {
                "match": "load_well_below",
                "label": "Well below rated wattage — should have plenty of headroom",
                "deltas": {
                    "load_overload": -0.20,
                    "air_filter_clogged": +0.10,
                    "fuel_restriction": +0.10,
                    "governor_fault": +0.10,
                    "spark_plug_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "air_filter_check",
            },
        ],
    },

    "air_filter_check": {
        "question": "When did you last inspect or clean the air filter?",
        "options": [
            {
                "match": "filter_dirty_or_unknown",
                "label": "Never checked, or it's visibly dirty / clogged",
                "deltas": {
                    "air_filter_clogged": +0.30,
                },
                "eliminate": [],
                "next_node": "runtime_hours",
            },
            {
                "match": "filter_clean_recent",
                "label": "Clean and recently inspected",
                "deltas": {
                    "air_filter_clogged": -0.15,
                    "fuel_restriction": +0.10,
                    "governor_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "runtime_hours",
            },
        ],
    },

    "runtime_hours": {
        "question": "Roughly how many hours of use does this generator have?",
        "options": [
            {
                "match": "high_hours",
                "label": "High use — likely over 200 hours",
                "deltas": {
                    "spark_plug_worn": +0.20,
                    "valve_clearance": +0.15,
                    "governor_fault": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low_hours",
                "label": "Low use — under 100 hours",
                "deltas": {
                    "stale_fuel": +0.10,
                    "fuel_restriction": +0.05,
                    "valve_clearance": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_hours",
                "label": "Not sure / unknown history",
                "deltas": {
                    "stale_fuel": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"stale_fuel": +0.06, "governor_fault": +0.04},
        "hot": {"air_filter_clogged": +0.06},
    },
    "storage_time": {
        "months": {"stale_fuel": +0.12, "fuel_restriction": +0.08},
        "season": {"stale_fuel": +0.15, "fuel_restriction": +0.10, "air_filter_clogged": +0.06},
    },
    "first_start_of_season": {
        "yes": {"stale_fuel": +0.10, "air_filter_clogged": +0.06, "spark_plug_worn": +0.06},
    },
    "mileage_band": {
        "high": {"valve_clearance": +0.08, "governor_fault": +0.06},
    },
}

LOSS_OF_POWER_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After repair, test under full load for 30 minutes — intermittent power loss under sustained load points to fuel starvation or governor issues.",
    "Check output voltage with a multimeter under load — should stay within ±5% of rated voltage.",
]
