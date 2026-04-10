"""
No-crank diagnostic tree — ATV/UTV variant.

Key ATV/UTV differences: thumb throttle kill switches, gear/brake
safety interlocks (engine won't crank unless in park or neutral with
brake held), and common battery drain from winches/accessories.
"""

NO_CRANK_ATV_HYPOTHESES: dict[str, dict] = {
    "dead_battery": {
        "label": "Dead or discharged battery — common after storage or accessory drain",
        "prior": 0.32,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "ATV/UTV battery (YTX or equivalent)", "notes": "Match CCA rating; ATVs sit unused for months — batteries sulfate quickly without a maintainer"},
            {"name": "Battery tender / maintainer", "notes": "Essential for seasonal machines; prevents discharge during storage"},
        ],
    },
    "safety_interlock": {
        "label": "Safety interlock not satisfied — gear not in Park/Neutral or brake not engaged",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Neutral safety switch / brake switch", "notes": "Most ATVs require Park or Neutral + brake engaged to crank. Wiggle the shifter and fully press the brake before troubleshooting further."},
        ],
    },
    "kill_switch": {
        "label": "Kill switch in OFF position or thumb kill switch stuck",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Kill switch / emergency stop switch", "notes": "Check the handlebar-mounted thumb kill switch — it's easy to accidentally bump to OFF. Also check the tether kill switch if equipped."},
        ],
    },
    "bad_connections": {
        "label": "Corroded or loose battery terminals or ground strap",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Battery terminal cleaner + protector spray", "notes": "ATVs/UTVs are operated in mud and water — corrosion on terminals is common"},
            {"name": "Ground strap", "notes": "Check frame ground strap at the battery negative and at the engine block"},
        ],
    },
    "blown_fuse": {
        "label": "Blown main fuse or ignition fuse — often from accessory overload",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "ATV fuse kit (blade fuses, assorted)", "notes": "Check the main fuse at the battery and the ignition/starter fuse in the fuse box. Accessory wiring (winch, lights) is a common blowing source."},
        ],
    },
    "failed_starter": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter solenoid", "notes": "Single click but no crank = suspect solenoid or very low battery"},
            {"name": "Starter motor", "notes": "No click at all with good battery and fuses = solenoid or starter motor failure"},
        ],
    },
}

NO_CRANK_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "When you press the start button, what happens — any sound at all, lights on the dash, or completely dead?",
        "options": [
            {
                "match": "nothing_dead",
                "label": "Completely dead — no lights, no click, no sound",
                "deltas": {
                    "dead_battery": +0.30,
                    "bad_connections": +0.20,
                    "blown_fuse": +0.15,
                    "kill_switch": +0.10,
                },
                "eliminate": ["failed_starter"],
                "next_node": "kill_switch_check",
            },
            {
                "match": "click_no_crank",
                "label": "One click or clunk but engine doesn't crank",
                "deltas": {
                    "failed_starter": +0.30,
                    "dead_battery": +0.25,
                    "bad_connections": +0.15,
                },
                "eliminate": ["blown_fuse", "kill_switch"],
                "next_node": "kill_switch_check",
            },
            {
                "match": "rapid_clicking",
                "label": "Rapid clicking (chatter)",
                "deltas": {
                    "dead_battery": +0.55,
                    "bad_connections": +0.20,
                },
                "eliminate": ["blown_fuse", "kill_switch", "failed_starter"],
                "next_node": "kill_switch_check",
            },
            {
                "match": "lights_on_no_crank",
                "label": "Lights and dash work but starter doesn't engage",
                "deltas": {
                    "safety_interlock": +0.30,
                    "failed_starter": +0.20,
                    "kill_switch": +0.15,
                    "blown_fuse": +0.10,
                },
                "eliminate": ["dead_battery"],
                "next_node": "kill_switch_check",
            },
        ],
    },

    "kill_switch_check": {
        "question": "Is the handlebar kill switch (thumb switch / emergency stop) in the RUN position?",
        "options": [
            {
                "match": "kill_switch_off",
                "label": "It was in the OFF or STOP position",
                "deltas": {
                    "kill_switch": +0.70,
                },
                "eliminate": ["dead_battery", "failed_starter", "blown_fuse"],
                "next_node": None,
            },
            {
                "match": "kill_switch_run",
                "label": "Yes — in RUN position",
                "deltas": {
                    "kill_switch": -0.15,
                    "safety_interlock": +0.10,
                    "dead_battery": +0.05,
                },
                "eliminate": [],
                "next_node": "safety_check",
            },
        ],
    },

    "safety_check": {
        "question": "Is the gear selector in Park or Neutral, and is the brake lever fully pressed?",
        "options": [
            {
                "match": "in_gear",
                "label": "No — was in gear, now in Park/Neutral with brake held",
                "deltas": {
                    "safety_interlock": +0.65,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "confirmed_safe",
                "label": "Yes — Park/Neutral with brake pressed, still no crank",
                "deltas": {
                    "safety_interlock": -0.15,
                    "dead_battery": +0.10,
                    "bad_connections": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_check",
            },
        ],
    },

    "battery_check": {
        "question": "When did you last charge or replace the battery, and has the machine been sitting unused?",
        "options": [
            {
                "match": "sat_long",
                "label": "Sat for weeks or months without being started",
                "deltas": {
                    "dead_battery": +0.40,
                    "bad_connections": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_fresh",
                "label": "Battery is new or recently charged and machine is used regularly",
                "deltas": {
                    "dead_battery": -0.15,
                    "blown_fuse": +0.15,
                    "failed_starter": +0.20,
                    "bad_connections": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "accessories_added",
                "label": "Accessories recently added (winch, lights, audio)",
                "deltas": {
                    "blown_fuse": +0.30,
                    "dead_battery": +0.15,
                    "bad_connections": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"dead_battery": +0.12, "bad_connections": +0.06},
    },
    "mileage_band": {
        "high": {"failed_starter": +0.08, "bad_connections": +0.06},
    },
    "storage_time": {
        "months": {"dead_battery": +0.15, "bad_connections": +0.08},
        "season": {"dead_battery": +0.18, "bad_connections": +0.10, "blown_fuse": +0.05},
    },
    "first_start_of_season": {
        "yes": {"dead_battery": +0.15, "bad_connections": +0.08},
    },
}

NO_CRANK_ATV_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, check all accessory wiring (winch, lights) for bare spots — ATV vibration chafes wires and causes fuse failures.",
    "Connect a battery maintainer during storage season to prevent sulfation.",
]
