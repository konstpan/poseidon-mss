"""Vessel API endpoints.

Provides endpoints for:
- Listing vessels with optional spatial filtering
- Getting vessel details
- Getting vessel track history
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_AsGeoJSON, ST_MakeEnvelope, ST_SetSRID, ST_Intersects
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.models.vessel import Vessel
from app.models.vessel_position import VesselPosition
from app.api.v1.schemas import (
    VesselResponse,
    VesselListResponse,
    VesselPositionResponse,
    VesselTrackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vessels", tags=["Vessels"])


def parse_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """Parse bounding box string into coordinates.

    Args:
        bbox: Comma-separated string "min_lon,min_lat,max_lon,max_lat"

    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat) or None

    Raises:
        ValueError: If bbox format is invalid
    """
    if not bbox:
        return None

    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must have exactly 4 values")

        min_lon, min_lat, max_lon, max_lat = parts

        # Validate coordinate ranges
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if min_lon >= max_lon:
            raise ValueError("min_lon must be less than max_lon")
        if min_lat >= max_lat:
            raise ValueError("min_lat must be less than max_lat")

        return (min_lon, min_lat, max_lon, max_lat)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid bbox format: {e}")


def get_ship_type_text(ship_type: Optional[int]) -> Optional[str]:
    """Convert AIS ship type code to human-readable text."""
    if ship_type is None:
        return None

    # Main ship type categories (first digit of 2-digit code)
    type_map = {
        # 20-29: Wing in ground
        range(20, 30): "Wing in Ground",
        # 30-39: Fishing/Towing
        range(30, 35): "Fishing",
        range(35, 38): "Towing",
        range(38, 40): "Engaged in dredging/underwater ops",
        # 40-49: High speed craft
        range(40, 50): "High Speed Craft",
        # 50-59: Special craft
        (50,): "Pilot Vessel",
        (51,): "Search and Rescue",
        (52,): "Tug",
        (53,): "Port Tender",
        (54,): "Anti-pollution",
        (55,): "Law Enforcement",
        range(56, 58): "Spare",
        (58,): "Medical Transport",
        (59,): "Ships according to RR Resolution No. 18",
        # 60-69: Passenger
        range(60, 70): "Passenger",
        # 70-79: Cargo
        range(70, 80): "Cargo",
        # 80-89: Tanker
        range(80, 90): "Tanker",
        # 90-99: Other
        range(90, 100): "Other",
    }

    for key, value in type_map.items():
        if isinstance(key, range):
            if ship_type in key:
                return value
        elif isinstance(key, tuple):
            if ship_type in key:
                return value

    return "Unknown"


@router.get(
    "",
    response_model=VesselListResponse,
    summary="List vessels",
    description="""
Get a list of vessels with their latest positions.

**Query Parameters:**
- `bbox`: Bounding box filter as "min_lon,min_lat,max_lon,max_lat"
- `vessel_type`: Filter by AIS ship type code
- `limit`: Maximum number of results (default 100, max 1000)
- `offset`: Pagination offset

**Example:**
```
GET /api/v1/vessels?bbox=22.5,40.2,23.5,41.0&limit=50
```

**Returns:**
List of vessels with their latest positions within the specified area.
    """,
)
async def get_vessels(
    db: AsyncSession = Depends(get_async_db),
    bbox: Optional[str] = Query(
        None,
        description="Bounding box: min_lon,min_lat,max_lon,max_lat",
        example="22.5,40.2,23.5,41.0",
    ),
    vessel_type: Optional[int] = Query(
        None,
        description="Filter by AIS ship type code (e.g., 70 for cargo)",
        ge=0,
        le=99,
    ),
    limit: int = Query(
        100,
        description="Maximum number of results",
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        0,
        description="Pagination offset",
        ge=0,
    ),
) -> VesselListResponse:
    """Get list of vessels with optional filtering.

    Example:
        GET /api/v1/vessels?bbox=22.5,40.2,23.5,41.0&limit=50

    Returns:
        VesselListResponse with vessels and pagination info
    """
    try:
        # Build base query
        query = select(Vessel)
        count_query = select(func.count()).select_from(Vessel)

        conditions = []

        # Apply vessel type filter
        if vessel_type is not None:
            conditions.append(Vessel.ship_type == vessel_type)

        # Apply bounding box filter using denormalized coordinates
        if bbox:
            try:
                min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)
                conditions.extend([
                    Vessel.last_latitude.is_not(None),
                    Vessel.last_longitude.is_not(None),
                    Vessel.last_latitude >= min_lat,
                    Vessel.last_latitude <= max_lat,
                    Vessel.last_longitude >= min_lon,
                    Vessel.last_longitude <= max_lon,
                ])
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid bbox parameter: {e}",
                )

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(desc(Vessel.last_position_time)).offset(offset).limit(limit)

        # Execute query
        result = await db.execute(query)
        vessels = result.scalars().all()

        # Convert to response models
        vessel_responses = []
        for vessel in vessels:
            vessel_responses.append(
                VesselResponse(
                    mmsi=vessel.mmsi,
                    imo=vessel.imo,
                    name=vessel.name,
                    call_sign=vessel.call_sign,
                    ship_type=vessel.ship_type,
                    ship_type_text=vessel.ship_type_text or get_ship_type_text(vessel.ship_type),
                    length=vessel.length,
                    width=vessel.width,
                    draught=float(vessel.draught) if vessel.draught else None,
                    flag_state=vessel.flag_state,
                    destination=vessel.destination,
                    eta=vessel.eta,
                    latitude=float(vessel.last_latitude) if vessel.last_latitude else None,
                    longitude=float(vessel.last_longitude) if vessel.last_longitude else None,
                    speed=float(vessel.last_speed) if vessel.last_speed else None,
                    course=float(vessel.last_course) if vessel.last_course else None,
                    heading=None,  # Not stored in denormalized data
                    last_seen=vessel.last_position_time,
                    risk_score=float(vessel.risk_score) if vessel.risk_score else None,
                    risk_category=vessel.risk_category,
                )
            )

        return VesselListResponse(
            vessels=vessel_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vessels: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching vessels",
        )


@router.get(
    "/{mmsi}",
    response_model=VesselResponse,
    summary="Get vessel details",
    description="""
Get detailed information about a specific vessel by MMSI.

**Path Parameters:**
- `mmsi`: Maritime Mobile Service Identity (9 digits)

**Example:**
```
GET /api/v1/vessels/237583000
```

**Returns:**
Vessel details including metadata and latest position.
    """,
    responses={
        404: {"description": "Vessel not found"},
    },
)
async def get_vessel(
    mmsi: str,
    db: AsyncSession = Depends(get_async_db),
) -> VesselResponse:
    """Get vessel details by MMSI.

    Example:
        GET /api/v1/vessels/237583000

    Args:
        mmsi: Maritime Mobile Service Identity

    Returns:
        VesselResponse with vessel details

    Raises:
        HTTPException 404: If vessel not found
    """
    try:
        # Validate MMSI format
        if not mmsi.isdigit() or len(mmsi) != 9:
            raise HTTPException(
                status_code=400,
                detail="MMSI must be a 9-digit number",
            )

        # Query vessel
        result = await db.execute(
            select(Vessel).where(Vessel.mmsi == mmsi)
        )
        vessel = result.scalar_one_or_none()

        if vessel is None:
            raise HTTPException(
                status_code=404,
                detail=f"Vessel with MMSI {mmsi} not found",
            )

        # Get latest position with heading if not in denormalized data
        heading = None
        if vessel.last_position_time:
            pos_result = await db.execute(
                select(VesselPosition.heading)
                .where(VesselPosition.mmsi == mmsi)
                .order_by(desc(VesselPosition.timestamp))
                .limit(1)
            )
            pos = pos_result.scalar_one_or_none()
            if pos is not None:
                heading = pos

        return VesselResponse(
            mmsi=vessel.mmsi,
            imo=vessel.imo,
            name=vessel.name,
            call_sign=vessel.call_sign,
            ship_type=vessel.ship_type,
            ship_type_text=vessel.ship_type_text or get_ship_type_text(vessel.ship_type),
            length=vessel.length,
            width=vessel.width,
            draught=float(vessel.draught) if vessel.draught else None,
            flag_state=vessel.flag_state,
            destination=vessel.destination,
            eta=vessel.eta,
            latitude=float(vessel.last_latitude) if vessel.last_latitude else None,
            longitude=float(vessel.last_longitude) if vessel.last_longitude else None,
            speed=float(vessel.last_speed) if vessel.last_speed else None,
            course=float(vessel.last_course) if vessel.last_course else None,
            heading=heading,
            last_seen=vessel.last_position_time,
            risk_score=float(vessel.risk_score) if vessel.risk_score else None,
            risk_category=vessel.risk_category,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching vessel {mmsi}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching vessel",
        )


@router.get(
    "/{mmsi}/track",
    response_model=VesselTrackResponse,
    summary="Get vessel track history",
    description="""
Get historical positions for a vessel as a GeoJSON track.

**Path Parameters:**
- `mmsi`: Maritime Mobile Service Identity (9 digits)

**Query Parameters:**
- `start_time`: Start of time range (ISO 8601, default: 24 hours ago)
- `end_time`: End of time range (ISO 8601, default: now)
- `limit`: Maximum number of positions (default 1000)

**Example:**
```
GET /api/v1/vessels/237583000/track?start_time=2025-01-14T00:00:00Z&limit=500
```

**Returns:**
GeoJSON FeatureCollection with LineString track and individual positions.
    """,
    responses={
        404: {"description": "Vessel not found"},
    },
)
async def get_vessel_track(
    mmsi: str,
    db: AsyncSession = Depends(get_async_db),
    start_time: Optional[datetime] = Query(
        None,
        description="Start time (ISO 8601), default 24h ago",
        example="2025-01-14T00:00:00Z",
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="End time (ISO 8601), default now",
        example="2025-01-14T12:00:00Z",
    ),
    limit: int = Query(
        1000,
        description="Maximum number of positions",
        ge=1,
        le=10000,
    ),
) -> VesselTrackResponse:
    """Get vessel track history as GeoJSON.

    Example:
        GET /api/v1/vessels/237583000/track?start_time=2025-01-14T00:00:00Z

    Args:
        mmsi: Maritime Mobile Service Identity
        start_time: Start of time range (default: 24 hours ago)
        end_time: End of time range (default: now)
        limit: Maximum positions to return

    Returns:
        VesselTrackResponse with GeoJSON track

    Raises:
        HTTPException 404: If vessel not found
    """
    try:
        # Validate MMSI format
        if not mmsi.isdigit() or len(mmsi) != 9:
            raise HTTPException(
                status_code=400,
                detail="MMSI must be a 9-digit number",
            )

        # Check vessel exists
        vessel_result = await db.execute(
            select(Vessel.name).where(Vessel.mmsi == mmsi)
        )
        vessel_name = vessel_result.scalar_one_or_none()

        if vessel_name is None:
            # Check if any positions exist for this MMSI
            pos_check = await db.execute(
                select(func.count()).select_from(VesselPosition).where(VesselPosition.mmsi == mmsi)
            )
            if pos_check.scalar() == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"Vessel with MMSI {mmsi} not found",
                )

        # Default time range
        now = datetime.now(timezone.utc)
        if end_time is None:
            end_time = now
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        # Ensure times are timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        # Query positions
        query = (
            select(VesselPosition)
            .where(
                and_(
                    VesselPosition.mmsi == mmsi,
                    VesselPosition.timestamp >= start_time,
                    VesselPosition.timestamp <= end_time,
                )
            )
            .order_by(VesselPosition.timestamp)
            .limit(limit)
        )

        result = await db.execute(query)
        positions = result.scalars().all()

        # Build GeoJSON response
        coordinates = []
        position_responses = []

        for pos in positions:
            # Add to coordinates for LineString
            coordinates.append([float(pos.longitude), float(pos.latitude)])

            # Add to positions list
            position_responses.append(
                VesselPositionResponse(
                    mmsi=pos.mmsi,
                    timestamp=pos.timestamp,
                    latitude=float(pos.latitude),
                    longitude=float(pos.longitude),
                    speed=float(pos.speed) if pos.speed else None,
                    course=float(pos.course) if pos.course else None,
                    heading=pos.heading,
                    navigation_status=pos.navigation_status,
                    navigation_status_text=VesselPosition.navigation_status_text(pos.navigation_status),
                )
            )

        # Build GeoJSON feature
        features = []
        if coordinates:
            # For a valid LineString, we need at least 2 points
            if len(coordinates) >= 2:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                    "properties": {
                        "mmsi": mmsi,
                        "vessel_name": vessel_name,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "point_count": len(coordinates),
                    },
                })
            elif len(coordinates) == 1:
                # Single point - use Point geometry
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": coordinates[0],
                    },
                    "properties": {
                        "mmsi": mmsi,
                        "vessel_name": vessel_name,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "point_count": 1,
                    },
                })

        return VesselTrackResponse(
            type="FeatureCollection",
            features=features,
            positions=position_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching track for vessel {mmsi}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching vessel track",
        )
