-- Migration 003: session_feedback table, expand symptom_category CHECK,
--               fix msg_type CHECK (latent bug: 'image' was written but not allowed)

-- 1. session_feedback: one rating per session (upsert-friendly)
CREATE TABLE IF NOT EXISTS session_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
  rating      INT  NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS idx_session_feedback_session_id
  ON session_feedback (session_id);

-- 2. Expand symptom_category CHECK to include the two new trees
ALTER TABLE diagnostic_sessions
  DROP CONSTRAINT IF EXISTS diagnostic_sessions_symptom_category_check;

ALTER TABLE diagnostic_sessions
  ADD CONSTRAINT diagnostic_sessions_symptom_category_check
  CHECK (symptom_category IN (
    'no_crank', 'crank_no_start', 'rough_idle',
    'loss_of_power', 'strange_noise', 'visible_leak',
    'overheating', 'check_engine_light'
  ));

-- 3. Fix latent bug: msg_type='image' is written by the backend but was
--    missing from the original CHECK constraint
ALTER TABLE session_messages
  DROP CONSTRAINT IF EXISTS session_messages_msg_type_check;

ALTER TABLE session_messages
  ADD CONSTRAINT session_messages_msg_type_check
  CHECK (msg_type IN ('chat', 'question', 'result', 'image'));
