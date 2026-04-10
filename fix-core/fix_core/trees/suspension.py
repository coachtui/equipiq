"""
Suspension and steering diagnostic tree (base / car).

Covers: worn struts/shocks, ball joints, sway bar links/bushings, wheel bearings,
tie rods, CV axles, alignment, and broken springs.
"""

SUSPENSION_HYPOTHESES: dict[str, dict] = {
    "worn_shocks_struts": {
        "label": "Worn shock absorbers or struts (excessive bouncing, poor rebound control)",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Shock absorbers or strut assemblies (replace in axle pairs)", "notes": "Quick strut assemblies include the spring — easier install but pricier than individual components"},
            {"name": "Strut mount bearing plate", "notes": "Replace the top mount and bearing when replacing struts — they wear together"},
        ],
    },
    "ball_joint_worn": {
        "label": "Worn or failing ball joint (clunking on turns or bumps, handling instability)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Ball joint (upper and/or lower)", "notes": "Check both upper and lower — confirm which is loose with a pry bar test before ordering"},
            {"name": "Alignment", "notes": "Mandatory after any ball joint replacement — camber and caster change when ball joints are disturbed"},
        ],
    },
    "sway_bar_link_bushing": {
        "label": "Worn sway bar end link or bushing (sharp clunk over bumps, worse on one side)",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Sway bar end links (both sides)", "notes": "Replace in pairs — the other side is usually close to failing"},
            {"name": "Sway bar bushings", "notes": "Rubber bushings crack and allow the bar to knock against the bracket; polyurethane is a longer-lasting upgrade"},
        ],
    },
    "wheel_bearing": {
        "label": "Failing wheel bearing (humming or grinding that changes with steering input)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wheel hub bearing assembly", "notes": "Sway vehicle side to side at 60 mph — noise getting louder when weight shifts away from a side = that side's bearing is bad"},
        ],
    },
    "tie_rod": {
        "label": "Worn tie rod end or inner tie rod (steering play, wander, uneven tire wear)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Outer tie rod end", "notes": "Grab the wheel at 9 and 3 o'clock and rock — movement indicates worn tie rod or steering gear"},
            {"name": "Inner tie rod (rack end)", "notes": "Move wheel at 12 and 6 o'clock — movement here points to inner tie rod or steering rack"},
            {"name": "Alignment", "notes": "Required after any tie rod replacement"},
        ],
    },
    "cv_axle": {
        "label": "Torn CV boot or worn CV axle (clicking on turns, vibration under acceleration)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CV axle shaft (remanufactured)", "notes": "Replace the full axle rather than re-booting in most cases — labor cost is similar and reman axles are inexpensive"},
        ],
    },
    "alignment_issue": {
        "label": "Wheel alignment out of specification (pulling, wander, uneven tire wear — no worn parts)",
        "prior": 0.05,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Alignment service", "notes": "Four-wheel alignment recommended — confirm all steering/suspension components are tight before spending on alignment"},
        ],
    },
    "spring_broken": {
        "label": "Broken coil spring (sudden ride height drop, harsh impact noise over bumps)",
        "prior": 0.03,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Coil spring (replace in axle pairs)", "notes": "Requires a spring compressor — serious injury risk if done without proper tools; best left to a shop"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

SUSPENSION_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary suspension or steering symptom?",
        "options": [
            {
                "match": "clunking_bumps",
                "label": "Clunking, thudding, or rattling noise over bumps or rough road",
                "deltas": {
                    "sway_bar_link_bushing": +0.20,
                    "ball_joint_worn": +0.15,
                    "worn_shocks_struts": +0.10,
                    "spring_broken": +0.08,
                    "alignment_issue": -0.05,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
            {
                "match": "vibration_shimmy",
                "label": "Steering wheel vibration or shimmy (especially at highway speeds)",
                "deltas": {
                    "wheel_bearing": +0.20,
                    "tie_rod": +0.15,
                    "alignment_issue": +0.15,
                    "worn_shocks_struts": +0.05,
                    "sway_bar_link_bushing": -0.05,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
            {
                "match": "pulling",
                "label": "Vehicle pulls or drifts to one side consistently",
                "deltas": {
                    "alignment_issue": +0.25,
                    "tie_rod": +0.15,
                    "ball_joint_worn": +0.10,
                    "sway_bar_link_bushing": -0.05,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
            {
                "match": "excessive_bouncing",
                "label": "Excessive bouncing — vehicle doesn't settle after bumps or dips",
                "deltas": {
                    "worn_shocks_struts": +0.40,
                    "spring_broken": +0.10,
                    "alignment_issue": -0.05,
                    "cv_axle": -0.05,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
            {
                "match": "clicking_on_turns",
                "label": "Clicking or popping noise specifically when turning",
                "deltas": {
                    "cv_axle": +0.40,
                    "ball_joint_worn": +0.15,
                    "wheel_bearing": +0.10,
                    "sway_bar_link_bushing": -0.05,
                },
                "eliminate": [],
                "next_node": "noise_location",
            },
        ],
    },

    "noise_location": {
        "question": "Where does the noise or sensation seem to originate?",
        "options": [
            {
                "match": "front",
                "label": "Front of the vehicle",
                "deltas": {
                    "ball_joint_worn": +0.10,
                    "sway_bar_link_bushing": +0.08,
                    "tie_rod": +0.08,
                    "cv_axle": +0.08,
                },
                "eliminate": [],
                "next_node": "speed_dependency",
            },
            {
                "match": "rear",
                "label": "Rear of the vehicle",
                "deltas": {
                    "worn_shocks_struts": +0.10,
                    "sway_bar_link_bushing": +0.08,
                    "spring_broken": +0.08,
                    "cv_axle": -0.10,
                    "tie_rod": -0.10,
                },
                "eliminate": [],
                "next_node": "speed_dependency",
            },
            {
                "match": "one_side",
                "label": "One side — left or right",
                "deltas": {
                    "wheel_bearing": +0.10,
                    "ball_joint_worn": +0.08,
                    "cv_axle": +0.08,
                },
                "eliminate": [],
                "next_node": "speed_dependency",
            },
            {
                "match": "unknown",
                "label": "Hard to tell / all over",
                "deltas": {},
                "eliminate": [],
                "next_node": "speed_dependency",
            },
        ],
    },

    "speed_dependency": {
        "question": "When is the symptom most noticeable?",
        "options": [
            {
                "match": "low_speed_bumps",
                "label": "Low speed — over bumps, turning, or parking lot maneuvers",
                "deltas": {
                    "sway_bar_link_bushing": +0.12,
                    "ball_joint_worn": +0.10,
                    "cv_axle": +0.10,
                    "alignment_issue": -0.10,
                },
                "eliminate": [],
                "next_node": "tire_wear",
            },
            {
                "match": "highway_speeds",
                "label": "Highway speeds — above 50–60 mph",
                "deltas": {
                    "wheel_bearing": +0.15,
                    "alignment_issue": +0.12,
                    "worn_shocks_struts": +0.08,
                    "sway_bar_link_bushing": -0.08,
                    "cv_axle": -0.08,
                },
                "eliminate": [],
                "next_node": "tire_wear",
            },
            {
                "match": "all_speeds",
                "label": "All speeds equally",
                "deltas": {
                    "worn_shocks_struts": +0.05,
                },
                "eliminate": [],
                "next_node": "tire_wear",
            },
        ],
    },

    "tire_wear": {
        "question": "Look at the front tires. How does the tread wear appear?",
        "options": [
            {
                "match": "even",
                "label": "Even across the tread — looks normal",
                "deltas": {
                    "alignment_issue": -0.15,
                    "tie_rod": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "edge_wear",
                "label": "Worn on one edge only (inner or outer edge worn down)",
                "deltas": {
                    "alignment_issue": +0.25,
                    "tie_rod": +0.10,
                    "ball_joint_worn": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cupping_scalloping",
                "label": "Cupped or scalloped pattern — uneven patches around the tread",
                "deltas": {
                    "worn_shocks_struts": +0.30,
                    "alignment_issue": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

SUSPENSION_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_shocks_struts": +0.10,
            "ball_joint_worn": +0.08,
            "tie_rod": +0.06,
            "wheel_bearing": +0.06,
        },
    },
    "usage_pattern": {
        "city": {
            "sway_bar_link_bushing": +0.06,
        },
    },
    "climate": {
        "cold": {
            "ball_joint_worn": +0.06,
            "sway_bar_link_bushing": +0.05,
            "spring_broken": +0.04,
        },
    },
    "awd_4wd": {
        "yes": {
            "cv_axle": +0.08,
        },
    },
}

SUSPENSION_POST_DIAGNOSIS: list[str] = [
    "Any steering or suspension repair that touches a component affecting camber, caster, or toe requires a four-wheel alignment afterward — skipping alignment after a ball joint or tie rod replacement will wear through new tires in under 10,000 miles.",
    "If a wheel bearing was the diagnosis, check the hub for play before ordering parts — grab the top and bottom of the wheel and rock it. Side-to-side (9 and 3 o'clock) play typically indicates tie rod wear, not bearing.",
    "After strut replacement, check strut mount play — a worn strut mount bearing is a common source of a popping noise on turns even after new struts are installed.",
]
