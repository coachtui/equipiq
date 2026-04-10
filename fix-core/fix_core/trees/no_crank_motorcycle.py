"""
No-crank diagnostic tree — motorcycle variant.

Motorcycle-specific causes: kickstand/neutral/clutch safety switches are
first-class suspects that don't exist on cars. Blown fuse from accessory
installs is also more common on motorcycles.
"""

NO_CRANK_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "dead_battery": {
        "label": "Dead or discharged battery",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Motorcycle battery (AGM or lithium)", "notes": "Check voltage: below 12.4V at rest = weak; below 11.8V = likely dead"},
            {"name": "Battery tender / trickle charger", "notes": "Ideal for bikes that sit; prevents sulphation"},
        ],
    },
    "safety_switch": {
        "label": "Safety switch preventing start (kickstand, neutral, or clutch switch)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Kickstand switch", "notes": "Most common culprit — bike must be in neutral or clutch pulled with stand up"},
            {"name": "Neutral switch", "notes": "Faulty switch can prevent start even in neutral; check neutral light"},
            {"name": "Clutch interlock switch", "notes": "Located on clutch lever perch; check for continuity"},
        ],
    },
    "blown_fuse": {
        "label": "Blown main fuse or starter circuit fuse",
        "prior": 0.15,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuse kit (assorted automotive blade fuses)", "notes": "Check main fuse (typically 30A) and starter/ignition fuse (10–15A)"},
        ],
    },
    "bad_starter_motor": {
        "label": "Failed starter motor or starter relay",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter relay (solenoid)", "notes": "Click with no crank = relay may be passing but starter is bad; no click = relay or wiring"},
            {"name": "Starter motor", "notes": "Bench test with direct 12V before replacing"},
        ],
    },
    "kill_switch": {
        "label": "Kill switch in OFF position or faulty",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Handlebar switch assembly", "notes": "Toggle kill switch off and back on; corrosion can cause intermittent open circuit"},
        ],
    },
    "bad_ground": {
        "label": "Loose or corroded battery ground or chassis ground strap",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Battery terminal connectors", "notes": "Clean terminals and ground strap bolt contact points with wire brush"},
        ],
    },
    "seized_engine": {
        "label": "Seized engine (hydrolocked or mechanical failure)",
        "prior": 0.03,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil", "notes": "Check level immediately; try rocking bike in gear to feel for seized rotation"},
        ],
    },
}

NO_CRANK_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "When you press the starter button, what happens?",
        "options": [
            {
                "match": "nothing_at_all",
                "label": "Absolutely nothing — no click, no sound, no dash lights",
                "deltas": {
                    "dead_battery": +0.30,
                    "blown_fuse": +0.20,
                    "bad_ground": +0.15,
                    "kill_switch": +0.10,
                    "bad_starter_motor": -0.05,
                    "safety_switch": -0.05,
                },
                "eliminate": ["seized_engine"],
                "next_node": "dash_lights",
            },
            {
                "match": "single_click",
                "label": "Single loud click but no crank",
                "deltas": {
                    "bad_starter_motor": +0.30,
                    "dead_battery": +0.20,
                    "bad_ground": +0.10,
                    "blown_fuse": -0.10,
                },
                "eliminate": ["kill_switch", "safety_switch"],
                "next_node": "battery_age",
            },
            {
                "match": "rapid_clicking",
                "label": "Rapid clicking (chatter)",
                "deltas": {
                    "dead_battery": +0.50,
                    "bad_ground": +0.15,
                    "bad_starter_motor": -0.10,
                },
                "eliminate": ["kill_switch", "blown_fuse", "safety_switch"],
                "next_node": "battery_age",
            },
            {
                "match": "starter_spins_no_crank",
                "label": "Starter whirs/spins but engine doesn't turn over",
                "deltas": {
                    "bad_starter_motor": +0.40,
                    "seized_engine": +0.20,
                },
                "eliminate": ["dead_battery", "blown_fuse", "kill_switch", "safety_switch"],
                "next_node": None,
            },
        ],
    },

    "dash_lights": {
        "question": "Do the dashboard/instrument lights come on when you turn the key to ON?",
        "options": [
            {
                "match": "no_lights",
                "label": "No dash lights at all",
                "deltas": {
                    "dead_battery": +0.20,
                    "blown_fuse": +0.20,
                    "bad_ground": +0.10,
                    "kill_switch": +0.10,
                },
                "eliminate": [],
                "next_node": "safety_switches",
            },
            {
                "match": "lights_on",
                "label": "Dash lights come on normally",
                "deltas": {
                    "safety_switch": +0.25,
                    "blown_fuse": +0.15,
                    "dead_battery": -0.10,
                    "kill_switch": +0.15,
                },
                "eliminate": ["bad_ground"],
                "next_node": "safety_switches",
            },
        ],
    },

    "safety_switches": {
        "question": "Before pressing start, is the kickstand fully up, the transmission in neutral (or clutch pulled), and the kill switch in RUN?",
        "options": [
            {
                "match": "all_correct",
                "label": "Yes — kickstand up, in neutral or clutch in, kill switch on RUN",
                "deltas": {
                    "safety_switch": -0.15,
                    "dead_battery": +0.10,
                    "blown_fuse": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "not_sure",
                "label": "Not sure — haven't checked all of them",
                "deltas": {
                    "safety_switch": +0.30,
                    "kill_switch": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "checked_still_no_start",
                "label": "Checked and corrected, still won't crank",
                "deltas": {
                    "safety_switch": +0.10,
                    "dead_battery": +0.15,
                    "blown_fuse": +0.10,
                    "bad_starter_motor": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery and when did you last ride?",
        "options": [
            {
                "match": "old_battery_or_sat",
                "label": "Battery is 3+ years old, or bike sat for weeks/months without charging",
                "deltas": {
                    "dead_battery": +0.30,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "new_battery",
                "label": "Battery is new or recently charged",
                "deltas": {
                    "dead_battery": -0.15,
                    "safety_switch": +0.10,
                    "blown_fuse": +0.10,
                    "bad_starter_motor": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_battery",
                "label": "Not sure about battery age / ridden recently",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"dead_battery": +0.10, "safety_switch": +0.04},
    },
    "mileage_band": {
        "high": {"bad_starter_motor": +0.08, "bad_ground": +0.06},
    },
    "storage_time": {
        "months": {"dead_battery": +0.12, "bad_ground": +0.06},
        "season": {"dead_battery": +0.15, "bad_ground": +0.08},
    },
    "first_start_of_season": {
        "yes": {"dead_battery": +0.12, "bad_ground": +0.06},
    },
}

NO_CRANK_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, check kill switch wiring for intermittent contacts — cheap to fix while everything is apart.",
    "Verify the safety switches (kickstand, neutral/clutch) function properly with a multimeter after repair.",
]
