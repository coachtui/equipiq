-- Phase 10: Learning System
-- Adds outcome tracking and admin-reviewed weight adjustment tables.
-- Learning is offline and controlled — no auto-mutations in production.

-- ── Outcome tracking ─────────────────────────────────────────────────────────

CREATE TABLE diagnostic_outcomes (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                      UUID NOT NULL UNIQUE
                                        REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    selected_tree                   TEXT,
    final_hypotheses                JSONB NOT NULL DEFAULT '[]',
    top_hypothesis                  TEXT,
    was_resolved                    BOOLEAN,               -- NULL until feedback submitted
    resolution_confirmed_hypothesis TEXT,                  -- NULL if not confirmed or not resolved
    rating                          INTEGER CHECK (rating BETWEEN 1 AND 5),
    evidence_summary                JSONB NOT NULL DEFAULT '{}',
    contradiction_count             INTEGER NOT NULL DEFAULT 0,
    safety_triggered                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_diagnostic_outcomes_top_hypothesis ON diagnostic_outcomes(top_hypothesis);
CREATE INDEX idx_diagnostic_outcomes_selected_tree  ON diagnostic_outcomes(selected_tree);
CREATE INDEX idx_diagnostic_outcomes_was_resolved   ON diagnostic_outcomes(was_resolved);

-- ── Approved weight adjustments ───────────────────────────────────────────────

CREATE TABLE approved_weight_adjustments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id TEXT NOT NULL UNIQUE,
    multiplier    FLOAT NOT NULL CHECK (multiplier BETWEEN 0.5 AND 2.0),
    approved_by   TEXT,          -- admin user email or ID
    approved_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
