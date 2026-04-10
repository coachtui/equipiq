-- Phase 9.5 — LLM Augmentation Layer
-- Adds shadow_hypotheses column to store LLM-proposed alternative hypotheses.

ALTER TABLE diagnostic_sessions
    ADD COLUMN IF NOT EXISTS shadow_hypotheses JSONB NOT NULL DEFAULT '[]';

COMMENT ON COLUMN diagnostic_sessions.shadow_hypotheses IS
    'Phase 9.5: LLM-generated alternative hypotheses not dominant in the tree. '
    'Advisory only — never modifies scores. Populated at exit or every 3 turns.';
