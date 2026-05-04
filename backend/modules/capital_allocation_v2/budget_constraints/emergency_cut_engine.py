"""
PHASE 21.2 — Emergency Cut Engine
=================================
Sub-engine for emergency capital cuts.

Rapidly reduces budget when conditions deteriorate.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    EMERGENCY_CUT_LEVELS,
)


class EmergencyCutEngine:
    """
    Emergency Cut Sub-Engine.
    
    Determines emergency capital reduction based on:
    - Portfolio state
    - Market risk
    - Loop state
    - Volatility
    """
    
    def __init__(self):
        """Initialize engine."""
        self._cut_levels = EMERGENCY_CUT_LEVELS.copy()
    
    def compute_emergency_cut(
        self,
        portfolio_state: str = "NORMAL",
        risk_state: str = "NORMAL",
        loop_state: str = "HEALTHY",
        volatility_extreme: bool = False,
    ) -> Dict[str, Any]:
        """
        Compute emergency cut multiplier.
        
        Rules:
        - normal      → 1.00
        - mild stress → 0.90
        - defensive   → 0.75
        - emergency   → 0.50
        
        Returns:
            {
                "emergency_cut": float,
                "cut_level": str,
                "triggers": list,
            }
        """
        portfolio_upper = portfolio_state.upper()
        risk_upper = risk_state.upper()
        loop_upper = loop_state.upper()
        
        triggers = []
        cut_level = "normal"
        
        # Check for emergency conditions
        if portfolio_upper in ["RISK_OFF", "EMERGENCY", "LIQUIDATION"]:
            triggers.append(f"portfolio_state={portfolio_state}")
            cut_level = "emergency"
        
        if risk_upper in ["SEVERE", "CRITICAL", "EMERGENCY"]:
            triggers.append(f"risk_state={risk_state}")
            if cut_level != "emergency":
                cut_level = "emergency"
        
        if loop_upper in ["CRITICAL"]:
            triggers.append(f"loop_state={loop_state}")
            if cut_level != "emergency":
                cut_level = "emergency" if len(triggers) > 1 else "defensive"
        
        if volatility_extreme:
            triggers.append("volatility_extreme=True")
            if cut_level == "normal":
                cut_level = "defensive"
        
        # Check for defensive conditions
        if cut_level == "normal":
            if portfolio_upper in ["DEFENSIVE", "REDUCE", "CONSTRAINED"]:
                triggers.append(f"portfolio_state={portfolio_state}")
                cut_level = "defensive"
            elif risk_upper in ["ELEVATED", "HIGH"]:
                triggers.append(f"risk_state={risk_state}")
                cut_level = "defensive"
            elif loop_upper in ["DEGRADED"]:
                triggers.append(f"loop_state={loop_state}")
                cut_level = "defensive"
        
        # Check for mild stress
        if cut_level == "normal":
            if portfolio_upper in ["WATCHLIST", "CAUTION"]:
                triggers.append(f"portfolio_state={portfolio_state}")
                cut_level = "mild_stress"
            elif risk_upper in ["MODERATE"]:
                triggers.append(f"risk_state={risk_state}")
                cut_level = "mild_stress"
            elif loop_upper in ["ADAPTING"]:
                # Adapting is not stress, but note it
                pass
        
        emergency_cut = self._cut_levels.get(cut_level, 1.0)
        
        return {
            "emergency_cut": emergency_cut,
            "cut_level": cut_level,
            "triggers": triggers,
        }
    
    def is_emergency(self, cut_level: str) -> bool:
        """Check if in emergency state."""
        return cut_level == "emergency"
    
    def is_defensive(self, cut_level: str) -> bool:
        """Check if in defensive or worse state."""
        return cut_level in ["defensive", "emergency"]


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[EmergencyCutEngine] = None


def get_emergency_cut_engine() -> EmergencyCutEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = EmergencyCutEngine()
    return _engine
