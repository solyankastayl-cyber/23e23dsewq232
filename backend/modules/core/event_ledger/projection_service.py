"""
Projection Service
==================

Builds and maintains read models from event stream.

Projections provide fast access to current state
while Event Ledger maintains the complete history.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from .ledger_types import LedgerEvent, EventType
from .event_publisher import event_publisher


@dataclass
class ProjectionState:
    """State of a projection"""
    name: str = ""
    last_sequence: int = 0
    last_updated: int = 0
    event_count: int = 0
    state: Dict[str, Any] = field(default_factory=dict)


class ProjectionService:
    """
    Manages projections (read models) built from events.
    
    Each projection:
    - Subscribes to specific event types
    - Maintains its own state
    - Can be rebuilt from event history
    
    Built-in projections:
    - current_positions: Latest position state
    - current_orders: Active orders
    - strategy_state: Current strategy decisions
    - risk_alerts: Active risk alerts
    - recent_events: Last N events for dashboard
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
        
        # Projection states
        self._projections: Dict[str, ProjectionState] = {}
        
        # Projection handlers
        self._handlers: Dict[str, Dict[str, Callable]] = {}
        
        # Initialize built-in projections
        self._init_builtin_projections()
        
        self._initialized = True
        print("[ProjectionService] Initialized")
    
    def _init_builtin_projections(self):
        """Initialize built-in projections"""
        
        # Recent events (for dashboard)
        self.register_projection(
            name="recent_events",
            event_types=None,  # All events
            handler=self._handle_recent_events,
            initial_state={"events": [], "max_size": 100}
        )
        
        # Current positions
        self.register_projection(
            name="current_positions",
            event_types=[
                "POSITION_OPENED", "POSITION_SCALED",
                "POSITION_REDUCED", "POSITION_CLOSED"
            ],
            handler=self._handle_position_events,
            initial_state={"positions": {}}
        )
        
        # Active orders
        self.register_projection(
            name="active_orders",
            event_types=[
                "ORDER_CREATED", "ORDER_SUBMITTED",
                "ORDER_FILLED", "ORDER_CANCELLED"
            ],
            handler=self._handle_order_events,
            initial_state={"orders": {}}
        )
        
        # Risk alerts
        self.register_projection(
            name="risk_alerts",
            event_types=[
                "RISK_ALERT_RAISED", "RISK_ALERT_CLEARED",
                "KILL_SWITCH_TRIGGERED", "SAFETY_BLOCK_TRIGGERED"
            ],
            handler=self._handle_risk_events,
            initial_state={"alerts": [], "kill_switch_active": False}
        )
        
        # Strategy decisions
        self.register_projection(
            name="strategy_decisions",
            event_types=[
                "STRATEGY_DECISION_MADE", "STRATEGY_BLOCKED",
                "STRATEGY_SELECTED", "PROFILE_SWITCHED"
            ],
            handler=self._handle_strategy_events,
            initial_state={"last_decisions": {}, "blocks": [], "current_profile": None}
        )
        
        # Reconciliation status
        self.register_projection(
            name="recon_status",
            event_types=[
                "RECON_RUN_COMPLETED", "RECON_MISMATCH_DETECTED",
                "EXCHANGE_QUARANTINED", "EXCHANGE_RESTORED"
            ],
            handler=self._handle_recon_events,
            initial_state={"mismatches": [], "quarantined": []}
        )
        
        # Subscribe to events
        event_publisher.subscribe(self._on_event)
    
    def register_projection(
        self,
        name: str,
        event_types: Optional[List[str]],
        handler: Callable[[LedgerEvent, Dict], Dict],
        initial_state: Dict[str, Any] = None
    ):
        """
        Register a new projection.
        
        Args:
            name: Projection name
            event_types: List of event types to handle (None = all)
            handler: Function(event, current_state) -> new_state
            initial_state: Initial projection state
        """
        
        self._projections[name] = ProjectionState(
            name=name,
            state=initial_state or {}
        )
        
        if event_types:
            for event_type in event_types:
                if event_type not in self._handlers:
                    self._handlers[event_type] = {}
                self._handlers[event_type][name] = handler
        else:
            # Global handler (receives all events)
            if "__global__" not in self._handlers:
                self._handlers["__global__"] = {}
            self._handlers["__global__"][name] = handler
    
    def _on_event(self, event: LedgerEvent):
        """Handle incoming event"""
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        # Type-specific handlers
        if event_type in self._handlers:
            for name, handler in self._handlers[event_type].items():
                self._apply_handler(name, handler, event)
        
        # Global handlers
        if "__global__" in self._handlers:
            for name, handler in self._handlers["__global__"].items():
                self._apply_handler(name, handler, event)
    
    def _apply_handler(
        self,
        projection_name: str,
        handler: Callable,
        event: LedgerEvent
    ):
        """Apply handler to projection"""
        try:
            proj = self._projections[projection_name]
            new_state = handler(event, proj.state)
            proj.state = new_state
            proj.last_sequence = event.sequence_number
            proj.last_updated = int(time.time() * 1000)
            proj.event_count += 1
        except Exception as e:
            print(f"[ProjectionService] Handler error for {projection_name}: {e}")
    
    # ===========================================
    # Built-in Handlers
    # ===========================================
    
    def _handle_recent_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Keep last N events"""
        events = state.get("events", [])
        max_size = state.get("max_size", 100)
        
        events.insert(0, {
            "eventId": event.event_id,
            "eventType": event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
            "aggregateType": event.aggregate_type,
            "aggregateId": event.aggregate_id,
            "sourceModule": event.source_module,
            "createdAt": event.created_at
        })
        
        if len(events) > max_size:
            events = events[:max_size]
        
        state["events"] = events
        return state
    
    def _handle_position_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Track position state"""
        positions = state.get("positions", {})
        pos_id = event.aggregate_id
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        if event_type == "POSITION_OPENED":
            positions[pos_id] = {
                **event.payload,
                "status": "OPEN",
                "opened_at": event.created_at
            }
        elif event_type == "POSITION_SCALED":
            if pos_id in positions:
                positions[pos_id].update(event.payload)
                positions[pos_id]["last_scaled"] = event.created_at
        elif event_type == "POSITION_REDUCED":
            if pos_id in positions:
                positions[pos_id].update(event.payload)
                positions[pos_id]["last_reduced"] = event.created_at
        elif event_type == "POSITION_CLOSED":
            if pos_id in positions:
                del positions[pos_id]
        
        state["positions"] = positions
        return state
    
    def _handle_order_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Track order state"""
        orders = state.get("orders", {})
        order_id = event.aggregate_id
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        if event_type in ["ORDER_CREATED", "ORDER_SUBMITTED"]:
            orders[order_id] = {
                **event.payload,
                "status": "ACTIVE" if event_type == "ORDER_SUBMITTED" else "CREATED",
                "created_at": event.created_at
            }
        elif event_type in ["ORDER_FILLED", "ORDER_CANCELLED"]:
            if order_id in orders:
                del orders[order_id]
        
        state["orders"] = orders
        return state
    
    def _handle_risk_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Track risk alerts"""
        alerts = state.get("alerts", [])
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        if event_type == "RISK_ALERT_RAISED":
            alerts.append({
                "alert_id": event.event_id,
                **event.payload,
                "raised_at": event.created_at
            })
        elif event_type == "RISK_ALERT_CLEARED":
            alert_id = event.payload.get("alert_id")
            alerts = [a for a in alerts if a.get("alert_id") != alert_id]
        elif event_type == "KILL_SWITCH_TRIGGERED":
            state["kill_switch_active"] = True
            state["kill_switch_at"] = event.created_at
        elif event_type == "KILL_SWITCH_RESET":
            state["kill_switch_active"] = False
        
        state["alerts"] = alerts[-50:]  # Keep last 50
        return state
    
    def _handle_strategy_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Track strategy state"""
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        if event_type == "STRATEGY_DECISION_MADE":
            symbol = event.payload.get("symbol", "unknown")
            state["last_decisions"][symbol] = {
                **event.payload,
                "decided_at": event.created_at
            }
        elif event_type == "STRATEGY_BLOCKED":
            blocks = state.get("blocks", [])
            blocks.append({
                **event.payload,
                "blocked_at": event.created_at
            })
            state["blocks"] = blocks[-20:]  # Keep last 20
        elif event_type == "PROFILE_SWITCHED":
            state["current_profile"] = event.payload.get("to_profile")
            state["profile_switched_at"] = event.created_at
        
        return state
    
    def _handle_recon_events(
        self,
        event: LedgerEvent,
        state: Dict
    ) -> Dict:
        """Track reconciliation state"""
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        
        if event_type == "RECON_MISMATCH_DETECTED":
            mismatches = state.get("mismatches", [])
            mismatches.append({
                **event.payload,
                "detected_at": event.created_at
            })
            state["mismatches"] = mismatches[-50:]
        elif event_type == "EXCHANGE_QUARANTINED":
            quarantined = state.get("quarantined", [])
            exchange = event.payload.get("exchange")
            if exchange and exchange not in quarantined:
                quarantined.append(exchange)
            state["quarantined"] = quarantined
        elif event_type == "EXCHANGE_RESTORED":
            exchange = event.payload.get("exchange")
            quarantined = state.get("quarantined", [])
            state["quarantined"] = [e for e in quarantined if e != exchange]
        
        return state
    
    # ===========================================
    # Read Methods
    # ===========================================
    
    def get_projection(self, name: str) -> Optional[Dict[str, Any]]:
        """Get projection state"""
        if name in self._projections:
            proj = self._projections[name]
            return {
                "name": proj.name,
                "state": proj.state,
                "lastSequence": proj.last_sequence,
                "lastUpdated": proj.last_updated,
                "eventCount": proj.event_count
            }
        return None
    
    def get_all_projections(self) -> Dict[str, Any]:
        """Get all projection states"""
        return {
            name: {
                "lastSequence": proj.last_sequence,
                "lastUpdated": proj.last_updated,
                "eventCount": proj.event_count
            }
            for name, proj in self._projections.items()
        }
    
    # Convenience methods for common projections
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events from projection"""
        proj = self.get_projection("recent_events")
        if proj:
            events = proj["state"].get("events", [])
            return events[:limit]
        return []
    
    def get_current_positions(self) -> Dict[str, Any]:
        """Get current positions from projection"""
        proj = self.get_projection("current_positions")
        if proj:
            return proj["state"].get("positions", {})
        return {}
    
    def get_active_orders(self) -> Dict[str, Any]:
        """Get active orders from projection"""
        proj = self.get_projection("active_orders")
        if proj:
            return proj["state"].get("orders", {})
        return {}
    
    def get_risk_alerts(self) -> Dict[str, Any]:
        """Get risk alerts from projection"""
        proj = self.get_projection("risk_alerts")
        if proj:
            return proj["state"]
        return {"alerts": [], "kill_switch_active": False}
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """Get strategy state from projection"""
        proj = self.get_projection("strategy_decisions")
        if proj:
            return proj["state"]
        return {}
    
    def get_recon_status(self) -> Dict[str, Any]:
        """Get reconciliation status from projection"""
        proj = self.get_projection("recon_status")
        if proj:
            return proj["state"]
        return {"mismatches": [], "quarantined": []}


# Global service instance
projection_service = ProjectionService()
