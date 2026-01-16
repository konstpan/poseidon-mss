"""Emulated vessel implementation.

Represents a simulated vessel with movement behaviors and AIS message generation.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from app.ais.models import AISMessage, NavigationStatus, VesselType
from app.emulator.behaviors import (
    MovementBehavior,
    MovementState,
    Position,
    create_behavior,
)


@dataclass
class VesselConfig:
    """Configuration for creating an emulated vessel."""

    mmsi: int
    name: str
    vessel_type: str
    start_position: tuple[float, float]
    speed: float = 10.0
    course: float = 0.0
    behavior: str = "straight"
    waypoints: Optional[list[tuple[float, float]]] = None
    loiter_radius: float = 0.1
    call_sign: Optional[str] = None
    imo_number: Optional[int] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draft: Optional[float] = None
    destination: Optional[str] = None
    flag_state: Optional[str] = None
    # AIS gap simulation
    ais_gap: Optional[dict[str, int]] = None


class EmulatedVessel:
    """Represents an emulated vessel with movement and AIS message generation."""

    def __init__(
        self,
        mmsi: int,
        name: str,
        vessel_type: VesselType,
        position: Position,
        speed: float,
        course: float,
        behavior: MovementBehavior,
        call_sign: Optional[str] = None,
        imo_number: Optional[int] = None,
        length: Optional[float] = None,
        width: Optional[float] = None,
        draft: Optional[float] = None,
        destination: Optional[str] = None,
        flag_state: Optional[str] = None,
        ais_gap_config: Optional[dict[str, int]] = None,
    ):
        """Initialize emulated vessel.

        Args:
            mmsi: Maritime Mobile Service Identity
            name: Vessel name
            vessel_type: Type of vessel
            position: Starting position
            speed: Initial speed in knots
            course: Initial course in degrees
            behavior: Movement behavior
            call_sign: Radio call sign
            imo_number: IMO number
            length: Vessel length in meters
            width: Vessel width in meters
            draft: Vessel draft in meters
            destination: Destination port
            flag_state: Flag state (country code)
            ais_gap_config: Configuration for simulating AIS gaps
        """
        self.mmsi = mmsi
        self.name = name
        self.vessel_type = vessel_type
        self.call_sign = call_sign
        self.imo_number = imo_number
        self.length = length
        self.width = width
        self.draft = draft
        self.destination = destination
        self.flag_state = flag_state

        # Movement state
        self._state = MovementState(
            position=position,
            speed=speed,
            course=course,
            heading=course,
        )
        self._behavior = behavior

        # Timing
        self._start_time = datetime.utcnow()
        self._last_update_time = self._start_time
        self._elapsed_seconds = 0.0

        # AIS gap simulation
        self._ais_gap_config = ais_gap_config
        self._is_transmitting = True

    @property
    def position(self) -> Position:
        """Get current position."""
        return self._state.position

    @property
    def latitude(self) -> float:
        """Get current latitude."""
        return self._state.position.latitude

    @property
    def longitude(self) -> float:
        """Get current longitude."""
        return self._state.position.longitude

    @property
    def speed(self) -> float:
        """Get current speed in knots."""
        return self._state.speed

    @property
    def course(self) -> float:
        """Get current course in degrees."""
        return self._state.course

    @property
    def heading(self) -> float:
        """Get current heading in degrees."""
        return self._state.heading

    @property
    def is_transmitting(self) -> bool:
        """Check if vessel is currently transmitting AIS."""
        return self._is_transmitting

    @property
    def navigation_status(self) -> NavigationStatus:
        """Determine navigation status based on behavior and speed."""
        if self._behavior.name == "anchored":
            return NavigationStatus.AT_ANCHOR
        elif self._behavior.name == "loiter" and self.speed < 1.0:
            return NavigationStatus.AT_ANCHOR
        elif self.speed < 0.5:
            return NavigationStatus.MOORED
        else:
            return NavigationStatus.UNDERWAY_ENGINE

    def update(self, time_delta: timedelta) -> None:
        """Update vessel position based on behavior.

        Args:
            time_delta: Time elapsed since last update
        """
        # Update elapsed time
        self._elapsed_seconds += time_delta.total_seconds()
        self._last_update_time = datetime.utcnow()

        # Check AIS gap
        self._update_ais_gap_status()

        # Update position using behavior
        self._state = self._behavior.update(self._state, time_delta)

    def _update_ais_gap_status(self) -> None:
        """Update whether vessel is transmitting based on AIS gap config."""
        if not self._ais_gap_config:
            self._is_transmitting = True
            return

        start_after = self._ais_gap_config.get("start_after_seconds", 0)
        duration = self._ais_gap_config.get("duration_seconds", 0)

        # Check if we're in the gap period
        if self._elapsed_seconds >= start_after:
            gap_elapsed = self._elapsed_seconds - start_after
            if gap_elapsed < duration:
                self._is_transmitting = False
            else:
                self._is_transmitting = True
        else:
            self._is_transmitting = True

    def to_ais_message(self) -> AISMessage:
        """Convert current state to AIS message.

        Returns:
            AISMessage representing current vessel state
        """
        # Add slight noise to position for realism
        lat_noise = random.uniform(-0.00001, 0.00001)
        lon_noise = random.uniform(-0.00001, 0.00001)

        return AISMessage(
            mmsi=self.mmsi,
            timestamp=datetime.utcnow(),
            latitude=self.latitude + lat_noise,
            longitude=self.longitude + lon_noise,
            speed_over_ground=round(self.speed, 1),
            course_over_ground=round(self.course, 1),
            heading=int(self.heading),
            navigation_status=self.navigation_status,
            vessel_name=self.name,
            vessel_type=self.vessel_type,
            call_sign=self.call_sign,
            imo_number=self.imo_number,
            length=self.length,
            width=self.width,
            draft=self.draft,
            destination=self.destination,
            position_accuracy="H",  # Emulated data is "high accuracy"
            source="emulator",
            source_quality=1.0,
        )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "EmulatedVessel":
        """Create emulated vessel from configuration dictionary.

        Args:
            config: Configuration dictionary with vessel parameters

        Returns:
            EmulatedVessel instance
        """
        # Parse vessel type
        vessel_type_str = config.get("type", "cargo").upper()
        try:
            vessel_type = VesselType[vessel_type_str]
        except KeyError:
            vessel_type = VesselType.from_ais_code(config.get("type_code"))

        # Get start position
        start_pos = config.get("start_position", [40.6401, 22.9444])
        position = Position(start_pos[0], start_pos[1])

        # Create behavior
        behavior = create_behavior(
            behavior_type=config.get("behavior", "straight"),
            waypoints=config.get("waypoints"),
            loiter_radius=config.get("loiter_radius", 0.1),
            loiter_center=config.get("loiter_center"),
            loop=config.get("loop", False),
        )

        return cls(
            mmsi=config["mmsi"],
            name=config["name"],
            vessel_type=vessel_type,
            position=position,
            speed=config.get("speed", 10.0),
            course=config.get("course", 0.0),
            behavior=behavior,
            call_sign=config.get("call_sign"),
            imo_number=config.get("imo_number"),
            length=config.get("length"),
            width=config.get("width"),
            draft=config.get("draft"),
            destination=config.get("destination"),
            flag_state=config.get("flag_state"),
            ais_gap_config=config.get("ais_gap"),
        )

    def __repr__(self) -> str:
        return (
            f"<EmulatedVessel(mmsi={self.mmsi}, name={self.name}, "
            f"pos=({self.latitude:.4f}, {self.longitude:.4f}), "
            f"speed={self.speed:.1f}kn, course={self.course:.1f})>"
        )


# Define sea-only zones in the Thermaikos Gulf (Thessaloniki area)
# These are rectangular areas that are guaranteed to be in water
THERMAIKOS_SEA_ZONES = [
    # Main shipping channel - center of the gulf
    (40.52, 40.58, 22.85, 22.95),
    # Southern approach
    (40.48, 40.54, 22.80, 22.92),
    # Eastern channel (near Kalamaria but in water)
    (40.54, 40.59, 22.90, 22.96),
    # Port approach area
    (40.58, 40.62, 22.90, 22.94),
    # Western gulf area
    (40.50, 40.56, 22.78, 22.88),
]


def get_random_sea_position(bbox: tuple[float, float, float, float]) -> Position:
    """Generate a random position that is guaranteed to be in the sea.

    Uses predefined sea zones for the Thermaikos Gulf area.
    Falls back to the bounding box for other areas.

    Args:
        bbox: (min_lat, max_lat, min_lon, max_lon)

    Returns:
        Position guaranteed to be in water (for known areas)
    """
    min_lat, max_lat, min_lon, max_lon = bbox

    # Check if this is the Thessaloniki/Thermaikos area
    is_thermaikos = (
        40.45 <= min_lat <= 40.65 and
        40.55 <= max_lat <= 40.70 and
        22.70 <= min_lon <= 23.10 and
        22.85 <= max_lon <= 23.10
    )

    if is_thermaikos:
        # Use predefined sea zones
        zone = random.choice(THERMAIKOS_SEA_ZONES)
        lat = random.uniform(zone[0], zone[1])
        lon = random.uniform(zone[2], zone[3])
    else:
        # Use provided bounding box for other areas
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)

    return Position(lat, lon)


def generate_random_vessel(
    mmsi: int,
    bbox: tuple[float, float, float, float],
    vessel_types: Optional[list[VesselType]] = None,
) -> EmulatedVessel:
    """Generate a random vessel within a bounding box.

    Args:
        mmsi: MMSI to assign
        bbox: (min_lat, max_lat, min_lon, max_lon)
        vessel_types: Optional list of vessel types to choose from

    Returns:
        Randomly configured EmulatedVessel
    """
    # Get a position that's guaranteed to be in water
    position = get_random_sea_position(bbox)

    # Random vessel type
    if vessel_types:
        vessel_type = random.choice(vessel_types)
    else:
        vessel_type = random.choice([
            VesselType.CARGO,
            VesselType.TANKER,
            VesselType.PASSENGER,
            VesselType.FISHING,
            VesselType.TUG,
            VesselType.PLEASURE_CRAFT,
        ])

    # Random navigation parameters
    speed = random.uniform(0.0, 15.0)
    course = random.uniform(0.0, 360.0)

    # Random behavior (weighted toward straight)
    behavior_choice = random.choices(
        ["straight", "loiter", "anchored"],
        weights=[0.7, 0.15, 0.15],
    )[0]

    behavior = create_behavior(
        behavior_type=behavior_choice,
        loiter_radius=random.uniform(0.05, 0.2),
    )

    # Generate vessel name
    name_prefixes = ["AEGEAN", "POSEIDON", "OLYMPIC", "MEDITERRANEAN", "GREEK"]
    name_suffixes = ["SPIRIT", "STAR", "VOYAGER", "CARRIER", "EXPRESS"]
    name = f"{random.choice(name_prefixes)} {random.choice(name_suffixes)}"

    # Random dimensions based on vessel type
    length = random.uniform(50, 300)
    width = length / random.uniform(4, 7)

    return EmulatedVessel(
        mmsi=mmsi,
        name=name,
        vessel_type=vessel_type,
        position=position,
        speed=speed,
        course=course,
        behavior=behavior,
        length=length,
        width=width,
        draft=random.uniform(4, 15),
        destination=random.choice(["PIRAEUS", "THESSALONIKI", "VOLOS", "PATRAS"]),
        flag_state=random.choice(["GR", "MT", "CY", "PA", "LR", "MH"]),
    )
