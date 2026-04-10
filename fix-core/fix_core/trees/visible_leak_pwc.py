"""
Visible leak diagnostic tree — PWC (personal watercraft) variant.

"Leaks" in a PWC are often found in the bilge rather than externally.
Any water accumulation in the hull needs to be triaged: normal ingestion
(around the pump), cooling system drainage, or a genuine hull/seal failure.
Fuel leaks in the enclosed hull are a fire/explosion risk.
"""

VISIBLE_LEAK_PWC_HYPOTHESES: dict[str, dict] = {
    "pump_shaft_seal": {
        "label": "Impeller shaft seal failure — water entering hull through the driveshaft tunnel",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Impeller shaft seal kit", "notes": "The most common water ingress point. A failed shaft seal lets water flow directly into the hull through the pump tunnel whenever underway."},
            {"name": "Carbon ring / mechanical seal", "notes": "Some models use a mechanical seal — these wear gradually and leak more at higher RPMs"},
        ],
    },
    "hull_intake_fitting": {
        "label": "Loose or failed hull fitting — bailer jets, cooling inlets, or thru-hull fittings",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Thru-hull fitting + O-ring kit", "notes": "Water pooling in the hull while at rest (not just after riding) points to a failed thru-hull fitting or hull crack rather than the pump seal"},
            {"name": "Marine sealant (3M 5200 or equivalent)", "notes": "For fittings that are intact but leaking at the hull contact point"},
        ],
    },
    "fuel_leak": {
        "label": "Fuel leak in the hull — fuel line, tank fitting, or carb/injector",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel line (fuel-rated, non-hardened)", "notes": "CRITICAL: fuel vapors in the enclosed hull are explosive. Identify and repair before any ignition source. Sniff the hull before starting."},
            {"name": "Fuel tank gasket / filler neck seal", "notes": "Check the fuel tank collar and all fuel line connections — any fuel smell in the hull is an emergency"},
        ],
    },
    "engine_oil_leak": {
        "label": "Engine oil leak — valve cover, drain plug, or crankshaft seal",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve cover gasket", "notes": "Oil in the hull bilge (oily water) points to an engine oil leak; check valve cover and base gasket first"},
            {"name": "Oil drain plug + crush washer", "notes": "Ensure drain plug is tight and washer was replaced at last oil change"},
        ],
    },
    "exhaust_manifold_leak": {
        "label": "Exhaust manifold water jacket leak — hot coolant or steam into hull",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust manifold gasket set", "notes": "Rusty water or steam in the hull after running = exhaust manifold water jacket failure. Salt deposits corrode the passages over time."},
        ],
    },
    "water_cooling_drain": {
        "label": "Normal cooling water drainage — not a leak but residual cooling water in bilge",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Some water in the hull bilge after riding is normal — it's residual cooling water that drains back. A few cups is normal; multiple gallons is not."},
        ],
    },
}

VISIBLE_LEAK_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "Where is the fluid, and what does it smell or look like?",
        "options": [
            {
                "match": "fuel_smell",
                "label": "Strong fuel smell in the hull — clear or slightly yellowish liquid",
                "deltas": {
                    "fuel_leak": +0.80,
                },
                "eliminate": ["pump_shaft_seal", "engine_oil_leak", "exhaust_manifold_leak", "water_cooling_drain"],
                "next_node": None,
            },
            {
                "match": "oily_water",
                "label": "Oily sheen on water in the bilge — dark or brown",
                "deltas": {
                    "engine_oil_leak": +0.50,
                    "exhaust_manifold_leak": +0.20,
                },
                "eliminate": ["pump_shaft_seal", "fuel_leak", "water_cooling_drain"],
                "next_node": "volume_check",
            },
            {
                "match": "clear_water",
                "label": "Clear water accumulating in the hull",
                "deltas": {
                    "pump_shaft_seal": +0.35,
                    "hull_intake_fitting": +0.25,
                    "water_cooling_drain": +0.20,
                },
                "eliminate": ["fuel_leak", "engine_oil_leak"],
                "next_node": "volume_check",
            },
            {
                "match": "rusty_milky",
                "label": "Rusty or milky fluid — may be steaming",
                "deltas": {
                    "exhaust_manifold_leak": +0.60,
                },
                "eliminate": ["fuel_leak", "pump_shaft_seal"],
                "next_node": "volume_check",
            },
        ],
    },

    "volume_check": {
        "question": "How much fluid is accumulating, and when does it accumulate — while riding or while sitting still?",
        "options": [
            {
                "match": "sitting_still",
                "label": "Accumulates while sitting at the dock — not just after riding",
                "deltas": {
                    "hull_intake_fitting": +0.40,
                    "fuel_leak": +0.15,
                    "pump_shaft_seal": -0.10,
                    "water_cooling_drain": -0.20,
                },
                "eliminate": [],
                "next_node": "pump_check",
            },
            {
                "match": "while_riding_lots",
                "label": "Several gallons after riding — much more than normal",
                "deltas": {
                    "pump_shaft_seal": +0.40,
                    "hull_intake_fitting": +0.20,
                    "water_cooling_drain": -0.20,
                },
                "eliminate": [],
                "next_node": "pump_check",
            },
            {
                "match": "small_amount",
                "label": "Small amount (a cup or two) — only after riding",
                "deltas": {
                    "water_cooling_drain": +0.40,
                    "pump_shaft_seal": -0.10,
                },
                "eliminate": ["hull_intake_fitting", "fuel_leak"],
                "next_node": None,
            },
        ],
    },

    "pump_check": {
        "question": "Has the pump shaft seal been inspected or recently replaced?",
        "options": [
            {
                "match": "seal_old",
                "label": "Never replaced, or machine has high hours",
                "deltas": {
                    "pump_shaft_seal": +0.30,
                },
                "eliminate": [],
                "next_node": "hull_check",
            },
            {
                "match": "seal_new",
                "label": "Shaft seal recently replaced",
                "deltas": {
                    "pump_shaft_seal": -0.20,
                    "hull_intake_fitting": +0.20,
                    "engine_oil_leak": +0.10,
                },
                "eliminate": [],
                "next_node": "hull_check",
            },
        ],
    },

    "hull_check": {
        "question": "Has the hull been inspected for cracks, and have thru-hull fittings been checked for tightness?",
        "options": [
            {
                "match": "fitting_loose",
                "label": "Found a loose thru-hull fitting or cracked hull",
                "deltas": {
                    "hull_intake_fitting": +0.65,
                },
                "eliminate": ["pump_shaft_seal", "engine_oil_leak", "exhaust_manifold_leak"],
                "next_node": None,
            },
            {
                "match": "hull_ok",
                "label": "Hull and fittings look intact",
                "deltas": {
                    "hull_intake_fitting": -0.15,
                    "pump_shaft_seal": +0.15,
                    "engine_oil_leak": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"exhaust_manifold_leak": +0.15, "hull_intake_fitting": +0.10, "pump_shaft_seal": +0.08},
    },
    "mileage_band": {
        "high": {"pump_shaft_seal": +0.12, "engine_oil_leak": +0.08, "exhaust_manifold_leak": +0.08},
    },
    "storage_time": {
        "months": {"fuel_leak": +0.08, "hull_intake_fitting": +0.06},
        "season": {"fuel_leak": +0.10, "hull_intake_fitting": +0.08},
    },
    "first_start_of_season": {
        "yes": {"fuel_leak": +0.08, "hull_intake_fitting": +0.06},
    },
}

VISIBLE_LEAK_PWC_POST_DIAGNOSIS: list[str] = [
    "Any fuel smell in an enclosed PWC hull is a fire/explosion emergency — ventilate the hull with the bilge blower for 4+ minutes before any ignition source.",
    "After pump shaft seal replacement, run the PWC for 20 minutes, then check the bilge for water accumulation to confirm the repair.",
    "For saltwater use, flush the entire cooling system and bilge with fresh water after every ride to slow corrosion of the exhaust manifold water jacket.",
]
