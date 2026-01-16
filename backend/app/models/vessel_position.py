"""VesselPosition model for AIS position reports."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.vessel import Vessel


class VesselPosition(Base):
    """Vessel position model for time-series AIS position data."""

    __tablename__ = "vessel_positions"
    __table_args__ = (
        Index("ix_vessel_positions_mmsi_timestamp", "mmsi", "timestamp", postgresql_using="btree"),
        Index("ix_vessel_positions_timestamp", "timestamp", postgresql_using="btree"),
        Index(
            "ix_vessel_positions_position",
            "position",
            postgresql_using="gist",
        ),
        {"schema": "ais"},
    )

    # Composite primary key for time-series partitioning
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign key to vessel
    mmsi: Mapped[str] = mapped_column(
        String(9),
        ForeignKey("ais.vessels.mmsi", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position timestamp from AIS message
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    # PostGIS geography point (SRID 4326 - WGS84)
    position: Mapped[bytes] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # Coordinates stored separately for easy access without PostGIS functions
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)

    # Speed Over Ground (knots, 0-102.2)
    speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Course Over Ground (degrees, 0-359.9)
    course: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # True heading (degrees, 0-359)
    heading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Navigation status (AIS navigation status code 0-15)
    navigation_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Rate of turn (degrees per minute, -127 to 127)
    rate_of_turn: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Position accuracy (0 = low, 1 = high)
    position_accuracy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # When the position was received by our system
    received_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationship to vessel
    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="positions")

    def __repr__(self) -> str:
        return f"<VesselPosition(mmsi={self.mmsi}, lat={self.latitude}, lon={self.longitude}, timestamp={self.timestamp})>"

    @classmethod
    def create_point_wkt(cls, longitude: float, latitude: float) -> str:
        """Create WKT representation of a point for PostGIS."""
        return f"SRID=4326;POINT({longitude} {latitude})"

    @staticmethod
    def navigation_status_text(status: Optional[int]) -> str:
        """Convert AIS navigation status code to text."""
        status_map = {
            0: "Under way using engine",
            1: "At anchor",
            2: "Not under command",
            3: "Restricted manoeuvrability",
            4: "Constrained by draught",
            5: "Moored",
            6: "Aground",
            7: "Engaged in fishing",
            8: "Under way sailing",
            9: "Reserved for HSC",
            10: "Reserved for WIG",
            11: "Reserved",
            12: "Reserved",
            13: "Reserved",
            14: "AIS-SART active",
            15: "Not defined",
        }
        return status_map.get(status, "Unknown") if status is not None else "Unknown"
