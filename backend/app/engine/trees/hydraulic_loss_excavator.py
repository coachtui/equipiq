"""
Hydraulic loss diagnostic tree — excavator (hydraulic excavator, mini-excavator).

Excavator hydraulic loss presents as: slow/no boom or arm movement, bucket
won't curl or extend, swing motor failure, travel motor failure, or total loss.
Excavators use a load-sensing tandem pump system — understanding which circuit
is affected narrows the diagnosis significantly.

Demand-tier rule (first-class routing signal):
  - High-demand circuits fail first (boom/arm/bucket weak, swing/travel OK)
    → flow/pressure limitation — suction restriction or pump control issue
  - All functions fail equally
    → system-wide cause — fluid, main pump, pilot circuit
  - Single function fails in isolation
    → localized valve or motor issue
"""

HYDRAULIC_LOSS_EXCAVATOR_HYPOTHESES: dict[str, dict] = {
    "low_fluid": {
        "label": "Low hydraulic fluid level",
        "prior": 0.22,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic fluid (OEM specification)", "notes": "Check OEM spec carefully — ISO 46 or 68 viscosity is typical; do NOT mix grades"},
        ],
    },
    "suction_restriction": {
        "label": "Restricted suction strainer or inlet-side starvation",
        "prior": 0.20,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Suction strainer / suction filter", "notes": "Located inside the tank — drain tank before removal; inspect for debris, sediment, or emulsified fluid; also check for a collapsed suction hose (same symptom)"},
        ],
    },
    "return_filter_contamination": {
        "label": "Contaminated hydraulic fluid / overdue return filter (system health indicator — return filter bypasses when clogged, fluid condition signals broader system damage)",
        "prior": 0.15,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Hydraulic return filter element", "notes": "Change every 500–1000 hours or per OEM schedule; inspect element for metal debris — debris indicates a failing internal component, not just a dirty filter"},
        ],
    },
    "pump_destroking": {
        "label": "Pump destroking or load-sensing control malfunction (pump not building adequate flow/pressure under demand)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Load-sensing relief valve / margin compensator", "notes": "Check load-sensing signal pressure vs. pump outlet pressure; margin spec is typically 200–300 PSI above LS signal; an adjustable compensator may need resetting before condemning the pump"},
        ],
    },
    "failed_main_pump": {
        "label": "Failed main hydraulic pump (tandem piston pump)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Main hydraulic pump assembly", "notes": "Very expensive — confirm with full pressure test at pump outlet ports after filter and fluid service; do not condemn on symptoms alone with unserviced filters"},
        ],
    },
    "pilot_circuit_fault": {
        "label": "Pilot circuit failure — all functions locked (no pilot pressure to main control valve)",
        "prior": 0.15,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Pilot pump", "notes": "Separate small gear pump — test pilot pressure (typically 500–600 PSI)"},
            {"name": "Pilot enable solenoid valve", "notes": "Check voltage at solenoid with gate lever up; no voltage = wiring or controller fault"},
        ],
    },
    "leaking_hose_fitting": {
        "label": "Hydraulic hose or fitting leak (external)",
        "prior": 0.12,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Hydraulic hose assembly (OEM routing)", "notes": "Match spiral braid count and working pressure rating exactly"},
        ],
    },
    "swing_motor_failure": {
        "label": "Swing motor failure (swing-only loss with boom/arm/travel working)",
        "prior": 0.10,
        "diy_difficulty": "seek_mechanic",
        "parts": [
            {"name": "Swing motor and brake assembly", "notes": "Confirm swing brake release pressure before condemning motor"},
        ],
    },
    "relief_valve_fault": {
        "label": "Work-port relief valve stuck open — function moves but extremely weak",
        "prior": 0.08,
        "diy_difficulty": "seek_mechanic",
        "parts": [],
    },
}

HYDRAULIC_LOSS_EXCAVATOR_TREE: dict[str, dict] = {
    "start": {
        "question": "Which functions are affected — boom/arm/bucket, swing, travel, or everything?",
        "options": [
            {
                "match": "all_functions",
                "label": "All functions — nothing responds or everything is extremely slow",
                "deltas": {
                    "low_fluid": +0.18,
                    "suction_restriction": +0.12,
                    "return_filter_contamination": +0.10,
                    "pump_destroking": +0.15,
                    "failed_main_pump": +0.18,
                    "pilot_circuit_fault": +0.20,
                },
                "eliminate": ["swing_motor_failure"],
                "next_node": "fluid_level",
            },
            {
                "match": "boom_arm_weak_swing_travel_ok",
                "label": "Boom, arm, or bucket slow or weak — swing and travel are mostly OK",
                "deltas": {
                    "low_fluid": +0.10,
                    "suction_restriction": +0.20,
                    "return_filter_contamination": +0.12,
                    "pump_destroking": +0.18,
                    "relief_valve_fault": +0.15,
                    "failed_main_pump": +0.06,
                },
                "eliminate": ["swing_motor_failure", "pilot_circuit_fault"],
                "next_node": "fluid_level",
            },
            {
                "match": "swing_only",
                "label": "Swing only — boom/arm/bucket and travel work fine",
                "deltas": {
                    "swing_motor_failure": +0.55,
                    "pilot_circuit_fault": -0.15,
                    "low_fluid": -0.10,
                },
                "eliminate": ["failed_main_pump", "suction_restriction", "return_filter_contamination", "pump_destroking", "relief_valve_fault"],
                "next_node": None,
            },
            {
                "match": "travel_only",
                "label": "Travel motors only — machine won't move but everything else works",
                "deltas": {
                    "relief_valve_fault": +0.20,
                    "leaking_hose_fitting": +0.15,
                    "pilot_circuit_fault": +0.10,
                },
                "eliminate": ["swing_motor_failure", "low_fluid"],
                "next_node": "fluid_level",
            },
        ],
    },

    "fluid_level": {
        "question": "Check the hydraulic fluid level in the sight glass or via the dipstick. What is the level?",
        "options": [
            {
                "match": "low",
                "label": "Level is below the minimum mark",
                "deltas": {
                    "low_fluid": +0.45,
                    "leaking_hose_fitting": +0.12,
                },
                "eliminate": [],
                "next_node": "visible_leak",
            },
            {
                "match": "ok",
                "label": "Level is within the normal range",
                "deltas": {
                    "low_fluid": -0.15,
                    "suction_restriction": +0.08,
                    "return_filter_contamination": +0.08,
                    "failed_main_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "pilot_check",
            },
            {
                "match": "not_sure",
                "label": "Can't check or don't know where the sight glass is",
                "deltas": {},
                "eliminate": [],
                "next_node": "pilot_check",
            },
        ],
    },

    "visible_leak": {
        "question": "Is there visible hydraulic fluid leaking from a hose, fitting, cylinder, or the pump area?",
        "options": [
            {
                "match": "visible_leak",
                "label": "Yes — I can see active fluid leaking",
                "deltas": {
                    "leaking_hose_fitting": +0.40,
                },
                "eliminate": ["failed_main_pump", "swing_motor_failure", "pilot_circuit_fault"],
                "next_node": None,
            },
            {
                "match": "no_leak",
                "label": "No visible external leak",
                "deltas": {
                    "suction_restriction": +0.08,
                    "return_filter_contamination": +0.06,
                    "failed_main_pump": +0.10,
                },
                "eliminate": ["leaking_hose_fitting"],
                "next_node": "pilot_check",
            },
        ],
    },

    "pilot_check": {
        "question": "With the machine running and gate lever UP, do any joystick movements respond — even a very little bit of movement in any function?",
        "options": [
            {
                "match": "nothing_responds",
                "label": "Absolutely nothing responds to any control input",
                "deltas": {
                    "pilot_circuit_fault": +0.45,
                    "failed_main_pump": +0.10,
                },
                "eliminate": ["swing_motor_failure", "relief_valve_fault", "suction_restriction", "pump_destroking"],
                "next_node": None,
            },
            {
                "match": "some_response",
                "label": "Some functions respond at least a little",
                "deltas": {
                    "pilot_circuit_fault": -0.20,
                    "suction_restriction": +0.12,
                    "return_filter_contamination": +0.08,
                    "pump_destroking": +0.08,
                    "relief_valve_fault": +0.12,
                    "failed_main_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "filter_service",
            },
        ],
    },

    "filter_service": {
        "question": "Check hydraulic service history: when was the return filter last changed, and has the suction strainer (inside the tank) been inspected or cleaned?",
        "options": [
            {
                "match": "suction_unknown_return_overdue",
                "label": "Return filter is overdue or was skipped; suction strainer has never been inspected or condition is unknown",
                "deltas": {
                    "suction_restriction": +0.28,
                    "return_filter_contamination": +0.22,
                    "failed_main_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "demand_pattern",
            },
            {
                "match": "return_overdue_suction_ok",
                "label": "Return filter is overdue; suction strainer was recently inspected and clear",
                "deltas": {
                    "return_filter_contamination": +0.22,
                    "suction_restriction": +0.08,
                    "pump_destroking": +0.10,
                    "failed_main_pump": +0.08,
                },
                "eliminate": [],
                "next_node": "demand_pattern",
            },
            {
                "match": "dark_fluid_debris",
                "label": "Dark or discolored fluid, or metal debris found in the filter element",
                "deltas": {
                    "return_filter_contamination": +0.28,
                    "suction_restriction": +0.18,
                    "failed_main_pump": +0.12,
                },
                "eliminate": [],
                "next_node": "demand_pattern",
            },
            {
                "match": "recent_clean",
                "label": "Both return filter and suction strainer serviced recently; fluid was clean",
                "deltas": {
                    "return_filter_contamination": -0.10,
                    "suction_restriction": -0.08,
                    "failed_main_pump": +0.15,
                    "pump_destroking": +0.15,
                    "relief_valve_fault": +0.10,
                },
                "eliminate": [],
                "next_node": "demand_pattern",
            },
            {
                "match": "not_sure",
                "label": "Service history unknown",
                "deltas": {
                    "suction_restriction": +0.08,
                },
                "eliminate": [],
                "next_node": "demand_pattern",
            },
        ],
    },

    "demand_pattern": {
        "question": "Under heavy load — digging hard or lifting at max reach — does the engine lug or bog down noticeably, or does the engine hold RPM while the function feels slow or starved for flow?",
        "options": [
            {
                "match": "engine_bogs",
                "label": "Engine lugs or bogs — RPM drops noticeably when the function is under load",
                "deltas": {
                    "pump_destroking": +0.28,
                    "suction_restriction": +0.12,
                    "failed_main_pump": +0.10,
                    "relief_valve_fault": -0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "engine_holds_rpm",
                "label": "Engine holds RPM but the function is still slow or weak — like it isn't getting enough flow",
                "deltas": {
                    "suction_restriction": +0.22,
                    "return_filter_contamination": +0.12,
                    "pump_destroking": +0.08,
                    "relief_valve_fault": +0.12,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "not_sure",
                "label": "Hard to tell or haven't tested under load",
                "deltas": {},
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

HYDRAULIC_LOSS_EXCAVATOR_CONTEXT_PRIORS: dict = {
    "environment": {
        "dusty": {"suction_restriction": +0.10, "return_filter_contamination": +0.12, "failed_main_pump": +0.05},
        "muddy": {"suction_restriction": +0.08, "return_filter_contamination": +0.08, "leaking_hose_fitting": +0.08},
        "marine": {"leaking_hose_fitting": +0.05, "return_filter_contamination": +0.05},
        "urban": {},
    },
    "hours_band": {
        "overdue_service": {
            "suction_restriction": +0.12,
            "return_filter_contamination": +0.18,
            "failed_main_pump": +0.08,
        },
    },
}

HYDRAULIC_LOSS_EXCAVATOR_POST_DIAGNOSIS: list[str] = [
    "Suction strainer vs. return filter — they fail differently: a clogged suction strainer starves the pump (cavitation, jerky movement, high-demand circuits fail first). A clogged return filter typically activates its bypass valve and goes into bypass rather than directly restricting flow — it is a system health indicator and contamination signal, not usually the direct restriction point.",
    "Pump destroking / load-sensing check: test load-sensing (LS) signal pressure vs. pump outlet pressure. The margin should be ~200–300 PSI above the LS signal per OEM spec. A destroking pump builds little or no margin. An adjustable compensator may only need resetting. Do this before condemning the pump assembly.",
    "Demand-tier pattern: if only high-demand circuits (boom, arm, bucket at max reach) are weak while swing and travel are OK, the system is flow/pressure-limited under high demand — prioritize suction-side restriction and pump control. If all functions fail equally, the cause is system-wide (fluid, main pump, pilot circuit).",
    "Pilot circuit test: with engine running and gate lever raised, check pilot pressure at the pilot manifold (typical spec 500–600 PSI). Zero pilot pressure = pilot pump failure or pilot enable solenoid not energized.",
    "Never perform hydraulic work on an excavator with the boom raised — the boom WILL fall if hydraulic pressure is lost. Always lower to ground and relieve all circuit pressure before disconnecting any line.",
    "Main pump diagnosis: do not condemn the main pump before servicing the return filter, inspecting the suction strainer, and correcting fluid condition. Pump failure is plausible after those steps if the machine is still weak under load and a pressure test at the pump outlet confirms a deficit.",
    "Metal debris in the filter element indicates internal component wear (pump or motor failure). Do not just change the filter — flush the system and identify the debris source before returning to service.",
    "Swing motor brake: the swing brake releases automatically on a pressure signal. If the swing won't move under power but there is no lock-out switch active, check brake release pressure at the swing motor port.",
]
