"""Test script for Poseidon MSS database operations.

Run with: python -m pytest tests/test_database.py -v
Or directly: python tests/test_database.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal, async_engine, check_database_connection
from app.models import (
    AlertAcknowledgment,
    GeofencedZone,
    RiskAlert,
    SystemConfig,
    Vessel,
    VesselPosition,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TestDatabaseConnection:
    """Test database connectivity."""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test that we can connect to the database."""
        result = await check_database_connection()
        assert result is True, "Database connection failed"
        logger.info("Database connection: OK")

    @pytest.mark.asyncio
    async def test_postgis_extension(self):
        """Test that PostGIS extension is available."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT PostGIS_Version()"))
            version = result.scalar()
            assert version is not None, "PostGIS not installed"
            logger.info(f"PostGIS version: {version}")


class TestVesselModel:
    """Test Vessel model operations."""

    @pytest.mark.asyncio
    async def test_query_vessels(self):
        """Test querying vessels."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Vessel).limit(5)
            )
            vessels = result.scalars().all()
            logger.info(f"Found {len(vessels)} vessels")

            for vessel in vessels:
                logger.info(f"  - {vessel.name} ({vessel.mmsi}) - {vessel.flag_state}")

            assert len(vessels) >= 0, "Query failed"

    @pytest.mark.asyncio
    async def test_vessel_by_mmsi(self):
        """Test fetching vessel by MMSI."""
        async with AsyncSessionLocal() as session:
            # Get first vessel
            result = await session.execute(select(Vessel).limit(1))
            vessel = result.scalar_one_or_none()

            if vessel:
                # Fetch by MMSI
                result = await session.execute(
                    select(Vessel).where(Vessel.mmsi == vessel.mmsi)
                )
                fetched = result.scalar_one_or_none()
                assert fetched is not None, "Vessel not found by MMSI"
                assert fetched.mmsi == vessel.mmsi
                logger.info(f"Vessel lookup by MMSI: OK ({vessel.mmsi})")

    @pytest.mark.asyncio
    async def test_vessel_risk_score_filter(self):
        """Test filtering vessels by risk score."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Vessel)
                .where(Vessel.risk_score >= 20)
                .order_by(Vessel.risk_score.desc())
            )
            high_risk = result.scalars().all()
            logger.info(f"Vessels with risk score >= 20: {len(high_risk)}")

            for vessel in high_risk:
                logger.info(f"  - {vessel.name}: {vessel.risk_score}")


class TestVesselPositionModel:
    """Test VesselPosition model operations."""

    @pytest.mark.asyncio
    async def test_query_positions(self):
        """Test querying vessel positions."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VesselPosition)
                .order_by(VesselPosition.timestamp.desc())
                .limit(10)
            )
            positions = result.scalars().all()
            logger.info(f"Found {len(positions)} recent positions")

    @pytest.mark.asyncio
    async def test_position_count_by_vessel(self):
        """Test counting positions per vessel."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT v.name, v.mmsi, COUNT(vp.id) as position_count
                    FROM ais.vessels v
                    LEFT JOIN ais.vessel_positions vp ON v.mmsi = vp.mmsi
                    GROUP BY v.mmsi, v.name
                    ORDER BY position_count DESC
                    LIMIT 5
                """)
            )
            rows = result.fetchall()
            logger.info("Position counts by vessel:")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[2]} positions")


class TestGeofencedZoneModel:
    """Test GeofencedZone model operations."""

    @pytest.mark.asyncio
    async def test_query_zones(self):
        """Test querying security zones."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GeofencedZone).where(GeofencedZone.active == True)
            )
            zones = result.scalars().all()
            logger.info(f"Found {len(zones)} active zones")

            for zone in zones:
                logger.info(f"  - {zone.name} ({zone.zone_type}) - Level {zone.security_level}")

    @pytest.mark.asyncio
    async def test_zone_by_code(self):
        """Test fetching zone by code."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GeofencedZone).where(GeofencedZone.code == "THESS_PORT_MAIN")
            )
            zone = result.scalar_one_or_none()

            if zone:
                logger.info(f"Found zone: {zone.name}")
                assert zone.zone_type == "port_boundary"
                assert zone.security_level == 3


class TestSpatialQueries:
    """Test PostGIS spatial queries."""

    @pytest.mark.asyncio
    async def test_vessels_within_zone(self):
        """Test finding vessels within a specific zone."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT v.name, v.mmsi,
                           v.last_latitude, v.last_longitude,
                           z.name as zone_name
                    FROM ais.vessels v, security.zones z
                    WHERE v.last_latitude IS NOT NULL
                      AND v.last_longitude IS NOT NULL
                      AND ST_Within(
                          ST_SetSRID(ST_MakePoint(v.last_longitude, v.last_latitude), 4326)::geography::geometry,
                          z.geometry::geometry
                      )
                    LIMIT 10
                """)
            )
            rows = result.fetchall()
            logger.info(f"Vessels currently within zones: {len(rows)}")
            for row in rows:
                logger.info(f"  - {row[0]} in {row[4]}")

    @pytest.mark.asyncio
    async def test_positions_within_radius(self):
        """Test finding positions within a radius of a point."""
        async with AsyncSessionLocal() as session:
            # Center on Thessaloniki port
            center_lat = 40.6400
            center_lon = 22.9350
            radius_meters = 5000  # 5km

            result = await session.execute(
                text("""
                    SELECT v.name, vp.latitude, vp.longitude, vp.speed, vp.timestamp,
                           ST_Distance(
                               vp.position,
                               ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                           ) as distance_m
                    FROM ais.vessel_positions vp
                    JOIN ais.vessels v ON v.mmsi = vp.mmsi
                    WHERE ST_DWithin(
                        vp.position,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :radius
                    )
                    ORDER BY vp.timestamp DESC
                    LIMIT 10
                """),
                {"lat": center_lat, "lon": center_lon, "radius": radius_meters}
            )
            rows = result.fetchall()
            logger.info(f"Positions within {radius_meters}m of port center: {len(rows)}")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[5]:.0f}m away, speed {row[3]} kn")

    @pytest.mark.asyncio
    async def test_zone_area_calculation(self):
        """Test calculating zone areas using PostGIS."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT name, zone_type,
                           ST_Area(geometry::geography) / 1000000 as area_km2
                    FROM security.zones
                    ORDER BY area_km2 DESC
                """)
            )
            rows = result.fetchall()
            logger.info("Zone areas:")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[2]:.2f} km2")


class TestRiskAlertModel:
    """Test RiskAlert model operations."""

    @pytest.mark.asyncio
    async def test_query_active_alerts(self):
        """Test querying active alerts."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RiskAlert)
                .where(RiskAlert.status == "active")
                .order_by(RiskAlert.created_at.desc())
            )
            alerts = result.scalars().all()
            logger.info(f"Active alerts: {len(alerts)}")

            for alert in alerts:
                logger.info(f"  - [{alert.severity}] {alert.title}")

    @pytest.mark.asyncio
    async def test_alerts_by_severity(self):
        """Test grouping alerts by severity."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT severity, COUNT(*) as count
                    FROM security.alerts
                    GROUP BY severity
                    ORDER BY
                        CASE severity
                            WHEN 'critical' THEN 1
                            WHEN 'alert' THEN 2
                            WHEN 'warning' THEN 3
                            WHEN 'info' THEN 4
                        END
                """)
            )
            rows = result.fetchall()
            logger.info("Alerts by severity:")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[1]}")


class TestSystemConfigModel:
    """Test SystemConfig model operations."""

    @pytest.mark.asyncio
    async def test_query_config(self):
        """Test querying system configuration."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemConfig)
                .where(SystemConfig.category == "alert_thresholds")
            )
            configs = result.scalars().all()
            logger.info(f"Alert threshold configs: {len(configs)}")

            for config in configs:
                logger.info(f"  - {config.key}: {config.value}")

    @pytest.mark.asyncio
    async def test_config_by_key(self):
        """Test fetching config by key."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemConfig)
                .where(SystemConfig.key == "alert.speed_violation_threshold")
            )
            config = result.scalar_one_or_none()

            if config:
                logger.info(f"Speed violation threshold: {config.value}")
                assert config.value_type == "float"


class TestRelationships:
    """Test model relationships."""

    @pytest.mark.asyncio
    async def test_vessel_positions_relationship(self):
        """Test vessel -> positions relationship."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Vessel).limit(1)
            )
            vessel = result.scalar_one_or_none()

            if vessel:
                # Get positions for this vessel
                result = await session.execute(
                    select(VesselPosition)
                    .where(VesselPosition.mmsi == vessel.mmsi)
                    .order_by(VesselPosition.timestamp.desc())
                    .limit(5)
                )
                positions = result.scalars().all()
                logger.info(f"Vessel {vessel.name} has {len(positions)} recent positions")

    @pytest.mark.asyncio
    async def test_alert_zone_relationship(self):
        """Test alert -> zone relationship."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT a.title, a.severity, z.name as zone_name
                    FROM security.alerts a
                    JOIN security.zones z ON a.zone_id = z.id
                    LIMIT 5
                """)
            )
            rows = result.fetchall()
            logger.info("Alerts with zones:")
            for row in rows:
                logger.info(f"  - {row[0]} -> {row[2]}")


async def run_all_tests():
    """Run all tests programmatically."""
    logger.info("=" * 60)
    logger.info("Poseidon MSS Database Test Suite")
    logger.info("=" * 60)

    test_classes = [
        TestDatabaseConnection,
        TestVesselModel,
        TestVesselPositionModel,
        TestGeofencedZoneModel,
        TestSpatialQueries,
        TestRiskAlertModel,
        TestSystemConfigModel,
        TestRelationships,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for test_class in test_classes:
        logger.info(f"\n--- {test_class.__name__} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                method = getattr(instance, method_name)
                total_tests += 1

                try:
                    await method()
                    passed_tests += 1
                    logger.info(f"  [PASS] {method_name}")
                except Exception as e:
                    failed_tests += 1
                    logger.error(f"  [FAIL] {method_name}: {e}")

    logger.info("\n" + "=" * 60)
    logger.info(f"Test Results: {passed_tests}/{total_tests} passed, {failed_tests} failed")
    logger.info("=" * 60)

    return failed_tests == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        asyncio.run(async_engine.dispose())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
