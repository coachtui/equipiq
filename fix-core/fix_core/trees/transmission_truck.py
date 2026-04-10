"""
Transmission diagnostic tree — truck/HD variant.

Key differences from base car tree:
- Allison 1000/2000/3000 automatics common on 3/4-ton and 1-ton HD trucks
- 6-speed manuals (ZF6, NV4500, G56) common on older HD diesel trucks
- Transfer case issues unique to 4WD/AWD trucks
- PTO (power take-off) engagement faults on work trucks
- Diesel engine torque demands cause faster ATF degradation
- Towing and heavy-load stress distinguishes HD truck failure modes
"""

TRANSMISSION_TRUCK_HYPOTHESES: dict[str, dict] = {
    "fluid_low_degraded": {
        "label": "Low or degraded transmission fluid (HD trucks degrade ATF faster under tow loads)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "ATF (correct spec — Allison TES-295/TES-389, Dexron HP, or as specified)", "notes": "HD trucks often require specific fluid — wrong spec causes shift quality issues and solenoid damage"},
            {"name": "Transmission filter kit", "notes": "Allison transmissions have an external spin-on filter that is easy to service"},
        ],
    },
    "solenoid_fault": {
        "label": "Shift solenoid or valve body fault (stuck gear, erratic shifts, P07xx codes)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Shift solenoid pack", "notes": "Allison transmissions have internal solenoid packs — requires pan removal; scan for specific P07xx code first"},
        ],
    },
    "transfer_case": {
        "label": "Transfer case fault (4WD not engaging, grinding on shift, stuck in 4WD, binding)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transfer case fluid (correct type per label — NV271/273, BorgWarner)", "notes": "Low fluid is the most common fixable cause; drain plug is often under the truck"},
            {"name": "Transfer case shift motor / encoder", "notes": "Electronic shift systems fail more often than mechanical — scan for U/C codes before mechanical teardown"},
        ],
    },
    "torque_converter": {
        "label": "Torque converter failure or lock-up clutch (shudder at cruise, no lockup under load)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Torque converter", "notes": "Towing stress accelerates TCC wear — transmission removal required; replace fluid and filter at the same time"},
        ],
    },
    "clutch_worn": {
        "label": "Worn clutch disc or pressure plate — manual transmission only (ZF6, NV4500, G56)",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Heavy-duty clutch kit (disc, pressure plate, throw-out bearing)", "notes": "HD diesel trucks need HD-rated clutch kits — standard light-duty clutches won't survive diesel torque"},
            {"name": "Flywheel resurfacing or dual-mass flywheel replacement", "notes": "Dual-mass flywheels are common on modern diesels; inspect for excessive play before resurfacing"},
        ],
    },
    "band_or_clutch_pack": {
        "label": "Worn internal clutch pack (slipping in specific range — common under heavy tow loads)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission rebuild kit", "notes": "Allison transmissions have a defined service rebuild interval — common on high-tow-mileage trucks"},
        ],
    },
    "pto_fault": {
        "label": "PTO (power take-off) engagement fault (work truck — hydraulic pump, aerial lift, etc.)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "PTO unit", "notes": "Check fluid in PTO separately from main transmission fluid; PTO gears can seize if underfilled"},
        ],
    },
    "cooler_line_blocked": {
        "label": "Blocked transmission cooler or line (thermal protection limp mode under tow load)",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "HD transmission cooler (add-on)", "notes": "Highly recommended for towing — back-flush existing cooler before installing"},
        ],
    },
}

TRANSMISSION_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the transmission do that seems wrong?",
        "options": [
            {
                "match": "slipping",
                "label": "Slipping — engine revs up but truck doesn't accelerate, especially under load",
                "deltas": {
                    "fluid_low_degraded": +0.15,
                    "band_or_clutch_pack": +0.15,
                    "torque_converter": +0.10,
                    "clutch_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "4wd_issue",
                "label": "4WD won't engage or disengage, grinding on shift, or binding when turning",
                "deltas": {
                    "transfer_case": +0.55,
                    "pto_fault": -0.10,
                    "solenoid_fault": -0.05,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "harsh_shifts",
                "label": "Harsh, clunky, or erratic shifts",
                "deltas": {
                    "fluid_low_degraded": +0.18,
                    "solenoid_fault": +0.15,
                    "torque_converter": +0.08,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "limp_mode",
                "label": "Stuck in one gear / limp mode — transmission warning light on",
                "deltas": {
                    "solenoid_fault": +0.25,
                    "fluid_low_degraded": +0.10,
                    "cooler_line_blocked": +0.10,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "pto_issue",
                "label": "PTO won't engage or disengages under load (work truck)",
                "deltas": {
                    "pto_fault": +0.55,
                    "fluid_low_degraded": +0.10,
                    "transfer_case": -0.10,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
        ],
    },

    "trans_type": {
        "question": "What type of transmission does this truck have?",
        "options": [
            {
                "match": "allison_auto",
                "label": "Allison automatic (common on HD trucks and vans — 6-speed Allison)",
                "deltas": {
                    "clutch_worn": -0.30,
                    "solenoid_fault": +0.08,
                    "fluid_low_degraded": +0.05,
                },
                "eliminate": [],
                "next_node": "tow_context",
            },
            {
                "match": "other_auto",
                "label": "Other automatic (68RFE, 10R140, GM 8L90, etc.)",
                "deltas": {
                    "clutch_worn": -0.25,
                    "torque_converter": +0.05,
                },
                "eliminate": [],
                "next_node": "tow_context",
            },
            {
                "match": "manual",
                "label": "Manual (stick shift — ZF6, NV4500, G56, or similar)",
                "deltas": {
                    "clutch_worn": +0.30,
                    "torque_converter": -0.30,
                    "solenoid_fault": -0.20,
                    "cooler_line_blocked": -0.15,
                    "pto_fault": -0.05,
                },
                "eliminate": [],
                "next_node": "tow_context",
            },
        ],
    },

    "tow_context": {
        "question": "Does the problem occur or get worse when towing or under heavy load?",
        "options": [
            {
                "match": "worse_under_load",
                "label": "Yes — much worse when towing or on grades",
                "deltas": {
                    "cooler_line_blocked": +0.20,
                    "fluid_low_degraded": +0.10,
                    "band_or_clutch_pack": +0.10,
                    "torque_converter": +0.08,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "no_load_diff",
                "label": "Same regardless of load",
                "deltas": {
                    "solenoid_fault": +0.08,
                    "fluid_low_degraded": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the transmission fluid (dipstick or Allison fill port). What is the level and condition?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and red/pink — clean, no burned smell",
                "deltas": {
                    "fluid_low_degraded": -0.25,
                    "solenoid_fault": +0.08,
                    "band_or_clutch_pack": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dark_burned",
                "label": "Dark brown or black, or smells burned",
                "deltas": {
                    "fluid_low_degraded": +0.25,
                    "band_or_clutch_pack": +0.15,
                    "cooler_line_blocked": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "fluid_low_degraded": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_TRUCK_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "fluid_low_degraded": +0.08,
            "band_or_clutch_pack": +0.08,
            "torque_converter": +0.06,
            "clutch_worn": +0.06,
        },
    },
    "usage_pattern": {
        "highway": {
            "cooler_line_blocked": +0.08,
            "torque_converter": +0.05,
        },
    },
    "awd_4wd": {
        "yes": {
            "transfer_case": +0.12,
        },
    },
    "transmission_type": {
        "manual": {
            "clutch_worn": +0.20,
            "torque_converter": -0.20,
            "solenoid_fault": -0.15,
        },
    },
}

TRANSMISSION_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After any Allison transmission service, perform a throttle position reset and allow the TCM to relearn shift points — Allison adaptive shift tables take 50–100 miles to fully recalibrate after a fluid change.",
    "If a transfer case fault was found, check the front driveshaft U-joints and slip yoke while you have things apart — worn U-joints cause the transfer case to work harder and can be mistaken for transfer case binding.",
    "For high-mileage diesel trucks used for towing, add an external transmission cooler if not already equipped — the factory cooler in the radiator end tank is marginal for sustained towing.",
]
