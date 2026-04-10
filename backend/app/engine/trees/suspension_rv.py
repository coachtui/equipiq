"""
Suspension diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Class A diesel pushers: air ride suspension is standard (front and rear tag axle)
  — air bag leaks, compressor faults, level sensor failures
- Leveling system (HWH, Lippert, Equalizer) is separate from drive suspension but
  causes confusion — jacks not retracting fully causes driving stability complaints
- Tag axle (third pusher axle on large Class A coaches) can have separate air bags
- Class C / gas Class A: truck-style spring and shock suspension with stiffer tuning
- Coach weight (25,000–45,000 lbs) means suspension failures are safety-critical
  and typically require a shop
- Tire and wheel bearing issues at this weight class are dangerous if ignored
"""

SUSPENSION_RV_HYPOTHESES: dict[str, dict] = {
    "air_bag_leak": {
        "label": "Air bag (air spring) leak or failure — Class A air ride suspension",
        "prior": 0.28,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Air spring / air bag (axle-specific)", "notes": "Identify axle position (front, rear drive, tag) before ordering — air bags have different load ratings per position; a hissing sound from the coach underbody points to the failed corner"},
            {"name": "Air fitting and line repair kit", "notes": "Air line fittings can crack or pull out — often easier and cheaper to fix than replacing the full air bag if the bag itself is intact"},
        ],
    },
    "air_compressor_dryer": {
        "label": "Air compressor or air dryer fault (slow leveling, low air pressure warning, won't level)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Air dryer cartridge", "notes": "Replace every 3 years — moisture saturates the cartridge and water enters the air bags, causing corrosion and premature bag failure"},
            {"name": "Air compressor", "notes": "Coach air compressor cycles more than a semi truck — high-hour compressors lose pumping efficiency; listen for extended run times to diagnose"},
        ],
    },
    "leveling_system_fault": {
        "label": "Leveling jack fault (jack won't retract, coach unlevel after setup, error light)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Leveling jack (HWH, Lippert, Equalizer — specific to brand)", "notes": "Hydraulic jack leaks at the cylinder are common; electric actuator jacks fail at the motor or limit switch; confirm brand and model before ordering"},
            {"name": "Hydraulic fluid (leveling system reservoir)", "notes": "Dedicated hydraulic fluid reservoir for leveling system — check level if jacks are slow; low fluid causes air ingestion and erratic jack behavior"},
        ],
    },
    "worn_shocks": {
        "label": "Worn shock absorbers (bouncing, wallowing on highways — all chassis types)",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "HD RV shock absorbers (Bilstein, Monroe Load Adjust, KYB)", "notes": "RV-specific shocks are rated for coach weight — standard passenger car shocks cannot support RV weight; confirm GVWR and axle position"},
        ],
    },
    "wheel_bearing": {
        "label": "Wheel bearing failure (humming, heat at wheel hub) — safety-critical at RV weight",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Wheel bearing and seal (axle-specific, matched pair)", "notes": "SAFETY-CRITICAL: wheel bearing failure at highway speed on a Class A can cause wheel separation; at first sign of humming or hub heat, stop and inspect"},
            {"name": "Hub oil bath refill or grease pack", "notes": "Many RV axles use oil bath hubs — check oil level at hub sight glass monthly; run dry for even 100 miles and the bearing will fail"},
        ],
    },
    "tag_axle_fault": {
        "label": "Tag axle fault (third axle on large diesel pushers — oscillation, uneven tire wear, retraction issue)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Tag axle air bag / beam suspension", "notes": "Tag axle retraction at low speed is controlled by a pressure valve — if tag drags at low speed and lifts at highway speed, the valve is the first suspect"},
        ],
    },
    "alignment_issue": {
        "label": "Alignment drift (pulling, uneven tire wear) — common after pothole or curb strike at coach weight",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Motorhome alignment (requires RV-capable alignment shop)", "notes": "Not all alignment shops can handle Class A coaches — confirm the shop has a drive-on rack rated for coach weight before scheduling"},
        ],
    },
}

SUSPENSION_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary suspension, handling, or leveling symptom?",
        "options": [
            {
                "match": "leveling_fault",
                "label": "Leveling jack won't extend/retract, coach unlevel after setup, or leveling warning light",
                "deltas": {
                    "leveling_system_fault": +0.60,
                    "air_compressor_dryer": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_class",
            },
            {
                "match": "one_corner_low",
                "label": "One corner of the RV sits noticeably lower (air bag or spring sagged)",
                "deltas": {
                    "air_bag_leak": +0.55,
                    "worn_shocks": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_class",
            },
            {
                "match": "bouncing_wallowing",
                "label": "Excessive bouncing, wallowing, or body roll at highway speed",
                "deltas": {
                    "worn_shocks": +0.40,
                    "air_bag_leak": +0.20,
                },
                "eliminate": [],
                "next_node": "chassis_class",
            },
            {
                "match": "pulling_alignment",
                "label": "RV pulls to one side or shows uneven tire wear",
                "deltas": {
                    "alignment_issue": +0.40,
                    "air_bag_leak": +0.20,
                    "wheel_bearing": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_class",
            },
            {
                "match": "hub_heat_hum",
                "label": "Humming noise from a wheel or hub feels hot after driving",
                "deltas": {
                    "wheel_bearing": +0.65,
                },
                "eliminate": [],
                "next_node": "chassis_class",
            },
        ],
    },

    "chassis_class": {
        "question": "What class of RV is this?",
        "options": [
            {
                "match": "class_a_diesel",
                "label": "Class A diesel pusher",
                "deltas": {
                    "air_bag_leak": +0.15,
                    "air_compressor_dryer": +0.08,
                    "tag_axle_fault": +0.08,
                    "worn_shocks": -0.05,
                },
                "eliminate": [],
                "next_node": "air_system",
            },
            {
                "match": "class_a_gas",
                "label": "Class A gas (Workhorse, Ford F53)",
                "deltas": {
                    "air_bag_leak": -0.15,
                    "worn_shocks": +0.10,
                    "alignment_issue": +0.05,
                },
                "eliminate": ["air_bag_leak", "air_compressor_dryer", "tag_axle_fault"],
                "next_node": "air_system",
            },
            {
                "match": "class_c",
                "label": "Class C (Ford E-450, Chevy Express, Ram ProMaster)",
                "deltas": {
                    "air_bag_leak": -0.20,
                    "worn_shocks": +0.10,
                },
                "eliminate": ["air_bag_leak", "air_compressor_dryer", "tag_axle_fault"],
                "next_node": "air_system",
            },
        ],
    },

    "air_system": {
        "question": "For air-ride coaches: is there a hissing or air leak sound from under the coach, or a low air pressure warning?",
        "options": [
            {
                "match": "hissing_low_pressure",
                "label": "Yes — hissing sound or low air pressure warning",
                "deltas": {
                    "air_bag_leak": +0.30,
                    "air_compressor_dryer": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_air_issue",
                "label": "No air leak or pressure issue noticed",
                "deltas": {
                    "worn_shocks": +0.08,
                    "alignment_issue": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_air_ride",
                "label": "Not applicable — this is a gas/spring chassis (no air ride)",
                "deltas": {
                    "air_bag_leak": -0.20,
                    "worn_shocks": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

SUSPENSION_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "air_bag_leak": +0.10,
            "worn_shocks": +0.10,
            "wheel_bearing": +0.08,
            "air_compressor_dryer": +0.06,
        },
    },
    "usage_pattern": {
        "highway": {
            "worn_shocks": +0.08,
            "alignment_issue": +0.05,
        },
    },
}

SUSPENSION_RV_POST_DIAGNOSIS: list[str] = [
    "SAFETY: If a wheel bearing heat or humming symptom was identified, do not continue driving to a shop — hub failure at highway speed on a Class A can cause wheel separation; call a mobile RV tech or tow to nearest service center.",
    "After any leveling jack service, test the full retract cycle before driving — a jack that fails to fully retract even 1 inch will contact the road surface when the coach settles under load; this causes immediate structural damage to the jack and the chassis.",
    "Air bag replacement on a Class A diesel pusher requires depressurizing the entire air system first — never unbolt an air bag fitting under pressure; the air dryer/compressor must be isolated and tanks bled before working on any air suspension component.",
]
