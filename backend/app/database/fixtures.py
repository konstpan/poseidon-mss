"""Sample data fixtures for Poseidon MSS testing and development.

Run with: python -m app.database.fixtures
"""

import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path for running as module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.connection import AsyncSessionLocal, async_engine
from app.models import RiskAlert, Vessel, VesselPosition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Sample vessels in the Thessaloniki area
SAMPLE_VESSELS: list[dict[str, Any]] = [
    {
        "mmsi": "239876543",
        "imo": "9876543",
        "name": "AEGEAN SPIRIT",
        "call_sign": "SVAB1",
        "ship_type": 70,  # Cargo
        "ship_type_text": "Cargo",
        "dimension_a": 150,
        "dimension_b": 30,
        "dimension_c": 15,
        "dimension_d": 15,
        "length": 180,
        "width": 30,
        "draught": Decimal("8.5"),
        "destination": "PIRAEUS",
        "flag_state": "GR",
        "risk_score": Decimal("0.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "240123456",
        "imo": "9123456",
        "name": "POSEIDON CARRIER",
        "call_sign": "SVCD2",
        "ship_type": 71,  # Cargo - hazardous cat A
        "ship_type_text": "Cargo - Hazardous category A",
        "dimension_a": 200,
        "dimension_b": 40,
        "dimension_c": 20,
        "dimension_d": 20,
        "length": 240,
        "width": 40,
        "draught": Decimal("10.2"),
        "destination": "ISTANBUL",
        "flag_state": "GR",
        "risk_score": Decimal("15.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "241567890",
        "imo": "9567890",
        "name": "MEDITERRANEAN STAR",
        "call_sign": "SVEF3",
        "ship_type": 80,  # Tanker
        "ship_type_text": "Tanker",
        "dimension_a": 250,
        "dimension_b": 50,
        "dimension_c": 22,
        "dimension_d": 22,
        "length": 300,
        "width": 44,
        "draught": Decimal("14.5"),
        "destination": "CONSTANTA",
        "flag_state": "MT",
        "risk_score": Decimal("25.0"),
        "risk_category": "moderate",
    },
    {
        "mmsi": "538001234",
        "imo": "9234567",
        "name": "OCEAN BREEZE",
        "call_sign": "V7AB4",
        "ship_type": 60,  # Passenger
        "ship_type_text": "Passenger",
        "dimension_a": 180,
        "dimension_b": 30,
        "dimension_c": 14,
        "dimension_d": 14,
        "length": 210,
        "width": 28,
        "draught": Decimal("7.0"),
        "destination": "MYKONOS",
        "flag_state": "MH",
        "risk_score": Decimal("5.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "636012345",
        "imo": "9345678",
        "name": "LIBERTY EXPRESS",
        "call_sign": "D5GH5",
        "ship_type": 70,  # Cargo
        "ship_type_text": "Cargo",
        "dimension_a": 120,
        "dimension_b": 25,
        "dimension_c": 12,
        "dimension_d": 12,
        "length": 145,
        "width": 24,
        "draught": Decimal("6.8"),
        "destination": "VOLOS",
        "flag_state": "LR",
        "risk_score": Decimal("10.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "255804000",
        "imo": "9456789",
        "name": "ATLANTIC VOYAGER",
        "call_sign": "CQIJ6",
        "ship_type": 79,  # Cargo - No additional info
        "ship_type_text": "Cargo",
        "dimension_a": 160,
        "dimension_b": 35,
        "dimension_c": 16,
        "dimension_d": 16,
        "length": 195,
        "width": 32,
        "draught": Decimal("9.0"),
        "destination": "THESSALONIKI",
        "flag_state": "PT",
        "risk_score": Decimal("0.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "311045000",
        "imo": "9567891",
        "name": "CARIBBEAN TRADER",
        "call_sign": "C6KL7",
        "ship_type": 70,  # Cargo
        "ship_type_text": "Cargo",
        "dimension_a": 140,
        "dimension_b": 30,
        "dimension_c": 13,
        "dimension_d": 13,
        "length": 170,
        "width": 26,
        "draught": Decimal("7.5"),
        "destination": "KAVALA",
        "flag_state": "BS",
        "risk_score": Decimal("35.0"),
        "risk_category": "moderate",
    },
    {
        "mmsi": "371234000",
        "imo": "9678901",
        "name": "PACIFIC DAWN",
        "call_sign": "HOMN8",
        "ship_type": 82,  # Tanker - hazardous cat B
        "ship_type_text": "Tanker - Hazardous category B",
        "dimension_a": 220,
        "dimension_b": 45,
        "dimension_c": 20,
        "dimension_d": 20,
        "length": 265,
        "width": 40,
        "draught": Decimal("12.0"),
        "destination": "ALEXANDROUPOLI",
        "flag_state": "PA",
        "risk_score": Decimal("45.0"),
        "risk_category": "elevated",
    },
    {
        "mmsi": "244890000",
        "imo": "9789012",
        "name": "DUTCH PIONEER",
        "call_sign": "PBOP9",
        "ship_type": 31,  # Towing
        "ship_type_text": "Towing",
        "dimension_a": 30,
        "dimension_b": 10,
        "dimension_c": 6,
        "dimension_d": 6,
        "length": 40,
        "width": 12,
        "draught": Decimal("4.0"),
        "destination": "THESSALONIKI",
        "flag_state": "NL",
        "risk_score": Decimal("0.0"),
        "risk_category": "low",
    },
    {
        "mmsi": "269057000",
        "imo": "9890123",
        "name": "SWISS LAKE",
        "call_sign": "HBQR0",
        "ship_type": 52,  # Tug
        "ship_type_text": "Tug",
        "dimension_a": 25,
        "dimension_b": 8,
        "dimension_c": 5,
        "dimension_d": 5,
        "length": 33,
        "width": 10,
        "draught": Decimal("3.5"),
        "destination": "THESSALONIKI PORT",
        "flag_state": "CH",
        "risk_score": Decimal("0.0"),
        "risk_category": "low",
    },
]


# Base positions for generating tracks (around Thessaloniki)
BASE_POSITIONS = [
    # In anchorage area
    {"lat": 40.6300, "lon": 22.9650, "speed": 0.5, "status": 1},  # At anchor
    # In approach channel
    {"lat": 40.6100, "lon": 22.9350, "speed": 10.0, "status": 0},  # Under way
    # In port area
    {"lat": 40.6400, "lon": 22.9300, "speed": 5.0, "status": 0},
    # Near pilot boarding
    {"lat": 40.5900, "lon": 22.9400, "speed": 6.0, "status": 0},
    # Moored
    {"lat": 40.6420, "lon": 22.9280, "speed": 0.0, "status": 5},  # Moored
    # In transit
    {"lat": 40.6050, "lon": 22.9500, "speed": 12.0, "status": 0},
    # Approaching
    {"lat": 40.5950, "lon": 22.9600, "speed": 8.0, "status": 0},
    # In anchorage
    {"lat": 40.6350, "lon": 22.9700, "speed": 0.2, "status": 1},
    # Near military zone (for alerts)
    {"lat": 40.6290, "lon": 22.9180, "speed": 4.0, "status": 0},
    # In port
    {"lat": 40.6450, "lon": 22.9350, "speed": 3.0, "status": 0},
]


def generate_track_positions(
    base_lat: float,
    base_lon: float,
    base_speed: float,
    course: float,
    num_points: int = 20,
    time_interval_minutes: int = 5,
) -> list[dict[str, Any]]:
    """Generate a realistic vessel track with slight variations."""
    positions = []
    current_time = datetime.utcnow() - timedelta(minutes=num_points * time_interval_minutes)

    lat = base_lat
    lon = base_lon
    speed = base_speed
    heading = int(course)

    for i in range(num_points):
        # Add slight random variations
        lat_variation = random.uniform(-0.001, 0.001)
        lon_variation = random.uniform(-0.001, 0.001)
        speed_variation = random.uniform(-1.0, 1.0) if speed > 0 else 0
        course_variation = random.uniform(-5, 5)

        # Move vessel slightly based on course and speed
        if speed > 0:
            import math
            # Simple movement approximation
            distance_nm = (speed * time_interval_minutes) / 60
            lat += distance_nm * math.cos(math.radians(course)) / 60
            lon += distance_nm * math.sin(math.radians(course)) / (60 * math.cos(math.radians(lat)))

        positions.append({
            "timestamp": current_time,
            "latitude": Decimal(str(round(lat + lat_variation, 6))),
            "longitude": Decimal(str(round(lon + lon_variation, 6))),
            "speed": Decimal(str(max(0, round(speed + speed_variation, 2)))),
            "course": Decimal(str(round((course + course_variation) % 360, 2))),
            "heading": (heading + int(course_variation)) % 360,
            "navigation_status": 0 if speed > 0.5 else 1,
            "rate_of_turn": random.randint(-10, 10),
            "position_accuracy": 1,
        })

        current_time += timedelta(minutes=time_interval_minutes)
        course = (course + course_variation) % 360

    return positions


async def insert_sample_vessels(session: AsyncSession) -> list[Vessel]:
    """Insert sample vessels into the database."""
    logger.info("Inserting sample vessels...")

    # Check if vessels already exist
    result = await session.execute(text("SELECT COUNT(*) FROM ais.vessels"))
    count = result.scalar()
    if count > 0:
        logger.info(f"Found {count} existing vessels, skipping insertion")
        result = await session.execute(text("SELECT mmsi FROM ais.vessels"))
        return []

    vessels = []
    for i, vessel_data in enumerate(SAMPLE_VESSELS):
        # Set initial position from base positions
        base_pos = BASE_POSITIONS[i % len(BASE_POSITIONS)]
        vessel_data["last_latitude"] = Decimal(str(base_pos["lat"]))
        vessel_data["last_longitude"] = Decimal(str(base_pos["lon"]))
        vessel_data["last_speed"] = Decimal(str(base_pos["speed"]))
        vessel_data["last_course"] = Decimal(str(random.randint(0, 359)))
        vessel_data["last_position_time"] = datetime.utcnow()

        vessel = Vessel(**vessel_data)
        session.add(vessel)
        vessels.append(vessel)
        logger.info(f"  - Added vessel: {vessel.name} ({vessel.mmsi})")

    await session.commit()
    logger.info(f"Inserted {len(vessels)} sample vessels")
    return vessels


async def insert_sample_positions(session: AsyncSession, vessels: list[Vessel]) -> None:
    """Insert sample position history for vessels."""
    logger.info("Inserting sample vessel positions...")

    # Check if positions already exist
    result = await session.execute(text("SELECT COUNT(*) FROM ais.vessel_positions"))
    count = result.scalar()
    if count > 0:
        logger.info(f"Found {count} existing positions, skipping insertion")
        return

    total_positions = 0
    for i, vessel in enumerate(vessels):
        base_pos = BASE_POSITIONS[i % len(BASE_POSITIONS)]
        course = random.randint(0, 359)

        # Generate track with 15-25 positions per vessel
        num_positions = random.randint(15, 25)
        positions_data = generate_track_positions(
            base_lat=base_pos["lat"],
            base_lon=base_pos["lon"],
            base_speed=base_pos["speed"],
            course=course,
            num_points=num_positions,
            time_interval_minutes=random.randint(3, 8),
        )

        for pos_data in positions_data:
            position = VesselPosition(
                mmsi=vessel.mmsi,
                position=WKTElement(
                    f"SRID=4326;POINT({pos_data['longitude']} {pos_data['latitude']})",
                    srid=4326,
                ),
                **pos_data,
            )
            session.add(position)
            total_positions += 1

    await session.commit()
    logger.info(f"Inserted {total_positions} position records for {len(vessels)} vessels")


async def insert_sample_alerts(session: AsyncSession) -> None:
    """Insert sample alerts for demonstration."""
    logger.info("Inserting sample alerts...")

    # Check if alerts already exist
    result = await session.execute(text("SELECT COUNT(*) FROM security.alerts"))
    count = result.scalar()
    if count > 0:
        logger.info(f"Found {count} existing alerts, skipping insertion")
        return

    # Get a zone for reference
    result = await session.execute(
        text("SELECT id, name FROM security.zones WHERE code = 'THESS_PORT_MAIN' LIMIT 1")
    )
    zone_row = result.first()
    zone_id = zone_row[0] if zone_row else None

    sample_alerts = [
        {
            "alert_type": "zone_entry",
            "severity": "info",
            "status": "active",
            "title": "Vessel entered port area",
            "message": "AEGEAN SPIRIT (239876543) has entered the Thessaloniki Port main area",
            "vessel_mmsi": "239876543",
            "zone_id": zone_id,
            "latitude": Decimal("40.6400"),
            "longitude": Decimal("22.9300"),
            "details": {
                "zone_name": "Port of Thessaloniki - Main Port Area",
                "vessel_speed": 5.2,
                "entry_bearing": 45,
            },
            "acknowledged": False,
        },
        {
            "alert_type": "speed_violation",
            "severity": "warning",
            "status": "active",
            "title": "Speed limit exceeded",
            "message": "PACIFIC DAWN (371234000) exceeding speed limit in port area",
            "vessel_mmsi": "371234000",
            "zone_id": zone_id,
            "latitude": Decimal("40.6350"),
            "longitude": Decimal("22.9280"),
            "details": {
                "speed_limit": 8.0,
                "current_speed": 11.5,
                "zone_name": "Port of Thessaloniki - Main Port Area",
            },
            "acknowledged": False,
        },
        {
            "alert_type": "ais_gap",
            "severity": "warning",
            "status": "acknowledged",
            "title": "AIS signal gap detected",
            "message": "CARIBBEAN TRADER (311045000) - No AIS signal for 45 minutes",
            "vessel_mmsi": "311045000",
            "latitude": Decimal("40.6100"),
            "longitude": Decimal("22.9500"),
            "details": {
                "gap_duration_minutes": 45,
                "last_known_speed": 8.0,
                "last_known_course": 180.0,
            },
            "acknowledged": True,
            "acknowledged_at": datetime.utcnow() - timedelta(hours=1),
            "acknowledged_by": "operator@poseidon.gr",
        },
    ]

    for alert_data in sample_alerts:
        lat = alert_data.pop("latitude")
        lon = alert_data.pop("longitude")

        alert = RiskAlert(
            **alert_data,
            position=WKTElement(f"SRID=4326;POINT({lon} {lat})", srid=4326),
            latitude=lat,
            longitude=lon,
        )
        session.add(alert)
        logger.info(f"  - Added alert: {alert.title}")

    await session.commit()
    logger.info(f"Inserted {len(sample_alerts)} sample alerts")


async def load_fixtures() -> None:
    """Load all sample data fixtures."""
    logger.info("=" * 60)
    logger.info("Loading Poseidon MSS Sample Data Fixtures")
    logger.info("=" * 60)

    try:
        async with AsyncSessionLocal() as session:
            # Insert vessels first
            vessels = await insert_sample_vessels(session)

            # Only insert positions if we created new vessels
            if vessels:
                await insert_sample_positions(session, vessels)

            # Insert sample alerts
            await insert_sample_alerts(session)

        logger.info("=" * 60)
        logger.info("Fixtures loaded successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to load fixtures: {e}")
        raise
    finally:
        await async_engine.dispose()


async def clear_fixtures() -> None:
    """Clear all sample data (vessels, positions, alerts)."""
    logger.warning("=" * 60)
    logger.warning("Clearing all fixture data...")
    logger.warning("=" * 60)

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM security.alert_acknowledgments"))
            await session.execute(text("DELETE FROM security.alerts"))
            await session.execute(text("DELETE FROM ais.vessel_positions"))
            await session.execute(text("DELETE FROM ais.vessels"))
            await session.commit()

        logger.info("All fixture data cleared")

    except Exception as e:
        logger.error(f"Failed to clear fixtures: {e}")
        raise
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load sample data fixtures")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all fixture data instead of loading",
    )
    args = parser.parse_args()

    if args.clear:
        asyncio.run(clear_fixtures())
    else:
        asyncio.run(load_fixtures())
