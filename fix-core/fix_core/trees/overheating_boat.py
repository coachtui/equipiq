"""
Overheating diagnostic tree — boat / marine variant.

The #1 cause of marine overheating is water pump impeller failure — a
rubber impeller in the lower unit that must be replaced annually. Sea cock
blockage (clogged raw water inlet) is the second most common cause and is
often caused by a plastic bag or weed blocking the intake.
"""

OVERHEATING_BOAT_HYPOTHESES: dict[str, dict] = {
    "impeller_failure": {
        "label": "Failed water pump impeller — the rubber raw-water impeller in the lower unit has collapsed or torn",
        "prior": 0.32,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Water pump impeller kit (year/make/HP specific)", "notes": "The most common marine overheating cause. The rubber impeller should be replaced annually. Look for telltale sign: no or reduced water stream from the tell-tale hole at the back of the outboard."},
        ],
    },
    "sea_cock_blockage": {
        "label": "Blocked sea cock or raw water inlet — plastic bag, weed, or debris blocking intake",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(Clear the obstruction)", "notes": "Check the sea cock (inlet valve) is fully open. Look for plastic bags, kelp, or debris over the water intake. Shut the sea cock, clear debris, reopen. On outboards, check the lower unit intake screens."},
        ],
    },
    "thermostat_stuck": {
        "label": "Stuck thermostat — not opening to allow full coolant flow",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine thermostat (correct temp rating for engine)", "notes": "Marine thermostats are often 140°F or 160°F — lower than automotive. Use the OEM-specified temperature rating."},
            {"name": "Thermostat housing gasket / O-ring", "notes": "Replace the seal whenever the housing is opened"},
        ],
    },
    "heat_exchanger_clog": {
        "label": "Scale-clogged heat exchanger (closed-cooling systems) — saltwater scale blocking tubes",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine descaler / heat exchanger flush (Salt-Away, Rydlyme)", "notes": "Salt water deposits calcium carbonate scale inside the heat exchanger tubes. Chemical descaling is effective for mild buildup."},
            {"name": "Heat exchanger", "notes": "Heavily scaled or internally corroded units need replacement — tubes can collapse, blocking flow"},
        ],
    },
    "coolant_low": {
        "label": "Low coolant (closed-cooling systems only) — leaking or evaporated from the freshwater circuit",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine engine coolant", "notes": "Closed-cooling engines have a small freshwater reservoir like a car. Check overflow tank and radiator cap (if accessible)."},
        ],
    },
    "tell_tale_clogged": {
        "label": "Clogged tell-tale (indicator stream) hole — blockage in the output not the flow",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(Clear tell-tale hole)", "notes": "The tell-tale is the small water stream from the back of the outboard. If it's blocked, the cooling system may be flowing normally but appears not to be. Clear with a piece of wire or a small drill bit."},
        ],
    },
    "head_gasket": {
        "label": "Blown head gasket — combustion gas entering the cooling circuit",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Head gasket combustion leak test kit", "notes": "Blue test fluid turns yellow/green if combustion gases are present in the cooling water"},
        ],
    },
}

OVERHEATING_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "Is there a water stream (tell-tale) coming out of the back of the outboard, or water flow visible from the engine cooling discharge?",
        "options": [
            {
                "match": "no_water_stream",
                "label": "No — no water stream at all from the tell-tale",
                "deltas": {
                    "impeller_failure": +0.40,
                    "sea_cock_blockage": +0.25,
                    "tell_tale_clogged": +0.10,
                    "thermostat_stuck": -0.05,
                    "heat_exchanger_clog": -0.05,
                },
                "eliminate": [],
                "next_node": "sea_cock_check",
            },
            {
                "match": "weak_stream",
                "label": "Weak or reduced stream — less than normal",
                "deltas": {
                    "impeller_failure": +0.25,
                    "sea_cock_blockage": +0.15,
                    "heat_exchanger_clog": +0.10,
                    "thermostat_stuck": +0.05,
                },
                "eliminate": ["tell_tale_clogged", "head_gasket"],
                "next_node": "sea_cock_check",
            },
            {
                "match": "stream_present",
                "label": "Yes — water stream is present and looks normal",
                "deltas": {
                    "impeller_failure": -0.20,
                    "sea_cock_blockage": -0.15,
                    "thermostat_stuck": +0.20,
                    "heat_exchanger_clog": +0.15,
                    "head_gasket": +0.10,
                    "coolant_low": +0.05,
                },
                "eliminate": [],
                "next_node": "sea_cock_check",
            },
            {
                "match": "no_telltale_inboard",
                "label": "This is an inboard — no tell-tale to check",
                "deltas": {
                    "sea_cock_blockage": +0.10,
                    "thermostat_stuck": +0.10,
                    "heat_exchanger_clog": +0.10,
                    "impeller_failure": +0.05,
                },
                "eliminate": ["tell_tale_clogged"],
                "next_node": "sea_cock_check",
            },
        ],
    },

    "sea_cock_check": {
        "question": "Is the sea cock (raw water inlet valve) fully open? Did you check for debris over the water intake?",
        "options": [
            {
                "match": "sea_cock_closed_or_blocked",
                "label": "Sea cock was closed, partially closed, or debris found at the inlet",
                "deltas": {
                    "sea_cock_blockage": +0.55,
                    "impeller_failure": -0.10,
                },
                "eliminate": [],
                "next_node": "impeller_age",
            },
            {
                "match": "sea_cock_open_clear",
                "label": "Sea cock is fully open and no debris visible at the intake",
                "deltas": {
                    "sea_cock_blockage": -0.15,
                    "impeller_failure": +0.10,
                    "thermostat_stuck": +0.05,
                },
                "eliminate": [],
                "next_node": "impeller_age",
            },
            {
                "match": "inboard_no_sea_cock",
                "label": "Inboard — checked intake strainer, it's clear",
                "deltas": {
                    "sea_cock_blockage": -0.10,
                    "heat_exchanger_clog": +0.10,
                    "thermostat_stuck": +0.10,
                },
                "eliminate": [],
                "next_node": "impeller_age",
            },
        ],
    },

    "impeller_age": {
        "question": "When was the water pump impeller last replaced?",
        "options": [
            {
                "match": "over_one_year_or_unknown",
                "label": "Over one year ago, or never / unknown",
                "deltas": {
                    "impeller_failure": +0.30,
                },
                "eliminate": [],
                "next_node": "exhaust_smoke",
            },
            {
                "match": "recently_replaced",
                "label": "Replaced within the last season / less than one year",
                "deltas": {
                    "impeller_failure": -0.20,
                    "thermostat_stuck": +0.10,
                    "heat_exchanger_clog": +0.10,
                    "head_gasket": +0.05,
                },
                "eliminate": [],
                "next_node": "exhaust_smoke",
            },
        ],
    },

    "exhaust_smoke": {
        "question": "Is there white steam or exhaust smoke — more than normal for a water-cooled exhaust?",
        "options": [
            {
                "match": "yes_white_steam",
                "label": "Yes — white steam or excessive smoke from the exhaust",
                "deltas": {
                    "head_gasket": +0.30,
                    "coolant_low": +0.10,
                    "sea_cock_blockage": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_steam",
                "label": "No unusual steam or smoke",
                "deltas": {
                    "head_gasket": -0.15,
                    "impeller_failure": +0.05,
                    "thermostat_stuck": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_smoke",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

OVERHEATING_BOAT_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"impeller_failure": +0.06, "tell_tale_clogged": +0.05},
        "cold": {"thermostat_stuck": +0.08},
    },
    "saltwater_use": {
        "yes": {"impeller_failure": +0.12, "sea_cock_blockage": +0.10, "heat_exchanger_clog": +0.08},
    },
    "storage_time": {
        "months": {"impeller_failure": +0.15, "sea_cock_blockage": +0.08},
        "season": {"impeller_failure": +0.18, "sea_cock_blockage": +0.10, "thermostat_stuck": +0.06},
    },
    "first_start_of_season": {
        "yes": {"impeller_failure": +0.15, "sea_cock_blockage": +0.08, "thermostat_stuck": +0.06},
    },
}

OVERHEATING_BOAT_POST_DIAGNOSIS: list[str] = [
    "After resolving overheating, flush the cooling system with fresh water and replace the impeller if it wasn't already — overheating events collapse rubber impellers.",
    "Run the engine at the dock for 15 minutes and confirm a steady tell-tale stream before returning to service.",
]
