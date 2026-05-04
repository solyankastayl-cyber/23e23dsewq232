"""
PHASE 17.3 — Deployment Governance Engine
==========================================
Third layer of Research Control Fabric.

Controls factor lifecycle and deployment decisions:
- Can signal/factor go to live?
- Should it stay in shadow mode?
- Can capital allocation be increased?
- Should it be rolled back / frozen?
- Does factor comply with deployment policy?

Deployment States: SHADOW → CANDIDATE → LIVE → FROZEN → RETIRED
"""

from modules.research_control.deployment_governance.deployment_governance_engine import (
    get_deployment_governance_engine,
    DeploymentGovernanceEngine,
)
from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentGovernanceResult,
    DeploymentState,
    GovernanceAction,
)
