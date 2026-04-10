"""
Strange noise diagnostic tree — PWC (personal watercraft) variant.

Debris ingestion causing metallic grinding in the pump is the most
alarming PWC noise and requires immediate shutdown. The unique underwater
exhaust of PWCs creates a range of normal sounds that are unfamiliar
to new riders — separating abnormal from normal is key.
"""

STRANGE_NOISE_PWC_HYPOTHESES: dict[str, dict] = {
    "debris_in_pump": {
        "label": "Debris (rock, gravel, shell) ingested into jet pump — grinding or metallic impact",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "(Inspection first)", "notes": "Shut down immediately. Tilt nose up and inspect the intake grate and pump tunnel for rocks or shell fragments. Clear debris before restarting."},
            {"name": "Impeller (if damaged)", "notes": "Rocks chipped off blade tips cause vibration and further damage — inspect impeller blades carefully"},
            {"name": "Wear ring (if scored)", "notes": "Gravel scores the wear ring inner surface — check for gouges after clearing debris"},
        ],
    },
    "wear_ring_scored": {
        "label": "Scored wear ring causing grinding or squealing in the pump",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wear ring replacement", "notes": "Squealing or grinding that matches engine RPM and comes from the pump = scored wear ring. Inspect by shining light down the pump nozzle."},
        ],
    },
    "pump_bearing": {
        "label": "Worn pump bearing or impeller shaft bearing",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pump shaft bearing set", "notes": "Rumbling or whining from the pump area that gets worse with RPM — bearing failure on high-hour machines"},
            {"name": "Impeller shaft seal", "notes": "Replace seal whenever accessing the pump — old seals cause water intrusion to the hull"},
        ],
    },
    "exhaust_system_noise": {
        "label": "Exhaust system rattle, resonance, or water-lock gurgling",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust manifold gasket", "notes": "Ticking or hissing from the engine bay = exhaust manifold leak. Hot exhaust in the closed hull is a fire/burn hazard."},
            {"name": "Water-cooled exhaust elbow", "notes": "Gurgling at idle = partially blocked water cooling in the exhaust; blocked cooling causes exhaust fire"},
        ],
    },
    "engine_knock": {
        "label": "Engine knock or pre-ignition — rod bearing or detonation",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil (check level immediately)", "notes": "PWC engines are high-RPM and knock quickly from oil starvation or detonation. Stop immediately — continued operation causes catastrophic damage."},
        ],
    },
    "cavitation_noise": {
        "label": "Cavitation — air ingestion in the pump causing hissing or gargling sound",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Intake grate (check for bending or large gaps)", "notes": "Cavitation hiss when accelerating hard = intake grate bent or damaged, or operating in very shallow water"},
        ],
    },
}

STRANGE_NOISE_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise — grinding/metallic impact, squealing from the pump, knocking, gurgling, or hissing?",
        "options": [
            {
                "match": "grinding_impact",
                "label": "Metallic grinding or impact sound — especially after running in shallow water",
                "deltas": {
                    "debris_in_pump": +0.65,
                    "wear_ring_scored": +0.15,
                },
                "eliminate": ["engine_knock", "cavitation_noise"],
                "next_node": "when_noise",
            },
            {
                "match": "squeal_pump",
                "label": "Squealing or screeching from the pump area — higher pitched",
                "deltas": {
                    "wear_ring_scored": +0.45,
                    "pump_bearing": +0.25,
                    "debris_in_pump": +0.15,
                },
                "eliminate": ["engine_knock", "cavitation_noise"],
                "next_node": "when_noise",
            },
            {
                "match": "knock_thud",
                "label": "Knocking, thumping, or heavy thudding from the engine",
                "deltas": {
                    "engine_knock": +0.55,
                    "debris_in_pump": +0.15,
                },
                "eliminate": ["cavitation_noise", "exhaust_system_noise"],
                "next_node": "when_noise",
            },
            {
                "match": "gurgle_hiss",
                "label": "Gurgling at idle or hissing under acceleration",
                "deltas": {
                    "exhaust_system_noise": +0.35,
                    "cavitation_noise": +0.30,
                    "pump_bearing": +0.10,
                },
                "eliminate": ["engine_knock", "debris_in_pump"],
                "next_node": "when_noise",
            },
            {
                "match": "rumble_vibration",
                "label": "Rumbling or vibration through the hull — worse at speed",
                "deltas": {
                    "pump_bearing": +0.30,
                    "wear_ring_scored": +0.25,
                    "debris_in_pump": +0.20,
                },
                "eliminate": ["cavitation_noise"],
                "next_node": "when_noise",
            },
        ],
    },

    "when_noise": {
        "question": "When does the noise occur — at idle, under acceleration, or only at higher speeds?",
        "options": [
            {
                "match": "idle_always",
                "label": "At idle / any RPM — continuous",
                "deltas": {
                    "exhaust_system_noise": +0.20,
                    "engine_knock": +0.15,
                    "pump_bearing": +0.10,
                },
                "eliminate": [],
                "next_node": "pump_inspection",
            },
            {
                "match": "under_acceleration",
                "label": "Only under acceleration or at higher RPMs",
                "deltas": {
                    "wear_ring_scored": +0.15,
                    "cavitation_noise": +0.15,
                    "pump_bearing": +0.10,
                },
                "eliminate": ["exhaust_system_noise"],
                "next_node": "pump_inspection",
            },
            {
                "match": "after_shallow_water",
                "label": "Started after running in very shallow water or over a sandbar",
                "deltas": {
                    "debris_in_pump": +0.50,
                    "wear_ring_scored": +0.20,
                    "cavitation_noise": +0.15,
                },
                "eliminate": ["engine_knock", "pump_bearing", "exhaust_system_noise"],
                "next_node": None,
            },
        ],
    },

    "pump_inspection": {
        "question": "Has the pump been inspected — any debris visible in the intake or pump tunnel?",
        "options": [
            {
                "match": "debris_found",
                "label": "Found rocks, gravel, shells, or rope in the intake/pump",
                "deltas": {
                    "debris_in_pump": +0.70,
                    "wear_ring_scored": +0.15,
                },
                "eliminate": ["engine_knock", "pump_bearing", "exhaust_system_noise"],
                "next_node": None,
            },
            {
                "match": "pump_clear",
                "label": "Pump tunnel and intake are clear",
                "deltas": {
                    "debris_in_pump": -0.20,
                    "wear_ring_scored": +0.15,
                    "pump_bearing": +0.12,
                    "engine_knock": +0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "What is the engine oil level and condition?",
        "options": [
            {
                "match": "oil_low_or_dirty",
                "label": "Oil is low or hasn't been changed in a long time",
                "deltas": {
                    "engine_knock": +0.35,
                    "pump_bearing": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "oil_ok",
                "label": "Oil level and condition are good",
                "deltas": {
                    "engine_knock": -0.10,
                    "wear_ring_scored": +0.10,
                    "pump_bearing": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"pump_bearing": +0.10, "wear_ring_scored": +0.08, "exhaust_system_noise": +0.06},
    },
    "mileage_band": {
        "high": {"pump_bearing": +0.10, "wear_ring_scored": +0.08, "engine_knock": +0.06},
    },
    "storage_time": {
        "months": {"exhaust_system_noise": +0.06},
        "season": {"exhaust_system_noise": +0.08, "pump_bearing": +0.05},
    },
    "first_start_of_season": {
        "yes": {"exhaust_system_noise": +0.06},
    },
}

STRANGE_NOISE_PWC_POST_DIAGNOSIS: list[str] = [
    "After any debris ingestion event, inspect the entire pump assembly — impeller, wear ring, and pump tunnel — before returning to service.",
    "A ticking exhaust manifold in the enclosed hull is a serious burn and fire hazard — prioritize this repair even if the noise seems minor.",
]
