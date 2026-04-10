"""
Coolant leak diagnostic tree — heavy equipment.

Covers visible external coolant loss: puddles, drips, residue, low coolant warning.
This is distinct from the overheating tree — the entry symptom here is a visible
or confirmed leak, not necessarily an overtemperature event (though both may
co-exist).

Heavy equipment coolant leaks differ from passenger vehicles:
- Engines are larger; even small leak rates deplete coolant quickly under load
- Many machines have remote-mounted coolant tanks accessible without opening
  the primary radiator cap
- Freeze plugs and coolant fittings are more exposed to vibration and impact
- Head gasket seeps (as opposed to full blows) are more common on high-hour engines
"""

COOLANT_LEAK_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "hose_or_fitting": {
        "label": "Cracked or leaking coolant hose, clamp, or fitting",
        "prior": 0.30,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant hose (upper or lower radiator)", "notes": "Inspect full length — cracks often start at the ends near clamps"},
            {"name": "Hose clamps", "notes": "Replace all clamps when replacing a hose; spring clamps fail with age"},
        ],
    },
    "radiator_damage": {
        "label": "Radiator core or tank damage (impact, corrosion, or electrolysis)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Radiator assembly", "notes": "Pressure test before replacing — electrolysis damage is not always visible"},
        ],
    },
    "water_pump_seal": {
        "label": "Water pump seal or weep hole leak",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Water pump assembly", "notes": "Weep hole drip = imminent failure. Replace before it becomes a bearing failure."},
        ],
    },
    "head_gasket_seep": {
        "label": "Head gasket seep — small external coolant loss at cylinder head",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "overflow_tank": {
        "label": "Cracked or split overflow/degas tank",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Coolant overflow / degas tank", "notes": "Check the tank itself, the cap, and the hose connecting it to the radiator"},
        ],
    },
    "freeze_plug": {
        "label": "Failed freeze plug (core plug) — common on high-hour or impact-damaged engines",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Freeze plug kit (brass or OEM steel)", "notes": "Requires engine access — often necessitates component removal to reach all plugs"},
        ],
    },
    "drain_petcock": {
        "label": "Open or leaking radiator drain petcock / drain plug",
        "prior": 0.07,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Radiator drain petcock / plug", "notes": "Check that petcock is fully closed; replace if cracked"},
        ],
    },
}

COOLANT_LEAK_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "Where do you see the coolant — is it dripping or pooling on the ground, or did you find the reservoir/overflow tank low?",
        "options": [
            {
                "match": "puddle_on_ground",
                "label": "Puddle or drip on the ground under the machine",
                "deltas": {
                    "hose_or_fitting": +0.15,
                    "radiator_damage": +0.10,
                    "water_pump_seal": +0.10,
                    "freeze_plug": +0.08,
                    "drain_petcock": +0.10,
                    "overflow_tank": -0.05,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "reservoir_low_no_puddle",
                "label": "Reservoir/overflow tank is low — no obvious drip or puddle",
                "deltas": {
                    "head_gasket_seep": +0.20,
                    "overflow_tank": +0.15,
                    "hose_or_fitting": +0.05,
                    "drain_petcock": -0.10,
                },
                "eliminate": [],
                "next_node": "residue_check",
            },
            {
                "match": "steam_or_spray",
                "label": "Steam or active spray — coolant coming out under pressure",
                "deltas": {
                    "hose_or_fitting": +0.25,
                    "radiator_damage": +0.15,
                    "water_pump_seal": +0.10,
                },
                "eliminate": ["overflow_tank", "drain_petcock"],
                "next_node": "leak_location",
            },
        ],
    },

    "leak_location": {
        "question": "Can you see where the coolant is coming from? Look at hoses, the radiator, the water pump area, and the bottom of the engine block.",
        "options": [
            {
                "match": "hose_or_clamp",
                "label": "Coming from a hose, hose end, or clamp",
                "deltas": {
                    "hose_or_fitting": +0.45,
                },
                "eliminate": ["head_gasket_seep", "freeze_plug", "radiator_damage"],
                "next_node": "onset",
            },
            {
                "match": "radiator_area",
                "label": "Coming from the radiator itself (core or side tanks)",
                "deltas": {
                    "radiator_damage": +0.40,
                    "drain_petcock": +0.10,
                },
                "eliminate": ["head_gasket_seep", "freeze_plug", "water_pump_seal"],
                "next_node": "onset",
            },
            {
                "match": "water_pump_area",
                "label": "Coming from the water pump area — front of engine, weep hole drip",
                "deltas": {
                    "water_pump_seal": +0.45,
                },
                "eliminate": ["head_gasket_seep", "drain_petcock", "overflow_tank"],
                "next_node": "onset",
            },
            {
                "match": "side_of_block",
                "label": "Coming from the side of the engine block (not pump, not hoses)",
                "deltas": {
                    "freeze_plug": +0.40,
                    "head_gasket_seep": +0.15,
                },
                "eliminate": ["hose_or_fitting", "drain_petcock", "overflow_tank"],
                "next_node": "onset",
            },
            {
                "match": "cant_locate",
                "label": "Can't locate the source / everything is wet",
                "deltas": {
                    "hose_or_fitting": +0.10,
                },
                "eliminate": [],
                "next_node": "residue_check",
            },
        ],
    },

    "residue_check": {
        "question": "Is there any dried white or brown residue (dried coolant deposits) on the engine, hoses, or ground near the leak area?",
        "options": [
            {
                "match": "residue_around_head",
                "label": "Yes — residue is around the cylinder head / head gasket area",
                "deltas": {
                    "head_gasket_seep": +0.35,
                    "freeze_plug": +0.05,
                },
                "eliminate": ["hose_or_fitting", "drain_petcock", "overflow_tank"],
                "next_node": "onset",
            },
            {
                "match": "residue_elsewhere",
                "label": "Yes — residue elsewhere (hoses, radiator, pump area)",
                "deltas": {
                    "hose_or_fitting": +0.10,
                    "radiator_damage": +0.10,
                    "water_pump_seal": +0.08,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "no_residue",
                "label": "No visible residue / just wet",
                "deltas": {
                    "drain_petcock": +0.08,
                    "hose_or_fitting": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "How long has the coolant loss been happening, and has the engine overheated as a result?",
        "options": [
            {
                "match": "sudden_with_overtemp",
                "label": "Started suddenly — engine overheated or warning light came on",
                "deltas": {
                    "hose_or_fitting": +0.15,
                    "radiator_damage": +0.10,
                    "water_pump_seal": +0.05,
                    "head_gasket_seep": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "gradual_no_overtemp",
                "label": "Gradual — slow loss over time, no overheating yet",
                "deltas": {
                    "head_gasket_seep": +0.15,
                    "overflow_tank": +0.10,
                    "water_pump_seal": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "found_at_inspection",
                "label": "Found at routine inspection — machine hasn't shown symptoms",
                "deltas": {
                    "drain_petcock": +0.10,
                    "freeze_plug": +0.08,
                    "hose_or_fitting": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

COOLANT_LEAK_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"radiator_damage": +0.05},
        "muddy": {"hose_or_fitting": +0.05, "freeze_plug": +0.05},
        "marine": {"radiator_damage": +0.08, "hose_or_fitting": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "water_pump_seal": +0.10,
            "hose_or_fitting": +0.08,
        },
        "long_storage": {
            "hose_or_fitting": +0.10,
            "freeze_plug": +0.05,
        },
    },
}

COOLANT_LEAK_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Never add cold water to a hot engine — thermal shock can crack the block or head. Let it cool completely first.",
    "Head gasket seeps: confirm with a combustion gas test (CO2 test kit on the coolant reservoir) before tearing down — external seeps can look identical to blown gaskets.",
    "Water pump weep holes: a small drip from the weep hole is a warning sign of imminent seal failure. Replace before it becomes a bearing failure.",
    "After any coolant system repair: pressure test to 15–20 PSI, let sit 15 minutes, recheck — this catches slow leaks before you reassemble everything.",
]
