"""
Check engine light diagnostic tree.

"Check engine light" = malfunction indicator lamp (MIL) is on. Targets
OBD-II vehicles (1996+). Questions narrow between emissions, fuel system,
misfires, and sensor faults using P-code ranges and drivability symptoms.
"""

CHECK_ENGINE_LIGHT_HYPOTHESES: dict[str, dict] = {
    "o2_sensor": {
        "label": "Faulty oxygen sensor (upstream or downstream)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Oxygen sensor", "notes": "Confirm upstream/downstream position from code (P0130–P0167); use socket tool for access"},
        ],
    },
    "catalytic_converter_fail": {
        "label": "Catalytic converter failure or low efficiency (P0420/P0430)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Catalytic converter", "notes": "Confirm upstream O2 sensor is good first — a bad upstream sensor can falsely trigger P0420"},
        ],
    },
    "evap_leak": {
        "label": "EVAP system leak — loose or failed gas cap, purge valve, or vent hose",
        "prior": 0.13,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Gas cap (OEM or quality aftermarket)", "notes": "Try a new cap first — it is the cheapest fix and very common"},
            {"name": "EVAP purge valve (solenoid)", "notes": "Click-tests with a hand vacuum pump; common on 100k+ mile vehicles"},
        ],
    },
    "maf_sensor_fail": {
        "label": "Dirty or failed MAF sensor causing incorrect air-fuel measurement",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "MAF sensor cleaner spray", "notes": "Clean before replacing — often resolves the issue"},
            {"name": "MAF sensor", "notes": "Replace only if cleaning does not resolve codes"},
        ],
    },
    "misfire": {
        "label": "Engine misfire — spark plug, ignition coil, or injector fault (P030X)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plugs (full set)", "notes": "Replace as a complete set; check gap against spec"},
            {"name": "Ignition coil", "notes": "Swap suspected coil to another cylinder — misfire code should follow it if coil is bad"},
        ],
    },
    "fuel_system": {
        "label": "Fuel system fault — low pressure, injector, or pump (P0087, P0171, P0174)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel filter", "notes": "Replace if not done in 30k+ miles; low pressure can cause lean codes"},
            {"name": "Fuel pressure test kit", "notes": "Confirm pressure at rail before replacing pump"},
            {"name": "Fuel injector cleaner additive", "notes": "Add to tank; can help with minor deposit buildup on injectors"},
        ],
    },
    "egr_failure": {
        "label": "EGR valve fault or carbon blockage (P0400 series)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "EGR valve", "notes": "Test with vacuum pump before replacing; carbon buildup is often the real cause"},
            {"name": "EGR cleaning kit / carbon cleaner", "notes": "Spray cleaner often restores function without full replacement"},
        ],
    },
    "transmission_fault": {
        "label": "Transmission fault — wrong gear ratio, solenoid, or slip (P07XX)",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission fluid and filter", "notes": "Check level and condition first — burnt smell or dark color means a service is overdue"},
            {"name": "Transmission solenoid kit", "notes": "Shift solenoids are a common cause of P07XX codes on high-mileage automatics"},
        ],
    },
    "engine_temp_sensor": {
        "label": "Engine coolant temperature sensor fault (P0115–P0119)",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant temperature sensor", "notes": "Verify with live OBD data — a stuck reading at extreme cold or hot confirms sensor failure"},
        ],
    },
    "battery_voltage_low": {
        "label": "Low battery voltage or charging system fault (P0562, P0563)",
        "prior": 0.02,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Battery", "notes": "Load-test battery; 3+ year old battery with marginal CCA should be replaced"},
            {"name": "Alternator", "notes": "Output should be 13.5–14.5 V at idle with load; below 13 V points to alternator failure"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

CHECK_ENGINE_LIGHT_TREE: dict[str, dict] = {
    "start": {
        "question": "Do you have the fault codes stored? An OBD-II scanner (including cheap Bluetooth adapters with a phone app) can read them.",
        "options": [
            {
                "match": "has_codes",
                "label": "Yes — I have the codes",
                "deltas": {},
                "eliminate": [],
                "next_node": "code_range",
            },
            {
                "match": "no_codes_yet",
                "label": "Not yet — no scanner available",
                "deltas": {
                    "o2_sensor": +0.05,
                    "evap_leak": +0.05,
                    "maf_sensor_fail": +0.05,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "light_just_came_on",
                "label": "Just came on — haven't checked codes yet",
                "deltas": {},
                "eliminate": [],
                "next_node": "driveability",
            },
        ],
    },

    "code_range": {
        "question": "Which range do the codes fall in? (Look at the first digits — e.g. P0420, P0302, P0171)",
        "options": [
            {
                "match": "p042x_catalyst",
                "label": "P0420 or P0430 — catalyst efficiency below threshold",
                "deltas": {
                    "catalytic_converter_fail": +0.45,
                    "o2_sensor": +0.10,
                    "misfire": -0.10,
                    "evap_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "p030x_misfire",
                "label": "P030X — misfire (P0300 random, P0301–P0309 cylinder-specific)",
                "deltas": {
                    "misfire": +0.45,
                    "fuel_system": +0.10,
                    "o2_sensor": -0.10,
                    "evap_leak": -0.15,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "p044x_evap",
                "label": "P044X or P045X — EVAP system leak or purge fault",
                "deltas": {
                    "evap_leak": +0.50,
                    "catalytic_converter_fail": -0.10,
                    "misfire": -0.10,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "p01xx_fuel_air",
                "label": "P01XX — fuel or air metering (P0171, P0174 lean; P0087 low pressure)",
                "deltas": {
                    "fuel_system": +0.30,
                    "maf_sensor_fail": +0.25,
                    "o2_sensor": +0.10,
                    "evap_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "p07xx_trans",
                "label": "P07XX — transmission (shift solenoid, gear ratio, slip)",
                "deltas": {
                    "transmission_fault": +0.50,
                    "fuel_system": -0.10,
                    "misfire": -0.10,
                },
                "eliminate": [],
                "next_node": "driveability",
            },
            {
                "match": "other_codes",
                "label": "Other codes or multiple different code families",
                "deltas": {},
                "eliminate": [],
                "next_node": "driveability",
            },
        ],
    },

    "driveability": {
        "question": "Is the engine running noticeably differently — rough idle, hesitation, loss of power, or stalling?",
        "options": [
            {
                "match": "running_rough",
                "label": "Yes — rough, misfiring, hesitating, or stalling",
                "deltas": {
                    "misfire": +0.20,
                    "fuel_system": +0.15,
                    "maf_sensor_fail": +0.10,
                    "evap_leak": -0.10,
                    "engine_temp_sensor": -0.05,
                },
                "eliminate": [],
                "next_node": "gas_cap",
            },
            {
                "match": "running_normal",
                "label": "No — runs perfectly normally",
                "deltas": {
                    "evap_leak": +0.20,
                    "o2_sensor": +0.10,
                    "catalytic_converter_fail": +0.10,
                    "misfire": -0.15,
                    "fuel_system": -0.10,
                },
                "eliminate": [],
                "next_node": "gas_cap",
            },
            {
                "match": "sluggish_power_loss",
                "label": "Sluggish or some power loss, but not rough",
                "deltas": {
                    "fuel_system": +0.20,
                    "catalytic_converter_fail": +0.15,
                    "transmission_fault": +0.10,
                    "evap_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "gas_cap",
            },
        ],
    },

    "gas_cap": {
        "question": "When did you last tighten or replace the gas cap? A loose or cracked cap is the most common EVAP code trigger.",
        "options": [
            {
                "match": "cap_loose_or_old",
                "label": "It was loose, I just tightened it — or the cap is old / cracked",
                "deltas": {
                    "evap_leak": +0.25,
                    "catalytic_converter_fail": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_trim",
            },
            {
                "match": "cap_fine",
                "label": "Cap is tight and in good condition",
                "deltas": {
                    "evap_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "fuel_trim",
            },
            {
                "match": "cap_unknown",
                "label": "Not sure / haven't checked",
                "deltas": {},
                "eliminate": [],
                "next_node": "fuel_trim",
            },
        ],
    },

    "fuel_trim": {
        "question": "Has the engine been running rich (poor MPG, black smoke, fuel smell from exhaust) or lean (stumbling, hesitation under load)?",
        "options": [
            {
                "match": "running_rich",
                "label": "Rich — poor MPG, black smoke, or fuel smell from exhaust",
                "deltas": {
                    "o2_sensor": +0.20,
                    "maf_sensor_fail": +0.15,
                    "fuel_system": +0.10,
                },
                "eliminate": [],
                "next_node": "mileage",
            },
            {
                "match": "running_lean",
                "label": "Lean — stumbling, surging, or hesitation under load",
                "deltas": {
                    "fuel_system": +0.25,
                    "maf_sensor_fail": +0.20,
                    "o2_sensor": +0.10,
                },
                "eliminate": [],
                "next_node": "mileage",
            },
            {
                "match": "neither",
                "label": "Neither / not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "mileage",
            },
        ],
    },

    "mileage": {
        "question": "Roughly how many miles (or hours) on this engine?",
        "options": [
            {
                "match": "high_mileage",
                "label": "High mileage — over 100,000 miles",
                "deltas": {
                    "o2_sensor": +0.10,
                    "catalytic_converter_fail": +0.10,
                    "egr_failure": +0.10,
                    "battery_voltage_low": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low_mid_mileage",
                "label": "Low to mid mileage — under 100,000 miles",
                "deltas": {
                    "evap_leak": +0.05,
                    "maf_sensor_fail": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_mileage",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CHECK_ENGINE_LIGHT_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"battery_voltage_low": +0.08, "engine_temp_sensor": +0.06},
        "hot": {"catalytic_converter_fail": +0.06},
    },
    "mileage_band": {
        "high": {"catalytic_converter_fail": +0.10, "maf_sensor_fail": +0.08, "egr_failure": +0.06},
    },
    "usage_pattern": {
        "city": {"catalytic_converter_fail": +0.08, "egr_failure": +0.08},
    },
}

CHECK_ENGINE_LIGHT_POST_DIAGNOSIS: list[str] = [
    "After repair, clear DTCs and complete a full drive cycle (highway + idle mix) to confirm readiness monitors pass — required for emissions testing.",
    "If multiple codes were stored, address them in priority order — a P0420 (cat efficiency) is often caused by an O2 sensor or misfire upstream, not the converter itself.",
]
