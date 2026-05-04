"""
WebSocket Routes
Sprint WS-1: Single /ws endpoint with channel subscriptions
"""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .service_locator import get_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# WS-1: Only execution.feed supported
# WS-2: Adding positions.state and safety.state
# WS-3: Adding portfolio.summary and strategy.signals
SUPPORTED_CHANNELS = {
    "execution.feed",
    "positions.state",
    "safety.state",
    "portfolio.summary",
    "strategy.signals",
}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Single WebSocket endpoint for all channels.
    
    Client sends:
        {"type": "subscribe", "channels": ["execution.feed"]}
    
    Server responds:
        {"type": "subscribed", "channels": [...], "version": 1, "ts": ...}
    
    Events:
        {"type": "event", "channel": "execution.feed", "event": "ORDER_FILLED", ...}
    
    Heartbeat:
        {"type": "heartbeat", "ts": ...} every 15s
    """
    manager = get_ws_manager()
    await manager.connect(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            msg_type = msg.get("type")
            channels = msg.get("channels", [])

            if msg_type == "subscribe":
                # Filter valid/invalid channels
                valid = [c for c in channels if c in SUPPORTED_CHANNELS]
                invalid = [c for c in channels if c not in SUPPORTED_CHANNELS]

                # Subscribe to valid channels
                await manager.subscribe(websocket, valid)

                # Send confirmation
                await manager.send_json(
                    websocket,
                    {
                        "type": "subscribed",
                        "channels": valid,
                        "version": 1,
                        "ts": int(time.time() * 1000),
                    },
                )
                
                # WS-2: Send initial snapshot for state channels
                if "positions.state" in valid:
                    try:
                        from modules.core.db import get_db
                        db = get_db()

                        rows = await db.portfolio_positions.find({"status": "OPEN"}).to_list(length=100)
                        for r in rows:
                            r.pop("_id", None)

                        await manager.send_json(
                            websocket,
                            {
                                "type": "snapshot",
                                "channel": "positions.state",
                                "version": 1,
                                "ts": int(time.time() * 1000),
                                "data": rows,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[WS] Initial positions snapshot failed: {e}")
                
                if "safety.state" in valid:
                    try:
                        from modules.auto_safety.service_locator import get_auto_safety_service
                        service = get_auto_safety_service()
                        state = await service.get_state()

                        await manager.send_json(
                            websocket,
                            {
                                "type": "snapshot",
                                "channel": "safety.state",
                                "version": 1,
                                "ts": int(time.time() * 1000),
                                "data": state,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[WS] Initial safety snapshot failed: {e}")
                
                # WS-3: Send initial snapshot for portfolio.summary
                if "portfolio.summary" in valid:
                    try:
                        from modules.portfolio.service import get_portfolio_service
                        service = get_portfolio_service()
                        summary = await service.get_summary()
                        
                        # Convert Pydantic model to dict
                        summary_dict = summary.dict() if hasattr(summary, 'dict') else summary.__dict__
                        
                        await manager.send_json(
                            websocket,
                            {
                                "type": "snapshot",
                                "channel": "portfolio.summary",
                                "version": 1,
                                "ts": int(time.time() * 1000),
                                "data": summary_dict,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[WS-3] Initial portfolio.summary snapshot failed: {e}")
                
                # WS-3: Send initial snapshot for strategy.signals
                if "strategy.signals" in valid:
                    try:
                        from modules.strategy_visibility.service_locator import get_strategy_visibility_service
                        service = get_strategy_visibility_service()
                        signals = await service.get_live_signals(limit=50)
                        
                        await manager.send_json(
                            websocket,
                            {
                                "type": "snapshot",
                                "channel": "strategy.signals",
                                "version": 1,
                                "ts": int(time.time() * 1000),
                                "data": signals,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[WS-3] Initial strategy.signals snapshot failed: {e}")

                # Send error for invalid channels
                if invalid:
                    await manager.send_json(
                        websocket,
                        {
                            "type": "error",
                            "code": "UNKNOWN_CHANNEL",
                            "message": f"Unsupported channels: {invalid}",
                            "ts": int(time.time() * 1000),
                        },
                    )

            elif msg_type == "unsubscribe":
                valid = [c for c in channels if c in SUPPORTED_CHANNELS]
                await manager.unsubscribe(websocket, valid)

            else:
                await manager.send_json(
                    websocket,
                    {
                        "type": "error",
                        "code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unsupported message type: {msg_type}",
                        "ts": int(time.time() * 1000),
                    },
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.exception("[WS] Endpoint error: %s", e)
        await manager.disconnect(websocket)
