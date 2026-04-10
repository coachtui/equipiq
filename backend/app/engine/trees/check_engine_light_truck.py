"""
Check engine light diagnostic tree — truck/diesel variant.

Diesel trucks have OBD-II codes but also have emissions-specific codes
not seen in gasoline vehicles: DEF/SCR system faults (P20XX), DPF codes
(P2002, P2003), EGR codes, and injection system codes. This tree routes
by code family and symptoms, prioritising the most common diesel-specific issues.
"""

CHECK_ENGINE_LIGHT_TRUCK_HYPOTHESES: dict[str, dict] = {
    "def_scr_fault": {
        "label": "DEF/SCR system fault — low DEF, contaminated DEF, or NOx sensor failure (P20XX)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Diesel Exhaust Fluid (DEF / AdBlue)", "notes": "Check DEF level first — low DEF is the most common cause. Use only ISO 22241-compliant fluid. Contaminated DEF (wrong fluid, water) requires draining the tank."},
            {"name": "NOx sensor", "notes": "If DEF is full and quality is confirmed, the upstream or downstream NOx sensor may be faulty (P2201/P2202)"},
        ],
    },
    "dpf_clog_code": {
        "label": "DPF (diesel particulate filter) full or failed regeneration (P2002, P2003)",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "DPF forced regeneration via scan tool", "notes": "A parked regen burns accumulated soot. Or: 40 min highway driving at 55+ mph often completes a passive regen."},
            {"name": "DPF professional cleaning or replacement", "notes": "If regeneration fails repeatedly, the DPF may be mechanically blocked or the ash load is too high for regen to clear"},
        ],
    },
    "egr_fault": {
        "label": "EGR system fault — valve stuck, cooler leak, or position sensor (P0400 series)",
        "prior": 0.16,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "EGR valve", "notes": "Diesel EGR valves clog heavily with carbon — clean with carbon remover before replacing"},
            {"name": "EGR cooler", "notes": "A leaking EGR cooler causes coolant loss and white exhaust smoke; replace if coolant is found in the intake"},
            {"name": "EGR position sensor / actuator", "notes": "The actuator that opens/closes the EGR valve can fail independently of the valve itself"},
        ],
    },
    "fuel_system_code": {
        "label": "Fuel injection system code — rail pressure, lift pump, or injector (P0087, P0088, P0093)",
        "prior": 0.14,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Diesel fuel filter (primary and secondary)", "notes": "P0087 (low rail pressure) is often a clogged fuel filter before an injection pump is condemned"},
            {"name": "Fuel lift / transfer pump", "notes": "Measure fuel pressure at the high-pressure pump inlet — below spec confirms lift pump failure"},
            {"name": "High-pressure fuel pump", "notes": "Last resort after filter and lift pump are verified good"},
        ],
    },
    "turbo_code": {
        "label": "Turbocharger or boost system code — variable vane, boost pressure, or wastegate (P0234, P0299)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Turbo VGT (variable geometry) actuator", "notes": "A sticking VGT causes P0299 (underboost) or P0234 (overboost). Clean carbon from the vanes before replacing."},
            {"name": "Boost pressure sensor / MAP sensor", "notes": "Test the sensor reading via live data; an out-of-range reading can trigger codes without actual turbo failure"},
        ],
    },
    "glow_plug_code": {
        "label": "Glow plug circuit fault — one or more plugs or the controller (P0670–P0679)",
        "prior": 0.10,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Glow plugs (full set)", "notes": "Test each plug for resistance — 2–6 Ω is normal. An open circuit (infinite resistance) = failed plug."},
            {"name": "Glow plug controller / module", "notes": "If all plugs test good, the controller or its fuse may be faulty"},
        ],
    },
    "o2_nox_sensor": {
        "label": "O2 or NOx sensor fault — emissions monitoring sensor (P0130–P0167, P2200–P2205)",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "O2 sensor (diesel-specific, wideband lambda)", "notes": "Confirm the specific sensor (upstream/downstream) from the code range before purchasing"},
            {"name": "NOx sensor", "notes": "P220X codes; check DEF quality and level before replacing the sensor"},
        ],
    },
    "battery_charging": {
        "label": "Low voltage or charging system fault affecting emissions modules (P0562, P0563)",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Batteries (dual battery system)", "notes": "Diesel trucks rely on stable voltage for emission control modules. Test both batteries under load."},
            {"name": "Alternator", "notes": "Output should be 13.8–14.5V at idle; below 13V under load indicates alternator failure"},
        ],
    },
}

CHECK_ENGINE_LIGHT_TRUCK_TREE: dict[str, dict] = {
    "start": {
        "question": "Do you have the fault codes from a scan tool?",
        "options": [
            {
                "match": "has_codes",
                "label": "Yes — I have the codes",
                "deltas": {},
                "eliminate": [],
                "next_node": "code_family",
            },
            {
                "match": "no_codes",
                "label": "No scanner — codes not read yet",
                "deltas": {
                    "def_scr_fault": +0.05,
                    "dpf_clog_code": +0.05,
                    "egr_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
        ],
    },

    "code_family": {
        "question": "What family or range do the codes fall in?",
        "options": [
            {
                "match": "p20xx_def_scr",
                "label": "P20XX — DEF/SCR/NOx emissions system",
                "deltas": {
                    "def_scr_fault": +0.55,
                    "o2_nox_sensor": +0.10,
                    "dpf_clog_code": -0.10,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "p2002_p2003_dpf",
                "label": "P2002 or P2003 — DPF efficiency / regeneration",
                "deltas": {
                    "dpf_clog_code": +0.60,
                    "egr_fault": -0.10,
                    "fuel_system_code": -0.10,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "p04xx_egr",
                "label": "P04XX — EGR system",
                "deltas": {
                    "egr_fault": +0.60,
                    "dpf_clog_code": -0.10,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "p0087_p0093_fuel",
                "label": "P0087/P0088/P0093 — fuel rail pressure",
                "deltas": {
                    "fuel_system_code": +0.60,
                    "def_scr_fault": -0.15,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "p0234_p0299_turbo",
                "label": "P0234/P0299 — turbo over/underboost",
                "deltas": {
                    "turbo_code": +0.60,
                    "def_scr_fault": -0.15,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "p067x_glow",
                "label": "P0670–P0679 — glow plug circuit",
                "deltas": {
                    "glow_plug_code": +0.60,
                    "def_scr_fault": -0.15,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
            {
                "match": "other_codes",
                "label": "Other codes or multiple different families",
                "deltas": {
                    "battery_charging": +0.05,
                },
                "eliminate": [],
                "next_node": "symptoms",
            },
        ],
    },

    "symptoms": {
        "question": "Is the truck running differently with the light on?",
        "options": [
            {
                "match": "power_loss_limp",
                "label": "Yes — power loss or in limp mode",
                "deltas": {
                    "dpf_clog_code": +0.15,
                    "turbo_code": +0.15,
                    "fuel_system_code": +0.10,
                    "def_scr_fault": +0.05,
                },
                "eliminate": [],
                "next_node": "def_level",
            },
            {
                "match": "runs_normally",
                "label": "Runs perfectly normally",
                "deltas": {
                    "def_scr_fault": +0.15,
                    "o2_nox_sensor": +0.10,
                    "battery_charging": +0.05,
                    "dpf_clog_code": +0.05,
                },
                "eliminate": [],
                "next_node": "def_level",
            },
            {
                "match": "rough_smoke",
                "label": "Rough idle, excess smoke, or hard to start",
                "deltas": {
                    "egr_fault": +0.20,
                    "glow_plug_code": +0.15,
                    "fuel_system_code": +0.10,
                    "dpf_clog_code": -0.05,
                },
                "eliminate": [],
                "next_node": "def_level",
            },
        ],
    },

    "def_level": {
        "question": "What is the DEF (diesel exhaust fluid) level in the tank?",
        "options": [
            {
                "match": "def_low_or_empty",
                "label": "Low or empty — DEF warning light may also be on",
                "deltas": {
                    "def_scr_fault": +0.35,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "def_ok",
                "label": "Full or adequate level",
                "deltas": {
                    "def_scr_fault": -0.10,
                    "dpf_clog_code": +0.05,
                    "egr_fault": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_def_system",
                "label": "This truck doesn't have a DEF system (pre-2010 diesel or deleted)",
                "deltas": {
                    "def_scr_fault": -0.30,
                    "dpf_clog_code": +0.10,
                    "egr_fault": +0.10,
                },
                "eliminate": ["def_scr_fault"],
                "next_node": None,
            },
        ],
    },
}

CHECK_ENGINE_LIGHT_TRUCK_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"glow_plug_code": +0.10, "battery_charging": +0.06},
        "hot": {"def_scr_fault": +0.04},
    },
    "mileage_band": {
        "high": {"dpf_clog_code": +0.10, "egr_fault": +0.08, "fuel_system_code": +0.06},
    },
    "usage_pattern": {
        "city": {"dpf_clog_code": +0.12, "egr_fault": +0.10},
        "highway": {"dpf_clog_code": -0.06},
    },
}

CHECK_ENGINE_LIGHT_TRUCK_POST_DIAGNOSIS: list[str] = [
    "After DPF or DEF/SCR repair, perform a stationary forced regeneration with a scan tool to confirm the system clears.",
    "After clearing truck-specific DTCs, drive a full highway cycle before checking whether readiness monitors have reset.",
]
