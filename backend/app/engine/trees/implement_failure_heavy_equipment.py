"""
Implement failure diagnostic tree — heavy equipment.

Covers failure of specific work implements: boom, arm, bucket, blade, forks,
or other attached work tools that fail to move, move incorrectly, or lose
holding force.

This is distinct from the hydraulic_loss tree which covers total or system-wide
hydraulic failure. Implement failure is selective — the machine can travel and
other functions may work, but one specific implement circuit is dead or degraded.

Key differential from hydraulic_loss:
  - hydraulic_loss: everything affected or major system loss
  - implement_failure: specific implement(s) affected, others may work fine
"""

IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "circuit_solenoid": {
        "label": "Implement circuit solenoid or control valve failure (specific function dead)",
        "prior": 0.25,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Solenoid valve for affected circuit", "notes": "Test coil resistance (typically 10–40 ohms) and voltage at connector with key ON"},
        ],
    },
    "hydraulic_cylinder_seal": {
        "label": "Hydraulic cylinder seal failure (drifting under load, won't hold position)",
        "prior": 0.20,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Cylinder seal kit (OEM spec for cylinder bore/rod diameter)", "notes": "Match seals to cylinder bore and operating temperature range"},
        ],
    },
    "joystick_control_fault": {
        "label": "Joystick or pilot control lever fault (electrical or mechanical)",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Joystick/control handle assembly", "notes": "Check for mechanical binding first; test electrical output with multimeter"},
        ],
    },
    "quick_coupler_lock": {
        "label": "Quick coupler not fully engaged or locking pin not seated",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "circuit_hose_leak": {
        "label": "Hydraulic hose on specific implement circuit leaking or blown",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly (match OEM pressure rating)", "notes": "Trace the hose to the affected cylinder — look for wet sections or swelling"},
        ],
    },
    "priority_valve": {
        "label": "Flow priority valve misadjusted or failed — implement starved of flow under load",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "check_valve_failure": {
        "label": "Load-holding check valve failure — implement drifts or drops uncontrolled",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the main symptom with the implement?",
        "options": [
            {
                "match": "wont_move_at_all",
                "label": "The implement won't move at all — no response when I operate the control",
                "deltas": {
                    "circuit_solenoid": +0.25,
                    "joystick_control_fault": +0.20,
                    "quick_coupler_lock": +0.15,
                    "circuit_hose_leak": +0.05,
                    "hydraulic_cylinder_seal": -0.10,
                    "check_valve_failure": -0.10,
                },
                "eliminate": ["check_valve_failure"],
                "next_node": "other_functions",
            },
            {
                "match": "slow_or_weak",
                "label": "Moves but is slow or weak — especially under load",
                "deltas": {
                    "circuit_hose_leak": +0.20,
                    "priority_valve": +0.20,
                    "hydraulic_cylinder_seal": +0.10,
                    "circuit_solenoid": +0.05,
                },
                "eliminate": ["quick_coupler_lock", "check_valve_failure"],
                "next_node": "other_functions",
            },
            {
                "match": "drifts_or_drops",
                "label": "Moves OK but drifts or drops slowly when I release the control",
                "deltas": {
                    "hydraulic_cylinder_seal": +0.30,
                    "check_valve_failure": +0.25,
                    "circuit_hose_leak": +0.10,
                },
                "eliminate": ["joystick_control_fault", "quick_coupler_lock", "circuit_solenoid"],
                "next_node": "other_functions",
            },
            {
                "match": "erratic_or_jerky",
                "label": "Moves but is jerky, surges, or responds differently than expected",
                "deltas": {
                    "joystick_control_fault": +0.25,
                    "circuit_solenoid": +0.15,
                    "priority_valve": +0.10,
                },
                "eliminate": ["check_valve_failure", "quick_coupler_lock"],
                "next_node": "other_functions",
            },
        ],
    },

    "other_functions": {
        "question": "Do other hydraulic functions on the machine (travel, swing, other boom/arm movements) work normally?",
        "options": [
            {
                "match": "others_work_fine",
                "label": "Yes — all other functions work normally",
                "deltas": {
                    "circuit_solenoid": +0.15,
                    "joystick_control_fault": +0.10,
                    "circuit_hose_leak": +0.10,
                    "hydraulic_cylinder_seal": +0.05,
                },
                "eliminate": [],
                "next_node": "quick_coupler_check",
            },
            {
                "match": "others_also_slow",
                "label": "Other functions are also slower than normal",
                "deltas": {
                    "priority_valve": +0.20,
                    "circuit_solenoid": -0.10,
                },
                "eliminate": [],
                "next_node": "quick_coupler_check",
            },
            {
                "match": "not_sure",
                "label": "Not sure / haven't tested other functions",
                "deltas": {},
                "eliminate": [],
                "next_node": "quick_coupler_check",
            },
        ],
    },

    "quick_coupler_check": {
        "question": "Is this machine using a quick coupler or pin-on attachment? If so, is the attachment fully and correctly seated and locked?",
        "options": [
            {
                "match": "quick_coupler_maybe_not_locked",
                "label": "Yes, using a quick coupler — not sure if it's fully locked",
                "deltas": {
                    "quick_coupler_lock": +0.40,
                },
                "eliminate": [],
                "next_node": "visible_check",
            },
            {
                "match": "coupler_confirmed_locked",
                "label": "Yes — coupler is fully seated and locked / pin-on and pins are secure",
                "deltas": {
                    "quick_coupler_lock": -0.20,
                    "circuit_solenoid": +0.10,
                },
                "eliminate": ["quick_coupler_lock"],
                "next_node": "visible_check",
            },
            {
                "match": "no_coupler",
                "label": "No quick coupler on this machine",
                "deltas": {
                    "quick_coupler_lock": -0.30,
                },
                "eliminate": ["quick_coupler_lock"],
                "next_node": "visible_check",
            },
        ],
    },

    "visible_check": {
        "question": "Look at the implement and its hoses — do you see any hydraulic fluid leaking from the cylinder, hoses, or fittings on the affected implement?",
        "options": [
            {
                "match": "oil_on_cylinder",
                "label": "Yes — oil on the cylinder rod or leaking from the cylinder end caps",
                "deltas": {
                    "hydraulic_cylinder_seal": +0.40,
                    "check_valve_failure": +0.05,
                },
                "eliminate": ["circuit_solenoid", "joystick_control_fault"],
                "next_node": None,
            },
            {
                "match": "hose_leak_visible",
                "label": "Yes — leaking from a hose, fitting, or quick-disconnect on the implement",
                "deltas": {
                    "circuit_hose_leak": +0.45,
                },
                "eliminate": ["circuit_solenoid", "joystick_control_fault", "check_valve_failure"],
                "next_node": None,
            },
            {
                "match": "no_visible_leak",
                "label": "No visible leak on the implement",
                "deltas": {
                    "circuit_solenoid": +0.10,
                    "joystick_control_fault": +0.08,
                    "check_valve_failure": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"joystick_control_fault": +0.05, "circuit_hose_leak": +0.05},
        "muddy": {"circuit_hose_leak": +0.08, "quick_coupler_lock": +0.05},
        "marine": {},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "hydraulic_cylinder_seal": +0.10,
            "check_valve_failure": +0.05,
        },
    },
}

IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Quick coupler safety: ALWAYS verify the coupler is fully locked before operating. A partially engaged coupler can release the attachment unexpectedly under load.",
    "Cylinder seal drift test: with implement raised, mark the cylinder rod position with chalk, leave for 10 minutes. If the mark moves, the seal is bypassing.",
    "Solenoid test: with key ON, use a test light or multimeter at the solenoid connector. No voltage = trace back to fuse/relay and controller. Voltage present but no movement = solenoid coil failed.",
    "Load-holding check valves: usually integral to the control valve block. Failure allows implement drift — requires control valve disassembly or block replacement.",
]
