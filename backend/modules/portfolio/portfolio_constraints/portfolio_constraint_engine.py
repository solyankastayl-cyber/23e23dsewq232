"""
PHASE 18.2 — Portfolio Constraint Engine
========================================
Main aggregator for Portfolio Constraint checking.

Combines all constraint engines:
- exposure_constraint_engine (HARD)
- cluster_constraint_engine (SOFT)
- factor_constraint_engine (SOFT)
- leverage_constraint_engine (HARD)

Pipeline position:
Signal → Portfolio Intelligence → Portfolio Constraints → Trading Decision
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    PortfolioConstraintState,
    ConstraintState,
    ConstraintViolation,
    ViolationType,
    ConstraintType,
    CONSTRAINT_STATE_MODIFIERS,
)
from modules.portfolio.portfolio_constraints.exposure_constraint_engine import (
    get_exposure_constraint_engine,
)
from modules.portfolio.portfolio_constraints.cluster_constraint_engine import (
    get_cluster_constraint_engine,
)
from modules.portfolio.portfolio_constraints.factor_constraint_engine import (
    get_factor_constraint_engine,
)
from modules.portfolio.portfolio_constraints.leverage_constraint_engine import (
    get_leverage_constraint_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_engine import (
    get_portfolio_intelligence_engine,
)


class PortfolioConstraintEngine:
    """
    Portfolio Constraint Engine - PHASE 18.2
    
    Checks portfolio constraints before trade execution.
    Determines if a new position CAN be opened even if signal is strong.
    
    Constraint Types:
    - HARD CONSTRAINTS: Cannot be violated (exposure, leverage)
    - SOFT CONSTRAINTS: Can violate with penalty (cluster, factor)
    
    State Logic:
    - no violations → OK
    - factor OR cluster violation → SOFT_LIMIT
    - exposure OR leverage violation → HARD_LIMIT
    
    Allowed Logic:
    - OK → allowed = True
    - SOFT_LIMIT → allowed = True
    - HARD_LIMIT → allowed = False
    """
    
    def __init__(self):
        # Sub-engines
        self.exposure_engine = get_exposure_constraint_engine()
        self.cluster_engine = get_cluster_constraint_engine()
        self.factor_engine = get_factor_constraint_engine()
        self.leverage_engine = get_leverage_constraint_engine()
        
        # Portfolio intelligence for getting current state
        self.portfolio_intelligence = get_portfolio_intelligence_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def check_constraints(
        self,
        portfolio_id: str = "default"
    ) -> PortfolioConstraintState:
        """
        Check all portfolio constraints.
        
        Args:
            portfolio_id: ID of portfolio to check
        
        Returns:
            PortfolioConstraintState with full analysis
        """
        now = datetime.now(timezone.utc)
        
        # Get current portfolio state from Portfolio Intelligence
        portfolio_state = self.portfolio_intelligence.analyze_portfolio(portfolio_id)
        
        return self.check_constraints_from_state(
            net_exposure=portfolio_state.net_exposure,
            gross_exposure=portfolio_state.gross_exposure,
            cluster_exposure=portfolio_state.cluster_exposure,
            factor_exposure=portfolio_state.factor_exposure,
        )
    
    def check_constraints_from_state(
        self,
        net_exposure: float,
        gross_exposure: float,
        cluster_exposure: Dict[str, float],
        factor_exposure: Dict[str, float],
    ) -> PortfolioConstraintState:
        """
        Check constraints from provided state values.
        
        Args:
            net_exposure: Current net exposure
            gross_exposure: Current gross exposure
            cluster_exposure: Dict of cluster exposures
            factor_exposure: Dict of factor exposures
        
        Returns:
            PortfolioConstraintState
        """
        now = datetime.now(timezone.utc)
        all_violations = []
        
        # STEP 2: Check exposure constraints (HARD)
        exposure_violation, exposure_violations = self.exposure_engine.check_constraints(
            net_exposure, gross_exposure
        )
        all_violations.extend(exposure_violations)
        
        # STEP 3: Check cluster constraints (SOFT)
        cluster_violation, cluster_violations = self.cluster_engine.check_constraints(
            cluster_exposure
        )
        all_violations.extend(cluster_violations)
        
        # STEP 4: Check factor constraints (SOFT)
        factor_violation, factor_violations = self.factor_engine.check_constraints(
            factor_exposure
        )
        all_violations.extend(factor_violations)
        
        # STEP 5: Check leverage constraints (HARD)
        leverage_violation, leverage_violations = self.leverage_engine.check_constraints(
            gross_exposure
        )
        all_violations.extend(leverage_violations)
        
        # STEP 6: Determine constraint state
        constraint_state = self._determine_constraint_state(
            exposure_violation,
            cluster_violation,
            factor_violation,
            leverage_violation,
        )
        
        # STEP 7: Determine if allowed
        allowed = self._determine_allowed(constraint_state)
        
        # STEP 8: Get modifiers
        modifiers = CONSTRAINT_STATE_MODIFIERS[constraint_state]
        
        # Build reason
        reason = self._build_reason(
            constraint_state,
            exposure_violation,
            cluster_violation,
            factor_violation,
            leverage_violation,
            all_violations,
        )
        
        # Build constraint values
        constraint_values = self._build_constraint_values(
            net_exposure,
            gross_exposure,
            cluster_exposure,
            factor_exposure,
        )
        
        return PortfolioConstraintState(
            constraint_state=constraint_state,
            exposure_violation=exposure_violation,
            cluster_violation=cluster_violation,
            factor_violation=factor_violation,
            leverage_violation=leverage_violation,
            allowed=allowed,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            reason=reason,
            timestamp=now,
            violations=all_violations,
            constraint_values=constraint_values,
        )
    
    # ═══════════════════════════════════════════════════════════
    # STATE DETERMINATION (STEP 6)
    # ═══════════════════════════════════════════════════════════
    
    def _determine_constraint_state(
        self,
        exposure_violation: bool,
        cluster_violation: bool,
        factor_violation: bool,
        leverage_violation: bool,
    ) -> ConstraintState:
        """
        Determine overall constraint state.
        
        Rules:
        - no violations → OK
        - factor OR cluster violation → SOFT_LIMIT
        - exposure OR leverage violation → HARD_LIMIT
        """
        # Check HARD constraints first (exposure, leverage)
        if exposure_violation or leverage_violation:
            return ConstraintState.HARD_LIMIT
        
        # Check SOFT constraints (factor, cluster)
        if factor_violation or cluster_violation:
            return ConstraintState.SOFT_LIMIT
        
        # No violations
        return ConstraintState.OK
    
    # ═══════════════════════════════════════════════════════════
    # ALLOWED LOGIC (STEP 7)
    # ═══════════════════════════════════════════════════════════
    
    def _determine_allowed(self, constraint_state: ConstraintState) -> bool:
        """
        Determine if new position is allowed.
        
        Rules:
        - OK → allowed = True
        - SOFT_LIMIT → allowed = True
        - HARD_LIMIT → allowed = False
        """
        if constraint_state == ConstraintState.HARD_LIMIT:
            return False
        return True
    
    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _build_reason(
        self,
        state: ConstraintState,
        exposure_violation: bool,
        cluster_violation: bool,
        factor_violation: bool,
        leverage_violation: bool,
        violations: List[ConstraintViolation],
    ) -> str:
        """Build human-readable reason string."""
        if state == ConstraintState.OK:
            return "All constraints satisfied"
        
        reasons = []
        
        if exposure_violation:
            reasons.append("exposure limit exceeded")
        if leverage_violation:
            reasons.append("leverage limit exceeded")
        if cluster_violation:
            reasons.append("cluster exposure exceeded threshold")
        if factor_violation:
            reasons.append("factor exposure exceeded threshold")
        
        if not reasons:
            return "Unknown constraint violation"
        
        return "; ".join(reasons)
    
    def _build_constraint_values(
        self,
        net_exposure: float,
        gross_exposure: float,
        cluster_exposure: Dict[str, float],
        factor_exposure: Dict[str, float],
    ) -> Dict:
        """Build constraint values dict for reporting."""
        return {
            "exposure": self.exposure_engine.get_constraint_values(
                net_exposure, gross_exposure
            ),
            "cluster": self.cluster_engine.get_constraint_values(cluster_exposure),
            "factor": self.factor_engine.get_constraint_values(factor_exposure),
            "leverage": self.leverage_engine.get_constraint_values(gross_exposure),
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[PortfolioConstraintEngine] = None


def get_portfolio_constraint_engine() -> PortfolioConstraintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PortfolioConstraintEngine()
    return _engine
