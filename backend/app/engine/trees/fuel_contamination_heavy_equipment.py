"""
Fuel contamination diagnostic tree — heavy equipment (diesel).

Covers bad fuel quality issues that cause running problems on diesel equipment:
- Water in fuel (most common on stored or tropical-climate equipment)
- Diesel bug (microbial growth / algae contamination)
- Wrong fuel type (petrol in diesel, mixing grades)
- Fuel oxidation and varnish (long storage)
- DEF contamination of diesel fuel (AdBlue in diesel tank)
- Sediment from old storage tanks

Fuel contamination is an important diagnostic category because it:
1. Causes symptoms identical to injector failure, fuel pump failure, or filter restriction
2. Is non-obvious — the operator may not know the fuel is bad
3. Can destroy expensive injection components if not caught early
4. Requires a specific remediation (drain and flush) rather than part replacement
"""

FUEL_CONTAMINATION_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "water_in_fuel": {
        "label": "Water contamination in diesel fuel (phase separation, condensation, or flooding)",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel filter / water separator", "notes": "Drain the water separator bowl first — visible water confirms contamination"},
            {"name": "Fuel system conditioner / water remover", "notes": "Add after drain and filter replacement to absorb residual moisture"},
        ],
    },
    "diesel_bug": {
        "label": "Diesel bug — microbial growth (bacteria/fungi) in fuel tank",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Diesel biocide treatment (e.g. Biobor JF)", "notes": "Treat after draining contaminated fuel; clean tank before treating"},
            {"name": "Fuel filter set (pre and secondary)", "notes": "Replace both after treating for diesel bug — filters will be clogged with biomass"},
        ],
    },
    "wrong_fuel": {
        "label": "Wrong fuel type — petrol/gasoline in diesel tank, or incorrect diesel grade",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "fuel_oxidation": {
        "label": "Oxidized or degraded fuel — fuel stored too long, varnish or gum formation",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Diesel fuel stabilizer (for prevention)", "notes": "For remediation: drain and replace with fresh fuel; run system until clear"},
        ],
    },
    "def_in_diesel": {
        "label": "DEF (AdBlue) accidentally added to diesel fuel tank",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "sediment_contamination": {
        "label": "Sediment or debris from fuel storage tank or old tank rust",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Inline fuel filter / strainer", "notes": "Add an inline pre-filter upstream of the primary filter to catch tank debris"},
        ],
    },
    "fuel_wax": {
        "label": "Waxed fuel — diesel gelled in cold weather (wax crystals blocking filters)",
        "prior": 0.07,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel anti-gel additive", "notes": "Add to prevent in future; for gelled fuel: warm the tank and filters, replace the primary filter"},
        ],
    },
}

FUEL_CONTAMINATION_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "What symptom made you suspect a fuel quality problem?",
        "options": [
            {
                "match": "runs_rough_filter_symptoms",
                "label": "Engine runs rough, lacks power, or dies — similar to a fuel filter blockage",
                "deltas": {
                    "water_in_fuel": +0.15,
                    "diesel_bug": +0.15,
                    "fuel_oxidation": +0.15,
                    "sediment_contamination": +0.10,
                    "fuel_wax": +0.10,
                },
                "eliminate": [],
                "next_node": "fuel_appearance",
            },
            {
                "match": "filter_clogging_repeatedly",
                "label": "Fuel filters keep clogging much faster than normal",
                "deltas": {
                    "diesel_bug": +0.30,
                    "sediment_contamination": +0.25,
                    "water_in_fuel": +0.10,
                    "wrong_fuel": -0.05,
                },
                "eliminate": ["wrong_fuel", "fuel_wax", "def_in_diesel"],
                "next_node": "fuel_appearance",
            },
            {
                "match": "wont_start_after_storage",
                "label": "Won't start or runs poorly after being stored for a while",
                "deltas": {
                    "fuel_oxidation": +0.30,
                    "water_in_fuel": +0.20,
                    "diesel_bug": +0.15,
                    "fuel_wax": +0.08,
                },
                "eliminate": ["wrong_fuel", "def_in_diesel"],
                "next_node": "fuel_appearance",
            },
            {
                "match": "known_misfuel",
                "label": "Someone may have put the wrong fuel in the tank",
                "deltas": {
                    "wrong_fuel": +0.45,
                    "def_in_diesel": +0.20,
                },
                "eliminate": ["diesel_bug", "fuel_oxidation", "fuel_wax"],
                "next_node": "fuel_appearance",
            },
            {
                "match": "cold_weather_issues",
                "label": "Problems started in cold weather — machine ran fine before the cold snap",
                "deltas": {
                    "fuel_wax": +0.45,
                    "water_in_fuel": +0.10,
                },
                "eliminate": ["diesel_bug", "wrong_fuel", "def_in_diesel"],
                "next_node": "fuel_appearance",
            },
            {
                "match": "rain_or_storm_exposure",
                "label": "Problems started after heavy rain, flooding, or storm — machine may have been exposed to water",
                "deltas": {
                    "water_in_fuel": +0.30,
                    "wrong_fuel": -0.20,
                    "fuel_wax": -0.15,
                    "def_in_diesel": -0.10,
                    "fuel_oxidation": -0.05,
                },
                "eliminate": ["fuel_wax", "def_in_diesel"],
                "next_node": "rain_confirmation",
            },
        ],
    },

    "rain_confirmation": {
        "question": (
            "A few quick checks on the water ingress path. "
            "Was the machine sitting outside unprotected during or after the storm? "
            "Have you inspected the fuel cap and its rubber seal for damage? "
            "And have you checked the water separator — is there visible water in it?"
        ),
        "options": [
            {
                "match": "outside_separator_wet",
                "label": "Yes — machine was outside during the storm, and the water separator is full or shows visible water",
                "deltas": {
                    "water_in_fuel": +0.35,
                    "wrong_fuel": -0.20,
                    "diesel_bug": +0.05,
                },
                "eliminate": ["wrong_fuel", "fuel_wax", "def_in_diesel"],
                "next_node": "fuel_source",
            },
            {
                "match": "outside_cap_damaged",
                "label": "Machine was outside and the fuel cap or its seal looks damaged or wasn't fully closed",
                "deltas": {
                    "water_in_fuel": +0.35,
                    "wrong_fuel": -0.20,
                    "diesel_bug": +0.05,
                },
                "eliminate": ["wrong_fuel", "fuel_wax", "def_in_diesel"],
                "next_node": "fuel_source",
            },
            {
                "match": "outside_separator_not_checked",
                "label": "Machine was outside during the storm but the separator has not been checked yet",
                "deltas": {
                    "water_in_fuel": +0.20,
                    "wrong_fuel": -0.10,
                },
                "eliminate": ["fuel_wax", "def_in_diesel"],
                "next_node": "fuel_appearance",
            },
            {
                "match": "sheltered_or_uncertain",
                "label": "Machine was sheltered or covered, or storm exposure is uncertain",
                "deltas": {
                    "water_in_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": "fuel_appearance",
            },
        ],
    },

    "fuel_appearance": {
        "question": "Can you drain a small sample from the water separator or primary filter bowl and look at it? What does the fuel look like?",
        "options": [
            {
                "match": "water_visible_or_cloudy",
                "label": "Cloudy, milky, or you can see a water layer at the bottom",
                "deltas": {
                    "water_in_fuel": +0.40,
                },
                "eliminate": ["wrong_fuel", "def_in_diesel", "fuel_wax"],
                "next_node": "fuel_source",
            },
            {
                "match": "dark_or_slimy",
                "label": "Dark brown or black, slimy, or has floating particles",
                "deltas": {
                    "diesel_bug": +0.40,
                    "sediment_contamination": +0.15,
                    "fuel_oxidation": +0.10,
                },
                "eliminate": ["wrong_fuel", "def_in_diesel", "fuel_wax"],
                "next_node": "fuel_source",
            },
            {
                "match": "pale_or_clear_petrol_smell",
                "label": "Pale yellow / clear and smells lighter than normal diesel",
                "deltas": {
                    "wrong_fuel": +0.45,
                },
                "eliminate": ["diesel_bug", "water_in_fuel", "fuel_wax"],
                "next_node": "fuel_source",
            },
            {
                "match": "wax_crystals",
                "label": "Has wax crystals, looks cloudy-white, or is thick/sluggish",
                "deltas": {
                    "fuel_wax": +0.45,
                },
                "eliminate": ["diesel_bug", "wrong_fuel", "def_in_diesel"],
                "next_node": "fuel_source",
            },
            {
                "match": "looks_normal",
                "label": "Looks normal — clear amber diesel",
                "deltas": {
                    "fuel_oxidation": +0.10,
                    "def_in_diesel": +0.08,
                    "sediment_contamination": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_source",
            },
            {
                "match": "cant_sample",
                "label": "Can't take a sample right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "fuel_source",
            },
        ],
    },

    "fuel_source": {
        "question": "Where was the fuel sourced from? Has the machine been sitting, shared fuel with other equipment, or fuelled from an older storage tank?",
        "options": [
            {
                "match": "long_storage",
                "label": "Fuel has been in the tank for months (machine sat unused)",
                "deltas": {
                    "fuel_oxidation": +0.25,
                    "diesel_bug": +0.15,
                    "water_in_fuel": +0.10,
                },
                "eliminate": ["wrong_fuel"],
                "next_node": None,
            },
            {
                "match": "bulk_storage_tank",
                "label": "Fuelled from a bulk storage tank on site",
                "deltas": {
                    "water_in_fuel": +0.22,
                    "diesel_bug": +0.20,
                    "sediment_contamination": +0.18,
                },
                "eliminate": ["wrong_fuel"],
                "next_node": None,
            },
            {
                "match": "retail_pump_recent",
                "label": "Recently fuelled from a retail pump or delivery truck",
                "deltas": {
                    "water_in_fuel": +0.03,
                },
                "eliminate": ["diesel_bug", "fuel_oxidation"],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Not sure of the fuel source",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

FUEL_CONTAMINATION_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"sediment_contamination": +0.05},
        "muddy": {"water_in_fuel": +0.08, "sediment_contamination": +0.05},
        "marine": {"water_in_fuel": +0.12, "diesel_bug": +0.08},
        "urban": {},
        "wet_outdoor": {"water_in_fuel": +0.18, "wrong_fuel": -0.08, "diesel_bug": +0.05},
    },
    "hours_band": {
        "long_storage": {
            "fuel_oxidation": +0.20,
            "diesel_bug": +0.12,
            "water_in_fuel": +0.10,
            "fuel_wax": +0.05,
        },
    },
    "climate": {
        "cold": {"fuel_wax": +0.15},
        "hot": {"diesel_bug": +0.08, "fuel_oxidation": +0.05},
    },
}

FUEL_CONTAMINATION_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "DEF in diesel is a serious emergency: even small amounts of DEF (AdBlue) in the diesel tank will crystallize and destroy injection pumps and injectors. Drain immediately, flush the entire system, and replace all filters before restarting.",
    "Diesel bug remediation: drain contaminated fuel, clean the tank interior, treat with biocide (e.g. Biobor JF), replace all fuel filters, then refuel with fresh diesel. Prevention: keep fuel tanks as full as possible to reduce condensation air space.",
    "Oxidized fuel: gums and varnish from degraded diesel can coat injector nozzles. After remediation, consider an injector cleaner additive for the first 2–3 fill-ups.",
    "Bulk storage tanks: check for water at the bottom of the storage tank annually using water-finding paste on a dipstick — water always sinks to the bottom and accumulates over time.",
    "Storm / rain water ingress: if the machine has NOT been restarted since water contamination was discovered — do not attempt to start it. Running a diesel injection system with significant water in the fuel can destroy injectors and the injection pump within seconds. Drain the water separator completely, replace the primary fuel filter, then drain and inspect the tank before attempting to restart.",
    "After storm exposure: check the fuel cap O-ring and cap seal for cracks or deformation — this is the most common water ingress point on outdoor equipment. Replace the cap seal as a matter of course after any flooding event.",
]
