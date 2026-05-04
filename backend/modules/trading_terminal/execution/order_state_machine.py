"""
Order State Machine
===================

Enforces valid state transitions for execution lifecycle.
Prevents illegal transitions like IDLE -> FILLED.
"""

from typing import Set, Dict


class OrderStateMachine:
    """
    State transitions for order lifecycle.
    
    Valid flow:
    IDLE -> WAITING_ENTRY -> READY_TO_PLACE -> ORDER_PLANNED -> ORDER_PLACED
    ORDER_PLACED -> PARTIAL_FILL -> FILLED -> CLOSED
    ORDER_PLACED -> CANCELLED / REJECTED / EXPIRED
    """
    
    ALLOWED: Dict[str, Set[str]] = {
        "IDLE": {"WAITING_ENTRY"},
        "WAITING_ENTRY": {"READY_TO_PLACE", "IDLE", "EXPIRED"},
        "READY_TO_PLACE": {"ORDER_PLANNED", "WAITING_ENTRY", "IDLE", "EXPIRED"},
        "ORDER_PLANNED": {"ORDER_PLACED", "CANCELLED", "EXPIRED"},
        "ORDER_PLACED": {"PARTIAL_FILL", "FILLED", "CANCELLED", "REJECTED", "EXPIRED"},
        "PARTIAL_FILL": {"FILLED", "CANCELLED"},
        "FILLED": {"CLOSED"},
        "CANCELLED": set(),
        "REJECTED": set(),
        "EXPIRED": set(),
        "CLOSED": set(),
    }

    def can_transition(self, old_state: str, new_state: str) -> bool:
        """Check if transition is allowed"""
        return new_state in self.ALLOWED.get(old_state, set())

    def ensure_transition(self, old_state: str, new_state: str) -> None:
        """Raise error if transition is illegal"""
        if not self.can_transition(old_state, new_state):
            raise ValueError(f"Illegal state transition: {old_state} -> {new_state}")

    def get_allowed_transitions(self, state: str) -> Set[str]:
        """Get all allowed transitions from a state"""
        return self.ALLOWED.get(state, set())

    def is_terminal_state(self, state: str) -> bool:
        """Check if state is terminal (no further transitions)"""
        return len(self.ALLOWED.get(state, set())) == 0

    def is_active_state(self, state: str) -> bool:
        """Check if state represents active execution"""
        return state in {"ORDER_PLACED", "PARTIAL_FILL", "FILLED"}
