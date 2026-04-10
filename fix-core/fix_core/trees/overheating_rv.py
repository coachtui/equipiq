"""
Overheating diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Class A diesel pusher: rear-mounted engine, long coolant circuit to front-mounted
  radiator; low road speed at high load (mountain grades) is the primary stress
- Diesel pushers have a large coolant capacity — overheating takes longer to manifest
  but is harder to recover from (longer flush/fill cycle)
- Fan clutch / pusher fan fault unique to rear-engine layout
- Mountain grade heat soak is a primary RV overheating scenario
- Gas Class A and Class C: similar to HD truck overheating but with higher GVWR
- Diesel pusher: DO NOT open the radiator cap when hot — the cap is on the degas
  bottle and releasing pressure when hot causes immediate coolant spray and burns
"""

OVERHEATING_RV_HYPOTHESES: dict[str, dict] = {
    "coolant_low_leak": {
        "label": "Low coolant level or coolant leak (hose, fitting, or coolant reservoir)",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Coolant (50/50 premix or concentrate — confirm diesel vs. gas spec)", "notes": "Diesel pushers often require a specific extended-life coolant (ELC) — Fleetguard or Delo ELC; do NOT mix conventional green coolant with ELC"},
            {"name": "Upper or lower radiator hose", "notes": "RV radiator hoses are long and prone to heat-cracking — squeeze hoses when cold; feel for soft spots or cracking at clamp ends"},
        ],
    },
    "mountain_grade_heat": {
        "label": "Mountain grade heat soak — normal for underpowered or loaded RV on sustained grades",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — driving technique", "notes": "Pull over on the shoulder and let the engine idle for 5–10 minutes with the AC off; idling cools an RV engine faster than shutting off because the water pump and fan continue to circulate coolant"},
        ],
    },
    "thermostat_fault": {
        "label": "Failed thermostat (stuck closed — overheats rapidly; or stuck open — runs cold, poor heat)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Thermostat and housing gasket (engine-specific)", "notes": "Diesel pusher thermostat access varies — Cummins ISL thermostat is accessible from the top of the engine; Workhorse and Ford V10 access from the front"},
        ],
    },
    "radiator_fan_fault": {
        "label": "Radiator fan or fan clutch fault (fan not engaging under load — rear-engine pushers)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Viscous fan clutch or electric fan motor", "notes": "Rear-engine diesel pushers use a large puller or pusher fan — if the fan clutch disengages at low speed (sitting in traffic), temperatures spike; touch the fan after shutdown to check if it was fully engaged"},
        ],
    },
    "water_pump": {
        "label": "Failing water pump (coolant circulation reduced — overheats at idle or low speed)",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump (engine-specific)", "notes": "Diesel pusher water pumps are high-volume — impeller erosion from scale buildup is common; check for weeping at the pump shaft seal as an early indicator"},
        ],
    },
    "coolant_system_scale": {
        "label": "Scale or mineral buildup in coolant passages (reduced flow — high-mileage engine with irregular coolant changes)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Radiator flush / descaler", "notes": "Scale buildup reduces coolant flow dramatically — perform a full coolant flush with a descaler before a road trip if the coolant hasn't been changed in over 100,000 miles or 5 years"},
            {"name": "Extended-life coolant (full drain and fill)", "notes": "After descaling, refill with fresh ELC coolant to prevent rapid re-scaling"},
        ],
    },
    "ac_compressor_load": {
        "label": "AC system overloading the engine at low speed on grades (AC adding thermal load to marginal cooling system)",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — AC management", "notes": "On steep grades: switch to max fan and vent mode (no compressor) to reduce engine load; run rooftop AC units on shore power when parked to avoid running the chassis AC system while cooling"},
        ],
    },
}

OVERHEATING_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "Describe the overheating situation — what was happening when it occurred?",
        "options": [
            {
                "match": "mountain_grade",
                "label": "Overheated on a long uphill mountain grade or sustained climb",
                "deltas": {
                    "mountain_grade_heat": +0.30,
                    "coolant_low_leak": +0.15,
                    "radiator_fan_fault": +0.12,
                    "ac_compressor_load": +0.10,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
            {
                "match": "highway_flat",
                "label": "Overheated on flat highway or moderate grades",
                "deltas": {
                    "thermostat_fault": +0.20,
                    "coolant_low_leak": +0.18,
                    "water_pump": +0.12,
                    "radiator_fan_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
            {
                "match": "idle_slow",
                "label": "Overheated sitting in traffic or at low speed",
                "deltas": {
                    "radiator_fan_fault": +0.30,
                    "thermostat_fault": +0.15,
                    "coolant_low_leak": +0.12,
                    "ac_compressor_load": +0.12,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
            {
                "match": "rapid_overheat",
                "label": "Overheated very quickly — temp gauge spiked in minutes",
                "deltas": {
                    "coolant_low_leak": +0.35,
                    "thermostat_fault": +0.20,
                    "water_pump": +0.15,
                },
                "eliminate": [],
                "next_node": "coolant_check",
            },
        ],
    },

    "coolant_check": {
        "question": "After the engine has fully cooled, check the coolant reservoir level. What is the condition?",
        "options": [
            {
                "match": "low",
                "label": "Low — significantly below the MIN mark",
                "deltas": {
                    "coolant_low_leak": +0.40,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "ok_clean",
                "label": "Full and clean — green, orange, or yellow (correct ELC color)",
                "deltas": {
                    "coolant_low_leak": -0.15,
                    "thermostat_fault": +0.10,
                    "radiator_fan_fault": +0.10,
                    "coolant_system_scale": +0.08,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "rusty_scale",
                "label": "Rusty, brown, or cloudy — looks like it hasn't been changed in a long time",
                "deltas": {
                    "coolant_system_scale": +0.30,
                    "water_pump": +0.10,
                    "thermostat_fault": +0.08,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
        ],
    },

    "chassis_type": {
        "question": "What chassis is this RV?",
        "options": [
            {
                "match": "diesel_pusher",
                "label": "Class A diesel pusher (rear-mounted diesel — Cummins, CAT)",
                "deltas": {
                    "radiator_fan_fault": +0.08,
                    "coolant_system_scale": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "gas_rv",
                "label": "Class A gas or Class C (Ford V10, Chevy 8.1L, Workhorse — front engine)",
                "deltas": {
                    "thermostat_fault": +0.05,
                    "coolant_low_leak": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "coolant_low_leak": +0.10,
            "water_pump": +0.10,
            "coolant_system_scale": +0.08,
            "thermostat_fault": +0.06,
        },
    },
    "usage_pattern": {
        "highway": {
            "mountain_grade_heat": +0.10,
            "ac_compressor_load": +0.06,
        },
    },
    "climate": {
        "hot": {
            "coolant_low_leak": +0.06,
            "ac_compressor_load": +0.10,
            "radiator_fan_fault": +0.06,
        },
    },
}

OVERHEATING_RV_POST_DIAGNOSIS: list[str] = [
    "NEVER open the radiator cap or coolant reservoir cap on a hot diesel pusher — the system is pressurized and coolant will spray immediately; wait until the engine has been off for at least 60 minutes and the overflow tank is cool to the touch.",
    "On mountain grades, the standard technique for RVs is '4-3-2': if temp starts climbing, downshift and turn off the AC; if it keeps climbing after 2 minutes, pull over on the shoulder and idle for 5–10 minutes with the hood/engine bay door open — do not shut the engine off as the water pump stops circulating coolant.",
    "After any overheating event, change the coolant regardless of age — the coolant's corrosion inhibitors are consumed rapidly during a heat event; running old post-overheat coolant causes rapid scale buildup in the coolant passages.",
]
