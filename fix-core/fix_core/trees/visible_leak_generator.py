"""
Visible leak diagnostic tree — generator variant.

Generator fluid leaks include engine oil (most common), fuel (from carb or tank),
coolant (liquid-cooled generators), and carbon/exhaust residue that looks like oil.
"""

VISIBLE_LEAK_GENERATOR_HYPOTHESES: dict[str, dict] = {
    "oil_drain_plug": {
        "label": "Loose or stripped oil drain plug or oil fill cap",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Oil drain plug with new washer/gasket", "notes": "Check torque spec; an overtightened plug can strip threads — use a new copper or aluminum crush washer each time"},
            {"name": "Oil fill cap / dipstick O-ring", "notes": "Fill cap that doesn't seat fully allows oil to escape during vibration"},
        ],
    },
    "fuel_carb_leak": {
        "label": "Fuel leak from carburetor float bowl, needle seat, or fuel line",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Carburetor rebuild kit (float needle and seat)", "notes": "Leaking fuel from the carb bowl drain = stuck float or worn needle seat. Rebuild or replace carb."},
            {"name": "Fuel line and clamps", "notes": "Cracked or loose fuel line at the petcock or carb inlet is common"},
        ],
    },
    "oil_gasket": {
        "label": "Valve cover gasket or crankcase gasket leak",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Valve cover gasket", "notes": "Common seep point on small engines; inexpensive gasket, straightforward repair"},
            {"name": "Crankcase gasket set", "notes": "If leak is below the valve cover level, check mating surface for corrosion or warping"},
        ],
    },
    "oil_seal_crankshaft": {
        "label": "Crankshaft oil seal leak (at the PTO/output shaft end)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Crankshaft oil seal (PTO side)", "notes": "Common on high-hour generators; oil seeps from behind the recoil starter or engine-generator coupling"},
        ],
    },
    "coolant_leak": {
        "label": "Coolant leak (liquid-cooled generators only — hose, radiator, or water pump seal)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Coolant hoses and clamps", "notes": "Inspect all hose connections; small generators often have only 2–3 hoses"},
            {"name": "Coolant", "notes": "Top up and run to find the source; a pressure test kit confirms leaks"},
        ],
    },
    "fuel_tank_seam": {
        "label": "Fuel tank seam or petcock leak",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Petcock / fuel valve", "notes": "Turn fuel off when not in use; a seeping petcock is a fire hazard"},
            {"name": "Tank sealer (Kreem or similar)", "notes": "Used for pinhole seam leaks; full tank replacement is safer for large cracks"},
        ],
    },
    "exhaust_carbon": {
        "label": "Exhaust carbon or condensate residue — not actually an oil leak",
        "prior": 0.03,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Black sooty residue near the exhaust is normal carbon — wipe with a rag to confirm it's not oil"},
        ],
    },
}

VISIBLE_LEAK_GENERATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the fluid look like?",
        "options": [
            {
                "match": "clear_or_gasoline_smell",
                "label": "Clear to light yellow with gasoline smell",
                "deltas": {
                    "fuel_carb_leak": +0.45,
                    "fuel_tank_seam": +0.20,
                    "oil_drain_plug": -0.10,
                    "coolant_leak": -0.10,
                },
                "eliminate": ["exhaust_carbon"],
                "next_node": "leak_location",
            },
            {
                "match": "brown_oily",
                "label": "Brown, amber, or black — oily texture",
                "deltas": {
                    "oil_drain_plug": +0.20,
                    "oil_gasket": +0.20,
                    "oil_seal_crankshaft": +0.15,
                    "fuel_carb_leak": -0.10,
                    "coolant_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "green_pink_coolant",
                "label": "Green, pink, or orange — coolant colour, sweet smell",
                "deltas": {
                    "coolant_leak": +0.55,
                    "oil_drain_plug": -0.15,
                    "fuel_carb_leak": -0.15,
                },
                "eliminate": ["fuel_carb_leak", "fuel_tank_seam", "exhaust_carbon"],
                "next_node": "leak_location",
            },
            {
                "match": "black_sooty",
                "label": "Black, sooty, dry residue (not wet fluid)",
                "deltas": {
                    "exhaust_carbon": +0.60,
                    "oil_drain_plug": -0.10,
                    "fuel_carb_leak": -0.10,
                },
                "eliminate": ["coolant_leak", "fuel_tank_seam"],
                "next_node": "leak_location",
            },
        ],
    },

    "leak_location": {
        "question": "Where on the generator is the fluid coming from?",
        "options": [
            {
                "match": "beneath_carb_fuel_line",
                "label": "Near the carburetor or fuel line / petcock",
                "deltas": {
                    "fuel_carb_leak": +0.35,
                    "fuel_tank_seam": +0.10,
                    "oil_drain_plug": -0.15,
                },
                "eliminate": [],
                "next_node": "leak_timing",
            },
            {
                "match": "bottom_engine",
                "label": "Bottom of the engine (underneath)",
                "deltas": {
                    "oil_drain_plug": +0.35,
                    "oil_seal_crankshaft": +0.15,
                    "oil_gasket": +0.10,
                },
                "eliminate": ["fuel_carb_leak", "coolant_leak"],
                "next_node": "leak_timing",
            },
            {
                "match": "side_of_engine",
                "label": "Side of the engine (valve cover area)",
                "deltas": {
                    "oil_gasket": +0.40,
                    "oil_seal_crankshaft": +0.10,
                },
                "eliminate": ["fuel_carb_leak", "fuel_tank_seam"],
                "next_node": "leak_timing",
            },
            {
                "match": "output_shaft_recoil",
                "label": "Near the recoil starter or output shaft coupling",
                "deltas": {
                    "oil_seal_crankshaft": +0.45,
                    "oil_gasket": +0.10,
                },
                "eliminate": ["fuel_carb_leak", "coolant_leak"],
                "next_node": "leak_timing",
            },
            {
                "match": "tank_area",
                "label": "From the fuel tank body or seam",
                "deltas": {
                    "fuel_tank_seam": +0.50,
                    "fuel_carb_leak": +0.10,
                },
                "eliminate": ["oil_drain_plug", "oil_gasket", "coolant_leak"],
                "next_node": "leak_timing",
            },
        ],
    },

    "leak_timing": {
        "question": "When does the leak occur — only while the engine is running, only when it is stopped, or both?",
        "options": [
            {
                "match": "only_running",
                "label": "Only while the engine is running or shortly after stopping",
                "deltas": {
                    "oil_seal_crankshaft": +0.15,
                    "oil_gasket": +0.10,
                    "fuel_carb_leak": +0.08,
                },
                "eliminate": [],
                "next_node": "fuel_shutoff",
            },
            {
                "match": "only_stopped",
                "label": "Only when the engine is stopped / parked",
                "deltas": {
                    "fuel_carb_leak": +0.25,
                    "fuel_tank_seam": +0.10,
                    "oil_drain_plug": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_shutoff",
            },
            {
                "match": "both_conditions",
                "label": "Both — leaks whether running or stopped",
                "deltas": {
                    "oil_drain_plug": +0.15,
                    "oil_gasket": +0.12,
                    "fuel_carb_leak": +0.08,
                },
                "eliminate": [],
                "next_node": "fuel_shutoff",
            },
        ],
    },

    "fuel_shutoff": {
        "question": "Does the generator have a fuel shutoff valve (petcock), and is it closed when the generator is not running?",
        "options": [
            {
                "match": "petcock_open_always",
                "label": "No petcock, or it's always left open",
                "deltas": {
                    "fuel_carb_leak": +0.15,
                    "fuel_tank_seam": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "petcock_used",
                "label": "Yes — I close the petcock when not running",
                "deltas": {
                    "fuel_carb_leak": -0.10,
                    "oil_drain_plug": +0.05,
                    "oil_gasket": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_shutoff",
                "label": "Not sure / don't have one",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_GENERATOR_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"fuel_carb_leak": +0.06},
    },
    "mileage_band": {
        "high": {"oil_seal_crankshaft": +0.10, "oil_gasket": +0.06},
    },
    "storage_time": {
        "months": {"fuel_carb_leak": +0.10, "fuel_tank_seam": +0.06},
        "season": {"fuel_carb_leak": +0.12, "fuel_tank_seam": +0.08},
    },
    "first_start_of_season": {
        "yes": {"fuel_carb_leak": +0.08, "oil_drain_plug": +0.04},
    },
}

VISIBLE_LEAK_GENERATOR_POST_DIAGNOSIS: list[str] = [
    "After stopping the leak, clean the engine with degreaser and run for 10 minutes to verify no new weeping points appear.",
    "Any fuel leak is a fire hazard — do not run the generator until the fuel leak is fully resolved.",
]
