"""Movement behavior implementations for emulated vessels.

Provides different movement patterns for realistic vessel simulation.
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional


@dataclass
class Position:
    """Geographic position (latitude, longitude)."""

    latitude: float
    longitude: float

    def copy(self) -> "Position":
        """Create a copy of this position."""
        return Position(self.latitude, self.longitude)


@dataclass
class MovementState:
    """Current movement state of a vessel."""

    position: Position
    speed: float  # knots
    course: float  # degrees 0-360
    heading: float  # degrees 0-360


def haversine_distance(pos1: Position, pos2: Position) -> float:
    """Calculate distance in nautical miles using Haversine formula.

    Args:
        pos1: First position
        pos2: Second position

    Returns:
        Distance in nautical miles
    """
    lat1 = math.radians(pos1.latitude)
    lon1 = math.radians(pos1.longitude)
    lat2 = math.radians(pos2.latitude)
    lon2 = math.radians(pos2.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Earth radius in nautical miles
    R = 3440.065

    return R * c


def calculate_bearing(pos1: Position, pos2: Position) -> float:
    """Calculate bearing from pos1 to pos2 in degrees.

    Args:
        pos1: Starting position
        pos2: Target position

    Returns:
        Bearing in degrees (0-360)
    """
    lat1 = math.radians(pos1.latitude)
    lon1 = math.radians(pos1.longitude)
    lat2 = math.radians(pos2.latitude)
    lon2 = math.radians(pos2.longitude)

    dlon = lon2 - lon1

    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


def dead_reckon(
    position: Position,
    speed: float,
    course: float,
    time_delta: timedelta,
) -> Position:
    """Calculate new position using dead reckoning.

    Args:
        position: Current position
        speed: Speed in knots
        course: Course in degrees
        time_delta: Time elapsed

    Returns:
        New position after movement
    """
    hours = time_delta.total_seconds() / 3600
    distance_nm = speed * hours

    # Convert to degrees (approximate)
    lat_change = distance_nm * math.cos(math.radians(course)) / 60
    lon_change = distance_nm * math.sin(math.radians(course)) / (
        60 * math.cos(math.radians(position.latitude))
    )

    return Position(
        latitude=position.latitude + lat_change,
        longitude=position.longitude + lon_change,
    )


class MovementBehavior(ABC):
    """Abstract base class for vessel movement behaviors."""

    @abstractmethod
    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Update vessel state based on behavior.

        Args:
            state: Current movement state
            time_delta: Time elapsed since last update

        Returns:
            Updated movement state
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return behavior name."""
        pass


class StraightBehavior(MovementBehavior):
    """Straight line movement with slight random variations."""

    def __init__(self, course_variation: float = 2.0, speed_variation: float = 0.5):
        """Initialize straight behavior.

        Args:
            course_variation: Maximum random course change per update (degrees)
            speed_variation: Maximum random speed change per update (knots)
        """
        self.course_variation = course_variation
        self.speed_variation = speed_variation

    @property
    def name(self) -> str:
        return "straight"

    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Move in straight line with slight variations."""
        # Calculate new position
        new_position = dead_reckon(state.position, state.speed, state.course, time_delta)

        # Add slight random variations for realism
        new_course = state.course + random.uniform(
            -self.course_variation, self.course_variation
        )
        new_course = new_course % 360

        new_speed = state.speed + random.uniform(
            -self.speed_variation, self.speed_variation
        )
        new_speed = max(0.0, new_speed)

        return MovementState(
            position=new_position,
            speed=new_speed,
            course=new_course,
            heading=new_course,
        )


class LoiterBehavior(MovementBehavior):
    """Loitering behavior - slow circular drift around a center point."""

    def __init__(
        self,
        center: Optional[Position] = None,
        radius_nm: float = 0.1,
        drift_speed: float = 0.5,
    ):
        """Initialize loiter behavior.

        Args:
            center: Center point of loiter (defaults to initial position)
            radius_nm: Loiter radius in nautical miles
            drift_speed: Drift speed in knots
        """
        self.center = center
        self.radius_nm = radius_nm
        self.drift_speed = drift_speed
        self._angle = 0.0
        self._initialized = False

    @property
    def name(self) -> str:
        return "loiter"

    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Drift in circular pattern around center."""
        # Initialize center on first update
        if not self._initialized:
            if self.center is None:
                self.center = state.position.copy()
            self._initialized = True

        # Calculate angular velocity (degrees per hour)
        hours = time_delta.total_seconds() / 3600
        angular_speed = 10  # degrees per hour
        self._angle += angular_speed * hours
        self._angle = self._angle % 360

        # Calculate new position on circle
        radius_deg = self.radius_nm / 60  # Convert nm to degrees (approximate)
        new_lat = self.center.latitude + radius_deg * math.cos(math.radians(self._angle))
        new_lon = self.center.longitude + radius_deg * math.sin(
            math.radians(self._angle)
        ) / math.cos(math.radians(self.center.latitude))

        # Course is tangent to circle
        new_course = (self._angle + 90) % 360

        # Randomize speed slightly
        new_speed = self.drift_speed + random.uniform(-0.2, 0.2)
        new_speed = max(0.1, min(1.0, new_speed))

        return MovementState(
            position=Position(new_lat, new_lon),
            speed=new_speed,
            course=new_course,
            heading=new_course,
        )


class WaypointBehavior(MovementBehavior):
    """Follow a predefined list of waypoints."""

    def __init__(
        self,
        waypoints: list[tuple[float, float]],
        arrival_threshold_nm: float = 0.05,
        loop: bool = False,
    ):
        """Initialize waypoint behavior.

        Args:
            waypoints: List of (latitude, longitude) tuples
            arrival_threshold_nm: Distance at which waypoint is considered reached
            loop: Whether to loop back to first waypoint after last
        """
        self.waypoints = [Position(lat, lon) for lat, lon in waypoints]
        self.arrival_threshold_nm = arrival_threshold_nm
        self.loop = loop
        self.current_waypoint_index = 0
        self._finished = False

    @property
    def name(self) -> str:
        return "waypoints"

    @property
    def current_waypoint(self) -> Optional[Position]:
        """Get current target waypoint."""
        if self._finished or self.current_waypoint_index >= len(self.waypoints):
            return None
        return self.waypoints[self.current_waypoint_index]

    @property
    def is_finished(self) -> bool:
        """Check if all waypoints have been reached."""
        return self._finished

    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Move toward current waypoint."""
        target = self.current_waypoint

        # If no more waypoints, continue straight
        if target is None:
            straight = StraightBehavior()
            return straight.update(state, time_delta)

        # Calculate bearing to target
        bearing = calculate_bearing(state.position, target)

        # Update course to point at target
        new_state = MovementState(
            position=state.position,
            speed=state.speed,
            course=bearing,
            heading=bearing,
        )

        # Move toward target
        new_position = dead_reckon(
            new_state.position, new_state.speed, new_state.course, time_delta
        )
        new_state.position = new_position

        # Check if waypoint reached
        distance = haversine_distance(new_state.position, target)
        if distance < self.arrival_threshold_nm:
            self.current_waypoint_index += 1

            # Check if finished
            if self.current_waypoint_index >= len(self.waypoints):
                if self.loop:
                    self.current_waypoint_index = 0
                else:
                    self._finished = True

        return new_state


class EvasiveBehavior(MovementBehavior):
    """Evasive/suspicious behavior with random course changes."""

    def __init__(
        self,
        course_change_range: float = 45.0,
        speed_change_range: float = 3.0,
        min_speed: float = 2.0,
        max_speed: float = 18.0,
    ):
        """Initialize evasive behavior.

        Args:
            course_change_range: Maximum course change per update (degrees)
            speed_change_range: Maximum speed change per update (knots)
            min_speed: Minimum speed (knots)
            max_speed: Maximum speed (knots)
        """
        self.course_change_range = course_change_range
        self.speed_change_range = speed_change_range
        self.min_speed = min_speed
        self.max_speed = max_speed

    @property
    def name(self) -> str:
        return "evasive"

    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Make random course and speed changes."""
        # Random course change
        new_course = state.course + random.uniform(
            -self.course_change_range, self.course_change_range
        )
        new_course = new_course % 360

        # Random speed change
        new_speed = state.speed + random.uniform(
            -self.speed_change_range, self.speed_change_range
        )
        new_speed = max(self.min_speed, min(self.max_speed, new_speed))

        # Calculate new position
        new_position = dead_reckon(state.position, new_speed, new_course, time_delta)

        return MovementState(
            position=new_position,
            speed=new_speed,
            course=new_course,
            heading=new_course,
        )


class AnchoredBehavior(MovementBehavior):
    """Stationary/anchored behavior with minimal drift."""

    def __init__(self, max_drift_nm: float = 0.01):
        """Initialize anchored behavior.

        Args:
            max_drift_nm: Maximum drift from anchor point (nm)
        """
        self.max_drift_nm = max_drift_nm
        self.anchor_point: Optional[Position] = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "anchored"

    def update(self, state: MovementState, time_delta: timedelta) -> MovementState:
        """Stay mostly stationary with minimal drift."""
        # Set anchor point on first update
        if not self._initialized:
            self.anchor_point = state.position.copy()
            self._initialized = True

        # Very slight random drift
        drift_lat = random.uniform(-0.0001, 0.0001)
        drift_lon = random.uniform(-0.0001, 0.0001)

        new_position = Position(
            state.position.latitude + drift_lat,
            state.position.longitude + drift_lon,
        )

        # Check if we've drifted too far from anchor
        if haversine_distance(new_position, self.anchor_point) > self.max_drift_nm:
            # Drift back toward anchor
            new_position = self.anchor_point.copy()

        # Random heading changes (vessel swings at anchor)
        new_heading = state.heading + random.uniform(-5, 5)
        new_heading = new_heading % 360

        return MovementState(
            position=new_position,
            speed=0.0,
            course=state.course,
            heading=new_heading,
        )


def create_behavior(
    behavior_type: str,
    waypoints: Optional[list[tuple[float, float]]] = None,
    loiter_radius: float = 0.1,
    **kwargs,
) -> MovementBehavior:
    """Factory function to create movement behaviors.

    Args:
        behavior_type: Type of behavior ('straight', 'loiter', 'waypoints', 'evasive', 'anchored')
        waypoints: List of waypoints for waypoint behavior
        loiter_radius: Radius for loiter behavior
        **kwargs: Additional behavior-specific parameters

    Returns:
        MovementBehavior instance
    """
    behavior_type = behavior_type.lower()

    if behavior_type == "straight":
        return StraightBehavior(
            course_variation=kwargs.get("course_variation", 2.0),
            speed_variation=kwargs.get("speed_variation", 0.5),
        )
    elif behavior_type == "loiter":
        center = kwargs.get("loiter_center")
        if center:
            center = Position(center[0], center[1])
        return LoiterBehavior(
            center=center,
            radius_nm=loiter_radius,
            drift_speed=kwargs.get("drift_speed", 0.5),
        )
    elif behavior_type == "waypoints":
        if not waypoints:
            raise ValueError("Waypoints required for waypoint behavior")
        return WaypointBehavior(
            waypoints=waypoints,
            arrival_threshold_nm=kwargs.get("arrival_threshold_nm", 0.05),
            loop=kwargs.get("loop", False),
        )
    elif behavior_type == "evasive":
        return EvasiveBehavior(
            course_change_range=kwargs.get("course_change_range", 45.0),
            speed_change_range=kwargs.get("speed_change_range", 3.0),
        )
    elif behavior_type == "anchored":
        return AnchoredBehavior(
            max_drift_nm=kwargs.get("max_drift_nm", 0.01),
        )
    else:
        # Default to straight behavior
        return StraightBehavior()
