"""
Crank-no-start diagnostic tree — PWC (personal watercraft) variant.

Flooding from repeated starting attempts is very common on carbureted
PWCs. Stale fuel after winter storage is the dominant cause on
recreational craft used only a few months per year. Fuel-injected
(DMPFI) Sea-Doos and modern Yamahas behave more like EFI cars.
"""

CRANK_NO_START_PWC_HYPOTHESES: dict[str, dict] = {
    "stale_fuel": {
        "label": "Stale fuel or varnished fuel system — ethanol separation after months in tank",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fresh fuel (premium recommended for Sea-Doo supercharged)", "notes": "Drain the tank and refill with fresh fuel. Phase separation (ethanol + water layer) leaves gum in injectors and carbs."},
            {"name": "Fuel system treatment / injector cleaner", "notes": "For EFI models, add injector cleaner before condemning injectors"},
            {"name": "Carb rebuild kit", "notes": "For carbureted models, a full clean or rebuild after winter storage is standard maintenance"},
        ],
    },
    "flooded": {
        "label": "Engine flooded from repeated cranking or improper starting procedure",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh spark plugs", "notes": "Remove plugs, tilt nose up to drain fuel from cylinders, crank briefly to blow out fuel, reinstall plugs and try again — choke/primer OFF"},
        ],
    },
    "fouled_plugs": {
        "label": "Fouled spark plugs — from flooding or carbon buildup",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plugs (OEM heat range — critical on PWCs)", "notes": "PWC plugs must match OEM heat range exactly — wrong heat range causes pre-ignition or persistent fouling"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem — fuel pump, VST, or injector (EFI models)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel pump / fuel pump module", "notes": "EFI models: no fuel pressure at the rail = fuel pump or fuel pump relay"},
            {"name": "Fuel injector cleaning service", "notes": "Partially clogged injectors don't deliver enough fuel to start — send for ultrasonic cleaning before replacing"},
        ],
    },
    "crankshaft_position_sensor": {
        "label": "Crankshaft position sensor failure — no RPM signal to ECM (EFI models)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Crankshaft position sensor", "notes": "EFI models: cranks normally but never fires = often CPS failure. Scan tool will show no RPM signal."},
        ],
    },
    "vapor_lock": {
        "label": "Vapor lock or fuel line air intrusion — fuel boiling in warm temperatures",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel line (heat-resistant)", "notes": "Vapor lock in a hot hull on a summer day — let craft cool in shade 15 minutes, then try again. Replace fuel lines if cracked or kinked."},
        ],
    },
}

CRANK_NO_START_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "Has the PWC been in storage, or was it running recently?",
        "options": [
            {
                "match": "after_storage",
                "label": "First start after winter or extended storage",
                "deltas": {
                    "stale_fuel": +0.35,
                    "fouled_plugs": +0.12,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": "flood_check",
            },
            {
                "match": "ran_fine_recently",
                "label": "Was running fine until recently / during this season",
                "deltas": {
                    "flooded": +0.20,
                    "fouled_plugs": +0.18,
                    "crankshaft_position_sensor": +0.12,
                    "stale_fuel": -0.10,
                },
                "eliminate": [],
                "next_node": "flood_check",
            },
            {
                "match": "hot_soak",
                "label": "Ran fine, stopped on the water, and now won't restart (hot engine)",
                "deltas": {
                    "vapor_lock": +0.30,
                    "flooded": +0.20,
                    "fuel_delivery": +0.15,
                },
                "eliminate": ["stale_fuel"],
                "next_node": "flood_check",
            },
        ],
    },

    "flood_check": {
        "question": "How many times did you crank it trying to start it before this check?",
        "options": [
            {
                "match": "cranked_many",
                "label": "Cranked it repeatedly — 10 or more attempts",
                "deltas": {
                    "flooded": +0.45,
                    "fouled_plugs": +0.15,
                },
                "eliminate": ["vapor_lock"],
                "next_node": "fuel_check",
            },
            {
                "match": "cranked_few",
                "label": "Only 2–3 attempts",
                "deltas": {
                    "flooded": -0.10,
                    "stale_fuel": +0.08,
                    "fuel_delivery": +0.08,
                },
                "eliminate": [],
                "next_node": "fuel_check",
            },
        ],
    },

    "fuel_check": {
        "question": "Is the fuel fresh, and is there adequate fuel in the tank?",
        "options": [
            {
                "match": "stale_low_fuel",
                "label": "Old fuel from storage, or tank is nearly empty",
                "deltas": {
                    "stale_fuel": +0.35,
                    "vapor_lock": +0.10,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
            {
                "match": "fresh_fuel_ok",
                "label": "Fresh fuel this season, tank has adequate fuel",
                "deltas": {
                    "stale_fuel": -0.15,
                    "fuel_delivery": +0.10,
                    "crankshaft_position_sensor": +0.08,
                },
                "eliminate": [],
                "next_node": "spark_check",
            },
        ],
    },

    "spark_check": {
        "question": "Have you pulled the spark plugs? What do they look like?",
        "options": [
            {
                "match": "plugs_wet_fuel",
                "label": "Plugs are wet and smell strongly of fuel",
                "deltas": {
                    "flooded": +0.55,
                    "fouled_plugs": +0.20,
                },
                "eliminate": ["crankshaft_position_sensor", "stale_fuel", "vapor_lock"],
                "next_node": None,
            },
            {
                "match": "plugs_normal",
                "label": "Plugs look dry and normal",
                "deltas": {
                    "stale_fuel": +0.15,
                    "fuel_delivery": +0.15,
                    "crankshaft_position_sensor": +0.12,
                    "flooded": -0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "plugs_black_carbon",
                "label": "Plugs are black and carbonated",
                "deltas": {
                    "fouled_plugs": +0.45,
                    "stale_fuel": +0.15,
                },
                "eliminate": ["crankshaft_position_sensor", "vapor_lock"],
                "next_node": None,
            },
            {
                "match": "not_checked",
                "label": "Haven't checked the plugs",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"fouled_plugs": +0.06, "fuel_delivery": +0.06},
    },
    "storage_time": {
        "months": {"stale_fuel": +0.20, "fouled_plugs": +0.08, "fuel_delivery": +0.06},
        "season": {"stale_fuel": +0.25, "fouled_plugs": +0.10, "fuel_delivery": +0.08},
    },
    "first_start_of_season": {
        "yes": {"stale_fuel": +0.20, "fouled_plugs": +0.08},
    },
    "climate": {
        "hot": {"vapor_lock": +0.10, "flooded": +0.06},
    },
}

CRANK_NO_START_PWC_POST_DIAGNOSIS: list[str] = [
    "After starting, run the PWC at the dock for 5 minutes to verify idle stability and check for any new fault codes (EFI models).",
    "If the cause was stale fuel, drain and replace the fuel filter and run the tank low before adding fresh fuel next season.",
    "Sea-Doo supercharged models require minimum 91 octane — ethanol-blend E85 will cause detonation and premature intercooler failure.",
]
