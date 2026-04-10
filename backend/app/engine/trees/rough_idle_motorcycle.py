"""
Rough idle diagnostic tree — motorcycle variant.

Carb-equipped bikes dominate this tree. Pilot jet clogging from
stale fuel is by far the most common cause of rough idle on motorcycles.
Air/fuel mixture screw is a close second on carb bikes.
"""

ROUGH_IDLE_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "pilot_jet_clog": {
        "label": "Clogged pilot jet — tiny idle circuit jet blocked by varnish from stale fuel",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot jet (correct size for your carb model)", "notes": "Clean or replace; drill size matching original — don't up-jet without cause"},
            {"name": "Carburetor cleaner + rebuild kit", "notes": "Full carb clean with all passages sprayed clear; replace o-rings and needle if worn"},
        ],
    },
    "air_fuel_mixture": {
        "label": "Air/fuel mixture screw out of adjustment (carb bikes)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Mixture screw o-ring kit", "notes": "Factory setting is usually 1.5–2.5 turns out; adjust in small increments for smoothest idle"},
        ],
    },
    "intake_air_leak": {
        "label": "Air leak at intake boot, carb manifold, or airbox connection",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intake boot / carb manifold", "notes": "Spray carb cleaner around boot joints while idling — idle change confirms leak"},
            {"name": "Intake manifold o-rings / clamps", "notes": "Retighten clamps before replacing; boots crack with age"},
        ],
    },
    "dirty_air_filter": {
        "label": "Severely clogged air filter — restricted airflow causing rich condition at idle",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter (foam or paper element)", "notes": "A partially blocked filter causes rich idle and flat throttle response"},
        ],
    },
    "valve_clearance": {
        "label": "Out-of-spec valve clearance — tight valves causing compression loss and rough idle",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve shim set (if shim-under-bucket engine)", "notes": "Most bikes specify check intervals at 12,000–24,000 km; a compression test first helps confirm"},
        ],
    },
    "idle_speed_screw": {
        "label": "Idle speed set too low — engine hunts or stalls because idle RPM is below spec",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Tachometer / phone RPM app", "notes": "Set idle to manufacturer spec (typically 1000–1500 RPM); adjust pilot screw first for quality, then idle speed for quantity"},
        ],
    },
    "fuel_quality": {
        "label": "Stale or contaminated fuel — ethanol phase separation or water in tank",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fresh premium fuel + fuel stabilizer", "notes": "Drain tank if fuel is more than 30 days old on a carb bike; ethanol-blend fuel degrades faster"},
        ],
    },
}

ROUGH_IDLE_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the idle problem — does it idle rough all the time, hunt (surge up and down), or stall?",
        "options": [
            {
                "match": "rough_constant",
                "label": "Rough but constant — lumpy, misfiring, or vibrating at idle",
                "deltas": {
                    "pilot_jet_clog": +0.15,
                    "valve_clearance": +0.15,
                    "intake_air_leak": +0.10,
                    "idle_speed_screw": -0.05,
                },
                "eliminate": [],
                "next_node": "storage_history",
            },
            {
                "match": "hunting_surge",
                "label": "Hunting / surging — RPM swings up and down on its own",
                "deltas": {
                    "intake_air_leak": +0.25,
                    "air_fuel_mixture": +0.20,
                    "pilot_jet_clog": +0.10,
                    "idle_speed_screw": +0.05,
                },
                "eliminate": ["valve_clearance"],
                "next_node": "storage_history",
            },
            {
                "match": "stalls",
                "label": "Stalls at idle or when coming to a stop",
                "deltas": {
                    "pilot_jet_clog": +0.20,
                    "air_fuel_mixture": +0.15,
                    "idle_speed_screw": +0.20,
                    "intake_air_leak": +0.10,
                },
                "eliminate": ["valve_clearance"],
                "next_node": "storage_history",
            },
        ],
    },

    "storage_history": {
        "question": "Has the bike sat unused for more than a few weeks, or was it running well until recently?",
        "options": [
            {
                "match": "sat_recently",
                "label": "Sat for weeks or months before this started",
                "deltas": {
                    "pilot_jet_clog": +0.30,
                    "fuel_quality": +0.15,
                    "air_fuel_mixture": +0.05,
                },
                "eliminate": ["valve_clearance"],
                "next_node": "carb_or_efi",
            },
            {
                "match": "ran_fine",
                "label": "Was running fine until this developed gradually",
                "deltas": {
                    "valve_clearance": +0.15,
                    "dirty_air_filter": +0.10,
                    "pilot_jet_clog": +0.05,
                },
                "eliminate": [],
                "next_node": "carb_or_efi",
            },
            {
                "match": "after_work",
                "label": "Started after maintenance or recent work",
                "deltas": {
                    "air_fuel_mixture": +0.20,
                    "intake_air_leak": +0.20,
                    "idle_speed_screw": +0.15,
                },
                "eliminate": [],
                "next_node": "carb_or_efi",
            },
        ],
    },

    "carb_or_efi": {
        "question": "Is the bike carbureted or fuel injected?",
        "options": [
            {
                "match": "carbureted",
                "label": "Carbureted (has a choke lever or enrichment knob)",
                "deltas": {
                    "pilot_jet_clog": +0.10,
                    "air_fuel_mixture": +0.10,
                    "intake_air_leak": +0.05,
                },
                "eliminate": [],
                "next_node": "air_filter",
            },
            {
                "match": "fuel_injected",
                "label": "Fuel injected (EFI — no choke, may have a throttle position sensor)",
                "deltas": {
                    "pilot_jet_clog": -0.20,
                    "air_fuel_mixture": -0.15,
                    "intake_air_leak": +0.15,
                    "valve_clearance": +0.10,
                    "dirty_air_filter": +0.10,
                },
                "eliminate": [],
                "next_node": "air_filter",
            },
        ],
    },

    "air_filter": {
        "question": "When did you last replace or clean the air filter?",
        "options": [
            {
                "match": "never_or_long_ago",
                "label": "Never changed, or it's been a very long time",
                "deltas": {
                    "dirty_air_filter": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recently_changed",
                "label": "Recently replaced or cleaned",
                "deltas": {
                    "dirty_air_filter": -0.20,
                    "pilot_jet_clog": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dont_know",
                "label": "Not sure",
                "deltas": {
                    "dirty_air_filter": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"idle_speed_screw": +0.08, "pilot_jet_clog": +0.06},
        "hot": {"fuel_quality": +0.06},
    },
    "mileage_band": {
        "high": {"valve_clearance": +0.10, "pilot_jet_clog": +0.06},
    },
    "storage_time": {
        "months": {"pilot_jet_clog": +0.15, "fuel_quality": +0.10},
        "season": {"pilot_jet_clog": +0.18, "fuel_quality": +0.12},
    },
    "first_start_of_season": {
        "yes": {"pilot_jet_clog": +0.10, "air_fuel_mixture": +0.06},
    },
}

ROUGH_IDLE_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After carb service, set idle speed to spec (typically 1,200–1,500 RPM cold) and recheck warm.",
    "Inspect air box for cracks or missing snorkel — an air leak mimics pilot circuit issues.",
]
