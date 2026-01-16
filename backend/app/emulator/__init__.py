"""AIS emulator module for Poseidon MSS.

Provides scenario-based AIS data emulation for development and testing.
"""

from app.emulator.behaviors import (
    AnchoredBehavior,
    EvasiveBehavior,
    LoiterBehavior,
    MovementBehavior,
    Position,
    StraightBehavior,
    WaypointBehavior,
    create_behavior,
    haversine_distance,
)
from app.emulator.engine import (
    THESSALONIKI_BBOX,
    TrafficEmulator,
    create_default_emulator,
)
from app.emulator.scenarios import (
    ExpectedAlert,
    Scenario,
    ScenarioLoadError,
    ScenarioValidationError,
    list_scenarios,
    load_scenario,
)
from app.emulator.vessel import (
    EmulatedVessel,
    VesselConfig,
    generate_random_vessel,
)

__all__ = [
    # Engine
    "TrafficEmulator",
    "create_default_emulator",
    "THESSALONIKI_BBOX",
    # Vessel
    "EmulatedVessel",
    "VesselConfig",
    "generate_random_vessel",
    # Behaviors
    "MovementBehavior",
    "StraightBehavior",
    "LoiterBehavior",
    "WaypointBehavior",
    "EvasiveBehavior",
    "AnchoredBehavior",
    "Position",
    "create_behavior",
    "haversine_distance",
    # Scenarios
    "Scenario",
    "ExpectedAlert",
    "load_scenario",
    "list_scenarios",
    "ScenarioLoadError",
    "ScenarioValidationError",
]
