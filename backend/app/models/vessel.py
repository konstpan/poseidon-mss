"""Vessel model for AIS vessel data."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.risk_alert import RiskAlert
    from app.models.vessel_position import VesselPosition


class Vessel(Base, TimestampMixin):
    """Vessel model representing AIS vessel static data."""

    __tablename__ = "vessels"
    __table_args__ = (
        Index("ix_vessels_name", "name"),
        Index("ix_vessels_ship_type", "ship_type"),
        Index("ix_vessels_flag_state", "flag_state"),
        Index("ix_vessels_risk_score", "risk_score"),
        {"schema": "ais"},
    )

    # Primary key - Maritime Mobile Service Identity (9 digits)
    mmsi: Mapped[str] = mapped_column(String(9), primary_key=True)

    # IMO number (optional, 7 digits)
    imo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Vessel identification
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    call_sign: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Vessel type (AIS ship type code)
    ship_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ship_type_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Dimensions (in meters from AIS reference point)
    dimension_a: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Bow
    dimension_b: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Stern
    dimension_c: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Port
    dimension_d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Starboard

    # Calculated dimensions
    length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Draft and destination
    draught: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 1), nullable=True
    )
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    eta: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Flag state (ISO 3166-1 alpha-2 country code)
    flag_state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    # Risk assessment
    risk_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), default=0.0, nullable=True
    )
    risk_category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Last known position data (denormalized for quick access)
    last_latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(9, 6), nullable=True
    )
    last_longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    last_speed: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    last_course: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    last_position_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    positions: Mapped[list["VesselPosition"]] = relationship(
        "VesselPosition",
        back_populates="vessel",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["RiskAlert"]] = relationship(
        "RiskAlert",
        back_populates="vessel",
        foreign_keys="RiskAlert.vessel_mmsi",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Vessel(mmsi={self.mmsi}, name={self.name})>"

    @property
    def dimensions_str(self) -> str:
        """Return vessel dimensions as a string."""
        if self.length and self.width:
            return f"{self.length}m x {self.width}m"
        return "Unknown"

    def update_last_position(
        self,
        latitude: Decimal,
        longitude: Decimal,
        speed: Optional[Decimal] = None,
        course: Optional[Decimal] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Update the denormalized last position data."""
        self.last_latitude = latitude
        self.last_longitude = longitude
        self.last_speed = speed
        self.last_course = course
        self.last_position_time = timestamp or datetime.utcnow()
