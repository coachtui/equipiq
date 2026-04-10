"""
Hydraulic loss diagnostic tree — heavy equipment.

Covers loss of hydraulic pressure or function: slow/no boom movement, bucket
won't curl, travel slow or stopped, implements unresponsive.  This is one of the
most common and consequential failure modes on construction equipment.

Hydraulic loss can mean:
  - Total loss (nothing moves)
  - Partial loss (implements slow or weak)
  - Selective loss (specific circuit dead, others OK)

Safety note: hydraulic line failures under high pressure are immediately dangerous.
The safety layer handles rupture/injection-injury detection before this tree runs.
"""

HYDRAULIC_LOSS_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic fluid (OEM specification)", "notes": "Do NOT mix fluid types — check OEM spec carefully"},
        ],
    },
    "air_in_system": {
        "label": "Air ingested into hydraulic system (cavitation)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "failed_hydraulic_pump": {
        "label": "Failed main hydraulic pump",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Main hydraulic pump", "notes": "Expensive — confirm with pressure test before ordering"},
        ],
    },
    "clogged_filter": {
        "label": "Clogged hydraulic return or suction filter (bypass mode)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic return filter element", "notes": "Change at OEM intervals; bypass indicator should trigger first"},
            {"name": "Hydraulic suction strainer", "notes": "Located inside reservoir — inspect for debris"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "Hydraulic hose or fitting leak (external)",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly (OEM routing)", "notes": "Match pressure rating exactly; use proper crimped fittings"},
        ],
    },
    "control_valve_failure": {
        "label": "Control valve or solenoid valve failure",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Directional control valve", "notes": "Test pilot pressure and electrical signals to solenoids first"},
        ],
    },
    "relief_valve_stuck_open": {
        "label": "Main relief valve stuck open (pressure bleeds off before work is done)",
        "prior": 0.02,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "pilot_solenoid_failure": {
        "label": "Pilot enable solenoid failure — pilot circuit dead, all functions locked out",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot enable solenoid valve", "notes": "Check 12V/24V signal at solenoid connector with key ON and pilot lever activated. No voltage = wiring or controller issue. Voltage but no movement = solenoid coil failed."},
        ],
    },
}

HYDRAULIC_LOSS_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "Which hydraulic functions are affected?",
        "options": [
            {
                "match": "everything_slow_or_dead",
                "label": "Everything is slow or not working — all functions affected",
                "deltas": {
                    "low_fluid": +0.20,
                    "failed_hydraulic_pump": +0.20,
                    "clogged_filter": +0.15,
                    "air_in_system": +0.10,
                    "pilot_solenoid_failure": +0.15,
                    "control_valve_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "fluid_level",
            },
            {
                "match": "one_circuit_dead",
                "label": "One specific function is dead but others work fine",
                "deltas": {
                    "control_valve_failure": +0.30,
                    "leaking_hose_fitting": +0.20,
                    "failed_hydraulic_pump": -0.15,
                    "low_fluid": -0.10,
                    "pilot_solenoid_failure": -0.20,
                },
                "eliminate": ["pilot_solenoid_failure"],
                "next_node": "fluid_level",
            },
            {
                "match": "slow_under_load",
                "label": "Functions work but feel weak or slow, especially under load",
                "deltas": {
                    "clogged_filter": +0.20,
                    "failed_hydraulic_pump": +0.15,
                    "relief_valve_stuck_open": +0.15,
                    "low_fluid": +0.10,
                },
                "eliminate": [],
                "next_node": "fluid_level",
            },
            {
                "match": "jerky_or_spongy",
                "label": "Controls are jerky, spongy, or the machine surges",
                "deltas": {
                    "air_in_system": +0.35,
                    "low_fluid": +0.15,
                    "leaking_hose_fitting": +0.10,
                },
                "eliminate": ["relief_valve_stuck_open"],
                "next_node": "fluid_level",
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic fluid sight glass or dipstick — what does the level show?",
        "options": [
            {
                "match": "fluid_low",
                "label": "Below minimum or I can see it's low",
                "deltas": {
                    "low_fluid": +0.40,
                    "leaking_hose_fitting": +0.15,
                    "air_in_system": +0.10,
                },
                "eliminate": [],
                "next_node": "visible_leak",
            },
            {
                "match": "fluid_ok",
                "label": "Level looks normal — between min and max marks",
                "deltas": {
                    "low_fluid": -0.20,
                    "clogged_filter": +0.10,
                    "failed_hydraulic_pump": +0.10,
                    "pilot_solenoid_failure": +0.08,
                    "control_valve_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "filter_indicator",
            },
            {
                "match": "fluid_overfull",
                "label": "Looks overfull",
                "deltas": {
                    "air_in_system": +0.15,
                },
                "eliminate": ["low_fluid"],
                "next_node": "filter_indicator",
            },
            {
                "match": "cant_check",
                "label": "Can't check right now / not sure how",
                "deltas": {},
                "eliminate": [],
                "next_node": "visible_leak",
            },
        ],
    },

    "visible_leak": {
        "question": "Look underneath the machine and around all hoses and fittings — do you see any hydraulic fluid on the ground or dripping?",
        "options": [
            {
                "match": "leak_visible",
                "label": "Yes — I can see fluid dripping, spraying, or pooling",
                "deltas": {
                    "leaking_hose_fitting": +0.40,
                    "low_fluid": +0.10,
                    "air_in_system": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "no_leak_visible",
                "label": "No visible leak that I can see",
                "deltas": {
                    "leaking_hose_fitting": -0.15,
                    "clogged_filter": +0.10,
                    "failed_hydraulic_pump": +0.10,
                },
                "eliminate": [],
                "next_node": "filter_indicator",
            },
            {
                "match": "not_sure",
                "label": "Not sure — couldn't get a good look",
                "deltas": {},
                "eliminate": [],
                "next_node": "filter_indicator",
            },
        ],
    },

    "filter_indicator": {
        "question": "Does the machine have a hydraulic filter restriction indicator (warning light or bypass indicator on the filter)? If so, is it triggered?",
        "options": [
            {
                "match": "filter_warning_on",
                "label": "Yes — the indicator is lit or triggered",
                "deltas": {
                    "clogged_filter": +0.40,
                    "pilot_solenoid_failure": -0.10,
                },
                "eliminate": [],
                "next_node": "pilot_enable_check",
            },
            {
                "match": "filter_ok",
                "label": "Indicator is not triggered / looks normal",
                "deltas": {
                    "clogged_filter": -0.10,
                    "failed_hydraulic_pump": +0.10,
                },
                "eliminate": [],
                "next_node": "pilot_enable_check",
            },
            {
                "match": "no_indicator_or_unknown",
                "label": "No indicator on this machine / not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "pilot_enable_check",
            },
        ],
    },

    "pilot_enable_check": {
        "question": "Does this machine have a pilot enable lever or switch (sometimes called the safety lock lever, gate lock, or hydraulic enable) that must be activated before the controls work? If so, is it in the active/unlocked position?",
        "options": [
            {
                "match": "pilot_lever_on_still_dead",
                "label": "Yes — the lever/switch is activated, but hydraulics still don't respond",
                "deltas": {
                    "pilot_solenoid_failure": +0.30,
                    "failed_hydraulic_pump": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "pilot_lever_was_off",
                "label": "Found it — the lever or switch was not activated",
                "deltas": {
                    "pilot_solenoid_failure": -0.20,
                    "failed_hydraulic_pump": -0.10,
                    "clogged_filter": -0.10,
                    "low_fluid": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_pilot_system",
                "label": "This machine doesn't have that / I'm not sure",
                "deltas": {
                    "pilot_solenoid_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Did this happen suddenly, or did performance gradually get worse over time?",
        "options": [
            {
                "match": "sudden",
                "label": "Sudden — was working fine, then stopped or dropped sharply",
                "deltas": {
                    "leaking_hose_fitting": +0.15,
                    "failed_hydraulic_pump": +0.15,
                    "control_valve_failure": +0.10,
                    "clogged_filter": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "gradual",
                "label": "Gradual — got slower or weaker over days or weeks",
                "deltas": {
                    "clogged_filter": +0.20,
                    "low_fluid": +0.10,
                    "failed_hydraulic_pump": +0.10,
                    "air_in_system": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "after_maintenance",
                "label": "Started right after maintenance or a filter change",
                "deltas": {
                    "air_in_system": +0.35,
                    "clogged_filter": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HYDRAULIC_LOSS_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"clogged_filter": +0.10, "failed_hydraulic_pump": +0.05},
        "muddy": {"clogged_filter": +0.08, "leaking_hose_fitting": +0.05},
        "marine": {"leaking_hose_fitting": +0.05, "control_valve_failure": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "clogged_filter": +0.15,
            "failed_hydraulic_pump": +0.08,
        },
    },
}

HYDRAULIC_LOSS_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Never work under a raised implement supported only by hydraulics — always use mechanical safety locks or blocks.",
    "Hydraulic fluid at operating pressure (3000–5000 PSI on many machines) can penetrate skin without a visible wound. If you suspect a pinhole leak, use a piece of cardboard to locate it — never use bare hands.",
    "After low fluid: fill slowly, cycle all functions to purge air, then recheck level.",
    "Milky or frothy fluid = water contamination — drain and flush before adding new fluid.",
    "Pilot solenoid check: with key ON and pilot lever activated, test voltage at the solenoid connector. Should read system voltage (12V or 24V). No voltage = trace back through fuse and wiring harness. Voltage present but nothing moves = solenoid coil has failed.",
]
