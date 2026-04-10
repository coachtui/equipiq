"""
HVAC diagnostic tree — RV/motorhome variant.

Key differences from base car/truck tree:
- Rooftop AC units (Coleman Mach, Dometic, Airxcel) are the primary cooling system
  — completely different from automotive AC (no engine-driven compressor)
- Shore power (120V AC) powers the rooftop unit when plugged in
- Generator powers the rooftop unit when boondocking
- Heat pump mode available on some newer units (heating from the AC unit)
- Propane furnace is the primary heat source (not a heater core)
- Ducted systems distribute air through ceiling ducts — duct leaks reduce output
- Multiple zone units on large Class A coaches
- Winterization state can leave lines blocked or dampers closed
"""

HVAC_RV_HYPOTHESES: dict[str, dict] = {
    "rooftop_ac_fault": {
        "label": "Rooftop AC unit failure (Coleman/Dometic — compressor, capacitor, or refrigerant)",
        "prior": 0.26,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Start capacitor / run capacitor (rooftop AC unit)", "notes": "Capacitor failure is the most common rooftop AC fault — symptoms: unit hums but compressor doesn't start, trips the breaker; capacitors are inexpensive and often DIY-replaceable on Coleman Mach and Dometic units"},
            {"name": "AC compressor (rooftop unit — unit-specific)", "notes": "Compressor failure on a rooftop unit usually means replacing the full unit rather than just the compressor — confirm unit model and age; parts for older units may be discontinued"},
        ],
    },
    "power_supply_fault": {
        "label": "Shore power or generator power fault (AC unit won't run or trips breaker)",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "30-amp or 50-amp shore power cord and connector", "notes": "Corrosion and heat damage at the pedestal connector causes voltage drop — rooftop AC needs full voltage to start; measure voltage at the AC unit before condemning the unit"},
            {"name": "AC circuit breaker (30A or 15A for AC circuit)", "notes": "Weak breaker trips under AC compressor start-up load — replace with identical amperage rating"},
        ],
    },
    "propane_furnace_fault": {
        "label": "Propane furnace fault (no heat, furnace won't ignite, or fan runs but no heat)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Furnace igniter / electrode", "notes": "Electrode gap widens over time — clean and re-gap or replace; furnace tries to light (clicking sound) but never sustains a flame"},
            {"name": "Sail switch", "notes": "Sail switch detects blower airflow before allowing ignition — fails or sticks on high-use furnaces; furnace blows cold air without igniting"},
            {"name": "Propane regulator", "notes": "Two-stage regulator can freeze or fail — low pressure at the furnace causes an ignition fault code; other LP appliances (stove, water heater) will also have reduced output if the regulator is failing"},
        ],
    },
    "duct_leak_damper": {
        "label": "Duct leak, blocked duct, or closed damper (uneven temperature, one area has no airflow)",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Duct tape / foil HVAC tape (interior duct repair)", "notes": "RV ducts are thin plastic — joints crack at slide-out connections and where ducts run over the slide room; inspect slide-out transitions first"},
            {"name": "Register damper (vent cover with louver)", "notes": "Individual vent dampers can be manually closed — check that all registers are open before diagnosing duct problems"},
        ],
    },
    "rooftop_ac_filter": {
        "label": "Clogged rooftop AC filter or condenser fins packed with debris",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Rooftop AC foam filter pad", "notes": "Clean or replace every 30–45 days of use — heavily clogged filter reduces airflow dramatically and causes the compressor to overheat and cycle off"},
        ],
    },
    "thermostat_fault": {
        "label": "Thermostat or control board fault (AC or furnace won't respond to controls)",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Dometic or Coleman thermostat (RV-specific)", "notes": "RV thermostats are 12V DC low-voltage control, not 24V like home thermostats — confirm brand and compatibility before replacing; Dometic and Coleman thermostats are not interchangeable"},
        ],
    },
    "heat_pump_fault": {
        "label": "Heat pump mode not heating (heat pump only works above ~40°F — below that, propane furnace must supplement)",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — heat pump operating limit", "notes": "Heat pumps on RV rooftop units are rated for outdoor temps above 40°F (4°C); below this, switch to propane furnace; this is a normal operating limitation, not a fault"},
        ],
    },
}

HVAC_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary HVAC symptom in the RV?",
        "options": [
            {
                "match": "no_cold_ac",
                "label": "Rooftop AC runs but doesn't cool — blowing warm air",
                "deltas": {
                    "rooftop_ac_fault": +0.30,
                    "rooftop_ac_filter": +0.20,
                    "power_supply_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
            {
                "match": "ac_wont_start",
                "label": "Rooftop AC unit won't start — hums, trips breaker, or nothing happens",
                "deltas": {
                    "power_supply_fault": +0.30,
                    "rooftop_ac_fault": +0.30,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
            {
                "match": "no_heat_furnace",
                "label": "No heat — furnace won't ignite or blows cold air",
                "deltas": {
                    "propane_furnace_fault": +0.55,
                    "thermostat_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
            {
                "match": "uneven_airflow",
                "label": "Uneven temperature — some areas of the coach much warmer/cooler than others",
                "deltas": {
                    "duct_leak_damper": +0.50,
                    "rooftop_ac_filter": +0.15,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
            {
                "match": "heat_pump_cold",
                "label": "Heat pump not heating well in cold weather",
                "deltas": {
                    "heat_pump_fault": +0.50,
                    "propane_furnace_fault": +0.15,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
            {
                "match": "wont_respond",
                "label": "AC or heat won't respond to thermostat — controls seem dead",
                "deltas": {
                    "thermostat_fault": +0.45,
                    "power_supply_fault": +0.20,
                },
                "eliminate": [],
                "next_node": "power_source",
            },
        ],
    },

    "power_source": {
        "question": "What is the power source for the rooftop AC when this problem occurs?",
        "options": [
            {
                "match": "shore_power",
                "label": "Shore power (plugged into campground or home outlet)",
                "deltas": {
                    "power_supply_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "ac_filter_check",
            },
            {
                "match": "generator",
                "label": "Generator (running on onboard generator)",
                "deltas": {
                    "power_supply_fault": +0.15,
                    "rooftop_ac_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "ac_filter_check",
            },
            {
                "match": "heat_only",
                "label": "Not applicable — only using the propane furnace (heat problem only)",
                "deltas": {
                    "propane_furnace_fault": +0.10,
                    "power_supply_fault": -0.15,
                    "rooftop_ac_fault": -0.20,
                },
                "eliminate": [],
                "next_node": "ac_filter_check",
            },
        ],
    },

    "ac_filter_check": {
        "question": "When was the rooftop AC air filter last cleaned or replaced?",
        "options": [
            {
                "match": "recently_cleaned",
                "label": "Cleaned within the last 30 days",
                "deltas": {
                    "rooftop_ac_filter": -0.20,
                    "rooftop_ac_fault": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_long",
                "label": "Not sure — or not cleaned this season",
                "deltas": {
                    "rooftop_ac_filter": +0.25,
                    "rooftop_ac_fault": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_ac",
                "label": "Not applicable — AC not being used / heat-only issue",
                "deltas": {
                    "rooftop_ac_filter": -0.15,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HVAC_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "rooftop_ac_fault": +0.10,
            "propane_furnace_fault": +0.08,
            "thermostat_fault": +0.06,
        },
    },
    "climate": {
        "hot": {
            "rooftop_ac_fault": +0.10,
            "rooftop_ac_filter": +0.08,
            "power_supply_fault": +0.05,
        },
        "cold": {
            "propane_furnace_fault": +0.12,
            "heat_pump_fault": +0.08,
        },
    },
    "first_start_of_season": {
        "yes": {
            "rooftop_ac_fault": +0.08,
            "propane_furnace_fault": +0.10,
            "duct_leak_damper": +0.06,
        },
    },
}

HVAC_RV_POST_DIAGNOSIS: list[str] = [
    "Before diagnosing a rooftop AC compressor fault, always check the start capacitor first — a failed capacitor costs under $20 and is the most common cause of 'compressor won't start' on Coleman Mach and Dometic units; replacing a $1,500 compressor when it was a $15 capacitor is one of the most common RV repair overspends.",
    "If the propane furnace fault involves no ignition: check that the LP tank is not on 'OPD' (overfill protection device) lock-out — tip the tank slightly and release pressure, then try again; OPD valves on some cylinders lock at high temperatures or when the tank is overfilled.",
    "After any slide-out movement or slideout seal work, inspect the ceiling duct connections at the slide-out transition points — these joints are the most common source of duct leaks in RVs and are easy to reseal with foil HVAC tape.",
]
