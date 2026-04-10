"""
Visible leak diagnostic tree — motorcycle variant.

Fork seal leaks are the dominant motorcycle-specific hypothesis —
far more common than any other leak on a bike. Shaft-drive bikes add
final drive oil as a hypothesis. Coolant leaks only apply to liquid-cooled bikes.
"""

VISIBLE_LEAK_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "fork_seal": {
        "label": "Fork seal leak — oil visible on lower fork tubes (very common on motorcycles)",
        "prior": 0.30,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fork seal set (pair)", "notes": "Replace both seals at the same time; dust wipers usually included in kit"},
            {"name": "Fork oil (correct weight per service manual)", "notes": "Drain and refill to spec while seals are out"},
        ],
    },
    "engine_oil_gasket": {
        "label": "Engine oil leak — drain plug, valve cover gasket, or base gasket",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Drain plug crush washer", "notes": "Replace every oil change — most neglected small leak source"},
            {"name": "Valve cover gasket", "notes": "Oil weeping from top of engine near the valve cover points here"},
        ],
    },
    "coolant_leak": {
        "label": "Coolant leak — hose, water pump, or radiator (liquid-cooled bikes only)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Coolant hose + clamps", "notes": "Squeeze hoses cold for cracks; check where they join the engine and radiator"},
            {"name": "Water pump seal / weep hole", "notes": "Drip from the weep hole under the water pump cover = internal seal failure"},
        ],
    },
    "fuel_carb_overflow": {
        "label": "Fuel overflow from carburetor float needle or overflow tube",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Carb float needle + seat kit", "notes": "Fuel dripping from the small rubber overflow tube = float needle not seating; turn petcock OFF when parked"},
        ],
    },
    "brake_fluid": {
        "label": "Brake fluid leak — master cylinder, brake line, or caliper",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Brake line banjo bolt washers", "notes": "Clear/amber fluid near caliper or master cylinder; SAFETY CRITICAL — braking may be severely compromised"},
        ],
    },
    "final_drive_oil": {
        "label": "Final drive gear oil — output shaft seal or bevel gear housing (shaft-drive bikes only)",
        "prior": 0.07,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Final drive output shaft seal", "notes": "Thick gear oil near rear wheel on BMW, Moto Guzzi, Honda shaft-drive models"},
        ],
    },
    "battery_acid": {
        "label": "Battery acid / electrolyte overflow (wet-cell conventional batteries only)",
        "prior": 0.03,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Sealed AGM battery", "notes": "Upgrade to sealed AGM to eliminate acid overflow entirely; also better for storage"},
        ],
    },
}

VISIBLE_LEAK_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "What color is the fluid, and where on the bike do you see it?",
        "options": [
            {
                "match": "oil_on_forks",
                "label": "Dark brown or amber oil — on the fork tubes (front suspension legs)",
                "deltas": {
                    "fork_seal": +0.60,
                    "engine_oil_gasket": -0.20,
                    "coolant_leak": -0.20,
                    "fuel_carb_overflow": -0.20,
                },
                "eliminate": ["brake_fluid", "battery_acid"],
                "next_node": "leak_when",
            },
            {
                "match": "oil_engine_area",
                "label": "Dark brown or black oil — from the engine area or crankcase",
                "deltas": {
                    "engine_oil_gasket": +0.45,
                    "fork_seal": -0.25,
                    "final_drive_oil": +0.05,
                },
                "eliminate": ["coolant_leak", "fuel_carb_overflow", "brake_fluid"],
                "next_node": "engine_location",
            },
            {
                "match": "clear_fuel_smell",
                "label": "Clear or slightly yellow with a strong gasoline smell",
                "deltas": {
                    "fuel_carb_overflow": +0.60,
                    "fork_seal": -0.30,
                    "engine_oil_gasket": -0.20,
                },
                "eliminate": ["coolant_leak", "brake_fluid", "battery_acid", "final_drive_oil"],
                "next_node": None,
            },
            {
                "match": "green_pink_coolant",
                "label": "Green, pink, or orange — looks like antifreeze",
                "deltas": {
                    "coolant_leak": +0.65,
                    "fork_seal": -0.30,
                    "engine_oil_gasket": -0.20,
                },
                "eliminate": ["fuel_carb_overflow", "brake_fluid", "final_drive_oil", "battery_acid"],
                "next_node": "leak_when",
            },
            {
                "match": "clear_brake_area",
                "label": "Clear or light amber fluid near the brake caliper or hand lever",
                "deltas": {
                    "brake_fluid": +0.65,
                    "fork_seal": -0.10,
                },
                "eliminate": ["coolant_leak", "fuel_carb_overflow", "engine_oil_gasket", "battery_acid"],
                "next_node": None,
            },
        ],
    },

    "engine_location": {
        "question": "More specifically, where on the engine is the oil coming from?",
        "options": [
            {
                "match": "bottom_drain_area",
                "label": "Under the engine — near the drain plug or oil filter",
                "deltas": {
                    "engine_oil_gasket": +0.30,
                },
                "eliminate": [],
                "next_node": "leak_when",
            },
            {
                "match": "top_sides_valve",
                "label": "Top or sides of the engine — valve cover area",
                "deltas": {
                    "engine_oil_gasket": +0.25,
                },
                "eliminate": [],
                "next_node": "leak_when",
            },
            {
                "match": "near_rear_wheel",
                "label": "Near the rear wheel or swingarm area",
                "deltas": {
                    "final_drive_oil": +0.40,
                    "engine_oil_gasket": -0.15,
                },
                "eliminate": [],
                "next_node": "leak_when",
            },
        ],
    },

    "leak_when": {
        "question": "When does the leak occur — only while the engine is running, only when parked, or both?",
        "options": [
            {
                "match": "only_running",
                "label": "Only while the engine is running or under load",
                "deltas": {
                    "engine_oil_gasket": +0.15,
                    "coolant_leak": +0.10,
                    "final_drive_oil": +0.05,
                },
                "eliminate": [],
                "next_node": "leak_rate",
            },
            {
                "match": "only_parked",
                "label": "Only when parked (gravity feed when stopped)",
                "deltas": {
                    "fuel_carb_overflow": +0.20,
                    "fork_seal": +0.10,
                    "engine_oil_gasket": +0.05,
                },
                "eliminate": [],
                "next_node": "leak_rate",
            },
            {
                "match": "both_always",
                "label": "Both — leaks whether running or parked",
                "deltas": {
                    "fork_seal": +0.10,
                    "engine_oil_gasket": +0.10,
                    "coolant_leak": +0.05,
                },
                "eliminate": [],
                "next_node": "leak_rate",
            },
        ],
    },

    "leak_rate": {
        "question": "How severe is the leak?",
        "options": [
            {
                "match": "minor_seep",
                "label": "Minor seep — small stain after sitting overnight",
                "deltas": {
                    "fork_seal": +0.05,
                    "engine_oil_gasket": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "steady_drip",
                "label": "Steady drip while running or leaving a puddle",
                "deltas": {
                    "fork_seal": +0.10,
                    "coolant_leak": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "heavy_flow",
                "label": "Heavy flow — losing fluid quickly, streaking down the bike",
                "deltas": {
                    "fork_seal": +0.15,
                    "coolant_leak": +0.20,
                    "fuel_carb_overflow": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"fork_seal": +0.06},
        "hot": {"coolant_leak": +0.08},
    },
    "mileage_band": {
        "high": {"engine_oil_gasket": +0.10, "fork_seal": +0.08, "final_drive_oil": +0.06},
    },
    "storage_time": {
        "months": {"fuel_carb_overflow": +0.10, "fork_seal": +0.06},
        "season": {"fuel_carb_overflow": +0.12, "fork_seal": +0.08},
    },
}

VISIBLE_LEAK_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After sealing the leak, clean the area thoroughly and check again after a short ride — multiple leaks often exist near the same location.",
    "If fork seals were replaced, top up fork oil to the exact spec height from the top of the tube — incorrect level affects handling.",
]
