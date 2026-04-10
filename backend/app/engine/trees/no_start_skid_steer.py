"""
No-start diagnostic tree — skid steer loader (compact track loader / CTL included).

Skid steer-specific no-start considerations: the door/lap bar interlock is the
most commonly missed safety requirement — the door must be latched AND the lap
bar/seat bar must be lowered for the start circuit to close on most machines.
Both Bobcat, Case, CAT, and Deere skid steers use this dual interlock system.
"""

NO_START_SKID_STEER_HYPOTHESES: dict[str, dict] = {
    "door_lap_bar_interlock": {
        "label": "Door or lap bar interlock not satisfied — safety interlock preventing start",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Door latch switch", "notes": "Must be fully latched — door ajar sensor is very common cause"},
            {"name": "Lap bar / seat bar safety switch", "notes": "Bar must be fully lowered into operating position"},
        ],
    },
    "battery_voltage_drop": {
        "label": "Weak or dead battery / voltage drop under starter load",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Skid steer battery (OEM spec)", "notes": "Compact machines often have limited battery access — check terminals thoroughly"},
            {"name": "Battery cables and frame ground strap", "notes": "Ground to frame and engine block — both must be clean and tight"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem (empty tank, clogged filter, lift pump failure)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Inline fuel filter", "notes": "Located in fuel line from tank — often overlooked on compact machines"},
            {"name": "Fuel lift pump", "notes": "Check fuel pressure at injection pump inlet"},
        ],
    },
    "starter_solenoid": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter assembly", "notes": "Access is tight on skid steers — confirm solenoid voltage before removing"},
        ],
    },
    "air_in_fuel": {
        "label": "Air in fuel system (after running dry or filter change)",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "glow_plug_failure": {
        "label": "Glow plug(s) failed — cold-start condition",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test resistance with multimeter — typical 0.5–2 Ω per plug"},
        ],
    },
    "ecu_fault": {
        "label": "ECU / machine controller fault blocking start enable",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

NO_START_SKID_STEER_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key or press start, what happens?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — no sound, no click, no panel lights",
                "deltas": {
                    "battery_voltage_drop": +0.25,
                    "door_lap_bar_interlock": +0.25,
                    "fuel_delivery": -0.10,
                },
                "eliminate": ["glow_plug_failure", "air_in_fuel"],
                "next_node": "door_lap_bar",
            },
            {
                "match": "click_no_crank",
                "label": "Click or rapid clicking — no cranking",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "starter_solenoid": +0.22,
                },
                "eliminate": ["door_lap_bar_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
            {
                "match": "cranks_wont_fire",
                "label": "Engine cranks over but won't start",
                "deltas": {
                    "fuel_delivery": +0.28,
                    "air_in_fuel": +0.18,
                    "glow_plug_failure": +0.12,
                    "battery_voltage_drop": -0.10,
                },
                "eliminate": ["door_lap_bar_interlock"],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_slow",
                "label": "Engine attempts to crank but sounds very slow / weak",
                "deltas": {
                    "battery_voltage_drop": +0.38,
                },
                "eliminate": ["door_lap_bar_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
        ],
    },

    "door_lap_bar": {
        "question": "Check the two key interlocks: (1) Is the cab door fully latched shut? (2) Is the lap bar / seat bar fully lowered into the operating position while you are seated?",
        "options": [
            {
                "match": "both_ok",
                "label": "Yes — door latched, lap bar down, I am seated",
                "deltas": {
                    "door_lap_bar_interlock": -0.20,
                    "battery_voltage_drop": +0.18,
                    "starter_solenoid": +0.08,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "door_not_latched",
                "label": "Door wasn't fully latched — just closed it fully",
                "deltas": {
                    "door_lap_bar_interlock": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "lap_bar_up",
                "label": "Lap bar was in the raised position — just lowered it",
                "deltas": {
                    "door_lap_bar_interlock": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure how these interlocks work on this machine",
                "deltas": {
                    "door_lap_bar_interlock": +0.20,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery, and are the cable connections tight and corrosion-free?",
        "options": [
            {
                "match": "old_or_corroded",
                "label": "3+ years old, or terminals look corroded / loose",
                "deltas": {"battery_voltage_drop": +0.28},
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "recent_clean",
                "label": "Battery replaced within the past year, connections look good",
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
        "question": "Is the fuel tank at least 1/4 full? And has the fuel filter been changed within the last 500 hours or per OEM spec?",
        "options": [
            {
                "match": "empty_or_low",
                "label": "Tank is empty or nearly empty",
                "deltas": {
                    "fuel_delivery": +0.45,
                    "air_in_fuel": +0.18,
                },
                "eliminate": ["glow_plug_failure"],
                "next_node": None,
            },
            {
                "match": "filter_overdue",
                "label": "Fuel level fine but filter is way overdue",
                "deltas": {
                    "fuel_delivery": +0.22,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "fuel_ok",
                "label": "Fuel level fine and filter recently serviced",
                "deltas": {
                    "glow_plug_failure": +0.10,
                    "ecu_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure / can't check from here",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_service",
            },
        ],
    },

    "recent_service": {
        "question": "Any recent service or repairs before this no-start — fuel system, battery disconnect, or hydraulic work?",
        "options": [
            {
                "match": "fuel_work",
                "label": "Yes — fuel filter or fuel lines were worked on",
                "deltas": {
                    "air_in_fuel": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "battery_disconnect",
                "label": "Yes — battery was disconnected",
                "deltas": {
                    "battery_voltage_drop": +0.08,
                    "ecu_fault": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_service",
                "label": "No recent service",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_START_SKID_STEER_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"fuel_delivery": +0.08, "battery_voltage_drop": +0.05},
        "muddy": {"door_lap_bar_interlock": +0.08, "battery_voltage_drop": +0.05},
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
            "door_lap_bar_interlock": +0.05,
        },
    },
    "climate": {
        "cold": {"glow_plug_failure": +0.15, "battery_voltage_drop": +0.12},
        "hot": {"fuel_delivery": +0.05},
    },
}

NO_START_SKID_STEER_POST_DIAGNOSIS: list[str] = [
    "Skid steer interlock sequence: door must be FULLY latched (not just pushed to) AND lap/seat bar must be FULLY lowered AND operator must be seated — all three must be true simultaneously. A partially closed door is the most common cause of a 'no-start' on a functioning machine.",
    "Lap bar switch test: with the machine key OFF, manually push the lap bar to the fully lowered position and check for continuity across the switch terminals. Open circuit with bar lowered = failed switch.",
    "Battery access on skid steers is typically at the rear behind the cab. Tight quarters mean cable connections are often loose — torque to spec and apply anti-corrosion spray.",
    "After fuel filter change on skid steer: use the manual priming pump (if equipped) or crank in 5-second bursts with the throttle at low idle until fuel pressure builds — air lock is common on small fuel systems.",
    "On machines with stored fault codes: some will not allow starting until codes are acknowledged via the instrument panel — check for any warning indicators before further diagnosis.",
]
