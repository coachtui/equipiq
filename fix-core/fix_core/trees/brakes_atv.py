"""
Brakes diagnostic tree — ATV/UTV variant.

Key differences from base car tree:
- Rear drum brakes are common on most ATVs (especially entry-level and utility)
- Front disc brakes can be single or dual, often with simple single-piston calipers
- Cable-actuated rear drum is standard on many utility ATVs
- Mud, trail debris, and water packing into calipers is a primary failure mode
- Sporadic use and storage causes caliper seizure more than wear
- UTVs (side-by-sides) more closely mirror car brake systems (4-wheel hydraulic disc)
"""

BRAKES_ATV_HYPOTHESES: dict[str, dict] = {
    "worn_brake_pads": {
        "label": "Worn brake pads or rear drum shoes",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Front brake pads", "notes": "ATV front calipers are simple single-piston — pads are inexpensive; confirm fitment by year/make/model"},
            {"name": "Rear brake shoes", "notes": "Most utility ATVs have drum rear — measure drum before ordering; check for scoring"},
        ],
    },
    "stuck_caliper_or_mud": {
        "label": "Seized caliper piston or mud/debris packed into caliper (dragging, uneven pad wear)",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper rebuild kit", "notes": "ATV calipers are simple and inexpensive to rebuild — mud packing and moisture are the primary causes of seizure"},
            {"name": "Brake caliper (replacement)", "notes": "If corrosion is beyond rebuild — ATV aftermarket calipers are low cost"},
        ],
    },
    "brake_fluid_low_contaminated": {
        "label": "Low or contaminated brake fluid (spongy lever, water or mud intrusion)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake fluid (DOT 4)", "notes": "ATV master cylinders are small — if fluid is dark or contaminated with water/mud, flush completely; check for cracked reservoir cap"},
        ],
    },
    "cable_fault": {
        "label": "Stretched, kinked, or seized rear brake cable (rear brake has no stopping power)",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Rear brake cable", "notes": "Mud packs into the cable housing — lubricate first; if housing is kinked near the rear axle, replace"},
        ],
    },
    "warped_rotor": {
        "label": "Warped front rotor (pulsating or grabbing under braking)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Front brake rotor", "notes": "ATV rotors are thin — impact from rocks or thermal shock from water crossing can warp them; replace rather than resurface"},
        ],
    },
    "brake_line_hose": {
        "label": "Cracked, kinked, or leaking brake line (spongy or no pressure, visible fluid loss)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "ATV brake line (front)", "notes": "Exposed brake lines on ATVs are vulnerable to trail damage — inspect full run from master cylinder to caliper for abrasion"},
        ],
    },
}

BRAKES_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary brake symptom on the ATV/UTV?",
        "options": [
            {
                "match": "dragging_hot",
                "label": "Wheel drags or won't spin freely — feels hot to the touch after riding",
                "deltas": {
                    "stuck_caliper_or_mud": +0.45,
                    "cable_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "terrain_context",
            },
            {
                "match": "weak_rear",
                "label": "Rear brake has little or no stopping effect",
                "deltas": {
                    "cable_fault": +0.35,
                    "worn_brake_pads": +0.15,
                    "stuck_caliper_or_mud": +0.10,
                },
                "eliminate": [],
                "next_node": "terrain_context",
            },
            {
                "match": "spongy",
                "label": "Spongy, soft, or mushy lever/pedal",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "brake_line_hose": +0.15,
                    "stuck_caliper_or_mud": +0.10,
                },
                "eliminate": [],
                "next_node": "terrain_context",
            },
            {
                "match": "grinding_squealing",
                "label": "Grinding or metal-on-metal noise when braking",
                "deltas": {
                    "worn_brake_pads": +0.35,
                    "stuck_caliper_or_mud": +0.15,
                    "warped_rotor": +0.05,
                },
                "eliminate": [],
                "next_node": "terrain_context",
            },
            {
                "match": "pulsating",
                "label": "Pulsating or grabbing when braking",
                "deltas": {
                    "warped_rotor": +0.40,
                    "stuck_caliper_or_mud": +0.15,
                },
                "eliminate": [],
                "next_node": "terrain_context",
            },
        ],
    },

    "terrain_context": {
        "question": "What conditions was the ATV/UTV used in recently?",
        "options": [
            {
                "match": "mud_water",
                "label": "Deep mud, water crossings, or very wet/dirty conditions",
                "deltas": {
                    "stuck_caliper_or_mud": +0.25,
                    "cable_fault": +0.15,
                    "brake_fluid_low_contaminated": +0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "dry_trail",
                "label": "Dry trails or normal recreational use",
                "deltas": {
                    "worn_brake_pads": +0.10,
                    "warped_rotor": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "storage",
                "label": "Recently out of storage or hadn't been ridden in a while",
                "deltas": {
                    "stuck_caliper_or_mud": +0.20,
                    "brake_fluid_low_contaminated": +0.12,
                    "cable_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Locate the brake fluid reservoir on the handlebar or near the master cylinder. What is the condition?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and clear — looks clean",
                "deltas": {
                    "brake_fluid_low_contaminated": -0.20,
                    "stuck_caliper_or_mud": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dark_contaminated",
                "label": "Dark, murky, or looks like it has debris",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "stuck_caliper_or_mud": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.20,
                    "worn_brake_pads": +0.10,
                    "brake_line_hose": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_reservoir",
                "label": "No hydraulic reservoir — rear brake is cable operated",
                "deltas": {
                    "cable_fault": +0.20,
                    "brake_fluid_low_contaminated": -0.15,
                    "brake_line_hose": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

BRAKES_ATV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_brake_pads": +0.10,
            "stuck_caliper_or_mud": +0.08,
            "cable_fault": +0.06,
        },
    },
    "storage_time": {
        "long": {
            "stuck_caliper_or_mud": +0.18,
            "brake_fluid_low_contaminated": +0.10,
            "cable_fault": +0.08,
        },
    },
    "saltwater_use": {
        "yes": {
            "stuck_caliper_or_mud": +0.12,
            "brake_line_hose": +0.08,
            "cable_fault": +0.08,
        },
    },
}

BRAKES_ATV_POST_DIAGNOSIS: list[str] = [
    "After any mud or water crossing, pump the brakes firmly several times while still moving slowly — this reseats pads against rotors and expels water from the drum gap.",
    "If a caliper was seized from mud packing, disassemble and clean the entire caliper interior including the piston boot grooves — mud trapped behind the dust boot causes the piston to seize again quickly.",
    "Cable-operated rear brakes need lubrication every season — run cable lube from the top of the housing and let it work down; a dry cable stretches and eventually breaks at the crimp fitting.",
]
