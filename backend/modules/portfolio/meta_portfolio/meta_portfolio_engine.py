"""
PHASE 18.3 — Meta Portfolio Engine
==================================
Main aggregator for Meta Portfolio Layer.

Combines:
- Portfolio Intelligence (risk assessment)
- Portfolio Constraints (limit enforcement)

Into a single unified portfolio management layer.

Key responsibilities:
- Evaluate portfolio state
- Decide if trades are allowed
- Correct risk and capital allocation
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.portfolio.meta_portfolio.meta_portfolio_types import (
    MetaPortfolioState,
    PortfolioState,
    STATE_PRIORITY,
    INTELLIGENCE_TO_PORTFOLIO,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_engine import (
    get_portfolio_intelligence_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    PortfolioRiskState,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_engine import (
    get_portfolio_constraint_engine,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintState,
)


class MetaPortfolioEngine:
    """
    Meta Portfolio Engine - PHASE 18.3
    
    Unified portfolio management layer.
    
    Combines:
    - Portfolio Intelligence: Risk assessment, concentration, exposure
    - Portfolio Constraints: Hard/soft limit enforcement
    
    State Logic:
    - HARD_LIMIT → RISK_OFF, allowed=False
    - SOFT_LIMIT → CONSTRAINED, allowed=True
    - OK + BALANCED → BALANCED
    - OK + CONCENTRATED/OVERLOADED → CONSTRAINED
    - OK + DEFENSIVE → RISK_OFF
    
    Modifier Combination:
    - final_confidence = min(intelligence_confidence, constraint_confidence)
    - final_capital = min(intelligence_capital, constraint_capital)
    """
    
    def __init__(self):
        self.intelligence_engine = get_portfolio_intelligence_engine()
        self.constraint_engine = get_portfolio_constraint_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def analyze_portfolio(
        self,
        portfolio_id: str = "default"
    ) -> MetaPortfolioState:
        """
        Full meta portfolio analysis.
        
        Args:
            portfolio_id: ID of portfolio to analyze
        
        Returns:
            MetaPortfolioState with unified analysis
        """
        now = datetime.now(timezone.utc)
        
        # Get Portfolio Intelligence state
        intelligence_state = self.intelligence_engine.analyze_portfolio(portfolio_id)
        
        # Get Portfolio Constraints state
        constraint_state = self.constraint_engine.check_constraints(portfolio_id)
        
        return self._combine_states(intelligence_state, constraint_state)
    
    def _combine_states(
        self,
        intelligence,
        constraints,
    ) -> MetaPortfolioState:
        """
        Combine intelligence and constraints into unified state.
        
        Args:
            intelligence: PortfolioIntelligenceState
            constraints: PortfolioConstraintState
        
        Returns:
            MetaPortfolioState
        """
        now = datetime.now(timezone.utc)
        
        # STEP 3: Determine portfolio state
        portfolio_state = self._determine_portfolio_state(
            intelligence.portfolio_risk_state.value,
            constraints.constraint_state.value,
        )
        
        # STEP 4: Combine modifiers (take minimum)
        confidence_modifier = min(
            intelligence.confidence_modifier,
            constraints.confidence_modifier,
        )
        capital_modifier = min(
            intelligence.capital_modifier,
            constraints.capital_modifier,
        )
        
        # Determine allowed (from constraints, but DEFENSIVE also blocks)
        allowed = constraints.allowed
        if portfolio_state == PortfolioState.RISK_OFF:
            allowed = False
        
        # STEP 5: Determine recommended action (constraint reason has priority)
        recommended_action = self._determine_recommended_action(
            intelligence.recommended_action.value,
            constraints.reason,
            portfolio_state,
        )
        
        # Build reason
        reason = self._build_reason(
            constraints.constraint_state.value,
            intelligence.portfolio_risk_state.value,
            constraints.reason,
        )
        
        return MetaPortfolioState(
            portfolio_state=portfolio_state,
            intelligence_state=intelligence.portfolio_risk_state.value,
            constraint_state=constraints.constraint_state.value,
            allowed=allowed,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            net_exposure=intelligence.net_exposure,
            gross_exposure=intelligence.gross_exposure,
            concentration_score=intelligence.concentration_score,
            diversification_score=intelligence.diversification_score,
            recommended_action=recommended_action,
            reason=reason,
            timestamp=now,
            intelligence_details=intelligence.to_dict(),
            constraint_details=constraints.to_dict(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: PORTFOLIO STATE LOGIC
    # ═══════════════════════════════════════════════════════════
    
    def _determine_portfolio_state(
        self,
        intelligence_state: str,
        constraint_state: str,
    ) -> PortfolioState:
        """
        Determine unified portfolio state.
        
        Rules:
        - HARD_LIMIT → RISK_OFF
        - DEFENSIVE (intelligence) → RISK_OFF (regardless of constraint)
        - SOFT_LIMIT → CONSTRAINED
        - OK:
            - BALANCED → BALANCED
            - CONCENTRATED → CONSTRAINED
            - OVERLOADED → CONSTRAINED
        """
        # Check constraint HARD_LIMIT first (highest priority)
        if constraint_state == "HARD_LIMIT":
            return PortfolioState.RISK_OFF
        
        # DEFENSIVE intelligence also triggers RISK_OFF (before SOFT_LIMIT check)
        if intelligence_state == "DEFENSIVE":
            return PortfolioState.RISK_OFF
        
        # Check SOFT_LIMIT constraint
        if constraint_state == "SOFT_LIMIT":
            return PortfolioState.CONSTRAINED
        
        # Constraint is OK, use intelligence state
        return INTELLIGENCE_TO_PORTFOLIO.get(
            intelligence_state,
            PortfolioState.CONSTRAINED,  # Default to constrained for unknown states
        )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: RECOMMENDED ACTION
    # ═══════════════════════════════════════════════════════════
    
    def _determine_recommended_action(
        self,
        intelligence_action: str,
        constraint_reason: str,
        portfolio_state: PortfolioState,
    ) -> str:
        """
        Determine recommended action.
        
        Priority: constraint_reason > intelligence_action
        """
        # If constraint has a specific reason, use it
        if constraint_reason and constraint_reason != "All constraints satisfied":
            # Convert constraint reason to action
            reason_lower = constraint_reason.lower()
            
            if "cluster" in reason_lower:
                return "REDUCE_CLUSTER_EXPOSURE"
            elif "factor" in reason_lower:
                return "REDUCE_FACTOR_EXPOSURE"
            elif "leverage" in reason_lower or "gross" in reason_lower:
                return "DELEVER"
            elif "net" in reason_lower or "exposure" in reason_lower:
                return "REDUCE_EXPOSURE"
            else:
                return "REBALANCE"
        
        # Use intelligence action
        return intelligence_action
    
    def _build_reason(
        self,
        constraint_state: str,
        intelligence_state: str,
        constraint_reason: str,
    ) -> str:
        """Build human-readable reason string."""
        parts = []
        
        if constraint_state == "HARD_LIMIT":
            parts.append(f"Hard limit violated: {constraint_reason}")
        elif constraint_state == "SOFT_LIMIT":
            parts.append(f"Soft limit: {constraint_reason}")
        
        if intelligence_state == "DEFENSIVE":
            parts.append("Portfolio in defensive mode due to weak market breadth")
        elif intelligence_state == "OVERLOADED":
            parts.append("Portfolio overloaded - concentration too high")
        elif intelligence_state == "CONCENTRATED":
            parts.append("Portfolio concentrated - consider diversification")
        
        if not parts:
            return "Portfolio balanced, all systems nominal"
        
        return "; ".join(parts)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[MetaPortfolioEngine] = None


def get_meta_portfolio_engine() -> MetaPortfolioEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = MetaPortfolioEngine()
    return _engine
