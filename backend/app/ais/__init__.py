"""AIS data processing module for Poseidon MSS.

This module provides:
- Source-agnostic AIS message representation
- Adapter pattern for multiple data sources
- Traffic emulator for development and testing
- Adapter manager with failover logic
- Message processing and database storage
"""

from app.ais.models import (
    AISMessage,
    BoundingBox,
    NavigationStatus,
    Position,
    VesselType,
)
from app.ais.adapters.base import (
    AISDataAdapter,
    AISDataFetchError,
    SourceInfo,
)
from app.ais.manager import (
    AISAdapterManager,
    get_ais_manager,
    set_ais_manager,
)
from app.ais.config import (
    create_adapter,
    create_adapters_from_config,
    create_default_adapter,
    load_config,
)

__all__ = [
    # Models
    "AISMessage",
    "BoundingBox",
    "NavigationStatus",
    "Position",
    "VesselType",
    # Adapters
    "AISDataAdapter",
    "AISDataFetchError",
    "SourceInfo",
    # Manager
    "AISAdapterManager",
    "get_ais_manager",
    "set_ais_manager",
    # Config
    "create_adapter",
    "create_adapters_from_config",
    "create_default_adapter",
    "load_config",
]
