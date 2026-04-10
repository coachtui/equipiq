"""
Loss of power diagnostic tree — motorcycle variant.

Clutch slip is a first-class hypothesis unique to motorcycles — it mimics
power loss perfectly but has nothing to do with the engine. Main jet clogging
(carb bikes) maps to high-RPM/WOT power loss specifically.
"""

LOSS_OF_POWER_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "clutch_slip": {
        "label": "Slipping clutch — engine revs freely but power doesn't reach rear wheel",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Clutch friction plate set", "notes": "Measure plate thickness; worn past spec or glazed plates slip under load"},
            {"name": "Clutch spring set", "notes": "Weak springs cause slip at high RPM/load; measure free length vs. spec"},
        ],
    },
    "clogged_main_jet": {
        "label": "Clogged main jet (carb bikes) — fuel restriction at high throttle",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Main jet (correct size)", "notes": "Power good at low throttle but falls off at mid-high throttle = main circuit; spray carb cleaner through jet"},
            {"name": "Needle clip position", "notes": "Mid-throttle flat spot: raise needle one clip position (richer) to check"},
        ],
    },
    "dirty_air_filter": {
        "label": "Severely clogged air filter — starving engine of air",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter", "notes": "Hold to light — if you can't see through it, replace; common on bikes ridden in dusty conditions"},
        ],
    },
    "worn_piston_rings": {
        "label": "Worn piston rings — low compression causing power loss across all RPM",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Compression gauge (motorcycle adapter)", "notes": "Check compression in each cylinder; below 80% of spec = rings or valves"},
            {"name": "Piston ring set", "notes": "Often paired with piston replacement; confirm with leakdown test"},
        ],
    },
    "valve_not_seating": {
        "label": "Valve not seating — compression leak reducing power",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Leakdown tester", "notes": "Differentiates rings (hissing from oil filler) vs. valves (hissing from intake/exhaust)"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery restriction — clogged petcock, kinked line, or weak fuel pump (EFI)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Inline fuel filter", "notes": "Replace if not serviced recently; especially important on ethanol-blend fuel"},
            {"name": "Fuel pump (EFI bikes)", "notes": "Check fuel pressure if EFI; low pressure at WOT = pump or pressure regulator"},
        ],
    },
    "exhaust_restriction": {
        "label": "Exhaust restriction — baffles clogged or catalytic converter failure (if equipped)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust baffle / insert", "notes": "Remove baffles if serviceable and test — power restoration confirms restriction"},
        ],
    },
}

LOSS_OF_POWER_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "When does the power loss occur — throughout the rev range, only at high RPM/wide-open throttle, or mainly at low RPM under load?",
        "options": [
            {
                "match": "all_throttle",
                "label": "Weak throughout the entire rev range",
                "deltas": {
                    "dirty_air_filter": +0.20,
                    "worn_piston_rings": +0.15,
                    "valve_not_seating": +0.10,
                    "clutch_slip": +0.10,
                    "fuel_delivery": +0.10,
                    "clogged_main_jet": -0.10,
                },
                "eliminate": [],
                "next_node": "clutch_check",
            },
            {
                "match": "high_rpm_only",
                "label": "Only at high RPM or wide-open throttle — fine at low throttle",
                "deltas": {
                    "clogged_main_jet": +0.35,
                    "dirty_air_filter": +0.15,
                    "exhaust_restriction": +0.15,
                    "fuel_delivery": +0.10,
                    "worn_piston_rings": -0.05,
                    "clutch_slip": -0.05,
                },
                "eliminate": [],
                "next_node": "clutch_check",
            },
            {
                "match": "low_rpm_load",
                "label": "Under load at low RPM — struggles uphill or accelerating from a stop",
                "deltas": {
                    "clutch_slip": +0.25,
                    "worn_piston_rings": +0.15,
                    "valve_not_seating": +0.15,
                    "clogged_main_jet": -0.10,
                },
                "eliminate": [],
                "next_node": "clutch_check",
            },
        ],
    },

    "clutch_check": {
        "question": "Test: hold the throttle steady and release the clutch slowly in a low gear at idle — does the engine bog and stall (normal), or does the engine keep revving while the bike barely moves (slipping)?",
        "options": [
            {
                "match": "clutch_normal",
                "label": "Engine bogs and stalls — clutch engages normally",
                "deltas": {
                    "clutch_slip": -0.30,
                    "worn_piston_rings": +0.10,
                    "clogged_main_jet": +0.05,
                },
                "eliminate": [],
                "next_node": "mileage_check",
            },
            {
                "match": "clutch_slips",
                "label": "Engine revs freely while bike barely moves",
                "deltas": {
                    "clutch_slip": +0.55,
                },
                "eliminate": ["clogged_main_jet", "worn_piston_rings", "fuel_delivery", "valve_not_seating"],
                "next_node": None,
            },
            {
                "match": "hard_to_tell",
                "label": "Hard to tell / haven't tried this",
                "deltas": {},
                "eliminate": [],
                "next_node": "mileage_check",
            },
        ],
    },

    "mileage_check": {
        "question": "Roughly how many miles/km on the engine, and has the air filter been changed recently?",
        "options": [
            {
                "match": "high_miles_no_service",
                "label": "High mileage (30,000+ miles / 50,000+ km) with no recent top-end service",
                "deltas": {
                    "worn_piston_rings": +0.25,
                    "valve_not_seating": +0.20,
                    "dirty_air_filter": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "filter_not_changed",
                "label": "Air filter hasn't been changed in a long time",
                "deltas": {
                    "dirty_air_filter": +0.35,
                    "clogged_main_jet": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recently_serviced",
                "label": "Recently serviced / filter is fresh",
                "deltas": {
                    "dirty_air_filter": -0.20,
                    "clogged_main_jet": +0.10,
                    "exhaust_restriction": +0.10,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"fuel_delivery": +0.06},
        "cold": {"clogged_main_jet": +0.06},
    },
    "mileage_band": {
        "high": {"worn_piston_rings": +0.10, "valve_not_seating": +0.08, "clutch_slip": +0.08},
    },
    "usage_pattern": {
        "city": {"clutch_slip": +0.08, "exhaust_restriction": +0.04},
    },
    "storage_time": {
        "months": {"fuel_delivery": +0.10, "clogged_main_jet": +0.08},
        "season": {"fuel_delivery": +0.12, "clogged_main_jet": +0.10, "worn_piston_rings": +0.05},
    },
    "first_start_of_season": {
        "yes": {"fuel_delivery": +0.10, "clogged_main_jet": +0.08},
    },
}

LOSS_OF_POWER_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After diagnosis, perform a compression test if power loss was significant — low compression points to rings or valves.",
    "Check drive chain tension and sprocket wear — a loose chain steals noticeable power.",
]
