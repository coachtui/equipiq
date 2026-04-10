"""
Cab electrical diagnostic tree — heavy equipment.

Covers electrical faults specific to the operator cab and cab systems:
- HVAC / air conditioning failure
- Instrument cluster / gauge failures
- Lighting faults (work lights, cab lights)
- Wiper / defroster failure
- Cab pressurizer failure (on enclosed cabs in dusty environments)
- Radio / display / telematics module issues

This is separate from the main electrical_fault tree which covers the charging
system, battery, and machine-critical electrical systems. Cab electrical faults
rarely prevent machine operation but significantly affect operator safety and
comfort on long shifts.
"""

CAB_ELECTRICAL_HEAVY_EQUIPMENT_HYPOTHESES: dict[str, dict] = {
    "ac_compressor_or_refrigerant": {
        "label": "AC compressor failure or refrigerant loss — no cooling",
        "prior": 0.22,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "AC compressor", "notes": "Test compressor clutch engagement before condemning compressor — may just be a clutch gap or fuse"},
            {"name": "Refrigerant (R-134a or R-1234yf per cab specs)", "notes": "Refrigerant recharge requires certified technician and recovery equipment"},
        ],
    },
    "cab_fuse_or_relay": {
        "label": "Blown fuse or failed relay in cab circuit",
        "prior": 0.25,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuse assortment (match amperage exactly)", "notes": "Check the cab fuse panel — usually located behind a panel near the operator seat or on the cab pillar"},
        ],
    },
    "gauge_cluster_fault": {
        "label": "Instrument cluster or gauge failure (single gauge or whole cluster dead)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Instrument cluster / gauge pod", "notes": "Check sender units and wiring harness to cluster before replacing cluster itself"},
        ],
    },
    "blower_motor": {
        "label": "Cab blower motor failure — no airflow or airflow only on some speeds",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Blower motor", "notes": "Check blower motor resistor first if only some speed settings are dead"},
            {"name": "Blower motor resistor", "notes": "Common failure — causes loss of lower speed settings"},
        ],
    },
    "work_light_failure": {
        "label": "Work light(s) failed — bulb, LED driver, or wiring fault",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Work light assembly or LED module", "notes": "LED work lights often fail as a module; halogen bulbs are easily replaced individually"},
        ],
    },
    "cab_pressurizer": {
        "label": "Cab pressurizer fan or filter failure — dust entering cab",
        "prior": 0.08,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Cab pressurizer filter", "notes": "Most common issue — replace filter before suspecting the fan motor"},
            {"name": "Cab pressurizer fan motor", "notes": "Test motor with direct 12V/24V before replacing"},
        ],
    },
    "wiper_or_defroster": {
        "label": "Wiper motor, washer pump, or rear defroster failure",
        "prior": 0.09,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wiper motor", "notes": "Check fuse first; also check for bent wiper linkage binding the motor"},
        ],
    },
}

CAB_ELECTRICAL_HEAVY_EQUIPMENT_TREE: dict[str, dict] = {
    "start": {
        "question": "Which cab system is having the problem?",
        "options": [
            {
                "match": "no_ac_or_heat",
                "label": "Air conditioning or heating — not cooling / not heating",
                "deltas": {
                    "ac_compressor_or_refrigerant": +0.25,
                    "blower_motor": +0.15,
                    "cab_fuse_or_relay": +0.15,
                    "work_light_failure": -0.10,
                    "wiper_or_defroster": -0.10,
                },
                "eliminate": ["work_light_failure", "cab_pressurizer"],
                "next_node": "fuse_check",
            },
            {
                "match": "gauges_dead",
                "label": "Instrument cluster / gauges — one or more not working",
                "deltas": {
                    "gauge_cluster_fault": +0.35,
                    "cab_fuse_or_relay": +0.20,
                    "ac_compressor_or_refrigerant": -0.15,
                    "work_light_failure": -0.15,
                },
                "eliminate": ["ac_compressor_or_refrigerant", "blower_motor", "work_light_failure", "cab_pressurizer", "wiper_or_defroster"],
                "next_node": "fuse_check",
            },
            {
                "match": "lights_out",
                "label": "Work lights or cab lights not working",
                "deltas": {
                    "work_light_failure": +0.35,
                    "cab_fuse_or_relay": +0.20,
                    "gauge_cluster_fault": -0.15,
                },
                "eliminate": ["ac_compressor_or_refrigerant", "blower_motor", "gauge_cluster_fault", "cab_pressurizer", "wiper_or_defroster"],
                "next_node": "fuse_check",
            },
            {
                "match": "dust_in_cab",
                "label": "Excessive dust entering the cab (pressurizer not working)",
                "deltas": {
                    "cab_pressurizer": +0.45,
                    "cab_fuse_or_relay": +0.10,
                },
                "eliminate": ["ac_compressor_or_refrigerant", "gauge_cluster_fault", "work_light_failure", "wiper_or_defroster"],
                "next_node": "fuse_check",
            },
            {
                "match": "wipers_or_washers",
                "label": "Wipers or washers not working",
                "deltas": {
                    "wiper_or_defroster": +0.35,
                    "cab_fuse_or_relay": +0.25,
                },
                "eliminate": ["ac_compressor_or_refrigerant", "gauge_cluster_fault", "cab_pressurizer"],
                "next_node": "fuse_check",
            },
        ],
    },

    "fuse_check": {
        "question": "Have you checked the fuse panel for the affected cab circuit? Is there a blown fuse or a fuse that looks dark/burnt?",
        "options": [
            {
                "match": "blown_fuse_found",
                "label": "Yes — found a blown fuse for that circuit",
                "deltas": {
                    "cab_fuse_or_relay": +0.45,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "fuses_all_ok",
                "label": "Checked — all fuses for that circuit look fine",
                "deltas": {
                    "cab_fuse_or_relay": -0.15,
                    "ac_compressor_or_refrigerant": +0.10,
                    "blower_motor": +0.05,
                    "gauge_cluster_fault": +0.05,
                    "work_light_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "onset",
            },
            {
                "match": "fuse_panel_not_checked",
                "label": "Haven't checked the fuse panel yet",
                "deltas": {
                    "cab_fuse_or_relay": +0.10,
                },
                "eliminate": [],
                "next_node": "onset",
            },
        ],
    },

    "onset": {
        "question": "Did the problem start suddenly, or did it come on gradually?",
        "options": [
            {
                "match": "sudden",
                "label": "Sudden — was working, then stopped",
                "deltas": {
                    "cab_fuse_or_relay": +0.15,
                    "work_light_failure": +0.08,
                    "ac_compressor_or_refrigerant": +0.05,
                },
                "eliminate": [],
                "next_node": "environment_context",
            },
            {
                "match": "gradual",
                "label": "Gradual — performance declined over time",
                "deltas": {
                    "ac_compressor_or_refrigerant": +0.15,
                    "blower_motor": +0.10,
                    "cab_pressurizer": +0.08,
                },
                "eliminate": [],
                "next_node": "environment_context",
            },
        ],
    },

    "environment_context": {
        "question": "What environment has the machine been working in recently?",
        "options": [
            {
                "match": "high_dust",
                "label": "Very dusty — demolition, quarry, dry earthmoving",
                "deltas": {
                    "cab_pressurizer": +0.15,
                    "blower_motor": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "wet_or_humid",
                "label": "Wet or humid — marine, near water, rain",
                "deltas": {
                    "gauge_cluster_fault": +0.08,
                    "cab_fuse_or_relay": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "normal_conditions",
                "label": "Normal conditions",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CAB_ELECTRICAL_HEAVY_EQUIPMENT_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"cab_pressurizer": +0.12, "blower_motor": +0.05},
        "muddy": {"wiper_or_defroster": +0.05},
        "marine": {"gauge_cluster_fault": +0.08, "cab_fuse_or_relay": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "cab_pressurizer": +0.08,
            "blower_motor": +0.05,
        },
        "long_storage": {
            "ac_compressor_or_refrigerant": +0.10,
        },
    },
}

CAB_ELECTRICAL_HEAVY_EQUIPMENT_POST_DIAGNOSIS: list[str] = [
    "Cab pressurizer filters should be cleaned or replaced every 250–500 hours in dusty environments — this is the most commonly neglected consumable on enclosed-cab machines.",
    "AC clutch test: with engine running and AC on, look at the AC compressor — the center hub should be spinning with the belt. If only the outer pulley spins and the center is still, the clutch has failed.",
    "Blower motor resistor failure: if the blower only works on the highest speed setting, the resistor is the most likely cause. Resistors are inexpensive and easy to replace.",
    "Work light LED modules: unlike halogen bulbs, LED light bars fail as a complete module. Check the connector and wiring harness voltage before ordering a replacement module.",
]
