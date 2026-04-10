"""
No-crank diagnostic tree — truck/diesel variant.

Diesel trucks have unique no-crank causes: fuel gelling in cold weather,
high-compression engines that demand more from batteries and starters, and
no ignition coil (compression ignition). Cold temperatures expose glow plug
and battery weaknesses that are invisible in warm conditions.
"""

NO_CRANK_TRUCK_HYPOTHESES: dict[str, dict] = {
    "weak_battery_bank": {
        "label": "Weak or undercharged battery bank — diesels need 2× the cranking amps of gas engines",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel truck battery (group 31 or dual-battery setup, 800+ CCA)", "notes": "Most diesel trucks use two batteries in parallel. Test both — a bad cell in one pulls down the whole bank."},
            {"name": "Battery terminal connectors and cable", "notes": "Voltage drop at the terminal can prevent cranking even with good batteries; clean to bare metal"},
        ],
    },
    "diesel_fuel_gelling": {
        "label": "Diesel fuel gelled (cold weather) — wax crystals blocking fuel flow",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel anti-gel / fuel treatment (e.g., Power Service Diesel 911)", "notes": "Add to tank; bring truck indoors if possible to warm fuel. Prevents gelling when added before temps drop."},
            {"name": "Diesel fuel filter", "notes": "Gelled fuel can permanently clog the fuel filter — replace after a gelling event"},
        ],
    },
    "failed_starter": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter solenoid", "notes": "Single click = solenoid likely good, starter bad; no click = solenoid, wiring, or batteries"},
            {"name": "Starter motor (HD diesel-rated)", "notes": "Diesel starters are heavy-duty — bench-test with 12V before purchasing replacement"},
        ],
    },
    "glow_plug_system": {
        "label": "Glow plug system failure — engine won't build heat for compression ignition in cold weather",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test each plug with a multimeter (2–6 Ω resistance); a failed plug in one cylinder prevents cold starts"},
            {"name": "Glow plug controller / relay", "notes": "If all plugs test good but wait-to-start light doesn't illuminate, the controller may be faulty"},
        ],
    },
    "bad_ground_or_cable": {
        "label": "Corroded battery cable or engine ground strap — voltage drop preventing adequate cranking",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Battery cable set (heavy gauge)", "notes": "Measure voltage AT the starter while cranking — below 10V indicates excessive cable resistance"},
            {"name": "Engine-to-frame ground strap", "notes": "Diesel engines are hard to ground properly due to vibration isolation mounts — check all ground points"},
        ],
    },
    "seized_engine": {
        "label": "Seized engine (hydrolocked or mechanical failure)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil", "notes": "Check level immediately. A diesel that was run with coolant in the oil (milky) may hydrolocked — do NOT crank further."},
        ],
    },
    "anti_theft_immobilizer": {
        "label": "Anti-theft or immobilizer system preventing start",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Check for security/theft indicator light flashing. Try second key if available. A dead key fob battery can trigger immobilizer."},
        ],
    },
}

NO_CRANK_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key to start, what happens?",
        "options": [
            {
                "match": "nothing_at_all",
                "label": "Nothing at all — no click, no solenoid, no dash response",
                "deltas": {
                    "weak_battery_bank": +0.25,
                    "bad_ground_or_cable": +0.20,
                    "anti_theft_immobilizer": +0.15,
                    "failed_starter": -0.05,
                },
                "eliminate": ["seized_engine"],
                "next_node": "temperature",
            },
            {
                "match": "single_click",
                "label": "Single loud click but engine doesn't crank",
                "deltas": {
                    "failed_starter": +0.30,
                    "weak_battery_bank": +0.20,
                    "bad_ground_or_cable": +0.10,
                },
                "eliminate": ["anti_theft_immobilizer", "glow_plug_system", "diesel_fuel_gelling"],
                "next_node": "temperature",
            },
            {
                "match": "rapid_clicking",
                "label": "Rapid clicking (chatter) when key is held to start",
                "deltas": {
                    "weak_battery_bank": +0.50,
                    "bad_ground_or_cable": +0.20,
                    "failed_starter": -0.10,
                },
                "eliminate": ["anti_theft_immobilizer", "glow_plug_system", "diesel_fuel_gelling"],
                "next_node": "temperature",
            },
            {
                "match": "slow_crank",
                "label": "Engine turns over very slowly — labored, sluggish cranking",
                "deltas": {
                    "weak_battery_bank": +0.35,
                    "bad_ground_or_cable": +0.20,
                    "diesel_fuel_gelling": +0.10,
                    "glow_plug_system": +0.05,
                },
                "eliminate": ["anti_theft_immobilizer"],
                "next_node": "temperature",
            },
        ],
    },

    "temperature": {
        "question": "What is the outside temperature, and has this truck been sitting in the cold?",
        "options": [
            {
                "match": "very_cold",
                "label": "Very cold — below 20°F (-7°C), especially overnight",
                "deltas": {
                    "diesel_fuel_gelling": +0.30,
                    "weak_battery_bank": +0.15,
                    "glow_plug_system": +0.15,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "moderate_cold",
                "label": "Cold but not extreme — 20°F to 40°F (-7°C to 4°C)",
                "deltas": {
                    "weak_battery_bank": +0.10,
                    "glow_plug_system": +0.10,
                    "diesel_fuel_gelling": +0.05,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "warm",
                "label": "Warm or mild — above 40°F (4°C)",
                "deltas": {
                    "diesel_fuel_gelling": -0.15,
                    "glow_plug_system": -0.10,
                    "weak_battery_bank": +0.05,
                    "failed_starter": +0.05,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old are the truck's batteries and when were they last tested?",
        "options": [
            {
                "match": "old_batteries",
                "label": "3+ years old or have never been tested",
                "deltas": {
                    "weak_battery_bank": +0.25,
                },
                "eliminate": [],
                "next_node": "glow_plug_light",
            },
            {
                "match": "new_batteries",
                "label": "New or recently tested — good health",
                "deltas": {
                    "weak_battery_bank": -0.20,
                    "failed_starter": +0.10,
                    "bad_ground_or_cable": +0.10,
                    "diesel_fuel_gelling": +0.05,
                },
                "eliminate": [],
                "next_node": "glow_plug_light",
            },
            {
                "match": "unknown_batteries",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "glow_plug_light",
            },
        ],
    },

    "glow_plug_light": {
        "question": "When you turn the key to ON (not start), does the wait-to-start / glow plug indicator light come on and then go out before you crank?",
        "options": [
            {
                "match": "light_works",
                "label": "Yes — light comes on then goes out normally",
                "deltas": {
                    "glow_plug_system": -0.15,
                    "anti_theft_immobilizer": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "light_missing",
                "label": "No — light never came on or stays on permanently",
                "deltas": {
                    "glow_plug_system": +0.20,
                    "anti_theft_immobilizer": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "light_unknown",
                "label": "Not sure / didn't notice",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"weak_battery_bank": +0.10, "diesel_fuel_gelling": +0.15, "glow_plug_system": +0.10},
        "hot": {"weak_battery_bank": +0.05},
    },
    "mileage_band": {
        "high": {"failed_starter": +0.08, "bad_ground_or_cable": +0.06},
        "low": {"anti_theft_immobilizer": +0.04},
    },
    "usage_pattern": {
        "city": {"weak_battery_bank": +0.05},
    },
}

NO_CRANK_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, load-test the entire battery bank — diesel trucks often have dual batteries, and one weak cell can cause intermittent no-crank.",
    "Inspect glow plug connector harness for heat damage if glow plugs were involved in the diagnosis.",
]
