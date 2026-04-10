"""
Crank-no-start diagnostic tree.

"Crank no start" = engine turns over (cranking sound) but won't fire and run.
"""

CRANK_NO_START_HYPOTHESES: dict[str, dict] = {
    "no_fuel_delivery": {
        "label": "No fuel delivery (empty tank, failed fuel pump, clogged filter)",
        "prior": 0.25,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel pump", "notes": "In-tank on most modern vehicles; confirm with pressure test first"},
            {"name": "Fuel filter", "notes": "Often serviceable; check interval in owner's manual"},
        ],
    },
    "ignition_spark_failure": {
        "label": "No spark (bad spark plugs, ignition coils, or ignition module)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plugs", "notes": "Replace as a set; match OEM spec"},
            {"name": "Ignition coils", "notes": "Coil-on-plug systems — replace only failed coil(s)"},
        ],
    },
    "timing_failure": {
        "label": "Timing belt/chain jumped or broken",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Timing belt/chain kit", "notes": "High-stakes repair — professional diagnosis recommended first"},
        ],
    },
    "flooded_engine": {
        "label": "Flooded engine (excess fuel, carburetor or injector stuck open)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [],
    },
    "crankshaft_position_sensor": {
        "label": "Bad crankshaft position sensor (CKP)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Crankshaft position sensor", "notes": "Will often throw P0335/P0336/P0337 code"},
        ],
    },
    "maf_map_sensor": {
        "label": "Faulty MAF or MAP sensor (wrong air/fuel calculation)",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "MAF sensor", "notes": "Try cleaning with MAF cleaner spray first"},
            {"name": "MAP sensor", "notes": "Used on speed-density systems without MAF"},
        ],
    },
    "no_compression": {
        "label": "Low or no compression (blown head gasket, bent valves, worn rings)",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "ecu_failure": {
        "label": "ECU/PCM failure",
        "prior": 0.03,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "immobilizer_anti_theft": {
        "label": "Anti-theft / immobilizer preventing start",
        "prior": 0.02,
        "diy_difficulty": "easy",
        "parts": [],
    },
}

CRANK_NO_START_TREE: dict[str, dict] = {
    "start": {
        "question": "Does the engine crank at a normal speed, or does it sound slow or labored?",
        "options": [
            {
                "match": "cranks_normal",
                "label": "Cranks at normal speed",
                "deltas": {
                    "no_fuel_delivery": +0.05,
                    "ignition_spark_failure": +0.05,
                    "crankshaft_position_sensor": +0.05,
                },
                "eliminate": [],
                "next_node": "check_engine_light",
            },
            {
                "match": "cranks_slow",
                "label": "Cranks slowly or sounds weak",
                "deltas": {
                    "no_compression": +0.10,
                    "no_fuel_delivery": -0.05,
                    "ignition_spark_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "check_engine_light",
            },
            {
                "match": "cranks_then_stops",
                "label": "Cranks briefly then suddenly stops mid-crank",
                "deltas": {
                    "timing_failure": +0.30,
                    "no_compression": +0.15,
                },
                "eliminate": ["flooded_engine", "maf_map_sensor"],
                "next_node": "check_engine_light",
            },
        ],
    },

    "check_engine_light": {
        "question": "Was the check engine light (CEL) on before this happened, or is it on now?",
        "options": [
            {
                "match": "cel_before",
                "label": "CEL was on before the no-start",
                "deltas": {
                    "crankshaft_position_sensor": +0.10,
                    "maf_map_sensor": +0.10,
                    "ignition_spark_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_gauge",
            },
            {
                "match": "cel_now_only",
                "label": "CEL came on when this problem started",
                "deltas": {
                    "crankshaft_position_sensor": +0.15,
                    "timing_failure": +0.10,
                    "no_fuel_delivery": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_gauge",
            },
            {
                "match": "cel_none",
                "label": "No CEL at all",
                "deltas": {
                    "flooded_engine": +0.10,
                    "ecu_failure": +0.05,
                    "crankshaft_position_sensor": -0.05,
                    "maf_map_sensor": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_gauge",
            },
        ],
    },

    "fuel_gauge": {
        "question": "What does the fuel gauge show, and do you smell gasoline near the engine or exhaust?",
        "options": [
            {
                "match": "fuel_empty_or_low",
                "label": "Gauge shows empty or very low",
                "deltas": {
                    "no_fuel_delivery": +0.35,
                },
                "eliminate": ["flooded_engine", "timing_failure", "no_compression"],
                "next_node": None,
            },
            {
                "match": "fuel_smell_strong",
                "label": "Tank shows fuel AND strong smell of gas",
                "deltas": {
                    "flooded_engine": +0.35,
                    "no_fuel_delivery": -0.15,
                },
                "eliminate": ["timing_failure"],
                "next_node": None,
            },
            {
                "match": "fuel_ok_no_smell",
                "label": "Fuel is fine, no gas smell",
                "deltas": {
                    "ignition_spark_failure": +0.10,
                    "crankshaft_position_sensor": +0.10,
                    "timing_failure": +0.05,
                    "flooded_engine": -0.15,
                },
                "eliminate": [],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Did this happen suddenly (was running fine then stopped) or gradually got worse over time?",
        "options": [
            {
                "match": "sudden",
                "label": "Sudden — was running fine, then wouldn't start",
                "deltas": {
                    "no_fuel_delivery": +0.10,
                    "timing_failure": +0.10,
                    "crankshaft_position_sensor": +0.10,
                    "maf_map_sensor": -0.05,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
            {
                "match": "gradual",
                "label": "Gradual — had rough starts or misfires beforehand",
                "deltas": {
                    "ignition_spark_failure": +0.15,
                    "maf_map_sensor": +0.10,
                    "no_fuel_delivery": +0.05,
                    "timing_failure": -0.10,
                    "crankshaft_position_sensor": +0.05,
                },
                "eliminate": [],
                "next_node": "recent_work",
            },
        ],
    },

    "recent_work": {
        "question": "Was any work done on the engine or fuel system recently (last 1–2 weeks)?",
        "options": [
            {
                "match": "work_timing",
                "label": "Yes — timing belt/chain or engine internals",
                "deltas": {
                    "timing_failure": +0.30,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "work_fuel",
                "label": "Yes — fuel system, injectors, or fuel pump",
                "deltas": {
                    "no_fuel_delivery": +0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "work_other",
                "label": "Yes — other work (electrical, sensors, etc.)",
                "deltas": {
                    "crankshaft_position_sensor": +0.10,
                    "maf_map_sensor": +0.10,
                    "ecu_failure": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_work",
                "label": "No recent work",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"ignition_spark_failure": +0.08, "flooded_engine": +0.06},
        "hot": {"no_fuel_delivery": +0.08},
    },
    "mileage_band": {
        "high": {"timing_failure": +0.10, "no_fuel_delivery": +0.06, "no_compression": +0.05},
        "low": {"immobilizer_anti_theft": +0.04},
    },
}

CRANK_NO_START_POST_DIAGNOSIS: list[str] = [
    "After resolving the crank-no-start, scan for any stored DTCs — fuel or ignition faults often leave codes even after the root cause is fixed.",
    "Check the fuel pump for proper pressure (35–65 PSI depending on system) — a marginal pump may start cold but fail hot.",
]
