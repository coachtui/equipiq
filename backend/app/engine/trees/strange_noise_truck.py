"""
Strange noise diagnostic tree — truck/diesel variant.

Diesel trucks make noises that would alarm a gasoline driver but are
normal: injector rattle, turbo spool whine, and DPF rattle on shutdown.
This tree distinguishes normal diesel sounds from genuine problems.
"""

STRANGE_NOISE_TRUCK_HYPOTHESES: dict[str, dict] = {
    "normal_diesel_noise": {
        "label": "Normal diesel combustion noise — injector clatter, turbo spool, DPF rattle are expected sounds",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No repair needed)", "notes": "Diesel engines are inherently louder than gasoline engines. Cold start clatter, turbo spool on acceleration, and DPF soot settlement rattle after shutdown are normal."},
        ],
    },
    "exhaust_manifold_crack": {
        "label": "Cracked exhaust manifold or failed gasket — loud tick or hiss from the exhaust port",
        "prior": 0.18,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Exhaust manifold gasket set", "notes": "A tick that is loudest cold and quiets when warm is often an exhaust manifold crack (metal expands and seals the gap at temperature)"},
            {"name": "Exhaust manifold", "notes": "Cast iron manifolds crack from thermal cycling — cracks appear at bolt holes or between ports"},
        ],
    },
    "turbo_bearing": {
        "label": "Worn turbocharger bearing — whine, whistle, or grinding that increases with RPM/boost",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Turbocharger assembly", "notes": "Check shaft radial play — any noticeable play means bearing failure. Also check for oil in the compressor inlet."},
            {"name": "Turbo oil feed line", "notes": "Confirm oil supply was not restricted before replacing — starvation causes most turbo bearing failures"},
        ],
    },
    "injector_knock": {
        "label": "Injector knock / rattle — one or more injectors misfiring or delivering unevenly",
        "prior": 0.15,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Injector return o-rings / seals", "notes": "Check injector return leak-off first — cheap repair that often resolves injector knock"},
            {"name": "Fuel injector", "notes": "A cylinder contribution test (via scan tool) identifies the weak injector"},
        ],
    },
    "dpf_heat_shield": {
        "label": "Loose DPF or catalytic converter heat shield — rattle on idle and deceleration",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Heat shield bolts / clamps", "notes": "The thin stamped-steel heat shield above the DPF/exhaust is held with small bolts that corrode and fail; rattle disappears when shield is pressed"},
        ],
    },
    "engine_knock_bearing": {
        "label": "Engine bearing knock — low oil pressure or worn rod/main bearing",
        "prior": 0.12,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Engine oil and filter", "notes": "Check oil level and pressure immediately. A deep knock that increases with RPM is a bearing failure — stop driving."},
        ],
    },
    "valve_train_tick": {
        "label": "Valve train tick — rocker arm, pushrod, or high-pressure pump cam follower wear",
        "prior": 0.09,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Valve cover gasket set (for access)", "notes": "A light tick at idle that does not change with throttle is often valve train. On some diesels, the high-pressure fuel pump cam follower is a known wear item."},
        ],
    },
}

STRANGE_NOISE_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "How would you describe the noise?",
        "options": [
            {
                "match": "tick_knock",
                "label": "Ticking, clicking, or rhythmic knock",
                "deltas": {
                    "exhaust_manifold_crack": +0.25,
                    "injector_knock": +0.20,
                    "engine_knock_bearing": +0.15,
                    "valve_train_tick": +0.15,
                    "normal_diesel_noise": -0.05,
                },
                "eliminate": ["turbo_bearing", "dpf_heat_shield"],
                "next_node": "noise_timing",
            },
            {
                "match": "whine_whistle",
                "label": "Whine, whistle, or high-pitched squeal",
                "deltas": {
                    "turbo_bearing": +0.45,
                    "normal_diesel_noise": +0.10,
                    "engine_knock_bearing": -0.10,
                },
                "eliminate": ["exhaust_manifold_crack", "dpf_heat_shield", "valve_train_tick"],
                "next_node": "noise_timing",
            },
            {
                "match": "rattle",
                "label": "Rattling — especially at idle or on deceleration",
                "deltas": {
                    "dpf_heat_shield": +0.40,
                    "normal_diesel_noise": +0.20,
                    "injector_knock": +0.10,
                },
                "eliminate": ["turbo_bearing", "engine_knock_bearing"],
                "next_node": "noise_timing",
            },
            {
                "match": "deep_knock",
                "label": "Deep, heavy knock or thud — especially under load",
                "deltas": {
                    "engine_knock_bearing": +0.40,
                    "injector_knock": +0.15,
                    "normal_diesel_noise": -0.10,
                },
                "eliminate": ["turbo_bearing", "dpf_heat_shield", "exhaust_manifold_crack"],
                "next_node": "noise_timing",
            },
        ],
    },

    "noise_timing": {
        "question": "When does the noise occur?",
        "options": [
            {
                "match": "cold_start_only",
                "label": "Cold start only — goes away when engine warms up",
                "deltas": {
                    "normal_diesel_noise": +0.25,
                    "exhaust_manifold_crack": +0.20,
                    "engine_knock_bearing": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "always_idle",
                "label": "Constant at idle (warm or cold)",
                "deltas": {
                    "injector_knock": +0.15,
                    "valve_train_tick": +0.10,
                    "engine_knock_bearing": +0.10,
                    "dpf_heat_shield": +0.10,
                    "normal_diesel_noise": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "under_boost_acceleration",
                "label": "Gets worse under acceleration or boost",
                "deltas": {
                    "turbo_bearing": +0.25,
                    "engine_knock_bearing": +0.20,
                    "injector_knock": +0.10,
                    "dpf_heat_shield": -0.10,
                },
                "eliminate": [],
                "next_node": "oil_check",
            },
            {
                "match": "deceleration_only",
                "label": "Only on deceleration / letting off the throttle",
                "deltas": {
                    "dpf_heat_shield": +0.30,
                    "normal_diesel_noise": +0.20,
                    "turbo_bearing": -0.05,
                },
                "eliminate": ["engine_knock_bearing", "injector_knock"],
                "next_node": "oil_check",
            },
        ],
    },

    "oil_check": {
        "question": "Is the engine oil level correct and has oil pressure been normal?",
        "options": [
            {
                "match": "oil_low_or_pressure_warning",
                "label": "Oil is low, or there has been an oil pressure warning light",
                "deltas": {
                    "engine_knock_bearing": +0.35,
                    "turbo_bearing": +0.20,
                    "valve_train_tick": +0.10,
                    "normal_diesel_noise": -0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "oil_ok",
                "label": "Oil level is correct and pressure seems normal",
                "deltas": {
                    "engine_knock_bearing": -0.15,
                    "exhaust_manifold_crack": +0.05,
                    "injector_knock": +0.05,
                    "dpf_heat_shield": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

STRANGE_NOISE_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"normal_diesel_noise": +0.08, "turbo_bearing": +0.04},
    },
    "mileage_band": {
        "high": {"turbo_bearing": +0.10, "engine_knock_bearing": +0.08, "valve_train_tick": +0.06},
    },
    "usage_pattern": {
        "city": {"dpf_heat_shield": +0.08},
    },
}

STRANGE_NOISE_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After turbo or bearing diagnosis, change the engine oil and inspect the oil for metal particles — bearing wear contaminates the oil system.",
    "If an exhaust manifold crack was found, replace all manifold bolts at the same time — diesel heat cycling fatigues the bolts.",
]
