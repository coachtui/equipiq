-- Migration 004: add vehicle_type column to diagnostic_sessions
--               drop symptom_category CHECK constraint (app-level validation is authoritative)

ALTER TABLE diagnostic_sessions
  ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR(32) NOT NULL DEFAULT 'car';

-- Drop the CHECK constraint — it has been manually updated twice already (001, 003)
-- and will need to change every time a new tree is added. The TREES registry in
-- trees/__init__.py is the authoritative list. The `if symptom_category not in TREES`
-- guard in sessions.py already handles unknown categories gracefully.
ALTER TABLE diagnostic_sessions
  DROP CONSTRAINT IF EXISTS diagnostic_sessions_symptom_category_check;
