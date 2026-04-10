"""
No-crank diagnostic tree — boat / marine variant.

The most commonly missed cause: safety lanyard (kill switch clip) not
attached to the helm. Many boats also have neutral safety switches and
remote fuel shutoffs. Saltwater accelerates battery terminal corrosion.
"""

NO_CRANK_BOAT_HYPOTHESES: dict[str, dict] = {
    "kill_switch_lanyard": {
        "label": "Kill switch lanyard not attached or safety interlock not engaged",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Kill switch lanyard (replacement)", "notes": "The red or black coiled cord with the clip — must be attached to the helm kill switch post and to your wrist/life jacket. If missing, engine will not crank on most boats."},
        ],
    },
    "dead_battery": {
        "label": "Dead or sulfated marine battery — discharged from storage or repeated deep cycling",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine starting battery (Group 24 or 27, 600+ CCA)", "notes": "Marine environments deplete batteries faster. If the boat has been sitting, battery may be completely discharged."},
            {"name": "Marine battery charger", "notes": "Restore charge before concluding the battery is dead — a deep-cycle battery may read 0V and still be recoverable"},
        ],
    },
    "corroded_terminals": {
        "label": "Saltwater-corroded battery terminals or cable ends — voltage drop preventing cranking",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine battery terminals (tinned copper or brass)", "notes": "Clean or replace corroded terminals; standard automotive terminals corrode quickly in marine environments"},
            {"name": "Battery terminal grease / corrosion protector spray", "notes": "Apply after cleaning; prevents return of corrosion"},
            {"name": "Battery cable set (tinned marine grade)", "notes": "Non-marine cable corrodes internally and fails — marine cable is tin-coated"},
        ],
    },
    "neutral_safety_switch": {
        "label": "Neutral safety switch — gear selector not in neutral or switch faulty",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Neutral safety switch", "notes": "Most inboard/sterndrive engines won't crank unless the gear selector is fully in neutral. Confirm lever position then check the switch if still no-crank."},
        ],
    },
    "blown_fuse": {
        "label": "Blown main fuse or starter circuit fuse",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine fuse kit (blade and ANL fuses)", "notes": "Check the main fuse at the battery and the ignition/starter fuse in the engine fuse panel"},
        ],
    },
    "failed_starter": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter solenoid", "notes": "Single click = solenoid passing but starter may be seized; no click = solenoid, wiring, or dead battery"},
            {"name": "Starter motor (marine-rated)", "notes": "Use a marine-rated starter — standard automotive starters corrode rapidly in the bilge environment"},
        ],
    },
    "battery_switch_off": {
        "label": "Battery disconnect switch in OFF position or on wrong bank",
        "prior": 0.02,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Check the battery selector switch (BOTH / 1 / 2 / OFF) — it must be on a live bank. Also check if a main disconnect switch was left off."},
        ],
    },
}

NO_CRANK_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "First: is the kill switch lanyard (safety cord) clipped into the helm kill switch post?",
        "options": [
            {
                "match": "lanyard_missing",
                "label": "Not attached — lanyard is off or missing",
                "deltas": {
                    "kill_switch_lanyard": +0.65,
                },
                "eliminate": [],
                "next_node": "battery_switch",
            },
            {
                "match": "lanyard_attached",
                "label": "Yes — lanyard is clipped in",
                "deltas": {
                    "kill_switch_lanyard": -0.25,
                    "dead_battery": +0.10,
                    "corroded_terminals": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_switch",
            },
            {
                "match": "no_lanyard_system",
                "label": "This boat doesn't have a lanyard kill switch",
                "deltas": {
                    "kill_switch_lanyard": -0.30,
                    "neutral_safety_switch": +0.10,
                    "dead_battery": +0.10,
                },
                "eliminate": ["kill_switch_lanyard"],
                "next_node": "battery_switch",
            },
        ],
    },

    "battery_switch": {
        "question": "Is the battery selector switch turned to a live position (not OFF)?",
        "options": [
            {
                "match": "switch_off",
                "label": "It was on OFF — just turned it to BOTH or to the correct bank",
                "deltas": {
                    "battery_switch_off": +0.80,
                },
                "eliminate": [],
                "next_node": "crank_response",
            },
            {
                "match": "switch_on",
                "label": "Switch is on BOTH, 1, 2, or ON — correct position",
                "deltas": {
                    "battery_switch_off": -0.20,
                    "dead_battery": +0.05,
                    "corroded_terminals": +0.05,
                },
                "eliminate": [],
                "next_node": "crank_response",
            },
            {
                "match": "no_battery_switch",
                "label": "This boat has no battery selector switch",
                "deltas": {},
                "eliminate": ["battery_switch_off"],
                "next_node": "crank_response",
            },
        ],
    },

    "crank_response": {
        "question": "When you turn the key to START, what do you hear?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — no click, no solenoid, instrument panel is dark",
                "deltas": {
                    "dead_battery": +0.25,
                    "corroded_terminals": +0.20,
                    "blown_fuse": +0.15,
                    "battery_switch_off": +0.05,
                },
                "eliminate": ["failed_starter"],
                "next_node": "neutral_check",
            },
            {
                "match": "click_no_crank",
                "label": "Single click but no cranking",
                "deltas": {
                    "failed_starter": +0.30,
                    "dead_battery": +0.20,
                    "corroded_terminals": +0.10,
                },
                "eliminate": ["blown_fuse", "battery_switch_off", "kill_switch_lanyard"],
                "next_node": "neutral_check",
            },
            {
                "match": "rapid_clicking",
                "label": "Rapid clicking (chatter)",
                "deltas": {
                    "dead_battery": +0.50,
                    "corroded_terminals": +0.20,
                },
                "eliminate": ["blown_fuse", "kill_switch_lanyard", "battery_switch_off"],
                "next_node": "neutral_check",
            },
        ],
    },

    "neutral_check": {
        "question": "Is the gear selector lever firmly in the neutral position?",
        "options": [
            {
                "match": "in_gear",
                "label": "No — it was in gear, I've moved it to neutral",
                "deltas": {
                    "neutral_safety_switch": +0.30,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "confirmed_neutral",
                "label": "Yes — firmly in neutral",
                "deltas": {
                    "neutral_safety_switch": -0.10,
                    "dead_battery": +0.05,
                    "corroded_terminals": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_BOAT_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"dead_battery": +0.10, "corroded_terminals": +0.08},
    },
    "saltwater_use": {
        "yes": {"corroded_terminals": +0.15, "blown_fuse": +0.06, "failed_starter": +0.06},
    },
    "storage_time": {
        "months": {"dead_battery": +0.12, "corroded_terminals": +0.08, "kill_switch_lanyard": +0.06},
        "season": {"dead_battery": +0.15, "corroded_terminals": +0.10, "kill_switch_lanyard": +0.08},
    },
    "first_start_of_season": {
        "yes": {"dead_battery": +0.12, "corroded_terminals": +0.08, "kill_switch_lanyard": +0.06},
    },
}

NO_CRANK_BOAT_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, verify the kill switch lanyard clip is not damaged — a worn clip can cause intermittent shutdowns.",
    "Check that the battery terminals are sealed with terminal protector spray — marine environments corrode terminals quickly.",
]
