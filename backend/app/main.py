"""Main FastAPI application entry point.

Initializes:
- FastAPI application with CORS middleware
- Database connection
- AIS adapter manager
- Redis cache client
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.socketio import sio, init_socketio_server
from app.config import get_settings
from app.database.connection import (
    check_database_connection,
    close_db_engine,
    init_db_engine,
)
from app.ais.startup import (
    initialize_ais_adapters,
    shutdown_ais_adapters,
)
from app.ais import get_ais_manager
from app.cache import (
    init_redis_client,
    close_redis_client,
    get_redis_client,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Starting Poseidon Maritime Security System")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database
    logger.info("Initializing database connection...")
    await init_db_engine()

    # Initialize Redis cache
    logger.info("Initializing Redis cache...")
    try:
        redis_client = await init_redis_client()
        app.state.redis_client = redis_client
        logger.info("Redis cache initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        app.state.redis_client = None

    # Initialize Socket.IO server
    logger.info("Initializing Socket.IO server...")
    try:
        await init_socketio_server()
        logger.info("Socket.IO server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Socket.IO: {e}")

    # Initialize AIS system
    logger.info("Initializing AIS system...")
    try:
        ais_manager = await initialize_ais_adapters()
        app.state.ais_manager = ais_manager
        if ais_manager:
            logger.info(
                f"AIS system initialized with {ais_manager.adapter_count} adapter(s)"
            )
        else:
            logger.warning("AIS system initialization failed - running without AIS data")
    except Exception as e:
        logger.error(f"Failed to initialize AIS system: {e}")
        app.state.ais_manager = None

    logger.info("=" * 60)
    logger.info("Poseidon MSS startup complete")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down Poseidon Maritime Security System")
    logger.info("=" * 60)

    # Shutdown AIS system
    logger.info("Shutting down AIS system...")
    await shutdown_ais_adapters()

    # Close Redis
    logger.info("Closing Redis connection...")
    await close_redis_client()

    # Close database
    logger.info("Closing database connection...")
    await close_db_engine()

    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="""
## Poseidon Maritime Security System API

A comprehensive API for vessel tracking, AIS data processing, and maritime security monitoring.

### Features
- **Vessel Tracking**: Real-time vessel positions and historical tracks
- **Security Zones**: Geofenced zone management with GeoJSON support
- **AIS Sources**: Multiple AIS data source management including emulator
- **Alerts**: Security alert monitoring and management

### API Versioning
All endpoints are prefixed with `/api/v1`.

### Authentication
Currently no authentication required (development mode).
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_tags=[
        {
            "name": "Vessels",
            "description": "Vessel tracking and position data endpoints",
        },
        {
            "name": "Security Zones",
            "description": "Geofenced security zone management",
        },
        {
            "name": "AIS Sources",
            "description": "AIS data source management and emulator control",
        },
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """Health check endpoint for container orchestration."""
    # Check database
    db_healthy = await check_database_connection()

    # Check AIS system
    ais_manager = get_ais_manager()
    ais_healthy = ais_manager is not None and ais_manager.is_started

    # Check Redis
    redis_client = get_redis_client()
    redis_healthy = redis_client is not None and await redis_client.health_check()

    overall_healthy = db_healthy and ais_healthy

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "service": "poseidon-mss",
        "environment": settings.environment,
        "database": db_healthy,
        "ais_system": ais_healthy,
        "redis_cache": redis_healthy,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "disabled",
    }


@app.get("/status")
async def system_status() -> dict:
    """Detailed system status endpoint."""
    # AIS status
    ais_manager = get_ais_manager()
    ais_status = None
    if ais_manager:
        ais_status = ais_manager.get_statistics()

    # Redis status
    redis_client = get_redis_client()
    redis_status = None
    if redis_client:
        redis_status = await redis_client.get_stats()

    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "ais": ais_status,
        "redis": redis_status,
    }


# Wrap FastAPI app with Socket.IO for WebSocket support
_fastapi_app = app
app = socketio.ASGIApp(sio, _fastapi_app)
