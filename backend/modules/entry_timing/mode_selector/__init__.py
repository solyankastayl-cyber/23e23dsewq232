"""
PHASE 4.2 — Entry Mode Selector

Decides HOW to enter, not whether to enter.
Does not change direction or signal - only controls timing.

Entry Modes:
- ENTER_NOW: Execute immediately
- ENTER_ON_CLOSE: Wait for candle close confirmation
- WAIT_RETEST: Wait for price to retest breakout level
- WAIT_PULLBACK: Wait for pullback after extension
- WAIT_CONFIRMATION: Wait for additional confirmation
- SKIP_LATE_ENTRY: Skip - price moved too far
- SKIP_CONFLICTED: Skip - conflicting signals
"""

from .entry_mode_types import (
    EntryMode,
    ENTRY_MODES,
    MODE_DESCRIPTIONS,
    MODE_RISK_LEVELS,
    MODE_WAIT_TIMES
)
from .entry_mode_rules import EntryModeRules
from .entry_mode_selector import EntryModeSelector
from .entry_mode_engine import EntryModeEngine, get_entry_mode_engine

__all__ = [
    "EntryMode",
    "ENTRY_MODES",
    "MODE_DESCRIPTIONS",
    "MODE_RISK_LEVELS",
    "MODE_WAIT_TIMES",
    "EntryModeRules",
    "EntryModeSelector",
    "EntryModeEngine",
    "get_entry_mode_engine",
]
