"""
Order State Machine
===================

PHASE 4.1 - Manages order lifecycle state transitions.
"""

import time
from typing import Dict, List, Optional, Set, Tuple

from .order_types import (
    OrderState,
    Order,
    StateTransition,
    ExecutionEventType,
    OrderFill
)


class OrderStateMachine:
    """
    Order State Machine:
    - Validates state transitions
    - Enforces order lifecycle rules
    - Tracks state history
    """
    
    def __init__(self):
        # Define valid state transitions
        self._transitions: Dict[OrderState, Set[OrderState]] = {
            OrderState.NEW: {
                OrderState.SUBMITTED,
                OrderState.CANCELLED,
                OrderState.FAILED
            },
            OrderState.SUBMITTED: {
                OrderState.ACCEPTED,
                OrderState.REJECTED,
                OrderState.CANCELLED,
                OrderState.FAILED
            },
            OrderState.ACCEPTED: {
                OrderState.PARTIAL_FILL,
                OrderState.FILLED,
                OrderState.CANCELLED,
                OrderState.EXPIRED,
                OrderState.FAILED
            },
            OrderState.PARTIAL_FILL: {
                OrderState.PARTIAL_FILL,  # Can have multiple partial fills
                OrderState.FILLED,
                OrderState.CANCELLED,
                OrderState.EXPIRED,
                OrderState.FAILED
            },
            # Terminal states - no further transitions
            OrderState.FILLED: set(),
            OrderState.CANCELLED: set(),
            OrderState.REJECTED: set(),
            OrderState.FAILED: set(),
            OrderState.EXPIRED: set()
        }
        
        # Map transitions to events
        self._event_map: Dict[Tuple[OrderState, OrderState], ExecutionEventType] = {
            (OrderState.NEW, OrderState.SUBMITTED): ExecutionEventType.ORDER_SUBMITTED,
            (OrderState.NEW, OrderState.CANCELLED): ExecutionEventType.ORDER_CANCELLED,
            (OrderState.NEW, OrderState.FAILED): ExecutionEventType.ORDER_FAILED,
            
            (OrderState.SUBMITTED, OrderState.ACCEPTED): ExecutionEventType.ORDER_ACCEPTED,
            (OrderState.SUBMITTED, OrderState.REJECTED): ExecutionEventType.ORDER_REJECTED,
            (OrderState.SUBMITTED, OrderState.CANCELLED): ExecutionEventType.ORDER_CANCELLED,
            (OrderState.SUBMITTED, OrderState.FAILED): ExecutionEventType.ORDER_FAILED,
            
            (OrderState.ACCEPTED, OrderState.PARTIAL_FILL): ExecutionEventType.ORDER_PARTIAL_FILL,
            (OrderState.ACCEPTED, OrderState.FILLED): ExecutionEventType.ORDER_FILLED,
            (OrderState.ACCEPTED, OrderState.CANCELLED): ExecutionEventType.ORDER_CANCELLED,
            (OrderState.ACCEPTED, OrderState.EXPIRED): ExecutionEventType.ORDER_EXPIRED,
            (OrderState.ACCEPTED, OrderState.FAILED): ExecutionEventType.ORDER_FAILED,
            
            (OrderState.PARTIAL_FILL, OrderState.PARTIAL_FILL): ExecutionEventType.ORDER_PARTIAL_FILL,
            (OrderState.PARTIAL_FILL, OrderState.FILLED): ExecutionEventType.ORDER_FILLED,
            (OrderState.PARTIAL_FILL, OrderState.CANCELLED): ExecutionEventType.ORDER_CANCELLED,
            (OrderState.PARTIAL_FILL, OrderState.EXPIRED): ExecutionEventType.ORDER_EXPIRED,
            (OrderState.PARTIAL_FILL, OrderState.FAILED): ExecutionEventType.ORDER_FAILED,
        }
        
        # States requiring fill data
        self._fill_required_states = {
            OrderState.PARTIAL_FILL,
            OrderState.FILLED
        }
        
        print("[OrderStateMachine] Initialized (PHASE 4.1)")
    
    def can_transition(self, from_state: OrderState, to_state: OrderState) -> bool:
        """Check if transition is valid"""
        valid_targets = self._transitions.get(from_state, set())
        return to_state in valid_targets
    
    def transition(
        self,
        order: Order,
        to_state: OrderState,
        fill: Optional[OrderFill] = None,
        error_code: str = "",
        error_message: str = ""
    ) -> Tuple[bool, str]:
        """
        Attempt to transition order to new state.
        
        Returns: (success, error_message)
        """
        
        from_state = order.state
        
        # Validate transition
        if not self.can_transition(from_state, to_state):
            return False, f"Invalid transition: {from_state.value} -> {to_state.value}"
        
        # Check fill requirement
        if to_state in self._fill_required_states and not fill:
            return False, f"Fill data required for {to_state.value}"
        
        # Perform transition
        order.previous_state = from_state
        order.state = to_state
        order.updated_at = int(time.time() * 1000)
        
        # Handle fill
        if fill:
            self._apply_fill(order, fill)
        
        # Handle error states
        if to_state in [OrderState.REJECTED, OrderState.FAILED]:
            order.error_code = error_code
            order.error_message = error_message
        
        # Update timestamps
        if to_state == OrderState.SUBMITTED:
            order.submitted_at = order.updated_at
        elif to_state == OrderState.ACCEPTED:
            order.accepted_at = order.updated_at
        elif to_state == OrderState.FILLED:
            order.filled_at = order.updated_at
        elif to_state == OrderState.CANCELLED:
            order.cancelled_at = order.updated_at
        
        return True, ""
    
    def _apply_fill(self, order: Order, fill: OrderFill):
        """Apply fill to order"""
        
        # Add fill
        order.fills.append(fill)
        order.fill_count += 1
        
        # Update quantities
        order.filled_quantity += fill.filled_qty
        order.remaining_quantity = order.quantity - order.filled_quantity
        
        # Update average fill price
        if order.filled_quantity > 0:
            total_value = sum(f.filled_qty * f.fill_price for f in order.fills)
            order.avg_fill_price = total_value / order.filled_quantity
        
        # Update commission
        order.total_commission += fill.commission
        
        # Calculate slippage
        if order.expected_price > 0 and order.avg_fill_price > 0:
            if order.side.value == "BUY":
                order.slippage_pct = (order.avg_fill_price - order.expected_price) / order.expected_price * 100
            else:
                order.slippage_pct = (order.expected_price - order.avg_fill_price) / order.expected_price * 100
        
        # Check if fully filled
        if order.remaining_quantity <= 0:
            order.state = OrderState.FILLED
            order.filled_at = int(time.time() * 1000)
    
    def get_event_type(self, from_state: OrderState, to_state: OrderState) -> Optional[ExecutionEventType]:
        """Get event type for transition"""
        return self._event_map.get((from_state, to_state))
    
    def get_valid_transitions(self, state: OrderState) -> List[OrderState]:
        """Get valid transitions from current state"""
        return list(self._transitions.get(state, set()))
    
    def get_all_transitions(self) -> List[StateTransition]:
        """Get all valid transitions"""
        transitions = []
        for from_state, to_states in self._transitions.items():
            for to_state in to_states:
                event = self.get_event_type(from_state, to_state)
                transitions.append(StateTransition(
                    from_state=from_state,
                    to_state=to_state,
                    event_type=event or ExecutionEventType.ORDER_CREATED,
                    requires_fill=to_state in self._fill_required_states
                ))
        return transitions
    
    def is_terminal(self, state: OrderState) -> bool:
        """Check if state is terminal"""
        return len(self._transitions.get(state, set())) == 0
    
    def get_health(self) -> Dict:
        """Get engine health"""
        return {
            "engine": "OrderStateMachine",
            "version": "1.0.0",
            "phase": "4.1",
            "status": "active",
            "states": [s.value for s in OrderState],
            "terminalStates": [s.value for s in OrderState if self.is_terminal(s)],
            "transitionCount": sum(len(t) for t in self._transitions.values()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
order_state_machine = OrderStateMachine()
