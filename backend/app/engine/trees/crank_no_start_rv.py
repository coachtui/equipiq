"""
Crank-no-start diagnostic tree — RV/motorhome variant.

Key differences from base car tree:
- Class A diesel pusher (Cummins ISL/ISC, CAT C7/C9): fuel prime sequence, air bleed
  required after running dry; no ignition coils
- Gas chassis (Ford V10, Chevy 8.1L, Workhorse): standard gasoline engine — similar
  to truck crank-no-start but with longer fuel lines and potential LP shutoff valves
- LP fuel system on some coaches: safety shutoff solenoid, CO detector triggering
- Diesel: water-in-fuel separator and air in fuel lines are RV-specific concerns
- Diesel fuel additives and biofuel blends can cause wax gelling and injector issues
"""

CRANK_NO_START_RV_HYPOTHESES: dict[str, dict] = {
    "diesel_fuel_prime": {
        "label": "Fuel prime needed — diesel pusher ran dry or air in fuel lines",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Diesel fuel (fill tank — minimum 1/4 tank)", "notes": "Running a diesel engine near empty introduces air into the fuel system; Cummins ISL and CAT C7 require a manual prime cycle before restarting after running dry"},
            {"name": "Fuel filter (primary and secondary — replace if water/debris found)", "notes": "Check the water-in-fuel separator indicator on the dash or filter housing; water in diesel destroys injectors"},
        ],
    },
    "glow_plug_system": {
        "label": "Glow plug or wait-to-start system fault — diesel pusher only (cold start failure)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Wait for the wait-to-start light to go out before cranking — if it never illuminates in cold weather, the glow plug controller has likely failed"},
            {"name": "Glow plug controller / relay", "notes": "Cummins engines have an intake air heater instead of glow plugs — if the air heater element fails, cold start performance degrades significantly"},
        ],
    },
    "lp_shutoff_or_sensor": {
        "label": "LP fuel shutoff solenoid triggered or CO/LP sensor fault — gas coach",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "LP fuel shutoff solenoid", "notes": "Located at the LP tank or inline on the fuel supply — a CO or LP leak detector inside the coach can trigger the shutoff; check for leak detector alarms before diagnosing the solenoid itself"},
            {"name": "CO/LP detector", "notes": "Old CO/LP detectors false-trigger and shut off the LP supply — test detector by pressing test button; replace detectors older than 5–7 years"},
        ],
    },
    "chassis_fuel_delivery": {
        "label": "Fuel pump or fuel filter fault — gas chassis (Ford V10, Chevy 8.1L)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel filter", "notes": "Gas chassis fuel filters are on a truck-like replacement interval; clogged filter reduces fuel pressure below crank-to-start threshold"},
            {"name": "Fuel pump (in-tank)", "notes": "Confirm fuel pressure with a gauge before condemning the pump; listen for the pump prime hum for 2 seconds after key-on"},
        ],
    },
    "no_spark_ignition": {
        "label": "Ignition fault — no spark (gas chassis only: coil pack, crankshaft position sensor)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Crankshaft position sensor", "notes": "Ford V10 and GM 8.1L CKP sensors fail without warning — engine cranks but ECM has no RPM signal; scan for P0335/P0336 codes first"},
            {"name": "Ignition coil pack (or coil-on-plug)", "notes": "Ford V10 uses a single coil pack — if partially failed, some cylinders fire and the engine cranks but misfires badly without starting"},
        ],
    },
    "diesel_fuel_quality": {
        "label": "Contaminated or gelled diesel fuel (bad fuel, water, or winter wax separation)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Diesel fuel additive / anti-gel (Power Service)", "notes": "Gelled or contaminated fuel requires draining the tank and replacing both fuel filters; anti-gel additive is preventive, not a cure for already-gelled fuel"},
            {"name": "Dual fuel filters (primary and secondary)", "notes": "Replace both filters when fuel quality is suspect — secondary filter clogged with wax will not clear even with heat treatment"},
        ],
    },
    "immobilizer_ecm": {
        "label": "ECM / PCM fault or anti-theft immobilizer active",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Scan tool / diagnostic check", "notes": "Connect scan tool and check for P-codes and B-codes (security) before condemning the PCM; security light on during cranking indicates the immobilizer is active"},
        ],
    },
}

CRANK_NO_START_RV_TREE: dict[str, dict] = {
    "start": {
        "question": "What happens when the RV cranks but won't start?",
        "options": [
            {
                "match": "cranks_normally",
                "label": "Cranks at normal speed but doesn't fire — no attempt to run",
                "deltas": {
                    "diesel_fuel_prime": +0.20,
                    "diesel_fuel_quality": +0.12,
                    "lp_shutoff_or_sensor": +0.10,
                    "chassis_fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_fuel_type",
            },
            {
                "match": "cranks_misfires",
                "label": "Cranks and tries to start but stumbles, fires briefly, then dies",
                "deltas": {
                    "diesel_fuel_prime": +0.25,
                    "glow_plug_system": +0.15,
                    "lp_shutoff_or_sensor": +0.10,
                    "diesel_fuel_quality": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_fuel_type",
            },
            {
                "match": "cold_start_only",
                "label": "Won't start only when cold — starts fine once warm",
                "deltas": {
                    "glow_plug_system": +0.40,
                    "diesel_fuel_quality": +0.15,
                },
                "eliminate": [],
                "next_node": "engine_fuel_type",
            },
        ],
    },

    "engine_fuel_type": {
        "question": "What type of engine does this RV have?",
        "options": [
            {
                "match": "diesel_pusher",
                "label": "Diesel pusher (Cummins ISL/ISC, CAT C7/C9 — rear engine)",
                "deltas": {
                    "glow_plug_system": +0.10,
                    "diesel_fuel_prime": +0.10,
                    "diesel_fuel_quality": +0.08,
                    "lp_shutoff_or_sensor": -0.10,
                    "no_spark_ignition": -0.20,
                },
                "eliminate": ["lp_shutoff_or_sensor", "no_spark_ignition"],
                "next_node": "recent_event",
            },
            {
                "match": "gas_engine",
                "label": "Gas engine (Ford V10, Chevy 8.1L, Workhorse — front engine)",
                "deltas": {
                    "chassis_fuel_delivery": +0.10,
                    "no_spark_ignition": +0.10,
                    "lp_shutoff_or_sensor": +0.08,
                    "glow_plug_system": -0.20,
                    "diesel_fuel_prime": -0.20,
                    "diesel_fuel_quality": -0.15,
                },
                "eliminate": ["glow_plug_system", "diesel_fuel_prime", "diesel_fuel_quality"],
                "next_node": "recent_event",
            },
        ],
    },

    "recent_event": {
        "question": "Did anything happen just before the no-start — ran out of fuel, recently stored, or alarm/security light on?",
        "options": [
            {
                "match": "ran_out_fuel",
                "label": "Ran out of fuel or fuel was very low",
                "deltas": {
                    "diesel_fuel_prime": +0.40,
                    "chassis_fuel_delivery": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "long_storage",
                "label": "Sat for an extended period (months)",
                "deltas": {
                    "diesel_fuel_quality": +0.15,
                    "chassis_fuel_delivery": +0.10,
                    "lp_shutoff_or_sensor": +0.08,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "security_light",
                "label": "Security or anti-theft light on during cranking",
                "deltas": {
                    "immobilizer_ecm": +0.55,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "nothing_obvious",
                "label": "Nothing specific — just didn't start",
                "deltas": {
                    "chassis_fuel_delivery": +0.05,
                    "glow_plug_system": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_RV_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "diesel_fuel_prime": +0.06,
            "glow_plug_system": +0.08,
            "chassis_fuel_delivery": +0.08,
        },
    },
    "storage_time": {
        "long": {
            "diesel_fuel_quality": +0.15,
            "lp_shutoff_or_sensor": +0.10,
            "chassis_fuel_delivery": +0.08,
        },
    },
    "climate": {
        "cold": {
            "glow_plug_system": +0.12,
            "diesel_fuel_quality": +0.10,
        },
    },
    "first_start_of_season": {
        "yes": {
            "diesel_fuel_quality": +0.12,
            "lp_shutoff_or_sensor": +0.10,
        },
    },
}

CRANK_NO_START_RV_POST_DIAGNOSIS: list[str] = [
    "After a diesel pusher runs out of fuel, the manual prime procedure is required — for Cummins ISL: turn key to run (not start) for 30 seconds to allow the lift pump to prime, repeat 3–4 times, then crank; do not crank repeatedly without priming as this accelerates starter wear.",
    "LP/CO detectors in RVs have a rated life of 5–7 years — an old detector triggering a false alarm and cutting LP fuel is a common cause of RV no-start complaints; check the manufacture date on the detector label before diagnosing the LP shutoff solenoid.",
    "If a diesel RV sat for more than 6 months, add a biocide fuel treatment before starting — microbial growth in diesel tanks is common during storage and produces a black slime that clogs both fuel filters; drain the primary water separator before attempting to start.",
]
