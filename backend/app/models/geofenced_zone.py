"""GeofencedZone model for security zones with PostGIS geometry."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.risk_alert import RiskAlert


class GeofencedZone(Base, TimestampMixin):
    """Geofenced security zone with PostGIS polygon geometry."""

    __tablename__ = "zones"
    __table_args__ = (
        Index("ix_zones_geometry", "geometry", postgresql_using="gist"),
        Index("ix_zones_zone_type", "zone_type"),
        Index("ix_zones_security_level", "security_level"),
        Index("ix_zones_active", "active"),
        {"schema": "security"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Zone identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Zone classification
    zone_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
    )
    # Zone types: port_boundary, restricted, anchorage, approach_channel,
    #             military, environmental, traffic_separation, pilot_boarding

    # Security level (1-5, higher = more secure/sensitive)
    security_level: Mapped[int] = mapped_column(Integer, default=1)

    # PostGIS geography polygon (SRID 4326 - WGS84)
    geometry: Mapped[bytes] = mapped_column(
        Geography(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    # Zone status
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Alert configuration (JSONB)
    alert_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    # Example alert_config:
    # {
    #     "entry_alert": true,
    #     "exit_alert": false,
    #     "speed_limit": 10.0,
    #     "restricted_vessel_types": [30, 31, 32],  # AIS ship types
    #     "alert_severity": "warning",
    #     "notification_channels": ["websocket", "email"]
    # }

    # Monitoring settings
    monitor_entries: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_exits: Mapped[bool] = mapped_column(Boolean, default=False)
    speed_limit_knots: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Time-based restrictions (JSONB)
    time_restrictions: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Example time_restrictions:
    # {
    #     "active_hours": {"start": "06:00", "end": "22:00"},
    #     "active_days": [0, 1, 2, 3, 4],  # Mon-Fri
    #     "timezone": "Europe/Athens"
    # }

    # Visual styling for map display
    display_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    fill_opacity: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.3)

    # Relationships
    alerts: Mapped[list["RiskAlert"]] = relationship(
        "RiskAlert",
        back_populates="zone",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<GeofencedZone(id={self.id}, name={self.name}, type={self.zone_type})>"

    @classmethod
    def create_polygon_wkt(cls, coordinates: list[tuple[float, float]]) -> str:
        """
        Create WKT representation of a polygon for PostGIS.

        Args:
            coordinates: List of (longitude, latitude) tuples.
                        First and last coordinate should be the same to close the polygon.
        """
        coord_str = ", ".join(f"{lon} {lat}" for lon, lat in coordinates)
        return f"SRID=4326;POLYGON(({coord_str}))"

    @classmethod
    def create_rectangle_wkt(
        cls,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> str:
        """Create WKT for a rectangular zone from bounding box."""
        coordinates = [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),  # Close the polygon
        ]
        return cls.create_polygon_wkt(coordinates)

    @property
    def security_level_text(self) -> str:
        """Return human-readable security level."""
        levels = {
            1: "Low",
            2: "Moderate",
            3: "Elevated",
            4: "High",
            5: "Critical",
        }
        return levels.get(self.security_level, "Unknown")

    @property
    def zone_type_text(self) -> str:
        """Return human-readable zone type."""
        types = {
            "port_boundary": "Port Boundary",
            "restricted": "Restricted Area",
            "anchorage": "Anchorage Area",
            "approach_channel": "Approach Channel",
            "military": "Military Zone",
            "environmental": "Environmental Protection Zone",
            "traffic_separation": "Traffic Separation Scheme",
            "pilot_boarding": "Pilot Boarding Area",
            "general": "General Zone",
        }
        return types.get(self.zone_type, self.zone_type.replace("_", " ").title())
