"""Abstract base class for AIS data adapters.

Defines the interface that all AIS data sources must implement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.ais.models import AISMessage, BoundingBox

logger = logging.getLogger(__name__)


class AISDataFetchError(Exception):
    """Exception raised when fetching AIS data fails."""

    def __init__(self, message: str, source: Optional[str] = None):
        self.source = source
        super().__init__(f"[{source}] {message}" if source else message)


@dataclass
class SourceInfo:
    """Metadata about an AIS data source."""

    name: str
    source_type: str
    is_active: bool
    last_successful_fetch: Optional[datetime] = None
    error_count: int = 0
    total_messages_received: int = 0
    average_latency_seconds: float = 0.0
    quality_score: float = 1.0  # 0.0-1.0
    extra_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "type": self.source_type,
            "is_active": self.is_active,
            "last_successful_fetch": (
                self.last_successful_fetch.isoformat()
                if self.last_successful_fetch
                else None
            ),
            "error_count": self.error_count,
            "total_messages_received": self.total_messages_received,
            "average_latency_seconds": self.average_latency_seconds,
            "quality_score": self.quality_score,
            "extra_info": self.extra_info,
        }


class AISDataAdapter(ABC):
    """Abstract base class for all AIS data sources.

    Implementations must provide:
    - fetch_data(): Retrieve AIS messages from the source
    - health_check(): Verify the source is available
    - get_source_info(): Return metadata about the source
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Adapter-specific configuration dictionary
        """
        self.config = config
        self.name = config.get("name", "unknown")
        self.is_enabled = config.get("enabled", True)
        self._error_count = 0
        self._total_messages = 0
        self._last_fetch_time: Optional[datetime] = None
        self._latency_samples: list[float] = []
        self._is_started = False

    @abstractmethod
    async def fetch_data(
        self, bbox: Optional[BoundingBox] = None
    ) -> list[AISMessage]:
        """Fetch AIS data from the source.

        Args:
            bbox: Optional bounding box to filter results geographically

        Returns:
            List of AISMessage objects

        Raises:
            AISDataFetchError: If fetch fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_source_info(self) -> SourceInfo:
        """Get metadata about this data source.

        Returns:
            SourceInfo object with current statistics
        """
        pass

    async def start(self) -> None:
        """Initialize the adapter (e.g., open connections, start emulator).

        Override in subclasses that need initialization.
        """
        self._is_started = True
        logger.info(f"Adapter '{self.name}' started")

    async def stop(self) -> None:
        """Cleanup the adapter (e.g., close connections, stop emulator).

        Override in subclasses that need cleanup.
        """
        self._is_started = False
        logger.info(f"Adapter '{self.name}' stopped")

    def _record_success(self, message_count: int, latency_seconds: float = 0.0) -> None:
        """Record a successful fetch operation.

        Args:
            message_count: Number of messages received
            latency_seconds: Time taken to fetch data
        """
        self._last_fetch_time = datetime.utcnow()
        self._error_count = 0
        self._total_messages += message_count

        # Track latency (keep last 100 samples)
        self._latency_samples.append(latency_seconds)
        if len(self._latency_samples) > 100:
            self._latency_samples.pop(0)

    def _record_error(self) -> None:
        """Record a failed fetch operation."""
        self._error_count += 1

    def _get_average_latency(self) -> float:
        """Calculate average latency from samples."""
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)

    @property
    def is_started(self) -> bool:
        """Check if adapter has been started."""
        return self._is_started

    @property
    def error_count(self) -> int:
        """Get current consecutive error count."""
        return self._error_count

    @property
    def last_fetch_time(self) -> Optional[datetime]:
        """Get time of last successful fetch."""
        return self._last_fetch_time

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, enabled={self.is_enabled})>"
