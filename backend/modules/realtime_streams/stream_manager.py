"""
Stream Manager

PHASE 41.2 — WebSocket Realtime Streams

In-memory pub/sub manager for real-time updates.
Manages WebSocket connections and channel subscriptions.

Channels:
- portfolio.updates
- orders.updates
- fills.updates
- alerts.updates
- dashboard.state
- safety.state
"""

import asyncio
import json
from typing import Optional, Dict, Set, List, Any
from datetime import datetime, timezone
from fastapi import WebSocket


class StreamManager:
    """
    Manages WebSocket connections and pub/sub channels.
    """

    def __init__(self):
        # channel -> set of websockets
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        # All connected websockets
        self._connections: Set[WebSocket] = set()
        # Message history per channel (ring buffer)
        self._history: Dict[str, List[Dict]] = {}
        self._history_limit = 100
        # Stats
        self._messages_sent = 0
        self._messages_published = 0

    # ═══════════════════════════════════════════════════════════
    # Connection Management
    # ═══════════════════════════════════════════════════════════

    async def connect(self, websocket: WebSocket, channels: Optional[List[str]] = None):
        """Accept WebSocket connection and subscribe to channels."""
        await websocket.accept()
        self._connections.add(websocket)

        if channels:
            for ch in channels:
                self._subscribe(websocket, ch)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket from all subscriptions."""
        self._connections.discard(websocket)
        for subs in self._subscriptions.values():
            subs.discard(websocket)

    def _subscribe(self, websocket: WebSocket, channel: str):
        if channel not in self._subscriptions:
            self._subscriptions[channel] = set()
        self._subscriptions[channel].add(websocket)

    def _unsubscribe(self, websocket: WebSocket, channel: str):
        if channel in self._subscriptions:
            self._subscriptions[channel].discard(websocket)

    # ═══════════════════════════════════════════════════════════
    # Publishing
    # ═══════════════════════════════════════════════════════════

    async def publish(self, channel: str, data: Any):
        """Publish message to all subscribers of a channel."""
        message = {
            "channel": channel,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._messages_published += 1

        # Save to history
        if channel not in self._history:
            self._history[channel] = []
        self._history[channel].append(message)
        if len(self._history[channel]) > self._history_limit:
            self._history[channel] = self._history[channel][-self._history_limit:]

        # Send to subscribers
        subscribers = self._subscriptions.get(channel, set()).copy()
        dead = []

        for ws in subscribers:
            try:
                await ws.send_json(message)
                self._messages_sent += 1
            except Exception:
                dead.append(ws)

        # Clean dead connections
        for ws in dead:
            self.disconnect(ws)

    async def broadcast(self, data: Any):
        """Broadcast message to ALL connected clients."""
        message = {
            "channel": "broadcast",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        dead = []
        for ws in self._connections.copy():
            try:
                await ws.send_json(message)
                self._messages_sent += 1
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    # ═══════════════════════════════════════════════════════════
    # Convenience publishers
    # ═══════════════════════════════════════════════════════════

    async def publish_portfolio_update(self, data: Dict):
        await self.publish("portfolio.updates", data)

    async def publish_order_update(self, data: Dict):
        await self.publish("orders.updates", data)

    async def publish_fill_update(self, data: Dict):
        await self.publish("fills.updates", data)

    async def publish_alert(self, data: Dict):
        await self.publish("alerts.updates", data)

    async def publish_dashboard_state(self, data: Dict):
        await self.publish("dashboard.state", data)

    async def publish_safety_state(self, data: Dict):
        await self.publish("safety.state", data)

    # ═══════════════════════════════════════════════════════════
    # Status
    # ═══════════════════════════════════════════════════════════

    def get_stats(self) -> Dict:
        return {
            "connections": len(self._connections),
            "channels": list(self._subscriptions.keys()),
            "subscribers_per_channel": {
                ch: len(subs) for ch, subs in self._subscriptions.items()
            },
            "messages_published": self._messages_published,
            "messages_sent": self._messages_sent,
            "history_size": {
                ch: len(msgs) for ch, msgs in self._history.items()
            },
        }

    def get_history(self, channel: str, limit: int = 50) -> List[Dict]:
        return self._history.get(channel, [])[-limit:]

    def get_channels(self) -> List[str]:
        return list(self._subscriptions.keys())


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
