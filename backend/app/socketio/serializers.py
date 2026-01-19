"""Serializers for Socket.IO event data.

Converts AIS messages and database models to frontend-compatible dictionaries.
"""

from datetime import datetime
from typing import Any, Optional

from app.models.risk_alert import RiskAlert


def serialize_vessel_from_ais(
    mmsi: int,
    latitude: float,
    longitude: float,
    speed: Optional[float] = None,
    course: Optional[float] = None,
    heading: Optional[int] = None,
    timestamp: Optional[datetime] = None,
    name: Optional[str] = None,
    ship_type: Optional[int] = None,
) -> dict[str, Any]:
    """Serialize AIS message data for Socket.IO emission.

    Used when emitting directly from AIS processor.

    Args:
        mmsi: Vessel MMSI
        latitude, longitude: Position
        speed, course, heading: Navigation data
        timestamp: Position timestamp
        name: Vessel name if available
        ship_type: AIS ship type code

    Returns:
        Vessel dictionary for frontend update
    """
    return {
        "mmsi": str(mmsi),
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "course": course,
        "heading": heading,
        "last_seen": timestamp.isoformat() if timestamp else datetime.utcnow().isoformat(),
        "name": name,
        "ship_type": ship_type,
    }


def serialize_alert(alert: RiskAlert) -> dict[str, Any]:
    """Serialize RiskAlert model for Socket.IO emission.

    Matches frontend Alert type interface.

    Args:
        alert: RiskAlert model instance

    Returns:
        Alert dictionary for frontend
    """
    return {
        "id": str(alert.id),
        "type": alert.alert_type,
        "severity": alert.severity,
        "vessel_mmsi": alert.vessel_mmsi,
        "message": alert.message,
        "timestamp": alert.created_at.isoformat() if alert.created_at else datetime.utcnow().isoformat(),
        "acknowledged": alert.acknowledged,
    }
