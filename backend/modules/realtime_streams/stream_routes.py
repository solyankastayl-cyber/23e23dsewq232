"""
Realtime Stream Routes

PHASE 41.2 — WebSocket Realtime Streams

Endpoints:
- WS  /api/v1/ws/stream            - WebSocket for real-time updates
- GET  /api/v1/streams/status       - Stream manager status
- GET  /api/v1/streams/channels     - Available channels
- GET  /api/v1/streams/history/{ch} - Channel message history
- POST /api/v1/streams/publish      - Publish message (internal)
- GET  /api/v1/streams/health       - Health check
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel

from .stream_manager import get_stream_manager


router = APIRouter(tags=["Realtime Streams"])


# ══════════════════════════════════════════════════════════════
# WebSocket Endpoint
# ══════════════════════════════════════════════════════════════

@router.websocket("/api/v1/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Connect and send a subscribe message:
    {"action": "subscribe", "channels": ["portfolio.updates", "orders.updates"]}

    Available channels:
    - portfolio.updates
    - orders.updates
    - fills.updates
    - alerts.updates
    - dashboard.state
    - safety.state
    """
    manager = get_stream_manager()
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "subscribe":
                channels = data.get("channels", [])
                for ch in channels:
                    manager._subscribe(websocket, ch)
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": channels,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif action == "unsubscribe":
                channels = data.get("channels", [])
                for ch in channels:
                    manager._unsubscribe(websocket, ch)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "channels": channels,
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ══════════════════════════════════════════════════════════════
# REST Endpoints
# ══════════════════════════════════════════════════════════════

class PublishRequest(BaseModel):
    channel: str
    data: dict


@router.get("/api/v1/streams/status")
async def get_stream_status():
    """Get stream manager status."""
    try:
        manager = get_stream_manager()
        stats = manager.get_stats()

        return {
            "status": "ok",
            "phase": "41",
            "streams": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/streams/channels")
async def get_channels():
    """Get available channels."""
    return {
        "status": "ok",
        "phase": "41",
        "available_channels": [
            "portfolio.updates",
            "orders.updates",
            "fills.updates",
            "alerts.updates",
            "dashboard.state",
            "safety.state",
        ],
        "active_channels": get_stream_manager().get_channels(),
    }


@router.get("/api/v1/streams/history/{channel}")
async def get_channel_history(
    channel: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get message history for a channel."""
    try:
        manager = get_stream_manager()
        history = manager.get_history(channel, limit=limit)

        return {
            "status": "ok",
            "phase": "41",
            "channel": channel,
            "count": len(history),
            "messages": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/streams/publish")
async def publish_message(request: PublishRequest):
    """Publish message to a channel (internal use)."""
    try:
        manager = get_stream_manager()
        await manager.publish(request.channel, request.data)

        return {
            "status": "ok",
            "phase": "41",
            "channel": request.channel,
            "published": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/streams/health")
async def streams_health():
    """Streams health check."""
    try:
        manager = get_stream_manager()
        stats = manager.get_stats()

        return {
            "status": "ok",
            "phase": "41",
            "module": "Realtime Streams",
            "connections": stats["connections"],
            "channels": len(stats["channels"]),
            "messages_published": stats["messages_published"],
            "endpoints": [
                "WS  /api/v1/ws/stream",
                "GET  /api/v1/streams/status",
                "GET  /api/v1/streams/channels",
                "GET  /api/v1/streams/history/{channel}",
                "POST /api/v1/streams/publish",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
