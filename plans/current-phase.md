# Current Phase: Phase 12 — Heavy Equipment Completion

**Status:** COMPLETE (2026-04-06)

## What was done

### 4 additional heavy equipment diagnostic trees

| Tree key | File | Symptom |
|---|---|---|
| `coolant_leak_heavy_equipment` | `trees/coolant_leak_heavy_equipment.py` | Visible coolant loss — hose, pump, radiator, head gasket, freeze plug |
| `implement_failure_heavy_equipment` | `trees/implement_failure_heavy_equipment.py` | Specific implement dead, slow, drifting, or jerky |
| `cab_electrical_heavy_equipment` | `trees/cab_electrical_heavy_equipment.py` | Cab HVAC, gauges, work lights, pressurizer, wipers |
| `fuel_contamination_heavy_equipment` | `trees/fuel_contamination_heavy_equipment.py` | Water, diesel bug, wrong fuel, oxidation, DEF contamination |

All 4 trees registered in `backend/app/engine/trees/__init__.py` (imports + all 4 dicts).

### Session mode (`consumer` | `operator` | `mechanic`)

- `backend/app/diagnostics/orchestrator/controller.py` — `session_mode` field on `SessionState`
- `backend/app/llm/claude.py` — `rephrase_question()` accepts `session_mode`; operator mode uses plain jobsite language with physical check prompts; mechanic mode uses technical terminology
- `backend/app/api/sessions.py` — `CreateSessionRequest` accepts `session_mode`; all three `rephrase_question` calls pass `session.session_mode`
- `backend/app/models/session.py` — `session_mode` column (VARCHAR 20, default `consumer`)
- `frontend/src/types/index.ts` — `SessionMode` type
- `frontend/src/components/ChatInterface.tsx` — mode toggle (Consumer | Operator | Mechanic) shown in idle state

### Heavy equipment intake context (`HeavyContext`)

- `backend/app/engine/context_heavy.py` — `HeavyContext` dataclass + `apply_heavy_context_priors()`
- `backend/app/api/sessions.py` — `HeavyEquipmentContextInput` Pydantic model; wired into session creation; `apply_heavy_context_priors()` applied after standard priors
- `backend/app/models/session.py` — `heavy_context` JSONB column
- `frontend/src/types/index.ts` — `HeavyEquipmentContext` interface
- `frontend/src/components/HeavyEquipmentForm.tsx` — new component: optional heavy context fields (hours, last_service, environment, storage, recent work type)
- `frontend/src/components/ChatInterface.tsx` — "Heavy equipment? Add context →" toggle in idle state
- `frontend/src/lib/api.ts` — `createSession()` accepts `heavy_context` and `session_mode` options

### DB migration

- `db/migrations/010_phase12.sql` — adds `session_mode VARCHAR(20) DEFAULT 'consumer'` and `heavy_context JSONB DEFAULT '{}'` to `diagnostic_sessions`

### `intake_classify` extended

- `backend/app/llm/claude.py` — `SYMPTOM_CATEGORIES` extended with 9 heavy equipment categories; `VEHICLE_TYPES` extended with `heavy_equipment`; prompt rewritten with separate heavy equipment symptom definitions and vehicle type description

---

# Previous Phase: Phase 11 — Heavy Equipment Domain Expansion

**Status:** COMPLETE (2026-04-06)

## What was done

### New vehicle type: `heavy_equipment`

Fully integrated into the existing orchestration architecture. No separate system was created. All flow goes through:
- `orchestration layer` (controller, evidence, safety, exit guard, contradictions)
- `deterministic tree engine` (new trees, same scoring model)
- `safety layer` (extended with construction-specific patterns)

### 7 new diagnostic trees

All trees follow the required 4-export pattern (`_TREE`, `_HYPOTHESES`, `_CONTEXT_PRIORS`, `_POST_DIAGNOSIS`).

| Tree key | File | Symptom |
|---|---|---|
| `no_start_heavy_equipment` | `trees/no_start_heavy_equipment.py` | Diesel no-start (combines no_crank + crank_no_start for operator UX) |
| `hydraulic_loss_heavy_equipment` | `trees/hydraulic_loss_heavy_equipment.py` | Loss of hydraulic pressure/function |
| `loss_of_power_heavy_equipment` | `trees/loss_of_power_heavy_equipment.py` | Engine/machine power loss |
| `overheating_heavy_equipment` | `trees/overheating_heavy_equipment.py` | Engine overtemperature |
| `electrical_fault_heavy_equipment` | `trees/electrical_fault_heavy_equipment.py` | Electrical system faults |
| `track_or_drive_issue_heavy_equipment` | `trees/track_or_drive_issue_heavy_equipment.py` | Track/undercarriage/drive problems |
| `abnormal_noise_heavy_equipment` | `trees/abnormal_noise_heavy_equipment.py` | Diesel, hydraulic, and mechanical noise diagnosis |

Trees resolve correctly via `resolve_tree_key(symptom, "heavy_equipment")`.

### Evidence expansion

`backend/app/diagnostics/orchestrator/evidence.py`:
- Added `operator_observation` source (field checks by operator — certainty 0.80)
- Added `manual_check` source (deliberate manual tests — certainty 0.90)
- Added `sensor_future` source (telematics/sensor placeholder — certainty 0.0)
- Added builder functions: `build_from_operator_observation()`, `build_from_manual_check()`, `build_sensor_placeholder()`

### Safety layer expansion

`backend/app/diagnostics/orchestrator/safety.py`:
- High-pressure hydraulic line rupture (critical — injection injury warning)
- Uncontrolled machine movement (critical)
- Equipment brake failure (critical)
- Fuel leak near hot diesel engine (critical)
- Electrical arc/short on heavy equipment (critical)
- Equipment overtemperature shutdown (critical)
- Low hydraulic fluid warning (warning)
- Machine tipping/stability risk (warning)

### HeavyContext dataclass and prior system

`backend/app/engine/context_heavy.py` (new file):
- `HeavyContext` dataclass: `hours_of_operation`, `last_service_hours`, `environment`, `storage_duration`, `recent_work_type`
- `apply_heavy_context_priors()`: adjusts hypothesis priors based on environment and hours bands
- Overdue service threshold: 250 hours since last PM → applies overdue priors
- Long storage threshold: 30 days → applies storage priors
- `heavy_context_from_intake()`: parses HeavyContext from intake data
- Future stubs: `telematics_context_hook()`, `maintenance_log_hook()` (no-op, phase 12+)

### Session mode

`backend/app/diagnostics/orchestrator/controller.py`:
- Added `session_mode: str = "consumer"` field to `SessionState`
- Supports: `"consumer"` | `"mechanic"` | `"operator"`
- Used downstream by `rephrase_question` LLM function to adjust terminology and depth

### Tree router: heavy equipment ambiguous pairs

`backend/app/diagnostics/orchestrator/tree_router.py`:
- `loss_of_power` ↔ `hydraulic_loss` — operator conflates engine and hydraulic power loss
- `no_start` ↔ `electrical_fault` — safety interlock failure vs battery failure
- `track_or_drive_issue` ↔ `abnormal_noise` — undercarriage noise vs drive system failure
- `overheating` ↔ `hydraulic_loss` — both can present as machine warning lights

### Registration

All 7 trees registered in `backend/app/engine/trees/__init__.py` under:
- `TREES`
- `HYPOTHESES`
- `CONTEXT_PRIORS`
- `POST_DIAGNOSIS`

## Key files changed

| File | Change |
|---|---|
| `backend/app/engine/trees/no_start_heavy_equipment.py` | New — 8 hypotheses, 7-node tree |
| `backend/app/engine/trees/hydraulic_loss_heavy_equipment.py` | New — 7 hypotheses, 5-node tree |
| `backend/app/engine/trees/loss_of_power_heavy_equipment.py` | New — 7 hypotheses, 5-node tree |
| `backend/app/engine/trees/overheating_heavy_equipment.py` | New — 7 hypotheses, 5-node tree |
| `backend/app/engine/trees/electrical_fault_heavy_equipment.py` | New — 7 hypotheses, 5-node tree |
| `backend/app/engine/trees/track_or_drive_issue_heavy_equipment.py` | New — 8 hypotheses, 5-node tree |
| `backend/app/engine/trees/abnormal_noise_heavy_equipment.py` | New — 7 hypotheses, 5-node tree |
| `backend/app/engine/trees/__init__.py` | +7 imports, +7 entries in all 4 dicts |
| `backend/app/diagnostics/orchestrator/evidence.py` | +3 new source types, +3 builder functions |
| `backend/app/diagnostics/orchestrator/safety.py` | +8 heavy equipment patterns (6 critical, 2 warning) |
| `backend/app/diagnostics/orchestrator/controller.py` | +session_mode field on SessionState |
| `backend/app/diagnostics/orchestrator/tree_router.py` | +4 heavy equipment ambiguous pairs |
| `backend/app/engine/context_heavy.py` | New — HeavyContext, apply_heavy_context_priors, future stubs |

## How heavy equipment differs from passenger vehicles

### Context priors
Passenger vehicles use `climate` and `mileage_band`. Heavy equipment uses:
- `environment`: dusty / muddy / marine / urban (jobsite condition)
- `hours_band.overdue_service`: triggered when `hours_of_operation - last_service_hours >= 250`
- `hours_band.long_storage`: triggered when `storage_duration >= 30` days

### Safety
- Passenger vehicle safety focuses on driving hazards (brake failure, fuel fire, overheating while driving)
- Heavy equipment safety adds: hydraulic injection injury, uncontrolled machine movement, brake-not-holding on grade, tip-over risk, arc flash from battery disconnects
- Both use the same `evaluate_safety()` scan mechanism — no separate system

### Question language
- Operator-level: plain language, physical check prompts ("look underneath", "check the sight glass")
- "Not sure / can't check" options on most nodes (jobsite reality)
- "Don't know" never dead-ends the tree — uncertainty is absorbed into score uncertainty

### Hypotheses
- Diesel-specific: glow plug failure, air in fuel system, safety interlocks (seat/neutral lock)
- Hydraulic-specific: new `hydraulic_loss` symptom category (no passenger vehicle equivalent)
- Undercarriage: track tension, sprocket wear, idler/roller failure (no passenger vehicle equivalent)
- Hours-based degradation replaces mileage-based degradation for wear priors

## Verification

1. `resolve_tree_key("no_start", "heavy_equipment")` → `"no_start_heavy_equipment"` ✓
2. `resolve_tree_key("hydraulic_loss", "heavy_equipment")` → `"hydraulic_loss_heavy_equipment"` ✓
3. `evaluate_safety(["hydraulic line bursting and spraying"])` → critical alert ✓
4. `HeavyContext(hours_of_operation=4500, last_service_hours=4100)` + `apply_heavy_context_priors()` → overdue service priors applied ✓
5. `SessionState(..., session_mode="operator")` serialises and deserialises correctly ✓
