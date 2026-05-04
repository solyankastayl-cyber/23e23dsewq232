"""
WebSocket Broadcaster
Sprint WS-1: Unified broadcast interface
Sprint WS-3: Added snapshot debouncing with stable hash
"""

from __future__ import annotations

import logging
import time

from .hash_utils import SnapshotDebouncer

logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    """
    Unified broadcaster for WebSocket messages.
    
    Single point for broadcasting events and snapshots.
    Never let WS broadcasting break core logic.
    
    Sprint WS-3: Snapshots are debounced using stable hash.
    """
    
    def __init__(self, ws_manager):
        self.ws = ws_manager
        self._debouncer = SnapshotDebouncer()

    async def broadcast_event(self, channel: str, event: str, data: dict):
        """
        Broadcast event to channel.
        
        Args:
            channel: Channel name (e.g., "execution.feed")
            event: Event type (e.g., "ORDER_FILLED")
            data: Event payload
        """
        payload = {
            "type": "event",
            "channel": channel,
            "event": event,
            "version": 1,
            "ts": int(time.time() * 1000),
            "data": data,
        }
        
        try:
            await self.ws.broadcast(channel, payload)
            logger.debug("[WS] Event broadcast: %s / %s", channel, event)
        except Exception as e:
            logger.error("[WS] Broadcast failed: %s", e)

    async def broadcast_snapshot(self, channel: str, data, force: bool = False):
        """
        Broadcast state snapshot to channel.
        
        Sprint WS-3: Snapshots are debounced using stable hash.
        Only broadcasts if data hash changed (or force=True).
        
        Args:
            channel: Channel name (e.g., "positions.state", "portfolio.summary")
            data: Snapshot payload
            force: Force broadcast even if hash unchanged (default: False)
        """
        # Debounce check (skip if hash unchanged)
        if not force and not self._debouncer.should_broadcast(channel, data):
            return
        
        payload = {
            "type": "snapshot",
            "channel": channel,
            "version": 1,
            "ts": int(time.time() * 1000),
            "data": data,
        }
        
        try:
            await self.ws.broadcast(channel, payload)
            logger.debug("[WS] Snapshot broadcast: %s", channel)
        except Exception as e:
            logger.error("[WS] Broadcast failed: %s", e)
