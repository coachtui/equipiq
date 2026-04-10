"""
Loss-of-power diagnostic tree.

"Loss of power" = engine runs but feels weak, sluggish, hesitates, or is
clearly limited. Covers both sudden and gradual onset.

The "all dashboard lights + random errors" pattern is treated as a first-class
signal — it strongly points to alternator/charging failure or a CAN bus fault
rather than a purely mechanical power loss.
"""

LOSS_OF_POWER_HYPOTHESES: dict[str, dict] = {
    "alternator_failure": {
        "label": "Failing or failed alternator (voltage drop triggering warning cascade)",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Alternator", "notes": "Test charging voltage first — should read 13.8–14.8V at idle"},
            {"name": "Serpentine belt", "notes": "Inspect if alternator is being replaced"},
        ],
    },
    "limp_mode_transmission": {
        "label": "Transmission limp mode (TCM limiting gears to protect drivetrain)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "limp_mode_engine": {
        "label": "Engine limp mode (ECU limiting power due to sensor fault or overheating)",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "maf_map_sensor": {
        "label": "Dirty or failed MAF/MAP sensor (incorrect air/fuel calculation)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "MAF sensor cleaner spray", "notes": "Try cleaning first before replacing"},
            {"name": "MAF sensor", "notes": "Replace if cleaning doesn't resolve — check for P0100–P0103"},
        ],
    },
    "catalytic_converter": {
        "label": "Clogged catalytic converter (exhaust restriction reducing power)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Catalytic converter", "notes": "Confirm with back-pressure test before replacing"},
        ],
    },
    "throttle_body_tps": {
        "label": "Dirty throttle body or faulty throttle position sensor (TPS)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Throttle body cleaner", "notes": "Clean throttle body first; reset idle after"},
            {"name": "Throttle position sensor", "notes": "Check for P0120–P0124 codes"},
        ],
    },
    "fuel_delivery_partial": {
        "label": "Weak fuel pump or partially clogged injectors",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel pressure gauge (test tool)", "notes": "Confirm low pressure before replacing pump"},
            {"name": "Fuel injector cleaner", "notes": "Add to tank as first step for injector issues"},
        ],
    },
    "vtc_actuator": {
        "label": "Variable valve timing actuator fault (common on Honda V6 engines)",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "VTC actuator", "notes": "Often presents with rattle on startup + power loss; check P0341"},
        ],
    },
    "canbus_ecu_fault": {
        "label": "CAN bus communication error or ECU/module fault",
        "prior": 0.02,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

LOSS_OF_POWER_TREE: dict[str, dict] = {
    "start": {
        "question": "Did all dashboard warning lights come on at the same time, or only specific warning lights?",
        "options": [
            {
                "match": "all_lights_on",
                "label": "All or most dashboard lights came on at once",
                "deltas": {
                    "alternator_failure": +0.30,
                    "canbus_ecu_fault": +0.15,
                    "limp_mode_engine": +0.05,
                    "limp_mode_transmission": -0.05,
                    "catalytic_converter": -0.10,
                    "fuel_delivery_partial": -0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "specific_lights",
                "label": "Only specific warning lights (check engine, transmission, etc.)",
                "deltas": {
                    "limp_mode_engine": +0.15,
                    "limp_mode_transmission": +0.10,
                    "maf_map_sensor": +0.10,
                    "throttle_body_tps": +0.05,
                    "alternator_failure": -0.15,
                    "canbus_ecu_fault": -0.10,
                },
                "eliminate": [],
                "next_node": "which_light",
            },
            {
                "match": "no_lights",
                "label": "No warning lights on",
                "deltas": {
                    "catalytic_converter": +0.15,
                    "fuel_delivery_partial": +0.15,
                    "maf_map_sensor": +0.05,
                    "alternator_failure": -0.20,
                    "canbus_ecu_fault": -0.15,
                    "limp_mode_engine": -0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
        ],
    },

    "which_light": {
        "question": "Which warning light is most prominent — check engine, transmission, battery/charging, or temperature?",
        "options": [
            {
                "match": "light_check_engine",
                "label": "Check engine light (CEL)",
                "deltas": {
                    "maf_map_sensor": +0.15,
                    "throttle_body_tps": +0.10,
                    "vtc_actuator": +0.10,
                    "limp_mode_engine": +0.10,
                    "catalytic_converter": +0.05,
                },
                "eliminate": ["alternator_failure", "canbus_ecu_fault"],
                "next_node": "onset",
            },
            {
                "match": "light_transmission",
                "label": "Transmission warning light",
                "deltas": {
                    "limp_mode_transmission": +0.35,
                    "limp_mode_engine": -0.05,
                },
                "eliminate": ["alternator_failure", "catalytic_converter", "fuel_delivery_partial"],
                "next_node": "onset",
            },
            {
                "match": "light_battery",
                "label": "Battery or charging warning light",
                "deltas": {
                    "alternator_failure": +0.35,
                    "canbus_ecu_fault": +0.05,
                },
                "eliminate": ["limp_mode_transmission", "catalytic_converter"],
                "next_node": "onset",
            },
            {
                "match": "light_temperature",
                "label": "Temperature warning (overheating)",
                "deltas": {
                    "limp_mode_engine": +0.35,
                },
                "eliminate": ["alternator_failure", "maf_map_sensor", "catalytic_converter"],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Did the power loss come on suddenly while driving, or has it been gradually getting worse over days or weeks?",
        "options": [
            {
                "match": "sudden",
                "label": "Sudden — happened all at once while driving",
                "deltas": {
                    "alternator_failure": +0.15,
                    "limp_mode_transmission": +0.10,
                    "limp_mode_engine": +0.10,
                    "canbus_ecu_fault": +0.10,
                    "catalytic_converter": -0.10,
                    "fuel_delivery_partial": -0.05,
                },
                "eliminate": [],
                "next_node": "speed_behavior",
            },
            {
                "match": "gradual",
                "label": "Gradual — slowly getting worse over time",
                "deltas": {
                    "catalytic_converter": +0.15,
                    "fuel_delivery_partial": +0.15,
                    "maf_map_sensor": +0.10,
                    "throttle_body_tps": +0.05,
                    "alternator_failure": -0.10,
                    "limp_mode_transmission": -0.05,
                    "canbus_ecu_fault": -0.10,
                },
                "eliminate": [],
                "next_node": "speed_behavior",
            },
        ],
    },

    "speed_behavior": {
        "question": "Is the car limited to a specific speed or RPM, or does power just feel weak across the board?",
        "options": [
            {
                "match": "hard_limit",
                "label": "Hard limit — stuck at low speed (30–40 mph) or won't rev past a point",
                "deltas": {
                    "limp_mode_transmission": +0.25,
                    "limp_mode_engine": +0.20,
                    "alternator_failure": +0.05,
                    "catalytic_converter": -0.10,
                    "maf_map_sensor": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_economy",
            },
            {
                "match": "generally_weak",
                "label": "Generally weak — accelerates but feels slow and sluggish",
                "deltas": {
                    "catalytic_converter": +0.10,
                    "fuel_delivery_partial": +0.10,
                    "maf_map_sensor": +0.10,
                    "throttle_body_tps": +0.05,
                    "limp_mode_transmission": -0.10,
                },
                "eliminate": [],
                "next_node": "fuel_economy",
            },
            {
                "match": "hesitation_acceleration",
                "label": "Hesitates or stumbles mainly under acceleration",
                "deltas": {
                    "throttle_body_tps": +0.15,
                    "maf_map_sensor": +0.15,
                    "fuel_delivery_partial": +0.10,
                    "vtc_actuator": +0.05,
                    "limp_mode_transmission": -0.10,
                    "alternator_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_economy",
            },
        ],
    },

    "fuel_economy": {
        "question": "Has your fuel economy (MPG) dropped noticeably alongside the power loss?",
        "options": [
            {
                "match": "mpg_much_worse",
                "label": "Yes — noticeably worse fuel economy, filling up more often",
                "deltas": {
                    "catalytic_converter": +0.15,
                    "maf_map_sensor": +0.15,
                    "fuel_delivery_partial": +0.10,
                    "limp_mode_transmission": -0.10,
                    "alternator_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "acceleration_profile",
            },
            {
                "match": "mpg_slightly",
                "label": "Maybe slightly worse, hard to tell",
                "deltas": {
                    "maf_map_sensor": +0.05,
                    "throttle_body_tps": +0.05,
                },
                "eliminate": [],
                "next_node": "acceleration_profile",
            },
            {
                "match": "mpg_normal",
                "label": "No — fuel economy seems unchanged",
                "deltas": {
                    "limp_mode_transmission": +0.10,
                    "limp_mode_engine": +0.10,
                    "alternator_failure": +0.05,
                    "catalytic_converter": -0.10,
                    "fuel_delivery_partial": -0.05,
                },
                "eliminate": [],
                "next_node": "acceleration_profile",
            },
        ],
    },

    "acceleration_profile": {
        "question": "Where does the power loss feel worst — getting moving from a stop, in the mid-range while cruising, or only at higher speeds?",
        "options": [
            {
                "match": "off_the_line",
                "label": "Worst getting moving — sluggish off the line from a stop",
                "deltas": {
                    "throttle_body_tps": +0.15,
                    "fuel_delivery_partial": +0.15,
                    "maf_map_sensor": +0.10,
                    "limp_mode_transmission": +0.10,
                    "catalytic_converter": -0.05,
                    "vtc_actuator": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "mid_range",
                "label": "Worst in the mid-range — weak between 30–60 mph",
                "deltas": {
                    "catalytic_converter": +0.15,
                    "maf_map_sensor": +0.10,
                    "fuel_delivery_partial": +0.10,
                    "limp_mode_engine": +0.05,
                    "throttle_body_tps": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "top_end",
                "label": "Only at highway speeds or high RPM — low-speed power is fine",
                "deltas": {
                    "catalytic_converter": +0.20,
                    "vtc_actuator": +0.15,
                    "maf_map_sensor": +0.05,
                    "limp_mode_transmission": -0.10,
                    "fuel_delivery_partial": +0.05,
                    "throttle_body_tps": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"catalytic_converter": +0.06, "throttle_body_tps": +0.04},
        "cold": {"maf_map_sensor": +0.06},
    },
    "mileage_band": {
        "high": {"catalytic_converter": +0.10, "fuel_delivery_partial": +0.08, "vtc_actuator": +0.06},
    },
    "usage_pattern": {
        "city": {"catalytic_converter": +0.08, "fuel_delivery_partial": +0.04},
    },
}

LOSS_OF_POWER_POST_DIAGNOSIS: list[str] = [
    "After repair, clear any stored DTCs and drive a full warm-up cycle to confirm the issue does not return.",
    "If a catalytic converter was identified, check upstream O2 sensor readings — a failed O2 sensor can cause the converter to be replaced unnecessarily.",
]
