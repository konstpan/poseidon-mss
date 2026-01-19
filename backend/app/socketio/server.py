"""Socket.IO server configuration and event handlers.

Provides:
- AsyncServer with Redis adapter for horizontal scaling
- Event emission functions that work from any process (web server or Celery)
- Connection/disconnection event handlers
"""

import logging
from typing import Any

import socketio

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis URL for Socket.IO pub/sub (use DB 3 to avoid conflicts)
_redis_url = settings.redis_url.replace("/0", "/3")

# Create Redis manager for cross-process communication
# This must be done at creation time, not after
try:
    _mgr = socketio.AsyncRedisManager(_redis_url)
    logger.info(f"Socket.IO Redis manager created: {_redis_url}")
except Exception as e:
    logger.warning(f"Socket.IO Redis manager creation failed, using memory: {e}")
    _mgr = None

# Create Socket.IO async server with Redis manager
sio = socketio.AsyncServer(
    client_manager=_mgr,
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)


async def init_socketio_server() -> socketio.AsyncServer:
    """Initialize Socket.IO server (called during app lifespan).

    Returns:
        The Socket.IO server instance
    """
    logger.info("Socket.IO server initialized")
    return sio


# Register event handlers
@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Handle client connection."""
    logger.info(f"Socket.IO client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    logger.info(f"Socket.IO client disconnected: {sid}")


async def emit_vessel_update(vessel_data: dict[str, Any]) -> None:
    """Emit vessel position update to all connected clients.

    Args:
        vessel_data: Vessel data dictionary matching frontend Vessel type
    """
    try:
        await sio.emit("vessel:update", vessel_data)
        logger.debug(f"Emitted vessel:update for MMSI {vessel_data.get('mmsi')}")
    except Exception as e:
        logger.warning(f"Failed to emit vessel:update: {e}")


async def emit_alert(alert_data: dict[str, Any]) -> None:
    """Emit new alert to all connected clients.

    Args:
        alert_data: Alert data dictionary matching frontend Alert type
    """
    try:
        await sio.emit("alert:new", alert_data)
        logger.info(f"Emitted alert:new for alert {alert_data.get('id')}")
    except Exception as e:
        logger.warning(f"Failed to emit alert:new: {e}")
