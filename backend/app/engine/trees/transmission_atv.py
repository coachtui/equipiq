"""
Transmission diagnostic tree — ATV/UTV variant.

Key differences from base car tree:
- CVT (continuously variable transmission) is the dominant design on ATVs and UTVs
  — belt-driven with a drive clutch (variator) and driven clutch
- CVT belt slip and wear is the #1 transmission complaint on ATVs/UTVs
- Manual gear range selector (H/L/R/N/P) controls range, not shift quality
- Wet clutch designs exist on some models (manual ATVs, sport quads)
- Mud, water, and debris ingestion into the CVT housing is a primary failure mode
- Electric power steering on modern UTVs is separate from the transmission
"""

TRANSMISSION_ATV_HYPOTHESES: dict[str, dict] = {
    "cvt_belt_worn": {
        "label": "Worn, slipping, or broken CVT belt (most common ATV/UTV transmission failure)",
        "prior": 0.35,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "OEM CVT drive belt (year/make/model specific)", "notes": "Always use OEM or OEM-spec belt — off-brand belts slip earlier and can shred inside the CVT housing, causing secondary damage"},
            {"name": "CVT housing gasket / seal kit", "notes": "Inspect the housing for belt debris and clean thoroughly before installing a new belt"},
        ],
    },
    "cvt_clutch_worn": {
        "label": "Worn drive clutch (variator) or driven clutch rollers/weights (poor engagement, sluggish acceleration)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CVT drive clutch rollers / weights (rebuild kit)", "notes": "Worn rollers cause sluggish engagement and reduced top speed — clean sheaves thoroughly before installing new rollers"},
            {"name": "Driven clutch spring", "notes": "Weak spring causes belt to ride too high in the driven clutch — results in sluggish take-off and belt wear"},
        ],
    },
    "range_selector_fault": {
        "label": "Range selector (H/L/R/N/P) not engaging, stuck, or jumping out of range under load",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Range selector linkage / detent ball and spring", "notes": "Worn detent allows range to pop out under hard acceleration — inspect shift linkage first before internal teardown"},
            {"name": "Shift shaft seal", "notes": "Leaking seal allows water to enter the gearbox around the range selector"},
        ],
    },
    "mud_water_ingestion": {
        "label": "Mud or water ingestion into CVT housing (burning belt smell, squealing, total loss of drive)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CVT belt (replacement after ingestion)", "notes": "Water or mud in the CVT housing glazes and destroys the belt rapidly — inspect drive and driven clutch faces for glazing too"},
            {"name": "CVT intake snorkel extension", "notes": "Raise the CVT air intake for improved water crossing clearance — common mod for trail riding ATVs"},
        ],
    },
    "wet_clutch_worn": {
        "label": "Wet clutch slip or drag — manual-shift sport ATVs and some utility quads",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Clutch fiber plates and springs", "notes": "Manual ATV wet clutch is identical in concept to a motorcycle clutch — measure plate thickness before ordering; use JASO MA-rated oil"},
        ],
    },
    "fluid_low_degraded": {
        "label": "Low or degraded gear oil in the final drive or angle gear (grinding, whine)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Gear oil (75W-90 or manufacturer spec)", "notes": "ATVs have a separate gear oil fill for the front differential, rear differential, and sometimes the angle gear — check all three fill ports"},
        ],
    },
}

TRANSMISSION_ATV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary transmission symptom on the ATV/UTV?",
        "options": [
            {
                "match": "no_drive",
                "label": "No drive — engine runs but machine doesn't move, or belt broke",
                "deltas": {
                    "cvt_belt_worn": +0.50,
                    "mud_water_ingestion": +0.15,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "slipping",
                "label": "Slipping — engine revs up but machine moves slowly, especially under load",
                "deltas": {
                    "cvt_belt_worn": +0.30,
                    "cvt_clutch_worn": +0.20,
                    "mud_water_ingestion": +0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "burning_smell",
                "label": "Burning rubber or burning smell from the CVT area",
                "deltas": {
                    "cvt_belt_worn": +0.35,
                    "mud_water_ingestion": +0.30,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "wont_engage_range",
                "label": "Won't go into High, Low, Reverse, or Range pops out under load",
                "deltas": {
                    "range_selector_fault": +0.55,
                    "fluid_low_degraded": +0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
            {
                "match": "sluggish_acceleration",
                "label": "Sluggish or delayed acceleration — slower than normal from a stop",
                "deltas": {
                    "cvt_clutch_worn": +0.30,
                    "cvt_belt_worn": +0.20,
                    "mud_water_ingestion": +0.10,
                },
                "eliminate": [],
                "next_node": "cvt_check",
            },
        ],
    },

    "cvt_check": {
        "question": "Was the ATV/UTV ridden through deep mud, water crossings, or heavy rain before the symptom started?",
        "options": [
            {
                "match": "yes_mud_water",
                "label": "Yes — deep mud or water crossing just before the problem",
                "deltas": {
                    "mud_water_ingestion": +0.40,
                    "cvt_belt_worn": +0.15,
                },
                "eliminate": [],
                "next_node": "belt_mileage",
            },
            {
                "match": "no_dry",
                "label": "No — dry conditions or normal use",
                "deltas": {
                    "cvt_belt_worn": +0.10,
                    "cvt_clutch_worn": +0.08,
                    "mud_water_ingestion": -0.15,
                },
                "eliminate": [],
                "next_node": "belt_mileage",
            },
        ],
    },

    "belt_mileage": {
        "question": "Do you know when the CVT belt was last replaced?",
        "options": [
            {
                "match": "recent",
                "label": "Recently replaced (within last season or known low mileage)",
                "deltas": {
                    "cvt_belt_worn": -0.15,
                    "cvt_clutch_worn": +0.15,
                    "range_selector_fault": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "overdue_unknown",
                "label": "Never replaced, overdue, or don't know",
                "deltas": {
                    "cvt_belt_worn": +0.20,
                    "cvt_clutch_worn": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

TRANSMISSION_ATV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "cvt_belt_worn": +0.12,
            "cvt_clutch_worn": +0.10,
            "fluid_low_degraded": +0.08,
        },
    },
    "storage_time": {
        "long": {
            "cvt_belt_worn": +0.08,
            "fluid_low_degraded": +0.08,
        },
    },
    "saltwater_use": {
        "yes": {
            "fluid_low_degraded": +0.10,
            "mud_water_ingestion": +0.08,
        },
    },
    "transmission_type": {
        "cvt": {
            "cvt_belt_worn": +0.10,
            "cvt_clutch_worn": +0.08,
            "wet_clutch_worn": -0.10,
        },
        "manual": {
            "wet_clutch_worn": +0.20,
            "cvt_belt_worn": -0.20,
            "cvt_clutch_worn": -0.15,
        },
    },
}

TRANSMISSION_ATV_POST_DIAGNOSIS: list[str] = [
    "After a water or mud ingestion event, open and clean the entire CVT housing before installing a new belt — belt debris and clay residue on the clutch sheave faces will destroy a new belt within miles.",
    "CVT belt replacement intervals vary widely by manufacturer — check your owner's manual; many manufacturers recommend inspection every 500–1000 miles and replacement at first signs of edge cracking or glazing.",
    "Never run an ATV/UTV CVT with the housing cover cracked open or removed — belt debris becomes a projectile hazard and the belt will cool improperly, accelerating fatigue cracking.",
]
