"""
No-start diagnostic tree — excavator (hydraulic excavator, mini-excavator).

Excavator-specific no-start considerations: gate lever / lockout lever interlock
(must be raised to enable start on most modern excavators), swing lock, and
cab/canopy door switches. Most excavators combine "no crank" and "cranks but
won't fire" in the same operator-described symptom.
"""

NO_START_EXCAVATOR_HYPOTHESES: dict[str, dict] = {
    "battery_voltage_drop": {
        "label": "Weak or dead battery / voltage drop under starter load",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Excavator battery (OEM group spec)", "notes": "Test under load — surface charge can mask a bad cell"},
            {"name": "Battery cable / terminal hardware", "notes": "Check both main cable and ground strap to frame"},
        ],
    },
    "gate_lever_interlock": {
        "label": "Gate/lockout lever not fully raised — safety interlock preventing start",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Gate lever safety switch", "notes": "Lever must be fully up before start circuit closes; test switch continuity"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem (empty tank, clogged filter, failed lift pump)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel pre-filter / water separator", "notes": "Most common service item — check fuel quality and water level in bowl"},
            {"name": "Fuel lift pump", "notes": "Check inlet restriction before replacing"},
        ],
    },
    "starter_solenoid": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter motor assembly", "notes": "Confirm solenoid pull-in voltage at S terminal before condemning"},
        ],
    },
    "air_in_fuel": {
        "label": "Air ingested into fuel system (after running dry or filter service)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "ecu_controller": {
        "label": "Engine/machine controller fault preventing start enable",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "glow_plug_failure": {
        "label": "Glow plug(s) failed — cold-weather no-fire",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Replace as a set; check continuity with multimeter"},
        ],
    },
}

NO_START_EXCAVATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key or press the start button, what happens?",
        "options": [
            {
                "match": "nothing",
                "label": "Nothing — no sound, no click, no instrument panel lights",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                    "gate_lever_interlock": +0.10,
                    "fuel_delivery": -0.10,
                },
                "eliminate": ["glow_plug_failure", "air_in_fuel"],
                "next_node": "gate_lever",
            },
            {
                "match": "click_no_crank",
                "label": "Click or rapid clicking — engine does not turn over",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "starter_solenoid": +0.25,
                },
                "eliminate": ["gate_lever_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
            {
                "match": "cranks_wont_fire",
                "label": "Engine cranks but won't start",
                "deltas": {
                    "fuel_delivery": +0.25,
                    "air_in_fuel": +0.20,
                    "glow_plug_failure": +0.12,
                    "battery_voltage_drop": -0.10,
                },
                "eliminate": ["gate_lever_interlock"],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_slow",
                "label": "Engine attempts to crank but sounds very slow / labored",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                },
                "eliminate": ["gate_lever_interlock", "glow_plug_failure"],
                "next_node": "battery_age",
            },
        ],
    },

    "gate_lever": {
        "question": "Is the gate lever (safety lockout bar — the bar next to your left leg in the cab) fully raised? And is the operator seat occupied with the seat belt fastened if required?",
        "options": [
            {
                "match": "lever_raised_ok",
                "label": "Yes — lever is fully raised, seat is occupied",
                "deltas": {
                    "gate_lever_interlock": -0.18,
                    "battery_voltage_drop": +0.15,
                    "starter_solenoid": +0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "lever_was_down",
                "label": "Lever was in the lowered position — just raised it",
                "deltas": {
                    "gate_lever_interlock": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure where the gate lever needs to be",
                "deltas": {
                    "gate_lever_interlock": +0.20,
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
        "question": "Check the fuel gauge and pre-filter water separator bowl. Is there adequate fuel, and is the water separator bowl clear (no milky or dark water)?",
        "options": [
            {
                "match": "empty_or_low",
                "label": "Fuel gauge shows empty or near empty",
                "deltas": {
                    "fuel_delivery": +0.45,
                    "air_in_fuel": +0.15,
                },
                "eliminate": ["glow_plug_failure"],
                "next_node": None,
            },
            {
                "match": "water_in_separator",
                "label": "Fuel level okay but separator bowl has water or milky fluid",
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
                    "ecu_controller": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_service",
            },
            {
                "match": "not_sure",
                "label": "Not sure / can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_service",
            },
        ],
    },

    "recent_service": {
        "question": "Was the excavator recently serviced? Specifically, was the fuel system, battery, or any electrical component worked on before this no-start?",
        "options": [
            {
                "match": "fuel_work",
                "label": "Yes — fuel filter, separator, or lines were serviced",
                "deltas": {
                    "air_in_fuel": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "electrical_work",
                "label": "Yes — battery or electrical system was worked on",
                "deltas": {
                    "battery_voltage_drop": +0.10,
                    "ecu_controller": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_work",
                "label": "No — came on suddenly without prior service",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_START_EXCAVATOR_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"fuel_delivery": +0.08, "battery_voltage_drop": +0.05},
        "muddy": {"battery_voltage_drop": +0.05, "gate_lever_interlock": +0.05},
        "marine": {"battery_voltage_drop": +0.10, "ecu_controller": +0.05},
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
        "cold": {"glow_plug_failure": +0.15, "battery_voltage_drop": +0.12},
        "hot": {"fuel_delivery": +0.05},
    },
}

NO_START_EXCAVATOR_POST_DIAGNOSIS: list[str] = [
    "Gate/lockout lever: must be in the fully RAISED position before the start circuit is enabled on most modern excavators (Komatsu, CAT, Deere, Volvo CE). If the lever switch is faulty, the circuit stays open even with lever raised.",
    "After any fuel system service, bleed air from the system: use the manual priming pump (if equipped) or crank briefly with injection pump decompressed to purge air before attempting a full start.",
    "Excavator batteries often sit in compartments with poor ventilation — inspect for corrosion at both posts and the ground strap to the frame.",
    "On machines with electronic engine controls: active fault codes may be locking out the start enable relay. Check the instrument panel for fault codes before further diagnosis.",
    "Cold-weather starts: ensure glow plug warm-up cycle completes (light off on instrument panel) before cranking — modern common-rail excavators may require 15–25 seconds in sub-zero conditions.",
]
