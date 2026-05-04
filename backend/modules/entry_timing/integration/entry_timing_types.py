"""
PHASE 4.5 + 4.8.1 — Entry Timing Types

Final decision types for the integration layer.
Updated with microstructure-aware decisions.
"""

from typing import Dict, List


FINAL_ENTRY_DECISIONS: List[str] = [
    "GO",
    "GO_FULL",
    "GO_REDUCED",
    "WAIT",
    "WAIT_MICROSTRUCTURE",
    "SKIP",
]


DECISION_DESCRIPTIONS: Dict[str, str] = {
    "GO": "Execute full entry - all conditions met",
    "GO_FULL": "Execute full entry - timing + microstructure fully aligned",
    "GO_REDUCED": "Execute with reduced size - moderate conditions",
    "WAIT": "Wait for better entry conditions",
    "WAIT_MICROSTRUCTURE": "Wait for microstructure confirmation (liquidity/sweep/absorption)",
    "SKIP": "Do not enter - conditions not suitable",
}


DECISION_ALLOWS_ENTRY: Dict[str, bool] = {
    "GO": True,
    "GO_FULL": True,
    "GO_REDUCED": True,
    "WAIT": False,
    "WAIT_MICROSTRUCTURE": False,
    "SKIP": False,
}


DECISION_SIZE_MODIFIERS: Dict[str, float] = {
    "GO": 1.0,
    "GO_FULL": 1.0,
    "GO_REDUCED": 0.6,
    "WAIT": 0.0,
    "WAIT_MICROSTRUCTURE": 0.0,
    "SKIP": 0.0,
}
