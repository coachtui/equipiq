"""
Check engine light diagnostic tree — motorcycle variant.

Modern fuel-injected motorcycles have proprietary fault codes. Only some
models (KTM, certain BMW, Honda, etc.) support standard OBD-II. The first
branch checks for the most motorcycle-specific cause: tip-over sensor
triggered after a drop. Then asks about codes and symptoms.
"""

CHECK_ENGINE_LIGHT_MOTORCYCLE_HYPOTHESES: dict[str, dict] = {
    "tip_over_sensor": {
        "label": "Tip-over / lean angle sensor triggered — common after a drop or hard bump",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Tip-over / lean angle sensor", "notes": "First: cycle ignition off, wait 10s, restart. If code clears, sensor latched from a drop. If it persists after a crash, sensor may need replacement."},
        ],
    },
    "o2_sensor": {
        "label": "Oxygen sensor fault (fuel injection trim issue)",
        "prior": 0.17,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "O2 sensor (motorcycle-specific)", "notes": "Thread size and connector differ from automotive sensors — use OEM or exact match"},
        ],
    },
    "tps": {
        "label": "Throttle position sensor (TPS) fault or miscalibration",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "TPS (throttle position sensor)", "notes": "Check adjustment first per service manual. Calibration often requires a dealer tool."},
        ],
    },
    "fuel_injector": {
        "label": "Fouled or failing fuel injector — common after extended storage",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Fuel injector cleaner additive", "notes": "Add to tank and run several tanks before replacing injector"},
            {"name": "Fuel injector (motorcycle-specific)", "notes": "Flow-test before replacing — cleaning is often sufficient"},
        ],
    },
    "battery_voltage_low": {
        "label": "Low battery voltage causing spurious ECU fault codes",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Motorcycle battery (AGM or lithium)", "notes": "Voltage below 12.0V at rest can cause false codes on many ECUs. Fully charge and clear codes before diagnosing further."},
            {"name": "Battery tender / trickle charger", "notes": "Modern bikes with always-on ECUs can drain batteries during storage"},
        ],
    },
    "abs_fault": {
        "label": "ABS wheel speed sensor or module fault (ABS-equipped bikes only)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Wheel speed sensor", "notes": "Check sensor-to-ring air gap and ring for debris or damage; clean before replacing"},
        ],
    },
    "cam_crank_sensor": {
        "label": "Camshaft or crankshaft position sensor fault",
        "prior": 0.09,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "CKP / CMP sensor", "notes": "Inspect wiring harness near engine — heat cycles crack insulation at the sensor pigtail"},
        ],
    },
    "ecu_spurious": {
        "label": "Spurious stored code — clears after a few ride cycles",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "OBD scan tool or manufacturer diagnostic app", "notes": "Clear the code; complete 2–3 cold-start ride cycles. If it doesn't return, likely a one-time event."},
        ],
    },
}

CHECK_ENGINE_LIGHT_MOTORCYCLE_TREE: dict[str, dict] = {
    "start": {
        "question": "Has the bike been dropped, tipped over, or bumped hard recently — even just leaned against a wall?",
        "options": [
            {
                "match": "yes_dropped",
                "label": "Yes — dropped or tipped over",
                "deltas": {
                    "tip_over_sensor": +0.45,
                    "abs_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "codes_available",
            },
            {
                "match": "no_drop",
                "label": "No — has not been dropped",
                "deltas": {
                    "tip_over_sensor": -0.15,
                    "o2_sensor": +0.05,
                    "tps": +0.05,
                    "battery_voltage_low": +0.05,
                },
                "eliminate": [],
                "next_node": "codes_available",
            },
            {
                "match": "maybe",
                "label": "Maybe — possibly bumped but not a full drop",
                "deltas": {
                    "tip_over_sensor": +0.10,
                },
                "eliminate": [],
                "next_node": "codes_available",
            },
        ],
    },

    "codes_available": {
        "question": "Do you have the fault codes? (Some bikes flash codes via the dash; others need a Bluetooth OBD adapter or dealer scanner.)",
        "options": [
            {
                "match": "has_codes",
                "label": "Yes — I have the codes",
                "deltas": {},
                "eliminate": [],
                "next_node": "code_category",
            },
            {
                "match": "no_codes",
                "label": "No — no scanner available",
                "deltas": {
                    "ecu_spurious": +0.05,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
        ],
    },

    "code_category": {
        "question": "What system does the code relate to? (If multiple, choose the most prominent.)",
        "options": [
            {
                "match": "o2_lambda",
                "label": "O2 / lambda sensor code",
                "deltas": {
                    "o2_sensor": +0.50,
                    "tip_over_sensor": -0.10,
                    "tps": -0.10,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
            {
                "match": "tps_throttle",
                "label": "TPS / throttle body / idle air control code",
                "deltas": {
                    "tps": +0.50,
                    "tip_over_sensor": -0.10,
                    "o2_sensor": -0.10,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
            {
                "match": "lean_angle_tip",
                "label": "Lean angle / tip-over / immobilizer code",
                "deltas": {
                    "tip_over_sensor": +0.40,
                    "ecu_spurious": +0.05,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
            {
                "match": "abs_code",
                "label": "ABS / wheel speed sensor code",
                "deltas": {
                    "abs_fault": +0.55,
                    "tip_over_sensor": -0.10,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
            {
                "match": "other_code",
                "label": "Fuel / injector / crank sensor / other",
                "deltas": {
                    "fuel_injector": +0.15,
                    "cam_crank_sensor": +0.15,
                    "battery_voltage_low": +0.10,
                },
                "eliminate": [],
                "next_node": "engine_behavior",
            },
        ],
    },

    "engine_behavior": {
        "question": "How is the engine running with the light on?",
        "options": [
            {
                "match": "runs_fine",
                "label": "Perfectly normal — no performance issues at all",
                "deltas": {
                    "tip_over_sensor": +0.10,
                    "ecu_spurious": +0.15,
                    "battery_voltage_low": +0.10,
                    "cam_crank_sensor": -0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "rough_hesitant",
                "label": "Rough idle, hesitation, or loss of power",
                "deltas": {
                    "fuel_injector": +0.20,
                    "tps": +0.15,
                    "o2_sensor": +0.10,
                    "cam_crank_sensor": +0.10,
                    "ecu_spurious": -0.15,
                    "tip_over_sensor": -0.10,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
            {
                "match": "stalls",
                "label": "Stalling or won't hold idle",
                "deltas": {
                    "tps": +0.20,
                    "fuel_injector": +0.15,
                    "cam_crank_sensor": +0.15,
                    "battery_voltage_low": +0.10,
                    "ecu_spurious": -0.20,
                },
                "eliminate": [],
                "next_node": "battery_age",
            },
        ],
    },

    "battery_age": {
        "question": "How old is the battery and does cranking feel strong?",
        "options": [
            {
                "match": "old_or_weak",
                "label": "3+ years old, or cranking feels slow / sluggish",
                "deltas": {
                    "battery_voltage_low": +0.30,
                    "ecu_spurious": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "new_strong",
                "label": "New or recently replaced — cranks strongly",
                "deltas": {
                    "battery_voltage_low": -0.20,
                    "o2_sensor": +0.05,
                    "tps": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "unknown_battery",
                "label": "Not sure",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CHECK_ENGINE_LIGHT_MOTORCYCLE_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {"cam_crank_sensor": +0.08, "fuel_injector": +0.06, "tps": +0.06},
    },
    "climate": {
        "cold": {"battery_voltage_low": +0.08},
    },
    "storage_time": {
        "months": {"battery_voltage_low": +0.10, "fuel_injector": +0.06},
        "season": {"battery_voltage_low": +0.12, "fuel_injector": +0.08, "cam_crank_sensor": +0.05},
    },
    "first_start_of_season": {
        "yes": {"battery_voltage_low": +0.10, "fuel_injector": +0.06},
    },
}

CHECK_ENGINE_LIGHT_MOTORCYCLE_POST_DIAGNOSIS: list[str] = [
    "After clearing the code and repairing the fault, ride two warm-up cycles and confirm the CEL does not return.",
    "Check all connector boots and sensor wiring harnesses for corrosion — motorcycle CEL codes are often triggered by moisture at connectors.",
]
