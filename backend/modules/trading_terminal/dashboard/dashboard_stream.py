"""
Dashboard Stream (TR6)
======================

WebSocket streaming for live dashboard updates.
"""

import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional, Callable
from dataclasses import dataclass, field
import uuid

from .dashboard_types import DashboardEvent, DashboardEventType


@dataclass
class StreamClient:
    """WebSocket client info"""
    client_id: str
    connected_at: datetime
    subscriptions: Set[str] = field(default_factory=set)


class DashboardStream:
    """
    Manages WebSocket connections and event streaming.
    
    Events:
    - portfolio_updated
    - risk_alert
    - strategy_switched
    - trade_filled
    - account_health_changed
    - kill_switch_triggered
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Connected clients
        self._clients: Dict[str, StreamClient] = {}
        
        # Event queue
        self._event_queue: List[DashboardEvent] = []
        self._max_queue_size = 100
        
        # Event handlers
        self._handlers: Dict[DashboardEventType, List[Callable]] = {}
        
        # WebSocket connections (for FastAPI)
        self._websockets: Dict[str, Any] = {}
        
        self._initialized = True
        print("[DashboardStream] Initialized")
    
    # ===========================================
    # Client Management
    # ===========================================
    
    def register_client(self, websocket: Any) -> str:
        """Register a new WebSocket client"""
        client_id = f"cli_{uuid.uuid4().hex[:8]}"
        
        client = StreamClient(
            client_id=client_id,
            connected_at=datetime.now(timezone.utc),
            subscriptions={"all"}  # Subscribe to all by default
        )
        
        self._clients[client_id] = client
        self._websockets[client_id] = websocket
        
        print(f"[DashboardStream] Client {client_id} connected")
        return client_id
    
    def unregister_client(self, client_id: str):
        """Unregister a client"""
        if client_id in self._clients:
            del self._clients[client_id]
        if client_id in self._websockets:
            del self._websockets[client_id]
        
        print(f"[DashboardStream] Client {client_id} disconnected")
    
    def subscribe(self, client_id: str, event_types: List[str]):
        """Subscribe client to specific event types"""
        if client_id in self._clients:
            self._clients[client_id].subscriptions.update(event_types)
    
    def unsubscribe(self, client_id: str, event_types: List[str]):
        """Unsubscribe client from event types"""
        if client_id in self._clients:
            self._clients[client_id].subscriptions -= set(event_types)
    
    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected clients"""
        return [
            {
                "clientId": c.client_id,
                "connectedAt": c.connected_at.isoformat(),
                "subscriptions": list(c.subscriptions)
            }
            for c in self._clients.values()
        ]
    
    # ===========================================
    # Event Publishing
    # ===========================================
    
    def publish(self, event: DashboardEvent):
        """Publish event to all subscribed clients"""
        # Add to queue
        self._event_queue.append(event)
        if len(self._event_queue) > self._max_queue_size:
            self._event_queue = self._event_queue[-self._max_queue_size:]
        
        # Notify handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[DashboardStream] Handler error: {e}")
    
    async def broadcast(self, event: DashboardEvent):
        """Broadcast event to all WebSocket clients"""
        message = json.dumps(event.to_dict())
        
        disconnected = []
        
        for client_id, websocket in self._websockets.items():
            client = self._clients.get(client_id)
            if not client:
                continue
            
            # Check subscription
            if "all" not in client.subscriptions and event.event_type.value not in client.subscriptions:
                continue
            
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"[DashboardStream] Send error to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected
        for client_id in disconnected:
            self.unregister_client(client_id)
    
    # ===========================================
    # Event Factory Methods
    # ===========================================
    
    def emit_portfolio_updated(self, payload: Dict[str, Any]):
        """Emit portfolio updated event"""
        event = DashboardEvent(
            event_type=DashboardEventType.PORTFOLIO_UPDATED,
            payload=payload
        )
        self.publish(event)
        return event
    
    def emit_risk_alert(self, alert_id: str, alert_type: str, severity: str, message: str):
        """Emit risk alert event"""
        event = DashboardEvent(
            event_type=DashboardEventType.RISK_ALERT,
            payload={
                "alertId": alert_id,
                "alertType": alert_type,
                "severity": severity,
                "message": message
            }
        )
        self.publish(event)
        return event
    
    def emit_strategy_switched(self, from_profile: str, to_profile: str, reason: str):
        """Emit strategy switched event"""
        event = DashboardEvent(
            event_type=DashboardEventType.STRATEGY_SWITCHED,
            payload={
                "fromProfile": from_profile,
                "toProfile": to_profile,
                "reason": reason
            }
        )
        self.publish(event)
        return event
    
    def emit_trade_filled(self, trade_id: str, symbol: str, side: str, size: float, price: float):
        """Emit trade filled event"""
        event = DashboardEvent(
            event_type=DashboardEventType.TRADE_FILLED,
            payload={
                "tradeId": trade_id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price
            }
        )
        self.publish(event)
        return event
    
    def emit_kill_switch_triggered(self, mode: str, reason: str, actor: str):
        """Emit kill switch triggered event"""
        event = DashboardEvent(
            event_type=DashboardEventType.KILL_SWITCH_TRIGGERED,
            payload={
                "mode": mode,
                "reason": reason,
                "actor": actor
            }
        )
        self.publish(event)
        return event
    
    def emit_position_opened(self, position_id: str, symbol: str, side: str, size: float):
        """Emit position opened event"""
        event = DashboardEvent(
            event_type=DashboardEventType.POSITION_OPENED,
            payload={
                "positionId": position_id,
                "symbol": symbol,
                "side": side,
                "size": size
            }
        )
        self.publish(event)
        return event
    
    def emit_position_closed(self, position_id: str, symbol: str, pnl: float):
        """Emit position closed event"""
        event = DashboardEvent(
            event_type=DashboardEventType.POSITION_CLOSED,
            payload={
                "positionId": position_id,
                "symbol": symbol,
                "pnl": pnl
            }
        )
        self.publish(event)
        return event
    
    def emit_system_health_changed(self, old_health: str, new_health: str, reasons: List[str]):
        """Emit system health changed event"""
        event = DashboardEvent(
            event_type=DashboardEventType.SYSTEM_HEALTH_CHANGED,
            payload={
                "oldHealth": old_health,
                "newHealth": new_health,
                "reasons": reasons
            }
        )
        self.publish(event)
        return event
    
    # ===========================================
    # Event Handlers
    # ===========================================
    
    def on(self, event_type: DashboardEventType, handler: Callable):
        """Register event handler"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def off(self, event_type: DashboardEventType, handler: Callable):
        """Unregister event handler"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    # ===========================================
    # Event History
    # ===========================================
    
    def get_recent_events(self, limit: int = 50) -> List[DashboardEvent]:
        """Get recent events from queue"""
        return list(reversed(self._event_queue[-limit:]))
    
    def get_events_by_type(
        self,
        event_type: DashboardEventType,
        limit: int = 20
    ) -> List[DashboardEvent]:
        """Get events filtered by type"""
        filtered = [e for e in self._event_queue if e.event_type == event_type]
        return list(reversed(filtered[-limit:]))
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get stream health info"""
        return {
            "status": "healthy",
            "connectedClients": len(self._clients),
            "queueSize": len(self._event_queue),
            "maxQueueSize": self._max_queue_size
        }


# Global singleton
dashboard_stream = DashboardStream()
