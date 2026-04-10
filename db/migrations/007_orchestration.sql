-- Phase 9: Diagnostic Orchestration Layer
-- Adds session-level routing state, structured evidence log, contradiction flags, and safety flags.

ALTER TABLE diagnostic_sessions
    ADD COLUMN IF NOT EXISTS routing_phase TEXT NOT NULL DEFAULT 'committed',
    ADD COLUMN IF NOT EXISTS selected_tree  TEXT,
    ADD COLUMN IF NOT EXISTS evidence_log   JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS contradiction_flags JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS safety_flags   JSONB NOT NULL DEFAULT '[]';

-- Back-fill selected_tree for existing sessions using the stored tree_key in context
UPDATE diagnostic_sessions
SET selected_tree = context->>'tree_key'
WHERE selected_tree IS NULL
  AND context ? 'tree_key';
