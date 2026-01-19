"""Socket.IO module for real-time WebSocket communication."""

from app.socketio.server import (
    sio,
    init_socketio_server,
    emit_vessel_update,
    emit_alert,
)

__all__ = [
    "sio",
    "init_socketio_server",
    "emit_vessel_update",
    "emit_alert",
]
