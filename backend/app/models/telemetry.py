"""
Asset Telemetry ORM model — Phase 13C.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import ARRAY, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AssetTelemetry(Base):
    """
    Raw + normalized sensor reading from a field asset.

    Populated by the telematics ingest endpoint.  Linked to a diagnostic
    session when one is active for the asset at ingest time.
    """
    __tablename__ = "asset_telemetry"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    asset_id: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    telemetry_ts: Mapped[datetime] = mapped_column(nullable=False)

    # Raw sensor values (all optional — partial payloads accepted)
    engine_temp_c: Mapped[float | None] = mapped_column(Numeric)
    voltage_v: Mapped[float | None] = mapped_column(Numeric)
    pressure_psi: Mapped[float | None] = mapped_column(Numeric)
    fuel_level_pct: Mapped[float | None] = mapped_column(Numeric)
    fault_codes: Mapped[list] = mapped_column(ARRAY(Text), default=list)

    # Derived from normalization
    normalized_signals: Mapped[list] = mapped_column(JSONB, default=list)
    safety_alerts: Mapped[list] = mapped_column(JSONB, default=list)

    # Optional session linkage
    linked_session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("diagnostic_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_asset_telemetry_asset_received", "asset_id", "received_at"),
        Index("idx_asset_telemetry_session", "linked_session_id"),
        Index("idx_asset_telemetry_received", "received_at"),
    )
