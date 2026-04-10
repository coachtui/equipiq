"""
Brakes diagnostic tree — motorcycle variant.

Key differences from base car tree:
- Front/rear brakes are independent (no proportioning valve linking them)
- Cable-actuated rear brakes are common on older/smaller bikes
- Linked brake systems (Honda CBS) — pressing rear lever also applies some front
- ABS is rare on older bikes; modern adventure/touring bikes have it
- Single front disc is norm; dual front discs on larger sport bikes
- Drum rear brakes still common on cruisers and small displacement bikes
- Lever/pedal feel is the primary diagnostic signal (no booster)
"""

BRAKES_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "worn_brake_pads": {
        "label": "Worn brake pads or shoes (front disc pads or rear drum shoes depleted)",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Front brake pads", "notes": "Confirm disc size and caliper piston count — sport bikes use radial mount calipers with different pad shapes"},
            {"name": "Rear brake shoes", "notes": "Drum rear common on cruisers and small bikes; measure drum diameter before ordering"},
        ],
    },
    "warped_rotors": {
        "label": "Warped or glazed rotor (pulsating lever or pedal, grabbing sensation)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Front brake rotor (disc)", "notes": "Check runout with a dial indicator — motorcycle rotors are thin and warp easily from thermal shock (washing hot rotor)"},
            {"name": "Brake pads", "notes": "Replace pads whenever replacing rotor — glazed pad surface on a new rotor causes grabbing"},
        ],
    },
    "brake_fluid_low_contaminated": {
        "label": "Low or contaminated brake fluid (spongy lever, moisture absorbed)",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake fluid (DOT 4 for most bikes — check owner's manual)", "notes": "Motorcycle brake systems are small — moisture contamination affects them faster than car systems; flush every 2 years"},
        ],
    },
    "stuck_caliper": {
        "label": "Seized brake caliper piston (dragging, hot wheel, uneven pad wear)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper rebuild kit (pistons, seals, dust boots)", "notes": "Motorcycle calipers seize from long-term storage or infrequent use — rebuild before condemning the caliper"},
            {"name": "Brake caliper (replacement)", "notes": "If pistons are corroded beyond rebuild — confirm piston count and mounting style"},
        ],
    },
    "cable_or_lever_fault": {
        "label": "Stretched, frayed, or kinked brake cable, or worn lever pivot (rear cable or front disc lever on older bikes)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Rear brake cable", "notes": "Rear drum brakes use a cable — lubricate before replacing; kinks near the drum end are the most common failure point"},
            {"name": "Brake lever (front)", "notes": "Worn pivot causes excessive free play; bent lever after a drop won't return to correct position"},
        ],
    },
    "brake_line_hose": {
        "label": "Cracked, swollen, or leaking brake line or banjo fitting (spongy lever, visible fluid)",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Braided stainless steel brake line", "notes": "Aftermarket SS lines eliminate rubber hose expansion — direct upgrade; requires bleeding"},
            {"name": "Banjo bolt and crush washers", "notes": "Always use new copper crush washers when reassembling banjo fittings — reusing old ones causes slow leaks"},
        ],
    },
    "abs_sensor_fault": {
        "label": "ABS wheel speed sensor or reluctor ring fault (ABS warning light on modern bikes)",
        "prior": 0.05,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "ABS wheel speed sensor", "notes": "Front sensor is most exposed to debris on motorcycles — check for bent tone ring from a drop first"},
        ],
    },
}

BRAKES_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary brake symptom?",
        "options": [
            {
                "match": "spongy_lever",
                "label": "Spongy or soft brake lever or pedal — no firm resistance",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "brake_line_hose": +0.15,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": "front_or_rear",
            },
            {
                "match": "pulsating",
                "label": "Pulsating, grabbing, or vibrating lever/pedal when braking",
                "deltas": {
                    "warped_rotors": +0.40,
                    "worn_brake_pads": +0.10,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": "front_or_rear",
            },
            {
                "match": "dragging",
                "label": "Wheel drags or feels hot — doesn't spin freely when bike is not braking",
                "deltas": {
                    "stuck_caliper": +0.45,
                    "warped_rotors": +0.10,
                    "cable_or_lever_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "front_or_rear",
            },
            {
                "match": "weak_stopping",
                "label": "Weak braking — poor stopping power even with full lever/pedal pressure",
                "deltas": {
                    "worn_brake_pads": +0.30,
                    "warped_rotors": +0.10,
                    "brake_fluid_low_contaminated": +0.10,
                },
                "eliminate": [],
                "next_node": "front_or_rear",
            },
            {
                "match": "warning_light",
                "label": "ABS or brake warning light on dash",
                "deltas": {
                    "abs_sensor_fault": +0.45,
                    "brake_fluid_low_contaminated": +0.15,
                },
                "eliminate": [],
                "next_node": "front_or_rear",
            },
        ],
    },

    "front_or_rear": {
        "question": "Which brake is affected?",
        "options": [
            {
                "match": "front",
                "label": "Front brake (lever on right handlebar)",
                "deltas": {
                    "warped_rotors": +0.08,
                    "cable_or_lever_fault": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "rear",
                "label": "Rear brake (foot pedal or left-hand lever)",
                "deltas": {
                    "cable_or_lever_fault": +0.15,
                    "warped_rotors": -0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "both",
                "label": "Both front and rear affected",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.12,
                    "worn_brake_pads": +0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the brake fluid reservoir (usually on the handlebar for front, near the master cylinder for rear). What is the level and color?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and clear/light yellow — looks clean",
                "deltas": {
                    "brake_fluid_low_contaminated": -0.20,
                    "stuck_caliper": +0.08,
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
            {
                "match": "dark",
                "label": "Full but dark brown or black — old fluid",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
            {
                "match": "low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.20,
                    "worn_brake_pads": +0.12,
                    "brake_line_hose": +0.08,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
            {
                "match": "no_reservoir",
                "label": "No reservoir visible — this brake uses a cable (rear drum)",
                "deltas": {
                    "cable_or_lever_fault": +0.25,
                    "brake_fluid_low_contaminated": -0.20,
                    "brake_line_hose": -0.15,
                },
                "eliminate": [],
                "next_node": "storage_check",
            },
        ],
    },

    "storage_check": {
        "question": "Was the bike recently brought out of storage or has it been sitting unused?",
        "options": [
            {
                "match": "long_storage",
                "label": "Yes — sat for more than a few months",
                "deltas": {
                    "stuck_caliper": +0.25,
                    "brake_fluid_low_contaminated": +0.15,
                    "cable_or_lever_fault": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "regular_use",
                "label": "No — ridden regularly",
                "deltas": {
                    "worn_brake_pads": +0.08,
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

BRAKES_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_brake_pads": +0.10,
            "warped_rotors": +0.08,
            "stuck_caliper": +0.08,
            "brake_fluid_low_contaminated": +0.05,
        },
    },
    "storage_time": {
        "long": {
            "stuck_caliper": +0.15,
            "brake_fluid_low_contaminated": +0.10,
            "cable_or_lever_fault": +0.08,
        },
    },
    "abs_light_on": {
        "yes": {
            "abs_sensor_fault": +0.25,
        },
    },
}

BRAKES_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After any brake work on a motorcycle, pump the lever/pedal firmly 10–15 times before riding — motorcycles have no power booster and the lever must rebuild pressure manually.",
    "If a caliper was seized from storage, clean and lubricate the caliper slide pins and rebuild the piston seals rather than just forcing the piston back — the seals are what caused the seizure.",
    "Never apply the front brake immediately after washing the bike — allow the rotor to air dry or bed in with light, progressive stops; thermal shock from cold water on a hot rotor warps thin motorcycle rotors.",
]
