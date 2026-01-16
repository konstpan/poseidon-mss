"""RiskAlert model for security alerts and risk events."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.alert_acknowledgment import AlertAcknowledgment
    from app.models.geofenced_zone import GeofencedZone
    from app.models.vessel import Vessel


class RiskAlert(Base):
    """Risk alert model for security events and notifications."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_alert_type", "alert_type"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_vessel_mmsi", "vessel_mmsi"),
        Index("ix_alerts_created_at", "created_at", postgresql_using="btree"),
        Index("ix_alerts_position", "position", postgresql_using="gist"),
        {"schema": "security"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Alert classification
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Alert types: zone_entry, zone_exit, speed_violation, ais_gap,
    #              dark_vessel, collision_risk, suspicious_behavior,
    #              anchor_dragging, route_deviation, port_approach

    # Severity level
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info",
    )
    # Severity levels: info, warning, alert, critical

    # Alert status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    # Status: active, acknowledged, resolved, dismissed, escalated

    # Alert message
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Primary vessel involved
    vessel_mmsi: Mapped[Optional[str]] = mapped_column(
        String(9),
        ForeignKey("ais.vessels.mmsi", ondelete="SET NULL"),
        nullable=True,
    )

    # Secondary vessel (for collision risks, etc.)
    secondary_vessel_mmsi: Mapped[Optional[str]] = mapped_column(
        String(9),
        ForeignKey("ais.vessels.mmsi", ondelete="SET NULL"),
        nullable=True,
    )

    # Related zone
    zone_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security.zones.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Position where alert occurred (PostGIS geography point)
    position: Mapped[Optional[bytes]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)

    # Alert details (JSONB for flexible storage)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    # Example details for zone_entry:
    # {
    #     "zone_name": "Port of Thessaloniki",
    #     "vessel_speed": 12.5,
    #     "vessel_course": 180.5,
    #     "zone_security_level": 3,
    #     "previous_position": {"lat": 40.123, "lon": 22.456},
    #     "entry_point": {"lat": 40.234, "lon": 22.567}
    # }

    # Risk score associated with this alert (0-100)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Acknowledgment fields
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acknowledgment_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution fields
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Alert expiry (for auto-dismissing old alerts)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    vessel: Mapped[Optional["Vessel"]] = relationship(
        "Vessel",
        back_populates="alerts",
        foreign_keys=[vessel_mmsi],
    )
    secondary_vessel: Mapped[Optional["Vessel"]] = relationship(
        "Vessel",
        foreign_keys=[secondary_vessel_mmsi],
    )
    zone: Mapped[Optional["GeofencedZone"]] = relationship(
        "GeofencedZone",
        back_populates="alerts",
    )
    acknowledgments: Mapped[list["AlertAcknowledgment"]] = relationship(
        "AlertAcknowledgment",
        back_populates="alert",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RiskAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"

    @property
    def severity_level(self) -> int:
        """Return numeric severity level for sorting."""
        levels = {"info": 1, "warning": 2, "alert": 3, "critical": 4}
        return levels.get(self.severity, 0)

    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.status == "active" and not self.resolved

    @property
    def alert_type_text(self) -> str:
        """Return human-readable alert type."""
        types = {
            "zone_entry": "Zone Entry",
            "zone_exit": "Zone Exit",
            "speed_violation": "Speed Violation",
            "ais_gap": "AIS Signal Gap",
            "dark_vessel": "Dark Vessel Detected",
            "collision_risk": "Collision Risk",
            "suspicious_behavior": "Suspicious Behavior",
            "anchor_dragging": "Anchor Dragging",
            "route_deviation": "Route Deviation",
            "port_approach": "Port Approach",
        }
        return types.get(self.alert_type, self.alert_type.replace("_", " ").title())

    def acknowledge(self, user: str, notes: Optional[str] = None) -> None:
        """Mark the alert as acknowledged."""
        self.acknowledged = True
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user
        self.acknowledgment_notes = notes
        self.status = "acknowledged"
        self.updated_at = datetime.utcnow()

    def resolve(self, user: str, notes: Optional[str] = None) -> None:
        """Mark the alert as resolved."""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user
        self.resolution_notes = notes
        self.status = "resolved"
        self.updated_at = datetime.utcnow()

    def dismiss(self, user: str, notes: Optional[str] = None) -> None:
        """Dismiss the alert."""
        self.status = "dismissed"
        self.resolution_notes = notes
        self.resolved_by = user
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def escalate(self, notes: Optional[str] = None) -> None:
        """Escalate the alert."""
        self.status = "escalated"
        if notes:
            self.details = self.details or {}
            self.details["escalation_notes"] = notes
        self.updated_at = datetime.utcnow()
