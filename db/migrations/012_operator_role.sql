-- Migration 012: Add is_operator role to users
-- Phase 15D — Fleet operator dashboard requires a distinct operator role
-- separate from is_admin. Operators can view fleet data but cannot access
-- admin intelligence, learning adjustments, or system configuration.

ALTER TABLE users
    ADD COLUMN is_operator BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.is_operator IS 'True for fleet operators who can access /api/fleet/ endpoints';
