"""Collision detection system for vessel traffic.

Implements CPA (Closest Point of Approach) and TCPA (Time to CPA) calculations
to detect potential collision risks between vessels.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vessel import Vessel
from app.models.risk_alert import RiskAlert
from app.socketio import emit_alert
from app.socketio.serializers import serialize_alert

logger = logging.getLogger(__name__)

# Earth radius in nautical miles
EARTH_RADIUS_NM = 3440.065

# Default thresholds
DEFAULT_CPA_THRESHOLD_NM = 0.5  # Alert if CPA < 0.5 nautical miles
DEFAULT_TCPA_THRESHOLD_MIN = 30  # Only consider if TCPA < 30 minutes
DEFAULT_MIN_SPEED_KNOTS = 0.5  # Ignore stationary vessels


@dataclass
class VesselState:
    """Current state of a vessel for collision calculations."""
    mmsi: str
    name: str
    latitude: float
    longitude: float
    speed: float  # knots
    course: float  # degrees
    length: Optional[float] = None

    @classmethod
    def from_vessel(cls, vessel: Vessel) -> Optional["VesselState"]:
        """Create VesselState from database Vessel model."""
        if not all([
            vessel.last_latitude,
            vessel.last_longitude,
            vessel.last_speed is not None,
            vessel.last_course is not None,
        ]):
            return None

        return cls(
            mmsi=vessel.mmsi,
            name=vessel.name or f"Unknown ({vessel.mmsi})",
            latitude=float(vessel.last_latitude),
            longitude=float(vessel.last_longitude),
            speed=float(vessel.last_speed),
            course=float(vessel.last_course),
            length=float(vessel.length) if vessel.length else None,
        )


@dataclass
class CollisionRisk:
    """Result of collision risk calculation between two vessels."""
    vessel1_mmsi: str
    vessel1_name: str
    vessel2_mmsi: str
    vessel2_name: str
    cpa: float  # Closest Point of Approach in nautical miles
    tcpa: float  # Time to CPA in minutes
    current_distance: float  # Current distance in nautical miles
    risk_level: str  # 'critical', 'high', 'medium', 'low'

    @property
    def is_critical(self) -> bool:
        return self.risk_level == "critical"

    @property
    def is_high(self) -> bool:
        return self.risk_level in ("critical", "high")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in nautical miles.

    Args:
        lat1, lon1: First position (degrees)
        lat2, lon2: Second position (degrees)

    Returns:
        Distance in nautical miles
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_NM * c


def calculate_velocity_components(speed: float, course: float) -> tuple[float, float]:
    """Convert speed and course to velocity components.

    Args:
        speed: Speed in knots
        course: Course in degrees (0 = North, 90 = East)

    Returns:
        (vx, vy) velocity components in knots (x = East, y = North)
    """
    course_rad = math.radians(course)
    vx = speed * math.sin(course_rad)  # East component
    vy = speed * math.cos(course_rad)  # North component
    return vx, vy


def calculate_cpa_tcpa(
    vessel1: VesselState,
    vessel2: VesselState,
) -> tuple[float, float]:
    """Calculate CPA and TCPA between two vessels.

    Uses relative velocity method to find closest point of approach.

    Args:
        vessel1: First vessel state
        vessel2: Second vessel state

    Returns:
        (cpa, tcpa) - CPA in nautical miles, TCPA in minutes
        TCPA is negative if vessels are moving apart
    """
    # Convert positions to approximate Cartesian (nm from vessel1)
    # This is an approximation valid for short distances
    avg_lat = (vessel1.latitude + vessel2.latitude) / 2
    nm_per_deg_lat = 60.0
    nm_per_deg_lon = 60.0 * math.cos(math.radians(avg_lat))

    # Relative position of vessel2 from vessel1 (in nm)
    dx = (vessel2.longitude - vessel1.longitude) * nm_per_deg_lon
    dy = (vessel2.latitude - vessel1.latitude) * nm_per_deg_lat

    # Velocity components
    v1x, v1y = calculate_velocity_components(vessel1.speed, vessel1.course)
    v2x, v2y = calculate_velocity_components(vessel2.speed, vessel2.course)

    # Relative velocity of vessel2 with respect to vessel1
    dvx = v2x - v1x
    dvy = v2y - v1y

    # Relative speed squared
    dv_squared = dvx * dvx + dvy * dvy

    # Current distance
    current_distance = math.sqrt(dx * dx + dy * dy)

    # If relative velocity is essentially zero, vessels maintain current distance
    if dv_squared < 0.0001:
        return current_distance, float('inf')

    # Time to CPA (in hours, since speed is in knots = nm/hour)
    # TCPA = -(relative_position · relative_velocity) / |relative_velocity|²
    tcpa_hours = -(dx * dvx + dy * dvy) / dv_squared

    # Convert to minutes
    tcpa_minutes = tcpa_hours * 60

    # Position at TCPA
    cpa_dx = dx + dvx * tcpa_hours
    cpa_dy = dy + dvy * tcpa_hours

    # CPA distance
    cpa = math.sqrt(cpa_dx * cpa_dx + cpa_dy * cpa_dy)

    return cpa, tcpa_minutes


def assess_collision_risk(
    vessel1: VesselState,
    vessel2: VesselState,
    cpa_threshold_nm: float = DEFAULT_CPA_THRESHOLD_NM,
    tcpa_threshold_min: float = DEFAULT_TCPA_THRESHOLD_MIN,
) -> Optional[CollisionRisk]:
    """Assess collision risk between two vessels.

    Args:
        vessel1: First vessel state
        vessel2: Second vessel state
        cpa_threshold_nm: CPA threshold for alerts (nautical miles)
        tcpa_threshold_min: Only consider risks within this time window (minutes)

    Returns:
        CollisionRisk if risk detected, None otherwise
    """
    # Skip if either vessel is stationary
    if vessel1.speed < DEFAULT_MIN_SPEED_KNOTS or vessel2.speed < DEFAULT_MIN_SPEED_KNOTS:
        return None

    # Calculate CPA and TCPA
    cpa, tcpa = calculate_cpa_tcpa(vessel1, vessel2)

    # Current distance
    current_distance = haversine_distance(
        vessel1.latitude, vessel1.longitude,
        vessel2.latitude, vessel2.longitude,
    )

    # Only consider future collisions (TCPA > 0) within time window
    if tcpa < 0 or tcpa > tcpa_threshold_min:
        return None

    # Determine risk level based on CPA and TCPA
    if cpa < cpa_threshold_nm * 0.5 and tcpa < 10:
        risk_level = "critical"
    elif cpa < cpa_threshold_nm and tcpa < 15:
        risk_level = "high"
    elif cpa < cpa_threshold_nm * 1.5 and tcpa < 20:
        risk_level = "medium"
    elif cpa < cpa_threshold_nm * 2:
        risk_level = "low"
    else:
        return None

    return CollisionRisk(
        vessel1_mmsi=vessel1.mmsi,
        vessel1_name=vessel1.name,
        vessel2_mmsi=vessel2.mmsi,
        vessel2_name=vessel2.name,
        cpa=round(cpa, 3),
        tcpa=round(tcpa, 1),
        current_distance=round(current_distance, 3),
        risk_level=risk_level,
    )


async def detect_collision_risks(
    session: AsyncSession,
    cpa_threshold_nm: float = DEFAULT_CPA_THRESHOLD_NM,
    tcpa_threshold_min: float = DEFAULT_TCPA_THRESHOLD_MIN,
    min_speed_knots: float = DEFAULT_MIN_SPEED_KNOTS,
) -> list[CollisionRisk]:
    """Detect all collision risks among active vessels.

    Args:
        session: Database session
        cpa_threshold_nm: CPA threshold for alerts
        tcpa_threshold_min: Time window to consider
        min_speed_knots: Minimum speed to consider vessel as moving

    Returns:
        List of detected collision risks
    """
    # Get all moving vessels with recent positions
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(minutes=10)

    result = await session.execute(
        select(Vessel).where(
            and_(
                Vessel.last_position_time >= cutoff_time,
                Vessel.last_speed >= Decimal(str(min_speed_knots)),
                Vessel.last_latitude.is_not(None),
                Vessel.last_longitude.is_not(None),
                Vessel.last_course.is_not(None),
            )
        )
    )
    vessels = result.scalars().all()

    # Convert to VesselState objects
    vessel_states = []
    for v in vessels:
        state = VesselState.from_vessel(v)
        if state:
            vessel_states.append(state)

    logger.debug(f"Checking {len(vessel_states)} moving vessels for collision risks")

    # Check all pairs
    risks = []
    for i, v1 in enumerate(vessel_states):
        for v2 in vessel_states[i + 1:]:
            risk = assess_collision_risk(
                v1, v2,
                cpa_threshold_nm=cpa_threshold_nm,
                tcpa_threshold_min=tcpa_threshold_min,
            )
            if risk:
                risks.append(risk)

    # Sort by risk level (critical first) and TCPA
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda r: (risk_order.get(r.risk_level, 4), r.tcpa))

    return risks


async def create_collision_alert(
    session: AsyncSession,
    risk: CollisionRisk,
) -> RiskAlert:
    """Create a collision risk alert in the database.

    Args:
        session: Database session
        risk: Collision risk details

    Returns:
        Created RiskAlert
    """
    # Map risk level to severity
    severity_map = {
        "critical": "critical",
        "high": "alert",
        "medium": "warning",
        "low": "info",
    }
    severity = severity_map.get(risk.risk_level, "warning")

    title = f"Collision Risk: {risk.vessel1_name} / {risk.vessel2_name}"
    message = (
        f"Potential collision detected between {risk.vessel1_name} (MMSI: {risk.vessel1_mmsi}) "
        f"and {risk.vessel2_name} (MMSI: {risk.vessel2_mmsi}). "
        f"CPA: {risk.cpa:.2f} nm in {risk.tcpa:.1f} minutes. "
        f"Current distance: {risk.current_distance:.2f} nm."
    )

    alert = RiskAlert(
        id=uuid4(),
        alert_type="collision_risk",
        severity=severity,
        status="active",
        title=title,
        message=message,
        vessel_mmsi=risk.vessel1_mmsi,
        secondary_vessel_mmsi=risk.vessel2_mmsi,
        risk_score=Decimal(str(min(100, (1 - risk.cpa) * 50 + (30 - risk.tcpa) * 2))),
        details={
            "cpa_nm": risk.cpa,
            "tcpa_minutes": risk.tcpa,
            "current_distance_nm": risk.current_distance,
            "risk_level": risk.risk_level,
            "vessel1": {
                "mmsi": risk.vessel1_mmsi,
                "name": risk.vessel1_name,
            },
            "vessel2": {
                "mmsi": risk.vessel2_mmsi,
                "name": risk.vessel2_name,
            },
        },
    )

    session.add(alert)

    # Emit alert via Socket.IO for real-time notification
    try:
        alert_data = serialize_alert(alert)
        await emit_alert(alert_data)
    except Exception as e:
        logger.warning(f"Failed to emit collision alert: {e}")

    return alert


async def check_existing_collision_alert(
    session: AsyncSession,
    mmsi1: str,
    mmsi2: str,
) -> Optional[RiskAlert]:
    """Check if an active collision alert already exists for this vessel pair.

    Args:
        session: Database session
        mmsi1: First vessel MMSI
        mmsi2: Second vessel MMSI

    Returns:
        Existing alert if found, None otherwise
    """
    from datetime import timedelta

    # Check for recent active alerts (within last 10 minutes)
    cutoff_time = datetime.utcnow() - timedelta(minutes=10)

    result = await session.execute(
        select(RiskAlert).where(
            and_(
                RiskAlert.alert_type == "collision_risk",
                RiskAlert.status == "active",
                RiskAlert.created_at >= cutoff_time,
                # Check both orderings of vessel pair
                (
                    (RiskAlert.vessel_mmsi == mmsi1) & (RiskAlert.secondary_vessel_mmsi == mmsi2)
                ) | (
                    (RiskAlert.vessel_mmsi == mmsi2) & (RiskAlert.secondary_vessel_mmsi == mmsi1)
                ),
            )
        )
    )
    return result.scalar_one_or_none()


async def run_collision_detection(
    session: AsyncSession,
    cpa_threshold_nm: float = DEFAULT_CPA_THRESHOLD_NM,
    tcpa_threshold_min: float = DEFAULT_TCPA_THRESHOLD_MIN,
) -> dict[str, int]:
    """Run collision detection and create alerts for new risks.

    Args:
        session: Database session
        cpa_threshold_nm: CPA threshold for alerts
        tcpa_threshold_min: Time window to consider

    Returns:
        Statistics dictionary
    """
    # Detect risks
    risks = await detect_collision_risks(
        session,
        cpa_threshold_nm=cpa_threshold_nm,
        tcpa_threshold_min=tcpa_threshold_min,
    )

    logger.info(f"Detected {len(risks)} potential collision risks")

    alerts_created = 0
    alerts_updated = 0

    for risk in risks:
        # Check if alert already exists
        existing = await check_existing_collision_alert(
            session, risk.vessel1_mmsi, risk.vessel2_mmsi
        )

        if existing:
            # Update existing alert with new CPA/TCPA values
            existing.details = existing.details or {}
            existing.details.update({
                "cpa_nm": risk.cpa,
                "tcpa_minutes": risk.tcpa,
                "current_distance_nm": risk.current_distance,
                "risk_level": risk.risk_level,
                "last_updated": datetime.utcnow().isoformat(),
            })
            existing.updated_at = datetime.utcnow()
            alerts_updated += 1
            logger.debug(
                f"Updated collision alert for {risk.vessel1_name}/{risk.vessel2_name}: "
                f"CPA={risk.cpa:.2f}nm, TCPA={risk.tcpa:.1f}min"
            )
        else:
            # Create new alert
            alert = await create_collision_alert(session, risk)
            alerts_created += 1
            logger.info(
                f"Created collision alert: {risk.vessel1_name}/{risk.vessel2_name} - "
                f"CPA={risk.cpa:.2f}nm, TCPA={risk.tcpa:.1f}min ({risk.risk_level})"
            )

    return {
        "risks_detected": len(risks),
        "alerts_created": alerts_created,
        "alerts_updated": alerts_updated,
    }
