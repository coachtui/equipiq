"""
Visible leak diagnostic tree — ATV/UTV variant.

Front and rear differential gear oil leaks are ATV-specific and
very common after water crossings (water intrusion thins the fluid
and pressure-washes seals). Coolant leaks are relevant to liquid-cooled
ATVs; air-cooled models have no coolant system.
"""

VISIBLE_LEAK_ATV_HYPOTHESES: dict[str, dict] = {
    "engine_oil": {
        "label": "Engine oil leak — rocker cover gasket, base gasket, or drain plug",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve cover gasket", "notes": "Most common engine oil leak source — tighten cover bolts first before replacing gasket"},
            {"name": "Drain plug crush washer", "notes": "Replace every oil change — reused washers weep slowly"},
            {"name": "Oil filter O-ring", "notes": "Check the O-ring on the filter housing after every oil change"},
        ],
    },
    "diff_gear_oil": {
        "label": "Front or rear differential oil leak — axle seal or breather tube overflow",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Differential axle seal (front or rear)", "notes": "Most common after water crossings — water enters the diff, displaces oil, and the seal leaks when the diff runs hot"},
            {"name": "Differential breather tube extension", "notes": "Extending the breather tube above the waterline prevents water from being sucked into the diff"},
        ],
    },
    "coolant_leak": {
        "label": "Coolant leak — hose, radiator fitting, or water pump seal (liquid-cooled models)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Radiator hose set + clamps", "notes": "Check all hose connections — ATV vibration loosens clamps over time"},
            {"name": "Water pump seal / impeller kit", "notes": "Coolant dripping from weep hole below water pump = seal failure"},
        ],
    },
    "fuel_leak": {
        "label": "Fuel leak — petcock seal, carb float, or fuel line",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Petcock rebuild kit", "notes": "Fuel dripping from petcock = failed diaphragm or O-ring; replace kit rather than whole petcock"},
            {"name": "Carburetor float valve / needle seat", "notes": "Fuel running from carb overflow tube = stuck float or worn needle — carb needs cleaning and inspection"},
            {"name": "Fuel line + clamps", "notes": "Inspect the full fuel line run for cracks, especially near heat sources"},
        ],
    },
    "brake_fluid": {
        "label": "Brake fluid leak — caliper, master cylinder, or brake line",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper rebuild kit", "notes": "Fluid at the wheel = caliper piston seal; DO NOT ride with a brake fluid leak"},
            {"name": "Master cylinder rebuild kit", "notes": "Fluid under the handlebar lever = master cylinder cup seals"},
        ],
    },
    "gear_oil_transmission": {
        "label": "Transmission or gearbox oil leak — output shaft seal or side cover",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Output shaft seal", "notes": "Gear oil leak from where a shaft exits the engine case = output shaft seal failure"},
        ],
    },
}

VISIBLE_LEAK_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "What color and consistency is the leaking fluid?",
        "options": [
            {
                "match": "black_brown_oil",
                "label": "Black or dark brown — engine oil",
                "deltas": {
                    "engine_oil": +0.55,
                    "gear_oil_transmission": +0.20,
                },
                "eliminate": ["coolant_leak", "fuel_leak", "brake_fluid"],
                "next_node": "location_check",
            },
            {
                "match": "amber_gear_oil",
                "label": "Amber or golden — gear oil or differential oil",
                "deltas": {
                    "diff_gear_oil": +0.45,
                    "gear_oil_transmission": +0.25,
                    "engine_oil": +0.10,
                },
                "eliminate": ["coolant_leak", "fuel_leak", "brake_fluid"],
                "next_node": "location_check",
            },
            {
                "match": "green_orange_coolant",
                "label": "Green, orange, or pink — coolant",
                "deltas": {
                    "coolant_leak": +0.80,
                },
                "eliminate": ["engine_oil", "diff_gear_oil", "fuel_leak", "brake_fluid", "gear_oil_transmission"],
                "next_node": "location_check",
            },
            {
                "match": "clear_fuel",
                "label": "Clear or slightly blue/yellow — fuel",
                "deltas": {
                    "fuel_leak": +0.70,
                },
                "eliminate": ["engine_oil", "diff_gear_oil", "coolant_leak", "brake_fluid"],
                "next_node": "location_check",
            },
            {
                "match": "clear_fluid_brakes",
                "label": "Clear or very light yellow — possibly brake fluid (near wheel or lever)",
                "deltas": {
                    "brake_fluid": +0.65,
                },
                "eliminate": ["engine_oil", "diff_gear_oil", "fuel_leak"],
                "next_node": "location_check",
            },
        ],
    },

    "location_check": {
        "question": "Where on the machine is the leak coming from?",
        "options": [
            {
                "match": "engine_top_side",
                "label": "Top or side of engine block / cylinder head",
                "deltas": {
                    "engine_oil": +0.30,
                    "coolant_leak": +0.10,
                },
                "eliminate": ["diff_gear_oil", "brake_fluid"],
                "next_node": "water_history",
            },
            {
                "match": "axle_wheel_area",
                "label": "Near a wheel hub, axle, or CV boot",
                "deltas": {
                    "diff_gear_oil": +0.45,
                    "brake_fluid": +0.20,
                },
                "eliminate": ["engine_oil", "fuel_leak", "coolant_leak"],
                "next_node": "water_history",
            },
            {
                "match": "under_engine",
                "label": "Under the engine or dripping from bottom",
                "deltas": {
                    "engine_oil": +0.30,
                    "gear_oil_transmission": +0.20,
                    "fuel_leak": +0.15,
                    "coolant_leak": +0.10,
                },
                "eliminate": [],
                "next_node": "water_history",
            },
            {
                "match": "carb_fuel_area",
                "label": "From carb overflow tube or fuel tank area",
                "deltas": {
                    "fuel_leak": +0.60,
                },
                "eliminate": ["engine_oil", "diff_gear_oil", "brake_fluid", "coolant_leak"],
                "next_node": "water_history",
            },
        ],
    },

    "water_history": {
        "question": "Has the ATV/UTV been through deep water crossings or heavy rain recently?",
        "options": [
            {
                "match": "water_crossings",
                "label": "Yes — deep water crossings or heavy mud use",
                "deltas": {
                    "diff_gear_oil": +0.30,
                    "engine_oil": +0.10,
                },
                "eliminate": [],
                "next_node": "leak_rate",
            },
            {
                "match": "dry_use",
                "label": "No — mostly dry trails or road use",
                "deltas": {
                    "engine_oil": +0.10,
                    "fuel_leak": +0.08,
                    "diff_gear_oil": -0.10,
                },
                "eliminate": [],
                "next_node": "leak_rate",
            },
        ],
    },

    "leak_rate": {
        "question": "How severe is the leak — a few drops after use, a slow drip, or an active stream?",
        "options": [
            {
                "match": "active_stream",
                "label": "Active stream or puddle forming quickly — do not run",
                "deltas": {
                    "coolant_leak": +0.10,
                    "fuel_leak": +0.10,
                    "brake_fluid": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "slow_drip",
                "label": "Slow drip after running — a few drops per minute",
                "deltas": {
                    "engine_oil": +0.08,
                    "diff_gear_oil": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "drops_only",
                "label": "Just a few spots after use — may be seepage",
                "deltas": {
                    "engine_oil": +0.06,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_ATV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {"engine_oil": +0.10, "diff_gear_oil": +0.10, "gear_oil_transmission": +0.06},
    },
    "storage_time": {
        "months": {"fuel_leak": +0.10, "engine_oil": +0.06},
        "season": {"fuel_leak": +0.12, "engine_oil": +0.08},
    },
    "first_start_of_season": {
        "yes": {"fuel_leak": +0.10, "coolant_leak": +0.06},
    },
}

VISIBLE_LEAK_ATV_POST_DIAGNOSIS: list[str] = [
    "After repairing a differential oil leak, extend the breather tube to prevent recurrence — route it to a high point above any likely water crossing depth.",
    "Any fuel leak near hot engine parts or the exhaust is a fire hazard — do not run until repaired.",
    "After coolant leak repair, run the engine to operating temperature and check for air pockets in the cooling system by squeezing the upper hose.",
]
