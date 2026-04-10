"""
Cranks but won't start diagnostic tree — truck/diesel variant.

Diesel cranks but won't fire. No spark plugs involved — diesel relies on
compression heat and fuel pressure. Common causes: air in fuel lines,
failed lift pump, glow plug system faults, water-contaminated fuel,
and fuel gelling. Always check wait-to-start light before cranking.
"""

CRANK_NO_START_TRUCK_HYPOTHESES: dict[str, dict] = {
    "glow_plug_system": {
        "label": "Glow plug system fault — plugs or controller not heating cylinders for cold start",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test each with a multimeter — 2–6 Ω is normal. A shorted or open plug prevents that cylinder from firing cold."},
            {"name": "Glow plug controller / relay", "notes": "Check fuse and relay first. If wait-to-start light doesn't illuminate, the controller may be faulty."},
        ],
    },
    "fuel_water_separator": {
        "label": "Water in diesel fuel — fuel/water separator full or fuel contaminated",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel/water separator filter", "notes": "Drain the separator bowl first — water settles at the bottom. If bowl is nearly full of water, drain and replace filter."},
        ],
    },
    "air_in_fuel": {
        "label": "Air in fuel system — after filter replacement, fuel line disconnect, or empty tank run",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hand primer pump (if equipped)", "notes": "Prime the fuel system until firm before cranking. On common-rail engines, cycling key ON 10+ times primes the system."},
        ],
    },
    "diesel_fuel_gelling": {
        "label": "Partially gelled diesel fuel — wax crystals restricting flow without fully blocking",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel 911 or equivalent gelling treatment", "notes": "Add treatment and bring truck to a warm environment. Replace fuel filter after treatment."},
            {"name": "Diesel fuel filter", "notes": "Gelled fuel permanently clogs filter media — replace after any gelling event"},
        ],
    },
    "lift_pump_failure": {
        "label": "Failed transfer/lift pump — no fuel pressure to injection pump or common rail",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel transfer (lift) pump", "notes": "Mechanical lift pumps on older diesels; electric on modern common-rail. Check for pressure at the filter outlet."},
        ],
    },
    "injection_pump": {
        "label": "Failed or seized injection pump — no fuel delivery regardless of lift pump",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Injection pump (high-pressure pump)", "notes": "Expensive — confirm lift pump is working and fuel is clean before condemning the injection pump"},
        ],
    },
    "clogged_fuel_filter": {
        "label": "Severely clogged diesel fuel filter restricting fuel delivery",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel fuel filter (primary and secondary)", "notes": "Most diesel trucks have two fuel filters. Replace both as a set — secondary filter clogs last but is often the one bypassed."},
        ],
    },
}

CRANK_NO_START_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the outside temperature and how long has the truck been sitting?",
        "options": [
            {
                "match": "cold_overnight",
                "label": "Cold — below freezing and sat overnight or longer",
                "deltas": {
                    "glow_plug_system": +0.25,
                    "diesel_fuel_gelling": +0.20,
                    "fuel_water_separator": +0.05,
                },
                "eliminate": [],
                "next_node": "wait_to_start",
            },
            {
                "match": "warm_or_engine_warm",
                "label": "Warm conditions, or engine was recently running",
                "deltas": {
                    "glow_plug_system": -0.15,
                    "diesel_fuel_gelling": -0.15,
                    "air_in_fuel": +0.15,
                    "lift_pump_failure": +0.10,
                    "clogged_fuel_filter": +0.10,
                },
                "eliminate": [],
                "next_node": "wait_to_start",
            },
            {
                "match": "unknown_temp",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "wait_to_start",
            },
        ],
    },

    "wait_to_start": {
        "question": "Does the wait-to-start (glow plug) indicator light come on when you turn the key to ON and then go out before you crank?",
        "options": [
            {
                "match": "light_works_correctly",
                "label": "Yes — light comes on then goes out normally before cranking",
                "deltas": {
                    "glow_plug_system": -0.20,
                    "air_in_fuel": +0.10,
                    "lift_pump_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_fuel_work",
            },
            {
                "match": "light_missing_or_always_on",
                "label": "No light — never illuminated, or it stays on and never goes out",
                "deltas": {
                    "glow_plug_system": +0.30,
                },
                "eliminate": [],
                "next_node": "recent_fuel_work",
            },
            {
                "match": "no_wait_cranked_immediately",
                "label": "I cranked immediately without waiting for the light — skipped pre-heat",
                "deltas": {
                    "glow_plug_system": +0.15,
                },
                "eliminate": [],
                "next_node": "recent_fuel_work",
            },
        ],
    },

    "recent_fuel_work": {
        "question": "Has any fuel system work been done recently? (Filter change, fuel line disconnect, ran out of fuel, fuel contamination?)",
        "options": [
            {
                "match": "yes_fuel_work",
                "label": "Yes — filter changed, line disconnected, ran empty, or bad fuel added",
                "deltas": {
                    "air_in_fuel": +0.40,
                    "fuel_water_separator": +0.10,
                    "clogged_fuel_filter": +0.10,
                },
                "eliminate": [],
                "next_node": "water_separator",
            },
            {
                "match": "no_fuel_work",
                "label": "No recent fuel system work",
                "deltas": {
                    "air_in_fuel": -0.10,
                    "lift_pump_failure": +0.10,
                    "clogged_fuel_filter": +0.05,
                    "injection_pump": +0.05,
                },
                "eliminate": [],
                "next_node": "water_separator",
            },
        ],
    },

    "water_separator": {
        "question": "Check the fuel/water separator bowl (usually transparent or with a drain). Is there visible water or the bowl is overdue for service?",
        "options": [
            {
                "match": "water_present",
                "label": "Yes — water visible in bowl, or a Water In Fuel (WIF) warning light is on",
                "deltas": {
                    "fuel_water_separator": +0.45,
                    "air_in_fuel": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "bowl_clear",
                "label": "Bowl is clear — no water visible",
                "deltas": {
                    "fuel_water_separator": -0.15,
                    "lift_pump_failure": +0.10,
                    "clogged_fuel_filter": +0.05,
                    "injection_pump": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"glow_plug_system": +0.15, "diesel_fuel_gelling": +0.12},
        "hot": {"lift_pump_failure": +0.08},
    },
    "mileage_band": {
        "high": {"injection_pump": +0.10, "lift_pump_failure": +0.08, "clogged_fuel_filter": +0.06},
    },
    "usage_pattern": {
        "highway": {"clogged_fuel_filter": +0.05},
    },
}

CRANK_NO_START_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After resolving the crank-no-start, bleed the fuel system completely — air in diesel injector lines causes extended hard-start after any fuel system work.",
    "If fuel gelling was the cause, switch to a winter-grade diesel or add a winter anti-gel additive before the next cold event.",
]
