# Latest Build Report — Phase 16

**Date:** 2026-04-07
**Phase:** 16 — Fleet Prioritization Layer (Operational Risk + Action Ranking)
**Status:** Complete — no migration required, 63/63 tests pass

---

## What was built

A deterministic, weighted, explainable risk scoring system for fleet assets.
Each asset receives a risk_score (0–1), a risk_level label, up to 5 contributing factors,
and a recommended action — all traceable to structured inputs with no LLM involvement.

---

## Architecture

```
GET /api/fleet/priorities
        ↓
fetch_all_asset_risk_data(db, days=30)
  — 2 queries: sessions (with outcomes) + telemetry
  — returns sessions_by_asset, telemetry_by_asset
        ↓
compute_asset_risk(asset_id, sessions, telemetry)   ← pure function, no DB
  — 7 components, each normalized [0,1], weighted
  — contributing_factors ordered by weighted impact
  — recommended_action from priority-ordered rules
        ↓
rank_assets_by_risk(risks)   ← sort descending by risk_score
        ↓
JSON response: [{asset_id, risk_score, risk_level,
                 contributing_factors, recommended_action, component_scores}]
```

---

## Scoring formula

| Component | Weight | Normalizer | Source |
|---|---|---|---|
| unresolved | 0.30 | /5 sessions | open or was_resolved=False |
| repeat_failure | 0.20 | /3 excess occurrences | same symptom_category |
| safety | 0.20 | /3 events | safety_triggered + critical telemetry |
| contradiction | 0.15 | /3 avg/session | contradiction_count from outcomes |
| anomaly | 0.05 | / total sessions | context.last_anomaly present |
| telematics | 0.05 | /5 readings | readings with any safety_alerts |
| service | 0.05 | binary | hours - last_service >= 250 |

All components independently clamped [0, 1]. Final score clamped [0, 1], rounded 4dp.
Weights sum exactly to 1.0.

---

## Risk levels

| Score range | Label | Frontend colour |
|---|---|---|
| 0.75–1.0 | critical | red |
| 0.50–0.75 | high | orange |
| 0.25–0.50 | medium | yellow |
| 0.00–0.25 | low | green |

---

## Recommended action rules (priority order)

1. `tel_critical > 0` → "Immediate stop — critical sensor alert detected"
2. `session_safety > 0` → "Immediate inspection required — safety risk..."
3. `unresolved ≥ 2 AND repeat ≥ 2` → "Escalate to mechanic — recurring {symptom}..."
4. `unresolved ≥ 3` → "Escalate to mechanic — {n} unresolved sessions"
5. `service_overdue AND repeat ≥ 2` → "Schedule urgent service..."
6. `service_overdue` → "Schedule service — maintenance interval exceeded"
7. `repeat ≥ 2` → "Re-investigate {symptom} — recurring issue..."
8. `avg_contradictions ≥ 1.5` → "Request diagnostic review..."
9. `tel_abnormal ≥ 3` → "Monitor sensors — elevated telemetry alerts..."
10. `risk_score > 0` → "Monitor — asset shows elevated risk signals..."
11. default → "No immediate action required"

---

## Files changed

| File | Change |
|---|---|
| `backend/app/fleet/__init__.py` | new — package init |
| `backend/app/fleet/risk_model.py` | new — core risk model |
| `backend/app/api/fleet.py` | added `GET /api/fleet/priorities` |
| `frontend/src/lib/fleet.ts` | added `AssetRisk` interface + `getFleetPriorities()` |
| `frontend/src/app/fleet/page.tsx` | added Assets/Priorities tab toggle, `AssetRiskCard`, `PriorityFilters` |
| `backend/tests/test_phase16_fleet_priorities.py` | new — 63 tests |
| `progress.md` | updated |
| `handoff.md` | updated |

---

## Limitations and future refinement paths

- **Days window is fixed at 30** (configurable via `?days=N`, range 7–90). Open sessions are always included regardless of age.
- **Asset identity comes from `asset_telemetry.asset_id`** only — sessions not linked to telemetry do not appear in risk scoring. A future migration adding `asset_id` to `diagnostic_sessions` would extend coverage.
- **Service interval is hardcoded at 250h** — different OEMs use 250h (standard), 500h (extended), or 1000h (annual). A per-asset service profile would refine this.
- **Recency weighting** — all sessions in the window are equally weighted regardless of age. Exponential decay or recency multiplier would make recent events more impactful.
- **No site/location filter** — the spec mentioned filtering by site. Site data is not currently stored; it would require an `asset_site` field in heavy_context or a separate asset registry.
