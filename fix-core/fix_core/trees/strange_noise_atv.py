"""
Strange noise diagnostic tree — ATV/UTV variant.

CVT belt slap (flapping on decel), wheel bearing failure from
water/mud immersion, and front/rear differential gear whine are
ATV/UTV-specific causes not found in car trees.
"""

STRANGE_NOISE_ATV_HYPOTHESES: dict[str, dict] = {
    "cvt_belt_slap": {
        "label": "CVT belt flapping or slapping inside the CVT cover — worn or glazed belt",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CVT drive belt", "notes": "Slapping sound on decel or at low speeds is often a worn or glazed belt oscillating inside the CVT case"},
            {"name": "CVT cover gasket", "notes": "Replace gasket when opening CVT — moisture entry from a bad seal causes belt wear"},
        ],
    },
    "wheel_bearing": {
        "label": "Worn wheel bearing — rumbling or grinding from water/mud intrusion",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wheel bearing set (front or rear, as applicable)", "notes": "ATVs submerged in water or mud-ridden without re-greasing fail bearings quickly. Grab each wheel and check for play."},
            {"name": "Bearing grease (marine/waterproof grade)", "notes": "Repack spindle bearings after every deep water crossing"},
        ],
    },
    "exhaust_leak": {
        "label": "Exhaust leak at header or mid-pipe joint — ticking or popping",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust header gasket", "notes": "Ticking that fades as engine warms is classic exhaust leak — metal expands and temporarily seals"},
            {"name": "Exhaust clamp / spring hooks", "notes": "Vibration from off-road use loosens slip-joint clamps"},
        ],
    },
    "diff_gear_whine": {
        "label": "Front or rear differential gear whine — low fluid level or worn gears",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Front/rear differential oil (check spec — SAE 80W-90 or GL-5)", "notes": "Check and change diff fluid — water intrusion from river crossings is common and destroys diff gears"},
            {"name": "Differential rebuild kit", "notes": "If fluid is milky or metallic, gears may already be damaged"},
        ],
    },
    "driveshaft_cv": {
        "label": "Worn CV joint or driveshaft U-joint — clicking or clunking under load",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CV axle / driveshaft (front or rear)", "notes": "Clicking on turns (front CV) or clunking on acceleration (rear U-joint) — common on high-mileage or hard-ridden ATVs"},
            {"name": "CV boot kit", "notes": "If boot is torn but joint not yet worn, a boot kit may save the CV axle"},
        ],
    },
    "engine_knock": {
        "label": "Engine knock — low oil pressure or internal bearing wear",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil (correct grade and viscosity)", "notes": "Check oil level immediately — ATVs run hot and burn/leak oil under hard use. Low oil causes rapid knock."},
        ],
    },
}

STRANGE_NOISE_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise — CVT belt slap, grinding/rumbling, ticking/popping, whining, or knocking?",
        "options": [
            {
                "match": "belt_slap",
                "label": "Flapping or slapping from the CVT area (left-side cover)",
                "deltas": {
                    "cvt_belt_slap": +0.65,
                },
                "eliminate": ["engine_knock", "diff_gear_whine", "exhaust_leak"],
                "next_node": "when_noise",
            },
            {
                "match": "grind_rumble",
                "label": "Grinding or rumbling — gets louder with speed",
                "deltas": {
                    "wheel_bearing": +0.45,
                    "diff_gear_whine": +0.20,
                    "driveshaft_cv": +0.10,
                },
                "eliminate": ["cvt_belt_slap", "exhaust_leak"],
                "next_node": "when_noise",
            },
            {
                "match": "tick_pop",
                "label": "Ticking or popping (metallic, rhythmic)",
                "deltas": {
                    "exhaust_leak": +0.40,
                    "engine_knock": +0.20,
                    "cvt_belt_slap": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
            {
                "match": "whine",
                "label": "Whining or howling — pitch changes with speed",
                "deltas": {
                    "diff_gear_whine": +0.45,
                    "wheel_bearing": +0.25,
                    "cvt_belt_slap": -0.10,
                },
                "eliminate": ["exhaust_leak", "engine_knock"],
                "next_node": "when_noise",
            },
            {
                "match": "knock_clunk",
                "label": "Knocking, clunking, or thudding (heavy impact sound)",
                "deltas": {
                    "engine_knock": +0.30,
                    "driveshaft_cv": +0.30,
                    "wheel_bearing": +0.15,
                    "cvt_belt_slap": -0.10,
                },
                "eliminate": [],
                "next_node": "when_noise",
            },
        ],
    },

    "when_noise": {
        "question": "When does the noise occur — all the time, only while moving, only under acceleration, or on deceleration?",
        "options": [
            {
                "match": "decel_only",
                "label": "On deceleration or engine braking only",
                "deltas": {
                    "cvt_belt_slap": +0.30,
                    "exhaust_leak": +0.15,
                    "diff_gear_whine": +0.10,
                },
                "eliminate": ["engine_knock"],
                "next_node": "location_check",
            },
            {
                "match": "under_load",
                "label": "Under load / acceleration — especially on hills",
                "deltas": {
                    "driveshaft_cv": +0.25,
                    "diff_gear_whine": +0.20,
                    "engine_knock": +0.15,
                    "cvt_belt_slap": -0.10,
                },
                "eliminate": [],
                "next_node": "location_check",
            },
            {
                "match": "turns_only",
                "label": "Only while turning",
                "deltas": {
                    "driveshaft_cv": +0.50,
                    "wheel_bearing": +0.20,
                },
                "eliminate": ["exhaust_leak", "engine_knock", "cvt_belt_slap"],
                "next_node": None,
            },
            {
                "match": "all_times",
                "label": "Continuous — whenever the machine is running",
                "deltas": {
                    "engine_knock": +0.20,
                    "exhaust_leak": +0.15,
                    "wheel_bearing": +0.10,
                },
                "eliminate": [],
                "next_node": "location_check",
            },
        ],
    },

    "location_check": {
        "question": "Where on the machine does the noise seem to come from?",
        "options": [
            {
                "match": "left_side_cvt",
                "label": "Left side of machine — CVT/belt cover area",
                "deltas": {
                    "cvt_belt_slap": +0.40,
                    "diff_gear_whine": -0.10,
                },
                "eliminate": ["wheel_bearing", "engine_knock"],
                "next_node": "oil_fluid_check",
            },
            {
                "match": "wheel_axle",
                "label": "Wheel or axle area (front or rear)",
                "deltas": {
                    "wheel_bearing": +0.35,
                    "driveshaft_cv": +0.25,
                    "diff_gear_whine": +0.10,
                },
                "eliminate": ["cvt_belt_slap", "exhaust_leak"],
                "next_node": "oil_fluid_check",
            },
            {
                "match": "engine_top",
                "label": "Top of engine — valve cover or cylinder head area",
                "deltas": {
                    "exhaust_leak": +0.20,
                    "engine_knock": +0.15,
                },
                "eliminate": ["wheel_bearing", "driveshaft_cv", "cvt_belt_slap"],
                "next_node": "oil_fluid_check",
            },
            {
                "match": "rear_diff",
                "label": "Rear differential or drive shaft area",
                "deltas": {
                    "diff_gear_whine": +0.35,
                    "driveshaft_cv": +0.25,
                },
                "eliminate": ["cvt_belt_slap", "exhaust_leak"],
                "next_node": "oil_fluid_check",
            },
        ],
    },

    "oil_fluid_check": {
        "question": "What is the engine oil level, and when was the differential fluid last changed?",
        "options": [
            {
                "match": "oil_low",
                "label": "Engine oil is low",
                "deltas": {
                    "engine_knock": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "diff_fluid_bad",
                "label": "Differential fluid is milky, burnt, or overdue",
                "deltas": {
                    "diff_gear_whine": +0.30,
                    "wheel_bearing": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "fluids_ok",
                "label": "Engine oil and diff fluid are good",
                "deltas": {
                    "engine_knock": -0.10,
                    "diff_gear_whine": -0.05,
                    "cvt_belt_slap": +0.08,
                    "wheel_bearing": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_ATV_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"exhaust_leak": +0.06},
    },
    "mileage_band": {
        "high": {"wheel_bearing": +0.10, "cvt_belt_slap": +0.08, "diff_gear_whine": +0.08, "engine_knock": +0.06},
    },
    "usage_pattern": {
        "mixed": {"wheel_bearing": +0.08, "driveshaft_cv": +0.06},
    },
    "storage_time": {
        "months": {"cvt_belt_slap": +0.08, "exhaust_leak": +0.05},
        "season": {"cvt_belt_slap": +0.10, "diff_gear_whine": +0.06},
    },
    "first_start_of_season": {
        "yes": {"exhaust_leak": +0.06, "cvt_belt_slap": +0.06},
    },
}

STRANGE_NOISE_ATV_POST_DIAGNOSIS: list[str] = [
    "After resolving the noise, change all fluids (engine oil, differential oil) if the machine has high hours — metallic debris from the noise source contaminates the oil.",
    "Check CVT vents and seals for mud/water intrusion after any deep water crossings — moisture destroys belts and variator bearings.",
]
