"""Emulator adapter for the AIS data abstraction layer.

Provides AIS data from the traffic emulator for development and testing.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.ais.adapters.base import (
    AISDataAdapter,
    AISDataFetchError,
    SourceInfo,
)
from app.ais.models import AISMessage, BoundingBox
from app.emulator.engine import TrafficEmulator, THESSALONIKI_BBOX
from app.emulator.scenarios import load_scenario, ScenarioLoadError

logger = logging.getLogger(__name__)


class EmulatorAdapter(AISDataAdapter):
    """Traffic emulator adapter for development and testing.

    Generates realistic vessel movements and scenarios without
    external dependencies.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize emulator adapter.

        Config options:
            name: Adapter name
            scenario_file: Path to scenario YAML (optional)
            num_vessels: Number of random vessels if no scenario (default: 50)
            update_interval_seconds: Interval between position updates (default: 30)
            default_bbox: Default bounding box for random traffic
        """
        super().__init__(config)

        self.scenario_file: Optional[str] = config.get("scenario_file")
        self.num_vessels: int = config.get("num_vessels", 50)
        self.update_interval: int = config.get("update_interval_seconds", 30)

        # Parse bounding box if provided
        bbox_config = config.get("default_bbox")
        if bbox_config:
            self.default_bbox = BoundingBox(
                min_lat=bbox_config["min_lat"],
                max_lat=bbox_config["max_lat"],
                min_lon=bbox_config["min_lon"],
                max_lon=bbox_config["max_lon"],
            )
        else:
            self.default_bbox = THESSALONIKI_BBOX

        self.emulator: Optional[TrafficEmulator] = None

    async def start(self) -> None:
        """Initialize and start the emulator."""
        logger.info(f"Starting emulator adapter: {self.name}")

        self.emulator = TrafficEmulator(update_interval=self.update_interval)

        # Load scenario or generate random traffic
        if self.scenario_file:
            try:
                scenario = load_scenario(self.scenario_file)
                await self.emulator.load_scenario(scenario)
                logger.info(f"Loaded scenario: {scenario.name}")
            except ScenarioLoadError as e:
                logger.error(f"Failed to load scenario: {e}")
                logger.info("Falling back to random traffic")
                await self.emulator.generate_random_traffic(
                    self.num_vessels, self.default_bbox
                )
        else:
            await self.emulator.generate_random_traffic(
                self.num_vessels, self.default_bbox
            )

        # Start the emulator
        await self.emulator.start()
        self._is_started = True

        logger.info(
            f"Emulator started with {self.emulator.vessel_count} vessels "
            f"(update interval: {self.update_interval}s)"
        )

    async def stop(self) -> None:
        """Stop the emulator."""
        if self.emulator:
            await self.emulator.stop()
            logger.info("Emulator stopped")

        self._is_started = False

    async def fetch_data(
        self, bbox: Optional[BoundingBox] = None
    ) -> list[AISMessage]:
        """Get current emulated vessel positions.

        Args:
            bbox: Optional bounding box to filter results

        Returns:
            List of AISMessage objects

        Raises:
            AISDataFetchError: If emulator is not running
        """
        if not self.emulator or not self.emulator.is_running:
            raise AISDataFetchError(
                "Emulator is not running",
                source=self.name,
            )

        start_time = datetime.utcnow()

        try:
            messages = await self.emulator.get_ais_messages(bbox=bbox)

            # Record success
            latency = (datetime.utcnow() - start_time).total_seconds()
            self._record_success(len(messages), latency)

            return messages

        except Exception as e:
            self._record_error()
            raise AISDataFetchError(
                f"Failed to get emulated data: {e}",
                source=self.name,
            )

    async def health_check(self) -> bool:
        """Check if emulator is running and healthy.

        Returns:
            True if emulator is running
        """
        return self.emulator is not None and self.emulator.is_running

    def get_source_info(self) -> SourceInfo:
        """Get metadata about the emulator source.

        Returns:
            SourceInfo with current statistics
        """
        vessel_count = 0
        transmitting_count = 0
        scenario_name = None

        if self.emulator:
            vessel_count = self.emulator.vessel_count
            transmitting_count = len(self.emulator.transmitting_vessels)
            if self.emulator.scenario:
                scenario_name = self.emulator.scenario.name

        return SourceInfo(
            name=self.name,
            source_type="emulator",
            is_active=self.emulator is not None and self.emulator.is_running,
            last_successful_fetch=self._last_fetch_time,
            error_count=self._error_count,
            total_messages_received=self._total_messages,
            average_latency_seconds=self._get_average_latency(),
            quality_score=1.0,  # Emulator always has perfect data quality
            extra_info={
                "vessel_count": vessel_count,
                "transmitting_count": transmitting_count,
                "scenario_name": scenario_name,
                "update_interval": self.update_interval,
                "elapsed_seconds": (
                    self.emulator.elapsed_seconds if self.emulator else 0
                ),
            },
        )

    async def load_scenario(self, scenario_file: str) -> None:
        """Load a new scenario into the running emulator.

        Args:
            scenario_file: Path to scenario YAML file

        Raises:
            AISDataFetchError: If emulator is not running
        """
        if not self.emulator:
            raise AISDataFetchError(
                "Emulator not initialized",
                source=self.name,
            )

        # Stop current emulation
        await self.emulator.stop()

        # Load new scenario
        scenario = load_scenario(scenario_file)
        await self.emulator.load_scenario(scenario)

        # Restart
        await self.emulator.start()

        logger.info(f"Loaded new scenario: {scenario.name}")

    async def add_vessel_from_config(self, config: dict[str, Any]) -> None:
        """Add a vessel to the running emulation.

        Args:
            config: Vessel configuration dictionary

        Raises:
            AISDataFetchError: If emulator is not running
        """
        if not self.emulator:
            raise AISDataFetchError(
                "Emulator not initialized",
                source=self.name,
            )

        from app.emulator.vessel import EmulatedVessel

        vessel = EmulatedVessel.from_config(config)
        self.emulator.add_vessel(vessel)
        logger.info(f"Added vessel: {vessel.name} ({vessel.mmsi})")

    async def remove_vessel(self, mmsi: int) -> bool:
        """Remove a vessel from the emulation.

        Args:
            mmsi: MMSI of vessel to remove

        Returns:
            True if vessel was removed
        """
        if not self.emulator:
            return False

        return self.emulator.remove_vessel(mmsi)

    def get_emulator_stats(self) -> dict[str, Any]:
        """Get detailed emulator statistics.

        Returns:
            Dictionary with emulator statistics
        """
        if not self.emulator:
            return {"status": "not_initialized"}

        return self.emulator.get_statistics()
