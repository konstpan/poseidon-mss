"""API routes for AIS source management.

Provides endpoints for:
- AIS source status and switching
- Emulator scenario management
- Source health monitoring
"""

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ais import get_ais_manager, BoundingBox
from app.ais.adapters.emulator import EmulatorAdapter
from app.emulator.scenarios import list_scenarios, get_scenario_info, load_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ais-sources", tags=["AIS Sources"])


class SourceStatusResponse(BaseModel):
    """Response model for source status."""

    active_source: str
    sources: list[dict[str, Any]]
    manager_stats: dict[str, Any]


class SourceSwitchRequest(BaseModel):
    """Request model for switching source."""

    source_name: str


class ScenarioListResponse(BaseModel):
    """Response model for scenario listing."""

    scenarios: list[dict[str, Any]]


class ScenarioLoadRequest(BaseModel):
    """Request model for loading a scenario."""

    scenario_name: str
    clear_existing: bool = True  # Clear existing vessels from DB when loading new scenario


class EmulatorStatsResponse(BaseModel):
    """Response model for emulator statistics."""

    stats: dict[str, Any]


@router.get("/status", response_model=SourceStatusResponse)
async def get_source_status() -> SourceStatusResponse:
    """Get status of all AIS data sources.

    Returns:
        Status of active source and all configured sources
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    source_info = await manager.get_all_source_info()

    return SourceStatusResponse(
        active_source=manager.active_adapter_name,
        sources=[info.to_dict() for info in source_info],
        manager_stats=manager.get_statistics(),
    )


@router.post("/switch")
async def switch_source(request: SourceSwitchRequest) -> dict[str, str]:
    """Manually switch to a different data source.

    Args:
        request: Source switch request with target source name

    Returns:
        Success message
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    success = await manager.switch_adapter(request.source_name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Source not found: {request.source_name}",
        )

    return {"message": f"Switched to source: {request.source_name}"}


@router.get("/health")
async def check_sources_health() -> dict[str, bool]:
    """Check health of all AIS data sources.

    Returns:
        Dictionary mapping source names to health status
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    return await manager.health_check_all()


def get_scenarios_dir() -> Path:
    """Get the scenarios directory, checking multiple possible locations.

    Returns:
        Path to scenarios directory
    """
    # Check Docker path first (when mounted at /app/scenarios)
    docker_path = Path("/app/scenarios")
    if docker_path.exists():
        logger.debug(f"Using Docker scenarios path: {docker_path}")
        return docker_path

    # Check relative path from working directory
    relative_path = Path("scenarios")
    if relative_path.exists():
        logger.debug(f"Using relative scenarios path: {relative_path.resolve()}")
        return relative_path

    # Check relative to this file's location (for local development)
    # ais_routes.py is at: backend/app/api/ais_routes.py
    # scenarios is at: scenarios/
    local_path = Path(__file__).parent.parent.parent.parent / "scenarios"
    if local_path.exists():
        logger.debug(f"Using local development scenarios path: {local_path}")
        return local_path

    # Default to relative path (may not exist)
    logger.warning(f"Scenarios directory not found. Checked: /app/scenarios, scenarios, {local_path}")
    return relative_path


@router.get("/emulator/scenarios", response_model=ScenarioListResponse)
async def list_emulator_scenarios() -> ScenarioListResponse:
    """List available emulator scenarios.

    Returns:
        List of scenario metadata
    """
    scenarios_dir = get_scenarios_dir()

    scenario_names = list_scenarios(scenarios_dir)

    scenarios = []
    for name in scenario_names:
        filepath = scenarios_dir / f"{name}.yaml"
        if filepath.exists():
            info = get_scenario_info(filepath)
            info["filename"] = f"{name}.yaml"
            scenarios.append(info)

    return ScenarioListResponse(scenarios=scenarios)


@router.post("/emulator/load-scenario")
async def load_emulator_scenario(request: ScenarioLoadRequest) -> dict[str, str]:
    """Load a different scenario into the emulator.

    Args:
        request: Scenario load request with scenario name and clear_existing flag

    Returns:
        Success message
    """
    return await _load_scenario(request.scenario_name, clear_existing=request.clear_existing)


@router.post(
    "/emulator/load-scenario/{name}",
    summary="Load scenario by name",
    description="""
Load a different scenario into the emulator using a path parameter.

**Path Parameters:**
- `name`: Scenario name (without .yaml extension)

**Query Parameters:**
- `clear_existing`: Clear existing vessels from database (default: true)

**Example:**
```
POST /api/v1/ais-sources/emulator/load-scenario/thessaloniki_normal_traffic
POST /api/v1/ais-sources/emulator/load-scenario/thessaloniki_normal_traffic?clear_existing=false
```

**Note:** This endpoint is an alternative to the request body version.
Only works when the active AIS source is the emulator.
    """,
    responses={
        400: {"description": "Active source is not an emulator"},
        404: {"description": "Scenario not found"},
        503: {"description": "AIS manager not initialized"},
    },
)
async def load_emulator_scenario_by_name(
    name: str,
    clear_existing: bool = True,
) -> dict[str, str]:
    """Load a scenario by name (path parameter version).

    Example:
        POST /api/v1/ais-sources/emulator/load-scenario/thessaloniki_normal_traffic

    Args:
        name: Scenario name (without .yaml extension)
        clear_existing: Whether to clear existing vessels from database

    Returns:
        Success message with loaded scenario name
    """
    return await _load_scenario(name, clear_existing=clear_existing)


async def _load_scenario(scenario_name: str, clear_existing: bool = True) -> dict[str, str]:
    """Internal function to load a scenario.

    Args:
        scenario_name: Name of scenario to load
        clear_existing: Whether to clear existing vessels from database

    Returns:
        Success message

    Raises:
        HTTPException: On various error conditions
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    # Check if active source is emulator
    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(
            status_code=400,
            detail="Active source is not an emulator",
        )

    # Build scenario path
    scenarios_dir = get_scenarios_dir()

    # Try with .yaml extension
    scenario_path = scenarios_dir / f"{scenario_name}.yaml"
    if not scenario_path.exists():
        scenario_path = scenarios_dir / f"{scenario_name}.yml"
        if not scenario_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Scenario not found: {scenario_name}",
            )

    try:
        # Clear existing vessels from database if requested
        if clear_existing:
            await _clear_vessel_data()
            logger.info("Cleared existing vessel data from database")

        # Load scenario in the backend's emulator
        await adapter.load_scenario(str(scenario_path))

        # Also trigger the Celery worker to reload the scenario
        # This ensures the worker's emulator (which feeds the DB) is in sync
        try:
            from app.tasks.ais_ingestion import reload_scenario_in_worker
            reload_scenario_in_worker.delay(scenario_name)
            logger.info(f"Triggered worker scenario reload for: {scenario_name}")
        except Exception as task_error:
            logger.warning(f"Failed to trigger worker reload (non-fatal): {task_error}")

        return {"message": f"Loaded scenario: {scenario_name}"}
    except Exception as e:
        logger.error(f"Failed to load scenario: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load scenario: {str(e)}",
        )


async def _clear_vessel_data() -> None:
    """Clear all vessel and position data from the database.

    This is used when loading a new scenario to remove old vessels.
    """
    from sqlalchemy import text
    from app.database.connection import get_async_session

    async with get_async_session() as session:
        # Delete positions first (foreign key constraint)
        await session.execute(text("DELETE FROM ais.vessel_positions"))
        # Then delete vessels
        await session.execute(text("DELETE FROM ais.vessels"))
        await session.commit()
        logger.info("Cleared vessel_positions and vessels tables")


@router.get("/emulator/stats", response_model=EmulatorStatsResponse)
async def get_emulator_stats() -> EmulatorStatsResponse:
    """Get detailed emulator statistics.

    Returns:
        Emulator statistics
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    # Check if active source is emulator
    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(
            status_code=400,
            detail="Active source is not an emulator",
        )

    return EmulatorStatsResponse(stats=adapter.get_emulator_stats())


@router.post("/emulator/add-vessel")
async def add_emulator_vessel(vessel_config: dict[str, Any]) -> dict[str, str]:
    """Add a vessel to the running emulation.

    Args:
        vessel_config: Vessel configuration dictionary

    Returns:
        Success message
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(
            status_code=400,
            detail="Active source is not an emulator",
        )

    # Validate required fields
    required_fields = ["mmsi", "name", "type", "start_position"]
    for field in required_fields:
        if field not in vessel_config:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}",
            )

    try:
        await adapter.add_vessel_from_config(vessel_config)
        return {
            "message": f"Added vessel: {vessel_config['name']} ({vessel_config['mmsi']})"
        }
    except Exception as e:
        logger.error(f"Failed to add vessel: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add vessel: {str(e)}",
        )


@router.delete("/emulator/vessel/{mmsi}")
async def remove_emulator_vessel(mmsi: int) -> dict[str, str]:
    """Remove a vessel from the emulation.

    Args:
        mmsi: MMSI of vessel to remove

    Returns:
        Success message
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(
            status_code=400,
            detail="Active source is not an emulator",
        )

    removed = await adapter.remove_vessel(mmsi)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Vessel not found: {mmsi}",
        )

    return {"message": f"Removed vessel: {mmsi}"}


@router.get("/emulator/vessels")
async def get_emulator_vessels() -> dict[str, list[dict[str, Any]]]:
    """Get current emulated vessels.

    Returns:
        List of current vessel states
    """
    manager = get_ais_manager()

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="AIS manager not initialized",
        )

    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(
            status_code=400,
            detail="Active source is not an emulator",
        )

    # Get current messages from emulator
    messages = await adapter.fetch_data()

    return {
        "vessels": [msg.to_dict() for msg in messages],
        "count": len(messages),
    }


@router.post("/detect-collisions")
async def trigger_collision_detection() -> dict[str, Any]:
    """Manually trigger collision detection.

    Useful for testing without waiting for the scheduled task.

    Returns:
        Detection results
    """
    from app.ais.collision_detection import run_collision_detection
    from app.database.connection import get_async_session

    try:
        async with get_async_session() as session:
            stats = await run_collision_detection(session)
            await session.commit()

        return {
            "status": "success",
            "risks_detected": stats["risks_detected"],
            "alerts_created": stats["alerts_created"],
            "alerts_updated": stats["alerts_updated"],
        }
    except Exception as e:
        logger.error(f"Error in collision detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Collision detection failed: {str(e)}",
        )
