-- Engine/Drivetrain AI Diagnostic System — V1 Schema

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Diagnostic sessions (one per user conversation)
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'complete', 'abandoned')),
  turn_count       INT  NOT NULL DEFAULT 0,
  -- Vehicle info (extracted from intake or prompted)
  vehicle_year     INT,
  vehicle_make     TEXT,
  vehicle_model    TEXT,
  vehicle_engine   TEXT,
  -- Diagnostic state
  symptom_category TEXT
                     CHECK (symptom_category IN (
                       'no_crank', 'crank_no_start', 'rough_idle',
                       'loss_of_power', 'strange_noise', 'visible_leak'
                     )),
  initial_description TEXT,
  current_node_id  TEXT,   -- active position in diagnostic tree
  context          JSONB NOT NULL DEFAULT '{}'
);

-- Every message exchanged in the session
CREATE TABLE IF NOT EXISTS session_messages (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content    TEXT NOT NULL,
  msg_type   TEXT NOT NULL DEFAULT 'chat'
               CHECK (msg_type IN ('chat', 'question', 'result'))
);

CREATE INDEX IF NOT EXISTS idx_session_messages_session_id
  ON session_messages (session_id, created_at);

-- Scored hypotheses, updated after each answer
CREATE TABLE IF NOT EXISTS session_hypotheses (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  hypothesis_key TEXT NOT NULL,
  score          FLOAT NOT NULL DEFAULT 0.0 CHECK (score >= 0 AND score <= 1),
  eliminated     BOOLEAN NOT NULL DEFAULT false,
  evidence       JSONB NOT NULL DEFAULT '[]',
  UNIQUE (session_id, hypothesis_key)
);

CREATE INDEX IF NOT EXISTS idx_session_hypotheses_session_id
  ON session_hypotheses (session_id);

-- Final result written when session completes
CREATE TABLE IF NOT EXISTS diagnostic_results (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id          UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  ranked_causes       JSONB NOT NULL,   -- [{cause, confidence, reasoning}]
  next_checks         JSONB NOT NULL,   -- [string]
  diy_difficulty      TEXT CHECK (diy_difficulty IN ('easy', 'moderate', 'hard', 'seek_mechanic')),
  suggested_parts     JSONB NOT NULL DEFAULT '[]',  -- [{name, notes}]
  escalation_guidance TEXT,
  confidence_level    FLOAT CHECK (confidence_level >= 0 AND confidence_level <= 1)
);

-- Media attachments — schema present in V1, used in Phase 2
CREATE TABLE IF NOT EXISTS media_attachments (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id          UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  file_type           TEXT NOT NULL CHECK (file_type IN ('image', 'video')),
  storage_path        TEXT NOT NULL,
  vision_analysis     JSONB,
  confidence_modifier FLOAT NOT NULL DEFAULT 0.0
);

-- Auto-update updated_at on diagnostic_sessions
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_diagnostic_sessions_updated_at
  BEFORE UPDATE ON diagnostic_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_session_hypotheses_updated_at
  BEFORE UPDATE ON session_hypotheses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
