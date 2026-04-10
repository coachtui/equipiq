"""
Strange noise diagnostic tree — generator variant.

Generator noises include: bearing whine, loose panel rattle, rod knock from
low oil, backfire, and alternator bearing noise. Also covers no electrical
output with engine running (capacitor / AVR / brushless alternator faults).
"""

STRANGE_NOISE_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "low_oil_knock": {
        "label": "Engine rod knock or bearing knock from low oil — serious damage risk",
        "prior": 0.22,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil", "notes": "Check level immediately. A deep rhythmic knock that worsens under load is a classic rod bearing knock — stop use immediately to prevent catastrophic failure."},
        ],
    },
    "loose_panel_vibration": {
        "label": "Loose housing panel, frame bolt, or accessory vibrating at resonance",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fastener kit (assorted metric bolts and washers)", "notes": "Press on each panel while running to isolate the vibrating surface; tighten or add rubber isolation grommets"},
        ],
    },
    "exhaust_leak": {
        "label": "Exhaust manifold or muffler leak — loud ticking or hissing from exhaust port",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Exhaust gasket (per generator model)", "notes": "A cracked muffler or loose exhaust bolts are very common; heat causes bolts to back out over time"},
            {"name": "Exhaust flange bolts", "notes": "Re-torque or replace if corroded"},
        ],
    },
    "alternator_bearing": {
        "label": "Worn alternator bearing — high-pitched whine or squeal from generator end",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Alternator bearing (end frame bearing)", "notes": "Whine that scales with RPM and doesn't change with engine load points to a bearing rather than combustion noise"},
        ],
    },
    "carbon_brush_worn": {
        "label": "Worn carbon brushes on brushed alternator — electrical arcing noise or no output",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Carbon brush set (per generator model)", "notes": "Brushes are a normal wear item; check length and spring tension. Short brushes cause sparking."},
        ],
    },
    "backfire_ignition": {
        "label": "Backfire through intake or exhaust — ignition timing or stale fuel issue",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug", "notes": "Worn plug can cause late ignition and backfire. Check gap and replace if needed."},
            {"name": "Fresh fuel", "notes": "Stale fuel burns unpredictably and can cause backfiring through the carb"},
        ],
    },
    "valve_train_tick": {
        "label": "Valve train ticking — excessive clearance or worn rocker arm (high-hour engines)",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Feeler gauge set", "notes": "Adjust valve clearance per service manual spec; a rhythmic tick at half engine speed is typically valves"},
        ],
    },
}

STRANGE_NOISE_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise?",
        "options": [
            {
                "match": "deep_knock_clunk",
                "label": "Deep knock, clunk, or thud — especially under load",
                "deltas": {
                    "low_oil_knock": +0.40,
                    "exhaust_leak": +0.05,
                    "valve_train_tick": -0.05,
                },
                "eliminate": ["alternator_bearing", "carbon_brush_worn"],
                "next_node": "oil_check",
            },
            {
                "match": "rattle_vibration",
                "label": "Rattling, buzzing, or panel vibration",
                "deltas": {
                    "loose_panel_vibration": +0.45,
                    "exhaust_leak": +0.10,
                    "low_oil_knock": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "whine_squeal",
                "label": "High-pitched whine or squeal, louder at higher RPM",
                "deltas": {
                    "alternator_bearing": +0.40,
                    "carbon_brush_worn": +0.15,
                    "low_oil_knock": -0.10,
                },
                "eliminate": ["loose_panel_vibration"],
                "next_node": "oil_check",
            },
            {
                "match": "tick_tap",
                "label": "Rhythmic ticking or tapping",
                "deltas": {
                    "valve_train_tick": +0.30,
                    "exhaust_leak": +0.25,
                    "low_oil_knock": +0.10,
                },
                "eliminate": ["alternator_bearing", "carbon_brush_worn"],
                "next_node": "oil_check",
            },
            {
                "match": "backfire_pop",
                "label": "Loud bang, pop, or backfire",
                "deltas": {
                    "backfire_ignition": +0.50,
                    "stale_fuel": +0.15,
                },
                "eliminate": ["alternator_bearing", "low_oil_knock", "valve_train_tick"],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "What is the engine oil level?",
        "options": [
            {
                "match": "oil_low",
                "label": "Low — below the minimum mark",
                "deltas": {
                    "low_oil_knock": +0.30,
                    "valve_train_tick": +0.10,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
            {
                "match": "oil_ok",
                "label": "Oil level is correct",
                "deltas": {
                    "low_oil_knock": -0.15,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
        ],
    },

    "noise_location": {
        "question": "Where does the noise seem to come from?",
        "options": [
            {
                "match": "engine_side",
                "label": "Engine side (cylinder / crankcase area)",
                "deltas": {
                    "low_oil_knock": +0.10,
                    "valve_train_tick": +0.10,
                    "exhaust_leak": +0.05,
                    "alternator_bearing": -0.10,
                },
                "eliminate": [],
                "next_node": "hours_check",
            },
            {
                "match": "generator_end",
                "label": "Generator / alternator end",
                "deltas": {
                    "alternator_bearing": +0.20,
                    "carbon_brush_worn": +0.15,
                    "low_oil_knock": -0.10,
                    "valve_train_tick": -0.10,
                },
                "eliminate": [],
                "next_node": "hours_check",
            },
            {
                "match": "panel_frame",
                "label": "Housing panels or frame",
                "deltas": {
                    "loose_panel_vibration": +0.30,
                    "exhaust_leak": +0.10,
                },
                "eliminate": [],
                "next_node": "hours_check",
            },
            {
                "match": "exhaust",
                "label": "Exhaust pipe or muffler area",
                "deltas": {
                    "exhaust_leak": +0.40,
                    "backfire_ignition": +0.10,
                },
                "eliminate": ["alternator_bearing", "low_oil_knock"],
                "next_node": "hours_check",
            },
        ],
    },

    "hours_check": {
        "question": "Roughly how many hours of use does this generator have?",
        "options": [
            {
                "match": "high_hours",
                "label": "High use — likely 300+ hours",
                "deltas": {
                    "valve_train_tick": +0.15,
                    "alternator_bearing": +0.10,
                    "carbon_brush_worn": +0.10,
                    "low_oil_knock": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low_hours",
                "label": "Low use — under 100 hours",
                "deltas": {
                    "loose_panel_vibration": +0.05,
                    "exhaust_leak": +0.05,
                    "valve_train_tick": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_hours",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"low_oil_knock": +0.06},
    },
    "mileage_band": {
        "high": {"low_oil_knock": +0.08, "alternator_bearing": +0.06, "valve_train_tick": +0.06},
    },
    "storage_time": {
        "months": {"backfire_ignition": +0.06, "loose_panel_vibration": +0.04},
        "season": {"backfire_ignition": +0.08, "carbon_brush_worn": +0.06},
    },
    "first_start_of_season": {
        "yes": {"backfire_ignition": +0.08, "low_oil_knock": +0.06, "valve_train_tick": +0.05},
    },
}

STRANGE_NOISE_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After identifying and fixing the noise source, check the oil level and condition — many noise causes accelerate oil contamination.",
    "Tighten all accessible panel bolts and screws — generator vibration loosens fasteners over time.",
]
