"""
HVAC diagnostic tree — truck/HD variant.

Key differences from base car tree:
- Dual-zone climate control common on crew cab trucks (separate rear HVAC unit)
- Rear HVAC unit in cab ceiling or behind rear seat — separate blower, separate
  blend door, can fail independently
- Larger refrigerant charge (R-134a or R-1234yf) than passenger cars
- Automatic Temperature Control (ATC) on higher trims — prone to sensor/actuator faults
- Diesel trucks: glow plug heat delay means cab heat comes up slower in extreme cold
- Crew cab footprint means longer cabin air ducting runs — blend door issues more common
"""

HVAC_TRUCK_HYPOTHESES: dict[str, dict] = {
    "refrigerant_low_leak": {
        "label": "Refrigerant leak or low charge (weak or no cold air, AC compressor cycling rapidly)",
        "prior": 0.24,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "R-1234yf or R-134a refrigerant (truck spec)", "notes": "Larger cab = larger charge — trucks typically 1.4–2.0 lbs; identify refrigerant type from underhood sticker before purchasing"},
            {"name": "Leak detection dye + UV light kit", "notes": "Leak trace dye is already in most systems — UV light is often sufficient to find the leak before recharging"},
        ],
    },
    "compressor_failure": {
        "label": "AC compressor failure (loud noise, no cold air, compressor clutch not engaging)",
        "prior": 0.16,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "AC compressor with clutch", "notes": "HD truck compressors are high-volume — confirm part by VIN; flush the system and replace the expansion valve/orifice tube whenever a compressor fails (metal debris)"},
            {"name": "Receiver-drier / accumulator", "notes": "Replace with the compressor — old desiccant contamination causes the new compressor to fail prematurely"},
        ],
    },
    "rear_hvac_unit": {
        "label": "Rear HVAC unit failure (rear passengers have no heat/AC — front works fine)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Rear blower motor", "notes": "Rear blower motor is a separate unit, typically under the rear seat or in the ceiling — confirm replacement with exact OEM part; resistor is a separate item"},
            {"name": "Rear blend door actuator", "notes": "Rear blend doors fail independently of the front — scan for rear-zone actuator fault codes before mechanical diagnosis"},
        ],
    },
    "blend_door_actuator": {
        "label": "Blend door actuator fault (stuck on heat or AC, clicking from dash, wrong zone temperature)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Blend door actuator (driver or passenger zone)", "notes": "Dual-zone trucks have multiple actuators — scan for HVAC DTCs (B1xxx) to identify which zone failed before replacing blindly"},
        ],
    },
    "cabin_air_filter_blocked": {
        "label": "Blocked cabin air filter (low airflow, musty smell, weak AC/heat output)",
        "prior": 0.12,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Cabin air filter", "notes": "Trucks used off-road or in rural areas clog cabin filters much faster than city vehicles — check every 15,000 miles or annually"},
        ],
    },
    "blower_motor_resistor": {
        "label": "Blower motor or resistor failure (only works on certain speeds, or no fan at all)",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Blower motor resistor", "notes": "Works on high only (not lower speeds) → resistor. No speeds at all → blower motor or fuse. Confirm which before ordering"},
            {"name": "Blower motor", "notes": "Front blower motor in trucks is typically easier to access than in cars — confirm access panel location in service manual"},
        ],
    },
    "heater_core": {
        "label": "Heater core leak or failure (no heat, foggy windshield, sweet smell, coolant loss)",
        "prior": 0.06,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Heater core", "notes": "Truck heater core replacement requires dash removal — labor-intensive; before condemning it, confirm coolant level and thermostat operation first"},
        ],
    },
    "condenser_blocked": {
        "label": "Condenser blocked with debris (mud, bugs, road debris — reduced cooling capacity)",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "No parts — cleaning only (compressed air or low-pressure water wash)", "notes": "Trucks used off-road or in agricultural settings pack the condenser with debris rapidly — inspect before assuming a refrigerant problem"},
        ],
    },
}

HVAC_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "What is the primary HVAC symptom in the truck?",
        "options": [
            {
                "match": "no_cold",
                "label": "No cold air or very weak AC — blower works but air is warm",
                "deltas": {
                    "refrigerant_low_leak": +0.30,
                    "compressor_failure": +0.20,
                    "cabin_air_filter_blocked": +0.08,
                    "condenser_blocked": +0.08,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
            {
                "match": "no_heat",
                "label": "No heat or very weak heat — blower works but air is cold",
                "deltas": {
                    "blend_door_actuator": +0.25,
                    "heater_core": +0.20,
                    "cabin_air_filter_blocked": +0.08,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
            {
                "match": "wrong_zone",
                "label": "One zone blows wrong temperature (dual-zone — driver side ≠ passenger side)",
                "deltas": {
                    "blend_door_actuator": +0.55,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
            {
                "match": "rear_only",
                "label": "Rear passengers have no heat or AC — front works normally",
                "deltas": {
                    "rear_hvac_unit": +0.65,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
            {
                "match": "low_airflow",
                "label": "Low airflow from all vents — weak air regardless of fan speed",
                "deltas": {
                    "cabin_air_filter_blocked": +0.40,
                    "blower_motor_resistor": +0.15,
                    "condenser_blocked": +0.08,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
            {
                "match": "blower_speed",
                "label": "Blower only works on some speeds, or no blower at all",
                "deltas": {
                    "blower_motor_resistor": +0.55,
                },
                "eliminate": [],
                "next_node": "zone_check",
            },
        ],
    },

    "zone_check": {
        "question": "Does the truck have dual-zone or rear HVAC?",
        "options": [
            {
                "match": "dual_zone",
                "label": "Yes — dual-zone (driver and passenger control independently)",
                "deltas": {
                    "blend_door_actuator": +0.10,
                    "rear_hvac_unit": -0.05,
                },
                "eliminate": [],
                "next_node": "compressor_clutch",
            },
            {
                "match": "rear_hvac",
                "label": "Yes — rear HVAC unit (crew cab with separate rear controls)",
                "deltas": {
                    "rear_hvac_unit": +0.10,
                    "blend_door_actuator": +0.05,
                },
                "eliminate": [],
                "next_node": "compressor_clutch",
            },
            {
                "match": "single_zone",
                "label": "Single zone — one control for the whole cab",
                "deltas": {
                    "rear_hvac_unit": -0.20,
                    "blend_door_actuator": -0.05,
                },
                "eliminate": ["rear_hvac_unit"],
                "next_node": "compressor_clutch",
            },
        ],
    },

    "compressor_clutch": {
        "question": "With AC on and engine running, can you see and hear the AC compressor clutch engaging at the front of the engine?",
        "options": [
            {
                "match": "clutch_engaging",
                "label": "Yes — clutch clicks in and compressor spins (but air is still warm)",
                "deltas": {
                    "refrigerant_low_leak": +0.20,
                    "condenser_blocked": +0.10,
                    "compressor_failure": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "clutch_not_engaging",
                "label": "No — clutch not engaging (compressor not turning when AC is on)",
                "deltas": {
                    "refrigerant_low_leak": +0.20,
                    "compressor_failure": +0.20,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "rapid_cycling",
                "label": "Clutch rapidly clicks on and off (every few seconds)",
                "deltas": {
                    "refrigerant_low_leak": +0.40,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "cant_check",
                "label": "Can't check right now",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HVAC_TRUCK_CONTEXT_PRIORS: dict = {
    "mileage_band": {
        "high": {
            "compressor_failure": +0.10,
            "heater_core": +0.08,
            "blower_motor_resistor": +0.06,
            "blend_door_actuator": +0.06,
        },
        "low": {
            "cabin_air_filter_blocked": +0.08,
        },
    },
    "climate": {
        "hot": {
            "refrigerant_low_leak": +0.10,
            "compressor_failure": +0.08,
            "condenser_blocked": +0.06,
        },
        "cold": {
            "heater_core": +0.08,
            "blend_door_actuator": +0.06,
        },
    },
    "usage_pattern": {
        "city": {
            "cabin_air_filter_blocked": +0.05,
        },
    },
}

HVAC_TRUCK_POST_DIAGNOSIS: list[str] = [
    "On dual-zone trucks, scan for HVAC actuator DTCs (B1xxx codes) before replacing blend door actuators — most actuators have self-diagnostic capability and will store a fault code that identifies exactly which door failed.",
    "After any AC compressor replacement in a truck, always flush the system, replace the orifice tube or expansion valve, and replace the accumulator/drier — metal particles from a failed compressor contaminate the entire circuit and will destroy a new compressor within hours.",
    "If the rear HVAC blower was the fault, check the rear air filter (if equipped) before condemning the motor — some trucks have a separate rear cabin air filter that clogs unnoticed until the rear unit loses airflow completely.",
]
