"""
PHASE 17.2 — Factor Governance Engine
======================================
Second layer of Research Control Fabric.

Controls quality of alpha-factors/signals built from features.

Evaluates each factor across 5 dimensions:
1. Performance Stability - Return consistency
2. Regime Robustness - Works across market regimes
3. Capacity - Handles capital scaling
4. Crowding Risk - Not overcrowded by participants
5. Decay Velocity - How fast the factor degrades
"""

from modules.research_control.factor_governance.factor_governance_engine import (
    get_factor_governance_engine,
    FactorGovernanceEngine,
)
from modules.research_control.factor_governance.factor_governance_types import (
    FactorGovernanceState,
    FactorGovernanceState as FactorState,
    FactorDimension,
)
