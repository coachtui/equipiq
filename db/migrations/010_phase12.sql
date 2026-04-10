-- Phase 12 — Heavy Equipment Session Support
-- Adds session_mode and heavy_context columns to diagnostic_sessions.

ALTER TABLE diagnostic_sessions
    ADD COLUMN IF NOT EXISTS session_mode VARCHAR(20) NOT NULL DEFAULT 'consumer';

ALTER TABLE diagnostic_sessions
    ADD COLUMN IF NOT EXISTS heavy_context JSONB NOT NULL DEFAULT '{}';

COMMENT ON COLUMN diagnostic_sessions.session_mode IS
    'Phase 12: Interaction mode for this session — consumer, mechanic, or operator. '
    'Affects rephrase_question tone. Default is consumer.';

COMMENT ON COLUMN diagnostic_sessions.heavy_context IS
    'Phase 12: HeavyContext fields for heavy_equipment sessions — '
    'hours_of_operation, last_service_hours, environment, storage_duration, recent_work_type. '
    'Empty object for non-heavy-equipment sessions.';
