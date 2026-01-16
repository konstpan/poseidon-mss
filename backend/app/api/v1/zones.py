"""Security zone API endpoints.

Provides endpoints for:
- Listing all geofenced zones
- Getting zone details
"""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.models.geofenced_zone import GeofencedZone
from app.api.v1.schemas import (
    GeofencedZoneResponse,
    ZoneListResponse,
    ZoneProperties,
    GeoJSONPolygon,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zones", tags=["Security Zones"])


def parse_geometry_to_geojson(geometry_wkb: bytes, db_geojson: Optional[str] = None) -> dict:
    """Parse PostGIS geometry to GeoJSON polygon.

    Args:
        geometry_wkb: PostGIS geometry in WKB format
        db_geojson: Pre-computed GeoJSON from ST_AsGeoJSON

    Returns:
        GeoJSON geometry dictionary
    """
    if db_geojson:
        return json.loads(db_geojson)

    # Default empty polygon if parsing fails
    return {
        "type": "Polygon",
        "coordinates": [],
    }


def zone_to_response(zone: GeofencedZone, geometry_geojson: str) -> GeofencedZoneResponse:
    """Convert GeofencedZone model to GeoJSON Feature response.

    Args:
        zone: GeofencedZone model instance
        geometry_geojson: GeoJSON string from ST_AsGeoJSON

    Returns:
        GeofencedZoneResponse as GeoJSON Feature
    """
    # Parse geometry
    geometry = parse_geometry_to_geojson(zone.geometry, geometry_geojson)

    # Build properties
    properties = ZoneProperties(
        id=str(zone.id),
        name=zone.name,
        code=zone.code,
        description=zone.description,
        zone_type=zone.zone_type,
        zone_type_text=zone.zone_type_text,
        security_level=zone.security_level,
        security_level_text=zone.security_level_text,
        active=zone.active,
        monitor_entries=zone.monitor_entries,
        monitor_exits=zone.monitor_exits,
        speed_limit_knots=zone.speed_limit_knots,
        display_color=zone.display_color,
        fill_opacity=zone.fill_opacity,
        alert_config=zone.alert_config,
        time_restrictions=zone.time_restrictions,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )

    return GeofencedZoneResponse(
        type="Feature",
        geometry=GeoJSONPolygon(
            type="Polygon",
            coordinates=geometry.get("coordinates", []),
        ),
        properties=properties,
    )


@router.get(
    "",
    response_model=ZoneListResponse,
    summary="List security zones",
    description="""
Get all geofenced security zones as a GeoJSON FeatureCollection.

**Query Parameters:**
- `zone_type`: Filter by zone type (e.g., port_boundary, restricted)
- `active_only`: Only return active zones (default: true)
- `security_level`: Filter by minimum security level (1-5)

**Example:**
```
GET /api/v1/zones?zone_type=port_boundary&active_only=true
```

**Returns:**
GeoJSON FeatureCollection with all zones matching the filters.

**Zone Types:**
- `port_boundary`: Port boundary area
- `restricted`: Restricted access area
- `anchorage`: Designated anchorage area
- `approach_channel`: Approach channel
- `military`: Military zone
- `environmental`: Environmental protection zone
- `traffic_separation`: Traffic separation scheme
- `pilot_boarding`: Pilot boarding area
- `general`: General zone
    """,
)
async def get_zones(
    db: AsyncSession = Depends(get_async_db),
    zone_type: Optional[str] = Query(
        None,
        description="Filter by zone type",
        example="port_boundary",
    ),
    active_only: bool = Query(
        True,
        description="Only return active zones",
    ),
    security_level: Optional[int] = Query(
        None,
        description="Minimum security level (1-5)",
        ge=1,
        le=5,
    ),
) -> ZoneListResponse:
    """Get all security zones as GeoJSON.

    Example:
        GET /api/v1/zones?zone_type=restricted&security_level=3

    Returns:
        ZoneListResponse with GeoJSON FeatureCollection
    """
    try:
        # Build query with ST_AsGeoJSON for geometry conversion
        query = select(
            GeofencedZone,
            func.ST_AsGeoJSON(GeofencedZone.geometry).label("geometry_geojson"),
        )

        conditions = []

        # Filter by active status
        if active_only:
            conditions.append(GeofencedZone.active == True)

        # Filter by zone type
        if zone_type:
            conditions.append(GeofencedZone.zone_type == zone_type)

        # Filter by minimum security level
        if security_level:
            conditions.append(GeofencedZone.security_level >= security_level)

        # Apply conditions
        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))

        # Order by security level (highest first), then name
        query = query.order_by(
            GeofencedZone.security_level.desc(),
            GeofencedZone.name,
        )

        # Execute query
        result = await db.execute(query)
        rows = result.all()

        # Convert to GeoJSON features
        features = []
        for row in rows:
            zone = row[0]  # GeofencedZone model
            geometry_geojson = row[1]  # GeoJSON string

            features.append(zone_to_response(zone, geometry_geojson))

        return ZoneListResponse(
            type="FeatureCollection",
            features=features,
            total=len(features),
        )

    except Exception as e:
        logger.error(f"Error fetching zones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching zones",
        )


@router.get(
    "/{zone_id}",
    response_model=GeofencedZoneResponse,
    summary="Get zone details",
    description="""
Get detailed information about a specific security zone.

**Path Parameters:**
- `zone_id`: Zone UUID

**Example:**
```
GET /api/v1/zones/123e4567-e89b-12d3-a456-426614174000
```

**Returns:**
GeoJSON Feature with zone geometry and properties.
    """,
    responses={
        404: {"description": "Zone not found"},
    },
)
async def get_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> GeofencedZoneResponse:
    """Get zone details by ID.

    Example:
        GET /api/v1/zones/123e4567-e89b-12d3-a456-426614174000

    Args:
        zone_id: Zone UUID

    Returns:
        GeofencedZoneResponse as GeoJSON Feature

    Raises:
        HTTPException 404: If zone not found
    """
    try:
        # Query zone with geometry as GeoJSON
        query = select(
            GeofencedZone,
            func.ST_AsGeoJSON(GeofencedZone.geometry).label("geometry_geojson"),
        ).where(GeofencedZone.id == zone_id)

        result = await db.execute(query)
        row = result.first()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Zone with ID {zone_id} not found",
            )

        zone = row[0]
        geometry_geojson = row[1]

        return zone_to_response(zone, geometry_geojson)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching zone {zone_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching zone",
        )
