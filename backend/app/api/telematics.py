"""
Telematics ingest and query API — Phase 13C.

Endpoints:
  POST /api/telematics/ingest            — accept sensor payload, normalize, store
  GET  /api/telematics/asset/{asset_id}  — recent readings for an asset

No rate limiter on these endpoints (machine-to-machine).
Authentication: API key check (same admin key) for ingest; admin user for query.

NOTE: from __future__ import annotations intentionally omitted here.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_admin_user
from app.models.telemetry import AssetTelemetry
from app.telematics.ingestor import (
    describe_normalization,
    normalize_telemetry,
    parse_payload,
    validate_payload,
)

router = APIRouter(prefix="/api/telematics", tags=["telematics"])


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/ingest")
async def ingest_telemetry(
    payload: dict,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Accept a sensor telemetry payload from a field asset.

    Flow:
      1. Validate fields and ranges
      2. Normalize to EvidencePackets + SafetyAlerts
      3. Resolve session linkage (explicit session_id, or lookup by asset_id)
      4. Persist to asset_telemetry table
      5. If linked to active session: append evidence + safety flags
      6. Return telemetry_id, signals fired, safety alerts, and linkage info

    Body (all fields except asset_id + timestamp are optional):
    {
        "asset_id":       "CAT-336-001",
        "timestamp":      "2026-04-06T10:30:00Z",
        "engine_temp_c":  102.5,
        "voltage_v":      13.8,
        "pressure_psi":   2950,
        "fuel_level_pct": 45.0,
        "fault_codes":    ["P0192"],
        "session_id":     "optional-uuid"
    }
    """
    # ── 1. Validate ───────────────────────────────────────────────────────────
    validation = validate_payload(payload)
    if not validation.valid:
        raise HTTPException(status_code=422, detail={"errors": validation.errors})

    # ── 2. Parse + normalize ──────────────────────────────────────────────────
    parsed = parse_payload(payload)
    result = normalize_telemetry(parsed)

    # ── 3. Resolve session linkage ────────────────────────────────────────────
    linked_session_id: str | None = None
    session_evidence_applied = False

    if parsed.session_id:
        # Explicit session_id provided — verify it exists and is heavy_equipment
        row = await db.execute(text("""
            SELECT id, vehicle_type, status
            FROM diagnostic_sessions
            WHERE id = :sid
        """), {"sid": parsed.session_id})
        sess = row.mappings().one_or_none()
        if sess and sess["vehicle_type"] == "heavy_equipment" and sess["status"] == "active":
            linked_session_id = str(sess["id"])
    else:
        # Auto-link: find the most recent active heavy_equipment session for this asset
        row = await db.execute(text("""
            SELECT id, evidence_log, safety_flags
            FROM diagnostic_sessions
            WHERE vehicle_type = 'heavy_equipment'
              AND status = 'active'
              AND heavy_context->>'asset_id' = :asset_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {"asset_id": parsed.asset_id})
        sess = row.mappings().one_or_none()
        if sess:
            linked_session_id = str(sess["id"])

    # ── 4. Persist telemetry reading ──────────────────────────────────────────
    reading = AssetTelemetry(
        asset_id=parsed.asset_id,
        telemetry_ts=parsed.timestamp,
        engine_temp_c=parsed.engine_temp_c,
        voltage_v=parsed.voltage_v,
        pressure_psi=parsed.pressure_psi,
        fuel_level_pct=parsed.fuel_level_pct,
        fault_codes=parsed.fault_codes,
        normalized_signals=[p.to_dict() for p in result.normalized_signals],
        safety_alerts=[a.to_dict() for a in result.safety_alerts],
        linked_session_id=linked_session_id,
    )
    db.add(reading)

    # ── 5. Apply to active session (if linked) ────────────────────────────────
    if linked_session_id and result.normalized_signals:
        # Load current session state
        sess_row = await db.execute(text("""
            SELECT evidence_log, safety_flags
            FROM diagnostic_sessions
            WHERE id = :sid
        """), {"sid": linked_session_id})
        sess_data = sess_row.mappings().one_or_none()

        if sess_data:
            new_evidence = list(sess_data["evidence_log"] or [])
            for pkt in result.normalized_signals:
                new_evidence.append(pkt.to_dict())

            new_safety = list(sess_data["safety_flags"] or [])
            existing_messages = {f.get("message") for f in new_safety}
            for alert in result.safety_alerts:
                if alert.message not in existing_messages:
                    new_safety.append(alert.to_dict())
                    existing_messages.add(alert.message)

            await db.execute(text("""
                UPDATE diagnostic_sessions
                SET evidence_log = :evidence,
                    safety_flags  = :safety,
                    updated_at    = NOW()
                WHERE id = :sid
            """), {
                "evidence": new_evidence,
                "safety":   new_safety,
                "sid":      linked_session_id,
            })
            session_evidence_applied = True

    await db.commit()
    await db.refresh(reading)

    return {
        "telemetry_id":            reading.id,
        "asset_id":                parsed.asset_id,
        "received_at":             reading.received_at.isoformat(),
        "signal_names":            result.signal_names,
        "evidence_packets":        len(result.normalized_signals),
        "safety_alerts":           [a.to_dict() for a in result.safety_alerts],
        "has_critical":            any(a.level == "critical" for a in result.safety_alerts),
        "linked_session_id":       linked_session_id,
        "session_evidence_applied": session_evidence_applied,
    }


# ── Asset query ───────────────────────────────────────────────────────────────

@router.get("/asset/{asset_id}")
async def get_asset_telemetry(
    asset_id: str,
    limit: int = 20,
    _: CurrentUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return recent telemetry readings for a specific asset.

    Includes raw values, normalized signals, safety alerts, and session linkage.
    Ordered by most recent first.
    """
    rows = await db.execute(text("""
        SELECT
            id, asset_id, received_at, telemetry_ts,
            engine_temp_c, voltage_v, pressure_psi, fuel_level_pct, fault_codes,
            normalized_signals, safety_alerts, linked_session_id
        FROM asset_telemetry
        WHERE asset_id = :asset_id
        ORDER BY received_at DESC
        LIMIT :limit
    """), {"asset_id": asset_id, "limit": limit})

    readings = [
        {
            "telemetry_id":       r["id"],
            "asset_id":           r["asset_id"],
            "received_at":        r["received_at"].isoformat() if r["received_at"] else None,
            "telemetry_ts":       r["telemetry_ts"].isoformat() if r["telemetry_ts"] else None,
            "raw": {
                "engine_temp_c":   float(r["engine_temp_c"]) if r["engine_temp_c"] is not None else None,
                "voltage_v":       float(r["voltage_v"]) if r["voltage_v"] is not None else None,
                "pressure_psi":    float(r["pressure_psi"]) if r["pressure_psi"] is not None else None,
                "fuel_level_pct":  float(r["fuel_level_pct"]) if r["fuel_level_pct"] is not None else None,
                "fault_codes":     r["fault_codes"] or [],
            },
            "normalized_signals":  r["normalized_signals"] or [],
            "safety_alerts":       r["safety_alerts"] or [],
            "has_critical":        any(a.get("level") == "critical" for a in (r["safety_alerts"] or [])),
            "linked_session_id":   r["linked_session_id"],
        }
        for r in rows.mappings()
    ]

    return {
        "asset_id":    asset_id,
        "count":       len(readings),
        "readings":    readings,
    }
