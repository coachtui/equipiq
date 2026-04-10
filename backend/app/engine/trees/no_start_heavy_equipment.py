"""
No-start diagnostic tree — heavy equipment (diesel).

Covers all failure modes where a diesel-powered heavy machine (excavator, dozer,
loader, crane, skid steer, roller, etc.) fails to start.  Unlike the passenger-
vehicle crank_no_start tree, this combines "no crank" and "cranks but won't fire"
into a single operator-facing workflow, since field operators describe both as
"won't start."

Questions use plain language, allow "not sure" responses, and guide operators
through physical checks they can perform on a jobsite.
"""

NO_START_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "battery_voltage_drop": {
        "label": "Weak or dead battery / voltage drop under starter load",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Heavy-duty battery (group 31 or OEM spec)", "notes": "Test voltage under load before replacing — surface charge can fool a voltmeter"},
            {"name": "Battery terminals / cable ends", "notes": "Corrosion or loose clamps are common on jobsite equipment"},
        ],
    },
    "starter_solenoid": {
        "label": "Failed starter motor or solenoid",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Starter motor assembly", "notes": "Bench test solenoid pull-in before condemning starter"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem (empty tank, clogged filter, failed lift pump)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel pre-filter / water separator", "notes": "Most common consumable on diesel equipment — change first"},
            {"name": "Fuel lift pump", "notes": "Check inlet side for restrictions before replacing pump"},
        ],
    },
    "air_in_fuel": {
        "label": "Air in the fuel system (after running dry, filter change, or line work)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "injector_failure": {
        "label": "Failed or stuck-open injector(s)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Diesel injectors", "notes": "Flow test recommended before replacing — expensive parts"},
        ],
    },
    "safety_interlock": {
        "label": "Safety interlock preventing start (seat switch, neutral/park lock, door/canopy switch)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "glow_plug_failure": {
        "label": "Glow plug(s) failed — engine too cold to fire",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Replace as a set; test with multimeter for continuity"},
        ],
    },
    "ecu_controller": {
        "label": "ECU / machine controller fault preventing crank enable",
        "prior": 0.02,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "fuel_shutoff_solenoid": {
        "label": "Fuel shutoff solenoid failed closed — cutting fuel despite pump and filters being fine",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel shutoff solenoid (ESOS)", "notes": "Powered-open type: 12V/24V to open, spring-closes on power loss. Test: apply battery voltage directly — you should hear a click and feel it open"},
        ],
    },
}

NO_START_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "When you turn the key or press start, what happens?",
        "options": [
            {
                "match": "nothing_at_all",
                "label": "Nothing — no click, no sound, no dash lights",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "safety_interlock": +0.15,
                    "ecu_controller": +0.05,
                    "fuel_delivery": -0.10,
                    "air_in_fuel": -0.10,
                },
                "eliminate": ["glow_plug_failure"],
                "next_node": "dash_lights",
            },
            {
                "match": "click_no_crank",
                "label": "Single click or rapid clicking — engine does not turn over",
                "deltas": {
                    "battery_voltage_drop": +0.35,
                    "starter_solenoid": +0.20,
                },
                "eliminate": ["air_in_fuel", "glow_plug_failure"],
                "next_node": "dash_lights",
            },
            {
                "match": "cranks_wont_fire",
                "label": "Engine turns over (cranking sound) but won't start",
                "deltas": {
                    "fuel_delivery": +0.20,
                    "air_in_fuel": +0.20,
                    "glow_plug_failure": +0.10,
                    "injector_failure": +0.08,
                    "fuel_shutoff_solenoid": +0.05,
                    "battery_voltage_drop": -0.10,
                    "starter_solenoid": -0.10,
                },
                "eliminate": [],
                "next_node": "cranks_speed",
            },
            {
                "match": "cranks_slow",
                "label": "Tries to crank but sounds very slow / labored",
                "deltas": {
                    "battery_voltage_drop": +0.30,
                    "fuel_delivery": +0.05,
                },
                "eliminate": ["safety_interlock"],
                "next_node": "dash_lights",
            },
        ],
    },

    "dash_lights": {
        "question": "Do the dash/instrument panel lights come on when you turn the key to the 'on' position (before starting)?",
        "options": [
            {
                "match": "lights_on_normal",
                "label": "Yes — lights come on normally",
                "deltas": {
                    "battery_voltage_drop": -0.10,
                    "safety_interlock": +0.15,
                    "starter_solenoid": +0.10,
                },
                "eliminate": [],
                "next_node": "safety_interlock_check",
            },
            {
                "match": "lights_dim_or_weak",
                "label": "Lights come on but they are dim or flicker",
                "deltas": {
                    "battery_voltage_drop": +0.25,
                },
                "eliminate": ["safety_interlock", "ecu_controller"],
                "next_node": "battery_age",
            },
            {
                "match": "no_lights",
                "label": "No lights at all",
                "deltas": {
                    "battery_voltage_drop": +0.40,
                },
                "eliminate": ["safety_interlock", "fuel_delivery", "air_in_fuel", "glow_plug_failure", "injector_failure"],
                "next_node": "battery_age",
            },
            {
                "match": "not_sure",
                "label": "Not sure / didn't check",
                "deltas": {},
                "eliminate": [],
                "next_node": "safety_interlock_check",
            },
        ],
    },

    "safety_interlock_check": {
        "question": "Is the operator properly seated, with the machine in neutral (or park), and all access doors/canopy closed?",
        "options": [
            {
                "match": "interlock_ok",
                "label": "Yes — everything is set correctly",
                "deltas": {
                    "safety_interlock": -0.15,
                    "starter_solenoid": +0.10,
                    "fuel_delivery": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "interlock_unsure",
                "label": "Not sure — haven't checked all the interlocks",
                "deltas": {
                    "safety_interlock": +0.20,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "interlock_issue",
                "label": "One of those may not be correct (seat, neutral, door)",
                "deltas": {
                    "safety_interlock": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "fuel_check": {
        "question": "Check the fuel gauge — how much fuel is showing? And do you see any fuel leaking under or around the machine?",
        "options": [
            {
                "match": "fuel_empty_or_low",
                "label": "Gauge shows empty or very low / tank looks empty",
                "deltas": {
                    "fuel_delivery": +0.40,
                },
                "eliminate": ["glow_plug_failure", "injector_failure", "air_in_fuel"],
                "next_node": None,
            },
            {
                "match": "fuel_ok_leak_visible",
                "label": "Fuel level is fine but I see fuel dripping or pooling",
                "deltas": {
                    "fuel_delivery": +0.15,
                    "air_in_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "fuel_ok_no_leak",
                "label": "Fuel level is fine, no visible leaks",
                "deltas": {
                    "air_in_fuel": +0.10,
                    "glow_plug_failure": +0.10,
                    "fuel_shutoff_solenoid": +0.08,
                    "starter_solenoid": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_shutoff_check",
            },
            {
                "match": "not_sure",
                "label": "Not sure / can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_work",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery, and when was it last replaced? (If you don't know, that's fine.)",
        "options": [
            {
                "match": "battery_old_or_unknown",
                "label": "Old (3+ years) or unknown age",
                "deltas": {
                    "battery_voltage_drop": +0.20,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "battery_recent",
                "label": "Replaced within the past year",
                "deltas": {
                    "battery_voltage_drop": -0.10,
                    "starter_solenoid": +0.10,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_work",
            },
        ],
    },

    "cranks_speed": {
        "question": "When the engine cranks over, does it sound normal and fast, or does it seem sluggish?",
        "options": [
            {
                "match": "cranks_fast_normal",
                "label": "Cranks fast and sounds normal",
                "deltas": {
                    "fuel_delivery": +0.10,
                    "air_in_fuel": +0.15,
                    "glow_plug_failure": +0.10,
                    "fuel_shutoff_solenoid": +0.08,
                    "battery_voltage_drop": -0.15,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
            {
                "match": "cranks_sluggish",
                "label": "Cranks slowly or sounds labored",
                "deltas": {
                    "battery_voltage_drop": +0.20,
                    "fuel_delivery": -0.05,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "fuel_shutoff_check": {
        "question": "When you turn the key to the ON position (before pressing start), do you hear a faint click or buzz from the fuel injection pump area? Also — did the engine stop suddenly while it was running, or has it simply never started since you first tried?",
        "options": [
            {
                "match": "no_click_stopped_running",
                "label": "No click heard — AND the engine was running fine then cut out suddenly",
                "deltas": {
                    "fuel_shutoff_solenoid": +0.35,
                    "fuel_delivery": -0.10,
                    "air_in_fuel": -0.10,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "no_click_never_started",
                "label": "No click heard — engine has just never started (no prior run)",
                "deltas": {
                    "fuel_shutoff_solenoid": +0.20,
                    "fuel_delivery": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "click_heard",
                "label": "Yes — heard a click or buzz from the injection pump area",
                "deltas": {
                    "fuel_shutoff_solenoid": -0.20,
                    "air_in_fuel": +0.10,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "not_sure",
                "label": "Not sure / couldn't hear clearly",
                "deltas": {},
                "eliminate": [],
                "next_node": "recent_work",
            },
        ],
    },

    "recent_work": {
        "question": "Was any maintenance or repair done on this machine recently — fuel filters, fuel lines, injectors, or the battery?",
        "options": [
            {
                "match": "work_fuel_system",
                "label": "Yes — fuel system work (filters, lines, injectors, running out of fuel)",
                "deltas": {
                    "air_in_fuel": +0.30,
                    "fuel_delivery": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "work_electrical",
                "label": "Yes — electrical work (battery, alternator, wiring)",
                "deltas": {
                    "battery_voltage_drop": +0.15,
                    "ecu_controller": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_recent_work",
                "label": "No recent work",
                "deltas": {
                    "battery_voltage_drop": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

NO_START_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"battery_voltage_drop": +0.05, "fuel_delivery": +0.05},
        "muddy": {"battery_voltage_drop": +0.05, "starter_solenoid": +0.05},
        "marine": {"battery_voltage_drop": +0.08, "ecu_controller": +0.05},
        "urban": {},
    },
    "hours_band": {
        # Applied when hours_of_operation > last_service_hours + 250
        "overdue_service": {
            "fuel_delivery": +0.12,
            "battery_voltage_drop": +0.08,
        },
        # Applied when storage_duration > 30 days
        "long_storage": {
            "fuel_delivery": +0.15,
            "air_in_fuel": +0.10,
            "battery_voltage_drop": +0.12,
            "glow_plug_failure": +0.05,
        },
    },
    "climate": {
        "cold": {"glow_plug_failure": +0.15, "battery_voltage_drop": +0.10},
        "hot": {"fuel_delivery": +0.05},
    },
}

NO_START_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "After a no-start on diesel equipment, always bleed the fuel system if any fuel lines, filters, or injectors were disturbed — air pockets prevent starting even with good fuel.",
    "Test battery voltage under load (not just open-circuit): a 12.6V resting battery can collapse to 8V under starter current if it has a bad cell.",
    "Check all safety interlocks systematically: seat pressure switch, neutral/park relay, door/canopy switches, and any operator presence systems.",
    "On cold-weather no-starts: allow adequate glow plug warm-up time (indicator light off = ready), and consider block heater use below 40°F / 5°C.",
    "Fuel shutoff solenoid test: with key OFF, disconnect the solenoid connector — you should hear a click as it spring-closes. Reconnect and turn key ON — you should hear another click as it opens. No second click with power applied = solenoid coil failed or no power reaching it.",
]
