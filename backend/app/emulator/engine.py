"""Traffic emulator engine for generating realistic vessel movements.

The main orchestrator for the AIS traffic simulation.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Optional

from app.ais.models import AISMessage, BoundingBox, VesselType
from app.emulator.behaviors import Position
from app.emulator.scenarios import Scenario
from app.emulator.vessel import EmulatedVessel, generate_random_vessel

logger = logging.getLogger(__name__)


class TrafficEmulator:
    """Traffic emulator for generating realistic vessel movements.

    Supports both scenario-based and random traffic generation.
    """

    def __init__(self, update_interval: int = 30):
        """Initialize traffic emulator.

        Args:
            update_interval: Seconds between position updates
        """
        self.vessels: list[EmulatedVessel] = []
        self.scenario: Optional[Scenario] = None
        self.is_running = False
        self.update_interval = update_interval
        self._update_task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None
        self._last_update_time: Optional[datetime] = None
        self._update_count = 0

    @property
    def vessel_count(self) -> int:
        """Get number of active vessels."""
        return len(self.vessels)

    @property
    def elapsed_seconds(self) -> float:
        """Get seconds elapsed since start."""
        if self._start_time is None:
            return 0.0
        return (datetime.utcnow() - self._start_time).total_seconds()

    @property
    def transmitting_vessels(self) -> list[EmulatedVessel]:
        """Get vessels that are currently transmitting AIS."""
        return [v for v in self.vessels if v.is_transmitting]

    async def load_scenario(self, scenario: Scenario) -> None:
        """Load a predefined scenario.

        Args:
            scenario: Scenario object to load
        """
        logger.info(f"Loading scenario: {scenario.name}")

        self.scenario = scenario
        self.update_interval = scenario.update_interval
        self.vessels = []

        # Create vessels from scenario configuration
        for vessel_config in scenario.vessels:
            try:
                vessel = EmulatedVessel.from_config(vessel_config)
                self.vessels.append(vessel)
                logger.debug(f"  Created vessel: {vessel.name} ({vessel.mmsi})")
            except Exception as e:
                logger.error(
                    f"  Failed to create vessel {vessel_config.get('name')}: {e}"
                )

        logger.info(
            f"Loaded {len(self.vessels)} vessels from scenario "
            f"(duration: {scenario.duration_minutes} minutes)"
        )

    async def generate_random_traffic(
        self,
        num_vessels: int,
        bbox: BoundingBox,
        vessel_types: Optional[list[VesselType]] = None,
    ) -> None:
        """Generate random traffic within a bounding box.

        Args:
            num_vessels: Number of vessels to generate
            bbox: Geographic bounding box
            vessel_types: Optional list of vessel types to use
        """
        logger.info(f"Generating {num_vessels} random vessels")

        self.scenario = None
        self.vessels = []

        bbox_tuple = (bbox.min_lat, bbox.max_lat, bbox.min_lon, bbox.max_lon)

        for i in range(num_vessels):
            mmsi = 999000000 + i
            vessel = generate_random_vessel(mmsi, bbox_tuple, vessel_types)
            self.vessels.append(vessel)

        logger.info(f"Generated {len(self.vessels)} random vessels")

    def add_vessel(self, vessel: EmulatedVessel) -> None:
        """Add a vessel to the emulation.

        Args:
            vessel: Vessel to add
        """
        # Check for duplicate MMSI
        existing = next((v for v in self.vessels if v.mmsi == vessel.mmsi), None)
        if existing:
            logger.warning(f"Replacing vessel with MMSI {vessel.mmsi}")
            self.vessels.remove(existing)

        self.vessels.append(vessel)
        logger.debug(f"Added vessel: {vessel.name} ({vessel.mmsi})")

    def remove_vessel(self, mmsi: int) -> bool:
        """Remove a vessel from the emulation.

        Args:
            mmsi: MMSI of vessel to remove

        Returns:
            True if vessel was found and removed
        """
        vessel = next((v for v in self.vessels if v.mmsi == mmsi), None)
        if vessel:
            self.vessels.remove(vessel)
            logger.debug(f"Removed vessel: {vessel.name} ({vessel.mmsi})")
            return True
        return False

    def get_vessel(self, mmsi: int) -> Optional[EmulatedVessel]:
        """Get a vessel by MMSI.

        Args:
            mmsi: MMSI to look up

        Returns:
            EmulatedVessel if found, None otherwise
        """
        return next((v for v in self.vessels if v.mmsi == mmsi), None)

    async def start(self) -> None:
        """Start the emulation."""
        if self.is_running:
            logger.warning("Emulator already running")
            return

        logger.info(
            f"Starting traffic emulator with {len(self.vessels)} vessels "
            f"(update interval: {self.update_interval}s)"
        )

        self.is_running = True
        self._start_time = datetime.utcnow()
        self._last_update_time = self._start_time
        self._update_count = 0

        # Start update loop
        self._update_task = asyncio.create_task(self._update_loop())

    async def stop(self) -> None:
        """Stop the emulation."""
        if not self.is_running:
            return

        logger.info("Stopping traffic emulator")

        self.is_running = False

        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None

        logger.info(
            f"Emulator stopped after {self._update_count} updates "
            f"({self.elapsed_seconds:.0f} seconds)"
        )

    async def _update_loop(self) -> None:
        """Main update loop for vessel positions."""
        logger.debug("Emulator update loop started")

        while self.is_running:
            try:
                await self.update_positions()
                self._update_count += 1

                # Check if scenario duration exceeded
                if self.scenario and self.elapsed_seconds >= self.scenario.duration_seconds:
                    logger.info("Scenario duration completed")
                    # Don't stop, just continue running
                    pass

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(1)

        logger.debug("Emulator update loop ended")

    async def update_positions(self) -> None:
        """Calculate and update positions for all vessels."""
        now = datetime.utcnow()
        time_delta = timedelta(seconds=self.update_interval)

        # Use actual time delta if available
        if self._last_update_time:
            actual_delta = now - self._last_update_time
            # Don't use deltas that are too large (e.g., after pause)
            if actual_delta.total_seconds() < self.update_interval * 2:
                time_delta = actual_delta

        self._last_update_time = now

        # Update each vessel
        for vessel in self.vessels:
            vessel.update(time_delta)

    async def get_ais_messages(
        self,
        bbox: Optional[BoundingBox] = None,
        include_non_transmitting: bool = False,
    ) -> list[AISMessage]:
        """Get current state of all vessels as AIS messages.

        Args:
            bbox: Optional bounding box to filter results
            include_non_transmitting: Include vessels with AIS gaps

        Returns:
            List of AISMessage objects
        """
        messages = []

        for vessel in self.vessels:
            # Skip non-transmitting vessels unless requested
            if not vessel.is_transmitting and not include_non_transmitting:
                continue

            # Skip vessels outside bounding box
            if bbox and not bbox.contains(vessel.latitude, vessel.longitude):
                continue

            messages.append(vessel.to_ais_message())

        return messages

    def get_statistics(self) -> dict[str, Any]:
        """Get emulator statistics.

        Returns:
            Dictionary with emulator statistics
        """
        # Count vessels by type
        type_counts: dict[str, int] = {}
        for vessel in self.vessels:
            type_name = vessel.vessel_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count vessels by behavior
        behavior_counts: dict[str, int] = {}
        for vessel in self.vessels:
            behavior = vessel._behavior.name
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1

        # Calculate speed statistics
        speeds = [v.speed for v in self.vessels]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0

        return {
            "is_running": self.is_running,
            "vessel_count": len(self.vessels),
            "transmitting_count": len(self.transmitting_vessels),
            "update_count": self._update_count,
            "elapsed_seconds": self.elapsed_seconds,
            "update_interval": self.update_interval,
            "scenario_name": self.scenario.name if self.scenario else None,
            "vessel_types": type_counts,
            "behaviors": behavior_counts,
            "average_speed_knots": round(avg_speed, 1),
        }

    def reset(self) -> None:
        """Reset the emulator state."""
        self.vessels = []
        self.scenario = None
        self._start_time = None
        self._last_update_time = None
        self._update_count = 0
        logger.info("Emulator reset")


# Default Thessaloniki area bounding box - SEA ONLY (Thermaikos Gulf)
# The city of Thessaloniki is at ~40.64N, 22.94E
# The gulf extends south from the city - these coordinates are in the water
THESSALONIKI_BBOX = BoundingBox(
    min_lat=40.50,  # Southern part of Thermaikos Gulf
    max_lat=40.60,  # Just south of the port (avoiding land)
    min_lon=22.80,  # Western part of gulf
    max_lon=22.98,  # Eastern part (avoiding Kalamaria peninsula)
)


async def create_default_emulator(
    num_vessels: int = 50,
    scenario_file: Optional[str] = None,
    update_interval: int = 30,
) -> TrafficEmulator:
    """Create and initialize a default emulator.

    Args:
        num_vessels: Number of random vessels (if no scenario)
        scenario_file: Optional path to scenario file
        update_interval: Update interval in seconds

    Returns:
        Initialized TrafficEmulator
    """
    from app.emulator.scenarios import load_scenario

    emulator = TrafficEmulator(update_interval=update_interval)

    if scenario_file:
        scenario = load_scenario(scenario_file)
        await emulator.load_scenario(scenario)
    else:
        await emulator.generate_random_traffic(num_vessels, THESSALONIKI_BBOX)

    return emulator
