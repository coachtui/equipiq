"""
Loss of power diagnostic tree — truck/diesel variant.

Diesel truck power loss has unique causes not seen in gas vehicles:
DPF regeneration interference, turbo failures (single or compound),
intercooler boost leaks, EGR clogging, and injection pump wear. Also covers
'limp mode' — when the ECU deliberately limits power to protect the drivetrain.
"""

LOSS_OF_POWER_TRUCK_HYPOTHESES: dict[str, dict] = {
    "dpf_clog": {
        "label": "Clogged diesel particulate filter (DPF) — ECU derate / regeneration needed",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "DPF professional cleaning or replacement", "notes": "If the truck hasn't completed a successful regen cycle recently (lots of short trips, idle time), the DPF fills with soot. Force a regen via scan tool or highway driving at 65+ mph for 30–40 min."},
        ],
    },
    "turbo_boost_leak": {
        "label": "Boost leak — cracked intercooler pipe, loose clamp, or failed boost hose",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Intercooler boost pipe (cracked section)", "notes": "Pressurize the intake system and listen for hissing; the cracked section expands under boost and deflates at idle — hard to find without pressure test"},
            {"name": "Silicone hose clamps and couplers", "notes": "Inspect all rubber boots and clamps at the turbo inlet, intercooler, and throttle body — any loose connection loses boost"},
        ],
    },
    "turbo_failure": {
        "label": "Failed or worn turbocharger — reduced boost pressure",
        "prior": 0.14,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Turbocharger assembly", "notes": "Check for shaft play (grab the shaft through the compressor inlet — should have no radial play). Also look for blue smoke indicating oil burning."},
            {"name": "Oil feed and drain lines to turbo", "notes": "Blocked oil feed is a common cause of turbo failure — inspect before replacement"},
        ],
    },
    "egr_clogged": {
        "label": "EGR system clogged with carbon — restricting intake and reducing combustion efficiency",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "EGR valve", "notes": "Heavy carbon buildup on diesel EGR valves is common — cleaning with carbon remover is a good first step"},
            {"name": "EGR cooler", "notes": "A clogged EGR cooler restricts airflow; cleaning or replacement restores proper function"},
            {"name": "Intake manifold cleaning", "notes": "Carbon buildup in the intake passages reduces effective displacement"},
        ],
    },
    "fuel_restriction": {
        "label": "Fuel restriction — clogged filter, failing lift pump, or restricted fuel return",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel fuel filter (primary and secondary)", "notes": "Power loss under load is a classic symptom of a partially restricted fuel filter"},
            {"name": "Fuel transfer pump", "notes": "Measure fuel pressure at the injection pump inlet — below spec indicates lift pump failure"},
        ],
    },
    "intercooler_failure": {
        "label": "Failed or oil-fouled intercooler reducing charge air cooling",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intercooler", "notes": "An oil-fouled intercooler (from turbo seal leak) loses cooling efficiency; inspect for oil inside charge air pipes"},
        ],
    },
    "injector_wear": {
        "label": "Worn fuel injectors — reduced spray atomization and fuel delivery",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Fuel injector set", "notes": "Injector wear on high-mileage diesel engines causes gradual power loss and increased smoke. Flow-test before replacing."},
        ],
    },
    "limp_mode": {
        "label": "ECU limp mode activated — power intentionally limited by a stored fault code",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "OBD-II / diesel scan tool", "notes": "Read all active and pending codes. Limp mode is a symptom, not the root cause — diagnose the stored fault first."},
        ],
    },
}

LOSS_OF_POWER_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "Is there a check engine light, warning lamp, or is the truck in 'limp mode'?",
        "options": [
            {
                "match": "cel_or_limp",
                "label": "Yes — check engine light is on or power is limited with a warning",
                "deltas": {
                    "limp_mode": +0.30,
                    "dpf_clog": +0.15,
                    "egr_clogged": +0.10,
                    "turbo_failure": +0.05,
                },
                "eliminate": [],
                "next_node": "smoke_check",
            },
            {
                "match": "no_cel",
                "label": "No warning lights — power loss with no codes",
                "deltas": {
                    "turbo_boost_leak": +0.20,
                    "fuel_restriction": +0.15,
                    "dpf_clog": +0.10,
                    "limp_mode": -0.05,
                },
                "eliminate": [],
                "next_node": "smoke_check",
            },
        ],
    },

    "smoke_check": {
        "question": "Is there any visible smoke from the exhaust?",
        "options": [
            {
                "match": "black_smoke",
                "label": "Black smoke — especially under load or acceleration",
                "deltas": {
                    "egr_clogged": +0.20,
                    "turbo_boost_leak": +0.15,
                    "injector_wear": +0.15,
                    "intercooler_failure": +0.10,
                    "dpf_clog": -0.10,
                },
                "eliminate": [],
                "next_node": "boost_feel",
            },
            {
                "match": "blue_smoke",
                "label": "Blue smoke — especially at startup or under load",
                "deltas": {
                    "turbo_failure": +0.35,
                    "injector_wear": +0.10,
                    "intercooler_failure": +0.10,
                },
                "eliminate": [],
                "next_node": "boost_feel",
            },
            {
                "match": "no_smoke",
                "label": "No unusual exhaust smoke",
                "deltas": {
                    "dpf_clog": +0.10,
                    "fuel_restriction": +0.10,
                    "turbo_boost_leak": +0.05,
                    "turbo_failure": -0.05,
                },
                "eliminate": [],
                "next_node": "boost_feel",
            },
        ],
    },

    "boost_feel": {
        "question": "Does the turbo spool up normally? Is there a noticeable loss of boost or a 'flat' feeling under hard acceleration?",
        "options": [
            {
                "match": "weak_boost",
                "label": "Definitely feels like less boost than normal — flat or sluggish",
                "deltas": {
                    "turbo_boost_leak": +0.25,
                    "turbo_failure": +0.20,
                    "intercooler_failure": +0.10,
                    "egr_clogged": +0.05,
                },
                "eliminate": [],
                "next_node": "driving_pattern",
            },
            {
                "match": "boost_seems_ok",
                "label": "Boost feels normal but power is still reduced",
                "deltas": {
                    "dpf_clog": +0.20,
                    "fuel_restriction": +0.15,
                    "injector_wear": +0.10,
                    "turbo_boost_leak": -0.10,
                    "turbo_failure": -0.10,
                },
                "eliminate": [],
                "next_node": "driving_pattern",
            },
            {
                "match": "unknown_boost",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": "driving_pattern",
            },
        ],
    },

    "driving_pattern": {
        "question": "What best describes how this truck is used?",
        "options": [
            {
                "match": "mostly_short_city",
                "label": "Mostly short trips, city driving, or idling (limited highway time)",
                "deltas": {
                    "dpf_clog": +0.30,
                    "egr_clogged": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "highway_and_towing",
                "label": "Highway driving and towing / hauling heavy loads",
                "deltas": {
                    "turbo_boost_leak": +0.10,
                    "turbo_failure": +0.10,
                    "fuel_restriction": +0.05,
                    "dpf_clog": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "mixed",
                "label": "Mixed use",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

LOSS_OF_POWER_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"diesel_fuel_gelling": +0.06, "turbo_boost_leak": +0.04},
        "hot": {"turbo_failure": +0.04},
    },
    "mileage_band": {
        "high": {"dpf_clog": +0.10, "egr_clogged": +0.08, "injector_wear": +0.08},
    },
    "usage_pattern": {
        "city": {"dpf_clog": +0.12, "egr_clogged": +0.08},
        "highway": {"dpf_clog": -0.06},
    },
}

LOSS_OF_POWER_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After DPF service or forced regen, perform a highway drive cycle to fully regenerate — stop-and-go driving after DPF work leads to repeat clogging.",
    "Check boost pressure with a gauge — intermittent boost loss that returns at highway speed points to a boost leak that seals under pressure.",
]
