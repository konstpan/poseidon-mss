"""Database initialization script for Poseidon MSS.

Run with: python -m app.database.init_db
"""

import asyncio
import logging
import sys
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path for running as module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.base import Base
from app.database.connection import AsyncSessionLocal, async_engine
from app.models import GeofencedZone, SystemConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Thessaloniki Port Security Zones
# Coordinates are approximate and for demonstration purposes
THESSALONIKI_ZONES = [
    {
        "name": "Port of Thessaloniki - Main Port Area",
        "code": "THESS_PORT_MAIN",
        "description": "Main commercial port boundary including container terminals and cargo areas",
        "zone_type": "port_boundary",
        "security_level": 3,
        "geometry": "SRID=4326;POLYGON((22.9200 40.6350, 22.9450 40.6350, 22.9450 40.6480, 22.9200 40.6480, 22.9200 40.6350))",
        "active": True,
        "monitor_entries": True,
        "monitor_exits": True,
        "speed_limit_knots": 8.0,
        "display_color": "#3B82F6",
        "fill_opacity": 0.2,
        "alert_config": {
            "entry_alert": True,
            "exit_alert": True,
            "speed_violation_alert": True,
            "alert_severity": "info",
            "notification_channels": ["websocket"],
        },
    },
    {
        "name": "Thessaloniki Naval Base - Restricted Zone",
        "code": "THESS_MILITARY",
        "description": "Hellenic Navy restricted area - unauthorized vessels prohibited",
        "zone_type": "military",
        "security_level": 5,
        "geometry": "SRID=4326;POLYGON((22.9100 40.6250, 22.9200 40.6250, 22.9200 40.6350, 22.9100 40.6350, 22.9100 40.6250))",
        "active": True,
        "monitor_entries": True,
        "monitor_exits": True,
        "speed_limit_knots": None,
        "display_color": "#EF4444",
        "fill_opacity": 0.4,
        "alert_config": {
            "entry_alert": True,
            "exit_alert": False,
            "alert_severity": "critical",
            "notification_channels": ["websocket", "email"],
            "restricted_vessel_types": "all_civilian",
        },
    },
    {
        "name": "Thessaloniki Anchorage Area",
        "code": "THESS_ANCHORAGE",
        "description": "Designated anchorage area for vessels awaiting berth or inspection",
        "zone_type": "anchorage",
        "security_level": 2,
        "geometry": "SRID=4326;POLYGON((22.9500 40.6200, 22.9800 40.6200, 22.9800 40.6400, 22.9500 40.6400, 22.9500 40.6200))",
        "active": True,
        "monitor_entries": True,
        "monitor_exits": True,
        "speed_limit_knots": 5.0,
        "display_color": "#F59E0B",
        "fill_opacity": 0.2,
        "alert_config": {
            "entry_alert": True,
            "exit_alert": True,
            "anchor_drag_alert": True,
            "alert_severity": "info",
            "notification_channels": ["websocket"],
        },
    },
    {
        "name": "Thessaloniki Approach Channel",
        "code": "THESS_APPROACH",
        "description": "Main approach channel to Thessaloniki port - traffic monitoring zone",
        "zone_type": "approach_channel",
        "security_level": 2,
        "geometry": "SRID=4326;POLYGON((22.9300 40.5900, 22.9400 40.5900, 22.9400 40.6350, 22.9300 40.6350, 22.9300 40.5900))",
        "active": True,
        "monitor_entries": True,
        "monitor_exits": False,
        "speed_limit_knots": 12.0,
        "display_color": "#10B981",
        "fill_opacity": 0.15,
        "alert_config": {
            "entry_alert": True,
            "exit_alert": False,
            "speed_violation_alert": True,
            "collision_detection": True,
            "alert_severity": "warning",
            "notification_channels": ["websocket"],
        },
    },
    {
        "name": "Thessaloniki Pilot Boarding Area",
        "code": "THESS_PILOT",
        "description": "Pilot boarding and disembarkation zone",
        "zone_type": "pilot_boarding",
        "security_level": 2,
        "geometry": "SRID=4326;POLYGON((22.9350 40.5850, 22.9450 40.5850, 22.9450 40.5950, 22.9350 40.5950, 22.9350 40.5850))",
        "active": True,
        "monitor_entries": True,
        "monitor_exits": True,
        "speed_limit_knots": 6.0,
        "display_color": "#8B5CF6",
        "fill_opacity": 0.25,
        "alert_config": {
            "entry_alert": True,
            "exit_alert": True,
            "alert_severity": "info",
            "notification_channels": ["websocket"],
        },
    },
]


async def create_extensions(session: AsyncSession) -> None:
    """Create required PostgreSQL extensions."""
    logger.info("Creating PostgreSQL extensions...")
    extensions = [
        "CREATE EXTENSION IF NOT EXISTS postgis",
        "CREATE EXTENSION IF NOT EXISTS postgis_topology",
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    ]
    for ext in extensions:
        await session.execute(text(ext))
    await session.commit()
    logger.info("Extensions created successfully")


async def create_schemas(session: AsyncSession) -> None:
    """Create required database schemas."""
    logger.info("Creating database schemas...")
    await session.execute(text("CREATE SCHEMA IF NOT EXISTS ais"))
    await session.execute(text("CREATE SCHEMA IF NOT EXISTS security"))
    await session.commit()
    logger.info("Schemas created successfully")


async def create_tables() -> None:
    """Create all database tables."""
    logger.info("Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created successfully")


async def insert_security_zones(session: AsyncSession) -> None:
    """Insert sample security zones for Thessaloniki port."""
    logger.info("Inserting security zones...")

    # Check if zones already exist
    result = await session.execute(
        text("SELECT COUNT(*) FROM security.zones")
    )
    count = result.scalar()
    if count > 0:
        logger.info(f"Found {count} existing zones, skipping insertion")
        return

    for zone_data in THESSALONIKI_ZONES:
        geometry_wkt = zone_data.pop("geometry")
        zone = GeofencedZone(
            **zone_data,
            geometry=WKTElement(geometry_wkt, srid=4326),
        )
        session.add(zone)
        logger.info(f"  - Added zone: {zone.name}")

    await session.commit()
    logger.info(f"Inserted {len(THESSALONIKI_ZONES)} security zones")


async def insert_default_config(session: AsyncSession) -> None:
    """Insert default system configuration values."""
    logger.info("Inserting default system configuration...")

    # Check if config already exists
    result = await session.execute(
        text("SELECT COUNT(*) FROM security.system_config")
    )
    count = result.scalar()
    if count > 0:
        logger.info(f"Found {count} existing config entries, skipping insertion")
        return

    default_configs = SystemConfig.get_default_configs()
    for config_data in default_configs:
        config = SystemConfig(
            **config_data,
            active=True,
            editable=True,
            requires_restart=False,
        )
        session.add(config)

    await session.commit()
    logger.info(f"Inserted {len(default_configs)} configuration entries")


async def verify_database(session: AsyncSession) -> None:
    """Verify database setup by running test queries."""
    logger.info("Verifying database setup...")

    # Check zones
    result = await session.execute(text("SELECT COUNT(*) FROM security.zones"))
    zone_count = result.scalar()
    logger.info(f"  - Security zones: {zone_count}")

    # Check config
    result = await session.execute(text("SELECT COUNT(*) FROM security.system_config"))
    config_count = result.scalar()
    logger.info(f"  - Config entries: {config_count}")

    # Check PostGIS
    result = await session.execute(text("SELECT PostGIS_Version()"))
    postgis_version = result.scalar()
    logger.info(f"  - PostGIS version: {postgis_version}")

    # Verify spatial query works
    result = await session.execute(
        text("""
            SELECT name, ST_Area(geometry::geography) / 1000000 as area_km2
            FROM security.zones
            ORDER BY ST_Area(geometry::geography) DESC
            LIMIT 1
        """)
    )
    row = result.first()
    if row:
        logger.info(f"  - Largest zone: {row[0]} ({row[1]:.2f} km2)")

    logger.info("Database verification complete")


async def init_database() -> None:
    """Initialize the database with all required structures and sample data."""
    logger.info("=" * 60)
    logger.info("Initializing Poseidon MSS Database")
    logger.info("=" * 60)

    try:
        async with AsyncSessionLocal() as session:
            # Create extensions and schemas
            await create_extensions(session)
            await create_schemas(session)

        # Create tables (uses separate connection)
        await create_tables()

        async with AsyncSessionLocal() as session:
            # Insert sample data
            await insert_security_zones(session)
            await insert_default_config(session)

            # Verify setup
            await verify_database(session)

        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await async_engine.dispose()


async def reset_database() -> None:
    """Drop and recreate all tables (WARNING: destroys all data)."""
    logger.warning("=" * 60)
    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST")
    logger.warning("=" * 60)

    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped")

        await init_database()

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Poseidon MSS database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database (drops all tables and data)",
    )
    args = parser.parse_args()

    if args.reset:
        asyncio.run(reset_database())
    else:
        asyncio.run(init_database())
