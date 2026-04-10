"""
Strange noise diagnostic tree.

"Strange noise" = unusual engine or drivetrain noise that wasn't there before.
Covers knocking, ticking, squealing, grinding, rattling, hissing, and similar.
Framed generically to cover cars, trucks, boats, generators, and other engines.
"""

STRANGE_NOISE_HYPOTHESES: dict[str, dict] = {
    "rod_bearing": {
        "label": "Spun or worn rod bearing (deep engine knock — serious)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Oil pressure gauge", "notes": "Check oil pressure immediately; low pressure = stop engine now"},
        ],
    },
    "low_oil_pressure": {
        "label": "Low oil pressure (worn main bearings, oil pump, or low oil level)",
        "prior": 0.13,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Oil pressure gauge", "notes": "Mechanical test is more reliable than dash gauge"},
            {"name": "Engine oil + filter", "notes": "Check and top off first; if already full, suspect pump or bearings"},
        ],
    },
    "valve_train": {
        "label": "Valve train noise — worn lifters, rocker arms, or low oil to valvetrain",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Engine oil (correct viscosity)", "notes": "Ensure oil is full and fresh; thick-ish tick at startup is often starved lifters"},
            {"name": "Lifter / valve cover gasket", "notes": "If tick persists after oil change, inspect valve cover area"},
        ],
    },
    "exhaust_leak": {
        "label": "Exhaust manifold leak or cracked header (ticking/tapping, worse when cold)",
        "prior": 0.13,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust manifold gasket", "notes": "Common on high-mileage engines; listen near manifold when cold"},
            {"name": "Exhaust stud / bolt kit", "notes": "Studs often snap on removal — have extras on hand"},
        ],
    },
    "belt_or_pulley": {
        "label": "Worn serpentine belt, tensioner, or accessory pulley bearing (squeal/chirp)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Serpentine belt", "notes": "Inspect for glazing, cracks, and correct tension"},
            {"name": "Belt tensioner / idler pulley", "notes": "Spin each pulley by hand with belt off — rough = replace"},
        ],
    },
    "detonation_knock": {
        "label": "Detonation / pinging (pre-ignition knock under load, often fuel-related)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Higher-octane fuel", "notes": "Try premium if noise is knock under acceleration"},
            {"name": "Fuel system cleaner", "notes": "Carbon deposits in combustion chamber can cause detonation"},
        ],
    },
    "heat_shield_rattle": {
        "label": "Loose heat shield or exhaust component rattle",
        "prior": 0.09,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Heat shield clamp / exhaust hanger", "notes": "Often fixable with a clamp — confirm by tapping exhaust while looking underneath"},
        ],
    },
    "vtc_timing_chain": {
        "label": "VTC actuator rattle or stretched timing chain (startup rattle, then quiets)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Timing chain kit", "notes": "If rattle only at cold startup and disappears quickly, suspect VTC/timing chain stretch"},
        ],
    },
    "coolant_or_steam": {
        "label": "Coolant boil-over or steam (hissing from overheated cooling system)",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Coolant / antifreeze", "notes": "NEVER open a hot radiator cap. Let cool 30+ min first."},
            {"name": "Pressure test kit", "notes": "Find leaks in hoses, radiator, or head gasket"},
        ],
    },
}

STRANGE_NOISE_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you best describe the noise — knocking or thumping, ticking or tapping, squealing or chirping, hissing, or rattling?",
        "options": [
            {
                "match": "knock_thump",
                "label": "Knocking or thumping — a heavy, rhythmic thud",
                "deltas": {
                    "rod_bearing": +0.30,
                    "low_oil_pressure": +0.20,
                    "detonation_knock": +0.15,
                    "vtc_timing_chain": +0.05,
                    "belt_or_pulley": -0.10,
                    "heat_shield_rattle": -0.10,
                    "coolant_or_steam": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "tick_tap",
                "label": "Ticking or tapping — rapid, lighter metallic sound",
                "deltas": {
                    "valve_train": +0.25,
                    "exhaust_leak": +0.20,
                    "vtc_timing_chain": +0.10,
                    "low_oil_pressure": +0.05,
                    "rod_bearing": -0.05,
                    "detonation_knock": -0.05,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "squeal_chirp",
                "label": "Squealing, chirping, or screeching",
                "deltas": {
                    "belt_or_pulley": +0.40,
                    "rod_bearing": -0.10,
                    "low_oil_pressure": -0.10,
                    "valve_train": -0.10,
                    "heat_shield_rattle": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "hiss",
                "label": "Hissing or sizzling",
                "deltas": {
                    "coolant_or_steam": +0.40,
                    "exhaust_leak": +0.15,
                    "rod_bearing": -0.15,
                    "belt_or_pulley": -0.15,
                    "vtc_timing_chain": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "rattle",
                "label": "Rattling or clattering — loose or vibrating sound",
                "deltas": {
                    "heat_shield_rattle": +0.30,
                    "vtc_timing_chain": +0.20,
                    "valve_train": +0.10,
                    "rod_bearing": -0.05,
                    "belt_or_pulley": +0.05,
                    "coolant_or_steam": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
        ],
    },

    "when_noise": {
        "question": "When does the noise occur — at startup only, at idle, under acceleration/load, or constantly?",
        "options": [
            {
                "match": "startup_only",
                "label": "Only at startup, then goes away after a few seconds",
                "deltas": {
                    "vtc_timing_chain": +0.30,
                    "valve_train": +0.20,
                    "low_oil_pressure": +0.10,
                    "rod_bearing": -0.10,
                    "belt_or_pulley": -0.10,
                    "detonation_knock": -0.15,
                    "heat_shield_rattle": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
            {
                "match": "at_idle",
                "label": "Present at idle, consistent",
                "deltas": {
                    "exhaust_leak": +0.15,
                    "valve_train": +0.10,
                    "rod_bearing": +0.10,
                    "low_oil_pressure": +0.10,
                    "belt_or_pulley": +0.05,
                    "detonation_knock": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
            {
                "match": "under_load",
                "label": "Mainly under acceleration or load",
                "deltas": {
                    "detonation_knock": +0.30,
                    "rod_bearing": +0.15,
                    "low_oil_pressure": +0.10,
                    "belt_or_pulley": +0.05,
                    "exhaust_leak": +0.05,
                    "vtc_timing_chain": -0.10,
                    "heat_shield_rattle": -0.05,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
            {
                "match": "constant",
                "label": "Constant — present at all RPMs and conditions",
                "deltas": {
                    "belt_or_pulley": +0.15,
                    "rod_bearing": +0.10,
                    "low_oil_pressure": +0.10,
                    "exhaust_leak": +0.05,
                    "heat_shield_rattle": +0.10,
                    "vtc_timing_chain": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_level",
            },
        ],
    },

    "oil_level": {
        "question": "Have you checked the oil level and condition recently? Is it full, low, or dirty?",
        "options": [
            {
                "match": "oil_low",
                "label": "Low on oil",
                "deltas": {
                    "low_oil_pressure": +0.30,
                    "valve_train": +0.20,
                    "rod_bearing": +0.15,
                    "vtc_timing_chain": +0.10,
                },
                "eliminate": [],
                "next_node": "rpm_dependence",
            },
            {
                "match": "oil_full_dirty",
                "label": "Full but dirty / overdue for a change",
                "deltas": {
                    "valve_train": +0.15,
                    "low_oil_pressure": +0.10,
                    "vtc_timing_chain": +0.05,
                    "detonation_knock": +0.05,
                },
                "eliminate": [],
                "next_node": "rpm_dependence",
            },
            {
                "match": "oil_full_clean",
                "label": "Full and clean / recently changed",
                "deltas": {
                    "exhaust_leak": +0.10,
                    "belt_or_pulley": +0.10,
                    "rod_bearing": +0.05,
                    "low_oil_pressure": -0.10,
                    "valve_train": -0.05,
                },
                "eliminate": [],
                "next_node": "rpm_dependence",
            },
        ],
    },

    "rpm_dependence": {
        "question": "Does the noise change with engine RPM — does it get louder or faster as RPM rises, stay the same at all RPMs, or appear only in a specific RPM range?",
        "options": [
            {
                "match": "tracks_rpm",
                "label": "Gets louder or faster as RPM increases — tracks engine speed",
                "deltas": {
                    "rod_bearing": +0.20,
                    "belt_or_pulley": +0.15,
                    "low_oil_pressure": +0.10,
                    "valve_train": +0.10,
                    "heat_shield_rattle": -0.10,
                    "exhaust_leak": -0.05,
                },
                "eliminate": [],
                "next_node": "load_dependence",
            },
            {
                "match": "same_all_rpm",
                "label": "Same noise at all RPMs — doesn't change with engine speed",
                "deltas": {
                    "exhaust_leak": +0.15,
                    "heat_shield_rattle": +0.15,
                    "coolant_or_steam": +0.10,
                    "rod_bearing": -0.10,
                    "belt_or_pulley": -0.05,
                    "vtc_timing_chain": -0.10,
                },
                "eliminate": [],
                "next_node": "load_dependence",
            },
            {
                "match": "specific_rpm_range",
                "label": "Only at a specific RPM range, then disappears above or below it",
                "deltas": {
                    "vtc_timing_chain": +0.20,
                    "detonation_knock": +0.15,
                    "belt_or_pulley": +0.10,
                    "rod_bearing": -0.05,
                    "exhaust_leak": -0.05,
                    "heat_shield_rattle": -0.05,
                },
                "eliminate": [],
                "next_node": "load_dependence",
            },
        ],
    },

    "load_dependence": {
        "question": "Is the noise worse under load — when accelerating or climbing — compared to coasting or idling?",
        "options": [
            {
                "match": "worse_under_load",
                "label": "Definitely worse under acceleration or load",
                "deltas": {
                    "detonation_knock": +0.25,
                    "rod_bearing": +0.20,
                    "low_oil_pressure": +0.10,
                    "heat_shield_rattle": -0.10,
                    "vtc_timing_chain": -0.10,
                    "belt_or_pulley": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "same_under_load",
                "label": "About the same — not affected by load",
                "deltas": {
                    "belt_or_pulley": +0.10,
                    "exhaust_leak": +0.10,
                    "heat_shield_rattle": +0.10,
                    "detonation_knock": -0.15,
                    "rod_bearing": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "worse_coasting",
                "label": "Worse when coasting or decelerating, not under power",
                "deltas": {
                    "exhaust_leak": +0.15,
                    "vtc_timing_chain": +0.10,
                    "heat_shield_rattle": +0.05,
                    "rod_bearing": -0.10,
                    "detonation_knock": -0.15,
                    "belt_or_pulley": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"valve_train": +0.06, "vtc_timing_chain": +0.06},
        "hot": {"detonation_knock": +0.06},
    },
    "mileage_band": {
        "high": {"rod_bearing": +0.08, "vtc_timing_chain": +0.08, "belt_or_pulley": +0.06},
    },
    "usage_pattern": {
        "highway": {"vtc_timing_chain": +0.04},
        "city": {"heat_shield_rattle": +0.06},
    },
}

STRANGE_NOISE_POST_DIAGNOSIS: list[str] = [
    "After diagnosis, check engine oil level and condition before returning to service — most noise causes are accelerated by low or degraded oil.",
    "If a timing chain or belt noise was suspected, verify tensioner and guides while the cover is off — replacing just one component is a false economy.",
]
