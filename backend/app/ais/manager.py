"""AIS Adapter Manager for managing multiple data sources with failover.

Orchestrates data fetching from multiple AIS sources and handles
automatic failover when primary sources fail.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.ais.adapters.base import AISDataAdapter, AISDataFetchError, SourceInfo
from app.ais.models import AISMessage, BoundingBox

logger = logging.getLogger(__name__)


class AISAdapterManager:
    """Manages multiple AIS data sources with failover logic.

    Supports:
    - Primary/secondary/tertiary source configuration
    - Automatic failover on source failures
    - Health monitoring for all sources
    - Message deduplication across sources
    - Statistics tracking
    """

    def __init__(
        self,
        primary_adapter: AISDataAdapter,
        secondary_adapter: Optional[AISDataAdapter] = None,
        tertiary_adapter: Optional[AISDataAdapter] = None,
        failover_threshold: int = 3,
    ):
        """Initialize adapter manager.

        Args:
            primary_adapter: Primary data source (required)
            secondary_adapter: Secondary/fallback data source
            tertiary_adapter: Tertiary/fallback data source
            failover_threshold: Number of consecutive failures before failover
        """
        self.adapters: list[AISDataAdapter] = [primary_adapter]
        if secondary_adapter:
            self.adapters.append(secondary_adapter)
        if tertiary_adapter:
            self.adapters.append(tertiary_adapter)

        self.active_adapter_index = 0
        self.failover_threshold = failover_threshold

        # Statistics
        self._total_fetches = 0
        self._total_messages = 0
        self._failover_count = 0
        self._start_time: Optional[datetime] = None
        self._is_started = False

    @property
    def active_adapter(self) -> AISDataAdapter:
        """Get the currently active adapter."""
        return self.adapters[self.active_adapter_index]

    @property
    def active_adapter_name(self) -> str:
        """Get name of active adapter."""
        return self.active_adapter.name

    @property
    def is_started(self) -> bool:
        """Check if manager has been started."""
        return self._is_started

    @property
    def adapter_count(self) -> int:
        """Get number of configured adapters."""
        return len(self.adapters)

    async def start_all(self) -> None:
        """Initialize and start all adapters."""
        logger.info(f"Starting AIS Adapter Manager with {len(self.adapters)} adapters")
        self._start_time = datetime.utcnow()

        for adapter in self.adapters:
            try:
                await adapter.start()
                logger.info(f"  Started adapter: {adapter.name}")
            except Exception as e:
                logger.error(f"  Failed to start adapter {adapter.name}: {e}")

        self._is_started = True
        logger.info(f"Active adapter: {self.active_adapter.name}")

    async def stop_all(self) -> None:
        """Stop all adapters."""
        logger.info("Stopping AIS Adapter Manager")

        for adapter in self.adapters:
            try:
                await adapter.stop()
                logger.info(f"  Stopped adapter: {adapter.name}")
            except Exception as e:
                logger.error(f"  Error stopping adapter {adapter.name}: {e}")

        self._is_started = False

    async def fetch_data(
        self, bbox: Optional[BoundingBox] = None
    ) -> list[AISMessage]:
        """Fetch data from active adapter with automatic failover.

        Args:
            bbox: Optional bounding box to filter results

        Returns:
            List of AISMessage objects

        Raises:
            AISDataFetchError: If all adapters fail
        """
        self._total_fetches += 1

        # Try each adapter in order starting from active
        for attempt in range(len(self.adapters)):
            adapter = self.adapters[self.active_adapter_index]

            try:
                # Check health first
                if not await adapter.health_check():
                    raise AISDataFetchError(
                        f"Health check failed",
                        source=adapter.name,
                    )

                # Fetch data
                messages = await adapter.fetch_data(bbox)

                # Deduplicate messages
                messages = self._deduplicate_messages(messages)

                self._total_messages += len(messages)

                logger.debug(
                    f"Fetched {len(messages)} messages from {adapter.name}"
                )

                return messages

            except AISDataFetchError as e:
                logger.warning(f"Adapter {adapter.name} failed: {e}")

                # Check if we should failover
                if adapter.error_count >= self.failover_threshold:
                    if attempt < len(self.adapters) - 1:
                        self._perform_failover()
                    else:
                        logger.error("All adapters have failed")
                        raise AISDataFetchError(
                            "All AIS data sources failed",
                            source="manager",
                        )

        # Should not reach here, but just in case
        return []

    def _perform_failover(self) -> None:
        """Switch to the next available adapter."""
        old_index = self.active_adapter_index
        old_name = self.adapters[old_index].name

        self.active_adapter_index = (self.active_adapter_index + 1) % len(self.adapters)
        new_name = self.adapters[self.active_adapter_index].name

        self._failover_count += 1

        logger.warning(
            f"Failover: {old_name} -> {new_name} "
            f"(total failovers: {self._failover_count})"
        )

    def _deduplicate_messages(
        self, messages: list[AISMessage]
    ) -> list[AISMessage]:
        """Remove duplicate messages (same MMSI, keep highest quality).

        Args:
            messages: List of messages to deduplicate

        Returns:
            Deduplicated list of messages
        """
        seen: dict[int, AISMessage] = {}

        for msg in messages:
            if msg.mmsi not in seen:
                seen[msg.mmsi] = msg
            else:
                # Keep message with higher quality
                if msg.source_quality > seen[msg.mmsi].source_quality:
                    seen[msg.mmsi] = msg

        return list(seen.values())

    async def switch_adapter(self, adapter_name: str) -> bool:
        """Manually switch to a specific adapter.

        Args:
            adapter_name: Name of adapter to switch to

        Returns:
            True if switch was successful
        """
        for i, adapter in enumerate(self.adapters):
            if adapter.name == adapter_name:
                old_name = self.active_adapter.name
                self.active_adapter_index = i
                logger.info(f"Manual switch: {old_name} -> {adapter_name}")
                return True

        logger.warning(f"Adapter not found: {adapter_name}")
        return False

    async def get_all_source_info(self) -> list[SourceInfo]:
        """Get status of all configured sources.

        Returns:
            List of SourceInfo objects
        """
        return [adapter.get_source_info() for adapter in self.adapters]

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all adapters.

        Returns:
            Dictionary mapping adapter names to health status
        """
        results = {}
        for adapter in self.adapters:
            try:
                results[adapter.name] = await adapter.health_check()
            except Exception:
                results[adapter.name] = False
        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get manager statistics.

        Returns:
            Dictionary with manager statistics
        """
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "is_started": self._is_started,
            "adapter_count": len(self.adapters),
            "active_adapter": self.active_adapter.name,
            "active_adapter_index": self.active_adapter_index,
            "total_fetches": self._total_fetches,
            "total_messages": self._total_messages,
            "failover_count": self._failover_count,
            "uptime_seconds": uptime,
            "adapters": [
                {
                    "name": a.name,
                    "is_enabled": a.is_enabled,
                    "is_started": a.is_started,
                    "error_count": a.error_count,
                }
                for a in self.adapters
            ],
        }

    def __repr__(self) -> str:
        adapters_str = ", ".join(a.name for a in self.adapters)
        return (
            f"<AISAdapterManager(adapters=[{adapters_str}], "
            f"active={self.active_adapter.name})>"
        )


# Global manager instance (initialized on startup)
_manager: Optional[AISAdapterManager] = None


def get_ais_manager() -> Optional[AISAdapterManager]:
    """Get the global AIS manager instance.

    Returns:
        AISAdapterManager if initialized, None otherwise
    """
    return _manager


def set_ais_manager(manager: AISAdapterManager) -> None:
    """Set the global AIS manager instance.

    Args:
        manager: AISAdapterManager instance to use globally
    """
    global _manager
    _manager = manager
    logger.info(f"Global AIS manager set: {manager}")
