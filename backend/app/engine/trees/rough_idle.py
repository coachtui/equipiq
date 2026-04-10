"""
Rough idle diagnostic tree.

"Rough idle" = engine runs but idles unevenly, misfires, shakes, surges, or
stalls at idle. Covers anything from generators to trucks — the hypotheses are
framed around generic engine concepts, not car-specific systems.
"""

ROUGH_IDLE_HYPOTHESES: dict[str, dict] = {
    "spark_ignition": {
        "label": "Worn or fouled spark plugs / ignition wires (misfiring cylinder)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plugs", "notes": "Replace as a set; gap to spec for your engine"},
            {"name": "Ignition wires / coil boots", "notes": "Inspect for cracks, arcing; replace if needed"},
        ],
    },
    "vacuum_leak": {
        "label": "Vacuum or intake air leak (unmetered air causing lean misfire)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intake manifold gasket set", "notes": "Common failure point on aged engines"},
            {"name": "Vacuum line kit", "notes": "Spray carb cleaner along lines at idle to find the leak"},
        ],
    },
    "idle_control": {
        "label": "Faulty IAC valve or throttle body deposit (idle speed control failure)",
        "prior": 0.15,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Throttle body / carb cleaner", "notes": "Clean IAC and throttle bore first before replacing"},
            {"name": "IAC valve", "notes": "Check for P0505–P0509; often carboned up rather than truly failed"},
        ],
    },
    "fuel_delivery": {
        "label": "Weak fuel pump, clogged filter, or dirty injectors/carburetor",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel filter", "notes": "Replace first — cheap and often the culprit on high-mileage engines"},
            {"name": "Fuel injector cleaner additive", "notes": "Add to tank for mild injector fouling"},
            {"name": "Carburetor rebuild kit", "notes": "For carbureted engines: inspect jets and float first"},
        ],
    },
    "egr_valve": {
        "label": "Stuck-open EGR valve (exhaust gas diluting intake charge at idle)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "EGR valve", "notes": "Remove and inspect; carbon buildup can hold it open — clean or replace"},
        ],
    },
    "coil_pack": {
        "label": "Failed or intermittent ignition coil (coil-on-plug engines)",
        "prior": 0.09,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Ignition coil", "notes": "Swap coils between cylinders to confirm — misfire code follows the coil"},
        ],
    },
    "compression_issue": {
        "label": "Low compression in one or more cylinders (rings, valves, head gasket)",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Compression test kit", "notes": "Test each cylinder; < 100 psi or > 15% spread warrants further diagnosis"},
        ],
    },
    "pcv_valve": {
        "label": "Clogged or failed PCV valve (crankcase pressure disrupting idle mixture)",
        "prior": 0.05,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "PCV valve", "notes": "Cheap and often overlooked; shake the old one — it should rattle"},
        ],
    },
}

ROUGH_IDLE_TREE: dict[str, dict] = {
    "start": {
        "question": "Does the rough running happen only at idle, or also at higher RPM or under load?",
        "options": [
            {
                "match": "idle_only",
                "label": "Only at idle — smooths out when I rev it or drive",
                "deltas": {
                    "idle_control": +0.20,
                    "vacuum_leak": +0.15,
                    "egr_valve": +0.15,
                    "pcv_valve": +0.10,
                    "spark_ignition": -0.05,
                    "compression_issue": -0.05,
                },
                "eliminate": [],
                "next_node": "check_engine_light",
            },
            {
                "match": "idle_and_load",
                "label": "At idle and also under acceleration or load",
                "deltas": {
                    "spark_ignition": +0.15,
                    "fuel_delivery": +0.15,
                    "coil_pack": +0.10,
                    "compression_issue": +0.10,
                    "idle_control": -0.10,
                    "egr_valve": -0.10,
                },
                "eliminate": [],
                "next_node": "check_engine_light",
            },
            {
                "match": "stalls",
                "label": "Stalls at idle or when coming to a stop",
                "deltas": {
                    "idle_control": +0.25,
                    "vacuum_leak": +0.15,
                    "fuel_delivery": +0.10,
                    "egr_valve": +0.10,
                    "spark_ignition": +0.05,
                    "pcv_valve": +0.05,
                },
                "eliminate": [],
                "next_node": "check_engine_light",
            },
        ],
    },

    "check_engine_light": {
        "question": "Is the check engine light on, and do you have any stored trouble codes (DTCs)?",
        "options": [
            {
                "match": "cel_with_misfire",
                "label": "Yes — misfire codes (P030X) stored",
                "deltas": {
                    "spark_ignition": +0.25,
                    "coil_pack": +0.20,
                    "compression_issue": +0.10,
                    "fuel_delivery": +0.05,
                    "idle_control": -0.10,
                    "egr_valve": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_type",
            },
            {
                "match": "cel_other",
                "label": "Yes — check engine light on but different codes (or I haven't checked)",
                "deltas": {
                    "vacuum_leak": +0.10,
                    "egr_valve": +0.10,
                    "idle_control": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_type",
            },
            {
                "match": "no_cel",
                "label": "No check engine light / no codes",
                "deltas": {
                    "vacuum_leak": +0.10,
                    "idle_control": +0.10,
                    "pcv_valve": +0.10,
                    "fuel_delivery": +0.05,
                    "coil_pack": -0.10,
                    "compression_issue": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_type",
            },
        ],
    },

    "fuel_type": {
        "question": "What type of fuel system does this engine use — fuel injected, carbureted, or diesel?",
        "options": [
            {
                "match": "fuel_injected",
                "label": "Fuel injected (most cars, trucks, boats after ~1990)",
                "deltas": {
                    "idle_control": +0.05,
                    "vacuum_leak": +0.05,
                    "egr_valve": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_events",
            },
            {
                "match": "carbureted",
                "label": "Carbureted (older vehicles, small engines, generators)",
                "deltas": {
                    "fuel_delivery": +0.20,
                    "idle_control": +0.10,
                    "egr_valve": -0.15,
                    "coil_pack": -0.10,
                },
                "eliminate": ["egr_valve"],
                "next_node": "recent_events",
            },
            {
                "match": "diesel",
                "label": "Diesel",
                "deltas": {
                    "fuel_delivery": +0.15,
                    "compression_issue": +0.15,
                    "spark_ignition": -0.40,
                    "coil_pack": -0.40,
                    "egr_valve": +0.05,
                },
                "eliminate": ["spark_ignition", "coil_pack"],
                "next_node": "recent_events",
            },
        ],
    },

    "recent_events": {
        "question": "Did anything happen just before the rough idle started — bad fuel fill-up, sitting unused for a while, or a recent repair?",
        "options": [
            {
                "match": "bad_fuel_or_sitting",
                "label": "Bad or old fuel, or sat unused for weeks/months",
                "deltas": {
                    "fuel_delivery": +0.25,
                    "spark_ignition": +0.10,
                    "idle_control": +0.05,
                },
                "eliminate": [],
                "next_node": "idle_in_gear",
            },
            {
                "match": "recent_repair",
                "label": "Recent repair or work done on the engine",
                "deltas": {
                    "vacuum_leak": +0.25,
                    "idle_control": +0.10,
                    "pcv_valve": +0.05,
                },
                "eliminate": [],
                "next_node": "idle_in_gear",
            },
            {
                "match": "nothing_obvious",
                "label": "Nothing obvious — just started happening",
                "deltas": {
                    "spark_ignition": +0.05,
                    "coil_pack": +0.05,
                    "vacuum_leak": +0.05,
                },
                "eliminate": [],
                "next_node": "idle_in_gear",
            },
        ],
    },

    "idle_in_gear": {
        "question": "Is the idle rougher when the transmission is in gear (Drive or 1st) compared to Park or Neutral? (If manual, motorcycle, or generator — pick the closest option.)",
        "options": [
            {
                "match": "worse_in_gear",
                "label": "Clearly rougher or more likely to stall in gear",
                "deltas": {
                    "vacuum_leak": +0.15,
                    "egr_valve": +0.15,
                    "fuel_delivery": +0.10,
                    "idle_control": +0.10,
                    "compression_issue": -0.05,
                    "spark_ignition": -0.05,
                },
                "eliminate": [],
                "next_node": "warm_up_pattern",
            },
            {
                "match": "same_either",
                "label": "About the same in gear and Park/Neutral",
                "deltas": {
                    "spark_ignition": +0.10,
                    "coil_pack": +0.10,
                    "compression_issue": +0.05,
                    "idle_control": -0.05,
                    "egr_valve": -0.05,
                },
                "eliminate": [],
                "next_node": "warm_up_pattern",
            },
            {
                "match": "na_manual_moto",
                "label": "N/A — manual, motorcycle, or generator (no Drive/Park distinction)",
                "deltas": {
                    "spark_ignition": +0.05,
                    "compression_issue": +0.05,
                },
                "eliminate": [],
                "next_node": "warm_up_pattern",
            },
        ],
    },

    "warm_up_pattern": {
        "question": "Once the engine reaches full operating temperature, does the rough idle smooth out, get worse, or stay consistently rough?",
        "options": [
            {
                "match": "smooths_when_warm",
                "label": "Smooths out once fully warm",
                "deltas": {
                    "idle_control": +0.20,
                    "vacuum_leak": +0.15,
                    "pcv_valve": +0.10,
                    "compression_issue": -0.10,
                    "fuel_delivery": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "worse_when_warm",
                "label": "Gets worse or starts rough-running only after warming up",
                "deltas": {
                    "compression_issue": +0.20,
                    "fuel_delivery": +0.15,
                    "egr_valve": +0.10,
                    "idle_control": -0.10,
                    "pcv_valve": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "consistently_rough",
                "label": "Consistently rough regardless of temperature",
                "deltas": {
                    "spark_ignition": +0.15,
                    "coil_pack": +0.10,
                    "compression_issue": +0.10,
                    "vacuum_leak": +0.05,
                    "idle_control": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"idle_control": +0.08, "vacuum_leak": +0.06},
        "hot": {"egr_valve": +0.06, "fuel_delivery": +0.04},
    },
    "mileage_band": {
        "high": {"spark_ignition": +0.08, "coil_pack": +0.06, "fuel_delivery": +0.06},
    },
    "usage_pattern": {
        "city": {"egr_valve": +0.08, "fuel_delivery": +0.04},
    },
}

ROUGH_IDLE_POST_DIAGNOSIS: list[str] = [
    "After repair, let the engine idle for 10 minutes and confirm a stable idle RPM (typically 600–800 RPM warmed up).",
    "Check for vacuum leaks with carb cleaner spray after any intake manifold work — even a small disturbed gasket causes rough idle.",
]
