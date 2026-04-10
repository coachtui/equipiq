"""
Suspension diagnostic tree — truck/HD variant.

Key differences from base car tree:
- Solid rear axle (leaf springs) is standard on most 3/4-ton and 1-ton trucks
- Torsion bar front suspension on many Dodge/Ram trucks and older GM trucks
- Lifted trucks introduce geometry problems: CV axle bind, driveshaft vibration,
  worn cam bolts from caster correction, premature tie rod wear
- HD trucks are often loaded or towing — overloaded suspensions mask symptoms
- Dana 60 / AAM front axle with steering stabilizer — stabilizer failure adds to
  wobble diagnosis
- Death wobble (violent steering shimmy at speed) is a known failure mode on
  solid-axle trucks and lifted Jeeps
"""

SUSPENSION_TRUCK_HYPOTHESES: dict[str, dict] = {
    "worn_shocks_struts": {
        "label": "Worn shock absorbers (HD trucks use heavy-duty shocks — degraded under load and towing)",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "HD shock absorbers (front and/or rear)", "notes": "Confirm load rating — trucks used for towing or payload need load-rated shocks; standard passenger shocks bottom out under load"},
        ],
    },
    "leaf_spring_worn": {
        "label": "Worn, broken, or sagging leaf spring (rear of truck sitting low, bottoming out under load)",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Leaf spring pack (rear, driver or passenger side)", "notes": "Individual broken leaf can sometimes be replaced; heavily sagged packs need full replacement — confirm U-bolt and center pin spec"},
            {"name": "Leaf spring bushings (eye bolts and shackle)", "notes": "Rubber spring eye bushings crack and degrade — replace at same time as spring for long-term fix"},
        ],
    },
    "ball_joint_worn": {
        "label": "Worn upper or lower ball joint (clunk, death wobble on solid-axle trucks, pulling)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Ball joint (upper and/or lower)", "notes": "Solid front axle trucks (Dana 60, AAM 9.25) use high-load ball joints — use a press; check both upper and lower before replacing only one"},
            {"name": "Alignment (post-replacement)", "notes": "Ball joint replacement always requires alignment — especially critical on lifted trucks with altered caster/camber geometry"},
        ],
    },
    "death_wobble": {
        "label": "Death wobble — violent steering shimmy above 45–55 mph on solid-axle truck or lifted 4WD",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Steering stabilizer", "notes": "Worn stabilizer is often the trigger for death wobble — but replacing it alone only masks the underlying worn components; inspect tie rods, drag link, ball joints, and trackbar first"},
            {"name": "Track bar (Panhard rod) and bracket", "notes": "Loose or worn track bar allows axle to shift laterally — a primary cause of death wobble on lifted Ram trucks and Jeeps"},
            {"name": "Tie rod ends (drag link and tie rod)", "notes": "Any play in the front steering linkage amplifies at speed into wobble — check all pivots with a helper turning the wheel"},
        ],
    },
    "sway_bar_link_bushing": {
        "label": "Worn sway bar end links or bushings (clunking over bumps, body roll under load)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Sway bar end links (front)", "notes": "HD trucks use heavy-duty end links — confirm correct length for stock or lifted height"},
            {"name": "Sway bar bushings (frame mount)", "notes": "Polyurethane replacements last significantly longer than rubber on trucks used for towing or off-road"},
        ],
    },
    "wheel_bearing": {
        "label": "Worn front or rear wheel bearing (humming noise, changes with steering input)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Front wheel bearing / hub assembly", "notes": "HD trucks often have bolt-on hub assemblies — confirm 4WD or 2WD spec; 4WD hubs are different"},
            {"name": "Rear wheel bearing (axle bearing)", "notes": "Solid axle trucks have inner axle bearings that can be replaced without replacing the full hub"},
        ],
    },
    "torsion_bar": {
        "label": "Failed or uneven torsion bar (front sits low on one side — Ram, older Silverado/Sierra)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Torsion bar (front, side-specific)", "notes": "Torsion bars rarely break but key-ends wear — if adjustment won't bring ride height back, measure bar length and check key end"},
            {"name": "Torsion bar adjustment bolt / key", "notes": "Adjustment range exhausted on high-mileage trucks — replacing the key or bar is the long-term fix"},
        ],
    },
    "cv_axle": {
        "label": "Torn CV boot or worn CV axle (clicking on turns, vibration on acceleration — lifted or 4WD trucks)",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CV axle shaft (front, driver or passenger)", "notes": "Lifted trucks run CV axles at extreme angles — accelerated wear is normal; inspect inner and outer joints for torn boots and play"},
        ],
    },
}

SUSPENSION_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary suspension or steering symptom?",
        "options": [
            {
                "match": "death_wobble",
                "label": "Death wobble or violent steering shimmy at highway speed (solid-axle / lifted truck)",
                "deltas": {
                    "death_wobble": +0.55,
                    "ball_joint_worn": +0.10,
                    "worn_shocks_struts": +0.08,
                },
                "eliminate": [],
                "next_node": "lift_status",
            },
            {
                "match": "clunk_bump",
                "label": "Clunking or banging over bumps",
                "deltas": {
                    "sway_bar_link_bushing": +0.25,
                    "leaf_spring_worn": +0.20,
                    "ball_joint_worn": +0.15,
                    "worn_shocks_struts": +0.08,
                },
                "eliminate": [],
                "next_node": "lift_status",
            },
            {
                "match": "sagging_low",
                "label": "Rear (or front) of truck sitting low or bottoming out under load",
                "deltas": {
                    "leaf_spring_worn": +0.40,
                    "worn_shocks_struts": +0.20,
                    "torsion_bar": +0.15,
                },
                "eliminate": [],
                "next_node": "lift_status",
            },
            {
                "match": "pulling_wander",
                "label": "Truck pulls to one side or wanders at highway speed",
                "deltas": {
                    "ball_joint_worn": +0.20,
                    "worn_shocks_struts": +0.15,
                    "death_wobble": +0.10,
                },
                "eliminate": [],
                "next_node": "lift_status",
            },
            {
                "match": "humming_noise",
                "label": "Humming or droning noise that changes speed with the truck — louder on one side",
                "deltas": {
                    "wheel_bearing": +0.55,
                    "cv_axle": +0.10,
                },
                "eliminate": [],
                "next_node": "lift_status",
            },
        ],
    },

    "lift_status": {
        "question": "Is this truck lifted (suspension lift or leveling kit installed)?",
        "options": [
            {
                "match": "lifted",
                "label": "Yes — has a suspension lift or leveling kit",
                "deltas": {
                    "death_wobble": +0.15,
                    "cv_axle": +0.15,
                    "ball_joint_worn": +0.10,
                },
                "eliminate": [],
                "next_node": "load_context",
            },
            {
                "match": "stock",
                "label": "No — stock ride height",
                "deltas": {
                    "cv_axle": -0.05,
                    "death_wobble": -0.08,
                    "leaf_spring_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "load_context",
            },
        ],
    },

    "load_context": {
        "question": "Is the truck used for towing, heavy payloads, or off-road use?",
        "options": [
            {
                "match": "heavy_use",
                "label": "Yes — regular towing, heavy loads, or off-road",
                "deltas": {
                    "leaf_spring_worn": +0.15,
                    "worn_shocks_struts": +0.12,
                    "ball_joint_worn": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "light_use",
                "label": "No — mostly light-duty daily driving",
                "deltas": {
                    "sway_bar_link_bushing": +0.05,
                    "worn_shocks_struts": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

SUSPENSION_TRUCK_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_shocks_struts": +0.10,
            "ball_joint_worn": +0.10,
            "leaf_spring_worn": +0.08,
            "wheel_bearing": +0.06,
        },
    },
    "usage_pattern": {
        "highway": {
            "worn_shocks_struts": +0.06,
            "death_wobble": +0.06,
        },
    },
    "awd_4wd": {
        "yes": {
            "cv_axle": +0.10,
            "ball_joint_worn": +0.06,
        },
    },
    "climate": {
        "cold": {
            "ball_joint_worn": +0.08,
            "leaf_spring_worn": +0.06,
            "sway_bar_link_bushing": +0.06,
        },
    },
}

SUSPENSION_TRUCK_POST_DIAGNOSIS: list[str] = [
    "Death wobble on a solid-axle truck is almost always the result of multiple worn components amplifying each other — replacing only the steering stabilizer without inspecting ball joints, trackbar, and tie rods will result in recurrence.",
    "After any front suspension or steering component replacement on a solid-axle truck, a 4-wheel alignment is mandatory — caster correction cam bolts (if equipped) must be set before alignment, especially on lifted trucks.",
    "If leaf springs were serviced, re-torque the U-bolts after the first 500 miles — U-bolts seat and loosen slightly as the suspension cycles; loose U-bolts allow the axle to shift on the spring pad and cause handling problems.",
]
