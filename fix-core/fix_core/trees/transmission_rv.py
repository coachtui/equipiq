"""
Transmission diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Class A diesel pushers commonly use Allison 3000 or 4000 series automatics
- Class A gas and Class C (Ford, Chevy, Ram) use truck-style automatics (6R140,
  68RFE, Allison 1000)
- Adaptive shift tables on Allison units require relearn after fluid change
- Towing a dinghy (toad) increases transmission load and thermal stress significantly
- High GVW means ATF degrades faster than in passenger vehicles
- Transmission range selector (PRND) issues on coach-style shift levers
"""

TRANSMISSION_RV_HYPOTHESES: dict[str, dict] = {
    "fluid_low_degraded": {
        "label": "Low or degraded ATF (RV transmissions degrade fluid fast under weight and towing load)",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "ATF (Allison TES-295/TES-389 for Allison units; Dexron HP or manufacturer spec for others)", "notes": "Confirm spec from transmission data plate or owner's manual — wrong fluid spec causes solenoid damage on Allison units"},
            {"name": "Transmission filter", "notes": "Allison units have an external spin-on filter — replace at every fluid change; internal filter on other units requires pan drop"},
        ],
    },
    "solenoid_fault": {
        "label": "Shift solenoid or valve body fault (stuck in gear, erratic shifts, P07xx codes)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Shift solenoid pack", "notes": "Allison 3000/4000 solenoid packs — scan for specific P07xx codes before condemning; wrong ATF spec is a common cause of solenoid failure"},
        ],
    },
    "torque_converter": {
        "label": "Torque converter lock-up clutch failure (shudder at highway speeds, no TCC lockup under load)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Torque converter", "notes": "RV GVW accelerates TCC wear — shudder at 45-55 mph when the converter should be locking is the telltale sign; transmission removal required"},
        ],
    },
    "adaptive_shift_relearn": {
        "label": "Allison adaptive shift table needs relearn (harsh or hunting shifts after fluid change or battery disconnect)",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — relearn procedure only", "notes": "Drive 50–100 miles including highway segments; Allison TCM relearns shift points based on actual throttle/load patterns; avoid towing during relearn period"},
        ],
    },
    "cooler_line_blocked": {
        "label": "Blocked transmission cooler or line (thermal protection limp mode — especially on grades or with toad attached)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "HD transmission cooler (add-on or replacement)", "notes": "RV factory coolers are marginal for sustained towing — back-flush before replacing; an add-on cooler is strongly recommended for towing use"},
        ],
    },
    "range_selector_fault": {
        "label": "Coach-style range selector or shift module fault (won't select range, stuck in park)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Allison shift selector / push-button module", "notes": "Coach-style RVs often use a Allison push-button or rocker selector — scan for U-codes (communication faults) before condemning the selector itself"},
        ],
    },
    "band_or_clutch_pack": {
        "label": "Worn internal clutch pack (slipping in specific range — high-mileage RV)",
        "prior": 0.09,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission rebuild kit", "notes": "Allison 3000/4000 have a defined rebuild interval based on service hours — common on high-tow-mileage coaches"},
        ],
    },
}

TRANSMISSION_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the RV transmission do that seems wrong?",
        "options": [
            {
                "match": "harsh_shifts",
                "label": "Harsh, clunky, or hunting shifts (including after a fluid change or battery disconnect)",
                "deltas": {
                    "adaptive_shift_relearn": +0.30,
                    "fluid_low_degraded": +0.15,
                    "solenoid_fault": +0.12,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "limp_mode",
                "label": "Stuck in one gear / limp mode — transmission warning light",
                "deltas": {
                    "solenoid_fault": +0.25,
                    "cooler_line_blocked": +0.15,
                    "fluid_low_degraded": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "slipping",
                "label": "Slipping — engine revs but RV doesn't accelerate, especially under load or on grades",
                "deltas": {
                    "fluid_low_degraded": +0.20,
                    "band_or_clutch_pack": +0.18,
                    "torque_converter": +0.12,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "shudder",
                "label": "Shudder or vibration at highway cruise speed (45–60 mph)",
                "deltas": {
                    "torque_converter": +0.40,
                    "fluid_low_degraded": +0.15,
                    "adaptive_shift_relearn": +0.08,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "no_range",
                "label": "Selector won't engage a range or is stuck in Park",
                "deltas": {
                    "range_selector_fault": +0.55,
                    "solenoid_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
        ],
    },

    "chassis_type": {
        "question": "What chassis and transmission does this RV have?",
        "options": [
            {
                "match": "allison_diesel",
                "label": "Allison automatic (diesel pusher — Allison 3000, 3500, or 4000 series)",
                "deltas": {
                    "adaptive_shift_relearn": +0.10,
                    "solenoid_fault": +0.08,
                    "fluid_low_degraded": +0.05,
                },
                "eliminate": [],
                "next_node": "tow_context",
            },
            {
                "match": "gas_auto",
                "label": "Gas chassis automatic (Ford F53/E-450, Chevy Express, Ram ProMaster)",
                "deltas": {
                    "adaptive_shift_relearn": -0.08,
                    "torque_converter": +0.05,
                },
                "eliminate": [],
                "next_node": "tow_context",
            },
            {
                "match": "unknown",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "tow_context",
            },
        ],
    },

    "tow_context": {
        "question": "Was this problem noted while towing a dinghy (toad), or on grades under load?",
        "options": [
            {
                "match": "towing_or_grade",
                "label": "Yes — worse when towing or on grades",
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
                "match": "no_load",
                "label": "Same regardless of load",
                "deltas": {
                    "adaptive_shift_relearn": +0.08,
                    "solenoid_fault": +0.08,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the transmission fluid (Allison: check via ProLink or dipstick when warm in park; other units: standard dipstick). What is the level and condition?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and red/pink — clean, correct level",
                "deltas": {
                    "fluid_low_degraded": -0.25,
                    "solenoid_fault": +0.08,
                    "adaptive_shift_relearn": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dark_burned",
                "label": "Dark brown or burned smell",
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
                "label": "Low — below minimum",
                "deltas": {
                    "fluid_low_degraded": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "fluid_low_degraded": +0.08,
            "band_or_clutch_pack": +0.08,
            "torque_converter": +0.06,
            "solenoid_fault": +0.05,
        },
    },
    "usage_pattern": {
        "highway": {
            "cooler_line_blocked": +0.08,
            "torque_converter": +0.05,
            "adaptive_shift_relearn": +0.05,
        },
    },
}

TRANSMISSION_RV_POST_DIAGNOSIS: list[str] = [
    "After any Allison fluid service, perform a ClearAlert / idle relearn per the Allison service manual — Allison adaptive tables must relearn over 50–100 miles of mixed driving before shift quality fully normalizes.",
    "Before towing a dinghy, verify transmission temperature stays below 250°F (120°C) on extended grades — if you don't have a transmission temp gauge, add one; overheating is the primary cause of premature Allison clutch pack failure in RVs.",
    "If a range selector fault was found on a coach with Allison push-button controls, check for U0100 or U0101 CAN bus communication codes first — a failed CAN connection between the selector and TCM is a common and inexpensive fix compared to replacing the selector.",
]
