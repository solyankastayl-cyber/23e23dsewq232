"""
WebSocket Manager
Sprint WS-1: Central connection & subscription manager
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Central WebSocket manager.
    
    Responsibilities:
    - Connection lifecycle (connect/disconnect)
    - Channel subscriptions per connection
    - Broadcast to subscribed clients
    - Heartbeat loop
    """
    
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = defaultdict(set)
        self._heartbeat_task = None
        self._running = False

    async def connect(self, websocket: WebSocket):
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        self.connections.add(websocket)
        logger.info("[WS] Client connected: %s", id(websocket))

    async def disconnect(self, websocket: WebSocket):
        """Unregister WebSocket connection and cleanup subscriptions."""
        self.connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info("[WS] Client disconnected: %s", id(websocket))

    async def subscribe(self, websocket: WebSocket, channels: list[str]):
        """Subscribe client to channels."""
        self.subscriptions[websocket].update(channels)
        logger.info("[WS] Client %s subscribed to: %s", id(websocket), channels)

    async def unsubscribe(self, websocket: WebSocket, channels: list[str]):
        """Unsubscribe client from channels."""
        for ch in channels:
            self.subscriptions[websocket].discard(ch)
        logger.info("[WS] Client %s unsubscribed from: %s", id(websocket), channels)

    async def send_json(self, websocket: WebSocket, payload: dict):
        """Send JSON message to specific client."""
        await websocket.send_text(json.dumps(payload))

    async def broadcast(self, channel: str, payload: dict):
        """
        Broadcast message to all clients subscribed to channel.
        
        Dead connections are automatically cleaned up.
        """
        dead = []

        for ws in list(self.connections):
            try:
                if channel not in self.subscriptions.get(ws, set()):
                    continue
                await self.send_json(ws, payload)
            except Exception as e:
                logger.warning("[WS] Broadcast failed for %s: %s", id(ws), e)
                dead.append(ws)

        # Cleanup dead connections
        for ws in dead:
            await self.disconnect(ws)

    async def start_heartbeat(self):
        """
        Start heartbeat loop (15s interval).
        
        Sends heartbeat to all connected clients.
        Cleans up dead connections.
        """
        if self._running:
            return

        self._running = True
        logger.info("[WS] Heartbeat loop started (15s interval)")

        while self._running:
            now = int(time.time() * 1000)
            payload = {
                "type": "heartbeat",
                "ts": now,
            }

            dead = []
            for ws in list(self.connections):
                try:
                    await self.send_json(ws, payload)
                except Exception:
                    dead.append(ws)

            for ws in dead:
                await self.disconnect(ws)

            await asyncio.sleep(15)

    async def stop(self):
        """Stop heartbeat loop."""
        self._running = False
        logger.info("[WS] Heartbeat loop stopped")
