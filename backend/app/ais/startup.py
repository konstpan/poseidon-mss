"""AIS adapter initialization for application startup.

Provides:
- Adapter initialization based on environment
- Configuration loading from YAML
- Manager setup and lifecycle management
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from app.ais.adapters.base import AISDataAdapter
from app.ais.manager import AISAdapterManager, set_ais_manager, get_ais_manager
from app.ais.models import BoundingBox
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Default Thessaloniki bounding box - SEA ONLY (Thermaikos Gulf)
# The city is at ~40.64N, 22.94E - these coords are in the water south of the port
DEFAULT_BBOX = BoundingBox(
    min_lat=40.50,
    max_lat=40.60,
    min_lon=22.80,
    max_lon=22.98,
)

# Default scenario for development
DEFAULT_DEVELOPMENT_SCENARIO = "thessaloniki_normal_traffic"


def load_ais_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """Load AIS configuration from YAML file.

    Args:
        config_path: Path to config file (optional)

    Returns:
        Configuration dictionary
    """
    # Try to find config file
    search_paths = [
        config_path,
        "config/ais_sources.yaml",
        "../config/ais_sources.yaml",
        Path(__file__).parent.parent.parent / "config" / "ais_sources.yaml",
    ]

    for path in search_paths:
        if path and Path(path).exists():
            logger.info(f"Loading AIS config from: {path}")
            with open(path, "r") as f:
                return yaml.safe_load(f)

    # Return default config if no file found
    logger.info("No AIS config file found, using defaults")
    return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Get default AIS configuration based on environment.

    Returns:
        Default configuration dictionary
    """
    environment = settings.environment

    # Find scenario file - search multiple locations
    scenario_file = None
    scenario_filename = f"{DEFAULT_DEVELOPMENT_SCENARIO}.yaml"

    # Get the project root (poseidon-mss directory)
    # startup.py is at: backend/app/ais/startup.py
    project_root = Path(__file__).parent.parent.parent.parent

    scenario_paths = [
        # Docker container path (scenarios mounted at /app/scenarios)
        Path("/app/scenarios") / scenario_filename,
        # Absolute path from project root (for local development)
        project_root / "scenarios" / scenario_filename,
        # From backend directory
        Path("../scenarios") / scenario_filename,
        # From project root
        Path("scenarios") / scenario_filename,
        # Alternative: backend/scenarios (if scenarios are copied there)
        Path(__file__).parent.parent.parent / "scenarios" / scenario_filename,
    ]

    for path in scenario_paths:
        resolved = path.resolve() if hasattr(path, 'resolve') else Path(path).resolve()
        logger.debug(f"Checking scenario path: {resolved}")
        if resolved.exists():
            scenario_file = str(resolved)
            logger.info(f"Found scenario file: {scenario_file}")
            break

    if not scenario_file:
        logger.warning(f"Scenario file not found. Searched paths: {[str(p) for p in scenario_paths]}")

    if environment in ("development", "testing"):
        return {
            "primary_source": {
                "name": f"{environment.title()} Emulator",
                "type": "emulator",
                "enabled": True,
                "config": {
                    "scenario_file": scenario_file,
                    "num_vessels": 50 if environment == "development" else 20,
                    "update_interval_seconds": 30,
                    "default_bbox": {
                        "min_lat": DEFAULT_BBOX.min_lat,
                        "max_lat": DEFAULT_BBOX.max_lat,
                        "min_lon": DEFAULT_BBOX.min_lon,
                        "max_lon": DEFAULT_BBOX.max_lon,
                    },
                },
            },
            "secondary_source": None,
            "tertiary_source": None,
        }
    else:
        # Production/staging - emulator for now, can add real sources later
        return {
            "primary_source": {
                "name": f"{environment.title()} Emulator",
                "type": "emulator",
                "enabled": True,
                "config": {
                    "num_vessels": 100,
                    "update_interval_seconds": 30,
                    "default_bbox": {
                        "min_lat": DEFAULT_BBOX.min_lat,
                        "max_lat": DEFAULT_BBOX.max_lat,
                        "min_lon": DEFAULT_BBOX.min_lon,
                        "max_lon": DEFAULT_BBOX.max_lon,
                    },
                },
            },
            "secondary_source": None,
            "tertiary_source": None,
        }


def create_adapter_from_config(source_config: dict[str, Any]) -> Optional[AISDataAdapter]:
    """Create an adapter from configuration.

    Args:
        source_config: Source configuration dictionary

    Returns:
        Configured adapter or None
    """
    if not source_config or not source_config.get("enabled", True):
        return None

    adapter_type = source_config.get("type", "").lower()
    adapter_config = source_config.get("config", {}).copy()
    adapter_config["name"] = source_config.get("name", adapter_type)
    adapter_config["enabled"] = source_config.get("enabled", True)

    try:
        if adapter_type == "emulator":
            from app.ais.adapters.emulator import EmulatorAdapter
            return EmulatorAdapter(adapter_config)
        elif adapter_type == "aishub":
            # Future: AISHub adapter
            logger.warning("AISHub adapter not implemented, skipping")
            return None
        elif adapter_type == "marinetraffic":
            # Future: MarineTraffic adapter
            logger.warning("MarineTraffic adapter not implemented, skipping")
            return None
        else:
            logger.warning(f"Unknown adapter type: {adapter_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to create adapter: {e}")
        return None


async def initialize_ais_adapters(
    config_path: Optional[str] = None,
) -> Optional[AISAdapterManager]:
    """Initialize AIS adapters based on configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        Initialized AISAdapterManager or None
    """
    logger.info(f"Initializing AIS adapters for environment: {settings.environment}")

    # Load configuration
    config = load_ais_config(config_path)

    # Create adapters
    adapters = []

    for source_key in ["primary_source", "secondary_source", "tertiary_source"]:
        source_config = config.get(source_key)
        if source_config:
            adapter = create_adapter_from_config(source_config)
            if adapter:
                adapters.append(adapter)
                logger.info(f"Created adapter: {adapter.name}")

    if not adapters:
        logger.error("No AIS adapters could be created")
        return None

    # Create manager
    manager = AISAdapterManager(
        primary_adapter=adapters[0],
        secondary_adapter=adapters[1] if len(adapters) > 1 else None,
        tertiary_adapter=adapters[2] if len(adapters) > 2 else None,
        failover_threshold=3,
    )

    # Start all adapters
    await manager.start_all()

    # Set global manager
    set_ais_manager(manager)

    logger.info(
        f"AIS system initialized with {manager.adapter_count} adapter(s) "
        f"(active: {manager.active_adapter_name})"
    )

    return manager


async def shutdown_ais_adapters() -> None:
    """Shutdown all AIS adapters."""
    manager = get_ais_manager()

    if manager:
        logger.info("Shutting down AIS adapters...")
        await manager.stop_all()
        logger.info("AIS adapters shutdown complete")


async def reinitialize_ais_adapters(
    config_path: Optional[str] = None,
) -> Optional[AISAdapterManager]:
    """Reinitialize AIS adapters with new configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        New AISAdapterManager or None
    """
    # Shutdown existing
    await shutdown_ais_adapters()

    # Initialize new
    return await initialize_ais_adapters(config_path)
