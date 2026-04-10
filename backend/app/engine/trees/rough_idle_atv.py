"""
Rough idle diagnostic tree — ATV/UTV variant.

Pilot jet clogging (idle/low-speed circuit) is the dominant ATV rough
idle cause — ethanol fuel leaves deposits in the small pilot jet passages
more readily than the main jet. Intake boot cracks from UV exposure
and off-road flex are also very common.
"""

ROUGH_IDLE_ATV_HYPOTHESES: dict[str, dict] = {
    "pilot_jet_clogged": {
        "label": "Clogged pilot jet (idle circuit) in carburetor — varnish from ethanol fuel",
        "prior": 0.30,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot jet (correct size)", "notes": "The tiny jet in the carb idle circuit — most common rough-idle cause. Spray carb cleaner through all passages; replace jet if cleaning fails."},
            {"name": "Carburetor rebuild kit", "notes": "If the carb has varnish throughout, a rebuild kit is more cost-effective than individual jet replacements"},
        ],
    },
    "intake_boot_leak": {
        "label": "Cracked intake boot or loose clamp — air leak between carb/throttle body and airbox",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intake boot / carb manifold", "notes": "ATV intake boots crack from UV exposure and flex during off-road use. Spray carb cleaner around the boot at idle — RPM change confirms a leak."},
            {"name": "Intake clamp set", "notes": "Loose hose clamps cause intermittent air leaks — check both ends"},
        ],
    },
    "spark_plug_worn": {
        "label": "Fouled or worn spark plug",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Spark plug (correct heat range for engine)", "notes": "Pull and inspect — black/sooty = running rich; white = lean; grey = normal. Replace if electrode is worn."},
        ],
    },
    "air_filter_clogged": {
        "label": "Severely clogged air filter — rich mixture causing rough idle",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Air filter", "notes": "A packed air filter richens the mixture at idle — clean or replace before carb work"},
        ],
    },
    "valve_clearance": {
        "label": "Valve clearance out of spec — tight valves causing low compression or misfire at idle",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Valve shim kit", "notes": "Check clearance per service manual with feeler gauges. Tight intake valves are common on high-mileage ATVs."},
            {"name": "Feeler gauge set", "notes": "Needed to measure clearance — check cold per spec"},
        ],
    },
    "fuel_screw_misadjusted": {
        "label": "Pilot fuel screw (air/fuel mixture screw) out of adjustment",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot screw adjuster tool", "notes": "Many ATVs have a tamper plug over the pilot screw. Adjust in 1/4-turn increments from baseline (2.5 turns out is typical) while at idle."},
        ],
    },
}

ROUGH_IDLE_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "How does the idle behave — rough and stumbling throughout, stalls when warm, or revs hunt up and down?",
        "options": [
            {
                "match": "rough_all_temps",
                "label": "Rough at all temps — stumbles or sputters consistently",
                "deltas": {
                    "pilot_jet_clogged": +0.25,
                    "intake_boot_leak": +0.15,
                    "spark_plug_worn": +0.15,
                    "air_filter_clogged": +0.10,
                },
                "eliminate": [],
                "next_node": "air_filter_check",
            },
            {
                "match": "hunts_surges",
                "label": "Idle hunts (RPMs rise and fall rhythmically)",
                "deltas": {
                    "intake_boot_leak": +0.35,
                    "pilot_jet_clogged": +0.20,
                    "fuel_screw_misadjusted": +0.15,
                },
                "eliminate": ["valve_clearance"],
                "next_node": "air_filter_check",
            },
            {
                "match": "stalls_warm",
                "label": "Idle fine cold but stalls or drops when warm",
                "deltas": {
                    "pilot_jet_clogged": +0.20,
                    "fuel_screw_misadjusted": +0.20,
                    "valve_clearance": +0.15,
                },
                "eliminate": [],
                "next_node": "air_filter_check",
            },
            {
                "match": "backfire_pop",
                "label": "Backfiring or popping on decel",
                "deltas": {
                    "intake_boot_leak": +0.30,
                    "pilot_jet_clogged": +0.15,
                    "fuel_screw_misadjusted": +0.15,
                },
                "eliminate": ["valve_clearance", "air_filter_clogged"],
                "next_node": "air_filter_check",
            },
        ],
    },

    "air_filter_check": {
        "question": "When was the air filter last cleaned or replaced?",
        "options": [
            {
                "match": "filter_dirty",
                "label": "Not recently — visibly dirty or never cleaned",
                "deltas": {
                    "air_filter_clogged": +0.40,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
            {
                "match": "filter_ok",
                "label": "Recently cleaned or replaced",
                "deltas": {
                    "air_filter_clogged": -0.10,
                    "pilot_jet_clogged": +0.08,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
        ],
    },

    "storage_check": {
        "question": "Did the rough idle start after storage or after the machine sat with old fuel?",
        "options": [
            {
                "match": "after_storage",
                "label": "Yes — started rough after sitting for weeks or longer",
                "deltas": {
                    "pilot_jet_clogged": +0.35,
                    "spark_plug_worn": +0.10,
                },
                "eliminate": ["valve_clearance"],
                "next_node": "intake_check",
            },
            {
                "match": "developed_gradually",
                "label": "No — developed gradually during regular use",
                "deltas": {
                    "valve_clearance": +0.20,
                    "spark_plug_worn": +0.15,
                    "intake_boot_leak": +0.10,
                    "pilot_jet_clogged": -0.10,
                },
                "eliminate": [],
                "next_node": "intake_check",
            },
        ],
    },

    "intake_check": {
        "question": "Has the intake boot or carb manifold been inspected for cracks, and are the clamps tight?",
        "options": [
            {
                "match": "boot_cracked",
                "label": "Found a crack, tear, or loose clamp",
                "deltas": {
                    "intake_boot_leak": +0.65,
                },
                "eliminate": ["pilot_jet_clogged", "valve_clearance"],
                "next_node": None,
            },
            {
                "match": "boot_ok",
                "label": "Boot looks good and clamps are tight",
                "deltas": {
                    "intake_boot_leak": -0.15,
                    "pilot_jet_clogged": +0.10,
                    "valve_clearance": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_checked",
                "label": "Haven't checked the intake boot yet",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"pilot_jet_clogged": +0.06, "fuel_screw_misadjusted": +0.05},
        "hot": {"intake_boot_leak": +0.06},
    },
    "mileage_band": {
        "high": {"valve_clearance": +0.10, "spark_plug_worn": +0.08},
    },
    "storage_time": {
        "months": {"pilot_jet_clogged": +0.18, "spark_plug_worn": +0.08},
        "season": {"pilot_jet_clogged": +0.22, "spark_plug_worn": +0.10, "air_filter_clogged": +0.06},
    },
    "first_start_of_season": {
        "yes": {"pilot_jet_clogged": +0.18, "spark_plug_worn": +0.08, "air_filter_clogged": +0.06},
    },
}

ROUGH_IDLE_ATV_POST_DIAGNOSIS: list[str] = [
    "After carb cleaning, set the idle speed screw to achieve a stable idle (typically 1,400–1,600 RPM) and then fine-tune the pilot fuel screw for smoothest idle.",
    "If the intake boot was replaced, re-check torque on both clamps after 5–10 hours of use — new boots settle and clamps can loosen.",
]
