"""
Brakes diagnostic tree (base / car).

Covers: worn pads/shoes, warped rotors, brake fluid, seized caliper, ABS sensor,
brake line/hose, brake booster/master cylinder, glazed pads/rotors.
"""

BRAKES_HYPOTHESES: dict[str, dict] = {
    "worn_brake_pads": {
        "label": "Worn brake pads or shoes (friction material depleted)",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake pads (front and/or rear)", "notes": "Replace axle pairs — never one side only; match OEM friction rating"},
            {"name": "Brake pad wear indicators / hardware kit", "notes": "Replace clips and shims when they come with the kit"},
        ],
    },
    "warped_rotors": {
        "label": "Warped or scored brake rotors causing pulsation or noise",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake rotors (front and/or rear pair)", "notes": "Replace in axle pairs; measure thickness before deciding resurface vs. replace"},
            {"name": "Brake pads", "notes": "Always replace pads when replacing rotors — bedding new pads on worn rotors causes glazing"},
        ],
    },
    "brake_fluid_low_contaminated": {
        "label": "Low or contaminated brake fluid (moisture absorbed, dark/murky)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake fluid (correct DOT spec — check reservoir cap)", "notes": "DOT 3/4 are glycol-based; DOT 5 is silicone — never mix"},
            {"name": "Brake bleeder kit", "notes": "Flush completely if fluid is dark or more than 2 years old"},
        ],
    },
    "stuck_caliper": {
        "label": "Seized brake caliper or wheel cylinder (dragging brakes, pulling to one side)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Brake caliper (loaded with pads)", "notes": "Confirm slide pins move freely before assuming the caliper piston is seized"},
            {"name": "Caliper slide pin rebuild kit", "notes": "Seized slide pins cause uneven pad wear and are often the real culprit"},
            {"name": "Brake hose (short flex hose at caliper)", "notes": "A collapsed inner liner can hold pressure and cause caliper drag"},
        ],
    },
    "abs_sensor_fault": {
        "label": "Faulty ABS wheel speed sensor or module (ABS warning light, pulsating pedal)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "ABS wheel speed sensor", "notes": "Confirm with a scan tool — C-code ABS fault will identify which wheel"},
            {"name": "Tone ring (reluctor ring)", "notes": "Damaged teeth on the tone ring read false signals — inspect when removing hub"},
        ],
    },
    "brake_line_hose": {
        "label": "Cracked or collapsed brake hose or corroded brake line (loss of pressure, soft pedal)",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Brake hose (flex hose at wheel)", "notes": "Inspect for cracks, swelling, or soft spots; collapsed inner liner won't be visible externally"},
            {"name": "Brake line repair kit", "notes": "Hard line corrosion is common in salt-belt vehicles; inspect all lines under the car"},
        ],
    },
    "brake_booster_master_cylinder": {
        "label": "Failing brake booster or master cylinder (hard pedal, sinking pedal, loss of assist)",
        "prior": 0.07,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Brake master cylinder", "notes": "A slow-sinking pedal under steady pressure with no external leak = internal bypass"},
            {"name": "Brake booster", "notes": "Hard stiff pedal with engine running = booster not receiving vacuum; check check valve first"},
        ],
    },
    "glazed_pads_rotors": {
        "label": "Glazed brake pads and rotors (reduced friction from overheating or improper bedding)",
        "prior": 0.05,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Brake pads", "notes": "Glazed pads have a shiny, hard surface — scuff lightly with 120-grit or replace"},
            {"name": "Brake rotors", "notes": "Heavily glazed rotors with a polished mirror surface should be replaced, not resurfaced"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tree nodes
# ─────────────────────────────────────────────────────────────────────────────

BRAKES_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary brake symptom?",
        "options": [
            {
                "match": "grinding",
                "label": "Grinding or metal-on-metal noise when braking",
                "deltas": {
                    "worn_brake_pads": +0.25,
                    "warped_rotors": +0.10,
                    "glazed_pads_rotors": -0.05,
                    "brake_booster_master_cylinder": -0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "squealing",
                "label": "High-pitched squeal or squeak when braking",
                "deltas": {
                    "worn_brake_pads": +0.20,
                    "glazed_pads_rotors": +0.10,
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "soft_spongy_pedal",
                "label": "Soft, spongy, or low brake pedal",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.20,
                    "brake_line_hose": +0.15,
                    "brake_booster_master_cylinder": +0.15,
                    "worn_brake_pads": -0.10,
                    "glazed_pads_rotors": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "pulling",
                "label": "Vehicle pulls to one side when braking",
                "deltas": {
                    "stuck_caliper": +0.30,
                    "warped_rotors": +0.10,
                    "brake_line_hose": +0.10,
                    "worn_brake_pads": -0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "warning_light",
                "label": "ABS or brake warning light on, no other symptom",
                "deltas": {
                    "abs_sensor_fault": +0.35,
                    "brake_fluid_low_contaminated": +0.15,
                    "worn_brake_pads": -0.10,
                    "warped_rotors": -0.10,
                    "glazed_pads_rotors": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the brake fluid reservoir (the small plastic reservoir near the firewall). What is the level and color?",
        "options": [
            {
                "match": "ok_clear",
                "label": "Full and light yellow or clear — looks clean",
                "deltas": {
                    "brake_fluid_low_contaminated": -0.20,
                    "brake_line_hose": -0.10,
                    "stuck_caliper": +0.05,
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": "pedal_depth",
            },
            {
                "match": "ok_dark",
                "label": "Full but dark brown or black — clearly degraded",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.30,
                    "brake_booster_master_cylinder": +0.10,
                },
                "eliminate": [],
                "next_node": "pedal_depth",
            },
            {
                "match": "level_low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.20,
                    "worn_brake_pads": +0.10,
                    "brake_line_hose": +0.15,
                },
                "eliminate": [],
                "next_node": "pedal_depth",
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": "pedal_depth",
            },
        ],
    },

    "pedal_depth": {
        "question": "With the engine running, describe how the brake pedal feels when you press it firmly.",
        "options": [
            {
                "match": "firm_normal",
                "label": "Firm — stops near the top of travel, normal feel",
                "deltas": {
                    "brake_fluid_low_contaminated": -0.15,
                    "brake_line_hose": -0.15,
                    "brake_booster_master_cylinder": -0.20,
                    "warped_rotors": +0.05,
                    "stuck_caliper": +0.05,
                },
                "eliminate": [],
                "next_node": "pad_age",
            },
            {
                "match": "soft_low",
                "label": "Soft or low — pedal goes closer to the floor than normal",
                "deltas": {
                    "brake_fluid_low_contaminated": +0.15,
                    "brake_line_hose": +0.15,
                    "brake_booster_master_cylinder": +0.10,
                },
                "eliminate": [],
                "next_node": "pad_age",
            },
            {
                "match": "sinks_slowly",
                "label": "Sinks — pedal holds initial pressure then slowly creeps to the floor",
                "deltas": {
                    "brake_booster_master_cylinder": +0.35,
                    "brake_fluid_low_contaminated": +0.05,
                },
                "eliminate": [],
                "next_node": "pad_age",
            },
            {
                "match": "hard_stiff",
                "label": "Hard or stiff — unusually difficult to press",
                "deltas": {
                    "brake_booster_master_cylinder": +0.40,
                    "brake_fluid_low_contaminated": -0.10,
                },
                "eliminate": [],
                "next_node": "pad_age",
            },
        ],
    },

    "pad_age": {
        "question": "Approximately when were the brake pads last replaced (or how many miles on the current pads)?",
        "options": [
            {
                "match": "recent_under_20k",
                "label": "Recently — under 20,000 miles ago",
                "deltas": {
                    "worn_brake_pads": -0.25,
                    "glazed_pads_rotors": +0.10,
                    "stuck_caliper": +0.05,
                    "abs_sensor_fault": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "moderate_20_50k",
                "label": "A while ago — around 20,000–50,000 miles ago",
                "deltas": {
                    "warped_rotors": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "old_over_50k",
                "label": "Long ago or never — over 50,000 miles or unknown",
                "deltas": {
                    "worn_brake_pads": +0.20,
                    "warped_rotors": +0.10,
                    "glazed_pads_rotors": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

BRAKES_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "worn_brake_pads": +0.10,
            "warped_rotors": +0.08,
            "stuck_caliper": +0.06,
            "brake_line_hose": +0.06,
        },
    },
    "usage_pattern": {
        "city": {
            "worn_brake_pads": +0.08,
            "warped_rotors": +0.06,
        },
    },
    "climate": {
        "cold": {
            "stuck_caliper": +0.08,
            "brake_line_hose": +0.06,
        },
    },
    "abs_light_on": {
        "yes": {
            "abs_sensor_fault": +0.25,
        },
    },
}

BRAKES_POST_DIAGNOSIS: list[str] = [
    "After any brake repair, bed the new pads by performing 6–8 moderate stops from 35 mph before making any hard stops — proper bedding prevents glazing and ensures even pad transfer to the rotors.",
    "Inspect the opposite side (other caliper or drum) when servicing one side — if one side failed, the other is usually close behind.",
    "If fluid was low with no obvious external leak, check for a worn rear drum cylinder or a caliper piston that's leaked past its dust boot.",
]
