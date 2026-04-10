"""
Strange noise diagnostic tree — boat / marine variant.

Boats have unique noise sources: propeller cavitation (expected in turns),
exhaust underwater (inboards), water pump impeller failure (shrieking),
lower unit gear noise, and hull resonance from engine vibration.
"""

STRANGE_NOISE_BOAT_HYPOTHESES: dict[str, dict] = {
    "cavitation_normal": {
        "label": "Propeller cavitation — expected popping/sputtering noise in sharp turns or at low speed",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No repair needed — adjust technique)", "notes": "Cavitation during sharp turns at speed is normal — the prop momentarily draws in surface air. Slow down before turning sharply. Persistent cavitation at normal speeds points to prop damage."},
        ],
    },
    "impeller_shriek": {
        "label": "Failed water pump impeller — high-pitched shriek or squeal (outboard or raw-water cooled)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Water pump impeller kit (year/make/HP specific)", "notes": "The rubber impeller in the lower unit water pump should be replaced annually or every 100 hours. A shrieking or squealing noise from the lower unit is a classic symptom — it will fail soon."},
        ],
    },
    "prop_damage_vibration": {
        "label": "Damaged propeller causing vibration or thumping noise at speed",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Propeller", "notes": "A bent blade causes rhythmic vibration that increases with RPM. Have the prop inspected and rebalanced or replace."},
        ],
    },
    "lower_unit_bearing": {
        "label": "Worn lower unit bearing or gear — grinding or whining from below the engine",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Lower unit gear oil (check level first)", "notes": "Check the lower unit oil — if it's milky (water intrusion) or dark, the seals and bearings may be failing. Low oil = bearing failure."},
            {"name": "Lower unit rebuild or replacement", "notes": "Grinding or whining from the lower unit that persists after oil check requires professional service"},
        ],
    },
    "exhaust_system_leak": {
        "label": "Exhaust manifold or water-cooled exhaust leak — gurgling, hissing, or steam from engine compartment",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Exhaust manifold riser / elbow", "notes": "On inboard engines, the exhaust riser (water-jacketed elbow) corrodes internally and can leak. A rusted riser is a serious fire and flooding risk."},
            {"name": "Exhaust manifold gasket", "notes": "Tick or hiss from the exhaust port area indicates a gasket failure at the cylinder head"},
        ],
    },
    "engine_knock_low_oil": {
        "label": "Engine knock from low oil — rhythmic knock worsening under load",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil", "notes": "Check level immediately. Stop running the engine if a deep knock is present under load — bearing damage progresses quickly."},
        ],
    },
    "hull_resonance": {
        "label": "Hull vibration / resonance — engine mounts worn or loose, causing noise to transmit through hull",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Engine mounts (marine, vibration isolation)", "notes": "Rubber engine mounts deteriorate from bilge fuel and moisture. Worn mounts transmit all engine vibration directly to the hull."},
        ],
    },
}

STRANGE_NOISE_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise?",
        "options": [
            {
                "match": "shriek_squeal",
                "label": "High-pitched shriek or squeal — especially at lower speeds",
                "deltas": {
                    "impeller_shriek": +0.50,
                    "lower_unit_bearing": +0.10,
                    "cavitation_normal": -0.10,
                },
                "eliminate": ["engine_knock_low_oil", "prop_damage_vibration"],
                "next_node": "noise_location",
            },
            {
                "match": "knock_thud",
                "label": "Deep knock, thud, or rhythmic heavy impact",
                "deltas": {
                    "engine_knock_low_oil": +0.35,
                    "prop_damage_vibration": +0.25,
                    "lower_unit_bearing": +0.15,
                    "cavitation_normal": -0.10,
                },
                "eliminate": ["impeller_shriek", "hull_resonance"],
                "next_node": "noise_location",
            },
            {
                "match": "grinding_whine",
                "label": "Grinding or whine — increases with speed",
                "deltas": {
                    "lower_unit_bearing": +0.40,
                    "prop_damage_vibration": +0.20,
                    "impeller_shriek": +0.10,
                },
                "eliminate": ["cavitation_normal", "hull_resonance"],
                "next_node": "noise_location",
            },
            {
                "match": "pop_sputter_turns",
                "label": "Popping or sputtering — mainly in sharp turns or at low speed",
                "deltas": {
                    "cavitation_normal": +0.50,
                    "prop_damage_vibration": +0.15,
                    "impeller_shriek": -0.10,
                },
                "eliminate": ["engine_knock_low_oil", "exhaust_system_leak"],
                "next_node": "noise_location",
            },
            {
                "match": "vibration_hum",
                "label": "Vibration through the hull or helm — steady hum",
                "deltas": {
                    "hull_resonance": +0.35,
                    "prop_damage_vibration": +0.30,
                    "lower_unit_bearing": +0.10,
                },
                "eliminate": ["cavitation_normal", "impeller_shriek"],
                "next_node": "noise_location",
            },
        ],
    },

    "noise_location": {
        "question": "Where does the noise seem to originate?",
        "options": [
            {
                "match": "below_waterline_lower_unit",
                "label": "Below the boat — lower unit or underwater",
                "deltas": {
                    "impeller_shriek": +0.15,
                    "lower_unit_bearing": +0.20,
                    "prop_damage_vibration": +0.10,
                    "cavitation_normal": +0.10,
                },
                "eliminate": ["exhaust_system_leak", "hull_resonance"],
                "next_node": "noise_under_load",
            },
            {
                "match": "engine_compartment",
                "label": "Engine compartment / inside the hull",
                "deltas": {
                    "engine_knock_low_oil": +0.20,
                    "exhaust_system_leak": +0.20,
                    "hull_resonance": +0.15,
                    "impeller_shriek": -0.05,
                    "cavitation_normal": -0.10,
                },
                "eliminate": [],
                "next_node": "noise_under_load",
            },
            {
                "match": "propeller_area",
                "label": "Near the propeller",
                "deltas": {
                    "prop_damage_vibration": +0.25,
                    "cavitation_normal": +0.15,
                    "impeller_shriek": +0.10,
                },
                "eliminate": ["engine_knock_low_oil", "hull_resonance"],
                "next_node": "noise_under_load",
            },
        ],
    },

    "noise_under_load": {
        "question": "Does the noise change when you shift into gear versus sitting in neutral at idle?",
        "options": [
            {
                "match": "only_in_gear",
                "label": "Only (or much worse) in gear — reduces or disappears in neutral",
                "deltas": {
                    "prop_damage_vibration": +0.20,
                    "lower_unit_bearing": +0.15,
                    "cavitation_normal": +0.10,
                    "engine_knock_low_oil": -0.05,
                    "hull_resonance": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "same_neutral_and_gear",
                "label": "Same noise in both neutral and gear",
                "deltas": {
                    "engine_knock_low_oil": +0.15,
                    "impeller_shriek": +0.10,
                    "exhaust_system_leak": +0.10,
                    "hull_resonance": +0.06,
                    "prop_damage_vibration": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "only_at_idle",
                "label": "Only at idle — goes away when RPM increases",
                "deltas": {
                    "impeller_shriek": +0.15,
                    "exhaust_system_leak": +0.10,
                    "hull_resonance": +0.10,
                    "cavitation_normal": -0.10,
                    "prop_damage_vibration": -0.05,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "Have you checked the engine oil and the lower unit gear oil levels?",
        "options": [
            {
                "match": "oil_low_or_milky",
                "label": "Engine oil or lower unit oil is low — or lower unit oil is milky / water-contaminated",
                "deltas": {
                    "engine_knock_low_oil": +0.25,
                    "lower_unit_bearing": +0.25,
                },
                "eliminate": ["cavitation_normal", "hull_resonance"],
                "next_node": None,
            },
            {
                "match": "oil_ok",
                "label": "Both oils are at correct level and look normal",
                "deltas": {
                    "engine_knock_low_oil": -0.10,
                    "lower_unit_bearing": -0.05,
                    "cavitation_normal": +0.05,
                    "hull_resonance": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "oil_not_checked",
                "label": "Haven't checked yet",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_BOAT_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"impeller_shriek": +0.08, "exhaust_system_leak": +0.08, "lower_unit_bearing": +0.06},
    },
    "mileage_band": {
        "high": {"impeller_shriek": +0.10, "lower_unit_bearing": +0.08, "engine_knock_low_oil": +0.06},
    },
    "storage_time": {
        "months": {"impeller_shriek": +0.08},
        "season": {"impeller_shriek": +0.10, "lower_unit_bearing": +0.06},
    },
    "first_start_of_season": {
        "yes": {"impeller_shriek": +0.10, "lower_unit_bearing": +0.06},
    },
}

STRANGE_NOISE_BOAT_POST_DIAGNOSIS: list[str] = [
    "After repairing the noise, check lower unit oil color — milky oil means water intrusion and requires immediate seal replacement even if the oil level seems ok.",
    "Inspect the impeller as a preventive measure whenever the lower unit is open — it's a $20 part that prevents a $2,000 overheating repair.",
]
