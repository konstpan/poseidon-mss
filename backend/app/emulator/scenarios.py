"""Scenario loading and management for traffic emulator.

Handles loading YAML scenario files and validating their structure.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class ScenarioLoadError(Exception):
    """Exception raised when loading a scenario fails."""

    pass


class ScenarioValidationError(Exception):
    """Exception raised when scenario validation fails."""

    pass


@dataclass
class ExpectedAlert:
    """Expected alert for scenario testing."""

    alert_type: str
    severity: str
    expected_after_seconds: int
    zone_code: Optional[str] = None
    vessel_mmsi: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    """Scenario definition loaded from YAML."""

    name: str
    description: str
    duration_minutes: int
    update_interval: int  # seconds
    vessels: list[dict[str, Any]]
    expected_alerts: list[ExpectedAlert] = field(default_factory=list)
    bounding_box: Optional[dict[str, float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> int:
        """Get duration in seconds."""
        return self.duration_minutes * 60

    @property
    def vessel_count(self) -> int:
        """Get number of vessels in scenario."""
        return len(self.vessels)


def validate_vessel_config(vessel: dict[str, Any], index: int) -> None:
    """Validate a vessel configuration.

    Args:
        vessel: Vessel configuration dictionary
        index: Index in vessels list for error messages

    Raises:
        ScenarioValidationError: If validation fails
    """
    required_fields = ["mmsi", "name", "type", "start_position"]

    for field_name in required_fields:
        if field_name not in vessel:
            raise ScenarioValidationError(
                f"Vessel {index}: missing required field '{field_name}'"
            )

    # Validate MMSI
    mmsi = vessel["mmsi"]
    if not isinstance(mmsi, int) or not (100000000 <= mmsi <= 999999999):
        raise ScenarioValidationError(
            f"Vessel {index}: invalid MMSI '{mmsi}' (must be 9-digit integer)"
        )

    # Validate start_position
    start_pos = vessel["start_position"]
    if not isinstance(start_pos, list) or len(start_pos) != 2:
        raise ScenarioValidationError(
            f"Vessel {index}: start_position must be [lat, lon] list"
        )

    lat, lon = start_pos
    if not (-90 <= lat <= 90):
        raise ScenarioValidationError(
            f"Vessel {index}: invalid latitude {lat}"
        )
    if not (-180 <= lon <= 180):
        raise ScenarioValidationError(
            f"Vessel {index}: invalid longitude {lon}"
        )

    # Validate vessel type
    valid_types = [
        "cargo", "tanker", "passenger", "fishing", "military",
        "pleasure_craft", "high_speed_craft", "tug", "pilot_vessel",
        "search_and_rescue", "dredger", "sailing", "other", "unknown"
    ]
    vessel_type = vessel["type"].lower()
    if vessel_type not in valid_types:
        raise ScenarioValidationError(
            f"Vessel {index}: invalid type '{vessel_type}'. "
            f"Valid types: {valid_types}"
        )

    # Validate behavior
    valid_behaviors = ["straight", "loiter", "waypoints", "evasive", "anchored"]
    behavior = vessel.get("behavior", "straight").lower()
    if behavior not in valid_behaviors:
        raise ScenarioValidationError(
            f"Vessel {index}: invalid behavior '{behavior}'. "
            f"Valid behaviors: {valid_behaviors}"
        )

    # Validate waypoints if behavior is waypoints
    if behavior == "waypoints":
        waypoints = vessel.get("waypoints")
        if not waypoints or not isinstance(waypoints, list):
            raise ScenarioValidationError(
                f"Vessel {index}: waypoints behavior requires 'waypoints' list"
            )
        for wp_idx, wp in enumerate(waypoints):
            if not isinstance(wp, list) or len(wp) != 2:
                raise ScenarioValidationError(
                    f"Vessel {index}, waypoint {wp_idx}: must be [lat, lon] list"
                )

    # Validate speed
    speed = vessel.get("speed", 10.0)
    if not isinstance(speed, (int, float)) or speed < 0 or speed > 50:
        raise ScenarioValidationError(
            f"Vessel {index}: speed must be between 0 and 50 knots"
        )

    # Validate course
    course = vessel.get("course", 0.0)
    if not isinstance(course, (int, float)) or course < 0 or course >= 360:
        raise ScenarioValidationError(
            f"Vessel {index}: course must be between 0 and 359 degrees"
        )


def validate_scenario(data: dict[str, Any]) -> None:
    """Validate scenario data structure.

    Args:
        data: Parsed YAML data

    Raises:
        ScenarioValidationError: If validation fails
    """
    # Required top-level fields
    required_fields = ["name", "description", "duration_minutes", "vessels"]
    for field_name in required_fields:
        if field_name not in data:
            raise ScenarioValidationError(f"Missing required field: {field_name}")

    # Validate duration
    duration = data["duration_minutes"]
    if not isinstance(duration, int) or duration <= 0:
        raise ScenarioValidationError(
            f"duration_minutes must be positive integer, got {duration}"
        )

    # Validate update_interval if present
    update_interval = data.get("update_interval", 30)
    if not isinstance(update_interval, int) or update_interval <= 0:
        raise ScenarioValidationError(
            f"update_interval must be positive integer, got {update_interval}"
        )

    # Validate vessels
    vessels = data["vessels"]
    if not isinstance(vessels, list) or len(vessels) == 0:
        raise ScenarioValidationError("vessels must be a non-empty list")

    # Check for duplicate MMSIs
    mmsis = [v.get("mmsi") for v in vessels]
    if len(mmsis) != len(set(mmsis)):
        raise ScenarioValidationError("Duplicate MMSI detected in vessels")

    # Validate each vessel
    for idx, vessel in enumerate(vessels):
        validate_vessel_config(vessel, idx)

    # Validate expected_alerts if present
    expected_alerts = data.get("expected_alerts", [])
    for idx, alert in enumerate(expected_alerts):
        if "type" not in alert:
            raise ScenarioValidationError(
                f"Expected alert {idx}: missing 'type' field"
            )
        if "severity" not in alert:
            raise ScenarioValidationError(
                f"Expected alert {idx}: missing 'severity' field"
            )


def load_scenario(filepath: str | Path) -> Scenario:
    """Load scenario from YAML file.

    Args:
        filepath: Path to scenario YAML file

    Returns:
        Parsed Scenario object

    Raises:
        ScenarioLoadError: If file cannot be loaded
        ScenarioValidationError: If scenario validation fails
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise ScenarioLoadError(f"Scenario file not found: {filepath}")

    if not filepath.suffix in (".yaml", ".yml"):
        raise ScenarioLoadError(
            f"Scenario file must have .yaml or .yml extension: {filepath}"
        )

    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ScenarioLoadError(f"Failed to parse YAML: {e}")

    if data is None:
        raise ScenarioLoadError("Scenario file is empty")

    # Validate scenario
    validate_scenario(data)

    # Parse expected alerts
    expected_alerts = []
    for alert_data in data.get("expected_alerts", []):
        expected_alerts.append(
            ExpectedAlert(
                alert_type=alert_data["type"],
                severity=alert_data["severity"],
                expected_after_seconds=alert_data.get("expected_after_seconds", 0),
                zone_code=alert_data.get("zone_code"),
                vessel_mmsi=alert_data.get("vessel_mmsi"),
                extra={
                    k: v for k, v in alert_data.items()
                    if k not in ["type", "severity", "expected_after_seconds", "zone_code", "vessel_mmsi"]
                },
            )
        )

    # Create scenario
    scenario = Scenario(
        name=data["name"],
        description=data["description"],
        duration_minutes=data["duration_minutes"],
        update_interval=data.get("update_interval", 30),
        vessels=data["vessels"],
        expected_alerts=expected_alerts,
        bounding_box=data.get("bounding_box"),
        metadata=data.get("metadata", {}),
    )

    logger.info(
        f"Loaded scenario: {scenario.name} "
        f"({scenario.vessel_count} vessels, {scenario.duration_minutes} minutes)"
    )

    return scenario


def list_scenarios(scenarios_dir: str | Path = "scenarios") -> list[str]:
    """List available scenario files.

    Args:
        scenarios_dir: Directory containing scenario files

    Returns:
        List of scenario names (without extension)
    """
    scenarios_dir = Path(scenarios_dir)

    if not scenarios_dir.exists():
        return []

    scenarios = []
    for filepath in scenarios_dir.glob("*.yaml"):
        scenarios.append(filepath.stem)
    for filepath in scenarios_dir.glob("*.yml"):
        scenarios.append(filepath.stem)

    return sorted(set(scenarios))


def get_scenario_info(filepath: str | Path) -> dict[str, Any]:
    """Get basic info about a scenario without fully loading it.

    Args:
        filepath: Path to scenario file

    Returns:
        Dictionary with scenario metadata
    """
    filepath = Path(filepath)

    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)

        return {
            "name": data.get("name", filepath.stem),
            "description": data.get("description", ""),
            "duration_minutes": data.get("duration_minutes", 0),
            "vessel_count": len(data.get("vessels", [])),
            "has_expected_alerts": len(data.get("expected_alerts", [])) > 0,
        }
    except Exception as e:
        return {
            "name": filepath.stem,
            "error": str(e),
        }
