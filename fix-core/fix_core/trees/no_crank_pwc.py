"""
No-crank diagnostic tree — PWC (personal watercraft / jet ski) variant.

The DESS (Digitally Encoded Security System) lanyard on Sea-Doos is the
single most-missed cause — without the correct DESS key on the post,
the engine is completely immobilized. Yamaha and Kawasaki use a simpler
mechanical lanyard. Water intrusion into the starter circuit is also
unique to PWCs.
"""

NO_CRANK_PWC_HYPOTHESES: dict[str, dict] = {
    "lanyard_missing": {
        "label": "Safety lanyard not attached or wrong DESS key (Sea-Doo) — engine immobilized",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "DESS lanyard (Sea-Doo only — must be programmed to the ECM)", "notes": "Sea-Doo: the magnetic lanyard must be seated on the post. A generic lanyard will NOT work — the key must be programmed. Yamaha/Kawasaki use a simple clip lanyard."},
        ],
    },
    "dead_battery": {
        "label": "Dead or deeply discharged battery — PWCs sit unused for months",
        "prior": 0.26,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "AGM or gel marine battery (sealed, no-spill)", "notes": "PWCs require sealed batteries only — standard flooded batteries can spill in the hull. Match the CCA specification."},
            {"name": "Battery maintainer / tender", "notes": "Essential during off-season storage — PWCs drain batteries quickly when sitting"},
        ],
    },
    "blown_fuse": {
        "label": "Blown fuse or relay in the starter circuit",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "PWC fuse kit (blade fuses, check OEM spec)", "notes": "Check the main fuse box — often located under the front hood or under the seat"},
        ],
    },
    "waterlogged_bilge": {
        "label": "Engine bay flooded — water in the bilge shorting electrical components",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "(No parts needed initially)", "notes": "Open the rear storage, check for standing water in the hull. Run the bilge pump. Allow to dry before attempting to start. Do not crank with water above the flywheel."},
        ],
    },
    "bad_connections": {
        "label": "Corroded or loose battery terminals — saltwater environment accelerates corrosion",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine battery terminals (tinned copper)", "notes": "PWC battery terminals corrode rapidly in saltwater environments. Clean or replace and coat with corrosion protector."},
        ],
    },
    "failed_starter": {
        "label": "Failed starter motor or starter relay",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter relay", "notes": "Click but no crank = check relay and solenoid before replacing starter motor"},
            {"name": "Starter motor", "notes": "Use a sealed marine-rated starter — open automotive starters corrode rapidly in the hull environment"},
        ],
    },
}

NO_CRANK_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "Is the safety lanyard clipped to the post and — if it's a Sea-Doo — is it the correct programmed DESS key?",
        "options": [
            {
                "match": "lanyard_off",
                "label": "Lanyard is not attached / DESS key not on post",
                "deltas": {
                    "lanyard_missing": +0.75,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
            {
                "match": "seadoo_wrong_key",
                "label": "Sea-Doo with a generic or unknown lanyard attached",
                "deltas": {
                    "lanyard_missing": +0.65,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
            {
                "match": "lanyard_ok",
                "label": "Correct lanyard is attached / DESS key confirmed",
                "deltas": {
                    "lanyard_missing": -0.25,
                    "dead_battery": +0.15,
                    "blown_fuse": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
        ],
    },

    "battery_check": {
        "question": "When you press START, what do you hear — silence, clicking, or something else?",
        "options": [
            {
                "match": "silence_dead",
                "label": "Complete silence — no click, no beep, dash may be dim or off",
                "deltas": {
                    "dead_battery": +0.30,
                    "bad_connections": +0.20,
                    "blown_fuse": +0.15,
                },
                "eliminate": ["failed_starter"],
                "next_node": "bilge_check",
            },
            {
                "match": "rapid_click",
                "label": "Rapid clicking",
                "deltas": {
                    "dead_battery": +0.55,
                    "bad_connections": +0.20,
                },
                "eliminate": ["blown_fuse", "failed_starter"],
                "next_node": "bilge_check",
            },
            {
                "match": "single_click",
                "label": "Single click but engine doesn't crank",
                "deltas": {
                    "failed_starter": +0.30,
                    "dead_battery": +0.20,
                    "bad_connections": +0.15,
                },
                "eliminate": ["blown_fuse"],
                "next_node": "bilge_check",
            },
        ],
    },

    "bilge_check": {
        "question": "Is there water in the hull / engine bay?",
        "options": [
            {
                "match": "hull_flooded",
                "label": "Yes — standing water visible in the hull",
                "deltas": {
                    "waterlogged_bilge": +0.70,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "hull_dry",
                "label": "Hull is dry",
                "deltas": {
                    "waterlogged_bilge": -0.10,
                    "dead_battery": +0.10,
                    "blown_fuse": +0.08,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
        ],
    },

    "storage_check": {
        "question": "How long was the PWC in storage, and was the battery removed or on a maintainer?",
        "options": [
            {
                "match": "sat_no_maintainer",
                "label": "Sat for months without a battery maintainer",
                "deltas": {
                    "dead_battery": +0.45,
                    "bad_connections": +0.10,
                },
                "eliminate": ["failed_starter"],
                "next_node": None,
            },
            {
                "match": "battery_maintained",
                "label": "Battery was on a maintainer or recently charged",
                "deltas": {
                    "dead_battery": -0.15,
                    "blown_fuse": +0.15,
                    "failed_starter": +0.15,
                    "bad_connections": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"bad_connections": +0.15, "blown_fuse": +0.08, "failed_starter": +0.06},
    },
    "storage_time": {
        "months": {"dead_battery": +0.15, "bad_connections": +0.08},
        "season": {"dead_battery": +0.18, "bad_connections": +0.10, "blown_fuse": +0.05},
    },
    "first_start_of_season": {
        "yes": {"dead_battery": +0.15, "bad_connections": +0.08, "lanyard_missing": +0.06},
    },
    "climate": {
        "cold": {"dead_battery": +0.10, "bad_connections": +0.06},
    },
}

NO_CRANK_PWC_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, coat all electrical connectors under the hood with dielectric grease — PWC connectors corrode rapidly from splash and humidity.",
    "Keep a spare DESS lanyard (Sea-Doo) or safety lanyard on the PWC — losing the only lanyard strands you on the water.",
]
