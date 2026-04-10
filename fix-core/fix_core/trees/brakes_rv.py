"""
Brakes diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Class A diesel pushers: air brakes (Bendix/Wabco), air pressure warning, spring
  brake (parking brake) actuation
- Class A gas and Class C (Ford/Chevy chassis): 4-wheel hydraulic disc, similar to HD truck
- Electric trailer brake controller is built into the motorhome tow vehicle circuit
- Much higher stopping weight — brake fade under sustained mountain descent is a primary risk
- Foundation brake service intervals shorter than passenger vehicles (weight + mileage)
- Slideout systems and leveling jacks do not affect brake function but confuse owners
"""

BRAKES_RV_HYPOTHESES: dict[str, dict] = {
    "worn_brake_pads_shoes": {
        "label": "Worn brake pads or drum shoes (hydraulic chassis — Class C or gas Class A)",
        "prior": 0.20,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "HD brake pads (axle set)", "notes": "RV chassis use HD truck brakes — confirm axle rating; front axle pads wear faster under nose-heavy weight distribution"},
            {"name": "Rear brake shoes", "notes": "Some older Class C chassis have rear drums; measure drum diameter and check for scoring"},
        ],
    },
    "brake_fade": {
        "label": "Brake fade from sustained mountain descent or repeated stops at gross weight",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "DOT 4 high-temp brake fluid", "notes": "Upgrade from DOT 3 if not already — RVs subject brakes to sustained heat that quickly degrades standard fluid"},
            {"name": "Performance brake pads (high-temp compound)", "notes": "Carbon-metallic or semi-metallic compounds handle sustained load and heat better than organic pads"},
        ],
    },
    "air_brake_fault": {
        "label": "Air brake system fault — low pressure warning, spring brake dragging, or compressor issue (Class A diesel pusher)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Air dryer cartridge", "notes": "Air dryer removes moisture from the system — replace every 3 years or per manufacturer; moisture causes rust in air tanks and valve failure"},
            {"name": "Brake chamber diaphragm", "notes": "Ruptured diaphragm causes air leak and uneven braking; hissing sound near a rear axle is the telltale sign"},
        ],
    },
    "trailer_brake_controller": {
        "label": "Toad (tow vehicle) brake controller fault or disconnected brake wiring",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Proportional brake controller", "notes": "Prodigy P3 or similar — aftermarket proportional controllers are more reliable than OEM time-delay units"},
            {"name": "7-pin or 6-way trailer connector", "notes": "Corrosion in the 7-pin connector is the most common cause of intermittent toad brake faults before condemning the controller"},
        ],
    },
    "brake_fluid_low_contaminated": {
        "label": "Low or contaminated brake fluid (hydraulic chassis — spongy pedal, fluid loss)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "DOT 4 brake fluid", "notes": "RV master cylinder reservoir is often in a hard-to-reach compartment — use a turkey baster to check; flush if dark or over 2 years old"},
        ],
    },
    "stuck_caliper": {
        "label": "Seized brake caliper (hot wheel, pulling, uneven pad wear) — common on infrequently driven units",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Brake caliper (loaded, HD rated)", "notes": "RV calipers are HD truck units — confirm GVWR and axle code; slide pins seize from infrequent use and storage"},
        ],
    },
    "abs_sensor_fault": {
        "label": "ABS or stability control fault (warning light, reduced stopping performance)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "ABS wheel speed sensor", "notes": "RV chassis ABS sensors are identical to the underlying truck chassis — scan for C-codes first"},
        ],
    },
}

BRAKES_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary brake symptom on the RV?",
        "options": [
            {
                "match": "fade_mountain",
                "label": "Brakes faded or became much less effective on a long downhill or mountain grade",
                "deltas": {
                    "brake_fade": +0.45,
                    "worn_brake_pads_shoes": +0.15,
                    "brake_fluid_low_contaminated": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "air_warning",
                "label": "Low air pressure warning light or buzzer, spring brakes applied, or air hissing sound",
                "deltas": {
                    "air_brake_fault": +0.70,
                    "worn_brake_pads_shoes": -0.10,
                    "brake_fluid_low_contaminated": -0.15,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "toad_issue",
                "label": "Issue with towed vehicle (toad) brakes — warning light, surging when stopping",
                "deltas": {
                    "trailer_brake_controller": +0.60,
                    "abs_sensor_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "grinding_noise",
                "label": "Grinding or metal-on-metal noise when braking",
                "deltas": {
                    "worn_brake_pads_shoes": +0.40,
                    "stuck_caliper": +0.15,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "spongy_soft",
                "label": "Spongy or soft pedal — increased pedal travel or goes toward floor",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "brake_fade": +0.15,
                    "stuck_caliper": +0.08,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
            {
                "match": "warning_light",
                "label": "ABS or brake warning light on with no other symptoms",
                "deltas": {
                    "abs_sensor_fault": +0.35,
                    "brake_fluid_low_contaminated": +0.15,
                    "air_brake_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "chassis_type",
            },
        ],
    },

    "chassis_type": {
        "question": "What type of chassis does this RV use?",
        "options": [
            {
                "match": "class_a_diesel",
                "label": "Class A diesel pusher (engine in rear — Cummins, CAT, or similar)",
                "deltas": {
                    "air_brake_fault": +0.30,
                    "worn_brake_pads_shoes": -0.05,
                },
                "eliminate": [],
                "next_node": "tow_vehicle",
            },
            {
                "match": "class_a_gas",
                "label": "Class A gas (Workhorse, Spartan, or Ford F53 chassis)",
                "deltas": {
                    "air_brake_fault": -0.20,
                    "brake_fade": +0.10,
                    "worn_brake_pads_shoes": +0.05,
                },
                "eliminate": ["air_brake_fault"],
                "next_node": "tow_vehicle",
            },
            {
                "match": "class_c",
                "label": "Class C (Ford E-450, Chevy Express, or Ram ProMaster cab chassis)",
                "deltas": {
                    "air_brake_fault": -0.20,
                    "worn_brake_pads_shoes": +0.05,
                    "brake_fade": +0.08,
                },
                "eliminate": ["air_brake_fault"],
                "next_node": "tow_vehicle",
            },
        ],
    },

    "tow_vehicle": {
        "question": "Is a toad (tow vehicle) connected, and does the problem involve the toad or occur when stopping with the toad?",
        "options": [
            {
                "match": "no_toad",
                "label": "No toad / driving solo",
                "deltas": {
                    "trailer_brake_controller": -0.30,
                },
                "eliminate": ["trailer_brake_controller"],
                "next_node": "mileage_service",
            },
            {
                "match": "toad_involved",
                "label": "Yes — toad is connected and involved in the symptom",
                "deltas": {
                    "trailer_brake_controller": +0.25,
                    "abs_sensor_fault": +0.08,
                },
                "eliminate": [],
                "next_node": "mileage_service",
            },
            {
                "match": "toad_not_involved",
                "label": "Toad is connected but problem occurs without it being relevant",
                "deltas": {
                    "trailer_brake_controller": -0.15,
                },
                "eliminate": [],
                "next_node": "mileage_service",
            },
        ],
    },

    "mileage_service": {
        "question": "When was the last full brake service (pads, fluid flush) on this RV?",
        "options": [
            {
                "match": "recent",
                "label": "Within the past year or 15,000 miles",
                "deltas": {
                    "worn_brake_pads_shoes": -0.10,
                    "brake_fluid_low_contaminated": -0.10,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "overdue",
                "label": "Over 2 years ago or unknown",
                "deltas": {
                    "worn_brake_pads_shoes": +0.15,
                    "brake_fluid_low_contaminated": +0.15,
                    "stuck_caliper": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

BRAKES_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_brake_pads_shoes": +0.10,
            "stuck_caliper": +0.08,
            "air_brake_fault": +0.06,
        },
    },
    "usage_pattern": {
        "highway": {
            "brake_fade": +0.10,
            "trailer_brake_controller": +0.05,
        },
    },
    "abs_light_on": {
        "yes": {
            "abs_sensor_fault": +0.25,
        },
    },
}

BRAKES_RV_POST_DIAGNOSIS: list[str] = [
    "Class A diesel pushers with air brakes: drain both air tanks weekly during a trip — water accumulates from compressed air moisture and corrodes valves from the inside.",
    "After brake fade on a long downhill, allow full cool-down before inspecting — do not pour water on hot rotors or drums; thermal shock causes immediate cracking in cast iron.",
    "RV brakes are rated for the specific GVWR of the chassis — never exceed the published weight rating when loaded, as overloaded brakes will fade earlier and wear out significantly faster than their rated interval.",
]
