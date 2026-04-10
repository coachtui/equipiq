"""
Transmission diagnostic tree — motorcycle variant.

Key differences from base car tree:
- Wet clutch (bathed in engine oil) is the dominant design — clutch plates, fiber
  plates, and clutch springs live inside the crankcase
- Sequential gearbox: rider can only shift one gear at a time, up or down; false
  neutral between gears is common on worn transmissions
- No torque converter, no solenoids, no ATF — the car transmission tree does not apply
- Clutch cable (or hydraulic actuator on modern bikes) is a primary failure point
- Primary drive chain (inside the primary cover) connects crank to clutch basket
- Some bikes have a wet slipper clutch (anti-hop clutch for downshifts)
- Shaft-drive bikes have a final drive gear/universal joint, not a chain
"""

TRANSMISSION_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "clutch_worn": {
        "label": "Worn clutch plates (slipping — engine revs but bike doesn't accelerate)",
        "prior": 0.28,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Clutch fiber plates (full set)", "notes": "Measure thickness — replace the full set when any plate is at or below the wear limit; mix of old and new plates causes uneven engagement"},
            {"name": "Clutch springs", "notes": "Weak springs are the most common cause of slip on high-mileage bikes; measure free length and compare to spec"},
        ],
    },
    "clutch_cable_or_actuator": {
        "label": "Stretched, frayed, or misadjusted clutch cable, or worn hydraulic clutch actuator",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Clutch cable", "notes": "Inspect for fraying at lever end and at the actuator arm — lubricate before replacing if cable is intact; kinks near the lever are the most common failure point"},
            {"name": "Clutch master cylinder / slave cylinder rebuild kit", "notes": "Hydraulic clutch — leaking or spongy lever indicates blown seal; rebuild before replacing the whole assembly"},
        ],
    },
    "false_neutral_or_hard_shift": {
        "label": "False neutral between gears, hard to find a gear, or gear pops out under load",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Shift fork and shift drum inspection", "notes": "False neutrals are caused by worn shift fork dogs or a worn shift drum — requires engine split on most bikes; confirm by checking gear engagement under light load"},
            {"name": "Transmission oil change (correct spec)", "notes": "Some false-neutral complaints resolve with fresh oil — try this first before engine teardown"},
        ],
    },
    "primary_drive_chain": {
        "label": "Worn or loose primary chain (clunking or rattling from the primary cover side)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Primary chain and tensioner", "notes": "Primary chain stretch causes a heavy clunk on engagement and at idle; check tensioner adjustment range before replacing both"},
        ],
    },
    "oil_viscosity_spec": {
        "label": "Wrong or degraded engine oil affecting wet clutch (slipping, dragging, or erratic engagement)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Motorcycle-specific engine oil (JASO MA or MA2 rated)", "notes": "Do NOT use car oil with friction modifiers (API SL/SM 'Energy Conserving') in a wet clutch — it causes slip; always use JASO MA/MA2 spec motorcycle oil"},
        ],
    },
    "shaft_drive_fault": {
        "label": "Final drive shaft or universal joint fault (clunk on acceleration/deceleration, shaft-drive bikes only)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Rear drive shaft / universal joint", "notes": "Check bevel gear lash and U-joint play before condemning the shaft — final drive oil level is a separate check from engine oil"},
            {"name": "Final drive oil (gear oil for rear bevel drive)", "notes": "Separate fill port on shaft-drive bikes — often overlooked; low level causes gear whine and premature wear"},
        ],
    },
    "clutch_basket_worn": {
        "label": "Notched clutch basket (jerky engagement, chattering on takeoff)",
        "prior": 0.04,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Clutch basket", "notes": "Tabs on the basket develop notches from the clutch plates — filing notches is a temporary fix; replace on high-mileage engines that have had repeated clutch work"},
        ],
    },
}

TRANSMISSION_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "What does the motorcycle transmission/clutch do that seems wrong?",
        "options": [
            {
                "match": "slipping",
                "label": "Clutch slipping — engine revs rise but bike doesn't accelerate proportionally",
                "deltas": {
                    "clutch_worn": +0.35,
                    "oil_viscosity_spec": +0.15,
                    "clutch_cable_or_actuator": +0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "hard_lever",
                "label": "Clutch lever is very hard to pull, stiff, or inconsistent",
                "deltas": {
                    "clutch_cable_or_actuator": +0.50,
                    "clutch_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "false_neutral",
                "label": "Drops into false neutral, hard to find gear, or pops out of gear under load",
                "deltas": {
                    "false_neutral_or_hard_shift": +0.55,
                    "oil_viscosity_spec": +0.08,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "clunking_noise",
                "label": "Clunking or rattling noise from the left engine cover or drivetrain area",
                "deltas": {
                    "primary_drive_chain": +0.35,
                    "shaft_drive_fault": +0.15,
                    "clutch_basket_worn": +0.15,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "chattering",
                "label": "Clutch chatters or shudders on takeoff",
                "deltas": {
                    "clutch_basket_worn": +0.30,
                    "clutch_worn": +0.20,
                    "oil_viscosity_spec": +0.20,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "When was the engine oil last changed, and what brand/spec was used?",
        "options": [
            {
                "match": "recent_correct",
                "label": "Recent change with motorcycle-specific JASO MA/MA2 oil",
                "deltas": {
                    "oil_viscosity_spec": -0.20,
                    "clutch_worn": +0.08,
                    "false_neutral_or_hard_shift": +0.05,
                },
                "eliminate": [],
                "next_node": "cable_check",
            },
            {
                "match": "overdue_or_unknown",
                "label": "Overdue for a change or not sure",
                "deltas": {
                    "oil_viscosity_spec": +0.15,
                    "clutch_worn": +0.08,
                    "clutch_cable_or_actuator": +0.05,
                },
                "eliminate": [],
                "next_node": "cable_check",
            },
            {
                "match": "car_oil",
                "label": "Car oil was used (not motorcycle-specific) or unsure of the spec",
                "deltas": {
                    "oil_viscosity_spec": +0.40,
                    "clutch_worn": +0.05,
                },
                "eliminate": [],
                "next_node": "cable_check",
            },
        ],
    },

    "cable_check": {
        "question": "Inspect the clutch cable or hydraulic line at the lever. What do you find?",
        "options": [
            {
                "match": "cable_ok",
                "label": "Cable looks intact — no visible fraying, kinks, or leaks",
                "deltas": {
                    "clutch_cable_or_actuator": -0.20,
                    "clutch_worn": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cable_frayed_kinked",
                "label": "Cable is frayed, kinked, or hard to move in the housing",
                "deltas": {
                    "clutch_cable_or_actuator": +0.45,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "hydraulic_spongy",
                "label": "Hydraulic clutch — lever feels spongy or has a leak at the master/slave",
                "deltas": {
                    "clutch_cable_or_actuator": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "clutch_worn": +0.12,
            "false_neutral_or_hard_shift": +0.10,
            "primary_drive_chain": +0.08,
            "clutch_basket_worn": +0.08,
        },
    },
    "storage_time": {
        "long": {
            "clutch_cable_or_actuator": +0.12,
            "oil_viscosity_spec": +0.08,
        },
    },
}

TRANSMISSION_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After replacing clutch plates on a wet clutch, soak new fiber plates in clean engine oil for 30 minutes before installation — dry plates bite hard and can cause the first few engagements to be jerky.",
    "Always change the engine oil after a clutch plate replacement — metal debris from worn plates contaminates the oil, and running that through the transmission accelerates wear on gears and bearings.",
    "If false neutrals were found, check the shift lever position and stopper arm spring before splitting the engine — a bent shift lever or weak stopper spring causes missed shifts that feel like internal transmission faults.",
]
