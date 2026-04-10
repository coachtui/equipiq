"""
Strange noise diagnostic tree — motorcycle variant.

Cam chain tensioner rattle (especially cold, common on Honda singles/parallel-twins),
drive chain slap, and clutch basket rattle are motorcycle-specific first-class
hypotheses not present in the car tree.
"""

STRANGE_NOISE_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "cam_chain_tensioner": {
        "label": "Cam chain tensioner failure or stretched cam chain — rattle at cold startup",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Cam chain tensioner", "notes": "Rattle loudest at cold startup, goes away when warm; common on Honda CB/CG singles and parallel twins"},
            {"name": "Cam chain", "notes": "Replace if tensioner is at its travel limit — inspect while tensioner is out"},
        ],
    },
    "drive_chain": {
        "label": "Loose, worn, or under-lubed drive chain — slap or clunk under load",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Chain lubricant", "notes": "Check slack first (typically 20–30mm); lube and adjust before condemning the chain"},
            {"name": "Drive chain + sprocket kit", "notes": "Replace chain and both sprockets together; worn sprockets eat new chains quickly"},
        ],
    },
    "exhaust_leak": {
        "label": "Exhaust leak at header gasket or mid-pipe joint — ticking or popping sound",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust header gasket", "notes": "Ticking that fades as engine warms often means this — metal expands and seals temporarily"},
            {"name": "Exhaust clamp / spring hooks", "notes": "Check slip-joint connections; springs stretch with heat cycles"},
        ],
    },
    "wheel_steering_bearing": {
        "label": "Worn wheel bearing or steering head bearing — clunk or rumble while moving",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wheel bearing set (front and/or rear)", "notes": "Grab wheel and check for play; spin by hand — rough or grinding = replace"},
            {"name": "Steering head bearing set", "notes": "Rock forks forward/backward at rest — clunk in a straight line = worn steering bearings"},
        ],
    },
    "engine_knock": {
        "label": "Engine knock or rod knock — serious internal failure",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil (correct grade)", "notes": "Check level immediately; low oil on a motorcycle engine causes rod knock rapidly"},
        ],
    },
    "clutch_rattle": {
        "label": "Clutch basket rattle or worn clutch damper springs",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Clutch basket damper springs", "notes": "Rattle that changes noticeably when you pull or release the clutch lever = clutch basket issue"},
            {"name": "Clutch basket", "notes": "Inspect for notching in clutch plate slots — notches cause grabbing and rattle"},
        ],
    },
    "brake_rubbing": {
        "label": "Brake pad dragging on rotor or seized caliper piston",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper rebuild kit", "notes": "Spin each wheel by hand — resistance or scraping = drag; common after brake work or long storage"},
            {"name": "Brake pads", "notes": "Check thickness; if pads are worn to metal that causes grinding"},
        ],
    },
}

STRANGE_NOISE_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise — rattling/clattering, knocking/thumping, ticking/tapping, or scraping/grinding/rubbing?",
        "options": [
            {
                "match": "rattle_clatter",
                "label": "Rattling or clattering (metallic, loose-sounding)",
                "deltas": {
                    "cam_chain_tensioner": +0.30,
                    "drive_chain": +0.20,
                    "clutch_rattle": +0.15,
                    "engine_knock": -0.05,
                    "brake_rubbing": -0.10,
                    "wheel_steering_bearing": -0.05,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "knock_thump",
                "label": "Knocking or thumping (heavier, rhythmic thud)",
                "deltas": {
                    "engine_knock": +0.35,
                    "drive_chain": +0.15,
                    "wheel_steering_bearing": +0.10,
                    "cam_chain_tensioner": -0.05,
                    "clutch_rattle": -0.05,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "tick_tap",
                "label": "Ticking or tapping (rapid, lighter metallic sound)",
                "deltas": {
                    "exhaust_leak": +0.30,
                    "cam_chain_tensioner": +0.20,
                    "engine_knock": +0.05,
                    "drive_chain": -0.10,
                    "brake_rubbing": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "scrape_grind",
                "label": "Scraping, grinding, or continuous rubbing",
                "deltas": {
                    "brake_rubbing": +0.45,
                    "wheel_steering_bearing": +0.20,
                    "drive_chain": +0.10,
                    "engine_knock": -0.10,
                    "cam_chain_tensioner": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
        ],
    },

    "when_noise": {
        "question": "When does the noise occur?",
        "options": [
            {
                "match": "cold_startup_only",
                "label": "Only at cold startup — goes away after warming up",
                "deltas": {
                    "cam_chain_tensioner": +0.35,
                    "exhaust_leak": +0.15,
                    "engine_knock": -0.10,
                    "brake_rubbing": -0.15,
                    "drive_chain": -0.10,
                },
                "eliminate": [],
                "next_node": "noise_source",
            },
            {
                "match": "idle_consistent",
                "label": "At idle, consistent regardless of temperature",
                "deltas": {
                    "exhaust_leak": +0.20,
                    "cam_chain_tensioner": +0.10,
                    "clutch_rattle": +0.15,
                    "engine_knock": +0.10,
                    "drive_chain": -0.10,
                    "brake_rubbing": -0.10,
                },
                "eliminate": [],
                "next_node": "noise_source",
            },
            {
                "match": "while_moving",
                "label": "Only while moving / riding (not at idle)",
                "deltas": {
                    "drive_chain": +0.25,
                    "brake_rubbing": +0.25,
                    "wheel_steering_bearing": +0.20,
                    "cam_chain_tensioner": -0.15,
                    "exhaust_leak": -0.10,
                    "clutch_rattle": -0.10,
                },
                "eliminate": [],
                "next_node": "noise_source",
            },
            {
                "match": "clutch_lever_change",
                "label": "Changes when I pull or release the clutch lever",
                "deltas": {
                    "clutch_rattle": +0.55,
                },
                "eliminate": ["brake_rubbing", "wheel_steering_bearing", "exhaust_leak"],
                "next_node": None,
            },
        ],
    },

    "noise_source": {
        "question": "Where on the motorcycle does the noise seem to originate?",
        "options": [
            {
                "match": "top_engine_head",
                "label": "Top of the engine — cylinder head or valve cover area",
                "deltas": {
                    "cam_chain_tensioner": +0.20,
                    "exhaust_leak": +0.10,
                    "engine_knock": -0.05,
                    "drive_chain": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "lower_engine_cases",
                "label": "Lower engine or crankcase area",
                "deltas": {
                    "engine_knock": +0.25,
                    "clutch_rattle": +0.10,
                    "cam_chain_tensioner": -0.10,
                    "exhaust_leak": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "transmission_clutch_area",
                "label": "Transmission / clutch area (mid-engine)",
                "deltas": {
                    "clutch_rattle": +0.30,
                    "drive_chain": +0.10,
                    "engine_knock": -0.05,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "wheel_suspension",
                "label": "Wheel, suspension, or brake area",
                "deltas": {
                    "wheel_steering_bearing": +0.30,
                    "brake_rubbing": +0.25,
                    "drive_chain": +0.10,
                    "cam_chain_tensioner": -0.20,
                    "engine_knock": -0.15,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "What is the engine oil level and condition?",
        "options": [
            {
                "match": "oil_low",
                "label": "Low on oil",
                "deltas": {
                    "engine_knock": +0.30,
                    "cam_chain_tensioner": +0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "oil_fresh",
                "label": "Full and recently changed",
                "deltas": {
                    "engine_knock": -0.10,
                    "cam_chain_tensioner": -0.05,
                    "exhaust_leak": +0.05,
                    "drive_chain": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "oil_overdue",
                "label": "Full but overdue for a change",
                "deltas": {
                    "cam_chain_tensioner": +0.10,
                    "engine_knock": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"cam_chain_tensioner": +0.10, "exhaust_leak": +0.06},
    },
    "mileage_band": {
        "high": {"cam_chain_tensioner": +0.08, "wheel_steering_bearing": +0.08, "engine_knock": +0.06},
    },
    "usage_pattern": {
        "highway": {"drive_chain": +0.08},
        "city": {"brake_rubbing": +0.06},
    },
    "storage_time": {
        "months": {"cam_chain_tensioner": +0.08, "drive_chain": +0.06},
        "season": {"cam_chain_tensioner": +0.10, "drive_chain": +0.08, "exhaust_leak": +0.05},
    },
    "first_start_of_season": {
        "yes": {"cam_chain_tensioner": +0.08, "exhaust_leak": +0.06},
    },
}

STRANGE_NOISE_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After repairing the noise source, test ride at varying speeds and confirm the noise is gone before returning the bike to service.",
    "If cam chain tensioner was replaced, check cam chain stretch with a dial indicator before buttoning up.",
]
