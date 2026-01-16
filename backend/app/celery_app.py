"""Celery application configuration for Poseidon MSS.

Provides:
- Celery app instance with Redis broker
- Task routing configuration
- Beat schedule for periodic tasks
- Worker initialization with AIS manager
"""

import asyncio
import logging
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown
from kombu import Exchange, Queue

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global event loop for async operations in Celery worker
_worker_loop: asyncio.AbstractEventLoop = None
_worker_ais_initialized = False


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """Get or create the worker's event loop."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def run_async(coro):
    """Run an async coroutine in the worker's event loop.

    This properly handles running async code in Celery's sync context.
    """
    loop = get_worker_loop()
    return loop.run_until_complete(coro)


def create_celery_app() -> Celery:
    """Create and configure Celery application.

    Returns:
        Configured Celery app instance
    """
    app = Celery(
        "poseidon",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "app.tasks.ais_ingestion",
        ],
    )

    # Task configuration
    app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",

        # Timezone
        timezone="UTC",
        enable_utc=True,

        # Task execution
        task_track_started=True,
        task_time_limit=300,  # 5 minute hard limit
        task_soft_time_limit=240,  # 4 minute soft limit
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Worker configuration
        worker_prefetch_multiplier=1,
        worker_concurrency=4,

        # Result backend
        result_expires=3600,  # Results expire after 1 hour
        result_extended=True,

        # Task routing
        task_routes={
            "ais.*": {"queue": "ais"},
            "alerts.*": {"queue": "alerts"},
            "default": {"queue": "default"},
        },

        # Queue definitions
        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("ais", Exchange("ais"), routing_key="ais"),
            Queue("alerts", Exchange("alerts"), routing_key="alerts"),
        ),
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
    )

    # Beat schedule for periodic tasks
    app.conf.beat_schedule = {
        # Fetch AIS data every 60 seconds
        "ais-fetch-every-minute": {
            "task": "ais.fetch_and_process",
            "schedule": 60.0,
            "args": (),
            "options": {"queue": "ais"},
        },
        # Cleanup old positions daily at 3 AM UTC
        "ais-cleanup-daily": {
            "task": "ais.cleanup_old_positions",
            "schedule": crontab(hour=3, minute=0),
            "args": (30,),  # Keep 30 days
            "options": {"queue": "ais"},
        },
        # Update vessel risk scores every 5 minutes
        "ais-update-risk-scores": {
            "task": "ais.update_risk_scores",
            "schedule": 300.0,
            "args": (),
            "options": {"queue": "ais"},
        },
        # Detect collision risks every 30 seconds
        "ais-detect-collisions": {
            "task": "ais.detect_collisions",
            "schedule": 30.0,
            "args": (),
            "options": {"queue": "ais"},
        },
    }

    return app


# Global Celery app instance
celery_app = create_celery_app()


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize AIS manager when Celery worker process starts.

    This is called once per worker process, ensuring each worker
    has its own initialized AIS manager.
    """
    global _worker_ais_initialized

    logger.info("Initializing Celery worker process...")

    try:
        # Initialize the event loop
        loop = get_worker_loop()

        # Initialize AIS adapters
        from app.ais.startup import initialize_ais_adapters

        async def _init():
            manager = await initialize_ais_adapters()
            if manager:
                logger.info(
                    f"Worker AIS manager initialized with {manager.adapter_count} adapter(s)"
                )
            return manager

        manager = loop.run_until_complete(_init())
        _worker_ais_initialized = manager is not None

        logger.info("Celery worker process initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize worker process: {e}")
        _worker_ais_initialized = False


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    """Cleanup when Celery worker process shuts down."""
    global _worker_loop, _worker_ais_initialized

    logger.info("Shutting down Celery worker process...")

    try:
        if _worker_loop and not _worker_loop.is_closed():
            # Shutdown AIS adapters
            from app.ais.startup import shutdown_ais_adapters
            _worker_loop.run_until_complete(shutdown_ais_adapters())

            # Close the event loop
            _worker_loop.close()
            _worker_loop = None

        _worker_ais_initialized = False
        logger.info("Celery worker process shutdown complete")

    except Exception as e:
        logger.error(f"Error during worker shutdown: {e}")


def is_worker_initialized() -> bool:
    """Check if the worker's AIS manager is initialized."""
    return _worker_ais_initialized


def get_celery_app() -> Celery:
    """Get the global Celery app instance.

    Returns:
        Celery app instance
    """
    return celery_app
