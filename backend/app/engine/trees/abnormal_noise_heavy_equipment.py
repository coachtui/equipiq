"""
Abnormal noise diagnostic tree — heavy equipment (diesel).

Covers unusual sounds from diesel-powered construction equipment. Abnormal noise
on heavy equipment spans a wider range than passenger vehicles: turbo whine,
hydraulic pump cavitation, undercarriage clatter, and diesel knock all need to
be differentiated.

Noise location and character are the primary discriminators. Questions guide
operators through physical observations they can make safely from outside the machine.
"""

ABNORMAL_NOISE_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "turbo_bearing_failure": {
        "label": "Turbocharger bearing failure (whine, shriek, or grinding at speed)",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Turbocharger assembly", "notes": "Check oil supply line for restriction before installing new turbo — that's often what kills them"},
        ],
    },
    "engine_knock": {
        "label": "Engine knock or rod bearing knock (deep thudding under load)",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "hydraulic_cavitation": {
        "label": "Hydraulic pump cavitation (whine or growl when actuating controls)",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [],
    },
    "undercarriage_noise": {
        "label": "Undercarriage noise — worn rollers, idlers, drive sprocket, or loose track",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
    "exhaust_leak": {
        "label": "Exhaust manifold or pipe leak (hissing, ticking, or soot at joints)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Exhaust manifold gasket / V-band clamp", "notes": "Look for soot trails on the manifold or pipe joints as a guide"},
        ],
    },
    "cooling_fan_damage": {
        "label": "Cooling fan blade damage or fan clutch bearing (rhythmic thwap or vibration)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fan blade assembly or hydraulic fan motor", "notes": "Inspect fan blades for cracks or missing material — even small imbalance causes vibration"},
        ],
    },
    "loose_hardware": {
        "label": "Loose guard, cover, or external hardware vibrating",
        "prior": 0.13,
        "diy_difficulty": "easy",
        "parts": [],
    },
}

ABNORMAL_NOISE_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "Where does the noise seem to be coming from?",
        "options": [
            {
                "match": "engine_top_or_front",
                "label": "Engine area — top, front, or air intake / exhaust side",
                "deltas": {
                    "turbo_bearing_failure": +0.20,
                    "exhaust_leak": +0.15,
                    "engine_knock": +0.10,
                    "undercarriage_noise": -0.15,
                    "hydraulic_cavitation": -0.05,
                },
                "eliminate": ["undercarriage_noise"],
                "next_node": "noise_character",
            },
            {
                "match": "engine_bottom",
                "label": "Engine area — bottom or deep inside the engine",
                "deltas": {
                    "engine_knock": +0.30,
                    "turbo_bearing_failure": -0.10,
                    "exhaust_leak": -0.10,
                },
                "eliminate": ["undercarriage_noise", "cooling_fan_damage", "hydraulic_cavitation"],
                "next_node": "noise_character",
            },
            {
                "match": "undercarriage",
                "label": "Undercarriage — tracks, drive area, or wheel area",
                "deltas": {
                    "undercarriage_noise": +0.40,
                    "turbo_bearing_failure": -0.15,
                    "engine_knock": -0.10,
                    "hydraulic_cavitation": -0.10,
                },
                "eliminate": ["turbo_bearing_failure", "exhaust_leak"],
                "next_node": "noise_character",
            },
            {
                "match": "hydraulic_area",
                "label": "Hydraulic area — when moving controls, boom, or bucket",
                "deltas": {
                    "hydraulic_cavitation": +0.40,
                    "undercarriage_noise": -0.10,
                    "engine_knock": -0.10,
                },
                "eliminate": ["turbo_bearing_failure", "exhaust_leak", "engine_knock"],
                "next_node": "noise_character",
            },
            {
                "match": "general_or_unsure",
                "label": "General area / not sure where it's coming from",
                "deltas": {},
                "eliminate": [],
                "next_node": "noise_character",
            },
        ],
    },

    "noise_character": {
        "question": "How would you best describe the sound?",
        "options": [
            {
                "match": "high_pitched_whine_or_shriek",
                "label": "High-pitched whine, whistle, or shriek",
                "deltas": {
                    "turbo_bearing_failure": +0.30,
                    "hydraulic_cavitation": +0.15,
                    "engine_knock": -0.20,
                    "undercarriage_noise": -0.10,
                },
                "eliminate": ["engine_knock", "loose_hardware"],
                "next_node": "when_it_occurs",
            },
            {
                "match": "deep_knock_or_thud",
                "label": "Deep knock, thud, or rhythmic clank",
                "deltas": {
                    "engine_knock": +0.30,
                    "undercarriage_noise": +0.20,
                    "turbo_bearing_failure": -0.15,
                    "hydraulic_cavitation": -0.15,
                },
                "eliminate": ["exhaust_leak", "cooling_fan_damage"],
                "next_node": "when_it_occurs",
            },
            {
                "match": "hissing_or_ticking",
                "label": "Hissing, ticking, or faint spitting sound",
                "deltas": {
                    "exhaust_leak": +0.40,
                    "turbo_bearing_failure": +0.05,
                },
                "eliminate": ["engine_knock", "undercarriage_noise", "hydraulic_cavitation"],
                "next_node": "when_it_occurs",
            },
            {
                "match": "rattling_or_vibration",
                "label": "Rattling, clattering, or vibration noise",
                "deltas": {
                    "loose_hardware": +0.30,
                    "undercarriage_noise": +0.20,
                    "cooling_fan_damage": +0.15,
                },
                "eliminate": ["engine_knock", "turbo_bearing_failure"],
                "next_node": "when_it_occurs",
            },
            {
                "match": "growling_or_grinding",
                "label": "Growling or grinding sound",
                "deltas": {
                    "hydraulic_cavitation": +0.20,
                    "undercarriage_noise": +0.20,
                    "turbo_bearing_failure": +0.15,
                    "engine_knock": +0.10,
                },
                "eliminate": ["exhaust_leak", "loose_hardware"],
                "next_node": "when_it_occurs",
            },
        ],
    },

    "when_it_occurs": {
        "question": "When does the noise happen?",
        "options": [
            {
                "match": "always_at_idle",
                "label": "Constant — present even at idle",
                "deltas": {
                    "engine_knock": +0.15,
                    "exhaust_leak": +0.10,
                    "turbo_bearing_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "noise_getting_worse",
            },
            {
                "match": "under_load_or_rpm",
                "label": "Gets louder or only appears under load or at higher RPM",
                "deltas": {
                    "turbo_bearing_failure": +0.20,
                    "engine_knock": +0.15,
                    "hydraulic_cavitation": +0.10,
                },
                "eliminate": ["loose_hardware"],
                "next_node": "noise_getting_worse",
            },
            {
                "match": "when_operating_controls",
                "label": "Only when I move the hydraulic controls or levers",
                "deltas": {
                    "hydraulic_cavitation": +0.40,
                },
                "eliminate": ["engine_knock", "exhaust_leak", "turbo_bearing_failure", "loose_hardware"],
                "next_node": "noise_getting_worse",
            },
            {
                "match": "only_when_traveling",
                "label": "Only when the machine is moving / traveling",
                "deltas": {
                    "undercarriage_noise": +0.40,
                    "cooling_fan_damage": +0.10,
                },
                "eliminate": ["hydraulic_cavitation", "exhaust_leak"],
                "next_node": "noise_getting_worse",
            },
        ],
    },

    "noise_getting_worse": {
        "question": "Is the noise getting worse over time, or has it been constant since it first appeared?",
        "options": [
            {
                "match": "getting_worse",
                "label": "Getting progressively louder or more frequent",
                "deltas": {
                    "turbo_bearing_failure": +0.15,
                    "engine_knock": +0.15,
                    "undercarriage_noise": +0.10,
                    "loose_hardware": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "constant",
                "label": "Constant — hasn't changed since it started",
                "deltas": {
                    "exhaust_leak": +0.10,
                    "loose_hardware": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "started_recently",
                "label": "Just started recently — first noticed today or this week",
                "deltas": {
                    "loose_hardware": +0.10,
                    "turbo_bearing_failure": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ABNORMAL_NOISE_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"turbo_bearing_failure": +0.08, "hydraulic_cavitation": +0.05},
        "muddy": {"undercarriage_noise": +0.10},
        "marine": {},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "turbo_bearing_failure": +0.10,
            "undercarriage_noise": +0.10,
            "engine_knock": +0.05,
        },
    },
}

ABNORMAL_NOISE_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Turbo bearing noise (high-pitched whine at speed) is a stop-now condition — running a failing turbo pulls oil into the intake and can cause a runaway diesel.",
    "Hydraulic cavitation (whine when operating controls) usually means low fluid or a restricted suction line — check fluid level and suction strainer before replacing the pump.",
    "Exhaust leaks: look for soot streaks radiating outward from joints — this confirms the leak location even before you can hear it clearly.",
    "Engine knock that worsens under load with low oil pressure is a main bearing or rod bearing failure — shut down immediately and do not restart.",
]
