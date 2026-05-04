"""
PHASE 4.2 — Entry Mode Types

Defines all entry mode types with descriptions and properties.
These are FIXED and should not be changed without careful consideration.
"""

from enum import Enum
from typing import Dict, List


class EntryMode(Enum):
    """All possible entry modes."""
    
    # === Immediate Entry ===
    ENTER_NOW = "ENTER_NOW"
    # Execute immediately - strong setup with good alignment
    
    # === Delayed Entry ===
    ENTER_ON_CLOSE = "ENTER_ON_CLOSE"
    # Wait for current candle to close before entering
    
    WAIT_RETEST = "WAIT_RETEST"
    # Wait for price to retest the breakout/trigger level
    
    WAIT_PULLBACK = "WAIT_PULLBACK"
    # Wait for pullback after price extended too far
    
    WAIT_CONFIRMATION = "WAIT_CONFIRMATION"
    # Wait for additional confirmation signal
    
    # === Skip Entry ===
    SKIP_LATE_ENTRY = "SKIP_LATE_ENTRY"
    # Skip - price moved too far, no good entry available
    
    SKIP_CONFLICTED = "SKIP_CONFLICTED"
    # Skip - conflicting signals between timeframes


# List version for validation
ENTRY_MODES: List[str] = [m.value for m in EntryMode]


# Mode descriptions
MODE_DESCRIPTIONS: Dict[str, str] = {
    "ENTER_NOW": "Execute immediately - strong setup with good alignment",
    "ENTER_ON_CLOSE": "Wait for current candle close to confirm the move",
    "WAIT_RETEST": "Wait for price to retest the breakout level",
    "WAIT_PULLBACK": "Wait for pullback after price extended from trigger",
    "WAIT_CONFIRMATION": "Wait for additional confirmation signal",
    "SKIP_LATE_ENTRY": "Skip entry - price moved too far from trigger",
    "SKIP_CONFLICTED": "Skip entry - conflicting signals between timeframes"
}


# Risk levels for each mode
MODE_RISK_LEVELS: Dict[str, str] = {
    "ENTER_NOW": "medium",        # Standard risk
    "ENTER_ON_CLOSE": "low",      # Lower risk with confirmation
    "WAIT_RETEST": "low",         # Lower risk at better price
    "WAIT_PULLBACK": "low",       # Better entry after pullback
    "WAIT_CONFIRMATION": "low",   # Additional safety
    "SKIP_LATE_ENTRY": "none",    # No entry = no risk
    "SKIP_CONFLICTED": "none"     # No entry = no risk
}


# Typical wait times (in candles/periods)
MODE_WAIT_TIMES: Dict[str, str] = {
    "ENTER_NOW": "0",
    "ENTER_ON_CLOSE": "1 candle",
    "WAIT_RETEST": "1-3 candles",
    "WAIT_PULLBACK": "2-5 candles",
    "WAIT_CONFIRMATION": "1-2 candles",
    "SKIP_LATE_ENTRY": "N/A",
    "SKIP_CONFLICTED": "N/A"
}


# Whether mode allows entry
MODE_ALLOWS_ENTRY: Dict[str, bool] = {
    "ENTER_NOW": True,
    "ENTER_ON_CLOSE": True,
    "WAIT_RETEST": True,
    "WAIT_PULLBACK": True,
    "WAIT_CONFIRMATION": True,
    "SKIP_LATE_ENTRY": False,
    "SKIP_CONFLICTED": False
}


# Priority for mode selection (higher = prefer over lower)
MODE_PRIORITY: Dict[str, int] = {
    "SKIP_CONFLICTED": 100,    # Highest - safety first
    "SKIP_LATE_ENTRY": 90,
    "WAIT_PULLBACK": 70,
    "WAIT_CONFIRMATION": 60,
    "ENTER_ON_CLOSE": 50,
    "WAIT_RETEST": 40,
    "ENTER_NOW": 30            # Lowest - default fallback
}


def get_mode_info(mode: str) -> Dict:
    """Get full information about a mode."""
    return {
        "mode": mode,
        "description": MODE_DESCRIPTIONS.get(mode, "Unknown"),
        "risk_level": MODE_RISK_LEVELS.get(mode, "unknown"),
        "wait_time": MODE_WAIT_TIMES.get(mode, "unknown"),
        "allows_entry": MODE_ALLOWS_ENTRY.get(mode, False),
        "priority": MODE_PRIORITY.get(mode, 0)
    }
