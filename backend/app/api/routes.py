"""API routes for Poseidon MSS.

Main API router that combines all route modules.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ais_routes import router as ais_router
from app.api.v1 import router as v1_router
from app.database.connection import get_async_db
from app.models.risk_alert import RiskAlert

logger = logging.getLogger(__name__)

router = APIRouter()

# Include v1 API routes (vessels, zones)
router.include_router(v1_router)

# Include AIS source management routes
router.include_router(ais_router)


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_async_db),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, alert, critical)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (collision_risk, zone_entry, etc.)"),
    hours: int = Query(24, description="Get alerts from last N hours", ge=1, le=168),
    limit: int = Query(100, description="Maximum number of alerts", ge=1, le=500),
) -> dict[str, list]:
    """Get alerts with optional filtering.

    Args:
        db: Database session
        status: Filter by status
        severity: Filter by severity level
        alert_type: Filter by alert type
        hours: Time window in hours
        limit: Maximum results

    Returns:
        Dictionary with alerts list
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Build query
        conditions = [RiskAlert.created_at >= cutoff_time]

        if status:
            conditions.append(RiskAlert.status == status)
        if severity:
            conditions.append(RiskAlert.severity == severity)
        if alert_type:
            conditions.append(RiskAlert.alert_type == alert_type)

        query = (
            select(RiskAlert)
            .where(and_(*conditions))
            .order_by(desc(RiskAlert.created_at))
            .limit(limit)
        )

        result = await db.execute(query)
        alerts = result.scalars().all()

        # Convert to response format
        alert_list = []
        for alert in alerts:
            alert_list.append({
                "id": str(alert.id),
                "type": alert.alert_type,
                "typeText": alert.alert_type_text,
                "severity": alert.severity,
                "status": alert.status,
                "title": alert.title,
                "message": alert.message,
                "vesselMmsi": alert.vessel_mmsi,
                "secondaryVesselMmsi": alert.secondary_vessel_mmsi,
                "latitude": float(alert.latitude) if alert.latitude else None,
                "longitude": float(alert.longitude) if alert.longitude else None,
                "details": alert.details,
                "riskScore": float(alert.risk_score) if alert.risk_score else None,
                "acknowledged": alert.acknowledged,
                "acknowledgedAt": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved": alert.resolved,
                "resolvedAt": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "createdAt": alert.created_at.isoformat() if alert.created_at else None,
                "updatedAt": alert.updated_at.isoformat() if alert.updated_at else None,
            })

        return {"alerts": alert_list}

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return {"alerts": []}
