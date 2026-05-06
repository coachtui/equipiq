-- Migration 013: Partner auth — let trusted external platforms (e.g. BedrockOS)
-- create users in Fix on behalf of their own users without sharing passwords.
--
-- A partner user is identified by (partner_id, partner_user_id).
-- - partner_id is the external platform name (e.g. "bedrock")
-- - partner_user_id is the user's ID inside that platform (e.g. a Supabase user UUID)
-- - partner_org_id is the external org for scoping (optional)
--
-- Email is auto-synthesized for partner users so the email NOT NULL constraint stays.
-- password_hash is NULL for partner users — they cannot log in via Fix's own login.

ALTER TABLE users
    ADD COLUMN partner_id      TEXT,
    ADD COLUMN partner_user_id TEXT,
    ADD COLUMN partner_org_id  TEXT;

ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- A given external user can only be linked once
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_partner
    ON users (partner_id, partner_user_id)
    WHERE partner_id IS NOT NULL;

-- Index for fast lookup by partner org (e.g. fleet views scoped to a customer)
CREATE INDEX IF NOT EXISTS idx_users_partner_org
    ON users (partner_org_id)
    WHERE partner_org_id IS NOT NULL;

COMMENT ON COLUMN users.partner_id      IS 'External platform name when user was provisioned via partner API. NULL for native Fix users.';
COMMENT ON COLUMN users.partner_user_id IS 'User ID in the partner platform. Combined with partner_id for unique lookup.';
COMMENT ON COLUMN users.partner_org_id  IS 'Org/tenant ID in the partner platform. Used for cross-customer scoping.';
