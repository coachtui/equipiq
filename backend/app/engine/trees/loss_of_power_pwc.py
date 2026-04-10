"""
Loss-of-power diagnostic tree — PWC (personal watercraft) variant.

Wear ring deterioration and impeller damage from debris ingestion are
the dominant PWC power-loss causes — completely unique to jet-pump
propulsion. These aren't present in any other vehicle tree.
Cavitation (air entering the jet pump intake) is another PWC-specific cause.
"""

LOSS_OF_POWER_PWC_HYPOTHESES: dict[str, dict] = {
    "wear_ring_worn": {
        "label": "Worn wear ring — gap between impeller and housing reduces thrust",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wear ring (match to impeller model)", "notes": "The plastic ring around the impeller — normal gap is under 1mm. A worn ring lets water slip past and dramatically reduces top speed. Inspect by looking down the pump nozzle."},
            {"name": "Impeller puller / installation tool", "notes": "Impeller must be removed to replace the wear ring — use the correct tool to avoid thread damage"},
        ],
    },
    "impeller_damage": {
        "label": "Damaged or wrapped impeller — struck rock, rope, or debris",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Impeller (OEM or aftermarket stainless)", "notes": "Inspect blades for chips, bends, or material wrapped around the shaft. A bent blade causes severe vibration in addition to power loss."},
            {"name": "Impeller shaft seal", "notes": "Replace the shaft seal whenever the impeller is removed — old seal allows water into the hull"},
        ],
    },
    "cavitation": {
        "label": "Cavitation — air entering the jet pump intake from a fouled hull or shallow water",
        "prior": 0.16,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Intake grate (OEM or aftermarket)", "notes": "A clogged or damaged intake grate causes cavitation — inspect and clean after every use in weeds or debris"},
            {"name": "Hull bottom inspection / cleaning", "notes": "Heavy marine growth on the hull bottom reduces flow into the intake; clean hull if in regular saltwater use"},
        ],
    },
    "fuel_delivery": {
        "label": "Fuel starvation — weak fuel pump, clogged filter, or vaporized fuel in heat",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel pump / fuel pump module", "notes": "Fuel pressure drop at wide-open throttle = failing fuel pump"},
            {"name": "Fuel filter", "notes": "Inline and in-tank filters — replace at the beginning of each season"},
        ],
    },
    "engine_power_loss": {
        "label": "Engine-side power loss — ignition, compression, or spark timing issue",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Spark plugs (OEM heat range)", "notes": "Check plugs for fouling or gap erosion — PWC engines are high-RPM and are sensitive to plug condition"},
            {"name": "Compression tester", "notes": "Low compression on one or more cylinders points to rings, valves, or head gasket"},
        ],
    },
    "intake_grate_clogged": {
        "label": "Intake grate clogged with weeds, rope, or debris",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Tilt the nose up, turn off the engine, and clear any weeds, rope, or debris from the intake grate. This is the first thing to check after any power loss in weedy water."},
        ],
    },
}

LOSS_OF_POWER_PWC_TREE: dict[str, dict] = {
    "start": {
        "question": "How does the power loss present — sudden loss of thrust, gradual, or RPMs climb but speed doesn't increase?",
        "options": [
            {
                "match": "rpm_no_speed",
                "label": "RPMs climb normally but speed doesn't increase — engine sounds strong",
                "deltas": {
                    "wear_ring_worn": +0.40,
                    "impeller_damage": +0.25,
                    "cavitation": +0.15,
                },
                "eliminate": ["fuel_delivery", "engine_power_loss"],
                "next_node": "debris_check",
            },
            {
                "match": "sudden_loss",
                "label": "Sudden loss of power — was running fine then dropped off sharply",
                "deltas": {
                    "impeller_damage": +0.30,
                    "intake_grate_clogged": +0.25,
                    "cavitation": +0.20,
                    "fuel_delivery": +0.10,
                },
                "eliminate": ["wear_ring_worn"],
                "next_node": "debris_check",
            },
            {
                "match": "gradual_loss",
                "label": "Gradual loss over the season — slower than last year",
                "deltas": {
                    "wear_ring_worn": +0.35,
                    "impeller_damage": +0.15,
                    "fuel_delivery": +0.15,
                    "engine_power_loss": +0.10,
                },
                "eliminate": ["intake_grate_clogged", "cavitation"],
                "next_node": "debris_check",
            },
            {
                "match": "low_speed_only",
                "label": "Fine at low speed but won't reach full speed / top end is gone",
                "deltas": {
                    "wear_ring_worn": +0.25,
                    "fuel_delivery": +0.25,
                    "engine_power_loss": +0.20,
                },
                "eliminate": ["intake_grate_clogged"],
                "next_node": "debris_check",
            },
        ],
    },

    "debris_check": {
        "question": "Has the intake grate been checked for weeds, rope, or debris?",
        "options": [
            {
                "match": "intake_clogged",
                "label": "Found weeds, rope, or debris in the intake grate",
                "deltas": {
                    "intake_grate_clogged": +0.70,
                    "cavitation": +0.15,
                },
                "eliminate": ["wear_ring_worn", "fuel_delivery", "engine_power_loss"],
                "next_node": None,
            },
            {
                "match": "intake_clear",
                "label": "Intake grate is clear",
                "deltas": {
                    "intake_grate_clogged": -0.15,
                    "wear_ring_worn": +0.10,
                    "impeller_damage": +0.08,
                },
                "eliminate": [],
                "next_node": "pump_check",
            },
        ],
    },

    "pump_check": {
        "question": "Has the jet pump been inspected — impeller blades and wear ring gap?",
        "options": [
            {
                "match": "impeller_damaged",
                "label": "Impeller has chipped blades, bent fins, or material wrapped around shaft",
                "deltas": {
                    "impeller_damage": +0.70,
                },
                "eliminate": ["wear_ring_worn", "cavitation", "fuel_delivery"],
                "next_node": None,
            },
            {
                "match": "wear_ring_gap",
                "label": "Wear ring gap visibly large — can fit a coin between impeller and ring",
                "deltas": {
                    "wear_ring_worn": +0.65,
                },
                "eliminate": ["impeller_damage", "cavitation"],
                "next_node": None,
            },
            {
                "match": "pump_looks_ok",
                "label": "Impeller and wear ring look good",
                "deltas": {
                    "wear_ring_worn": -0.15,
                    "impeller_damage": -0.15,
                    "fuel_delivery": +0.15,
                    "engine_power_loss": +0.12,
                    "cavitation": +0.10,
                },
                "eliminate": [],
                "next_node": "fuel_engine_check",
            },
            {
                "match": "not_inspected",
                "label": "Pump hasn't been inspected",
                "deltas": {
                    "wear_ring_worn": +0.10,
                    "impeller_damage": +0.08,
                },
                "eliminate": [],
                "next_node": "fuel_engine_check",
            },
        ],
    },

    "fuel_engine_check": {
        "question": "Is the fuel fresh and are spark plugs recently serviced?",
        "options": [
            {
                "match": "old_fuel_plugs",
                "label": "Old fuel and/or plugs not recently changed",
                "deltas": {
                    "fuel_delivery": +0.20,
                    "engine_power_loss": +0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "fresh_maintained",
                "label": "Fresh fuel and plugs recently serviced",
                "deltas": {
                    "fuel_delivery": -0.10,
                    "engine_power_loss": +0.08,
                    "wear_ring_worn": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_PWC_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"wear_ring_worn": +0.08, "intake_grate_clogged": +0.06, "impeller_damage": +0.06},
    },
    "mileage_band": {
        "high": {"wear_ring_worn": +0.12, "impeller_damage": +0.08, "engine_power_loss": +0.06},
    },
    "storage_time": {
        "months": {"fuel_delivery": +0.10},
        "season": {"fuel_delivery": +0.12, "engine_power_loss": +0.06},
    },
    "first_start_of_season": {
        "yes": {"fuel_delivery": +0.08, "intake_grate_clogged": +0.05},
    },
    "climate": {
        "hot": {"fuel_delivery": +0.06, "cavitation": +0.05},
    },
}

LOSS_OF_POWER_PWC_POST_DIAGNOSIS: list[str] = [
    "After impeller or wear ring replacement, do a WOT (wide-open throttle) pass in open water and note the top speed — compare to manufacturer spec to confirm the pump is delivering full thrust.",
    "Inspect the pump tunnel and intake for erosion or cracks after any impeller impact — even minor cavitation damage can grow into a hull breach.",
]
