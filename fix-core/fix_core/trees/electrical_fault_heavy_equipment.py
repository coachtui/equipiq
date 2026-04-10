"""
Electrical fault diagnostic tree — heavy equipment.

Covers electrical system failures: instrument panel errors, unexpected shutdowns,
charging system failure, wiring/harness damage (often from jobsite debris, rodents,
or heat), fuse/relay failures, and ECU/controller faults.

Heavy equipment electrical systems are 12V or 24V and are often exposed to harsher
conditions than passenger vehicles: vibration, water ingress, arc-flash from battery
terminals during jump starts, and chafed wiring from undercarriage debris.
"""

ELECTRICAL_FAULT_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "battery_failure": {
        "label": "Battery failure (bad cell, sulfation, or end-of-life)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Heavy-duty battery (match OEM group size and CCA)", "notes": "Test with a load tester — surface voltage is misleading"},
        ],
    },
    "alternator_failure": {
        "label": "Alternator or charging system failure — battery not charging",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Alternator", "notes": "Measure charge voltage at battery terminals at idle: should be 13.8–14.8V (12V system) or 27.6–28.8V (24V system)"},
        ],
    },
    "wiring_harness_damage": {
        "label": "Wiring harness chafing, damage, or rodent damage",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "ground_fault": {
        "label": "Loose or corroded ground strap / ground fault",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Ground strap (battery negative to chassis)", "notes": "Also check engine-to-frame ground — often overlooked"},
        ],
    },
    "fuse_relay_failure": {
        "label": "Blown fuse or failed relay",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuse assortment (match OEM amperage ratings)", "notes": "Replace blown fuses with same amperage only — never use a higher amp fuse"},
        ],
    },
    "ecu_controller_fault": {
        "label": "ECU / machine controller fault or corruption",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "parasitic_drain": {
        "label": "Parasitic drain — something drawing power when machine is off",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [],
    },
}

ELECTRICAL_FAULT_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the main electrical symptom you're seeing?",
        "options": [
            {
                "match": "wont_start_no_power",
                "label": "Machine won't start and has no or very low electrical power",
                "deltas": {
                    "battery_failure": +0.30,
                    "ground_fault": +0.15,
                    "alternator_failure": +0.05,
                },
                "eliminate": ["ecu_controller_fault"],
                "next_node": "charging_voltage",
            },
            {
                "match": "intermittent_shutdowns",
                "label": "Machine shuts off unexpectedly or has intermittent power loss",
                "deltas": {
                    "wiring_harness_damage": +0.20,
                    "ground_fault": +0.20,
                    "fuse_relay_failure": +0.15,
                    "battery_failure": +0.10,
                },
                "eliminate": [],
                "next_node": "fault_codes",
            },
            {
                "match": "fault_codes_on_dash",
                "label": "Fault codes or warning lights on the dash — machine still runs",
                "deltas": {
                    "ecu_controller_fault": +0.25,
                    "wiring_harness_damage": +0.15,
                    "fuse_relay_failure": +0.10,
                },
                "eliminate": ["battery_failure", "alternator_failure"],
                "next_node": "fault_codes",
            },
            {
                "match": "battery_draining",
                "label": "Battery keeps going dead even after charging",
                "deltas": {
                    "parasitic_drain": +0.35,
                    "alternator_failure": +0.25,
                    "battery_failure": +0.20,
                },
                "eliminate": ["ecu_controller_fault", "wiring_harness_damage"],
                "next_node": "charging_voltage",
            },
        ],
    },

    "charging_voltage": {
        "question": "With the engine running, do you have a way to check the battery voltage? (A multimeter or the machine's own voltage gauge.) What does it show?",
        "options": [
            {
                "match": "voltage_low_under14",
                "label": "Below 13.5V (12V system) or below 27V (24V system) — not charging properly",
                "deltas": {
                    "alternator_failure": +0.40,
                },
                "eliminate": ["parasitic_drain"],
                "next_node": "ground_check",
            },
            {
                "match": "voltage_normal",
                "label": "Normal charging voltage (13.8–14.8V on 12V, or 27–29V on 24V)",
                "deltas": {
                    "alternator_failure": -0.20,
                    "battery_failure": +0.15,
                    "parasitic_drain": +0.10,
                },
                "eliminate": [],
                "next_node": "ground_check",
            },
            {
                "match": "cant_check",
                "label": "No way to check voltage right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "ground_check",
            },
        ],
    },

    "fault_codes": {
        "question": "Have you been able to read any fault codes from the machine's control system?",
        "options": [
            {
                "match": "codes_read_electrical",
                "label": "Yes — codes related to wiring, sensors, or communication faults",
                "deltas": {
                    "wiring_harness_damage": +0.25,
                    "ecu_controller_fault": +0.15,
                    "ground_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "ground_check",
            },
            {
                "match": "codes_read_other",
                "label": "Yes — codes present but not clearly electrical",
                "deltas": {
                    "ecu_controller_fault": +0.15,
                },
                "eliminate": [],
                "next_node": "ground_check",
            },
            {
                "match": "no_codes_or_unread",
                "label": "No codes, or couldn't read them",
                "deltas": {
                    "wiring_harness_damage": +0.05,
                    "fuse_relay_failure": +0.10,
                },
                "eliminate": ["ecu_controller_fault"],
                "next_node": "ground_check",
            },
        ],
    },

    "ground_check": {
        "question": "Have the battery terminals and main ground straps been inspected for corrosion or looseness?",
        "options": [
            {
                "match": "corrosion_or_loose_found",
                "label": "Yes — found corrosion, loose connections, or damaged cable ends",
                "deltas": {
                    "ground_fault": +0.40,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "connections_look_ok",
                "label": "Checked — connections look tight and clean",
                "deltas": {
                    "ground_fault": -0.15,
                    "alternator_failure": +0.05,
                    "wiring_harness_damage": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "not_checked",
                "label": "Haven't checked the connections yet",
                "deltas": {
                    "ground_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
        ],
    },

    "recent_work": {
        "question": "Was any electrical work done recently — jump starting, battery replacement, or wiring repairs?",
        "options": [
            {
                "match": "jump_started",
                "label": "Yes — machine was jump started recently",
                "deltas": {
                    "battery_failure": +0.15,
                    "ecu_controller_fault": +0.10,
                    "alternator_failure": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "wiring_work",
                "label": "Yes — wiring, harness, or controller work was done",
                "deltas": {
                    "wiring_harness_damage": +0.20,
                    "ground_fault": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_recent_work",
                "label": "No recent electrical work",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ELECTRICAL_FAULT_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"wiring_harness_damage": +0.05, "ground_fault": +0.05},
        "muddy": {"ground_fault": +0.08, "wiring_harness_damage": +0.08},
        "marine": {"battery_failure": +0.10, "ground_fault": +0.10, "alternator_failure": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "battery_failure": +0.10,
            "alternator_failure": +0.05,
        },
        "long_storage": {
            "battery_failure": +0.20,
            "parasitic_drain": +0.05,
        },
    },
}

ELECTRICAL_FAULT_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Before replacing a battery, test it under load — a battery showing 12.5V open-circuit can drop to 8V under starter current if it has a bad cell.",
    "On 24V systems: two 12V batteries in series — if one cell is bad, both batteries are affected. Test each battery individually.",
    "After any wiring repair, use dielectric grease on all connectors to prevent moisture ingress and corrosion.",
    "Jump starting with reversed polarity can destroy the ECU and alternator in seconds — always double-check polarity before connecting cables.",
]
