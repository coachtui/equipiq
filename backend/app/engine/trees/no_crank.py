"""
No-crank diagnostic tree.

"No crank" = turning the key produces no cranking sound at all
(or only a click/clunk but engine does not turn over).

Hypotheses and their initial prior scores (0-1).
Scores are updated as answers come in via delta weights.
"""

# Initial prior scores for each hypothesis (before any questions answered)
NO_CRANK_HYPOTHESES: dict[str, dict] = {
    "dead_battery": {
        "label": "Dead or severely discharged battery",
        "prior": 0.40,
        "diy_difficulty": "easy",
        "parts": [{"name": "Car battery", "notes": "Match group size on old battery label"}],
    },
    "bad_battery_connections": {
        "label": "Corroded or loose battery terminals/cables",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [{"name": "Battery terminal cleaner/protector", "notes": "Or replacement cables if badly corroded"}],
    },
    "faulty_starter": {
        "label": "Failed starter motor",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [{"name": "Starter motor", "notes": "Confirm compatibility with year/make/model"}],
    },
    "bad_starter_relay_solenoid": {
        "label": "Bad starter relay or solenoid",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [{"name": "Starter relay", "notes": "Check fuse box label; often $5–15 part"}],
    },
    "neutral_safety_switch": {
        "label": "Faulty neutral safety switch / clutch switch",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [{"name": "Neutral safety switch", "notes": "Automatic; or clutch pedal switch for manual"}],
    },
    "immobilizer_anti_theft": {
        "label": "Anti-theft / immobilizer engaged",
        "prior": 0.05,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "ignition_switch": {
        "label": "Failed ignition switch",
        "prior": 0.02,
        "diy_difficulty": "moderate",
        "parts": [{"name": "Ignition switch", "notes": "Electrical portion, not key cylinder"}],
    },
    "seized_engine": {
        "label": "Seized engine (hydrolocked or mechanical failure)",
        "prior": 0.01,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
#
# Each node has:
#   question  - what to ask (used as template; LLM rephrases naturally)
#   options   - list of answer options, each with:
#       match     - keywords/phrases LLM maps user answer to (for display)
#       deltas    - {hypothesis_key: float} score adjustments
#       next_node - which node to go to after this answer (None = end)
#       eliminate - [hypothesis_keys] to eliminate outright
# ─────────────────────────────────────────────────────────────────────────────

NO_CRANK_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key (or press start), what do you hear or see?",
        "options": [
            {
                "match": "nothing_silent",
                "label": "Completely silent — no sound at all",
                "deltas": {
                    "dead_battery": +0.10,
                    "ignition_switch": +0.10,
                    "neutral_safety_switch": +0.10,
                    "bad_starter_relay_solenoid": +0.05,
                    "faulty_starter": -0.05,
                },
                "eliminate": [],
                "next_node": "lights_work",
            },
            {
                "match": "single_click",
                "label": "One loud click, then nothing",
                "deltas": {
                    "faulty_starter": +0.25,
                    "bad_battery_connections": +0.15,
                    "dead_battery": +0.05,
                    "bad_starter_relay_solenoid": +0.05,
                },
                "eliminate": ["seized_engine", "immobilizer_anti_theft"],
                "next_node": "battery_age",
            },
            {
                "match": "rapid_clicks",
                "label": "Rapid clicking (chatter) when key is held",
                "deltas": {
                    "dead_battery": +0.30,
                    "bad_battery_connections": +0.20,
                    "faulty_starter": -0.10,
                },
                "eliminate": ["seized_engine", "immobilizer_anti_theft", "ignition_switch"],
                "next_node": "battery_age",
            },
            {
                "match": "slow_groan",
                "label": "Slow labored cranking / groaning but won't start",
                "deltas": {
                    "dead_battery": +0.25,
                    "seized_engine": +0.15,
                    "bad_battery_connections": +0.10,
                },
                "eliminate": ["ignition_switch", "neutral_safety_switch", "immobilizer_anti_theft"],
                "next_node": "battery_age",
            },
            {
                "match": "lights_dim_flicker",
                "label": "Dashboard lights dim or flicker but no crank",
                "deltas": {
                    "dead_battery": +0.25,
                    "bad_battery_connections": +0.20,
                },
                "eliminate": ["ignition_switch", "immobilizer_anti_theft"],
                "next_node": "battery_age",
            },
        ],
    },

    "lights_work": {
        "question": "Do the headlights and interior lights work normally when you try them?",
        "options": [
            {
                "match": "lights_full",
                "label": "Yes — lights are bright and normal",
                "deltas": {
                    "dead_battery": -0.20,
                    "neutral_safety_switch": +0.15,
                    "ignition_switch": +0.15,
                    "bad_starter_relay_solenoid": +0.10,
                    "immobilizer_anti_theft": +0.10,
                },
                "eliminate": [],
                "next_node": "transmission_position",
            },
            {
                "match": "lights_dim",
                "label": "Lights are dim or flicker",
                "deltas": {
                    "dead_battery": +0.25,
                    "bad_battery_connections": +0.20,
                },
                "eliminate": ["ignition_switch", "neutral_safety_switch", "immobilizer_anti_theft"],
                "next_node": "battery_age",
            },
            {
                "match": "lights_none",
                "label": "No lights at all",
                "deltas": {
                    "dead_battery": +0.30,
                    "bad_battery_connections": +0.25,
                },
                "eliminate": ["ignition_switch", "neutral_safety_switch", "faulty_starter", "immobilizer_anti_theft"],
                "next_node": "battery_age",
            },
        ],
    },

    "transmission_position": {
        "question": "Is this an automatic or manual transmission, and what gear/position is it in?",
        "options": [
            {
                "match": "auto_park",
                "label": "Automatic — in Park",
                "deltas": {},
                "eliminate": [],
                "next_node": "anti_theft",
            },
            {
                "match": "auto_neutral",
                "label": "Automatic — tried Park AND Neutral",
                "deltas": {
                    "neutral_safety_switch": -0.10,
                },
                "eliminate": [],
                "next_node": "anti_theft",
            },
            {
                "match": "auto_not_tried_neutral",
                "label": "Automatic — only tried Park, not Neutral",
                "deltas": {
                    "neutral_safety_switch": +0.15,
                },
                "eliminate": [],
                "next_node": "anti_theft",
            },
            {
                "match": "manual_clutch_in",
                "label": "Manual — clutch pedal fully pressed",
                "deltas": {},
                "eliminate": [],
                "next_node": "anti_theft",
            },
            {
                "match": "manual_clutch_not_pressed",
                "label": "Manual — clutch not pressed or partially pressed",
                "deltas": {
                    "neutral_safety_switch": +0.30,
                },
                "eliminate": [],
                "next_node": None,  # very likely cause — end early
            },
        ],
    },

    "anti_theft": {
        "question": "Does your security / anti-theft light flash or stay solid on the dashboard?",
        "options": [
            {
                "match": "security_light_on",
                "label": "Yes — security light is on or flashing",
                "deltas": {
                    "immobilizer_anti_theft": +0.35,
                    "dead_battery": -0.10,
                    "faulty_starter": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "security_light_off",
                "label": "No security light",
                "deltas": {
                    "immobilizer_anti_theft": -0.20,
                    "faulty_starter": +0.10,
                    "bad_starter_relay_solenoid": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "battery_age": {
        "question": "Roughly how old is your battery, and when did the car last run normally?",
        "options": [
            {
                "match": "battery_new",
                "label": "Battery is less than 2 years old / replaced recently",
                "deltas": {
                    "dead_battery": -0.15,
                    "bad_battery_connections": +0.10,
                    "faulty_starter": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_old",
                "label": "Battery is 3+ years old",
                "deltas": {
                    "dead_battery": +0.20,
                    "bad_battery_connections": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_unknown",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "ran_recently",
                "label": "Ran fine very recently (today or yesterday)",
                "deltas": {
                    "dead_battery": +0.10,
                    "bad_battery_connections": +0.05,
                    "faulty_starter": +0.05,
                },
                "eliminate": ["seized_engine"],
                "next_node": None,
            },
        ],
    },
}

NO_CRANK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"dead_battery": +0.10, "faulty_starter": +0.05},
        "hot": {"dead_battery": +0.05},
    },
    "mileage_band": {
        "high": {"faulty_starter": +0.08, "bad_battery_connections": +0.06},
        "low": {"immobilizer_anti_theft": +0.05},
    },
    "usage_pattern": {
        "city": {"bad_battery_connections": +0.05},
    },
}

NO_CRANK_POST_DIAGNOSIS: list[str] = [
    "After resolving the no-crank, fully charge the battery and load-test it — a battery that caused a no-crank event often has reduced capacity even after charging.",
    "Inspect battery cable ends for heat discoloration or melted insulation if a starter draw was involved.",
]
