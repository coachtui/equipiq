# Fix — Progress Log

## Phase 16 — Fleet Prioritization Layer (2026-04-07)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| Risk model (pure functions) | `backend/app/fleet/risk_model.py` | ✅ |
| Fleet package init | `backend/app/fleet/__init__.py` | ✅ |
| `/api/fleet/priorities` endpoint | `backend/app/api/fleet.py` | ✅ |
| Frontend: Priority List + filters | `frontend/src/app/fleet/page.tsx` | ✅ |
| Frontend: API client | `frontend/src/lib/fleet.ts` | ✅ |
| Tests | `backend/tests/test_phase16_fleet_priorities.py` | ✅ 63/63 |

### Scoring formula

```
risk_score =
    0.30 × unresolved_score    (open/unresolved sessions, normalized /5)
  + 0.20 × repeat_score        (same symptom repeated, normalized /3 excess)
  + 0.20 × safety_score        (session safety triggers + critical telemetry, normalized /3)
  + 0.15 × contradiction_score (avg contradictions/session, normalized /3)
  + 0.05 × anomaly_score       (anomaly-flagged sessions / total)
  + 0.05 × telematics_score    (readings with abnormal signals, normalized /5)
  + 0.05 × service_score       (binary: 1.0 if >250h since last service)
```

All components clamped [0,1]. Final score clamped [0,1], 4dp.

### Risk levels
- 0.75–1.0 → critical (red)
- 0.50–0.75 → high (orange)
- 0.25–0.50 → medium (yellow)
- 0.00–0.25 → low (green)

### Key design decisions
- No LLM involvement — fully deterministic
- `recommended_action` is rule-based, priority-ordered, traceable to inputs
- DB fetch uses 2 queries (sessions + telemetry) regardless of asset count
- Warning-level telemetry counts as `telematics_score` only; critical counts as `safety_score`
- Service overdue at `hours_of_operation - last_service_hours >= 250`

---

## Phase 12 — Heavy Equipment Completion (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| 4 additional heavy equipment trees | `trees/coolant_leak_heavy_equipment.py`, `implement_failure_heavy_equipment.py`, `cab_electrical_heavy_equipment.py`, `fuel_contamination_heavy_equipment.py` | ✅ |
| Tree registration | `backend/app/engine/trees/__init__.py` | ✅ |
| Session mode | `claude.py`, `sessions.py`, `session.py`, `ChatInterface.tsx` | ✅ |
| HeavyContext intake form | `context_heavy.py`, `sessions.py`, `HeavyEquipmentForm.tsx` | ✅ |
| DB migration | `db/migrations/010_phase12.sql` | ✅ |
| `intake_classify` extended | `backend/app/llm/claude.py` | ✅ |

### Total heavy equipment trees: 11

7 from Phase 11 + 4 from Phase 12. Full symptom coverage:
`no_start`, `hydraulic_loss`, `loss_of_power`, `overheating`, `electrical_fault`, `track_or_drive_issue`, `abnormal_noise`, `coolant_leak`, `implement_failure`, `cab_electrical`, `fuel_contamination`

---

## Phase 10.5 — Learning Intelligence Layer (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| Failure Pattern Analyzer | `backend/app/learning/patterns.py` | ✅ |
| Insight Generator | `backend/app/learning/insights.py` | ✅ |
| Admin endpoint | `backend/app/api/admin.py` (`GET /learning/insights`) | ✅ |
| Tests | `backend/tests/test_phase105.py` | ✅ |

### New capabilities

**Failure Pattern Analyzer (`patterns.py`)** — four analysis functions:
- `detect_weak_hypotheses(metrics)` — deterministic; flags low resolution, high reversal, low rating
- `detect_tree_gaps(tree_performance)` — deterministic; flags trees with high unresolved rate or high contradiction rate
- `detect_anomaly_trends(weekly_data)` — deterministic; detects volume or contradiction spikes vs historical baseline
- `analyze_failure_patterns(outcome_data)` — statistical clustering + optional LLM semantic summary

Three DB fetch helpers: `fetch_outcome_data()`, `fetch_tree_performance()`, `fetch_weekly_trends()`

**Insight Generator (`insights.py`)** — `generate_insights()`:
- LLM synthesises all structured findings into prioritised `{type, title, description, affected, suggested_action, priority}` insights
- Returns empty list on failure; deterministic outputs always available

**Admin endpoint** — `GET /api/admin/learning/insights`:
- `use_llm=true` (default) — full analysis including LLM pattern summaries and insights
- `use_llm=false` — deterministic analysis only (faster, no LLM)
- `data_limit=200` — max outcome rows to analyse

### Guardrails enforced
- No weights, trees, or routing changed by any new code
- LLM outputs are suggestions only — still require admin approval via existing endpoints
- Every LLM call wrapped in try/except; deterministic outputs always returned
- DB fetch functions are read-only

---

## Phase 9.5 — LLM Augmentation Layer (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| Shadow Hypothesis Generator | `backend/app/llm/shadow_hypotheses.py` | ✅ |
| Cross-Tree Routing Hints | `backend/app/llm/routing_hints.py` | ✅ |
| Evidence Extractor | `backend/app/llm/evidence_extractor.py` | ✅ |
| Anomaly Detector | `backend/app/llm/anomaly_detector.py` | ✅ |
| combine_candidates() | `backend/app/diagnostics/orchestrator/tree_router.py` | ✅ |
| DB Migration | `db/migrations/009_llm_augmentation.sql` | ✅ |
| Session Model | `backend/app/models/session.py` (shadow_hypotheses column) | ✅ |
| sessions.py integration | `backend/app/api/sessions.py` | ✅ |
| Tests | `backend/tests/test_phase95.py` | ✅ |

### New capabilities

**Shadow Hypothesis Generator** — LLM proposes up to 3 alternative causes not dominant in the tree. Stored in `shadow_hypotheses` JSONB. Returned in `MessageResponse.shadow_hypotheses` at exit or every 3 turns. Never modifies scores.

**Cross-Tree Routing Hints** — LLM suggests additional candidate trees at session creation. Merged with deterministic candidates via `combine_candidates()`. LLM influence capped at 25%. Deterministic primary always stays dominant.

**Evidence Extractor** — LLM extracts structured observation signals from free-text intake. Added to `evidence_log` as `source="intake"` packets with empty `affects` (no score impact). Enriches contradiction detection and anomaly analysis.

**Anomaly Detector** — Called only when exit guard fires (early exits). If `severity >= 0.6`, suppresses early exit and returns a targeted clarification question. Anomaly stored in `context.last_anomaly` for admin inspection. Falls back to normal exit on LLM failure.

### New DB column
- `diagnostic_sessions.shadow_hypotheses JSONB DEFAULT '[]'`

### New API response field
- `MessageResponse.shadow_hypotheses: list[dict] | None` — populated at exit or every 3 turns

### Guardrails enforced
- All four LLM functions wrapped in try/except — system operates identically if any fail
- LLM never sets final scores, never bypasses tree scoring
- Shadow hypotheses are advisory alternatives, not diagnoses
- Anomaly suppression only on early exits (not tree-exhausted, not max-turn exits)
- LLM routing influence capped at 25%; deterministic primary cannot be displaced by LLM alone

---

## Phase 11 — Heavy Equipment Domain Expansion (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| no_start tree | `engine/trees/no_start_heavy_equipment.py` | ✅ |
| hydraulic_loss tree | `engine/trees/hydraulic_loss_heavy_equipment.py` | ✅ |
| loss_of_power tree | `engine/trees/loss_of_power_heavy_equipment.py` | ✅ |
| overheating tree | `engine/trees/overheating_heavy_equipment.py` | ✅ |
| electrical_fault tree | `engine/trees/electrical_fault_heavy_equipment.py` | ✅ |
| track_or_drive_issue tree | `engine/trees/track_or_drive_issue_heavy_equipment.py` | ✅ |
| abnormal_noise tree | `engine/trees/abnormal_noise_heavy_equipment.py` | ✅ |
| HeavyContext priors | `engine/context_heavy.py` | ✅ |
| Evidence source expansion | `orchestrator/evidence.py` | ✅ |
| Safety pattern expansion | `orchestrator/safety.py` | ✅ |
| SessionState session_mode | `orchestrator/controller.py` | ✅ |
| Ambiguous pairs (router) | `orchestrator/tree_router.py` | ✅ |
| Tree registration | `engine/trees/__init__.py` | ✅ |

### Notes
- 7 new trees, operator-friendly language, "not sure" options on all nodes
- Hours-based context priors (vs mileage-based for passenger vehicles)
- 8 new safety patterns including hydraulic injection injury
- Future stubs in place: telematics hook, maintenance log hook, sensor feed evidence
- No database migrations required

---

## Phase 10 — Learning System (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| DB Migration | `db/migrations/008_learning_system.sql` | ✅ |
| ORM Models | `backend/app/models/session.py` (DiagnosticOutcome, ApprovedWeightAdjustment) | ✅ |
| Outcome Recording | `backend/app/learning/outcomes.py` | ✅ |
| Performance Metrics | `backend/app/learning/metrics.py` | ✅ |
| Adjustment Engine | `backend/app/learning/adjustments.py` | ✅ |
| Approved Weights Store | `backend/app/learning/weights.py` | ✅ |
| Admin Learning Endpoints | `backend/app/api/admin.py` (4 new routes) | ✅ |
| Runtime Weight Application | `backend/app/engine/hypothesis_scorer.py` | ✅ |
| sessions.py integration | `backend/app/api/sessions.py` | ✅ |
| Tests | `backend/tests/test_learning.py` | ✅ |

### New DB tables
- `diagnostic_outcomes` — per-session outcome record (top hypothesis, resolution, rating, evidence summary)
- `approved_weight_adjustments` — admin-approved multipliers applied to hypothesis priors

### New admin API endpoints
- `GET /api/admin/learning/metrics` — raw per-hypothesis performance metrics
- `GET /api/admin/learning/adjustments` — suggested adjustments with context + sample sessions
- `POST /api/admin/learning/adjustments/{hypothesis_id}/approve` — approve with explicit multiplier
- `POST /api/admin/learning/adjustments/{hypothesis_id}/reject` — remove approval (revert to 1.0)

### How learning works
```
session exits → record_outcome() → diagnostic_outcomes row
user rates    → update_outcome_feedback() → was_resolved + rating added
admin views   → GET /admin/learning/adjustments → compute_hypothesis_metrics() + generate_adjustments()
admin approves → POST .../approve → approved_weight_adjustments row
new session   → get_approved_multipliers() → HypothesisScorer(multipliers=...) → priors adjusted
```

### Guardrails enforced
- No auto-adjustment in production — admin approval required before any multiplier is active
- LLM cannot change weights
- Scoring remains deterministic (same session always produces same result)
- Multipliers applied to priors at session creation only; in-progress sessions unaffected
- Multipliers clamped to [0.5, 2.0]

---

## Phase 9 — Diagnostic Orchestration Layer (2026-04-06)

**Status: COMPLETE**

### Deliverables

| Component | File | Status |
|---|---|---|
| DB Migration | `db/migrations/007_orchestration.sql` | ✅ |
| Evidence Engine | `backend/app/diagnostics/orchestrator/evidence.py` | ✅ |
| Tree Candidate Ranking | `backend/app/diagnostics/orchestrator/tree_router.py` | ✅ |
| Discriminator Questions | `backend/app/diagnostics/orchestrator/discriminator.py` | ✅ |
| Early Exit Guard | `backend/app/diagnostics/orchestrator/exit_guard.py` | ✅ |
| Contradiction Detection | `backend/app/diagnostics/orchestrator/contradictions.py` | ✅ |
| Safety Interruption | `backend/app/diagnostics/orchestrator/safety.py` | ✅ |
| Orchestrator Controller | `backend/app/diagnostics/orchestrator/controller.py` | ✅ |
| classify_answer reliability | `backend/app/llm/claude.py` | ✅ |
| Session model new columns | `backend/app/models/session.py` | ✅ |
| sessions.py integration | `backend/app/api/sessions.py` | ✅ |
| Tests | `backend/tests/test_orchestrator.py` | ✅ |

### New DB columns on `diagnostic_sessions`
- `routing_phase TEXT DEFAULT 'committed'`
- `selected_tree TEXT`
- `evidence_log JSONB DEFAULT '[]'`
- `contradiction_flags JSONB DEFAULT '[]'`
- `safety_flags JSONB DEFAULT '[]'`

### New API response fields
- `MessageResponse.safety_alerts: list[dict] | None` — populated when safety interrupt fires
- `MessageResponse.msg_type` now also uses `"safety"` and `"clarify"` values

---

## Phase 7 — All Complete (2026-04-06)
- 7B: Production hardening
- 7A: User accounts + auth
- 7E: Deeper tree quality (POST_DIAGNOSIS, context priors)
- 7D: ATV/UTV (7) + PWC (6) trees = 49 total
- 7C: Admin dashboard

## Phase 8 — In Progress (separate session)
- 8A: Brakes system trees
- 8B: Transmission system trees
- 8C: HVAC system trees (deferred)
- 8D: Suspension system trees
- Trees added: brakes, transmission, suspension, hvac (base car)

## Phase 1–6 — Complete
See git history.
