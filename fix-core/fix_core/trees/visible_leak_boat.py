"""
Visible leak diagnostic tree — boat / marine variant.

Marine leaks are more serious than automotive — a significant leak can sink
a boat. Key marine-specific leaks: raw water from impeller housing,
fresh/coolant from heat exchanger, fuel from carb or tank (fire hazard),
and lower unit oil (milky from water intrusion).
"""

VISIBLE_LEAK_BOAT_HYPOTHESES: dict[str, dict] = {
    "raw_water_leak": {
        "label": "Raw water (seawater / lake water) leak — impeller housing, through-hull fitting, or hose",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Water pump impeller kit", "notes": "A leaking impeller housing is a common source; worn impeller or housing O-ring allows water to seep when running"},
            {"name": "Marine hose and clamps (stainless)", "notes": "Raw water hoses are constantly wet — inspect all clamps for corrosion and hoses for cracking"},
            {"name": "Through-hull fitting and seacock", "notes": "Inspect where raw water enters the hull; the seacock packing nut may need tightening or repacking"},
        ],
    },
    "fuel_leak": {
        "label": "Fuel leak — from carburetor, fuel line, primer bulb, or tank fitting (fire and explosion hazard)",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine fuel line (USCG A1 or A2 rated)", "notes": "SAFETY: fuel in the bilge is a serious explosion risk. Ventilate the bilge before starting the engine. Only use USCG-rated marine fuel hose."},
            {"name": "Fuel primer bulb", "notes": "Primer bulbs crack from UV exposure and ethanol fuel — inspect for cracking and replace every 2–3 years"},
            {"name": "Carburetor float needle and seat", "notes": "A leaking needle seat allows fuel to overflow from the carb bowl"},
        ],
    },
    "engine_oil_leak": {
        "label": "Engine oil leak — valve cover gasket, oil pan, or front/rear crank seal",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve cover gasket", "notes": "Most common engine oil seep point; inexpensive gasket repair"},
            {"name": "Oil drain plug with washer", "notes": "Check drain plug and O-ring; easy to strip on aluminum pans"},
        ],
    },
    "lower_unit_oil": {
        "label": "Lower unit gear oil leak — prop shaft seal, drain/fill plug, or housing crack",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Lower unit gear oil (SAE 90 or per spec)", "notes": "If the lower unit oil is milky/white, water has entered through a failed prop shaft seal — requires seal replacement"},
            {"name": "Prop shaft seal (lower unit)", "notes": "Most common cause of lower unit oil loss; contact with fishing line or debris accelerates seal wear"},
            {"name": "Lower unit drain/fill screws with new crush washers", "notes": "Aluminum drain screws strip easily — use new sealing washers each time"},
        ],
    },
    "coolant_fresh_water": {
        "label": "Coolant or fresh water leak — heat exchanger, hose, or thermostat housing (closed-cooling systems)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Coolant hose and clamps", "notes": "Closed-cooling (fresh water only) system hoses run at high temperature — inspect for soft spots or swelling"},
            {"name": "Heat exchanger", "notes": "Internal tube failure causes coolant and raw water to mix; white deposits inside are a sign of scale from sea water"},
        ],
    },
    "bilge_water_normal": {
        "label": "Normal bilge water accumulation — not a mechanical leak",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Bilge pump and float switch", "notes": "All boats accumulate some bilge water from rain, spray, and condensation. A working bilge pump and float switch should handle normal accumulation."},
        ],
    },
    "power_steering_hydraulic": {
        "label": "Power steering or trim hydraulic fluid leak (inboard/sterndrive with hydraulic steering)",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic steering hose and fittings", "notes": "Check hose connections at the helm pump and ram cylinder; tighten or replace leaking fittings"},
            {"name": "Steering fluid (Dexron ATF or per spec)", "notes": "Low fluid causes loss of power assist — check reservoir level and top up if needed"},
        ],
    },
}

VISIBLE_LEAK_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the leaking fluid look, smell, and feel like?",
        "options": [
            {
                "match": "gasoline_smell",
                "label": "Clear to light yellow with strong gasoline smell",
                "deltas": {
                    "fuel_leak": +0.65,
                    "raw_water_leak": -0.20,
                    "engine_oil_leak": -0.10,
                },
                "eliminate": ["coolant_fresh_water", "lower_unit_oil", "bilge_water_normal"],
                "next_node": "fuel_safety",
            },
            {
                "match": "clear_no_smell",
                "label": "Clear, no significant smell (could be water)",
                "deltas": {
                    "raw_water_leak": +0.40,
                    "bilge_water_normal": +0.20,
                    "coolant_fresh_water": +0.15,
                    "fuel_leak": -0.20,
                },
                "eliminate": ["engine_oil_leak", "lower_unit_oil"],
                "next_node": "fuel_safety",
            },
            {
                "match": "brown_oily",
                "label": "Brown, dark, or amber — oily texture",
                "deltas": {
                    "engine_oil_leak": +0.35,
                    "lower_unit_oil": +0.25,
                    "power_steering_hydraulic": +0.10,
                    "fuel_leak": -0.15,
                },
                "eliminate": ["raw_water_leak", "bilge_water_normal"],
                "next_node": "fuel_safety",
            },
            {
                "match": "milky_white",
                "label": "Milky or white — could be coolant or oil mixed with water",
                "deltas": {
                    "lower_unit_oil": +0.40,
                    "coolant_fresh_water": +0.25,
                    "engine_oil_leak": +0.10,
                },
                "eliminate": ["fuel_leak", "bilge_water_normal"],
                "next_node": "fuel_safety",
            },
        ],
    },

    "fuel_safety": {
        "question": "Is there a fuel smell in the bilge or enclosed engine compartment? (This is a safety-critical question.)",
        "options": [
            {
                "match": "strong_fuel_smell",
                "label": "Yes — strong fuel smell in the bilge or engine compartment",
                "deltas": {
                    "fuel_leak": +0.35,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
            {
                "match": "no_fuel_smell",
                "label": "No fuel smell",
                "deltas": {
                    "fuel_leak": -0.15,
                    "raw_water_leak": +0.05,
                    "engine_oil_leak": +0.05,
                },
                "eliminate": [],
                "next_node": "leak_location",
            },
        ],
    },

    "leak_location": {
        "question": "Where is the fluid coming from on the boat?",
        "options": [
            {
                "match": "bilge_under_engine",
                "label": "Bilge beneath the engine",
                "deltas": {
                    "raw_water_leak": +0.15,
                    "engine_oil_leak": +0.15,
                    "fuel_leak": +0.10,
                    "coolant_fresh_water": +0.05,
                    "bilge_water_normal": +0.10,
                },
                "eliminate": [],
                "next_node": "leak_volume",
            },
            {
                "match": "lower_unit_prop",
                "label": "Lower unit / near the propeller",
                "deltas": {
                    "lower_unit_oil": +0.50,
                    "raw_water_leak": +0.10,
                },
                "eliminate": ["fuel_leak", "coolant_fresh_water", "bilge_water_normal"],
                "next_node": "leak_volume",
            },
            {
                "match": "fuel_tank_carb",
                "label": "Near the fuel tank, carb/injectors, or fuel lines",
                "deltas": {
                    "fuel_leak": +0.50,
                },
                "eliminate": ["raw_water_leak", "lower_unit_oil", "coolant_fresh_water"],
                "next_node": "leak_volume",
            },
            {
                "match": "through_hull",
                "label": "Through-hull fitting, sea cock, or drain plug",
                "deltas": {
                    "raw_water_leak": +0.60,
                    "bilge_water_normal": +0.10,
                },
                "eliminate": ["fuel_leak", "engine_oil_leak", "lower_unit_oil"],
                "next_node": "leak_volume",
            },
        ],
    },

    "leak_volume": {
        "question": "How much fluid is accumulating and how quickly?",
        "options": [
            {
                "match": "minor_seep",
                "label": "Minor seep — small stain or slight moisture, no significant pooling",
                "deltas": {
                    "engine_oil_leak": +0.05,
                    "lower_unit_oil": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "steady_drip_puddle",
                "label": "Steady drip — puddle forming in the bilge or on the dock after running",
                "deltas": {
                    "raw_water_leak": +0.10,
                    "fuel_leak": +0.10,
                    "lower_unit_oil": +0.05,
                },
                "eliminate": ["bilge_water_normal"],
                "next_node": None,
            },
            {
                "match": "fast_accumulation",
                "label": "Fast accumulation — significant volume in the bilge (SAFETY: shut off engine now)",
                "deltas": {
                    "raw_water_leak": +0.20,
                    "fuel_leak": +0.15,
                    "coolant_fresh_water": +0.10,
                },
                "eliminate": ["bilge_water_normal", "power_steering_hydraulic"],
                "next_node": None,
            },
        ],
    },
}

VISIBLE_LEAK_BOAT_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"raw_water_leak": +0.10, "lower_unit_oil": +0.08, "coolant_fresh_water": +0.06},
    },
    "mileage_band": {
        "high": {"engine_oil_leak": +0.08, "lower_unit_oil": +0.08, "raw_water_leak": +0.06},
    },
    "storage_time": {
        "months": {"fuel_leak": +0.08, "raw_water_leak": +0.06},
        "season": {"fuel_leak": +0.10, "raw_water_leak": +0.06, "lower_unit_oil": +0.06},
    },
    "first_start_of_season": {
        "yes": {"fuel_leak": +0.10, "raw_water_leak": +0.06, "engine_oil_leak": +0.06},
    },
}

VISIBLE_LEAK_BOAT_POST_DIAGNOSIS: list[str] = [
    "After repairing the leak, run the engine at the dock and inspect the bilge area again — marine leaks often have secondary sources near the primary.",
    "Any fuel leak in the bilge is an explosion risk: ventilate the bilge with the blower for 4+ minutes before starting the engine.",
]
