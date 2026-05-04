"""
PHASE 17.4 — Attribution / Failure Forensics Engine
=====================================================
Final layer of Research Control Fabric.

Transforms system from "black box" to explainable trading system.

Key Functions:
1. Explains WHY trade happened
2. Explains WHY trade failed
3. Shows WHICH LAYER was responsible

Analyzes:
- TAHypothesis
- ExchangeContext
- MarketState
- Alpha Ecology
- Alpha Interaction
- Decision Layer
- Position Sizing
- Execution Mode
"""

from modules.research_control.attribution.attribution_engine import (
    get_attribution_engine,
    AttributionEngine,
)
from modules.research_control.attribution.attribution_types import (
    TradeAttributionReport,
    TradeOutcome,
    FailureClassification,
    SystemLayer,
)
