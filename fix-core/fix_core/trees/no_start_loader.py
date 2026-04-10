"""
No-start diagnostic tree — loader (wheel loader, front-end loader, telescopic handler).

Wheel loader no-start considerations: parking brake engagement interlock,
boom/bucket in lowered/float position requirement on some models, and the
distinct electrical system differences between compact and large loaders.
"""

NO_START_LOADER_HYPOTHESES: dict[str, dict] = {
    "battery_voltage_drop": {
        "label": "Weak or dead battery / voltage drop under starter load",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Loader battery (OEM spec)", "notes": "Large loaders may use dual 12V batteries in series for 24V systems"},
            {"name": "Battery cables and terminals", "notes": "Check both posts and all ground straps to frame and engine block"},
        ],
    },
    "parking_brake_interlock": {
        "label": "Parking brake interlock — brake not set or switch fault",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Parking brake switch", "notes": "Must be engaged before start circuit closes on most loaders"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem (empty tank, clogged pre-filter, failed lift pump)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel pre-filter / water separator element", "notes": "Change at every other engine oil service; inspect water bowl"},
            {"name": "Fuel lift pump", "notes": "Test with pressure gauge at pump outlet — typical spec 8–12 PSI"},
        ],
    },
    "starter_solenoid": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter motor / solenoid", "notes": "Test 12V or 24V at S terminal during crank attempt before replacing"},
        ],
    },
    "air_in_fuel": {
        "label": "Air in the fuel system",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "neutral_interlock": {
        "label": "Transmission or directional selector not in neutral",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "glow_plug_failure": {
        "label": "Glow plug(s) failed — cold-start issue",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test continuity; replace as a set"},
        ],
    },
}

NO_START_LOADER_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key or press start, what happens?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — no sound, no click, no instrument panel lights",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                    "parking_brake_interlock": +0.10,
                },
                "eliminate": ["glow_plug_failure", "air_in_fuel"],
                "next_node": "interlocks",
            },
            {
                "match": "click_no_crank",
                "label": "Click or rapid clicking — engine does not crank",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "starter_solenoid": +0.25,
                },
                "eliminate": ["parking_brake_interlock", "neutral_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
            {
                "match": "cranks_wont_fire",
                "label": "Engine cranks but won't start",
                "deltas": {
                    "fuel_delivery": +0.28,
                    "air_in_fuel": +0.18,
                    "glow_plug_failure": +0.12,
                    "battery_voltage_drop": -0.10,
                },
                "eliminate": ["parking_brake_interlock", "neutral_interlock"],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_slow",
                "label": "Tries to crank but sounds slow or labored",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                },
                "eliminate": ["parking_brake_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
        ],
    },

    "interlocks": {
        "question": "Check the loader's start interlocks: Is the parking brake engaged, the directional/gear selector in neutral, and the operator seated?",
        "options": [
            {
                "match": "all_set",
                "label": "Yes — parking brake on, neutral, seated",
                "deltas": {
                    "parking_brake_interlock": -0.15,
                    "neutral_interlock": -0.15,
                    "battery_voltage_drop": +0.15,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "brake_off",
                "label": "Parking brake was not set — just set it",
                "deltas": {
                    "parking_brake_interlock": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_neutral",
                "label": "Selector was not in neutral — just moved it",
                "deltas": {
                    "neutral_interlock": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure — will check now",
                "deltas": {
                    "parking_brake_interlock": +0.12,
                    "neutral_interlock": +0.12,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery, and is this a 12V or 24V system (24V uses two batteries)?",
        "options": [
            {
                "match": "old_12v",
                "label": "Single 12V battery, 3+ years old or unknown age",
                "deltas": {"battery_voltage_drop": +0.22},
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "dual_24v_old",
                "label": "24V system (two batteries), one or both may be old",
                "deltas": {"battery_voltage_drop": +0.25},
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "recent",
                "label": "Battery/batteries replaced within the past year",
                "deltas": {"battery_voltage_drop": -0.10, "starter_solenoid": +0.12},
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
        "question": "Is the fuel tank at least 1/4 full, and is the pre-filter / water separator showing clear (no water in bowl)?",
        "options": [
            {
                "match": "empty_or_low",
                "label": "Tank is empty or very low",
                "deltas": {
                    "fuel_delivery": +0.45,
                    "air_in_fuel": +0.15,
                },
                "eliminate": ["glow_plug_failure"],
                "next_node": None,
            },
            {
                "match": "water_in_filter",
                "label": "Fuel level fine but water in the separator bowl",
                "deltas": {
                    "fuel_delivery": +0.30,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "fuel_ok",
                "label": "Fuel level fine, separator clear",
                "deltas": {
                    "glow_plug_failure": +0.10,
                    "air_in_fuel": +0.08,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure / can't access right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_service",
            },
        ],
    },

    "recent_service": {
        "question": "Was any recent service performed — fuel system, battery disconnect, or engine work — before this no-start?",
        "options": [
            {
                "match": "fuel_service",
                "label": "Yes — fuel filter or lines were worked on",
                "deltas": {
                    "air_in_fuel": +0.38,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_disconnect",
                "label": "Yes — battery was disconnected and reconnected",
                "deltas": {
                    "battery_voltage_drop": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_service",
                "label": "No recent service — sudden no-start",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_START_LOADER_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"fuel_delivery": +0.08, "battery_voltage_drop": +0.05},
        "muddy": {"battery_voltage_drop": +0.05, "parking_brake_interlock": +0.05},
        "marine": {"battery_voltage_drop": +0.10},
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
        },
    },
    "climate": {
        "cold": {"glow_plug_failure": +0.15, "battery_voltage_drop": +0.12},
        "hot": {"fuel_delivery": +0.05},
    },
}

NO_START_LOADER_POST_DIAGNOSIS: list[str] = [
    "On 24V dual-battery loaders: test each battery individually (with the other disconnected). A single weak cell in one battery pulls down the entire series circuit and causes slow crank or no-start.",
    "Parking brake interlock: the switch is typically on the parking brake valve or pedal linkage. Test continuity with the brake set — open circuit = switch fault or adjustment needed.",
    "After fuel system service, bleed air via the manual priming pump and/or loosen the bleed screw at the injection pump until bubble-free fuel flows, then tighten and crank.",
    "Neutral interlock switch location varies: check the directional control lever (F-N-R), transmission range selector, and any joystick pilot solenoid override.",
    "Large wheel loaders with electronic engine management: fault codes stored in the ECU may need to be cleared after battery replacement before the start circuit will enable.",
]
