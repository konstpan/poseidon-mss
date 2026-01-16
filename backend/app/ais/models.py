"""Internal AIS data representation models.

Source-agnostic data structures for AIS messages and related types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum
from typing import Any, Optional


class NavigationStatus(IntEnum):
    """AIS Navigation Status codes (0-15)."""

    UNDERWAY_ENGINE = 0
    AT_ANCHOR = 1
    NOT_UNDER_COMMAND = 2
    RESTRICTED_MANEUVERABILITY = 3
    CONSTRAINED_BY_DRAFT = 4
    MOORED = 5
    AGROUND = 6
    ENGAGED_IN_FISHING = 7
    UNDERWAY_SAILING = 8
    RESERVED_HSC = 9
    RESERVED_WIG = 10
    RESERVED_1 = 11
    RESERVED_2 = 12
    RESERVED_3 = 13
    AIS_SART_ACTIVE = 14
    NOT_DEFINED = 15

    @classmethod
    def from_code(cls, code: Optional[int]) -> Optional["NavigationStatus"]:
        """Create NavigationStatus from AIS code."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return cls.NOT_DEFINED

    @property
    def display_text(self) -> str:
        """Return human-readable status text."""
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
        return status_map.get(self.value, "Unknown")


class VesselType(Enum):
    """Vessel type categories (simplified from AIS ship type codes)."""

    CARGO = "cargo"
    TANKER = "tanker"
    PASSENGER = "passenger"
    FISHING = "fishing"
    MILITARY = "military"
    PLEASURE_CRAFT = "pleasure_craft"
    HIGH_SPEED_CRAFT = "high_speed_craft"
    TUG = "tug"
    PILOT_VESSEL = "pilot_vessel"
    SEARCH_AND_RESCUE = "search_and_rescue"
    DREDGER = "dredger"
    LAW_ENFORCEMENT = "law_enforcement"
    SAILING = "sailing"
    OTHER = "other"
    UNKNOWN = "unknown"

    @classmethod
    def from_ais_code(cls, code: Optional[int]) -> "VesselType":
        """Convert AIS ship type code to VesselType."""
        if code is None:
            return cls.UNKNOWN

        # AIS ship type ranges
        if 70 <= code <= 79:
            return cls.CARGO
        elif 80 <= code <= 89:
            return cls.TANKER
        elif 60 <= code <= 69:
            return cls.PASSENGER
        elif code == 30:
            return cls.FISHING
        elif code == 35:
            return cls.MILITARY
        elif 36 <= code <= 37:
            return cls.PLEASURE_CRAFT
        elif 40 <= code <= 49:
            return cls.HIGH_SPEED_CRAFT
        elif 31 <= code <= 32:
            return cls.TUG
        elif code == 50:
            return cls.PILOT_VESSEL
        elif code == 51:
            return cls.SEARCH_AND_RESCUE
        elif code == 33:
            return cls.DREDGER
        elif code == 55:
            return cls.LAW_ENFORCEMENT
        elif code == 36:
            return cls.SAILING
        elif code == 0:
            return cls.UNKNOWN
        else:
            return cls.OTHER

    @property
    def display_text(self) -> str:
        """Return human-readable vessel type."""
        return self.value.replace("_", " ").title()


@dataclass
class BoundingBox:
    """Geographic bounding box for spatial queries."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def __post_init__(self) -> None:
        """Validate bounding box coordinates."""
        if not (-90 <= self.min_lat <= 90 and -90 <= self.max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= self.min_lon <= 180 and -180 <= self.max_lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if self.min_lat > self.max_lat:
            raise ValueError("min_lat must be <= max_lat")
        if self.min_lon > self.max_lon:
            raise ValueError("min_lon must be <= max_lon")

    def contains(self, latitude: float, longitude: float) -> bool:
        """Check if a point is within the bounding box."""
        return (
            self.min_lat <= latitude <= self.max_lat
            and self.min_lon <= longitude <= self.max_lon
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
        }


@dataclass
class Position:
    """Geographic position (latitude, longitude)."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_tuple(self) -> tuple[float, float]:
        """Return as (lat, lon) tuple."""
        return (self.latitude, self.longitude)


@dataclass
class AISMessage:
    """Source-agnostic AIS message representation.

    This dataclass represents the internal format for AIS data,
    independent of the original data source (emulator, AISHub, port receiver, etc.).
    """

    # Required fields
    mmsi: int
    timestamp: datetime
    latitude: float
    longitude: float

    # Navigation data (usually present in position reports)
    speed_over_ground: Optional[float] = None  # knots
    course_over_ground: Optional[float] = None  # degrees 0-360
    heading: Optional[int] = None  # degrees 0-359
    rate_of_turn: Optional[float] = None  # degrees per minute

    # Navigation status
    navigation_status: Optional[NavigationStatus] = None

    # Vessel static data (from Type 5 messages or enrichment)
    vessel_name: Optional[str] = None
    vessel_type: Optional[VesselType] = None
    vessel_type_code: Optional[int] = None
    call_sign: Optional[str] = None
    imo_number: Optional[int] = None

    # Vessel dimensions
    length: Optional[float] = None  # meters
    width: Optional[float] = None  # meters
    draft: Optional[float] = None  # meters

    # Destination
    destination: Optional[str] = None
    eta: Optional[datetime] = None

    # Position accuracy ('H' = high <10m, 'L' = low >10m)
    position_accuracy: str = "L"

    # Data source metadata
    source: str = "unknown"
    source_quality: float = 1.0  # 0.0-1.0 confidence in data
    raw_message: Optional[str] = None  # Original message for debugging

    # Reception metadata
    received_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize message data."""
        # Validate MMSI (9 digits)
        if not (100000000 <= self.mmsi <= 999999999):
            raise ValueError(f"Invalid MMSI: {self.mmsi}")

        # Validate coordinates
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")

        # Normalize speed
        if self.speed_over_ground is not None:
            self.speed_over_ground = max(0.0, min(102.2, self.speed_over_ground))

        # Normalize course (0-360)
        if self.course_over_ground is not None:
            self.course_over_ground = self.course_over_ground % 360

        # Normalize heading (0-359)
        if self.heading is not None:
            self.heading = self.heading % 360

        # Clamp source quality
        self.source_quality = max(0.0, min(1.0, self.source_quality))

    @property
    def position(self) -> Position:
        """Get position as Position object."""
        return Position(self.latitude, self.longitude)

    @property
    def is_moving(self) -> bool:
        """Check if vessel is moving (speed > 0.5 knots)."""
        return (self.speed_over_ground or 0.0) > 0.5

    @property
    def mmsi_str(self) -> str:
        """Get MMSI as 9-digit string."""
        return f"{self.mmsi:09d}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mmsi": self.mmsi,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed_over_ground": self.speed_over_ground,
            "course_over_ground": self.course_over_ground,
            "heading": self.heading,
            "rate_of_turn": self.rate_of_turn,
            "navigation_status": (
                self.navigation_status.value if self.navigation_status else None
            ),
            "navigation_status_text": (
                self.navigation_status.display_text if self.navigation_status else None
            ),
            "vessel_name": self.vessel_name,
            "vessel_type": self.vessel_type.value if self.vessel_type else None,
            "vessel_type_code": self.vessel_type_code,
            "call_sign": self.call_sign,
            "imo_number": self.imo_number,
            "length": self.length,
            "width": self.width,
            "draft": self.draft,
            "destination": self.destination,
            "eta": self.eta.isoformat() if self.eta else None,
            "position_accuracy": self.position_accuracy,
            "source": self.source,
            "source_quality": self.source_quality,
            "received_at": self.received_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AISMessage":
        """Create AISMessage from dictionary."""
        # Parse navigation status
        nav_status = None
        if data.get("navigation_status") is not None:
            nav_status = NavigationStatus.from_code(data["navigation_status"])

        # Parse vessel type
        vessel_type = None
        if data.get("vessel_type"):
            try:
                vessel_type = VesselType(data["vessel_type"])
            except ValueError:
                vessel_type = VesselType.UNKNOWN
        elif data.get("vessel_type_code"):
            vessel_type = VesselType.from_ais_code(data["vessel_type_code"])

        # Parse timestamps
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        received_at = data.get("received_at")
        if received_at and isinstance(received_at, str):
            received_at = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
        else:
            received_at = datetime.utcnow()

        eta = data.get("eta")
        if eta and isinstance(eta, str):
            eta = datetime.fromisoformat(eta.replace("Z", "+00:00"))

        return cls(
            mmsi=int(data["mmsi"]),
            timestamp=timestamp,
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            speed_over_ground=data.get("speed_over_ground"),
            course_over_ground=data.get("course_over_ground"),
            heading=data.get("heading"),
            rate_of_turn=data.get("rate_of_turn"),
            navigation_status=nav_status,
            vessel_name=data.get("vessel_name"),
            vessel_type=vessel_type,
            vessel_type_code=data.get("vessel_type_code"),
            call_sign=data.get("call_sign"),
            imo_number=data.get("imo_number"),
            length=data.get("length"),
            width=data.get("width"),
            draft=data.get("draft"),
            destination=data.get("destination"),
            eta=eta,
            position_accuracy=data.get("position_accuracy", "L"),
            source=data.get("source", "unknown"),
            source_quality=data.get("source_quality", 1.0),
            raw_message=data.get("raw_message"),
            received_at=received_at,
        )
