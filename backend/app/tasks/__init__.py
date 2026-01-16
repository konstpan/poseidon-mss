"""Celery tasks for Poseidon MSS.

Provides:
- AIS data ingestion tasks
- Position cleanup tasks
- Risk score update tasks

Usage:
    # Start Celery worker (initializes AIS manager automatically)
    celery -A app.celery_app worker -Q ais,default -l info

    # Start Celery beat (scheduler)
    celery -A app.celery_app beat -l info

    # Trigger task manually (Python)
    from app.tasks import fetch_and_process_ais_data
    result = fetch_and_process_ais_data.delay()
    print(result.get())  # Wait for result

Note:
    The Celery worker automatically initializes the AIS manager when
    the worker process starts (via worker_process_init signal).
    This is separate from the FastAPI app's initialization.
"""

# Import celery app from dedicated module
from app.celery_app import (
    celery_app,
    get_celery_app,
    run_async,
    is_worker_initialized,
)

# Import tasks to register them with Celery
from app.tasks.ais_ingestion import (
    fetch_and_process_ais_data,
    update_risk_scores,
    cleanup_old_positions,
    get_manager_statistics,
    trigger_manual_fetch,
)

__all__ = [
    # Celery app
    "celery_app",
    "get_celery_app",
    # Utilities
    "run_async",
    "is_worker_initialized",
    # AIS tasks
    "fetch_and_process_ais_data",
    "update_risk_scores",
    "cleanup_old_positions",
    "get_manager_statistics",
    "trigger_manual_fetch",
]
