"""
Brakes diagnostic tree — truck/HD variant.

Key differences from base car tree:
- Rear drum brakes are common on HD trucks (especially dually, fleet, towing config)
- Trailer brake controller faults (electric trailer brakes)
- Brake fade under sustained towing/downhill grade loads
- Air brake systems on Class 4-6 trucks (fade, low pressure warning)
- Heavier rotors/drums take longer to show wear but are more expensive to resurface
"""

BRAKES_TRUCK_HYPOTHESES: dict[str, dict] = {
    "worn_brake_pads": {
        "label": "Worn brake pads or shoes (front disc pads or rear drum shoes depleted)",
        "prior": 0.26,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake pads (front)", "notes": "HD trucks use thicker pads — confirm correct part for GVWR/tow package"},
            {"name": "Rear brake shoes", "notes": "Common on 3/4-ton and 1-ton trucks; check drum diameter before ordering"},
        ],
    },
    "warped_rotors": {
        "label": "Warped or heat-cracked rotors from towing or sustained downhill braking",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "HD brake rotors (axle pair)", "notes": "Towing trucks need higher-grade rotors — avoid thin economy units that warp quickly under load"},
            {"name": "Brake pads", "notes": "Always replace pads when replacing rotors"},
        ],
    },
    "brake_fade": {
        "label": "Brake fade from sustained towing or repeated downhill stops (overheated brakes)",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Heavy-duty brake fluid (DOT 4 high-temp)", "notes": "Upgrade from DOT 3 if towing regularly — higher boiling point reduces vapor fade"},
            {"name": "Performance brake pads (high-temp compound)", "notes": "Carbon-metallic or ceramic-metallic compounds handle sustained heat better than standard organic pads"},
        ],
    },
    "trailer_brake_controller": {
        "label": "Trailer brake controller fault (trailer brakes not engaging, warning light, or overbraking)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Trailer brake controller", "notes": "Aftermarket proportional controllers (Prodigy, Tekonsha) are more reliable than basic time-delay units"},
            {"name": "7-pin trailer connector", "notes": "Corroded trailer plug pins are often the real culprit before condemning the controller"},
        ],
    },
    "stuck_caliper": {
        "label": "Seized brake caliper or wheel cylinder (dragging, uneven pad wear, pulling)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper (loaded with pads)", "notes": "HD truck calipers are larger — confirm fitment by GVWR and axle code"},
            {"name": "Rear wheel cylinder", "notes": "For drum brake axles; leaking wheel cylinder also causes soft pedal and fluid loss"},
        ],
    },
    "brake_fluid_low_contaminated": {
        "label": "Low or contaminated brake fluid (moisture absorbed, dark/murky)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake fluid (DOT 4 recommended for towing trucks)", "notes": "Flush completely if dark or over 2 years old — moisture lowers boiling point significantly"},
        ],
    },
    "abs_sensor_fault": {
        "label": "ABS wheel speed sensor or tone ring fault (ABS light, trailer sway, stability warning)",
        "prior": 0.06,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "ABS wheel speed sensor", "notes": "Scan for C-code ABS faults first — rear axle sensors on trucks are exposed to more debris"},
        ],
    },
    "brake_booster_master_cylinder": {
        "label": "Failing brake booster or master cylinder (hard pedal or sinking pedal)",
        "prior": 0.04,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Brake master cylinder", "notes": "HD trucks have larger bore master cylinders — confirm part by VIN"},
            {"name": "Hydro-boost unit", "notes": "Many HD trucks use hydro-boost (power steering fluid powered) instead of vacuum boost"},
        ],
    },
}

BRAKES_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary brake symptom?",
        "options": [
            {
                "match": "grinding_noise",
                "label": "Grinding or metal-on-metal noise when braking",
                "deltas": {
                    "worn_brake_pads": +0.25,
                    "warped_rotors": +0.10,
                    "brake_fade": -0.10,
                },
                "eliminate": [],
                "next_node": "towing_context",
            },
            {
                "match": "fade_or_spongy",
                "label": "Pedal feels spongy, fades under sustained braking, or goes to the floor on long downhill",
                "deltas": {
                    "brake_fade": +0.30,
                    "brake_fluid_low_contaminated": +0.15,
                    "brake_booster_master_cylinder": +0.10,
                    "worn_brake_pads": -0.05,
                },
                "eliminate": [],
                "next_node": "towing_context",
            },
            {
                "match": "pulling",
                "label": "Truck pulls to one side when braking",
                "deltas": {
                    "stuck_caliper": +0.30,
                    "warped_rotors": +0.10,
                    "worn_brake_pads": +0.05,
                },
                "eliminate": [],
                "next_node": "towing_context",
            },
            {
                "match": "trailer_issue",
                "label": "Issue specifically when towing — trailer brakes not working, surging, or warning light",
                "deltas": {
                    "trailer_brake_controller": +0.50,
                    "abs_sensor_fault": +0.10,
                    "worn_brake_pads": -0.10,
                    "warped_rotors": -0.10,
                },
                "eliminate": [],
                "next_node": "towing_context",
            },
            {
                "match": "warning_light",
                "label": "ABS, brake, or stability control warning light on",
                "deltas": {
                    "abs_sensor_fault": +0.35,
                    "brake_fluid_low_contaminated": +0.15,
                    "trailer_brake_controller": +0.10,
                },
                "eliminate": [],
                "next_node": "towing_context",
            },
        ],
    },

    "towing_context": {
        "question": "Does the problem occur mainly when towing a trailer, or also when driving without a trailer?",
        "options": [
            {
                "match": "towing_only",
                "label": "Only or much worse when towing",
                "deltas": {
                    "trailer_brake_controller": +0.20,
                    "brake_fade": +0.15,
                    "warped_rotors": +0.05,
                    "stuck_caliper": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "both",
                "label": "Both with and without a trailer",
                "deltas": {
                    "worn_brake_pads": +0.08,
                    "warped_rotors": +0.05,
                    "trailer_brake_controller": -0.15,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "no_trailer",
                "label": "Don't tow / no trailer involved",
                "deltas": {
                    "trailer_brake_controller": -0.30,
                    "worn_brake_pads": +0.05,
                    "warped_rotors": +0.05,
                },
                "eliminate": ["trailer_brake_controller"],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the brake fluid reservoir (under the hood near the firewall). What is the level and color?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and light in color — looks clean",
                "deltas": {
                    "brake_fluid_low_contaminated": -0.20,
                    "stuck_caliper": +0.05,
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": "rear_drum_check",
            },
            {
                "match": "dark",
                "label": "Full but dark brown or black",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "brake_fade": +0.08,
                },
                "eliminate": [],
                "next_node": "rear_drum_check",
            },
            {
                "match": "low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.20,
                    "worn_brake_pads": +0.10,
                    "stuck_caliper": +0.08,
                },
                "eliminate": [],
                "next_node": "rear_drum_check",
            },
        ],
    },

    "rear_drum_check": {
        "question": "Does this truck have rear drum brakes (common on 3/4-ton and 1-ton trucks), or rear disc brakes?",
        "options": [
            {
                "match": "rear_drums",
                "label": "Rear drums (I can see a drum hub, not a rotor, at the rear)",
                "deltas": {
                    "worn_brake_pads": +0.05,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "rear_disc",
                "label": "Rear disc (I can see rotors at all four corners)",
                "deltas": {
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unsure",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

BRAKES_TRUCK_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_brake_pads": +0.10,
            "warped_rotors": +0.08,
            "stuck_caliper": +0.06,
        },
    },
    "usage_pattern": {
        "city": {
            "worn_brake_pads": +0.08,
            "warped_rotors": +0.06,
        },
        "highway": {
            "brake_fade": +0.08,
            "trailer_brake_controller": +0.05,
        },
    },
    "climate": {
        "cold": {
            "stuck_caliper": +0.08,
            "brake_fluid_low_contaminated": +0.05,
        },
    },
    "abs_light_on": {
        "yes": {
            "abs_sensor_fault": +0.25,
        },
    },
}

BRAKES_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After brake fade from towing, allow brakes to fully cool before inspecting — heat-cracked rotors may look fine when hot but show cracks once cold.",
    "When towing regularly, upgrade to DOT 4 fluid and high-temp pads — standard DOT 3 / organic pads are not rated for sustained towing heat cycles.",
    "If trailer brakes were involved, check the 7-pin connector at the truck first — corroded pins are the #1 cause of intermittent trailer brake faults before replacing the controller.",
]
