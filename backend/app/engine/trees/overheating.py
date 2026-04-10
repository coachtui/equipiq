"""
Overheating diagnostic tree.

"Overheating" = engine temperature gauge reads high, temperature warning light
on, steam visible, or coolant loss/overflow observed. Generic enough for cars,
trucks, boats, motorcycles, and diesel generators with liquid-cooled engines.
"""

OVERHEATING_HYPOTHESES: dict[str, dict] = {
    "coolant_low": {
        "label": "Low coolant level (leak or evaporation)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant / antifreeze (correct type for engine)", "notes": "Check cap for correct spec; mix 50/50 with distilled water unless pre-mixed"},
            {"name": "Cooling system pressure test kit", "notes": "Find the source of the leak before refilling"},
        ],
    },
    "thermostat_failure": {
        "label": "Stuck-closed thermostat blocking coolant flow",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Thermostat and housing gasket / O-ring", "notes": "Replace as a pair; match OEM temperature rating"},
        ],
    },
    "water_pump_failure": {
        "label": "Failed water pump (impeller, shaft seal, or bearing)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump with gasket or O-ring", "notes": "Confirm fit for year/make/model/engine"},
            {"name": "Timing belt / chain kit", "notes": "If water pump is timing-driven, replace both together"},
        ],
    },
    "radiator_blocked": {
        "label": "Blocked or restricted radiator (external debris or internal scale)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Radiator flush kit", "notes": "Chemical flush can clear mild internal scale"},
            {"name": "Radiator", "notes": "Pressure-test first; replace if internally blocked or leaking"},
        ],
    },
    "head_gasket": {
        "label": "Blown head gasket (combustion gas entering coolant circuit)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Head gasket combustion leak test kit", "notes": "Blue fluid turns green/yellow if combustion gases are in coolant"},
        ],
    },
    "cooling_fan": {
        "label": "Cooling fan not operating (electric motor, relay, or mechanical clutch)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Cooling fan relay", "notes": "Check fuse box diagram; relay swap is a quick test"},
            {"name": "Cooling fan motor assembly", "notes": "For electric fans; test with direct 12V before replacing"},
            {"name": "Fan clutch", "notes": "For mechanical fans; worn clutch slips at high temp instead of engaging"},
        ],
    },
    "serpentine_belt": {
        "label": "Broken or slipping serpentine belt (drives water pump on belt-driven systems)",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Serpentine belt", "notes": "Match rib count and length exactly"},
            {"name": "Belt tensioner", "notes": "Replace together on high-mileage engines — a worn tensioner kills new belts"},
        ],
    },
    "coolant_temperature_sensor": {
        "label": "Faulty coolant temperature sensor (false high reading, not true overheat)",
        "prior": 0.05,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant temperature sensor", "notes": "Check for OBD codes P0115–P0119 before replacing; confirm actual coolant temp with IR gun"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

OVERHEATING_TREE: dict[str, dict] = {
    "start": {
        "question": "What symptom made you think the engine is overheating?",
        "options": [
            {
                "match": "gauge_high",
                "label": "Temperature gauge is in the red or reading very high",
                "deltas": {
                    "coolant_low": +0.10,
                    "thermostat_failure": +0.10,
                    "water_pump_failure": +0.10,
                    "radiator_blocked": +0.10,
                    "cooling_fan": +0.10,
                    "coolant_temperature_sensor": -0.05,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "steam_or_smell",
                "label": "Steam coming from engine bay or strong sweet coolant smell",
                "deltas": {
                    "coolant_low": +0.20,
                    "head_gasket": +0.15,
                    "water_pump_failure": +0.10,
                    "coolant_temperature_sensor": -0.25,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "warning_light_only",
                "label": "Only a warning light — no other obvious symptoms",
                "deltas": {
                    "coolant_temperature_sensor": +0.30,
                    "coolant_low": +0.05,
                    "thermostat_failure": -0.05,
                    "head_gasket": -0.05,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
        ],
    },

    "coolant_level": {
        "question": "Check the coolant overflow reservoir (when the engine is cold). What is the level?",
        "options": [
            {
                "match": "level_ok",
                "label": "Level is correct — at or between the MIN/MAX marks",
                "deltas": {
                    "coolant_low": -0.30,
                    "thermostat_failure": +0.15,
                    "cooling_fan": +0.15,
                    "radiator_blocked": +0.10,
                    "head_gasket": +0.10,
                },
                "eliminate": [],
                "next_node": "fan_operation",
            },
            {
                "match": "level_low",
                "label": "Low — below the MIN mark but not empty",
                "deltas": {
                    "coolant_low": +0.20,
                    "head_gasket": +0.10,
                    "water_pump_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "fan_operation",
            },
            {
                "match": "level_empty",
                "label": "Empty or nearly empty",
                "deltas": {
                    "coolant_low": +0.35,
                    "head_gasket": +0.15,
                    "water_pump_failure": +0.10,
                    "coolant_temperature_sensor": -0.20,
                },
                "eliminate": [],
                "next_node": "fan_operation",
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "fan_operation",
            },
        ],
    },

    "fan_operation": {
        "question": "With the engine warmed up, are the cooling fans spinning? (Turn on the A/C — electric fans should run immediately.)",
        "options": [
            {
                "match": "fans_running",
                "label": "Yes — fans are spinning",
                "deltas": {
                    "cooling_fan": -0.30,
                    "thermostat_failure": +0.10,
                    "radiator_blocked": +0.10,
                    "water_pump_failure": +0.10,
                },
                "eliminate": [],
                "next_node": "belt_condition",
            },
            {
                "match": "fans_not_running",
                "label": "No — fans are not spinning when they should be",
                "deltas": {
                    "cooling_fan": +0.40,
                    "thermostat_failure": -0.05,
                    "radiator_blocked": -0.05,
                },
                "eliminate": [],
                "next_node": "belt_condition",
            },
            {
                "match": "fans_unknown",
                "label": "Not sure / unable to check",
                "deltas": {},
                "eliminate": [],
                "next_node": "belt_condition",
            },
        ],
    },

    "belt_condition": {
        "question": "Is the serpentine belt present and does it look intact — no cracks, fraying, or obvious slack?",
        "options": [
            {
                "match": "belt_ok",
                "label": "Belt looks fine and is present",
                "deltas": {
                    "serpentine_belt": -0.25,
                    "water_pump_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "exhaust_smoke",
            },
            {
                "match": "belt_damaged_missing",
                "label": "Belt is cracked, slipping, squealing, or missing",
                "deltas": {
                    "serpentine_belt": +0.50,
                    "water_pump_failure": +0.15,
                    "cooling_fan": -0.10,
                },
                "eliminate": [],
                "next_node": "exhaust_smoke",
            },
            {
                "match": "belt_unknown",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "exhaust_smoke",
            },
        ],
    },

    "exhaust_smoke": {
        "question": "Is there white or sweet-smelling smoke from the exhaust (not just cold-morning condensation)?",
        "options": [
            {
                "match": "white_smoke_yes",
                "label": "Yes — white or sweet-smelling exhaust smoke",
                "deltas": {
                    "head_gasket": +0.35,
                    "coolant_low": +0.05,
                    "coolant_temperature_sensor": -0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "white_smoke_no",
                "label": "No unusual exhaust smoke",
                "deltas": {
                    "head_gasket": -0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "white_smoke_unknown",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"coolant_low": +0.08, "cooling_fan": +0.10, "radiator_blocked": +0.06},
        "cold": {"thermostat_failure": +0.08, "coolant_temperature_sensor": +0.05},
    },
    "mileage_band": {
        "high": {"water_pump_failure": +0.10, "thermostat_failure": +0.06, "head_gasket": +0.06, "serpentine_belt": +0.05},
    },
    "usage_pattern": {
        "city": {"cooling_fan": +0.08},
    },
}

OVERHEATING_POST_DIAGNOSIS: list[str] = [
    "After resolving overheating, flush and refill the cooling system — overheating events degrade coolant inhibitors and can introduce head gasket combustion gases.",
    "Pressure-test the cooling system before returning to service — overheating often weakens the weakest hose or clamp.",
]
