"""
Visible leak diagnostic tree.

"Visible leak" = fluid leak the user can see under the machine or in the engine
bay. Covers oil, coolant, transmission fluid, fuel, power steering fluid, and
hydraulic fluid. Generic enough to apply to cars, trucks, boats, generators,
heavy equipment, etc.
"""

VISIBLE_LEAK_HYPOTHESES: dict[str, dict] = {
    "oil_gasket": {
        "label": "Engine oil leak — valve cover, oil pan, or rear main seal gasket",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve cover gasket set", "notes": "Most common; inspect top of engine for wetness first"},
            {"name": "Oil pan gasket", "notes": "Look under engine for pooling; tighten bolts to spec before replacing"},
        ],
    },
    "coolant_hose": {
        "label": "Coolant leak — hose, clamp, or radiator",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant hoses (upper + lower)", "notes": "Squeeze hoses when cold — cracked or soft = replace"},
            {"name": "Hose clamps", "notes": "Tighten loose clamps first before replacing hoses"},
            {"name": "Coolant / antifreeze", "notes": "Top off after repair; check for correct mix ratio"},
        ],
    },
    "head_gasket": {
        "label": "Blown head gasket (coolant or oil mixing, white exhaust smoke)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Head gasket test kit (combustion gas test)", "notes": "Blue/purple → green color change confirms combustion gases in coolant"},
        ],
    },
    "transmission_fluid": {
        "label": "Transmission fluid leak — pan gasket, cooler line, or seal",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Transmission pan gasket", "notes": "Red fluid under middle of vehicle points here; check fluid level and color"},
            {"name": "Transmission cooler line", "notes": "Look for wet lines running from transmission to radiator"},
        ],
    },
    "oil_drain_plug": {
        "label": "Loose or stripped oil drain plug or filter",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Drain plug washer", "notes": "Always replace the crush washer — cheap and prevents future leaks"},
            {"name": "Oil filter", "notes": "Hand-tighten + 3/4 turn; over-tightening can crack the housing"},
        ],
    },
    "fuel_leak": {
        "label": "Fuel leak — line, injector O-ring, or tank fitting",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Fuel line repair kit", "notes": "SAFETY: no ignition sources near fuel leaks. Gasoline/diesel is fire hazard."},
            {"name": "Injector O-ring kit", "notes": "Fuel smell under hood often points to injector O-rings on high-mileage engines"},
        ],
    },
    "power_steering_hydraulic": {
        "label": "Power steering fluid or hydraulic fluid leak (rack, hose, or pump)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Power steering hose", "notes": "Slippery clear/amber fluid near front axle area is common here"},
            {"name": "Hydraulic fluid (for equipment)", "notes": "Check reservoir level; trace leak to hose fittings or cylinder seals"},
        ],
    },
    "water_pump": {
        "label": "Leaking water pump (weep hole drip or shaft seal failure)",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Water pump", "notes": "Weep hole drip under pump = seal failure. Replace pump + timing belt/chain if applicable."},
            {"name": "Water pump gasket / O-ring", "notes": "Included with most pump kits"},
        ],
    },
    "differential_axle": {
        "label": "Differential or axle seal leak (gear oil near wheels or rear axle)",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Axle shaft seal", "notes": "Thick dark gear oil near a wheel or axle housing points here"},
            {"name": "Differential gasket", "notes": "Rear diff cover gasket is a common seep on high-mileage trucks"},
        ],
    },
}

VISIBLE_LEAK_TREE: dict[str, dict] = {
    "start": {
        "question": "What color and consistency is the fluid you see leaking?",
        "options": [
            {
                "match": "dark_brown_black",
                "label": "Dark brown or black — looks like motor oil",
                "deltas": {
                    "oil_gasket": +0.30,
                    "oil_drain_plug": +0.20,
                    "differential_axle": +0.10,
                    "coolant_hose": -0.15,
                    "fuel_leak": -0.15,
                    "power_steering_hydraulic": -0.05,
                    "transmission_fluid": -0.05,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "green_orange_pink",
                "label": "Green, orange, or pink — looks like antifreeze/coolant",
                "deltas": {
                    "coolant_hose": +0.30,
                    "head_gasket": +0.15,
                    "water_pump": +0.15,
                    "oil_gasket": -0.15,
                    "transmission_fluid": -0.10,
                    "fuel_leak": -0.15,
                    "differential_axle": -0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "red_pink",
                "label": "Red or pinkish — possibly transmission or power steering fluid",
                "deltas": {
                    "transmission_fluid": +0.35,
                    "power_steering_hydraulic": +0.25,
                    "oil_gasket": -0.10,
                    "coolant_hose": -0.10,
                    "fuel_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "clear_or_fuel_smell",
                "label": "Clear, pale, or has a distinct fuel smell",
                "deltas": {
                    "fuel_leak": +0.40,
                    "power_steering_hydraulic": +0.10,
                    "oil_gasket": -0.10,
                    "coolant_hose": -0.10,
                    "transmission_fluid": -0.15,
                    "differential_axle": -0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
        ],
    },

    "leak_location": {
        "question": "Where on the machine is the leak — top of the engine bay, under the engine, near a wheel or axle housing, or middle of the undercarriage?",
        "options": [
            {
                "match": "top_engine",
                "label": "Top or sides of the engine / engine bay",
                "deltas": {
                    "oil_gasket": +0.20,
                    "coolant_hose": +0.15,
                    "water_pump": +0.10,
                    "fuel_leak": +0.10,
                    "differential_axle": -0.20,
                    "transmission_fluid": -0.10,
                    "oil_drain_plug": -0.10,
                },
                "eliminate": [],
                "next_node": "rate_of_leak",
            },
            {
                "match": "under_engine_center",
                "label": "Under the engine, center of the vehicle",
                "deltas": {
                    "oil_drain_plug": +0.25,
                    "oil_gasket": +0.15,
                    "transmission_fluid": +0.10,
                    "coolant_hose": +0.05,
                    "differential_axle": -0.10,
                    "water_pump": -0.05,
                },
                "eliminate": [],
                "next_node": "rate_of_leak",
            },
            {
                "match": "near_wheel_axle",
                "label": "Near a wheel or axle",
                "deltas": {
                    "differential_axle": +0.40,
                    "oil_gasket": -0.15,
                    "coolant_hose": -0.15,
                    "oil_drain_plug": -0.15,
                    "water_pump": -0.10,
                },
                "eliminate": [],
                "next_node": "rate_of_leak",
            },
            {
                "match": "middle_undercarriage",
                "label": "Middle of the vehicle / undercarriage",
                "deltas": {
                    "transmission_fluid": +0.25,
                    "fuel_leak": +0.15,
                    "power_steering_hydraulic": +0.10,
                    "oil_gasket": -0.05,
                    "differential_axle": +0.05,
                    "water_pump": -0.10,
                },
                "eliminate": [],
                "next_node": "rate_of_leak",
            },
        ],
    },

    "rate_of_leak": {
        "question": "How bad is the leak — a drip or two after sitting, a steady drip while running, or an active stream/gush?",
        "options": [
            {
                "match": "minor_seep",
                "label": "Minor seep or a spot or two after sitting overnight",
                "deltas": {
                    "oil_gasket": +0.10,
                    "oil_drain_plug": +0.10,
                    "differential_axle": +0.05,
                    "head_gasket": -0.10,
                    "water_pump": -0.05,
                },
                "eliminate": [],
                "next_node": "fluid_smell",
            },
            {
                "match": "steady_drip",
                "label": "Steady drip while running or leaving a puddle",
                "deltas": {
                    "coolant_hose": +0.10,
                    "transmission_fluid": +0.10,
                    "water_pump": +0.10,
                    "oil_gasket": +0.05,
                    "oil_drain_plug": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_smell",
            },
            {
                "match": "active_stream",
                "label": "Active stream, gush, or losing fluid fast",
                "deltas": {
                    "coolant_hose": +0.20,
                    "fuel_leak": +0.20,
                    "head_gasket": +0.15,
                    "oil_drain_plug": +0.05,
                    "differential_axle": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_smell",
            },
        ],
    },

    "fluid_smell": {
        "question": "Does the leaking fluid have a distinct smell?",
        "options": [
            {
                "match": "sweet_coolant",
                "label": "Sweet or slightly syrupy — like antifreeze",
                "deltas": {
                    "coolant_hose": +0.25,
                    "head_gasket": +0.20,
                    "water_pump": +0.15,
                    "oil_gasket": -0.15,
                    "fuel_leak": -0.15,
                    "transmission_fluid": -0.10,
                },
                "eliminate": [],
                "next_node": "engine_temp",
            },
            {
                "match": "acrid_burning",
                "label": "Acrid or burnt — like burning oil",
                "deltas": {
                    "oil_gasket": +0.20,
                    "oil_drain_plug": +0.15,
                    "differential_axle": +0.05,
                    "coolant_hose": -0.10,
                    "fuel_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "engine_temp",
            },
            {
                "match": "fuel_smell",
                "label": "Strong fuel smell — gasoline or diesel",
                "deltas": {
                    "fuel_leak": +0.40,
                    "oil_gasket": -0.15,
                    "coolant_hose": -0.15,
                    "transmission_fluid": -0.15,
                },
                "eliminate": [],
                "next_node": "engine_temp",
            },
            {
                "match": "no_smell",
                "label": "No distinct smell or hard to tell",
                "deltas": {
                    "differential_axle": +0.05,
                    "transmission_fluid": +0.05,
                    "power_steering_hydraulic": +0.05,
                },
                "eliminate": [],
                "next_node": "engine_temp",
            },
        ],
    },

    "engine_temp": {
        "question": "Is the temperature gauge reading normal while the leak is happening, or is the engine running hot?",
        "options": [
            {
                "match": "running_hot",
                "label": "Running hot — temperature gauge elevated or warning light on",
                "deltas": {
                    "coolant_hose": +0.20,
                    "head_gasket": +0.25,
                    "water_pump": +0.15,
                    "oil_gasket": -0.05,
                    "fuel_leak": -0.10,
                    "oil_drain_plug": -0.05,
                    "transmission_fluid": -0.05,
                },
                "eliminate": [],
                "next_node": "leak_after_sitting",
            },
            {
                "match": "temp_normal",
                "label": "Temperature gauge is normal",
                "deltas": {
                    "oil_gasket": +0.10,
                    "oil_drain_plug": +0.10,
                    "transmission_fluid": +0.05,
                    "differential_axle": +0.05,
                    "head_gasket": -0.15,
                    "coolant_hose": -0.05,
                },
                "eliminate": [],
                "next_node": "leak_after_sitting",
            },
        ],
    },

    "leak_after_sitting": {
        "question": "Does fluid pool under the vehicle when it's parked overnight?",
        "options": [
            {
                "match": "yes_puddle",
                "label": "Yes — noticeable puddle or wet spot after sitting",
                "deltas": {
                    "oil_gasket": +0.10,
                    "transmission_fluid": +0.10,
                    "oil_drain_plug": +0.10,
                    "differential_axle": +0.05,
                    "water_pump": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "minor_spot",
                "label": "Minor spot or just a drop or two",
                "deltas": {
                    "oil_gasket": +0.05,
                    "oil_drain_plug": +0.05,
                    "head_gasket": -0.05,
                    "coolant_hose": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_puddle",
                "label": "No — nothing on the ground after parking",
                "deltas": {
                    "water_pump": +0.10,
                    "coolant_hose": +0.05,
                    "fuel_leak": +0.05,
                    "oil_gasket": -0.05,
                    "oil_drain_plug": -0.05,
                    "differential_axle": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"coolant_hose": +0.06},
        "hot": {"head_gasket": +0.06, "coolant_hose": +0.06},
    },
    "mileage_band": {
        "high": {"oil_gasket": +0.10, "coolant_hose": +0.08, "water_pump": +0.06},
    },
    "usage_pattern": {
        "city": {"oil_gasket": +0.04},
    },
}

VISIBLE_LEAK_POST_DIAGNOSIS: list[str] = [
    "After sealing the leak, clean the engine bay and check again after 100 miles — leaks often have multiple sources that are only visible after the primary one is fixed.",
    "Pressure-test the cooling system if a coolant leak was involved — a $20 pressure tester finds weeping hoses that look dry at rest.",
]
