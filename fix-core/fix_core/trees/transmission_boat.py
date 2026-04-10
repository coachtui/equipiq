"""
Transmission diagnostic tree — boat/marine variant.

Key differences from base car tree:
- Stern drive (outdrive) and inboard boats use a marine reverse gear (transmission)
  — Velvet Drive, Borg Warner, ZF are the dominant units
- Outboard motors have no conventional transmission — forward/neutral/reverse is
  handled by the gearcases's shift mechanism (lower unit); outboard issues belong
  in engine trees or a separate lower unit category
- Key failure modes: shift cable out of adjustment, fluid spec failure, hard shifts,
  no forward or no reverse
- The transmission is filled with ATF (usually Dexron III or as specified on tag)
- Overheating from inadequate raw water cooling of the transmission cooler is a
  real failure mode in inboard/stern drive boats
"""

TRANSMISSION_BOAT_HYPOTHESES: dict[str, dict] = {
    "shift_cable_adjustment": {
        "label": "Shift cable stretched, misadjusted, or kinked (no neutral, hard to shift, grinding on engagement)",
        "prior": 0.30,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine shift cable (correct length for vessel)", "notes": "Cable length and routing are boat-specific — measure the existing cable run before ordering; adjust at the transmission end first before replacing"},
        ],
    },
    "fluid_low_degraded": {
        "label": "Low or degraded transmission fluid (Velvet Drive/ZF — uses ATF, not gear oil)",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "ATF (check transmission tag — Dexron III or Dexron VI)", "notes": "Marine transmissions use ATF, not gear oil — confirm spec on the transmission data plate; overfilling causes foaming and slip"},
        ],
    },
    "coupler_or_damper_plate": {
        "label": "Worn flex coupler or damper plate (clunking on engagement, vibration when in gear)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Shaft coupler / flex disc", "notes": "Rubber elements in the coupler absorb shock from engagement and propeller impact — cracking or chunk loss causes a hard clunk on every gear change"},
        ],
    },
    "hard_shift_valve_body": {
        "label": "Hard or abrupt shift engagement (valve body or internal clutch pack fault)",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission service / valve body inspection", "notes": "Velvet Drive and ZF units can have stuck servo valves — a fluid and filter service first; if still harsh, valve body inspection is next"},
        ],
    },
    "no_forward_no_reverse": {
        "label": "No forward or no reverse — other direction works (clutch pack or shift valve stuck)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Transmission rebuild kit", "notes": "Velvet Drive and ZF units are well-supported for rebuild — confirm unit model number from the data plate before ordering"},
        ],
    },
    "cooler_blocked": {
        "label": "Transmission overheating (raw water cooler blocked, thermostat stuck — inboard/stern drive)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Transmission cooler (heat exchanger)", "notes": "Marine transmission coolers are cooled by raw water from the engine's raw water circuit; blocked cooler causes thermal slip and fluid breakdown"},
            {"name": "Raw water impeller", "notes": "If the impeller failed, the whole raw water circuit is starved — check engine temp at the same time"},
        ],
    },
}

TRANSMISSION_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the boat transmission/drive unit do that seems wrong?",
        "options": [
            {
                "match": "no_shift",
                "label": "Hard to shift, won't go into gear, or grinds when engaging forward or reverse",
                "deltas": {
                    "shift_cable_adjustment": +0.45,
                    "fluid_low_degraded": +0.10,
                },
                "eliminate": [],
                "next_node": "outboard_check",
            },
            {
                "match": "no_forward",
                "label": "No forward or no reverse — one direction works, the other doesn't",
                "deltas": {
                    "no_forward_no_reverse": +0.35,
                    "shift_cable_adjustment": +0.25,
                    "fluid_low_degraded": +0.10,
                },
                "eliminate": [],
                "next_node": "outboard_check",
            },
            {
                "match": "clunk_vibration",
                "label": "Clunking or thud on engagement, or vibration when in gear",
                "deltas": {
                    "coupler_or_damper_plate": +0.45,
                    "shift_cable_adjustment": +0.15,
                },
                "eliminate": [],
                "next_node": "outboard_check",
            },
            {
                "match": "slipping",
                "label": "Slipping — engine revs but boat moves slower than expected",
                "deltas": {
                    "fluid_low_degraded": +0.30,
                    "no_forward_no_reverse": +0.15,
                    "cooler_blocked": +0.10,
                },
                "eliminate": [],
                "next_node": "outboard_check",
            },
        ],
    },

    "outboard_check": {
        "question": "What type of propulsion does this boat use?",
        "options": [
            {
                "match": "inboard_sterndr",
                "label": "Inboard or stern drive (engine inside hull — MerCruiser, Volvo Penta, etc.)",
                "deltas": {
                    "cooler_blocked": +0.08,
                    "coupler_or_damper_plate": +0.05,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
            {
                "match": "outboard",
                "label": "Outboard motor (engine hangs on transom)",
                "deltas": {
                    "shift_cable_adjustment": +0.15,
                    "cooler_blocked": -0.15,
                    "hard_shift_valve_body": -0.20,
                    "no_forward_no_reverse": -0.10,
                },
                "eliminate": [],
                "next_node": "fluid_check",
            },
        ],
    },

    "fluid_check": {
        "question": "Check the transmission fluid dipstick (inboard/stern drive — on the top of the transmission). What is the level and condition?",
        "options": [
            {
                "match": "ok_clean",
                "label": "Full and clean — red/pink with no metal particles",
                "deltas": {
                    "fluid_low_degraded": -0.25,
                    "shift_cable_adjustment": +0.10,
                    "coupler_or_damper_plate": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "dark_metallic",
                "label": "Dark brown, black, or has metallic sheen",
                "deltas": {
                    "fluid_low_degraded": +0.30,
                    "no_forward_no_reverse": +0.10,
                    "hard_shift_valve_body": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "low",
                "label": "Low — below the MIN mark",
                "deltas": {
                    "fluid_low_degraded": +0.35,
                    "cooler_blocked": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "outboard_no_dipstick",
                "label": "Outboard — no transmission dipstick",
                "deltas": {
                    "shift_cable_adjustment": +0.15,
                    "fluid_low_degraded": -0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_BOAT_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "fluid_low_degraded": +0.10,
            "coupler_or_damper_plate": +0.10,
            "no_forward_no_reverse": +0.08,
        },
    },
    "saltwater_use": {
        "yes": {
            "cooler_blocked": +0.10,
            "shift_cable_adjustment": +0.08,
        },
    },
    "storage_time": {
        "long": {
            "shift_cable_adjustment": +0.10,
            "fluid_low_degraded": +0.08,
        },
    },
}

TRANSMISSION_BOAT_POST_DIAGNOSIS: list[str] = [
    "When adjusting a marine shift cable, always verify neutral at the transmission end — engine must be able to crank and run in neutral without propeller movement; test before putting back in the water.",
    "Marine transmission fluid (ATF in Velvet Drive / ZF units) should be changed every 100 engine hours or annually — metallic contamination from clutch pack wear accumulates fast in a small fluid volume.",
    "If an outboard motor lower unit won't shift or grinds into gear, check the shift rod detent and shift shaft seal inside the lower unit — this is separate from the shift cable and requires lower unit removal to inspect.",
]
