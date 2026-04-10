"""
No-start diagnostic tree — tractor (agricultural/utility).

Covers diesel and gas tractor no-start conditions. Tractor-specific failure modes
include PTO disengagement interlocks, clutch/range neutral requirements, 3-point
hitch position interlocks, and implement-related safety switches that differ from
general construction equipment.
"""

NO_START_TRACTOR_HYPOTHESES: dict[str, dict] = {
    "battery_voltage_drop": {
        "label": "Weak or dead battery / voltage drop under starter load",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Tractor battery (group 24 or OEM spec)", "notes": "Test voltage under load — resting voltage can be misleading"},
            {"name": "Battery cable ends / terminals", "notes": "Corrosion under insulation is common on field tractors"},
        ],
    },
    "pto_interlock": {
        "label": "PTO or implement interlock preventing start",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "PTO engagement switch / safety switch", "notes": "Must be fully disengaged to enable starting on most tractors"},
        ],
    },
    "neutral_clutch_interlock": {
        "label": "Clutch not fully depressed or range selector not in neutral",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem (empty tank, clogged filter, failed lift pump)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Inline fuel filter", "notes": "Replace first — inexpensive and commonly neglected on farm equipment"},
            {"name": "Fuel lift pump", "notes": "Check inlet side restriction before condemning pump"},
        ],
    },
    "starter_solenoid": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter motor / solenoid assembly", "notes": "Bench-test solenoid pull-in before replacing"},
        ],
    },
    "glow_plug_failure": {
        "label": "Glow plug(s) failed (diesel) — cold-start issue",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test with multimeter — should show ~0.5-2 Ω resistance"},
        ],
    },
    "air_in_fuel": {
        "label": "Air in the fuel system (after running dry or filter change)",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [],
    },
}

NO_START_TRACTOR_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key, what happens?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — no click, no sound, no lights",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                    "starter_solenoid": +0.05,
                    "fuel_delivery": -0.10,
                },
                "eliminate": ["glow_plug_failure", "air_in_fuel"],
                "next_node": "interlocks",
            },
            {
                "match": "click_no_crank",
                "label": "Single click or rapid clicking — no crank",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "starter_solenoid": +0.20,
                },
                "eliminate": ["pto_interlock", "neutral_clutch_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
            {
                "match": "cranks_wont_fire",
                "label": "Engine cranks over but won't fire",
                "deltas": {
                    "fuel_delivery": +0.25,
                    "air_in_fuel": +0.20,
                    "glow_plug_failure": +0.15,
                    "battery_voltage_drop": -0.10,
                },
                "eliminate": ["pto_interlock", "neutral_clutch_interlock"],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_slow",
                "label": "Tries to crank but very slow / labored",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                },
                "eliminate": ["pto_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
        ],
    },

    "interlocks": {
        "question": "Check the tractor interlocks: Is the PTO disengaged, clutch pedal depressed (or clutch lever in 'start' position), range selector in neutral, and seat occupied?",
        "options": [
            {
                "match": "all_ok",
                "label": "Yes — PTO off, clutch in, neutral set, seated",
                "deltas": {
                    "pto_interlock": -0.15,
                    "neutral_clutch_interlock": -0.15,
                    "battery_voltage_drop": +0.15,
                    "starter_solenoid": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "pto_engaged",
                "label": "PTO was engaged — just disengaged it",
                "deltas": {
                    "pto_interlock": +0.50,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_in_neutral",
                "label": "Range selector wasn't in neutral / clutch wasn't in",
                "deltas": {
                    "neutral_clutch_interlock": +0.50,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure which interlocks to check",
                "deltas": {
                    "pto_interlock": +0.15,
                    "neutral_clutch_interlock": +0.15,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery, or when was it last replaced?",
        "options": [
            {
                "match": "old_or_unknown",
                "label": "3+ years old or unknown",
                "deltas": {"battery_voltage_drop": +0.20},
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "recent",
                "label": "Replaced within the past year",
                "deltas": {"battery_voltage_drop": -0.10, "starter_solenoid": +0.10},
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "fuel_check",
            },
        ],
    },

    "fuel_check": {
        "question": "Check the fuel level and filter. Is the tank at least 1/4 full, and when was the fuel filter last changed?",
        "options": [
            {
                "match": "low_or_empty",
                "label": "Tank is empty or very low",
                "deltas": {
                    "fuel_delivery": +0.45,
                    "air_in_fuel": +0.15,
                },
                "eliminate": ["glow_plug_failure", "starter_solenoid"],
                "next_node": None,
            },
            {
                "match": "filter_overdue",
                "label": "Fuel level fine but filter hasn't been changed in years",
                "deltas": {
                    "fuel_delivery": +0.20,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "fuel_ok",
                "label": "Fuel level fine, filter recently serviced",
                "deltas": {
                    "glow_plug_failure": +0.10,
                    "air_in_fuel": +0.08,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_service",
            },
        ],
    },

    "recent_service": {
        "question": "Was any recent work done on the tractor — fuel system, battery, or engine — before this no-start condition began?",
        "options": [
            {
                "match": "fuel_work",
                "label": "Yes — fuel filter, fuel lines, or injectors were disturbed",
                "deltas": {
                    "air_in_fuel": +0.35,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_work",
                "label": "Yes — battery or electrical work was done",
                "deltas": {
                    "battery_voltage_drop": +0.10,
                    "starter_solenoid": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_recent_work",
                "label": "No recent work — this came on suddenly",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_START_TRACTOR_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"fuel_delivery": +0.08, "battery_voltage_drop": +0.05},
        "cold": {"glow_plug_failure": +0.15, "battery_voltage_drop": +0.12},
        "marine": {"battery_voltage_drop": +0.08},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "fuel_delivery": +0.12,
            "battery_voltage_drop": +0.08,
        },
        "long_storage": {
            "fuel_delivery": +0.15,
            "air_in_fuel": +0.12,
            "battery_voltage_drop": +0.15,
            "glow_plug_failure": +0.05,
        },
    },
    "climate": {
        "cold": {"glow_plug_failure": +0.18, "battery_voltage_drop": +0.12},
        "hot": {"fuel_delivery": +0.05},
    },
}

NO_START_TRACTOR_POST_DIAGNOSIS: list[str] = [
    "Tractor interlock reminder: PTO must be fully disengaged, clutch fully depressed or in 'start' detent, range/gear selector in neutral — all must be satisfied simultaneously before the start circuit is enabled.",
    "After any fuel filter change or running dry, bleed the fuel system at the injection pump or bleed screw before attempting to start — air in the high-pressure fuel circuit prevents firing.",
    "Test battery voltage under cranking load: a battery reading 12.6V at rest can collapse below 10V under starter current if a cell is failing.",
    "Cold-start diesel tractors: wait for the glow plug indicator light to go out before cranking — some older tractors require a full 15–20 seconds in cold weather.",
    "Fuel shutoff solenoid check (if equipped): turn key to RUN and listen for an audible click from the solenoid. No click = solenoid or wiring issue. Key OFF should produce a second click as it closes.",
]
