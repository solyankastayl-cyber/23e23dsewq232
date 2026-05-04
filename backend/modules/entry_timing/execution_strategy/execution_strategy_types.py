"""
PHASE 4.3 — Execution Strategy Types

Defines execution strategies that map from entry modes.
"""

from enum import Enum
from typing import Dict, List


class ExecutionStrategy(Enum):
    """All possible execution strategies."""
    
    FULL_ENTRY_NOW = "FULL_ENTRY_NOW"
    # Execute full position immediately
    
    ENTER_ON_CLOSE_FULL = "ENTER_ON_CLOSE_FULL"
    # Wait for candle close, then full entry
    
    PARTIAL_NOW_PARTIAL_RETEST = "PARTIAL_NOW_PARTIAL_RETEST"
    # 50% now, 50% on retest
    
    WAIT_RETEST_FULL = "WAIT_RETEST_FULL"
    # Wait for retest, then full entry
    
    WAIT_PULLBACK_LIMIT = "WAIT_PULLBACK_LIMIT"
    # Place limit order at pullback level
    
    CONFIRM_THEN_ENTER = "CONFIRM_THEN_ENTER"
    # Wait for confirmation signal, then enter
    
    SKIP_ENTRY = "SKIP_ENTRY"
    # Do not enter


EXECUTION_STRATEGIES: List[str] = [s.value for s in ExecutionStrategy]


STRATEGY_DESCRIPTIONS: Dict[str, str] = {
    "FULL_ENTRY_NOW": "Execute full position immediately at market",
    "ENTER_ON_CLOSE_FULL": "Wait for candle close confirmation, then full entry",
    "PARTIAL_NOW_PARTIAL_RETEST": "Split: 50% at market now, 50% limit at retest level",
    "WAIT_RETEST_FULL": "Place limit order at retest level for full position",
    "WAIT_PULLBACK_LIMIT": "Place limit order at pullback level (extension too high)",
    "CONFIRM_THEN_ENTER": "Wait for additional confirmation before entering",
    "SKIP_ENTRY": "Do not enter - conditions not suitable"
}


# Mapping from entry mode to default execution strategy
MODE_TO_STRATEGY: Dict[str, str] = {
    "ENTER_NOW": "FULL_ENTRY_NOW",
    "ENTER_ON_CLOSE": "ENTER_ON_CLOSE_FULL",
    "WAIT_RETEST": "WAIT_RETEST_FULL",
    "WAIT_PULLBACK": "WAIT_PULLBACK_LIMIT",
    "WAIT_CONFIRMATION": "CONFIRM_THEN_ENTER",
    "SKIP_LATE_ENTRY": "SKIP_ENTRY",
    "SKIP_CONFLICTED": "SKIP_ENTRY"
}


def get_strategy_info(strategy: str) -> Dict:
    """Get full information about a strategy."""
    return {
        "strategy": strategy,
        "description": STRATEGY_DESCRIPTIONS.get(strategy, "Unknown"),
        "allows_entry": strategy != "SKIP_ENTRY"
    }
