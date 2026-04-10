# Fix — Diagnostic Platform Engineering Standards

This project is a **diagnostic platform with orchestration, evidence control, and safety-aware decision flow** — not a simple tree-based chat app. All engineering work follows these standards.

---

## Architecture

```
UI/chat layer
→ orchestration layer
→ deterministic tree engine
→ result synthesis
```

All new diagnostic features route through the orchestration layer. No shortcut paths that bypass orchestration.

- Routing logic → orchestrator
- Evidence normalized before scoring
- Contradictions checked before exit
- Safety checked in parallel
- Exit conditions centrally gated

---

## Deterministic Core

LLM assists. It does not score.

| LLM may | LLM must not |
|---|---|
| classify intake language | determine final diagnosis scores |
| rephrase questions | replace tree scoring logic |
| normalize free-text answers | become the hidden reasoning engine |
| summarize results | |

LLM outputs feed the engine as structured evidence or routing hints — not opaque diagnosis outputs.

Current LLM functions: `intake_classify`, `rephrase_question`, `classify_answer`, `synthesize_result`, `interpret_followup`, `analyze_image`, `lookup_obd_code`. Do not add new LLM functions without explicit approval.

---

## Tree Development

Trees stay in Python code (`backend/app/engine/trees/`).

Every tree must have all four exports: `{SYMPTOM}_TREE`, `{SYMPTOM}_HYPOTHESES`, `{SYMPTOM}_CONTEXT_PRIORS`, `{SYMPTOM}_POST_DIAGNOSIS`.

Trees should evolve toward containing:
- metadata, entry conditions, hypotheses, priors
- nodes, transitions, reroute hooks
- post-diagnosis tips, safety hooks
- evidence category requirements

Do not create one-off tree logic that can't be inspected or extended.

---

## Orchestration-First Checklist

Before changing a tree, ask in order:
1. Is this a routing problem?
2. Is this an evidence normalization problem?
3. Is this a contradiction problem?
4. Is this an exit-confidence problem?
5. Is this a safety problem?
6. Only then: is this a tree-content problem?

Fix orchestration failures in the orchestrator. Do not solve them by stuffing trees with more content.

---

## Evidence Standard

Evidence sources: user text, image, video frame, OBD code, manual test result, future sensor input, technician observations.

All inputs must be designed to normalize into structured evidence packets:
1. Normalize input
2. Store evidence packet
3. Apply deterministic effect
4. Log impact

No isolated scoring hacks for specific features.

---

## Confidence Standard

Confidence must be earned. No feature increases exit aggressiveness without considering:
- Evidence diversity
- Answer reliability
- Contradictions
- Safety flags
- Minimum question depth

Favor honest uncertainty and recoverable flow over fast but brittle certainty.

---

## Contradiction Handling

Contradictions are a first-class system condition.
- Detect explicitly
- Suppress premature conclusions
- Trigger clarification or rerouting
- Make contradiction state inspectable in admin/debug flows

Do not bury conflicting signals inside score math alone.

---

## Safety Standard

Safety logic runs in parallel with diagnostic logic. Every domain expansion must define:
- Warning conditions
- Critical-stop conditions
- User-facing interruption behavior
- Acknowledgment flow if continuation is allowed

Mandatory for: passenger vehicles, motorcycles, marine, generators, heavy equipment, construction equipment.

---

## Extensibility

Evaluate all new work against future expansion into:
- Brakes, transmission, HVAC, suspension (in progress — Phase 8)
- Heavy equipment (construction, agricultural, industrial)
- Operator-guided troubleshooting
- Mechanic-assisted workflows
- Fleet/failure pattern intelligence

Build so today's code supports tomorrow's domains.

---

## Analytics Preservation

Preserve the ability to capture per-session:
- Selected tree, top hypotheses, evidence trail
- Contradictions, safety alerts, follow-up findings
- Resolved/unresolved outcomes, user rating

Do not build features that reduce auditability.

---

## Code Review Checklist

Stop and redesign if any answer is yes:
- [ ] Does it bypass orchestration?
- [ ] Does it add opaque scoring?
- [ ] Does it reduce explainability?
- [ ] Does it weaken determinism?
- [ ] Does it avoid evidence normalization?
- [ ] Does it ignore contradiction handling?
- [ ] Does it skip safety review?
- [ ] Does it make heavy-equipment expansion harder?

---

## Known Rules (Do Not Violate)

- `from __future__ import annotations` must NOT appear in FastAPI route files that use `@limiter.limit()` — causes slowapi decorator wrapping to break FastAPI's type resolution (discovered Phase 7B)
- `bcrypt` must be pinned to `==4.0.1` when using `passlib[bcrypt]==1.7.4` — bcrypt 5.x breaks passlib's API (discovered Phase 7A)
- Session endpoints return 404, not 403, for wrong-user access — prevents session ID enumeration
- `classify_answer` returns a dict `{option_key, classification_confidence, answer_reliability, needs_clarification}` — not a plain string (changed Phase 9)
- LLM score deltas from `classify_answer` feed the hypothesis scorer; they do not replace it
- Hypothesis scores clamp to [0, 1], never normalized — absolute confidence signal must be preserved
- Early exit: governed by `exit_guard.can_exit()` — requires top score >= 0.75, lead >= 0.20, answered_nodes >= 3, evidence_types >= 2, no blocking contradictions. Do not bypass with direct `should_exit_early()` calls.

---

## Stack Reference

- Frontend: Next.js 14 App Router, TypeScript, Tailwind — `/fix/frontend`
- Backend: FastAPI Python 3.12 — `/fix/backend`
- Database: PostgreSQL — schema in `/fix/db/migrations/`
- AI: `claude-sonnet-4-6`
- Local dev: Docker Compose at `/fix/docker-compose.yml`

## Permanent Principle

The goal is not to feel more "AI." The goal is to be more correct, resilient, inspectable, safety-aware, extensible, and useful in real diagnostic conditions.

Favor operational truth over novelty.
