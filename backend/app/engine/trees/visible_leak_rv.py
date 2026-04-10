"""
Visible leak diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Propane (LP) system: tank connections, regulator, copper tubing, flex hose to
  appliances — LP leaks are a fire and explosion hazard; safety stop required
- Fresh water / grey water / black water plumbing — completely absent from car trees
- Roof leaks from sealant failure — the dominant coach-specific leak category
- Slide-out seal and gasket leaks — water intrusion around slides is the #1 RV
  maintenance complaint
- Engine coolant and engine oil leaks are the same as truck/car but harder to inspect
  on rear-mounted diesel pushers
- Hydraulic fluid (leveling jacks) is a separate fluid system unique to RVs
"""

VISIBLE_LEAK_RV_HYPOTHESES: dict[str, dict] = {
    "lp_gas_leak": {
        "label": "LP (propane) gas leak — smell of rotten eggs/sulfur, hissing near tank or appliance",
        "prior": 0.22,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "LP line fitting or flex hose", "notes": "STOP: if you smell propane, turn off the LP tank valve at the tank immediately, open all windows, and do not use any switches or flames; spray soapy water on fittings to locate the leak"},
            {"name": "Two-stage LP regulator", "notes": "Regulators crack and develop leaks around the diaphragm housing — leaks are most visible at the regulator body, not the fitting"},
        ],
    },
    "roof_or_slide_water": {
        "label": "Roof seal failure or slide-out seal leak (interior water stains, wet ceiling, soft floor at slide edge)",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Dicor self-leveling roof sealant (for rubber EPDM or TPO roof)", "notes": "Apply around all roof penetrations: vents, AC units, antenna bases; lap sealant cracks within 3–5 years on southern exposures; inspect annually"},
            {"name": "Slide-out room seal / wiper seal", "notes": "Top, bottom, and side slide seals are rubber or brush-type — leaks at the top corner of a slide are most common; apply 303 Protectant to rubber seals annually to prevent cracking"},
        ],
    },
    "freshwater_plumbing": {
        "label": "Fresh water plumbing leak (fitting, flex hose, or water pump — water under dinette, inside cabinets)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pex plumbing fitting or push-to-connect fitting", "notes": "RV water lines are Pex or polyethylene with push-fit fittings — fittings loosen from vibration; run the water pump and trace the wet area to the source"},
            {"name": "Fresh water pump", "notes": "Pump body can crack from freezing or from running dry — inspect the pump body itself, not just the hose connections"},
        ],
    },
    "grey_black_tank": {
        "label": "Grey or black water tank fitting leak (sewage smell, wet under bathroom floor or tank bay)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Tank valve (grey or black dump valve)", "notes": "Dump valves corrode and fail to seal fully — a slow leak is almost always the dump valve blade; close the valve and check if the leak stops to confirm"},
            {"name": "Tank fitting / ABS flange fitting", "notes": "Tank ABS plastic fittings can crack at the tank weld; if the tank itself is cracked, replacement is required"},
        ],
    },
    "engine_coolant_oil": {
        "label": "Engine coolant or oil leak — chassis engine (puddle under engine bay, steam from engine compartment)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Radiator hose or heater hose", "notes": "Diesel pusher: radiator and hoses are at the rear; access requires opening the engine bay door; inspect all hose clamps and look for weeping at hose ends"},
            {"name": "Oil drain plug or oil filter", "notes": "Rear-engine diesels: oil filter is accessible from the engine bay; look for oil drips on the frame below the engine before assuming a major seal leak"},
        ],
    },
    "hydraulic_fluid": {
        "label": "Hydraulic fluid leak from leveling jack system (oily fluid near jacks or under the coach)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Hydraulic jack cylinder seal kit", "notes": "Hydraulic jack cylinders develop weeping seals after years of use — the seal kit is jack-model-specific; confirm HWH, Lippert, or Equalizer brand before ordering"},
            {"name": "Hydraulic fluid (leveling system)", "notes": "Top up after seal repair — use the manufacturer-specified fluid, not generic ATF; some systems use a specific ISO hydraulic oil"},
        ],
    },
    "water_heater_leak": {
        "label": "Water heater tank or pressure relief valve leak (hot water smell, wet in water heater compartment)",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pressure relief valve (T&P valve — water heater)", "notes": "T&P valve drips when the hot water temperature or pressure is too high — check water heater thermostat setting and water pressure reducer; replace T&P valve if it drips at normal pressure"},
            {"name": "Water heater anode rod and drain fitting", "notes": "Drain fitting and anode rod threads corrode and leak — replace anode rod annually and use Teflon tape on all water heater pipe threads"},
        ],
    },
}

VISIBLE_LEAK_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the nature of the leak?",
        "options": [
            {
                "match": "smell_gas",
                "label": "Smell of rotten eggs or sulfur — possible propane/LP gas leak",
                "deltas": {
                    "lp_gas_leak": +0.85,
                },
                "eliminate": [],
                "next_node": "lp_safety",
            },
            {
                "match": "water_interior",
                "label": "Water inside the coach — wet ceiling, wet floor, or water stains near a slide or roof vent",
                "deltas": {
                    "roof_or_slide_water": +0.60,
                    "freshwater_plumbing": +0.15,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "puddle_under",
                "label": "Puddle or drip under the coach exterior — on the ground beneath it",
                "deltas": {
                    "freshwater_plumbing": +0.20,
                    "engine_coolant_oil": +0.18,
                    "grey_black_tank": +0.15,
                    "hydraulic_fluid": +0.12,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "sewage_smell",
                "label": "Sewage smell or wet under the bathroom floor / tank bay",
                "deltas": {
                    "grey_black_tank": +0.60,
                    "freshwater_plumbing": +0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "hot_water_bay",
                "label": "Leak in the water heater compartment (exterior access door bay)",
                "deltas": {
                    "water_heater_leak": +0.60,
                    "freshwater_plumbing": +0.15,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
        ],
    },

    "lp_safety": {
        "question": "SAFETY CHECK: Have you turned off the LP tank valve at the tank?",
        "options": [
            {
                "match": "lp_off",
                "label": "Yes — LP tank valve is closed; no flame sources nearby",
                "deltas": {
                    "lp_gas_leak": +0.10,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "lp_not_off",
                "label": "No — I haven't turned off the LP yet",
                "deltas": {
                    "lp_gas_leak": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },

    "leak_location": {
        "question": "Where is the leak coming from or where is the wet area located?",
        "options": [
            {
                "match": "roof_ceiling",
                "label": "Roof or ceiling — wet spots on the ceiling or around roof vents/AC",
                "deltas": {
                    "roof_or_slide_water": +0.35,
                    "freshwater_plumbing": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "slide_edge",
                "label": "Near the slide-out — wet floor at the slide edge or wall near slide",
                "deltas": {
                    "roof_or_slide_water": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "under_cabinets",
                "label": "Under a kitchen or bathroom cabinet — inside the coach",
                "deltas": {
                    "freshwater_plumbing": +0.40,
                    "water_heater_leak": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "engine_bay",
                "label": "Engine bay or below the engine (rear on diesel pushers)",
                "deltas": {
                    "engine_coolant_oil": +0.50,
                    "hydraulic_fluid": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "jack_area",
                "label": "Near a leveling jack or under the coach frame near a jack",
                "deltas": {
                    "hydraulic_fluid": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "roof_or_slide_water": +0.10,
            "engine_coolant_oil": +0.08,
            "hydraulic_fluid": +0.06,
        },
    },
    "storage_time": {
        "long": {
            "freshwater_plumbing": +0.10,
            "roof_or_slide_water": +0.08,
            "grey_black_tank": +0.06,
        },
    },
    "climate": {
        "cold": {
            "freshwater_plumbing": +0.12,
        },
    },
}

VISIBLE_LEAK_RV_POST_DIAGNOSIS: list[str] = [
    "SAFETY: If an LP leak was suspected and confirmed, do not re-enter the coach until the area is fully ventilated and the leak source is repaired and re-tested with soapy water — LP gas is heavier than air and pools in floor areas and under the coach.",
    "Roof sealant should be inspected and reapplied every 12 months on rubber (EPDM/TPO) roofs — use Dicor self-leveling sealant on horizontal surfaces and Dicor lap sealant on vertical surfaces; do not use standard silicone, which does not bond to RV roofing membranes.",
    "Before winterizing or after returning from winter storage, run all water system lines under pressure and check every cabinet base for moisture — freeze damage in RV water lines always appears at fittings and valves, not in the middle of a straight run.",
]
