"""
No-crank diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Chassis battery (engine start) vs. house battery bank are completely separate
  — house battery being dead does not prevent engine starting
- Battery isolator or solenoid separates the two banks; an isolator failure can
  drain the chassis battery or prevent charging
- Class A diesel pusher: rear-mounted engine, dual chassis batteries (like a diesel truck)
- Gas Class A and Class C: front-engine, typically single chassis battery
- LP (propane) fuel shutoff solenoid on some coaches — LP won't start if solenoid fails
- Chassis relay and battery boost switch allow house bank to assist chassis bank
"""

NO_CRANK_RV_HYPOTHESES: dict[str, dict] = {
    "chassis_battery_weak": {
        "label": "Weak or discharged chassis (engine start) battery",
        "prior": 0.32,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Chassis battery (group 31, 800+ CCA for diesel)", "notes": "Chassis battery is separate from house batteries — test chassis battery specifically; house batteries at full charge does not help engine starting"},
            {"name": "Battery terminal connectors", "notes": "Clean to bare metal; voltage drop at corroded terminals prevents cranking even with a good battery"},
        ],
    },
    "battery_isolator_fault": {
        "label": "Battery isolator or solenoid fault (chassis battery not charging while driving, or house bank dragging down chassis)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Battery isolator (diode-based or relay-based)", "notes": "Diode isolators fail silently — chassis battery stops receiving charge while driving; relay-type solenoids click audibly and can be tested with a multimeter"},
            {"name": "Battery disconnect relay", "notes": "Some coaches have a manual battery disconnect switch that can be inadvertently left off — check before further diagnosis"},
        ],
    },
    "failed_starter": {
        "label": "Failed starter motor or starter solenoid",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Starter motor (chassis-specific)", "notes": "RV chassis starters are Ford, GM, Workhorse, or Cummins/CAT depending on chassis — confirm part by chassis year/make; bench-test before ordering"},
        ],
    },
    "chassis_ground_cable": {
        "label": "Corroded chassis battery cable or engine ground strap",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Chassis battery cable (positive and/or negative)", "notes": "RV chassis battery cables run longer distances than in cars — inspect full run for rodent damage, chafing, and corrosion"},
            {"name": "Engine ground strap", "notes": "Rear-engine diesel pushers have a long ground run from the battery compartment to the engine; any corrosion in the run causes cranking problems"},
        ],
    },
    "glow_plug_system": {
        "label": "Glow plug system fault — diesel pusher only (engine won't crank successfully in cold weather)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Glow plugs (full set — Cummins ISL, CAT C7/C9, or similar)", "notes": "Diesel pusher glow plugs — access varies significantly by manufacturer; Cummins ISL has a wait-to-start indicator on the dash; test individually with a multimeter"},
        ],
    },
    "boost_switch_fault": {
        "label": "Chassis battery boost switch or emergency start relay fault (boost switch won't transfer power)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Battery boost relay / emergency start solenoid", "notes": "Most Class A coaches have a chassis boost switch that connects house and chassis batteries for emergency starts — a failed relay means this switch does nothing"},
        ],
    },
    "lp_shutoff_solenoid": {
        "label": "LP fuel shutoff solenoid stuck closed — gas-powered coaches only",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "LP fuel shutoff solenoid", "notes": "Some gas coaches use an LP (propane) fuel system with a safety shutoff solenoid — if the solenoid fails closed or is triggered by a CO/LP sensor, the engine cranks but won't start"},
        ],
    },
}

NO_CRANK_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key or press start, what happens?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — completely dead, no click, no noise",
                "deltas": {
                    "chassis_battery_weak": +0.25,
                    "chassis_ground_cable": +0.15,
                    "boost_switch_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
            {
                "match": "single_click",
                "label": "Single loud click — nothing else",
                "deltas": {
                    "failed_starter": +0.30,
                    "chassis_battery_weak": +0.20,
                    "chassis_ground_cable": +0.15,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
            {
                "match": "rapid_click",
                "label": "Rapid clicking — chatter or machine-gun click",
                "deltas": {
                    "chassis_battery_weak": +0.55,
                    "chassis_ground_cable": +0.15,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
            {
                "match": "slow_crank",
                "label": "Cranks very slowly — motor turns but sounds labored",
                "deltas": {
                    "chassis_battery_weak": +0.40,
                    "chassis_ground_cable": +0.15,
                    "glow_plug_system": +0.08,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
        ],
    },

    "battery_check": {
        "question": "What is the state of the chassis batteries (not house batteries)?",
        "options": [
            {
                "match": "recently_charged",
                "label": "Chassis battery was recently charged or is known-good",
                "deltas": {
                    "chassis_battery_weak": -0.20,
                    "failed_starter": +0.15,
                    "battery_isolator_fault": +0.10,
                    "chassis_ground_cable": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_type",
            },
            {
                "match": "sat_unplugged",
                "label": "RV sat without shore power or charging for weeks/months",
                "deltas": {
                    "chassis_battery_weak": +0.30,
                    "battery_isolator_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_type",
            },
            {
                "match": "unknown",
                "label": "Not sure of chassis battery state",
                "deltas": {
                    "chassis_battery_weak": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_type",
            },
        ],
    },

    "engine_type": {
        "question": "What engine does this RV have?",
        "options": [
            {
                "match": "diesel_pusher",
                "label": "Diesel pusher (Cummins, CAT, Mercedes BlueTec, or similar — engine in rear)",
                "deltas": {
                    "glow_plug_system": +0.08,
                    "lp_shutoff_solenoid": -0.10,
                    "chassis_battery_weak": +0.05,
                },
                "eliminate": ["lp_shutoff_solenoid"],
                "next_node": None,
            },
            {
                "match": "gas_front",
                "label": "Gas engine (Ford V10, Chevy 8.1, Workhorse — front engine)",
                "deltas": {
                    "glow_plug_system": -0.15,
                    "lp_shutoff_solenoid": +0.05,
                },
                "eliminate": ["glow_plug_system"],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "failed_starter": +0.10,
            "battery_isolator_fault": +0.08,
            "chassis_ground_cable": +0.06,
        },
    },
    "storage_time": {
        "long": {
            "chassis_battery_weak": +0.20,
            "battery_isolator_fault": +0.10,
        },
    },
    "climate": {
        "cold": {
            "chassis_battery_weak": +0.12,
            "glow_plug_system": +0.10,
        },
    },
}

NO_CRANK_RV_POST_DIAGNOSIS: list[str] = [
    "Always test the chassis battery specifically (not the house bank) — an RV with a fully charged house bank can still have a dead chassis battery; the two systems are isolated by design.",
    "If the battery isolator has failed (chassis not charging while driving), replace it with a relay-type solenoid isolator — diode-type isolators have a 0.7V voltage drop that causes undercharging on long trips; a quality relay isolator charges both banks to full voltage.",
    "After any extended storage, charge the chassis battery separately with a dedicated charger before relying on the built-in converter — the converter may not have enough output to recover a deeply discharged chassis battery in a reasonable time.",
]
