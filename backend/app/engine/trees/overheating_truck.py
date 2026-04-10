"""
Overheating diagnostic tree — truck/diesel variant.

Diesel trucks have unique overheating causes: EGR cooler failure (coolant
into intake), DPF active regen heat soak, and oil cooler clogging are
diesel-specific. High-output diesel engines also have very high cooling
demands when towing or in limp mode.
"""

OVERHEATING_TRUCK_HYPOTHESES: dict[str, dict] = {
    "coolant_low": {
        "label": "Low coolant level — slow leak or DCA (coolant additive) depletion",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel coolant / antifreeze (correct spec for diesel — often OAT or NOAT)", "notes": "Diesel engines often require Diesel Coolant Additive (DCA) to protect liner cavitation. Use the spec in your owner's manual."},
            {"name": "Coolant system pressure test kit", "notes": "Find and fix the source of loss before refilling"},
        ],
    },
    "egr_cooler_failure": {
        "label": "EGR cooler failure — coolant leaking into the intake or EGR circuit",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "EGR cooler", "notes": "A failed EGR cooler causes white smoke from the exhaust (coolant burning), coolant consumption, and rising coolant temps. Common on Ford 6.0L and some Duramax engines."},
        ],
    },
    "thermostat_failure": {
        "label": "Stuck thermostat — not opening and allowing full coolant flow",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Thermostat and housing gasket / O-ring", "notes": "Diesel thermostats often run at higher temperature ranges (195°F+) — match the OEM spec"},
        ],
    },
    "water_pump_failure": {
        "label": "Failed water pump — impeller, bearing, or shaft seal failure",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump with gasket", "notes": "On belt-driven water pumps, check serpentine or accessory belt condition too"},
            {"name": "Coolant pump housing O-ring", "notes": "External seal leak at housing is common before full pump failure"},
        ],
    },
    "radiator_or_fan": {
        "label": "Radiator blocked or cooling fan not operating — insufficient heat rejection",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fan clutch (viscous or electric)", "notes": "Diesel trucks often use a large mechanical fan clutch — a worn clutch slips and reduces airflow at low speeds when cooling demand is highest"},
            {"name": "Radiator flush kit", "notes": "Diesel coolant with DCA can deposit scale internally; flush and recharge per service interval"},
        ],
    },
    "oil_cooler_clogged": {
        "label": "Clogged engine oil cooler — can't transfer heat from oil to coolant circuit",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil cooler", "notes": "A clogged oil cooler raises both coolant and oil temperature simultaneously. Common on Ford 6.0L Power Stroke. Check if oil and coolant temps rise together."},
        ],
    },
    "head_gasket": {
        "label": "Blown head gasket — combustion gas entering coolant circuit",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Head gasket combustion leak test kit", "notes": "Blue fluid turns yellow/green if combustion gas is in coolant. On diesel trucks this is a serious (and expensive) repair — confirm before proceeding."},
        ],
    },
    "dpf_regen_heat": {
        "label": "DPF active regeneration causing elevated exhaust and cab heat — not a true cooling system fault",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No repair needed during regen)", "notes": "DPF regeneration burns soot at 1000°F+ inside the filter. This produces noticeable heat and can temporarily raise coolant temp. Temp should return to normal after regen completes (20–40 min highway driving)."},
        ],
    },
}

OVERHEATING_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What symptom made you think the engine is overheating?",
        "options": [
            {
                "match": "gauge_in_red",
                "label": "Temperature gauge is in the red / high temperature warning",
                "deltas": {
                    "coolant_low": +0.10,
                    "thermostat_failure": +0.10,
                    "water_pump_failure": +0.10,
                    "radiator_or_fan": +0.10,
                },
                "eliminate": ["dpf_regen_heat"],
                "next_node": "coolant_level",
            },
            {
                "match": "steam_or_smell",
                "label": "Steam, coolant smell, or overflow boiling",
                "deltas": {
                    "coolant_low": +0.20,
                    "head_gasket": +0.15,
                    "egr_cooler_failure": +0.10,
                    "dpf_regen_heat": -0.20,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "white_smoke_exhaust",
                "label": "White smoke from exhaust along with temperature rising",
                "deltas": {
                    "egr_cooler_failure": +0.30,
                    "head_gasket": +0.20,
                    "coolant_low": +0.10,
                    "dpf_regen_heat": -0.20,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
            {
                "match": "heat_while_parked_idling",
                "label": "Noticed heat while parked or idling (not during driving)",
                "deltas": {
                    "dpf_regen_heat": +0.30,
                    "radiator_or_fan": +0.15,
                    "coolant_low": +0.05,
                },
                "eliminate": [],
                "next_node": "coolant_level",
            },
        ],
    },

    "coolant_level": {
        "question": "Check the coolant reservoir level when the engine is cold. What is the level?",
        "options": [
            {
                "match": "level_ok",
                "label": "Correct — at the MIN/MAX marks",
                "deltas": {
                    "coolant_low": -0.25,
                    "thermostat_failure": +0.10,
                    "radiator_or_fan": +0.10,
                    "oil_cooler_clogged": +0.10,
                    "egr_cooler_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "white_smoke_exhaust",
            },
            {
                "match": "level_low",
                "label": "Low or empty",
                "deltas": {
                    "coolant_low": +0.30,
                    "head_gasket": +0.10,
                    "egr_cooler_failure": +0.10,
                    "water_pump_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "white_smoke_exhaust",
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "white_smoke_exhaust",
            },
        ],
    },

    "white_smoke_exhaust": {
        "question": "Is there persistent white smoke from the exhaust (not just cold morning condensation)?",
        "options": [
            {
                "match": "white_smoke_yes",
                "label": "Yes — white smoke that continues after warmup",
                "deltas": {
                    "egr_cooler_failure": +0.30,
                    "head_gasket": +0.25,
                    "coolant_low": +0.05,
                    "dpf_regen_heat": -0.20,
                },
                "eliminate": [],
                "next_node": "towing_condition",
            },
            {
                "match": "white_smoke_no",
                "label": "No unusual exhaust smoke",
                "deltas": {
                    "egr_cooler_failure": -0.15,
                    "head_gasket": -0.10,
                    "dpf_regen_heat": +0.10,
                },
                "eliminate": [],
                "next_node": "towing_condition",
            },
            {
                "match": "unknown_smoke",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "towing_condition",
            },
        ],
    },

    "towing_condition": {
        "question": "Was the truck towing or hauling a heavy load when overheating occurred?",
        "options": [
            {
                "match": "yes_towing",
                "label": "Yes — towing or carrying a heavy load",
                "deltas": {
                    "radiator_or_fan": +0.15,
                    "oil_cooler_clogged": +0.10,
                    "thermostat_failure": +0.05,
                    "dpf_regen_heat": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_towing",
                "label": "No — normal unloaded driving or idling",
                "deltas": {
                    "dpf_regen_heat": +0.15,
                    "egr_cooler_failure": +0.10,
                    "coolant_low": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_load",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"coolant_low": +0.06, "radiator_or_fan": +0.06},
        "cold": {"thermostat_failure": +0.06},
    },
    "mileage_band": {
        "high": {"egr_cooler_failure": +0.10, "water_pump_failure": +0.08, "oil_cooler_clogged": +0.08},
    },
    "usage_pattern": {
        "city": {"egr_cooler_failure": +0.08, "radiator_or_fan": +0.06},
    },
}

OVERHEATING_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After overheating, perform a combustion gas test on the coolant — diesel head gasket failures are common after overheating events and easy to miss.",
    "Flush the entire cooling system including the EGR cooler and oil cooler passages — debris from an overheating event can block these narrow passages.",
]
