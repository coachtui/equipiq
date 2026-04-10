"""
Suspension diagnostic tree — motorcycle variant.

Key differences from base car tree:
- Front suspension: telescopic fork (right-side-up or USD/inverted) with oil and springs
- Rear suspension: single shock (most bikes) or dual shocks (cruisers and older bikes)
- Fork seals leak oil — visible oil streaks down the lower fork legs is a primary symptom
- Fork oil viscosity and level affect handling significantly
- Steering head bearings (headset) are unique to motorcycles — wear causes fork vague-ness
  and a characteristic "notchy" center feel when turning the bars
- Rear shock preload and rebound are adjustable on most bikes — incorrect setup
  feels like a worn suspension issue
- Swingarm pivot bearing and linkage bearings are common wear items on sport bikes
"""

SUSPENSION_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "fork_seals_oil": {
        "label": "Fork seal leak or low/degraded fork oil (oil streaks on lower legs, soft or wallowing front end)",
        "prior": 0.30,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fork seal kit (dust seals and oil seals, matched pair)", "notes": "Always replace both forks together — mismatched seal condition causes uneven damping; confirm inner tube diameter"},
            {"name": "Fork oil (correct viscosity per service manual)", "notes": "Viscosity is as important as level — 5W, 10W, and 15W give very different handling feel; use manufacturer spec"},
        ],
    },
    "rear_shock_worn": {
        "label": "Worn or blown rear shock (bouncing, bottoming out, harsh ride, leaking oil at shock body)",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Rear shock absorber", "notes": "Mono-shock bikes: confirm spring rate and linkage ratio before selecting replacement; aftermarket (Öhlins, YSS, Progressive) often superior to OEM on high-mileage bikes"},
            {"name": "Rear shock linkage bearing kit", "notes": "Linkage bearings are a separate wear item — replace at the same time as the shock for a complete rebuild; needle bearings rust from water intrusion"},
        ],
    },
    "steering_head_bearing": {
        "label": "Worn steering head bearings (vague or notchy steering, wobble at specific speeds)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Steering head bearing kit (tapered roller or ball race)", "notes": "Tapered roller bearing replacement (Pivot Works or All Balls) is a significant upgrade over stock ball bearings on most bikes — better load capacity and adjustability"},
        ],
    },
    "swingarm_bearing": {
        "label": "Worn swingarm pivot or linkage bearings (vague rear end, clunking from rear over bumps)",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Swingarm pivot bearing and seal kit", "notes": "Requires swingarm removal — bearings are pressed in; neglected greasing or water entry causes premature failure on adventure and enduro bikes"},
        ],
    },
    "front_wheel_bearing": {
        "label": "Worn front wheel bearing (wobble, humming, play when wheel is spun off the ground)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Front wheel bearing (sealed)", "notes": "Simple replacement with a bearing driver — confirm bearing dimensions by wheel size; check disc/rotor run-out after replacing"},
        ],
    },
    "shock_setup_preload": {
        "label": "Incorrect shock preload or rebound setting (handling complaint — not mechanical failure)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — suspension setup adjustment only", "notes": "Measure sag: 25–30mm front (unloaded), 30–35mm rear (rider on) is a general starting point; adjust preload collars and rebound damping to spec"},
        ],
    },
}

SUSPENSION_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary suspension symptom?",
        "options": [
            {
                "match": "oil_leak_fork",
                "label": "Oil streaks or wet oil on the lower fork legs",
                "deltas": {
                    "fork_seals_oil": +0.70,
                },
                "eliminate": [],
                "next_node": "location",
            },
            {
                "match": "wobbly_vague",
                "label": "Wobble, weave, or vague/imprecise steering feel at speed",
                "deltas": {
                    "steering_head_bearing": +0.30,
                    "rear_shock_worn": +0.15,
                    "fork_seals_oil": +0.10,
                    "swingarm_bearing": +0.10,
                },
                "eliminate": [],
                "next_node": "location",
            },
            {
                "match": "bottoming_soft",
                "label": "Front end dives under braking, bottoms out over bumps, or rear bounces",
                "deltas": {
                    "fork_seals_oil": +0.25,
                    "rear_shock_worn": +0.25,
                    "shock_setup_preload": +0.15,
                },
                "eliminate": [],
                "next_node": "location",
            },
            {
                "match": "clunk_rear",
                "label": "Clunking or knocking from the rear suspension area over bumps",
                "deltas": {
                    "swingarm_bearing": +0.35,
                    "rear_shock_worn": +0.25,
                },
                "eliminate": [],
                "next_node": "location",
            },
            {
                "match": "notchy_center",
                "label": "Steering feels notchy or has a dead spot in the center when turning the bars slowly",
                "deltas": {
                    "steering_head_bearing": +0.70,
                },
                "eliminate": [],
                "next_node": "location",
            },
        ],
    },

    "location": {
        "question": "Is the problem primarily from the front, rear, or both ends?",
        "options": [
            {
                "match": "front",
                "label": "Front — fork area, steering, or front wheel",
                "deltas": {
                    "fork_seals_oil": +0.10,
                    "steering_head_bearing": +0.10,
                    "front_wheel_bearing": +0.05,
                    "rear_shock_worn": -0.10,
                    "swingarm_bearing": -0.10,
                },
                "eliminate": [],
                "next_node": "mileage_service",
            },
            {
                "match": "rear",
                "label": "Rear — shock, linkage, or swingarm area",
                "deltas": {
                    "rear_shock_worn": +0.15,
                    "swingarm_bearing": +0.10,
                    "fork_seals_oil": -0.15,
                    "steering_head_bearing": -0.10,
                },
                "eliminate": [],
                "next_node": "mileage_service",
            },
            {
                "match": "both",
                "label": "Both ends affected",
                "deltas": {
                    "fork_seals_oil": +0.05,
                    "rear_shock_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "mileage_service",
            },
        ],
    },

    "mileage_service": {
        "question": "Has the suspension ever been serviced (fork oil changed, bearings greased, shock rebuilt) on this bike?",
        "options": [
            {
                "match": "never_unknown",
                "label": "Never serviced or unknown service history",
                "deltas": {
                    "fork_seals_oil": +0.15,
                    "steering_head_bearing": +0.12,
                    "swingarm_bearing": +0.12,
                    "rear_shock_worn": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "recently_serviced",
                "label": "Recently serviced — fork oil changed, bearings greased",
                "deltas": {
                    "fork_seals_oil": -0.10,
                    "steering_head_bearing": -0.08,
                    "shock_setup_preload": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

SUSPENSION_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "fork_seals_oil": +0.12,
            "steering_head_bearing": +0.10,
            "rear_shock_worn": +0.10,
            "swingarm_bearing": +0.08,
        },
    },
    "storage_time": {
        "long": {
            "fork_seals_oil": +0.10,
            "steering_head_bearing": +0.08,
            "swingarm_bearing": +0.08,
        },
    },
}

SUSPENSION_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "When replacing fork seals, also change the fork oil — old oil degrades and causes the new seals to fail prematurely; measure oil level by depth (not volume) after removing the spring to get an accurate fill.",
    "After replacing steering head bearings, adjust the bearing preload carefully before riding — too tight causes heavy steering and rapid wear; too loose allows the wobble to return immediately; check by rocking the fork fore and aft with the front wheel lifted.",
    "Linkage bearing lubrication is often listed as a 12,000-mile interval in service manuals but should be done annually on bikes ridden in rain or off-road — water intrusion corrodes needle bearings rapidly and the service is inexpensive compared to swingarm removal later.",
]
