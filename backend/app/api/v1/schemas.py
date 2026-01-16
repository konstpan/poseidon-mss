"""Pydantic response schemas for API v1 endpoints.

Defines response models for vessels, zones, and AIS sources
with proper serialization for GeoJSON and ISO 8601 timestamps.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Vessel Response Models
# =============================================================================


class VesselPositionResponse(BaseModel):
    """Single vessel position response."""

    model_config = ConfigDict(from_attributes=True)

    mmsi: str = Field(..., description="Maritime Mobile Service Identity (9 digits)")
    timestamp: datetime = Field(..., description="Position report time (ISO 8601)")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    speed: Optional[float] = Field(None, ge=0, le=102.3, description="Speed over ground (knots)")
    course: Optional[float] = Field(None, ge=0, le=360, description="Course over ground (degrees)")
    heading: Optional[int] = Field(None, ge=0, le=359, description="True heading (degrees)")
    navigation_status: Optional[int] = Field(None, ge=0, le=15, description="AIS navigation status code")
    navigation_status_text: Optional[str] = Field(None, description="Human-readable navigation status")


class VesselResponse(BaseModel):
    """Vessel details with latest position.

    Example:
        {
            "mmsi": "237583000",
            "imo": "9234567",
            "name": "OLYMPIC CHAMPION",
            "call_sign": "SVDE",
            "ship_type": 70,
            "ship_type_text": "Cargo",
            "length": 189,
            "width": 28,
            "flag_state": "GR",
            "destination": "THESSALONIKI",
            "latitude": 40.6234,
            "longitude": 22.9456,
            "speed": 12.5,
            "course": 45.2,
            "heading": 44,
            "last_seen": "2025-01-14T12:30:00Z"
        }
    """

    model_config = ConfigDict(from_attributes=True)

    mmsi: str = Field(..., description="Maritime Mobile Service Identity")
    imo: Optional[str] = Field(None, description="IMO number")
    name: Optional[str] = Field(None, description="Vessel name")
    call_sign: Optional[str] = Field(None, description="Radio call sign")
    ship_type: Optional[int] = Field(None, description="AIS ship type code")
    ship_type_text: Optional[str] = Field(None, description="Human-readable ship type")
    length: Optional[int] = Field(None, description="Vessel length (meters)")
    width: Optional[int] = Field(None, description="Vessel width (meters)")
    draught: Optional[float] = Field(None, description="Vessel draught (meters)")
    flag_state: Optional[str] = Field(None, description="Flag state (ISO country code)")
    destination: Optional[str] = Field(None, description="Reported destination")
    eta: Optional[datetime] = Field(None, description="Estimated time of arrival")

    # Current position (denormalized)
    latitude: Optional[float] = Field(None, description="Current latitude")
    longitude: Optional[float] = Field(None, description="Current longitude")
    speed: Optional[float] = Field(None, description="Current speed (knots)")
    course: Optional[float] = Field(None, description="Current course (degrees)")
    heading: Optional[int] = Field(None, description="Current heading (degrees)")
    last_seen: Optional[datetime] = Field(None, description="Last position update time")

    # Risk assessment
    risk_score: Optional[float] = Field(None, description="Risk score (0-100)")
    risk_category: Optional[str] = Field(None, description="Risk category")


class VesselListResponse(BaseModel):
    """Paginated list of vessels.

    Example:
        {
            "vessels": [...],
            "total": 150,
            "limit": 100,
            "offset": 0
        }
    """

    vessels: list[VesselResponse] = Field(..., description="List of vessels")
    total: int = Field(..., description="Total number of vessels matching query")
    limit: int = Field(..., description="Maximum results returned")
    offset: int = Field(default=0, description="Offset for pagination")


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="[longitude, latitude]"
    )


class GeoJSONLineString(BaseModel):
    """GeoJSON LineString geometry."""

    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(
        ...,
        description="Array of [longitude, latitude] coordinate pairs"
    )


class TrackProperties(BaseModel):
    """Properties for vessel track GeoJSON."""

    mmsi: str
    vessel_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    point_count: int
    total_distance_nm: Optional[float] = Field(None, description="Total distance in nautical miles")


class VesselTrackResponse(BaseModel):
    """GeoJSON FeatureCollection for vessel track.

    Example:
        {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[22.9, 40.6], [22.91, 40.61], ...]
                },
                "properties": {
                    "mmsi": "237583000",
                    "vessel_name": "OLYMPIC CHAMPION",
                    "start_time": "2025-01-14T00:00:00Z",
                    "end_time": "2025-01-14T12:00:00Z",
                    "point_count": 150
                }
            }],
            "positions": [...]
        }
    """

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]] = Field(..., description="GeoJSON features")
    positions: list[VesselPositionResponse] = Field(
        default_factory=list,
        description="Individual position points with full details"
    )


# =============================================================================
# Zone Response Models
# =============================================================================


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Array of linear rings (outer ring first, then holes)"
    )


class ZoneProperties(BaseModel):
    """Properties for zone GeoJSON feature."""

    id: str = Field(..., description="Zone UUID")
    name: str = Field(..., description="Zone name")
    code: Optional[str] = Field(None, description="Zone code")
    description: Optional[str] = Field(None, description="Zone description")
    zone_type: str = Field(..., description="Zone type")
    zone_type_text: str = Field(..., description="Human-readable zone type")
    security_level: int = Field(..., ge=1, le=5, description="Security level (1-5)")
    security_level_text: str = Field(..., description="Human-readable security level")
    active: bool = Field(..., description="Whether zone is active")
    monitor_entries: bool = Field(..., description="Whether to monitor zone entries")
    monitor_exits: bool = Field(..., description="Whether to monitor zone exits")
    speed_limit_knots: Optional[float] = Field(None, description="Speed limit in knots")
    display_color: Optional[str] = Field(None, description="Display color (hex)")
    fill_opacity: Optional[float] = Field(None, description="Fill opacity (0-1)")
    alert_config: Optional[dict[str, Any]] = Field(None, description="Alert configuration")
    time_restrictions: Optional[dict[str, Any]] = Field(None, description="Time restrictions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class GeofencedZoneResponse(BaseModel):
    """GeoJSON Feature for a geofenced zone.

    Example:
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[22.9, 40.6], [22.95, 40.6], [22.95, 40.65], [22.9, 40.65], [22.9, 40.6]]]
            },
            "properties": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Port of Thessaloniki",
                "zone_type": "port_boundary",
                "security_level": 3
            }
        }
    """

    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONPolygon = Field(..., description="Zone polygon geometry")
    properties: ZoneProperties = Field(..., description="Zone properties")


class ZoneListResponse(BaseModel):
    """GeoJSON FeatureCollection of zones.

    Example:
        {
            "type": "FeatureCollection",
            "features": [...],
            "total": 5
        }
    """

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeofencedZoneResponse] = Field(..., description="Zone features")
    total: int = Field(..., description="Total number of zones")


# =============================================================================
# AIS Source Response Models
# =============================================================================


class AISSourceInfo(BaseModel):
    """Information about a single AIS source."""

    name: str = Field(..., description="Source name")
    source_type: str = Field(..., description="Source type (emulator, live, etc.)")
    is_active: bool = Field(..., description="Whether this source is active")
    is_healthy: bool = Field(..., description="Health status")
    message_count: int = Field(default=0, description="Total messages processed")
    last_message_time: Optional[datetime] = Field(None, description="Time of last message")
    error_count: int = Field(default=0, description="Number of errors")
    last_error: Optional[str] = Field(None, description="Last error message")


class AISSourceStatusResponse(BaseModel):
    """Status of all AIS sources.

    Example:
        {
            "active_source": "emulator",
            "sources": [
                {
                    "name": "emulator",
                    "source_type": "emulator",
                    "is_active": true,
                    "is_healthy": true,
                    "message_count": 1523
                }
            ],
            "total_messages": 1523,
            "uptime_seconds": 3600
        }
    """

    active_source: str = Field(..., description="Currently active source name")
    sources: list[AISSourceInfo] = Field(..., description="All configured sources")
    total_messages: int = Field(default=0, description="Total messages across all sources")
    uptime_seconds: Optional[float] = Field(None, description="System uptime")


class ScenarioInfo(BaseModel):
    """Information about an emulator scenario."""

    name: str = Field(..., description="Scenario name")
    filename: str = Field(..., description="Scenario filename")
    description: Optional[str] = Field(None, description="Scenario description")
    vessel_count: int = Field(default=0, description="Number of vessels in scenario")
    duration_minutes: Optional[int] = Field(None, description="Scenario duration")
    area: Optional[str] = Field(None, description="Geographic area")


class ScenarioListResponse(BaseModel):
    """List of available scenarios."""

    scenarios: list[ScenarioInfo] = Field(..., description="Available scenarios")
    total: int = Field(..., description="Total number of scenarios")


# =============================================================================
# Error Response Models
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    error_type: Optional[str] = Field(None, description="Error type/code")


class ValidationErrorDetail(BaseModel):
    """Detail for validation errors."""

    loc: list[str | int] = Field(..., description="Location of error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""

    detail: list[ValidationErrorDetail] = Field(..., description="Validation errors")
