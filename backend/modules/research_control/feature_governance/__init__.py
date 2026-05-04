"""
PHASE 17.1 — Feature Governance Engine
=======================================
First layer of Research Control Fabric.

Evaluates each feature across 5 dimensions:
1. Stability - How stable is the feature over time
2. Drift - Has the distribution drifted from baseline
3. Coverage - How often is the feature available/valid
4. Redundancy - Does the feature duplicate others
5. Predictive Utility - Does the feature provide signal value
"""

from modules.research_control.feature_governance.feature_governance_engine import (
    get_feature_governance_engine,
    FeatureGovernanceEngine,
)
from modules.research_control.feature_governance.feature_governance_types import (
    FeatureGovernanceState,
    GovernanceState,
    GovernanceDimension,
)
