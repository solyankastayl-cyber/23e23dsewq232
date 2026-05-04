"""
PHASE 4.5 + 4.8.1 — Entry Timing Integration Layer

Unifies the entire Entry Timing Stack into a single decision:
- GO: Execute entry
- GO_FULL: Execute full entry (timing + micro aligned)
- GO_REDUCED: Execute with reduced size
- WAIT: Wait for better conditions
- WAIT_MICROSTRUCTURE: Wait for microstructure confirmation
- SKIP: Do not enter
"""

from .entry_timing_types import FINAL_ENTRY_DECISIONS, DECISION_DESCRIPTIONS
from .entry_governor import EntryGovernor
from .entry_decision_builder import EntryDecisionBuilder
from .microstructure_merge_engine import MicrostructureMergeEngine
from .entry_timing_integration import EntryTimingIntegration, get_entry_timing_integration

__all__ = [
    "FINAL_ENTRY_DECISIONS",
    "DECISION_DESCRIPTIONS",
    "EntryGovernor",
    "EntryDecisionBuilder",
    "MicrostructureMergeEngine",
    "EntryTimingIntegration",
    "get_entry_timing_integration",
]
