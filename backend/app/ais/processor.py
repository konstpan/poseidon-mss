"""AIS message processor for database storage and vessel enrichment.

Provides:
- Message processing and validation
- Vessel record creation/updates
- Position storage with PostGIS
- Risk score calculation
- Transaction management
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import text, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ais.models import AISMessage, NavigationStatus, VesselType
from app.cache import get_redis_client
from app.models import Vessel, VesselPosition

logger = logging.getLogger(__name__)


class AISMessageProcessor:
    """Processes AIS messages for storage and vessel updates."""

    def __init__(self, session: AsyncSession):
        """Initialize processor with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self._vessels_processed = 0
        self._positions_stored = 0
        self._errors = 0

    async def process_message(self, message: AISMessage) -> bool:
        """Process a single AIS message.

        Args:
            message: AIS message to process

        Returns:
            True if processed successfully
        """
        try:
            # Update or create vessel record
            await self._upsert_vessel(message)
            self._vessels_processed += 1

            # Store position
            await self._store_position(message)
            self._positions_stored += 1

            # Cache position in Redis
            await self._cache_position(message)

            return True

        except Exception as e:
            logger.error(f"Failed to process message for MMSI {message.mmsi}: {e}")
            self._errors += 1
            return False

    async def process_batch(self, messages: list[AISMessage]) -> dict[str, int]:
        """Process a batch of AIS messages.

        Args:
            messages: List of AIS messages

        Returns:
            Dictionary with processing statistics
        """
        start_time = datetime.utcnow()

        for message in messages:
            await self.process_message(message)

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        return {
            "total_messages": len(messages),
            "vessels_processed": self._vessels_processed,
            "positions_stored": self._positions_stored,
            "errors": self._errors,
            "elapsed_seconds": elapsed,
        }

    async def _upsert_vessel(self, message: AISMessage) -> None:
        """Update or create vessel record from AIS message.

        Args:
            message: AIS message with vessel data
        """
        # Build vessel data from message
        vessel_data = {
            "mmsi": str(message.mmsi),
            "last_position_time": message.timestamp,
            "last_latitude": Decimal(str(message.latitude)),
            "last_longitude": Decimal(str(message.longitude)),
            "last_speed": Decimal(str(message.speed_over_ground)) if message.speed_over_ground else None,
            "last_course": Decimal(str(message.course_over_ground)) if message.course_over_ground else None,
        }

        # Add optional static data if present
        if message.vessel_name:
            vessel_data["name"] = message.vessel_name
        if message.vessel_type_code:
            vessel_data["ship_type"] = message.vessel_type_code
        if message.vessel_type:
            vessel_data["ship_type_text"] = message.vessel_type.display_text
        if message.call_sign:
            vessel_data["call_sign"] = message.call_sign
        if message.imo_number:
            vessel_data["imo"] = str(message.imo_number)
        if message.length:
            vessel_data["length"] = int(message.length)
        if message.width:
            vessel_data["width"] = int(message.width)
        if message.draft:
            vessel_data["draught"] = Decimal(str(message.draft))
        if message.destination:
            vessel_data["destination"] = message.destination

        # Upsert vessel record
        stmt = pg_insert(Vessel).values(**vessel_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["mmsi"],
            set_={
                "last_position_time": stmt.excluded.last_position_time,
                "last_latitude": stmt.excluded.last_latitude,
                "last_longitude": stmt.excluded.last_longitude,
                "last_speed": stmt.excluded.last_speed,
                "last_course": stmt.excluded.last_course,
                "name": stmt.excluded.name,
                "ship_type": stmt.excluded.ship_type,
                "ship_type_text": stmt.excluded.ship_type_text,
                "call_sign": stmt.excluded.call_sign,
                "imo": stmt.excluded.imo,
                "length": stmt.excluded.length,
                "width": stmt.excluded.width,
                "draught": stmt.excluded.draught,
                "destination": stmt.excluded.destination,
            },
        )

        await self.session.execute(stmt)

    async def _store_position(self, message: AISMessage) -> None:
        """Store vessel position from AIS message.

        Args:
            message: AIS message with position data
        """
        # Create PostGIS point from coordinates
        point_wkt = f"SRID=4326;POINT({message.longitude} {message.latitude})"

        # Insert position record using raw SQL for PostGIS
        stmt = text("""
            INSERT INTO ais.vessel_positions
            (mmsi, timestamp, position, latitude, longitude, speed, course, heading,
             navigation_status, rate_of_turn, position_accuracy)
            VALUES
            (:mmsi, :timestamp, ST_GeogFromText(:position), :latitude, :longitude,
             :speed, :course, :heading, :navigation_status, :rate_of_turn, :position_accuracy)
        """)

        await self.session.execute(
            stmt,
            {
                "mmsi": str(message.mmsi),
                "timestamp": message.timestamp,
                "position": point_wkt,
                "latitude": message.latitude,
                "longitude": message.longitude,
                "speed": message.speed_over_ground,
                "course": message.course_over_ground,
                "heading": message.heading,
                "navigation_status": (
                    message.navigation_status.value if message.navigation_status else None
                ),
                "rate_of_turn": message.rate_of_turn,
                "position_accuracy": 1 if message.position_accuracy == "H" else 0,
            },
        )

    async def _cache_position(self, message: AISMessage) -> None:
        """Cache vessel position in Redis.

        Args:
            message: AIS message with position data
        """
        redis_client = get_redis_client()
        if not redis_client:
            return

        await redis_client.set_vessel_position(
            mmsi=message.mmsi,
            latitude=message.latitude,
            longitude=message.longitude,
            speed=message.speed_over_ground,
            course=message.course_over_ground,
            heading=message.heading,
            timestamp=message.timestamp,
        )


async def process_ais_message(
    session: AsyncSession,
    message: AISMessage,
) -> bool:
    """Process a single AIS message.

    Convenience function for processing a single message.

    Args:
        session: Database session
        message: AIS message to process

    Returns:
        True if successful
    """
    processor = AISMessageProcessor(session)
    return await processor.process_message(message)


async def process_ais_messages(
    session: AsyncSession,
    messages: list[AISMessage],
) -> dict[str, int]:
    """Process multiple AIS messages.

    Convenience function for batch processing.

    Args:
        session: Database session
        messages: List of AIS messages

    Returns:
        Processing statistics dictionary
    """
    processor = AISMessageProcessor(session)
    return await processor.process_batch(messages)


# ==================== Risk Score Calculation ====================

async def calculate_vessel_risk_score(
    session: AsyncSession,
    mmsi: str,
) -> Optional[Decimal]:
    """Calculate risk score for a vessel.

    Risk factors:
    - Flag state (high-risk registries)
    - Vessel type
    - Speed patterns
    - Position history anomalies
    - AIS gaps

    Args:
        session: Database session
        mmsi: Vessel MMSI

    Returns:
        Calculated risk score (0-100) or None
    """
    # Get vessel record
    result = await session.execute(
        select(Vessel).where(Vessel.mmsi == mmsi)
    )
    vessel = result.scalar_one_or_none()

    if not vessel:
        return None

    risk_score = Decimal("0.0")

    # Factor 1: Flag state risk (certain flag states have higher risk)
    high_risk_flags = {"XX", "PA", "MH", "LR", "KM", "VU"}
    if vessel.flag_state and vessel.flag_state.upper() in high_risk_flags:
        risk_score += Decimal("15.0")

    # Factor 2: Unknown flag state
    if not vessel.flag_state or vessel.flag_state == "XX":
        risk_score += Decimal("10.0")

    # Factor 3: Missing vessel name
    if not vessel.name or vessel.name.strip() == "":
        risk_score += Decimal("10.0")

    # Factor 4: Suspicious vessel type
    if vessel.ship_type_text and "unknown" in vessel.ship_type_text.lower():
        risk_score += Decimal("10.0")

    # Factor 5: Check for AIS gaps (no positions in last 30 minutes when moving)
    if vessel.last_position_time:
        time_since_update = datetime.utcnow() - vessel.last_position_time
        if time_since_update > timedelta(minutes=30):
            # Check if vessel was moving (speed > 1 knot)
            if vessel.last_speed and vessel.last_speed > Decimal("1.0"):
                risk_score += Decimal("25.0")  # Potential dark vessel

    # Factor 6: Abnormal speed for vessel type
    if vessel.last_speed:
        speed = float(vessel.last_speed)
        # Cargo/tanker vessels rarely exceed 20 knots
        if vessel.ship_type in range(70, 90) and speed > 20:
            risk_score += Decimal("15.0")

    # Cap at 100
    risk_score = min(risk_score, Decimal("100.0"))

    # Determine category
    if risk_score >= 75:
        category = "critical"
    elif risk_score >= 50:
        category = "high"
    elif risk_score >= 25:
        category = "medium"
    else:
        category = "low"

    # Update vessel record
    await session.execute(
        update(Vessel)
        .where(Vessel.mmsi == mmsi)
        .values(risk_score=risk_score, risk_category=category)
    )

    return risk_score


async def update_all_risk_scores(session: AsyncSession) -> dict[str, int]:
    """Update risk scores for all active vessels.

    Active vessels are those seen in the last hour.

    Args:
        session: Database session

    Returns:
        Statistics dictionary
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=1)

    # Get active vessels
    result = await session.execute(
        select(Vessel.mmsi).where(Vessel.last_position_time >= cutoff_time)
    )
    mmsis = [row[0] for row in result.fetchall()]

    updated = 0
    errors = 0

    for mmsi in mmsis:
        try:
            await calculate_vessel_risk_score(session, mmsi)
            updated += 1
        except Exception as e:
            logger.error(f"Failed to update risk score for {mmsi}: {e}")
            errors += 1

    return {
        "total_vessels": len(mmsis),
        "updated": updated,
        "errors": errors,
    }
