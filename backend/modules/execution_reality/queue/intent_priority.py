"""
Execution Intent Priority (P1.5 - Critical)
============================================

Priority-based execution order для survival под нагрузкой.

CRITICAL RULE:
STOP_LOSS НИКОГДА НЕ ЖДЁТ

Priority Order (lower number = higher priority):
1. STOP_LOSS (CRITICAL - prevent drawdown)
2. CLOSE_POSITION (CRITICAL - exit losing position)
3. REDUCE (HIGH - reduce exposure)
4. TAKE_PROFIT (MEDIUM - lock profits)
5. ENTRY (LOW - new position)
6. DEFAULT (LOWEST - unknown intent type)

Usage:
    priority = get_intent_priority("STOP_LOSS")  # Returns 1
    
    # In queue: orders sorted by priority (ascending)
    # STOP_LOSS executes before ENTRY even if ENTRY was submitted first
"""

from enum import IntEnum


class IntentPriority(IntEnum):
    """
    Intent priority levels (lower value = higher priority).
    
    CRITICAL: System survival (STOP_LOSS, CLOSE)
    HIGH: Risk reduction (REDUCE)
    MEDIUM: Profit taking (TAKE_PROFIT)
    LOW: New positions (ENTRY)
    """
    STOP_LOSS = 1      # CRITICAL: Stop loss to prevent catastrophic loss
    CLOSE_POSITION = 2  # CRITICAL: Close existing position (losing or manual)
    REDUCE = 3          # HIGH: Reduce position size (risk management)
    TAKE_PROFIT = 4     # MEDIUM: Take profit on winning position
    ENTRY = 5           # LOW: Enter new position
    DEFAULT = 999       # LOWEST: Unknown intent type (fallback)


# Intent type string mapping
PRIORITY_MAP = {
    "STOP_LOSS": IntentPriority.STOP_LOSS,
    "CLOSE": IntentPriority.CLOSE_POSITION,
    "CLOSE_POSITION": IntentPriority.CLOSE_POSITION,
    "REDUCE": IntentPriority.REDUCE,
    "REDUCE_POSITION": IntentPriority.REDUCE,
    "TAKE_PROFIT": IntentPriority.TAKE_PROFIT,
    "TP": IntentPriority.TAKE_PROFIT,
    "ENTRY": IntentPriority.ENTRY,
    "OPEN": IntentPriority.ENTRY,
    "OPEN_POSITION": IntentPriority.ENTRY,
}


def get_intent_priority(intent_type: str) -> int:
    """
    Get priority for intent type.
    
    Args:
        intent_type: Intent type string (e.g., "STOP_LOSS", "ENTRY")
    
    Returns:
        Priority integer (1-999, lower = higher priority)
    """
    intent_type_upper = intent_type.upper() if intent_type else "DEFAULT"
    return int(PRIORITY_MAP.get(intent_type_upper, IntentPriority.DEFAULT))


def is_critical_intent(intent_type: str) -> bool:
    """
    Check if intent is critical (STOP_LOSS or CLOSE).
    
    Critical intents should bypass queue and execute immediately.
    
    Args:
        intent_type: Intent type string
    
    Returns:
        True if critical (priority <= 2), False otherwise
    """
    priority = get_intent_priority(intent_type)
    return priority <= IntentPriority.CLOSE_POSITION


def get_priority_label(priority: int) -> str:
    """Get human-readable label for priority."""
    if priority == IntentPriority.STOP_LOSS:
        return "🔴 CRITICAL (STOP_LOSS)"
    elif priority == IntentPriority.CLOSE_POSITION:
        return "🔴 CRITICAL (CLOSE)"
    elif priority == IntentPriority.REDUCE:
        return "🟠 HIGH (REDUCE)"
    elif priority == IntentPriority.TAKE_PROFIT:
        return "🟡 MEDIUM (TAKE_PROFIT)"
    elif priority == IntentPriority.ENTRY:
        return "🟢 LOW (ENTRY)"
    else:
        return "⚪ DEFAULT (UNKNOWN)"
