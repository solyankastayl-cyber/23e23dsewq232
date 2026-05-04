"""
PHASE 21.2 — Reserve Capital Engine
===================================
Sub-engine for reserve capital management.

Determines how much capital to hold inactive based on regime.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    RESERVE_CAPITAL_BY_REGIME,
)


class ReserveCapitalEngine:
    """
    Reserve Capital Sub-Engine.
    
    Determines reserve capital requirements based on:
    - Market regime
    - Portfolio state
    - Risk conditions
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_reserve = 0.10  # 10% default
        self._reserve_by_regime = RESERVE_CAPITAL_BY_REGIME.copy()
    
    def compute_reserve(
        self,
        total_capital: float,
        regime: str = "normal",
        portfolio_state: str = "NORMAL",
        risk_state: str = "NORMAL",
        volatility_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Compute reserve capital requirement.
        
        Rules:
        - normal regime      → 10% reserve
        - unclear / mixed    → 15%
        - high vol / stressed → 20%
        - crisis / emergency → 30%+
        
        Returns:
            {
                "reserve_ratio": float,
                "reserve_capital": float,
                "regime_category": str,
            }
        """
        # Determine regime category
        regime_category = self._categorize_regime(
            regime=regime,
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            volatility_state=volatility_state,
        )
        
        # Get reserve ratio
        reserve_ratio = self._reserve_by_regime.get(regime_category, self._base_reserve)
        
        # Calculate reserve capital
        reserve_capital = total_capital * reserve_ratio
        
        return {
            "reserve_ratio": reserve_ratio,
            "reserve_capital": reserve_capital,
            "regime_category": regime_category,
        }
    
    def _categorize_regime(
        self,
        regime: str,
        portfolio_state: str,
        risk_state: str,
        volatility_state: str,
    ) -> str:
        """Categorize current conditions for reserve calculation."""
        regime_upper = regime.upper()
        portfolio_upper = portfolio_state.upper()
        risk_upper = risk_state.upper()
        vol_upper = volatility_state.upper()
        
        # Emergency conditions
        if portfolio_upper in ["RISK_OFF", "EMERGENCY", "LIQUIDATION"]:
            return "emergency"
        
        if risk_upper in ["SEVERE", "CRITICAL", "EMERGENCY"]:
            return "crisis"
        
        # Crisis conditions
        if regime_upper in ["CRISIS", "CRASH"]:
            return "crisis"
        
        # Stressed conditions
        if vol_upper in ["HIGH", "EXTREME", "EXPANSION"]:
            return "high_vol"
        
        if portfolio_upper in ["DEFENSIVE", "REDUCE"]:
            return "stressed"
        
        if risk_upper in ["ELEVATED", "HIGH"]:
            return "stressed"
        
        # Mixed/unclear conditions
        if regime_upper in ["MIXED", "UNCLEAR", "TRANSITION"]:
            return "mixed"
        
        if regime_upper in ["SQUEEZE", "VOL"]:
            return "unclear"
        
        # Normal conditions
        return "normal"
    
    def get_min_reserve(self) -> float:
        """Get minimum reserve ratio."""
        return min(self._reserve_by_regime.values())
    
    def get_max_reserve(self) -> float:
        """Get maximum reserve ratio."""
        return max(self._reserve_by_regime.values())


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ReserveCapitalEngine] = None


def get_reserve_capital_engine() -> ReserveCapitalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ReserveCapitalEngine()
    return _engine
