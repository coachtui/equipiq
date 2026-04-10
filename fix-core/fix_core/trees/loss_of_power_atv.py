"""
Loss-of-power diagnostic tree — ATV/UTV variant.

CVT belt wear/slippage is the #1 ATV/UTV-specific power-loss cause —
not present in any other vehicle type. Air filter clogging from
off-road dust is also disproportionately common.
"""

LOSS_OF_POWER_ATV_HYPOTHESES: dict[str, dict] = {
    "cvt_belt_worn": {
        "label": "Worn or slipping CVT belt — belt glazed, cracked, or stretched past spec",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CVT drive belt (OEM or Gates equivalent)", "notes": "Match exact part number — width and circumference must be correct. Measure old belt width; if narrower than spec, the belt is worn."},
            {"name": "CVT belt deflection gauge", "notes": "Check belt deflection before and after replacement"},
        ],
    },
    "air_filter_clogged": {
        "label": "Severely clogged air filter — restricting airflow from off-road dust and mud",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter (foam or paper, check OEM spec)", "notes": "ATVs operated in dusty/muddy conditions need filter checks every few rides, not by mileage"},
            {"name": "Air filter oil (for foam filters)", "notes": "Re-oil foam filters after washing — dry foam passes fine particles"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel delivery problem — clogged jets, weak fuel pump, or restricted fuel line",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Carburetor main jet", "notes": "Power loss at wide-open throttle points to main jet; loss at part throttle points to needle jet position"},
            {"name": "Inline fuel filter", "notes": "Replace if not recently serviced — ethanol deposits clog these"},
        ],
    },
    "exhaust_restriction": {
        "label": "Blocked exhaust — spark arrestor packed with carbon or debris in the pipe",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark arrestor screen (fits inside end cap)", "notes": "Remove and burn off carbon deposits or replace; required by law in most areas — do not remove permanently"},
        ],
    },
    "worn_rings_valves": {
        "label": "Worn piston rings or valve seating — engine compression loss",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Compression tester", "notes": "Test each cylinder; spec is typically 130–175 PSI. Low compression confirms rings/valves — check before expensive disassembly"},
        ],
    },
    "clutch_variator": {
        "label": "Worn CVT variator or clutch weights — belt ratio not shifting correctly",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CVT variator kit (weights + rollers)", "notes": "Worn variator weights cause the belt to shift at wrong RPMs — sluggish acceleration or RPM flare with no speed gain"},
            {"name": "Clutch spring", "notes": "Weak secondary clutch spring prevents proper belt clamping under load"},
        ],
    },
}

LOSS_OF_POWER_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "When does the power loss occur — at all throttle positions, only at wide-open throttle, or mainly under load (hill climbing, hauling)?",
        "options": [
            {
                "match": "all_throttle",
                "label": "All throttle positions — generally weak throughout",
                "deltas": {
                    "air_filter_clogged": +0.25,
                    "cvt_belt_worn": +0.20,
                    "worn_rings_valves": +0.15,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "wide_open_only",
                "label": "Only at wide-open throttle — fine at lower speeds",
                "deltas": {
                    "fuel_delivery": +0.30,
                    "air_filter_clogged": +0.20,
                    "exhaust_restriction": +0.15,
                    "cvt_belt_worn": -0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "under_load",
                "label": "Under load — climbs hills slowly, struggles with cargo",
                "deltas": {
                    "cvt_belt_worn": +0.35,
                    "clutch_variator": +0.20,
                    "worn_rings_valves": +0.15,
                    "air_filter_clogged": +0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "rpm_flare",
                "label": "RPMs climb high but speed doesn't — belt slipping sensation",
                "deltas": {
                    "cvt_belt_worn": +0.55,
                    "clutch_variator": +0.20,
                },
                "eliminate": ["worn_rings_valves", "fuel_delivery", "exhaust_restriction"],
                "next_node": None,
            },
        ],
    },

    "cvt_check": {
        "question": "Has the CVT belt been inspected recently, and does the machine have high hours/miles?",
        "options": [
            {
                "match": "belt_due",
                "label": "Belt not inspected — high hours or many miles since last service",
                "deltas": {
                    "cvt_belt_worn": +0.25,
                    "clutch_variator": +0.15,
                },
                "eliminate": [],
                "next_node": "air_fuel_check",
            },
            {
                "match": "belt_new",
                "label": "Belt recently replaced and looks good",
                "deltas": {
                    "cvt_belt_worn": -0.20,
                    "air_filter_clogged": +0.10,
                    "fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": "air_fuel_check",
            },
            {
                "match": "belt_unknown",
                "label": "Don't know belt condition / haven't checked",
                "deltas": {
                    "cvt_belt_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "air_fuel_check",
            },
        ],
    },

    "air_fuel_check": {
        "question": "When was the air filter last cleaned or replaced, and is the fuel fresh?",
        "options": [
            {
                "match": "filter_dirty",
                "label": "Air filter hasn't been cleaned in a long time or is visibly dirty",
                "deltas": {
                    "air_filter_clogged": +0.40,
                },
                "eliminate": [],
                "next_node": "exhaust_check",
            },
            {
                "match": "filter_ok_old_fuel",
                "label": "Filter is clean but fuel has been sitting for months",
                "deltas": {
                    "fuel_delivery": +0.25,
                    "air_filter_clogged": -0.10,
                },
                "eliminate": [],
                "next_node": "exhaust_check",
            },
            {
                "match": "both_ok",
                "label": "Air filter clean and fresh fuel",
                "deltas": {
                    "air_filter_clogged": -0.15,
                    "fuel_delivery": -0.05,
                    "worn_rings_valves": +0.15,
                    "cvt_belt_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "exhaust_check",
            },
        ],
    },

    "exhaust_check": {
        "question": "Has this machine been used heavily off-road in dusty or wooded terrain with the spark arrestor in place?",
        "options": [
            {
                "match": "heavy_offroad",
                "label": "Yes — heavy off-road use, spark arrestor never cleaned",
                "deltas": {
                    "exhaust_restriction": +0.35,
                    "air_filter_clogged": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "normal_use",
                "label": "Normal use or mostly trail riding",
                "deltas": {
                    "exhaust_restriction": -0.05,
                    "worn_rings_valves": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "hot": {"air_filter_clogged": +0.06, "fuel_delivery": +0.05},
    },
    "mileage_band": {
        "high": {"cvt_belt_worn": +0.12, "worn_rings_valves": +0.10, "clutch_variator": +0.08},
    },
    "usage_pattern": {
        "city": {"exhaust_restriction": +0.05},
    },
    "storage_time": {
        "months": {"fuel_delivery": +0.10, "air_filter_clogged": +0.06},
        "season": {"fuel_delivery": +0.12, "air_filter_clogged": +0.08, "cvt_belt_worn": +0.06},
    },
    "first_start_of_season": {
        "yes": {"fuel_delivery": +0.10, "air_filter_clogged": +0.08},
    },
}

LOSS_OF_POWER_ATV_POST_DIAGNOSIS: list[str] = [
    "After fixing the power loss, do a full-throttle pull in a safe area to confirm the CVT is shifting properly through the full RPM range.",
    "Check CVT intake snorkel for mud packing — a clogged CVT intake causes belt heat and dramatically shortens belt life.",
    "If compression was low, do a leak-down test before deciding between rings (cylinder bore) and valves (lap or shim).",
]
