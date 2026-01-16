"""AIS data ingestion Celery tasks.

Provides:
- Periodic AIS data fetching from configured sources
- Message processing and database storage
- Position caching in Redis
- Risk score updates
- Old position cleanup
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from sqlalchemy import text

from app.ais import BoundingBox, get_ais_manager, AISDataFetchError
from app.ais.processor import process_ais_messages, update_all_risk_scores
from app.cache import get_redis_client
from app.celery_app import run_async, is_worker_initialized
from app.database.connection import get_async_session

logger = logging.getLogger(__name__)

# Default Thessaloniki bounding box - Thermaikos Gulf (sea area)
# Must match the scenario vessel locations
DEFAULT_BBOX = BoundingBox(
    min_lat=40.48,
    max_lat=40.65,
    min_lon=22.78,
    max_lon=23.00,
)


# ==================== Main AIS Fetch Task ====================

@shared_task(
    name="ais.fetch_and_process",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
    acks_late=True,
)
def fetch_and_process_ais_data(
    self,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
) -> dict[str, Any]:
    """Celery task to fetch and process AIS data.

    This task is scheduled to run every 60 seconds via Celery Beat.
    It fetches AIS data from the active data source, processes each
    message, and stores vessel/position data in the database.

    The task is idempotent - running it multiple times will update
    existing records rather than creating duplicates.

    Args:
        self: Celery task instance (bound)
        min_lat, max_lat, min_lon, max_lon: Optional bounding box coordinates

    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Starting AIS fetch task")

    # Check if worker is initialized
    if not is_worker_initialized():
        logger.error(f"[{task_id}] Worker not initialized - AIS manager not available")
        return {
            "status": "error",
            "message": "Worker not initialized - AIS manager not available",
            "task_id": task_id,
        }

    # Build bounding box
    if all(x is not None for x in [min_lat, max_lat, min_lon, max_lon]):
        bbox = BoundingBox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )
    else:
        bbox = DEFAULT_BBOX

    try:
        result = run_async(_fetch_and_process_impl(bbox, task_id))
        return result

    except SoftTimeLimitExceeded:
        logger.warning(f"[{task_id}] Task soft time limit exceeded")
        return {
            "status": "timeout",
            "message": "Task exceeded soft time limit",
            "task_id": task_id,
        }

    except AISDataFetchError as e:
        logger.error(f"[{task_id}] AIS fetch error: {e}")

        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            return {
                "status": "error",
                "message": f"Max retries exceeded: {str(e)}",
                "task_id": task_id,
            }

    except Exception as e:
        logger.exception(f"[{task_id}] Unexpected error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }


async def _fetch_and_process_impl(
    bbox: BoundingBox,
    task_id: str,
) -> dict[str, Any]:
    """Internal async implementation of fetch and process.

    Args:
        bbox: Bounding box for filtering
        task_id: Task ID for logging

    Returns:
        Processing results dictionary
    """
    manager = get_ais_manager()

    if manager is None:
        logger.error(f"[{task_id}] AIS manager is None")
        return {
            "status": "error",
            "message": "AIS manager not initialized",
            "task_id": task_id,
        }

    if not manager.is_started:
        logger.error(f"[{task_id}] AIS manager not started")
        return {
            "status": "error",
            "message": "AIS manager not started",
            "task_id": task_id,
        }

    start_time = datetime.utcnow()

    # Fetch data from active source
    messages = await manager.fetch_data(bbox)
    fetch_time = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"[{task_id}] Fetched {len(messages)} messages from "
        f"{manager.active_adapter_name} in {fetch_time:.2f}s"
    )

    if not messages:
        return {
            "status": "success",
            "messages_fetched": 0,
            "vessels_processed": 0,
            "positions_stored": 0,
            "source": manager.active_adapter_name,
            "elapsed_seconds": fetch_time,
            "task_id": task_id,
        }

    # Process messages in database transaction
    async with get_async_session() as session:
        stats = await process_ais_messages(session, messages)
        await session.commit()

    # Cache positions in Redis (batch operation)
    cached = await _cache_positions_batch(messages)

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"[{task_id}] Processed {stats['vessels_processed']} vessels, "
        f"{stats['positions_stored']} positions, cached {cached} in {elapsed:.2f}s "
        f"(errors: {stats['errors']})"
    )

    return {
        "status": "success",
        "messages_fetched": len(messages),
        "vessels_processed": stats["vessels_processed"],
        "positions_stored": stats["positions_stored"],
        "positions_cached": cached,
        "errors": stats["errors"],
        "source": manager.active_adapter_name,
        "elapsed_seconds": elapsed,
        "task_id": task_id,
    }


async def _cache_positions_batch(messages) -> int:
    """Cache vessel positions in Redis.

    Args:
        messages: List of AIS messages

    Returns:
        Number of positions cached
    """
    redis_client = get_redis_client()
    if not redis_client or not redis_client.is_connected:
        return 0

    positions = []
    for msg in messages:
        positions.append({
            "mmsi": msg.mmsi,
            "latitude": msg.latitude,
            "longitude": msg.longitude,
            "speed": msg.speed_over_ground,
            "course": msg.course_over_ground,
            "heading": msg.heading,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        })

    return await redis_client.set_vessel_positions_batch(positions)


# ==================== Risk Score Update Task ====================

@shared_task(
    name="ais.update_risk_scores",
    bind=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=360,
)
def update_risk_scores(self) -> dict[str, Any]:
    """Celery task to update vessel risk scores.

    Updates risk scores for all vessels that have been seen
    in the last hour.

    Returns:
        Dictionary with update statistics
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Starting risk score update task")

    try:
        result = run_async(_update_risk_scores_impl(task_id))
        return result

    except Exception as e:
        logger.exception(f"[{task_id}] Error updating risk scores: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }


async def _update_risk_scores_impl(task_id: str) -> dict[str, Any]:
    """Internal async implementation of risk score update.

    Args:
        task_id: Task ID for logging

    Returns:
        Update statistics dictionary
    """
    start_time = datetime.utcnow()

    async with get_async_session() as session:
        stats = await update_all_risk_scores(session)
        await session.commit()

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"[{task_id}] Updated {stats['updated']} risk scores in {elapsed:.2f}s "
        f"(errors: {stats['errors']})"
    )

    return {
        "status": "success",
        "total_vessels": stats["total_vessels"],
        "updated": stats["updated"],
        "errors": stats["errors"],
        "elapsed_seconds": elapsed,
        "task_id": task_id,
    }


# ==================== Collision Detection Task ====================

@shared_task(
    name="ais.detect_collisions",
    bind=True,
    max_retries=2,
    soft_time_limit=60,
    time_limit=90,
)
def detect_collisions(
    self,
    cpa_threshold_nm: float = 0.5,
    tcpa_threshold_min: float = 30.0,
) -> dict[str, Any]:
    """Celery task to detect potential collision risks.

    Calculates CPA/TCPA for all moving vessel pairs and creates
    alerts when collision risk is detected.

    Args:
        self: Celery task instance (bound)
        cpa_threshold_nm: CPA threshold in nautical miles
        tcpa_threshold_min: Time window to consider in minutes

    Returns:
        Dictionary with detection statistics
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Starting collision detection task")

    try:
        result = run_async(_detect_collisions_impl(
            task_id, cpa_threshold_nm, tcpa_threshold_min
        ))
        return result

    except Exception as e:
        logger.exception(f"[{task_id}] Error in collision detection: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }


async def _detect_collisions_impl(
    task_id: str,
    cpa_threshold_nm: float,
    tcpa_threshold_min: float,
) -> dict[str, Any]:
    """Internal async implementation of collision detection.

    Args:
        task_id: Task ID for logging
        cpa_threshold_nm: CPA threshold
        tcpa_threshold_min: TCPA threshold

    Returns:
        Detection statistics dictionary
    """
    from app.ais.collision_detection import run_collision_detection

    start_time = datetime.utcnow()

    async with get_async_session() as session:
        stats = await run_collision_detection(
            session,
            cpa_threshold_nm=cpa_threshold_nm,
            tcpa_threshold_min=tcpa_threshold_min,
        )
        await session.commit()

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"[{task_id}] Collision detection complete: "
        f"{stats['risks_detected']} risks, {stats['alerts_created']} new alerts, "
        f"{stats['alerts_updated']} updated in {elapsed:.2f}s"
    )

    return {
        "status": "success",
        "risks_detected": stats["risks_detected"],
        "alerts_created": stats["alerts_created"],
        "alerts_updated": stats["alerts_updated"],
        "elapsed_seconds": elapsed,
        "task_id": task_id,
    }


# ==================== Cleanup Task ====================

@shared_task(
    name="ais.cleanup_old_positions",
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    time_limit=720,
)
def cleanup_old_positions(self, days_to_keep: int = 30) -> dict[str, Any]:
    """Celery task to clean up old position records.

    Deletes position records older than the specified number of days.
    This task is scheduled to run daily at 3 AM UTC.

    Args:
        self: Celery task instance (bound)
        days_to_keep: Number of days of positions to retain

    Returns:
        Dictionary with cleanup statistics
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Starting position cleanup task (keeping {days_to_keep} days)")

    try:
        result = run_async(_cleanup_impl(days_to_keep, task_id))
        return result

    except Exception as e:
        logger.exception(f"[{task_id}] Error cleaning up positions: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }


async def _cleanup_impl(days_to_keep: int, task_id: str) -> dict[str, Any]:
    """Internal async implementation of cleanup.

    Args:
        days_to_keep: Days of data to retain
        task_id: Task ID for logging

    Returns:
        Cleanup statistics dictionary
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    start_time = datetime.utcnow()

    async with get_async_session() as session:
        # Delete old positions in batches to avoid long locks
        total_deleted = 0
        batch_size = 10000

        while True:
            stmt = text("""
                DELETE FROM ais.vessel_positions
                WHERE id IN (
                    SELECT id FROM ais.vessel_positions
                    WHERE timestamp < :cutoff_date
                    LIMIT :batch_size
                )
            """)

            result = await session.execute(
                stmt,
                {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )
            await session.commit()

            deleted = result.rowcount or 0
            total_deleted += deleted

            if deleted < batch_size:
                break

            logger.debug(f"[{task_id}] Deleted {total_deleted} positions so far...")

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        f"[{task_id}] Cleaned up {total_deleted} positions in {elapsed:.2f}s "
        f"(cutoff: {cutoff_date.isoformat()})"
    )

    return {
        "status": "success",
        "deleted_count": total_deleted,
        "cutoff_date": cutoff_date.isoformat(),
        "elapsed_seconds": elapsed,
        "task_id": task_id,
    }


# ==================== Manager Statistics Task ====================

@shared_task(name="ais.get_manager_stats")
def get_manager_statistics() -> dict[str, Any]:
    """Celery task to get AIS manager statistics.

    Returns:
        Dictionary with manager statistics
    """
    manager = get_ais_manager()

    if manager is None:
        return {
            "status": "error",
            "message": "Manager not initialized",
            "worker_initialized": is_worker_initialized(),
        }

    stats = manager.get_statistics()
    stats["status"] = "success"
    stats["worker_initialized"] = is_worker_initialized()

    return stats


# ==================== Manual Trigger Task ====================

@shared_task(
    name="ais.trigger_fetch",
    bind=True,
)
def trigger_manual_fetch(
    self,
    scenario_name: Optional[str] = None,
) -> dict[str, Any]:
    """Manually trigger an AIS data fetch.

    Can optionally load a different scenario before fetching.

    Args:
        self: Celery task instance (bound)
        scenario_name: Optional scenario to load first

    Returns:
        Processing results dictionary
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Manual AIS fetch triggered")

    # Check if worker is initialized
    if not is_worker_initialized():
        return {
            "status": "error",
            "message": "Worker not initialized",
            "task_id": task_id,
        }

    try:
        if scenario_name:
            run_async(_load_scenario(scenario_name, task_id))

        # Run the main fetch directly (not via delay to get immediate result)
        return run_async(_fetch_and_process_impl(DEFAULT_BBOX, task_id))

    except Exception as e:
        logger.exception(f"[{task_id}] Error in manual fetch: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }


def _get_scenario_path(scenario_name: str) -> str:
    """Find the path to a scenario file.

    Args:
        scenario_name: Name of scenario (without extension)

    Returns:
        Path to scenario file

    Raises:
        FileNotFoundError: If scenario not found
    """
    from pathlib import Path

    # Check multiple locations
    search_paths = [
        # Docker mount path
        Path("/app/scenarios") / f"{scenario_name}.yaml",
        Path("/app/scenarios") / f"{scenario_name}.yml",
        # Relative to working directory
        Path("scenarios") / f"{scenario_name}.yaml",
        Path("scenarios") / f"{scenario_name}.yml",
        # Relative to this file
        Path(__file__).parent.parent.parent.parent / "scenarios" / f"{scenario_name}.yaml",
        Path(__file__).parent.parent.parent.parent / "scenarios" / f"{scenario_name}.yml",
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    raise FileNotFoundError(f"Scenario not found: {scenario_name}")


async def _load_scenario(scenario_name: str, task_id: str) -> None:
    """Load a scenario into the emulator.

    Args:
        scenario_name: Name of scenario to load
        task_id: Task ID for logging
    """
    from app.ais.adapters.emulator import EmulatorAdapter

    manager = get_ais_manager()
    if not manager:
        raise RuntimeError("AIS manager not initialized")

    adapter = manager.active_adapter
    if not isinstance(adapter, EmulatorAdapter):
        raise RuntimeError("Active source is not an emulator")

    scenario_path = _get_scenario_path(scenario_name)
    await adapter.load_scenario(scenario_path)
    logger.info(f"[{task_id}] Loaded scenario: {scenario_name}")


# ==================== Scenario Reload Task ====================

@shared_task(
    name="ais.reload_scenario",
    bind=True,
)
def reload_scenario_in_worker(self, scenario_name: str) -> dict[str, Any]:
    """Celery task to reload a scenario in the worker's emulator.

    This task should be called after loading a scenario via the API
    to sync the worker's emulator with the backend.

    Args:
        self: Celery task instance (bound)
        scenario_name: Name of scenario to load

    Returns:
        Result dictionary
    """
    task_id = self.request.id or "manual"
    logger.info(f"[{task_id}] Reloading scenario in worker: {scenario_name}")

    if not is_worker_initialized():
        return {
            "status": "error",
            "message": "Worker not initialized",
            "task_id": task_id,
        }

    try:
        run_async(_load_scenario(scenario_name, task_id))
        return {
            "status": "success",
            "message": f"Loaded scenario: {scenario_name}",
            "task_id": task_id,
        }

    except FileNotFoundError as e:
        logger.error(f"[{task_id}] Scenario not found: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }

    except Exception as e:
        logger.exception(f"[{task_id}] Error reloading scenario: {e}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
        }
