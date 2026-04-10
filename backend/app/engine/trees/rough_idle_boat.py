"""
Rough idle diagnostic tree — boat / marine variant.

Marine rough idle includes: water in fuel (most common marine fuel issue),
dirty carb/injectors from storage, idle mixture screws that need adjustment
after carb rebuild, and ignition problems from corrosive bilge environment.
"""

ROUGH_IDLE_BOAT_HYPOTHESES: dict[str, dict] = {
    "water_in_fuel": {
        "label": "Water in fuel — phase-separated ethanol or tank condensation causing rough combustion",
        "prior": 0.26,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel/water separator filter (Racor or equivalent)", "notes": "Look for cloudy or milky fuel in the filter bowl. Drain water from the separator, replace filter, and refuel with clean fuel."},
        ],
    },
    "idle_circuit_clogged": {
        "label": "Clogged carburetor idle circuit / pilot jet — lean stumble at idle",
        "prior": 0.22,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine carburetor cleaner", "notes": "Spray into the idle passage; the pilot jet orifice is very small and blocks from ethanol varnish"},
            {"name": "Carburetor rebuild kit (marine spec)", "notes": "Rebuild is often necessary after storage with ethanol fuel"},
        ],
    },
    "spark_plug_fouled": {
        "label": "Fouled marine spark plugs — water, oil, or carbon fouling causing misfires",
        "prior": 0.18,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine spark plugs (per engine spec)", "notes": "Marine plugs are often fouled by low-speed/idle operation in displacement mode. Inspect for wet fouling or carbon deposits."},
        ],
    },
    "ignition_corrosion": {
        "label": "Corroded ignition wiring, distributor cap, or rotor in the marine environment",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine distributor cap and rotor", "notes": "Salt air and bilge moisture attack distributor contacts — use marine-grade ignition components with corrosion-resistant contacts"},
            {"name": "Marine ignition wire set", "notes": "Marine wires have extra moisture protection; automotive wires corrode in bilge environments"},
        ],
    },
    "idle_mixture_adjustment": {
        "label": "Idle mixture or idle speed set incorrectly (after carb rebuild or tune-up)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "(No parts — idle mixture screw adjustment)", "notes": "Adjust idle mixture screw per manufacturer spec (typically 1.5 turns out from lightly seated). Set idle speed to 600–700 RPM in gear with engine warm."},
        ],
    },
    "fuel_pressure_low": {
        "label": "Low fuel pressure at idle — failing fuel pump or restricted fuel supply",
        "prior": 0.08,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine fuel pump", "notes": "Check fuel pressure at the carb or injector rail at idle. A mechanical pump can lose diaphragm integrity; an electric pump can wear."},
        ],
    },
    "air_leak_intake": {
        "label": "Air leak at intake manifold or carburetor flange — lean idle",
        "prior": 0.04,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Intake manifold gasket set", "notes": "Spray carb cleaner around the manifold flanges while running — RPM change indicates an air leak"},
        ],
    },
}

ROUGH_IDLE_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "When does the rough idle occur?",
        "options": [
            {
                "match": "cold_start_only",
                "label": "Only on cold start — smooths out when engine warms up",
                "deltas": {
                    "spark_plug_fouled": +0.20,
                    "water_in_fuel": +0.10,
                    "idle_circuit_clogged": +0.10,
                    "idle_mixture_adjustment": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_appearance",
            },
            {
                "match": "always_at_idle",
                "label": "Consistently rough at idle — warm or cold",
                "deltas": {
                    "water_in_fuel": +0.15,
                    "idle_circuit_clogged": +0.20,
                    "ignition_corrosion": +0.10,
                    "idle_mixture_adjustment": +0.10,
                    "air_leak_intake": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_appearance",
            },
            {
                "match": "after_storage",
                "label": "After the boat was stored for the off-season",
                "deltas": {
                    "idle_circuit_clogged": +0.30,
                    "water_in_fuel": +0.20,
                    "spark_plug_fouled": +0.15,
                    "ignition_corrosion": +0.10,
                },
                "eliminate": [],
                "next_node": "fuel_appearance",
            },
        ],
    },

    "fuel_appearance": {
        "question": "Check the fuel/water separator filter bowl. Does the fuel look clear or is it cloudy / milky?",
        "options": [
            {
                "match": "fuel_cloudy_water",
                "label": "Cloudy, milky, or a water layer visible at the bottom",
                "deltas": {
                    "water_in_fuel": +0.45,
                    "idle_circuit_clogged": -0.05,
                },
                "eliminate": [],
                "next_node": "ignition_check",
            },
            {
                "match": "fuel_clear",
                "label": "Fuel is clear — no visible water",
                "deltas": {
                    "water_in_fuel": -0.15,
                    "idle_circuit_clogged": +0.10,
                    "spark_plug_fouled": +0.10,
                    "ignition_corrosion": +0.05,
                },
                "eliminate": [],
                "next_node": "ignition_check",
            },
            {
                "match": "no_separator",
                "label": "No fuel/water separator installed",
                "deltas": {
                    "water_in_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": "ignition_check",
            },
        ],
    },

    "ignition_check": {
        "question": "When did you last replace the spark plugs, distributor cap, and wires?",
        "options": [
            {
                "match": "never_or_old",
                "label": "Never replaced, or unknown age — likely original or several seasons old",
                "deltas": {
                    "spark_plug_fouled": +0.25,
                    "ignition_corrosion": +0.20,
                },
                "eliminate": [],
                "next_node": "carb_service_check",
            },
            {
                "match": "recently_replaced",
                "label": "Recently replaced with marine-grade components",
                "deltas": {
                    "spark_plug_fouled": -0.15,
                    "ignition_corrosion": -0.15,
                    "idle_circuit_clogged": +0.10,
                    "water_in_fuel": +0.10,
                    "air_leak_intake": +0.05,
                },
                "eliminate": [],
                "next_node": "carb_service_check",
            },
            {
                "match": "unknown_service",
                "label": "Not sure",
                "deltas": {
                    "spark_plug_fouled": +0.05,
                    "ignition_corrosion": +0.05,
                },
                "eliminate": [],
                "next_node": "carb_service_check",
            },
        ],
    },

    "carb_service_check": {
        "question": "Has the carburetor been rebuilt, serviced, or had the idle mixture adjusted in the past season?",
        "options": [
            {
                "match": "recent_rebuild",
                "label": "Yes — recently rebuilt, cleaned, or adjusted",
                "deltas": {
                    "idle_mixture_adjustment": +0.30,
                    "idle_circuit_clogged": -0.10,
                    "water_in_fuel": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_recent_work",
                "label": "No recent carb work — hasn't been serviced in a season or more",
                "deltas": {
                    "idle_circuit_clogged": +0.12,
                    "water_in_fuel": +0.06,
                    "idle_mixture_adjustment": -0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "coming_out_of_storage",
                "label": "Just came out of storage for the season",
                "deltas": {
                    "idle_circuit_clogged": +0.20,
                    "water_in_fuel": +0.15,
                    "spark_plug_fouled": +0.06,
                    "ignition_corrosion": +0.06,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

ROUGH_IDLE_BOAT_CONTEXT_PRIORS: dict = {
    "saltwater_use": {
        "yes": {"ignition_corrosion": +0.10, "spark_plug_fouled": +0.06},
    },
    "storage_time": {
        "weeks": {"idle_circuit_clogged": +0.08, "water_in_fuel": +0.06},
        "months": {"idle_circuit_clogged": +0.15, "water_in_fuel": +0.12, "ignition_corrosion": +0.06},
        "season": {"idle_circuit_clogged": +0.18, "water_in_fuel": +0.14, "spark_plug_fouled": +0.08, "ignition_corrosion": +0.08},
    },
    "first_start_of_season": {
        "yes": {"idle_circuit_clogged": +0.12, "water_in_fuel": +0.10, "spark_plug_fouled": +0.06},
    },
    "climate": {
        "cold": {"spark_plug_fouled": +0.06, "idle_mixture_adjustment": +0.04},
    },
}

ROUGH_IDLE_BOAT_POST_DIAGNOSIS: list[str] = [
    "After carburetor service, run the engine at idle in gear for 10 minutes to confirm stable idle — marine idles are sensitive to small fuel restrictions.",
    "Install a fuel/water separator if one is not already fitted — it pays for itself in prevented carb rebuilds.",
]
