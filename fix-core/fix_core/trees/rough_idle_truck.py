"""
Rough idle diagnostic tree — truck/diesel variant.

Diesel rough idle includes: injector rattle at startup (normal on cold diesel),
genuine misfire (one cylinder not firing), EGR-related rough idle, and air/fuel
imbalances. 'Diesel knock' at startup that goes away warm is often normal.
"""

ROUGH_IDLE_TRUCK_HYPOTHESES: dict[str, dict] = {
    "injector_issue": {
        "label": "Fuel injector fault — worn tip, stuck-open, or return leak causing rough combustion",
        "prior": 0.24,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Injector return line o-rings / seals", "notes": "A common and cheap fix on common-rail diesels — leaking return o-rings cause pressure loss and rough idle"},
            {"name": "Fuel injector (professional flow test first)", "notes": "Flow-test all injectors before condemning one — worn injectors vary in delivery"},
        ],
    },
    "egr_fault": {
        "label": "EGR valve stuck open or clogged with carbon — dumping exhaust into intake at idle",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "EGR valve", "notes": "A stuck-open EGR bleeds exhaust into the intake at idle, causing rough, smoky combustion. Carbon buildup is the main culprit."},
            {"name": "EGR cleaner / carbon remover", "notes": "Spray cleaning often restores function without full replacement"},
        ],
    },
    "glow_plug_misfire": {
        "label": "Failed glow plug causing one cylinder to misfire on cold starts",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "A single failed glow plug causes one cylinder to not fire on cold starts — rough idle that smooths out after 1–2 minutes warm-up"},
        ],
    },
    "air_intake_restriction": {
        "label": "Severely clogged air filter or restricted intake — lean idle",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter (diesel truck, often large panel filter)", "notes": "Check restriction indicator if equipped. A heavily loaded air filter robs the engine of air at idle."},
        ],
    },
    "fuel_return_leak": {
        "label": "High-pressure fuel return line leak reducing common rail pressure at idle",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel return line and fittings", "notes": "Perform a leak-off test on injectors — excessive return flow indicates a leaking injector or return line"},
        ],
    },
    "mass_airflow_sensor": {
        "label": "Dirty or failed mass airflow (MAF) sensor — incorrect air metering at idle",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "MAF sensor cleaner", "notes": "Clean before replacing. Common on diesel trucks post-EGR — oil mist from crankcase vents contaminates the MAF."},
            {"name": "Mass airflow sensor", "notes": "Replace if cleaning does not resolve codes or rough idle"},
        ],
    },
    "normal_diesel_clatter": {
        "label": "Normal diesel combustion noise — hard knock on cold start that smooths out when warm",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No repair needed)", "notes": "Cold diesel knock at startup is normal — the delay before glow plugs fully condition fuel ignition causes brief rough combustion. If it smooths within 2–3 minutes of warm-up, this is expected behavior."},
        ],
    },
}

ROUGH_IDLE_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "When does the rough idle occur?",
        "options": [
            {
                "match": "cold_start_only",
                "label": "Only when cold — smooths out after the engine warms up (2–5 minutes)",
                "deltas": {
                    "normal_diesel_clatter": +0.25,
                    "glow_plug_misfire": +0.30,
                    "injector_issue": +0.10,
                    "egr_fault": -0.10,
                },
                "eliminate": [],
                "next_node": "cel_present",
            },
            {
                "match": "all_the_time",
                "label": "All the time — rough when warm too",
                "deltas": {
                    "injector_issue": +0.20,
                    "egr_fault": +0.15,
                    "fuel_return_leak": +0.10,
                    "mass_airflow_sensor": +0.10,
                    "normal_diesel_clatter": -0.15,
                    "glow_plug_misfire": -0.10,
                },
                "eliminate": [],
                "next_node": "cel_present",
            },
            {
                "match": "worse_under_load",
                "label": "Rough at idle but worse under load",
                "deltas": {
                    "injector_issue": +0.20,
                    "egr_fault": +0.15,
                    "air_intake_restriction": +0.10,
                    "fuel_return_leak": +0.10,
                },
                "eliminate": [],
                "next_node": "cel_present",
            },
        ],
    },

    "cel_present": {
        "question": "Is there a check engine light on?",
        "options": [
            {
                "match": "cel_on",
                "label": "Yes — check engine light is on",
                "deltas": {
                    "egr_fault": +0.15,
                    "injector_issue": +0.10,
                    "mass_airflow_sensor": +0.10,
                    "normal_diesel_clatter": -0.20,
                },
                "eliminate": [],
                "next_node": "smoke_color",
            },
            {
                "match": "no_cel",
                "label": "No — no warning lights",
                "deltas": {
                    "normal_diesel_clatter": +0.10,
                    "glow_plug_misfire": +0.05,
                    "fuel_return_leak": +0.05,
                },
                "eliminate": [],
                "next_node": "smoke_color",
            },
        ],
    },

    "smoke_color": {
        "question": "Is there any exhaust smoke visible at idle?",
        "options": [
            {
                "match": "white_blue_smoke",
                "label": "White or light blue smoke at idle",
                "deltas": {
                    "injector_issue": +0.20,
                    "glow_plug_misfire": +0.15,
                    "fuel_return_leak": +0.10,
                    "normal_diesel_clatter": -0.10,
                },
                "eliminate": [],
                "next_node": "mileage",
            },
            {
                "match": "black_smoke",
                "label": "Black smoke at idle",
                "deltas": {
                    "egr_fault": +0.25,
                    "air_intake_restriction": +0.15,
                    "mass_airflow_sensor": +0.10,
                },
                "eliminate": ["normal_diesel_clatter"],
                "next_node": "mileage",
            },
            {
                "match": "no_smoke",
                "label": "No unusual smoke",
                "deltas": {
                    "normal_diesel_clatter": +0.10,
                    "mass_airflow_sensor": +0.05,
                },
                "eliminate": [],
                "next_node": "mileage",
            },
        ],
    },

    "mileage": {
        "question": "How many miles are on this engine?",
        "options": [
            {
                "match": "high_mileage",
                "label": "High mileage — over 150,000 miles",
                "deltas": {
                    "injector_issue": +0.15,
                    "egr_fault": +0.10,
                    "fuel_return_leak": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low_mid_mileage",
                "label": "Under 150,000 miles",
                "deltas": {
                    "egr_fault": +0.05,
                    "air_intake_restriction": +0.05,
                    "normal_diesel_clatter": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_mileage",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"glow_plug_misfire": +0.10, "fuel_return_leak": +0.04},
    },
    "mileage_band": {
        "high": {"injector_issue": +0.10, "egr_fault": +0.08, "mass_airflow_sensor": +0.06},
    },
    "usage_pattern": {
        "city": {"egr_fault": +0.10, "injector_issue": +0.04},
    },
}

ROUGH_IDLE_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After injector or EGR repair, perform an injector contribution test with a scan tool to confirm balanced cylinders.",
    "If EGR was cleaned or replaced, clean the EGR cooler as well — a restricted cooler causes EGR to re-foul rapidly.",
]
