"""
Suspension diagnostic tree — ATV/UTV variant.

Key differences from base car tree:
- A-arm (double wishbone) front suspension is standard on most ATVs and UTVs
- IRS (independent rear suspension) is common on UTVs and sport ATVs
- Solid rear axle still found on utility ATVs
- Ball joints and tie rod ends take heavy abuse from off-road use and are primary
  wear items
- A-arm bushings pack with mud and degrade faster than on-road use
- Wheel bearings exposed to water/mud contamination — very common failure
- Bent A-arms and toe links after rock or stump strikes are common
"""

SUSPENSION_ATV_HYPOTHESES: dict[str, dict] = {
    "ball_joint_worn": {
        "label": "Worn or failed A-arm ball joint (clunk over bumps, excessive play, front end vague)",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Ball joint (upper and/or lower A-arm)", "notes": "ATV ball joints press in — confirm A-arm bolt pattern; upper and lower joints wear at different rates; check both before ordering only one"},
        ],
    },
    "tie_rod_end": {
        "label": "Worn or bent tie rod or tie rod end (steering play, toe wander, vague steering)",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Tie rod end (inner and/or outer)", "notes": "ATV tie rods bend easily after rock strikes — check for bends visually before ordering ends; bent tube requires full tie rod replacement"},
            {"name": "Tie rod (full assembly)", "notes": "If the rod itself is bent, replace the whole assembly and perform toe adjustment after installation"},
        ],
    },
    "wheel_bearing_worn": {
        "label": "Worn or water-damaged wheel bearing (humming, wobble, rough feel when spinning wheel by hand)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wheel bearing and seal kit", "notes": "ATV wheel bearings fail frequently from water and mud intrusion — replace the seal at the same time; All Balls kit includes bearing and seal"},
        ],
    },
    "a_arm_bushing": {
        "label": "Worn or mud-packed A-arm bushings (clunking, imprecise feel, visible gap at pivot)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "A-arm bushing kit (pivot tube bushings)", "notes": "Rubber bushings pack with mud and degrade — polyurethane replacements last significantly longer on ATVs used in mud; grease after every deep water crossing"},
        ],
    },
    "shock_worn": {
        "label": "Worn shock absorber (bouncing, harsh ride, leaking shock body)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Shock absorber (front or rear)", "notes": "Stock ATV shocks are often marginal for hard use — aftermarket (Fox, Elka, Walker Evans) provide significant improvement for trail or sport use"},
        ],
    },
    "bent_a_arm": {
        "label": "Bent A-arm or toe link from impact (misaligned wheel, won't track straight after a hit)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "A-arm (upper or lower, side-specific)", "notes": "Bent A-arms are common after rock or stump strikes; aftermarket heavier-wall arms are worth the upgrade on trail ATVs if the OEM arm bent on a moderate hit"},
        ],
    },
}

SUSPENSION_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary suspension or steering symptom on the ATV/UTV?",
        "options": [
            {
                "match": "clunk_bump",
                "label": "Clunking or popping over bumps or during turns",
                "deltas": {
                    "ball_joint_worn": +0.30,
                    "a_arm_bushing": +0.20,
                    "wheel_bearing_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "impact_history",
            },
            {
                "match": "steering_vague",
                "label": "Steering feels loose, vague, or has excessive play in the handlebar",
                "deltas": {
                    "tie_rod_end": +0.35,
                    "ball_joint_worn": +0.20,
                    "a_arm_bushing": +0.10,
                },
                "eliminate": [],
                "next_node": "impact_history",
            },
            {
                "match": "wont_track",
                "label": "ATV/UTV doesn't track straight or pulls to one side — especially after an impact",
                "deltas": {
                    "bent_a_arm": +0.35,
                    "tie_rod_end": +0.25,
                    "wheel_bearing_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "impact_history",
            },
            {
                "match": "humming_wobble",
                "label": "Humming noise or wheel wobble — changes with speed",
                "deltas": {
                    "wheel_bearing_worn": +0.55,
                    "bent_a_arm": +0.10,
                },
                "eliminate": [],
                "next_node": "impact_history",
            },
            {
                "match": "bouncing",
                "label": "Excessive bouncing, harsh ride, or rear end bottoming out",
                "deltas": {
                    "shock_worn": +0.50,
                    "a_arm_bushing": +0.10,
                },
                "eliminate": [],
                "next_node": "impact_history",
            },
        ],
    },

    "impact_history": {
        "question": "Did the ATV/UTV recently hit something hard — rock, stump, rut, or drop off a ledge?",
        "options": [
            {
                "match": "recent_impact",
                "label": "Yes — hit something hard recently",
                "deltas": {
                    "bent_a_arm": +0.30,
                    "tie_rod_end": +0.20,
                    "ball_joint_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "mud_water",
            },
            {
                "match": "no_impact",
                "label": "No recent impact — gradual wear",
                "deltas": {
                    "ball_joint_worn": +0.08,
                    "a_arm_bushing": +0.08,
                    "wheel_bearing_worn": +0.08,
                    "bent_a_arm": -0.15,
                },
                "eliminate": [],
                "next_node": "mud_water",
            },
        ],
    },

    "mud_water": {
        "question": "Is this ATV/UTV used regularly in mud, water crossings, or very wet conditions?",
        "options": [
            {
                "match": "regular_mud",
                "label": "Yes — regularly ridden in mud or water crossings",
                "deltas": {
                    "wheel_bearing_worn": +0.20,
                    "a_arm_bushing": +0.12,
                    "ball_joint_worn": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dry_trail",
                "label": "Mostly dry trails or recreational use",
                "deltas": {
                    "ball_joint_worn": +0.08,
                    "shock_worn": +0.06,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

SUSPENSION_ATV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "ball_joint_worn": +0.12,
            "tie_rod_end": +0.10,
            "wheel_bearing_worn": +0.10,
            "a_arm_bushing": +0.08,
        },
    },
    "saltwater_use": {
        "yes": {
            "wheel_bearing_worn": +0.15,
            "a_arm_bushing": +0.10,
            "ball_joint_worn": +0.08,
        },
    },
    "awd_4wd": {
        "yes": {
            "wheel_bearing_worn": +0.05,
        },
    },
}

SUSPENSION_ATV_POST_DIAGNOSIS: list[str] = [
    "After any ball joint or tie rod replacement on an ATV, perform a toe adjustment before riding — most ATVs have a simple toe specification (1/8 inch toe-in is common); incorrect toe causes rapid tire wear on the inside or outside edges.",
    "Grease all A-arm pivot bushings and ball joints after every extended mud or water ride — water intrusion destroys rubber boots and accelerates wear; many ATV ball joints have zerk fittings that are easy to overlook.",
    "When replacing bent A-arms, compare the new and old arm lengths before installing — aftermarket arms sometimes ship in the wrong length for your specific model variant; even a few millimeters of difference changes toe alignment.",
]
