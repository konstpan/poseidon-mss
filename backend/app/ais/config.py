"""AIS source configuration management.

Handles loading AIS source configuration from YAML files
and creating appropriate adapters based on environment.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from app.ais.adapters.base import AISDataAdapter
from app.ais.models import BoundingBox

# Note: EmulatorAdapter is imported lazily in create_adapter() to avoid circular imports

logger = logging.getLogger(__name__)


class AISConfigError(Exception):
    """Exception raised when AIS configuration loading fails."""

    pass


# Default Thessaloniki bounding box - Thermaikos Gulf (sea area)
# Must match scenario vessel locations
DEFAULT_BBOX = {
    "min_lat": 40.48,
    "max_lat": 40.65,
    "min_lon": 22.78,
    "max_lon": 23.00,
}

# Default configuration for each environment
DEFAULT_CONFIGS = {
    "development": {
        "primary_source": {
            "name": "Development Emulator",
            "type": "emulator",
            "enabled": True,
            "config": {
                "scenario_file": None,
                "num_vessels": 50,
                "update_interval_seconds": 30,
                "default_bbox": DEFAULT_BBOX,
            },
        },
        "secondary_source": None,
        "tertiary_source": None,
    },
    "testing": {
        "primary_source": {
            "name": "Test Emulator",
            "type": "emulator",
            "enabled": True,
            "config": {
                "scenario_file": None,
                "num_vessels": 20,
                "update_interval_seconds": 10,
                "default_bbox": DEFAULT_BBOX,
            },
        },
        "secondary_source": None,
        "tertiary_source": None,
    },
    "staging": {
        "primary_source": {
            "name": "Staging Emulator",
            "type": "emulator",
            "enabled": True,
            "config": {
                "num_vessels": 100,
                "update_interval_seconds": 30,
                "default_bbox": DEFAULT_BBOX,
            },
        },
        "secondary_source": None,
        "tertiary_source": None,
    },
    "production": {
        "primary_source": {
            "name": "Production Emulator",
            "type": "emulator",
            "enabled": True,
            "config": {
                "num_vessels": 50,
                "update_interval_seconds": 30,
                "default_bbox": DEFAULT_BBOX,
            },
        },
        "secondary_source": None,
        "tertiary_source": None,
    },
}


def _substitute_env_vars(value: Any) -> Any:
    """Substitute environment variables in string values.

    Supports ${VAR_NAME} syntax.

    Args:
        value: Value to process

    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, "")
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(v) for v in value]
    return value


def load_config(
    config_file: Optional[str] = None,
    environment: Optional[str] = None,
) -> dict[str, Any]:
    """Load AIS configuration for specified environment.

    Args:
        config_file: Path to YAML config file (optional)
        environment: Environment name (development, testing, staging, production)

    Returns:
        Configuration dictionary for the environment

    Raises:
        AISConfigError: If configuration loading fails
    """
    # Determine environment
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    logger.info(f"Loading AIS configuration for environment: {environment}")

    # Try to load from config file if provided
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    all_config = yaml.safe_load(f)

                if environment in all_config:
                    config = all_config[environment]
                    # Substitute environment variables
                    config = _substitute_env_vars(config)
                    logger.info(f"Loaded configuration from {config_file}")
                    return config
                else:
                    logger.warning(
                        f"Environment '{environment}' not found in {config_file}, "
                        f"using defaults"
                    )
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse config file: {e}")
                raise AISConfigError(f"Invalid YAML in config file: {e}")

    # Use default configuration
    if environment not in DEFAULT_CONFIGS:
        logger.warning(
            f"Unknown environment '{environment}', using 'development' defaults"
        )
        environment = "development"

    return DEFAULT_CONFIGS[environment]


def create_adapter(
    adapter_type: str,
    config: dict[str, Any],
) -> AISDataAdapter:
    """Factory function to create appropriate adapter.

    Args:
        adapter_type: Type of adapter ('emulator', 'aishub', 'port_receiver')
        config: Adapter configuration

    Returns:
        Initialized AISDataAdapter

    Raises:
        AISConfigError: If adapter type is unknown
    """
    adapter_type = adapter_type.lower()

    if adapter_type == "emulator":
        # Lazy import to avoid circular imports
        from app.ais.adapters.emulator import EmulatorAdapter
        return EmulatorAdapter(config)
    elif adapter_type == "aishub":
        # TODO: Implement AISHubAdapter
        raise AISConfigError(
            "AISHub adapter not yet implemented - use emulator for now"
        )
    elif adapter_type == "marinetraffic":
        # TODO: Implement MarineTrafficAdapter
        raise AISConfigError(
            "MarineTraffic adapter not yet implemented - use emulator for now"
        )
    elif adapter_type == "port_receiver":
        # TODO: Implement PortReceiverAdapter
        raise AISConfigError(
            "Port receiver adapter not yet implemented - use emulator for now"
        )
    else:
        raise AISConfigError(f"Unknown adapter type: {adapter_type}")


def create_adapters_from_config(
    config: dict[str, Any],
) -> list[AISDataAdapter]:
    """Create all adapters from configuration dictionary.

    Args:
        config: Environment configuration dictionary

    Returns:
        List of configured adapters
    """
    adapters = []

    for source_key in ["primary_source", "secondary_source", "tertiary_source"]:
        source_config = config.get(source_key)

        if not source_config:
            continue

        if not source_config.get("enabled", True):
            logger.info(f"Skipping disabled source: {source_config.get('name')}")
            continue

        try:
            adapter_type = source_config["type"]
            adapter_config = source_config.get("config", {}).copy()
            adapter_config["name"] = source_config.get("name", adapter_type)
            adapter_config["enabled"] = source_config.get("enabled", True)

            adapter = create_adapter(adapter_type, adapter_config)
            adapters.append(adapter)
            logger.info(f"Created adapter: {adapter.name} ({adapter_type})")

        except Exception as e:
            logger.error(
                f"Failed to create adapter for {source_key}: {e}"
            )

    if not adapters:
        raise AISConfigError("No adapters could be created from configuration")

    return adapters


def create_default_adapter(
    scenario_file: Optional[str] = None,
    num_vessels: int = 50,
    update_interval: int = 30,
) -> AISDataAdapter:
    """Create a default emulator adapter for development.

    Args:
        scenario_file: Optional path to scenario file
        num_vessels: Number of random vessels (if no scenario)
        update_interval: Update interval in seconds

    Returns:
        Configured EmulatorAdapter
    """
    # Lazy import to avoid circular imports
    from app.ais.adapters.emulator import EmulatorAdapter

    config = {
        "name": "Default Emulator",
        "enabled": True,
        "scenario_file": scenario_file,
        "num_vessels": num_vessels,
        "update_interval_seconds": update_interval,
        "default_bbox": DEFAULT_BBOX,
    }

    return EmulatorAdapter(config)


# Configuration file path (relative to project root)
CONFIG_FILE_PATH = "config/ais_sources.yaml"


def get_config_file_path() -> Path:
    """Get the path to the AIS configuration file.

    Returns:
        Path to config file
    """
    # Try relative to current directory first
    config_path = Path(CONFIG_FILE_PATH)
    if config_path.exists():
        return config_path

    # Try relative to backend directory
    backend_config = Path(__file__).parent.parent.parent / CONFIG_FILE_PATH
    if backend_config.exists():
        return backend_config

    # Return default path even if it doesn't exist
    return config_path
