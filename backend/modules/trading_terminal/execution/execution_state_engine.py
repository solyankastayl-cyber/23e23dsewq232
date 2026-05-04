"""
Execution State Engine
======================

Main orchestrator for execution lifecycle.
Bridges decision -> intent -> order -> position.
"""

import uuid
from typing import Dict, Any, Optional
from .execution_models import (
    ExecutionIntent,
    OrderState,
    ExecutionStatusSummary,
    ExecutionState,
    utc_now,
)
from .order_state_machine import OrderStateMachine
from .execution_repository import ExecutionRepository, get_execution_repository


class ExecutionStateEngine:
    """Main execution lifecycle orchestrator"""
    
    def __init__(self, repo: Optional[ExecutionRepository] = None):
        self.repo = repo or get_execution_repository()
        self.sm = OrderStateMachine()

    def build_or_update_intent(
        self,
        symbol: str,
        timeframe: str,
        decision: Dict[str, Any],
        execution: Dict[str, Any],
        validation: Dict[str, Any],
        position: Optional[Dict[str, Any]] = None,
    ) -> ExecutionIntent:
        """Create or update execution intent based on current state"""
        symbol = symbol.upper()
        timeframe = timeframe.upper()
        now = utc_now()
        
        latest = self.repo.get_latest_intent(symbol, timeframe)
        next_state, reason = self._resolve_intent_state(decision, validation, position)

        if latest:
            # Check if we can transition
            if latest.status != next_state:
                try:
                    self.sm.ensure_transition(latest.status, next_state)
                except ValueError:
                    # If transition not allowed, keep current state
                    next_state = latest.status
                    reason = latest.reason

            # Update existing intent
            latest.action = decision.get("action", latest.action)
            latest.direction = decision.get("direction", latest.direction)
            latest.entry_mode = decision.get("mode", latest.entry_mode)
            latest.execution_mode = execution.get("mode", latest.execution_mode)
            latest.planned_entry = execution.get("entry") or latest.planned_entry
            latest.planned_stop = execution.get("stop") or latest.planned_stop
            latest.planned_target = execution.get("target") or latest.planned_target
            latest.planned_rr = execution.get("rr") or latest.planned_rr
            latest.size_multiplier = execution.get("size", latest.size_multiplier or 1.0)
            latest.execution_confidence = execution.get(
                "execution_confidence",
                execution.get("confidence", latest.execution_confidence or 0.0),
            )
            latest.status = next_state
            latest.reason = reason
            latest.updated_at = now
            return self.repo.save_intent(latest)

        # Create new intent
        intent = ExecutionIntent(
            intent_id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            action=decision.get("action", "WAIT"),
            direction=decision.get("direction", "NEUTRAL"),
            entry_mode=decision.get("mode", "UNKNOWN"),
            execution_mode=execution.get("mode", "PASSIVE_LIMIT"),
            planned_entry=execution.get("entry"),
            planned_stop=execution.get("stop"),
            planned_target=execution.get("target"),
            planned_rr=execution.get("rr"),
            size_multiplier=execution.get("size", 1.0),
            execution_confidence=execution.get(
                "execution_confidence", 
                execution.get("confidence", 0.0)
            ),
            status=next_state,
            reason=reason,
            created_at=now,
            updated_at=now,
        )
        return self.repo.save_intent(intent)

    def create_simulated_order(
        self, 
        intent_id: str, 
        side: str = "BUY", 
        order_type: str = "LIMIT"
    ) -> OrderState:
        """Create a simulated order from intent"""
        intent = self.repo.get_intent(intent_id)
        if not intent:
            raise ValueError(f"Intent not found: {intent_id}")

        # Transition to ORDER_PLANNED
        self.sm.ensure_transition(intent.status, "ORDER_PLANNED")
        intent.status = "ORDER_PLANNED"
        intent.updated_at = utc_now()
        self.repo.save_intent(intent)

        # Create order
        order = OrderState(
            order_id=str(uuid.uuid4()),
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=side,
            order_type=order_type,
            status="ORDER_PLACED",
            price=intent.planned_entry,
            size=intent.size_multiplier,
            filled_size=0.0,
            remaining_size=intent.size_multiplier,
            avg_fill_price=None,
            time_in_force="GTC",
            placed_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repo.save_order(order)

        # Transition intent to ORDER_PLACED
        self.sm.ensure_transition(intent.status, "ORDER_PLACED")
        intent.status = "ORDER_PLACED"
        intent.updated_at = utc_now()
        self.repo.save_intent(intent)
        
        return order

    def simulate_fill(
        self, 
        order_id: str, 
        fill_size: float, 
        fill_price: Optional[float] = None
    ) -> OrderState:
        """Simulate partial or full fill"""
        order = self.repo.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if order.status not in {"ORDER_PLACED", "PARTIAL_FILL"}:
            raise ValueError(f"Order is not fillable (status: {order.status})")

        # Update fill
        new_filled = min(order.size, order.filled_size + fill_size)
        order.filled_size = new_filled
        order.remaining_size = max(0.0, order.size - new_filled)
        order.avg_fill_price = fill_price or order.price
        order.updated_at = utc_now()

        # Get intent
        intent = self.repo.get_intent(order.intent_id)
        if not intent:
            raise ValueError(f"Intent not found: {order.intent_id}")

        # Determine new status
        if order.remaining_size > 0:
            order.status = "PARTIAL_FILL"
            self.repo.save_order(order)
            
            if self.sm.can_transition(intent.status, "PARTIAL_FILL"):
                intent.status = "PARTIAL_FILL"
                intent.updated_at = utc_now()
                self.repo.save_intent(intent)
        else:
            order.status = "FILLED"
            self.repo.save_order(order)
            
            if self.sm.can_transition(intent.status, "FILLED"):
                intent.status = "FILLED"
                intent.updated_at = utc_now()
                self.repo.save_intent(intent)

        return order

    def simulate_cancel(
        self, 
        order_id: str, 
        reason: str = "manual_cancel"
    ) -> OrderState:
        """Simulate order cancellation"""
        order = self.repo.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if order.status not in {"ORDER_PLACED", "PARTIAL_FILL"}:
            raise ValueError(f"Order is not cancellable (status: {order.status})")

        order.status = "CANCELLED"
        order.cancel_reason = reason
        order.updated_at = utc_now()
        self.repo.save_order(order)

        # Update intent
        intent = self.repo.get_intent(order.intent_id)
        if intent and self.sm.can_transition(intent.status, "CANCELLED"):
            intent.status = "CANCELLED"
            intent.reason = reason
            intent.updated_at = utc_now()
            self.repo.save_intent(intent)

        return order

    def build_status_summary(
        self, 
        symbol: str, 
        timeframe: str, 
        position: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build execution status summary for terminal state"""
        symbol = symbol.upper()
        timeframe = timeframe.upper()
        
        intent = self.repo.get_latest_intent(symbol, timeframe)
        
        if not intent:
            return ExecutionStatusSummary(
                execution_state="IDLE",
                intent_state="IDLE",
                order_present=False,
                position_open=bool(position and position.get("has_position")),
                order_id=None,
                filled_pct=0.0,
                status_label="Idle",
                status_reason="no active execution intent",
            ).to_dict()

        order = self.repo.get_latest_order_by_intent(intent.intent_id)
        
        filled_pct = 0.0
        order_present = False
        order_id = None
        execution_state = intent.status
        status_reason = intent.reason

        if order:
            order_present = True
            order_id = order.order_id
            filled_pct = order.filled_pct
            execution_state = order.status
            status_reason = order.cancel_reason or order.reject_reason or intent.reason

        return ExecutionStatusSummary(
            execution_state=execution_state,
            intent_state=intent.status,
            order_present=order_present,
            position_open=bool(position and position.get("has_position")),
            order_id=order_id,
            filled_pct=filled_pct,
            status_label=self._state_label(execution_state),
            status_reason=status_reason,
        ).to_dict()

    def get_orders_preview(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 5
    ) -> list:
        """Get orders preview for terminal state"""
        orders = self.repo.list_orders(symbol=symbol, limit=limit)
        return [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side,
                "status": o.status,
                "price": o.price,
                "size": o.size,
                "filled_pct": o.filled_pct,
                "updated_at": o.updated_at,
            }
            for o in orders
        ]

    def _resolve_intent_state(
        self, 
        decision: Dict[str, Any], 
        validation: Dict[str, Any], 
        position: Optional[Dict[str, Any]]
    ) -> tuple:
        """Determine intent state from decision/validation"""
        action = decision.get("action", "WAIT")

        # Position already open
        if position and position.get("has_position"):
            return "FILLED", "position_open"

        # Validation failed
        if validation and not validation.get("is_valid", True):
            return "REJECTED", "validation_failed"

        # Wait states
        if action in {"WAIT", "WAIT_MICRO", "WAIT_MICROSTRUCTURE"}:
            return "WAITING_ENTRY", "waiting_for_conditions"

        # Skip
        if action == "SKIP":
            return "IDLE", "decision_skip"

        # Go states
        if action in {"GO", "GO_FULL", "GO_REDUCED"}:
            return "READY_TO_PLACE", "all_conditions_satisfied"

        return "IDLE", "unknown_state"

    def _state_label(self, state: str) -> str:
        """Human-readable state label"""
        labels = {
            "IDLE": "Idle",
            "WAITING_ENTRY": "Waiting entry",
            "READY_TO_PLACE": "Ready to place",
            "ORDER_PLANNED": "Order planned",
            "ORDER_PLACED": "Order placed",
            "PARTIAL_FILL": "Partial fill",
            "FILLED": "Filled",
            "CANCELLED": "Cancelled",
            "REJECTED": "Rejected",
            "EXPIRED": "Expired",
            "CLOSED": "Closed",
        }
        return labels.get(state, state)


# Singleton instance
_execution_engine: Optional[ExecutionStateEngine] = None


def get_execution_engine() -> ExecutionStateEngine:
    """Get singleton engine instance"""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionStateEngine()
    return _execution_engine
