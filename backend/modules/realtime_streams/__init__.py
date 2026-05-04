"""
Realtime Streams Module

PHASE 41.2 — WebSocket Realtime Streams

Channels:
- portfolio.updates
- orders.updates
- fills.updates
- alerts.updates
- dashboard.state
- safety.state
"""

from .stream_manager import (
    StreamManager,
    get_stream_manager,
)

from .stream_routes import router as stream_router

__all__ = [
    "StreamManager",
    "get_stream_manager",
    "stream_router",
]
