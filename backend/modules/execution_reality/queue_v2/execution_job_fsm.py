"""
Execution Job FSM Validator (P1.3 Checkpoint 1)
================================================

Строгий валидатор переходов статусов.

Разрешённые переходы:
- queued → leased
- leased → in_flight
- leased → retry_wait (если ошибка до submit)
- in_flight → acked
- in_flight → retry_wait (если retryable ошибка)
- in_flight → failed_terminal (если non-retryable)
- retry_wait → queued (автоматически при retry scheduling)
- failed_terminal → dead_letter

ЗАПРЕЩЕНО:
- queued → acked (bypass execution)
- retry_wait → in_flight (должен вернуться в queued сначала)
- dead_letter → любой статус (финальное состояние)
- acked → любой статус (финальное состояние)
"""

from typing import Set, Tuple

# Allowed FSM transitions (from_status, to_status)
ALLOWED_TRANSITIONS: Set[Tuple[str, str]] = {
    # Normal flow
    ("queued", "leased"),
    ("leased", "in_flight"),
    ("in_flight", "acked"),
    
    # Retry flow
    ("leased", "retry_wait"),      # Error before submit
    ("in_flight", "retry_wait"),   # Error after submit (retryable)
    ("retry_wait", "queued"),      # Retry scheduled → back to queue
    
    # Failure flow
    ("leased", "failed_terminal"),      # Non-retryable error before submit
    ("in_flight", "failed_terminal"),   # Non-retryable error after submit
    ("failed_terminal", "dead_letter"), # Manual DLQ move
    
    # Правка 2: Future transitions (для P1.4+ partial fills)
    # Добавляем заранее, чтобы избежать миграции FSM позже
    ("acked", "partially_filled"),      # Partial fill detected
    ("partially_filled", "filled"),     # Full fill after partial
    ("partially_filled", "acked"),      # Update partial status
}


def is_transition_allowed(from_status: str, to_status: str) -> bool:
    """
    Check if status transition is allowed by FSM.
    
    Args:
        from_status: Current status
        to_status: Target status
    
    Returns:
        True if transition allowed, False otherwise
    """
    # Allow same-status (idempotent operations)
    if from_status == to_status:
        return True
    
    return (from_status, to_status) in ALLOWED_TRANSITIONS


def validate_transition(from_status: str, to_status: str) -> None:
    """
    Validate status transition, raise ValueError if not allowed.
    
    Args:
        from_status: Current status
        to_status: Target status
    
    Raises:
        ValueError: If transition not allowed
    """
    if not is_transition_allowed(from_status, to_status):
        raise ValueError(
            f"Invalid FSM transition: {from_status} → {to_status}. "
            f"Allowed transitions: {ALLOWED_TRANSITIONS}"
        )
