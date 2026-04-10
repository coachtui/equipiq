# Handoff — Phase 16 Complete

## Current state

All migrations applied (001–012). Backend and frontend fully wired.

```bash
# Start everything
docker compose up -d

# Note: if spinning up a fresh DB, apply missing migrations manually:
# docker exec fix-db-1 psql -U fix -d fixdb -f /tmp/<migration>.sql
# Migrations 009, 011, 012 were missing from the running DB as of 2026-04-07
# and were applied manually.
```

---

## What's complete

### Platform summary
- **91 diagnostic trees** across 13 vehicle types (car, truck, motorcycle, boat, generator, atv, pwc, rv, heavy_equipment, tractor, excavator, loader, skid_steer)
- **Orchestration layer**: evidence normalization, tree routing, discriminator, exit guard, contradiction detection, safety interrupts
- **Learning system**: outcome recording, metrics, controlled weight adjustment (admin-approved), intelligence layer (pattern detection + LLM insights)
- **Telematics**: ingest endpoint, signal normalization → EvidencePackets, session auto-linkage
- **Session modes**: consumer / operator / mechanic — affects rephrase_question tone and result card format
- **HeavyContext**: hours, service hours, environment, storage duration, recent work type — adjusts hypothesis priors

### Phase 16 — Fleet Prioritization Layer
New: `GET /api/fleet/priorities`

Returns all assets ranked by operational risk. Deterministic, weighted, fully explainable.

**Scoring formula:**
```
0.30 × unresolved   + 0.20 × repeat_failure + 0.20 × safety
0.15 × contradictions + 0.05 × anomaly + 0.05 × telematics + 0.05 × service_overdue
```

**Key files:**
- `backend/app/fleet/risk_model.py` — `AssetRisk` dataclass, `compute_asset_risk()`, `rank_assets_by_risk()`, `fetch_all_asset_risk_data()`
- `backend/app/api/fleet.py` — `GET /api/fleet/priorities` endpoint added at bottom
- `frontend/src/lib/fleet.ts` — `AssetRisk` interface + `getFleetPriorities()`
- `frontend/src/app/fleet/page.tsx` — Assets / Priorities tab toggle; `AssetRiskCard` with expand/collapse; `PriorityFilters` by risk level

**No new DB migration required.**

### Phase 15 — Professional Experience + HE Subtype Expansion
- 15A: HE DTC lookup (`POST /api/dtc/lookup`)
- 15B: Professional result card (mechanic/operator mode)
- 15C: HE subtype trees (tractor, excavator, loader, skid_steer — no_start + hydraulic_loss each)
- 15D: Fleet operator dashboard (`/fleet`), `is_operator` role, `GET /api/fleet/*`
- 15E: Operator UX polish (touch targets, camera capture, quick reply chips)

### Phase 14 — Admin Intelligence Dashboard
Expanded admin at `/admin` from 4 to 8 tabs:

| Tab | What it shows |
|---|---|
| Overview | Session stats, 30-day chart |
| Top Diagnoses | symptom × vehicle breakdown |
| Feedback | Rating distribution + comment feed |
| Tree Coverage | Green/grey grid: tree exists vs fallback |
| Learning | AI insights (colored cards), weight adjustment approve/reject, hypothesis metrics |
| Fleet | HE session summary, by_environment/by_mode/top_trees, detected fleet patterns |
| Modes | Per-mode cards + comparison table (green=best, red=worst) |
| Telematics | Asset-filtered feed of recent telemetry readings with signal chips |

---

## DB migrations applied
001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011 → 012

---

## Test suite
- test_orchestrator.py
- test_learning.py
- test_phase95.py (27)
- test_phase105.py (34, 2 pre-existing failures)
- test_phase13a_heavy_equipment.py (207)
- test_phase13b_fleet_heavy.py (56)
- test_phase13c_telematics.py (74)
- test_phase13d_mode_analytics.py (68)
- test_phase15a_dtc.py (15)
- test_phase15b_result_modes.py (19)
- test_phase15c_subtypes.py (22)
- test_phase15d_fleet.py (17 pass, 4 skip)
- **test_phase16_fleet_priorities.py (63)** ← new

Run: `cd backend && pytest tests/ -q`
Total: **696 tests** (692 pass, 4 skip, 2 pre-existing failures in test_phase105.py)

---

## Fleet access

Promote a user to operator to access `/fleet` and `/api/fleet/*`:
```sql
UPDATE users SET is_operator = TRUE WHERE email = 'your@email.com';
```

Promote to admin to access `/admin` and all fleet data:
```sql
UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
```

---

## Phase 17 candidates

### Operationally high-value (fits current architecture)
1. **Telemetry trend detection** — detect rising temp/voltage drift across readings *before* threshold breach. Add `detect_trend()` in `ingestor.py`, surface as a warning-level evidence packet. No schema changes needed.
2. **Asset ID on sessions** — add `asset_id TEXT` column to `diagnostic_sessions` so sessions can be linked to an asset without requiring a telemetry row. Enables direct `asset_id` lookup without the telemetry join. Migration only.
3. **J1939/CAN fault layer** — translate SPN/FMI format into evidence packets + hypothesis adjustments. Parallel to `lookup_he_dtc`. Would need a SPN reference table or LLM function.

### Platform evolution
4. **WebSocket / SSE for live telematics** — push inbound telemetry to open sessions without page refresh. Requires frontend WS hook + backend broadcast.
5. **Operator-guided troubleshooting mode** — step-by-step physical inspection prompts driven by tree nodes, formatted for field use (bold verbs, numbered steps, pass/fail answers).
6. **Service manual reference links** — attach hypothesis keys to service manual section IDs per OEM. Surface as "See service manual §X.X" in mechanic result cards.
