"""
HVAC diagnostic tree (base / car).

Covers: refrigerant leak, compressor failure, cabin air filter, blend door actuator,
blower motor resistor/relay, heater core, blocked condenser, expansion valve / orifice tube.
"""

HVAC_HYPOTHESES: dict[str, dict] = {
    "refrigerant_low_leak": {
        "label": "Low refrigerant / refrigerant leak (weak or no cooling, hissing sound)",
        "prior": 0.26,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "A/C refrigerant recharge kit (R-134a or R-1234yf — check door sticker)", "notes": "R-1234yf is used on most vehicles 2017 and newer; do not use R-134a in an R-1234yf system"},
            {"name": "UV leak dye and UV light kit", "notes": "Dye injection locates the leak source — look for green/yellow staining at fittings, hoses, and condenser fins"},
        ],
    },
    "compressor_failure": {
        "label": "Failed A/C compressor or clutch (no cold air, loud clicking or grinding)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "A/C compressor with clutch assembly", "notes": "Always flush the system and replace the receiver/drier when replacing the compressor — metal debris from a failed compressor contaminates the entire system"},
            {"name": "PAG oil (correct viscosity — check compressor spec)", "notes": "Add correct PAG oil when installing new compressor; over or under-oiling causes premature failure"},
        ],
    },
    "cabin_air_filter_blocked": {
        "label": "Blocked cabin air filter (low airflow even at maximum fan speed)",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Cabin air filter", "notes": "Usually behind the glove box or under the dash; replace every 15,000–25,000 miles or annually — a blocked filter can also cause musty smells"},
        ],
    },
    "blend_door_actuator": {
        "label": "Failed blend door or actuator (stuck on full hot or full cold, clicking from dash)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Blend door actuator motor", "notes": "Clicking or tapping from behind the dashboard when changing temperature is the classic sign — typically a 20-minute DIY replacement"},
        ],
    },
    "blower_motor_resistor": {
        "label": "Failed blower motor resistor or relay (fan only works on some speeds or not at all)",
        "prior": 0.11,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Blower motor resistor module", "notes": "If fan only works on HIGH but not lower speeds, the resistor is the typical culprit"},
            {"name": "Blower motor relay", "notes": "If fan doesn't work at all on any speed, check the relay and blower fuse before replacing the motor"},
        ],
    },
    "heater_core": {
        "label": "Leaking or blocked heater core (no heat, sweet smell from vents, foggy windshield)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Heater core", "notes": "Dashboard removal required on most vehicles — this is typically 8–12 hours of labor at a shop"},
            {"name": "Heater hose and clamps", "notes": "Inspect heater inlet/outlet hoses while the dashboard is out — replace if swollen or brittle"},
        ],
    },
    "condenser_blocked": {
        "label": "Blocked A/C condenser (bugs, leaves, or bent fins — reduced cooling at low speed)",
        "prior": 0.07,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Condenser fin straightening comb", "notes": "Compressed air blows debris out from the back of the condenser; fin comb straightens bent fins — often restores lost cooling capacity"},
            {"name": "A/C condenser", "notes": "Replace if fins are more than 30% damaged or if the condenser core is cracked"},
        ],
    },
    "expansion_valve_orifice": {
        "label": "Clogged expansion valve or orifice tube (icing, intermittent cooling loss, hissing)",
        "prior": 0.04,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Expansion valve (TXV) or orifice tube", "notes": "Ice formation on the evaporator inlet line is the giveaway — system must be evacuated and recharged after replacement"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

HVAC_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary HVAC symptom?",
        "options": [
            {
                "match": "no_cold_air",
                "label": "No cold air — A/C blows warm or ambient temperature air",
                "deltas": {
                    "refrigerant_low_leak": +0.20,
                    "compressor_failure": +0.15,
                    "condenser_blocked": +0.08,
                    "blend_door_actuator": +0.05,
                    "heater_core": -0.05,
                    "blower_motor_resistor": -0.05,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
            {
                "match": "no_heat",
                "label": "No heat — heater blows cold air when set to hot",
                "deltas": {
                    "heater_core": +0.20,
                    "blend_door_actuator": +0.18,
                    "refrigerant_low_leak": -0.15,
                    "compressor_failure": -0.15,
                    "condenser_blocked": -0.15,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
            {
                "match": "weak_airflow",
                "label": "Weak airflow — temperature is OK but air volume is low",
                "deltas": {
                    "cabin_air_filter_blocked": +0.40,
                    "blower_motor_resistor": +0.15,
                    "refrigerant_low_leak": -0.10,
                    "compressor_failure": -0.10,
                    "heater_core": -0.10,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
            {
                "match": "fan_speed_issue",
                "label": "Fan only works on some speeds (e.g., only works on HIGH)",
                "deltas": {
                    "blower_motor_resistor": +0.55,
                    "refrigerant_low_leak": -0.15,
                    "compressor_failure": -0.15,
                    "heater_core": -0.10,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
            {
                "match": "bad_smell",
                "label": "Bad smell from vents — musty, sweet, or chemical odor",
                "deltas": {
                    "cabin_air_filter_blocked": +0.25,
                    "heater_core": +0.20,
                    "refrigerant_low_leak": -0.05,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
            {
                "match": "clicking_from_dash",
                "label": "Clicking, tapping, or banging noise from behind the dashboard",
                "deltas": {
                    "blend_door_actuator": +0.50,
                    "refrigerant_low_leak": -0.10,
                    "compressor_failure": -0.10,
                    "cabin_air_filter_blocked": -0.10,
                },
                "eliminate": [],
                "next_node": "compressor_check",
            },
        ],
    },

    "compressor_check": {
        "question": "When you turn on the A/C, can you hear the compressor clutch engage — a noticeable click from the engine bay?",
        "options": [
            {
                "match": "clicks_then_cycles",
                "label": "Clicks on, runs briefly (under 30 seconds), then clicks off repeatedly",
                "deltas": {
                    "refrigerant_low_leak": +0.30,
                    "compressor_failure": -0.10,
                    "expansion_valve_orifice": +0.08,
                },
                "eliminate": [],
                "next_node": "cabin_filter_check",
            },
            {
                "match": "clicks_runs",
                "label": "Clicks on and stays running continuously",
                "deltas": {
                    "condenser_blocked": +0.15,
                    "refrigerant_low_leak": +0.05,
                    "expansion_valve_orifice": +0.10,
                    "compressor_failure": -0.10,
                },
                "eliminate": [],
                "next_node": "cabin_filter_check",
            },
            {
                "match": "no_click",
                "label": "No click at all — compressor doesn't engage",
                "deltas": {
                    "compressor_failure": +0.30,
                    "refrigerant_low_leak": +0.10,
                    "expansion_valve_orifice": -0.05,
                },
                "eliminate": [],
                "next_node": "cabin_filter_check",
            },
            {
                "match": "not_ac_issue",
                "label": "Not an A/C issue — problem is with heat or fan only",
                "deltas": {},
                "eliminate": [],
                "next_node": "cabin_filter_check",
            },
        ],
    },

    "cabin_filter_check": {
        "question": "When was the cabin air filter last replaced? (It's usually behind the glove box.)",
        "options": [
            {
                "match": "recently",
                "label": "Recently — within the last year or 15,000 miles",
                "deltas": {
                    "cabin_air_filter_blocked": -0.25,
                },
                "eliminate": [],
                "next_node": "heat_or_defrost",
            },
            {
                "match": "never_or_unknown",
                "label": "Never changed or unknown",
                "deltas": {
                    "cabin_air_filter_blocked": +0.25,
                },
                "eliminate": [],
                "next_node": "heat_or_defrost",
            },
            {
                "match": "over_two_years",
                "label": "More than two years ago",
                "deltas": {
                    "cabin_air_filter_blocked": +0.12,
                },
                "eliminate": [],
                "next_node": "heat_or_defrost",
            },
        ],
    },

    "heat_or_defrost": {
        "question": "Is there any issue with the windshield fogging up inside, or does the defroster work poorly?",
        "options": [
            {
                "match": "fogging_inside",
                "label": "Yes — windshield fogs up heavily from the inside, especially in cold weather",
                "deltas": {
                    "heater_core": +0.35,
                    "cabin_air_filter_blocked": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "sweet_smell_heat",
                "label": "Sweet or antifreeze-like smell when the heater is on",
                "deltas": {
                    "heater_core": +0.45,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_fogging",
                "label": "No — no unusual fogging or windshield issues",
                "deltas": {
                    "heater_core": -0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HVAC_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {
            "refrigerant_low_leak": +0.10,
            "compressor_failure": +0.06,
            "condenser_blocked": +0.05,
        },
        "cold": {
            "heater_core": +0.12,
            "blend_door_actuator": +0.06,
        },
    },
    "mileage_band": {
        "high": {
            "compressor_failure": +0.08,
            "heater_core": +0.06,
            "blower_motor_resistor": +0.05,
        },
        "low": {
            "cabin_air_filter_blocked": +0.08,
        },
    },
}

HVAC_POST_DIAGNOSIS: list[str] = [
    "After any A/C refrigerant recharge, have the system leak-tested — a slow leak will have the system back to empty within a season and a recharge kit is not a permanent fix.",
    "If the heater core was the diagnosis, check coolant level and condition before pulling the dashboard — a blocked heater core is sometimes caused by debris from a previous coolant flush; a full system flush first may restore heat without a heater core replacement.",
    "After blend door actuator replacement, cycle the temperature control from full cold to full hot several times to recalibrate the actuator position sensor.",
]
