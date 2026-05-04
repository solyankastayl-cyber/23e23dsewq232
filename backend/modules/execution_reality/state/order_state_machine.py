"""
Order State Machine (P1 - State Discipline)
============================================

Production-grade Finite State Machine для order lifecycle.

States:
- PENDING: Order created, not yet submitted to exchange
- SUBMITTED: Sent to exchange, awaiting acknowledgment
- ACKNOWLEDGED: Exchange confirmed receipt (order in book)
- PARTIALLY_FILLED: Some quantity filled, remainder active
- FILLED: Fully executed
- CANCELING: Cancel request sent, awaiting confirmation
- CANCELED: Successfully canceled by exchange
- REJECTED: Exchange rejected the order
- EXPIRED: Order expired (time-in-force)
- FAILED: System-level failure (network, etc.)

Transitions:
- NEW → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
                        ↓                    ↓
                    REJECTED            CANCELING → CANCELED
                                             ↓
                                        FAILED

Critical Rules:
1. FILLED is terminal (no transitions out)
2. CANCELED is terminal
3. REJECTED is terminal
4. FAILED is terminal
5. Cannot transition from terminal states
6. PARTIALLY_FILLED can only go to FILLED or CANCELING
"""

from enum import Enum
from typing import Optional, Set
import logging

logger = logging.getLogger(__name__)


class OrderState(str, Enum):
    """Order states (comprehensive)."""
    PENDING = "PENDING"                    # Created, not submitted yet
    SUBMITTED = "SUBMITTED"                # Sent to exchange
    ACKNOWLEDGED = "ACKNOWLEDGED"          # Exchange confirmed (in book)
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partial execution
    FILLED = "FILLED"                      # Fully executed (TERMINAL)
    CANCELING = "CANCELING"                # Cancel request sent
    CANCELED = "CANCELED"                  # Successfully canceled (TERMINAL)
    REJECTED = "REJECTED"                  # Exchange rejected (TERMINAL)
    EXPIRED = "EXPIRED"                    # Time-in-force expired (TERMINAL)
    FAILED = "FAILED"                      # System failure (TERMINAL)


class OrderStateMachine:
    """
    Order state machine with strict transition validation.
    
    Prevents invalid state transitions that could cause:
    - Double fills
    - Inconsistent state
    - Race conditions
    - Ghost orders
    """
    
    # Terminal states (no transitions out)
    TERMINAL_STATES: Set[OrderState] = {
        OrderState.FILLED,
        OrderState.CANCELED,
        OrderState.REJECTED,
        OrderState.EXPIRED,
        OrderState.FAILED
    }
    
    # Allowed transitions: {from_state: {to_state1, to_state2, ...}}
    ALLOWED_TRANSITIONS = {
        OrderState.PENDING: {
            OrderState.SUBMITTED,
            OrderState.ACKNOWLEDGED,  # P1: Allow direct ACK (legacy simulated orders)
            OrderState.FAILED  # System failure before submit
        },
        OrderState.SUBMITTED: {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.FAILED  # Network failure
        },
        OrderState.ACKNOWLEDGED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,  # Direct fill (no partial)
            OrderState.CANCELING,
            OrderState.EXPIRED,
            OrderState.REJECTED  # Late rejection (rare)
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.FILLED,
            OrderState.CANCELING  # Cancel remainder
        },
        OrderState.CANCELING: {
            OrderState.CANCELED,
            OrderState.FILLED,  # Filled before cancel processed
            OrderState.FAILED  # Cancel failed
        },
        # Terminal states have no outgoing transitions
        OrderState.FILLED: set(),
        OrderState.CANCELED: set(),
        OrderState.REJECTED: set(),
        OrderState.EXPIRED: set(),
        OrderState.FAILED: set()
    }
    
    @classmethod
    def is_terminal(cls, state: OrderState) -> bool:
        """Check if state is terminal (no transitions out)."""
        return state in cls.TERMINAL_STATES
    
    @classmethod
    def is_transition_allowed(
        cls,
        from_state: OrderState,
        to_state: OrderState
    ) -> bool:
        """
        Validate if transition is allowed.
        
        Args:
            from_state: Current order state
            to_state: Target order state
        
        Returns:
            True if transition is valid, False otherwise
        """
        # Same state is always allowed (idempotent)
        if from_state == to_state:
            return True
        
        # Check if transition exists in allowed transitions
        allowed_next_states = cls.ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed_next_states
    
    @classmethod
    def validate_transition(
        cls,
        from_state: OrderState,
        to_state: OrderState,
        client_order_id: str,
        strict: bool = True
    ) -> None:
        """
        Validate transition and raise exception if invalid.
        
        Args:
            from_state: Current order state
            to_state: Target order state
            client_order_id: Order identifier (for logging)
            strict: If True, enforce strict FSM rules. If False, allow exchange reconciliation.
        
        Raises:
            OrderStateViolationError: If transition is invalid (only in strict mode)
        
        Notes:
            strict=False for exchange events (tolerates out-of-order, reconciliation)
            strict=True for internal logic (enforces FSM rules)
        """
        if not cls.is_transition_allowed(from_state, to_state):
            error_msg = (
                f"Invalid order state transition: {from_state} → {to_state} "
                f"(order={client_order_id})"
            )
            
            if strict:
                # STRICT: Internal logic - enforce FSM
                logger.error(f"🔥 STATE VIOLATION: {error_msg}")
                raise OrderStateViolationError(error_msg)
            else:
                # RELAXED: Exchange events - log warning but allow
                logger.warning(
                    f"⚠️ Out-of-order exchange event (allowed): {error_msg}"
                )
                return
        
        logger.debug(
            f"✅ Valid transition: {from_state} → {to_state} "
            f"(order={client_order_id})"
        )
    
    @classmethod
    def get_allowed_next_states(cls, current_state: OrderState) -> Set[OrderState]:
        """
        Get allowed next states from current state.
        
        Args:
            current_state: Current order state
        
        Returns:
            Set of allowed next states
        """
        return cls.ALLOWED_TRANSITIONS.get(current_state, set())
    
    @classmethod
    def can_cancel(cls, current_state: OrderState) -> bool:
        """Check if order can be canceled from current state."""
        return OrderState.CANCELING in cls.get_allowed_next_states(current_state)
    
    @classmethod
    def can_fill(cls, current_state: OrderState) -> bool:
        """Check if order can be filled from current state."""
        allowed = cls.get_allowed_next_states(current_state)
        return (
            OrderState.FILLED in allowed or
            OrderState.PARTIALLY_FILLED in allowed
        )
    
    @classmethod
    def is_active(cls, state: OrderState) -> bool:
        """
        Check if order is active (can receive fills or cancels).
        
        Active states: ACKNOWLEDGED, PARTIALLY_FILLED
        """
        return state in {OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED}
    
    @classmethod
    def is_closed(cls, state: OrderState) -> bool:
        """Check if order is closed (terminal or failed)."""
        return cls.is_terminal(state)


class OrderStateViolationError(Exception):
    """Raised when invalid order state transition is attempted."""
    pass


# Event Type → Order State mapping (for automatic state derivation)
EVENT_TO_STATE_MAP = {
    "ORDER_SUBMIT_REQUESTED": OrderState.PENDING,
    "ORDER_SUBMITTED": OrderState.SUBMITTED,
    "ORDER_ACKNOWLEDGED": OrderState.ACKNOWLEDGED,
    "ORDER_FILL_RECORDED": OrderState.PARTIALLY_FILLED,  # May become FILLED
    "ORDER_FULLY_FILLED": OrderState.FILLED,
    "ORDER_CANCEL_REQUESTED": OrderState.CANCELING,
    "ORDER_CANCELED": OrderState.CANCELED,
    "ORDER_REJECTED": OrderState.REJECTED,
    "ORDER_EXPIRED": OrderState.EXPIRED,
    "ORDER_FAILED": OrderState.FAILED
}


def get_next_state_from_event(
    event_type: str,
    current_state: OrderState,
    filled_qty: float,
    total_qty: float
) -> OrderState:
    """
    Derive next order state from event.
    
    Args:
        event_type: Execution event type
        current_state: Current order state
        filled_qty: Cumulative filled quantity
        total_qty: Order total quantity
    
    Returns:
        Next order state
    """
    # Special case: ORDER_FILL_RECORDED may result in FILLED or PARTIALLY_FILLED
    if event_type == "ORDER_FILL_RECORDED":
        if filled_qty >= total_qty:
            return OrderState.FILLED
        else:
            return OrderState.PARTIALLY_FILLED
    
    # Map event to state
    return EVENT_TO_STATE_MAP.get(event_type, current_state)
