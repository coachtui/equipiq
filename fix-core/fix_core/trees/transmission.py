"""
Transmission diagnostic tree (base / car).

Covers automatic and manual transmissions: ATF low/degraded, shift solenoid,
torque converter, worn clutch (manual), band/clutch pack, range sensor,
transmission cooler, and shift linkage/cable.
"""

TRANSMISSION_HYPOTHESES: dict[str, dict] = {
    "fluid_low_degraded": {
        "label": "Low or degraded transmission fluid (slipping, harsh shifts, overheating)",
        "prior": 0.24,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Automatic transmission fluid (correct spec — check dipstick or owner's manual)", "notes": "Never substitute a different ATF spec — wrong fluid ruins clutch packs; check for Dexron, Mercon, ZF Lifeguard, etc."},
            {"name": "Transmission filter and pan gasket kit", "notes": "Drop the pan to inspect for debris and replace the filter when doing a fluid service"},
        ],
    },
    "solenoid_fault": {
        "label": "Shift solenoid or valve body fault (stuck gear, erratic shifts, P07xx codes)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Shift solenoid pack or individual solenoid", "notes": "Scan for P07xx codes to identify which solenoid circuit — confirms before replacement"},
            {"name": "Valve body", "notes": "If multiple solenoids are faulty or pressure is wrong, the valve body may need replacement or reconditioning"},
        ],
    },
    "torque_converter": {
        "label": "Torque converter failure or lock-up clutch (shudder at cruise, no TCC lockup)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Torque converter", "notes": "Transmission removal required — always do a full fluid flush when replacing the converter"},
        ],
    },
    "clutch_worn": {
        "label": "Worn clutch disc or pressure plate (slipping under load — manual transmission only)",
        "prior": 0.13,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Clutch kit (disc, pressure plate, throw-out bearing)", "notes": "Always replace as a set — mismatched wear causes rapid re-failure"},
            {"name": "Flywheel resurfacing or replacement", "notes": "Hot spots or cracks on the flywheel face prevent the new clutch from bedding properly"},
        ],
    },
    "band_or_clutch_pack": {
        "label": "Worn internal clutch pack or band (slipping in a specific gear range)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission rebuild kit (friction plates, steels, seals)", "notes": "Internal wear is confirmed by a pressure test or by observing which gears slip"},
        ],
    },
    "transmission_range_sensor": {
        "label": "Transmission range / position sensor fault (wrong gear display, no start in park, won't shift)",
        "prior": 0.09,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Transmission range sensor (MLPS / neutral safety switch)", "notes": "Common symptom: car won't start in Park/Neutral or gear indicator is off by one position"},
        ],
    },
    "cooler_line_blocked": {
        "label": "Blocked transmission cooler or cooler line (thermal limp mode, overheating under load)",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Transmission cooler", "notes": "External auxiliary cooler is a worthwhile upgrade for towing applications"},
            {"name": "Transmission cooler line flush kit", "notes": "Back-flush the cooler before installing a rebuilt transmission — old debris re-contaminates"},
        ],
    },
    "linkage_cable": {
        "label": "Stretched or misadjusted shift cable or linkage (gear mismatch, hard shift)",
        "prior": 0.05,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Shift cable", "notes": "Often stretches on high-mileage vehicles; adjustment may restore correct gear engagement"},
            {"name": "Shift cable bushing / end clip kit", "notes": "Worn bushings cause slop in the shifter without requiring full cable replacement"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

TRANSMISSION_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the transmission do that seems wrong?",
        "options": [
            {
                "match": "slipping",
                "label": "Slipping — engine revs up but vehicle doesn't accelerate proportionally",
                "deltas": {
                    "fluid_low_degraded": +0.15,
                    "band_or_clutch_pack": +0.15,
                    "torque_converter": +0.10,
                    "clutch_worn": +0.10,
                    "linkage_cable": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "no_engage",
                "label": "No engagement — no movement in Drive or Reverse, or very delayed",
                "deltas": {
                    "fluid_low_degraded": +0.20,
                    "band_or_clutch_pack": +0.10,
                    "transmission_range_sensor": +0.15,
                    "linkage_cable": +0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "harsh_shifts",
                "label": "Harsh, clunky, or erratic shifts between gears",
                "deltas": {
                    "fluid_low_degraded": +0.15,
                    "solenoid_fault": +0.15,
                    "linkage_cable": +0.10,
                    "torque_converter": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "shudder",
                "label": "Shudder or vibration at highway cruise speed (feels like driving over rumble strips)",
                "deltas": {
                    "torque_converter": +0.35,
                    "fluid_low_degraded": +0.10,
                    "band_or_clutch_pack": +0.05,
                    "linkage_cable": -0.10,
                    "transmission_range_sensor": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "limp_mode",
                "label": "Stuck in one gear or limp mode — transmission warning light on",
                "deltas": {
                    "solenoid_fault": +0.25,
                    "fluid_low_degraded": +0.10,
                    "transmission_range_sensor": +0.10,
                    "cooler_line_blocked": +0.08,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the transmission fluid dipstick (if accessible — not all vehicles have one). What is the level and condition?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and bright red or pink — clean, no burned smell",
                "deltas": {
                    "fluid_low_degraded": -0.25,
                    "solenoid_fault": +0.10,
                    "band_or_clutch_pack": +0.10,
                    "torque_converter": +0.05,
                },
                "eliminate": [],
                "next_node": "when_occurs",
            },
            {
                "match": "dark_burned",
                "label": "Dark brown or black, or smells burned",
                "deltas": {
                    "fluid_low_degraded": +0.25,
                    "band_or_clutch_pack": +0.15,
                    "torque_converter": +0.10,
                    "cooler_line_blocked": +0.10,
                },
                "eliminate": [],
                "next_node": "when_occurs",
            },
            {
                "match": "level_low",
                "label": "Low — below the MIN mark on the dipstick",
                "deltas": {
                    "fluid_low_degraded": +0.35,
                    "solenoid_fault": -0.05,
                },
                "eliminate": [],
                "next_node": "when_occurs",
            },
            {
                "match": "no_dipstick",
                "label": "No dipstick — sealed transmission (common on many modern vehicles)",
                "deltas": {},
                "eliminate": [],
                "next_node": "when_occurs",
            },
        ],
    },

    "when_occurs": {
        "question": "When does the problem occur most noticeably?",
        "options": [
            {
                "match": "cold_only",
                "label": "Mostly when cold — clears up once the transmission warms up",
                "deltas": {
                    "solenoid_fault": +0.15,
                    "fluid_low_degraded": +0.08,
                    "linkage_cable": +0.05,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "hot_or_load",
                "label": "Gets worse when hot or under heavy load (towing, hills, hard acceleration)",
                "deltas": {
                    "cooler_line_blocked": +0.20,
                    "fluid_low_degraded": +0.10,
                    "band_or_clutch_pack": +0.10,
                    "torque_converter": +0.08,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "always",
                "label": "Always — doesn't matter if hot or cold",
                "deltas": {
                    "band_or_clutch_pack": +0.08,
                    "transmission_range_sensor": +0.08,
                    "linkage_cable": +0.08,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
            {
                "match": "intermittent",
                "label": "Intermittent — comes and goes unpredictably",
                "deltas": {
                    "solenoid_fault": +0.10,
                    "transmission_range_sensor": +0.08,
                },
                "eliminate": [],
                "next_node": "trans_type",
            },
        ],
    },

    "trans_type": {
        "question": "Is this an automatic or manual (stick shift / clutch pedal) transmission?",
        "options": [
            {
                "match": "automatic",
                "label": "Automatic — no clutch pedal",
                "deltas": {
                    "clutch_worn": -0.30,
                    "solenoid_fault": +0.05,
                    "torque_converter": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "manual",
                "label": "Manual — has a clutch pedal and gear shift",
                "deltas": {
                    "clutch_worn": +0.30,
                    "torque_converter": -0.30,
                    "solenoid_fault": -0.20,
                    "cooler_line_blocked": -0.15,
                    "band_or_clutch_pack": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cvt",
                "label": "CVT — continuously variable (no traditional gear steps)",
                "deltas": {
                    "clutch_worn": -0.20,
                    "torque_converter": -0.20,
                    "fluid_low_degraded": +0.10,
                    "band_or_clutch_pack": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "fluid_low_degraded": +0.08,
            "solenoid_fault": +0.06,
            "band_or_clutch_pack": +0.08,
            "torque_converter": +0.06,
        },
        "low": {
            "linkage_cable": +0.05,
            "transmission_range_sensor": +0.05,
        },
    },
    "climate": {
        "hot": {
            "cooler_line_blocked": +0.08,
            "fluid_low_degraded": +0.05,
        },
    },
    "usage_pattern": {
        "city": {
            "fluid_low_degraded": +0.06,
            "torque_converter": +0.05,
        },
    },
    "transmission_type": {
        "manual": {
            "clutch_worn": +0.20,
            "torque_converter": -0.20,
            "solenoid_fault": -0.15,
        },
        "cvt": {
            "fluid_low_degraded": +0.10,
            "band_or_clutch_pack": +0.08,
            "torque_converter": -0.15,
        },
    },
}

TRANSMISSION_POST_DIAGNOSIS: list[str] = [
    "After any transmission fluid service, check the level again after a 15-minute drive — fluid expands when hot, and some transmissions require a specific check procedure with the engine running.",
    "If the transmission was in limp mode, perform a transmission adaptive reset after repair (disconnect battery for 15 minutes on many vehicles) — old learned shift tables can cause continued harsh shifts even after the underlying fault is fixed.",
    "Never tow or drive with a slipping transmission any further than necessary — each slip event burns clutch material into the fluid and accelerates internal damage.",
]
