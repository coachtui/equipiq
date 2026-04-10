-- Phase 13C — Telematics Hook (Sensor Evidence)
-- Stores raw machine telemetry readings, normalized evidence signals,
-- and safety alerts derived from sensor data.  Optionally linked to an
-- active diagnostic session.

CREATE TABLE IF NOT EXISTS asset_telemetry (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id        TEXT        NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    telemetry_ts    TIMESTAMPTZ NOT NULL,

    -- Raw sensor fields (all nullable — ingest accepts partial payloads)
    engine_temp_c   NUMERIC,            -- engine coolant temperature, Celsius
    voltage_v       NUMERIC,            -- system voltage, Volts
    pressure_psi    NUMERIC,            -- hydraulic / system pressure, PSI
    fuel_level_pct  NUMERIC,            -- fuel level, 0–100 %
    fault_codes     TEXT[]  NOT NULL DEFAULT '{}',  -- CAN / OBD fault code strings

    -- Derived from normalization
    normalized_signals  JSONB NOT NULL DEFAULT '[]',  -- list of EvidencePacket dicts
    safety_alerts       JSONB NOT NULL DEFAULT '[]',  -- list of SafetyAlert dicts

    -- Optional session linkage (SET NULL when session deleted)
    linked_session_id   UUID REFERENCES diagnostic_sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_asset_telemetry_asset_received
    ON asset_telemetry (asset_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_asset_telemetry_session
    ON asset_telemetry (linked_session_id)
    WHERE linked_session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_asset_telemetry_received
    ON asset_telemetry (received_at DESC);

COMMENT ON TABLE asset_telemetry IS
    'Phase 13C: Machine sensor telemetry ingested from field assets. '
    'Raw values are stored alongside normalized EvidencePackets and safety alerts. '
    'Linked to a diagnostic session when one is active for the asset.';

COMMENT ON COLUMN asset_telemetry.normalized_signals IS
    'Normalized EvidencePacket dicts derived from the raw sensor values. '
    'source=sensor_future. Applied to the linked session evidence_log if session is active.';

COMMENT ON COLUMN asset_telemetry.safety_alerts IS
    'SafetyAlert dicts raised from numeric threshold evaluation of sensor values. '
    'Critical alerts are pushed to linked session safety_flags.';
