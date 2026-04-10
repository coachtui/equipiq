-- Add awaiting_followup to the session status enum
-- The initial schema only had: active, complete, abandoned

ALTER TABLE diagnostic_sessions
  DROP CONSTRAINT diagnostic_sessions_status_check;

ALTER TABLE diagnostic_sessions
  ADD CONSTRAINT diagnostic_sessions_status_check
  CHECK (status IN ('active', 'awaiting_followup', 'complete', 'abandoned'));

-- Add unique constraint on diagnostic_results.session_id so follow-up
-- re-synthesises can upsert rather than inserting duplicate result rows
ALTER TABLE diagnostic_results
  ADD CONSTRAINT diagnostic_results_session_id_key UNIQUE (session_id);
