"""
PHASE 22.1 — Risk State Engine
==============================
Sub-engine for determining portfolio risk state.

Classifies risk into NORMAL/ELEVATED/HIGH/CRITICAL.
"""

from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.institutional_risk.var_engine.var_types import (
    RiskState,
    RecommendedAction,
    RISK_STATE_THRESHOLDS,
    RISK_STATE_MODIFIERS,
)


class RiskStateEngine:
    """
    Risk State Sub-Engine.
    
    Determines portfolio risk state based on:
    - VaR ratio
    - Tail risk ratio
    - Volatility state
    """
    
    def __init__(self):
        """Initialize engine."""
        self._thresholds = RISK_STATE_THRESHOLDS.copy()
    
    def determine_risk_state(
        self,
        var_ratio: float,
        tail_risk_ratio: float = 1.20,
        volatility_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Determine risk state from VaR ratio.
        
        Thresholds:
        - var_ratio < 0.10      → NORMAL
        - var_ratio 0.10-0.18   → ELEVATED
        - var_ratio 0.18-0.28   → HIGH
        - var_ratio > 0.28      → CRITICAL
        
        With hard override for extreme conditions.
        
        Returns:
            {
                "risk_state": RiskState,
                "recommended_action": RecommendedAction,
                "base_state": str,
                "override_applied": bool,
            }
        """
        # Base classification
        if var_ratio < self._thresholds[RiskState.NORMAL]:
            base_state = RiskState.NORMAL
        elif var_ratio < self._thresholds[RiskState.ELEVATED]:
            base_state = RiskState.ELEVATED
        elif var_ratio < self._thresholds[RiskState.HIGH]:
            base_state = RiskState.HIGH
        else:
            base_state = RiskState.CRITICAL
        
        # Hard override for extreme conditions
        override_applied = False
        final_state = base_state
        
        vol_upper = volatility_state.upper()
        
        # Bump up if expanding volatility + high tail risk
        if vol_upper in ["EXPANDING", "EXTREME"] and tail_risk_ratio > 1.25:
            if final_state == RiskState.NORMAL:
                final_state = RiskState.ELEVATED
                override_applied = True
            elif final_state == RiskState.ELEVATED:
                final_state = RiskState.HIGH
                override_applied = True
            elif final_state == RiskState.HIGH:
                final_state = RiskState.CRITICAL
                override_applied = True
        
        # Map state to recommended action
        action_map = {
            RiskState.NORMAL: RecommendedAction.HOLD,
            RiskState.ELEVATED: RecommendedAction.REDUCE_RISK,
            RiskState.HIGH: RecommendedAction.DELEVER,
            RiskState.CRITICAL: RecommendedAction.EMERGENCY_CUT,
        }
        
        recommended_action = action_map[final_state]
        
        return {
            "risk_state": final_state,
            "recommended_action": recommended_action,
            "base_state": base_state.value,
            "override_applied": override_applied,
        }
    
    def get_modifiers(
        self,
        risk_state: RiskState,
    ) -> Tuple[float, float]:
        """Get confidence and capital modifiers for risk state."""
        modifiers = RISK_STATE_MODIFIERS.get(risk_state, {
            "confidence_modifier": 1.0,
            "capital_modifier": 1.0,
        })
        
        return (
            modifiers["confidence_modifier"],
            modifiers["capital_modifier"],
        )
    
    def is_action_required(
        self,
        risk_state: RiskState,
    ) -> bool:
        """Check if risk reduction action is required."""
        return risk_state in [RiskState.ELEVATED, RiskState.HIGH, RiskState.CRITICAL]
    
    def is_emergency(
        self,
        risk_state: RiskState,
    ) -> bool:
        """Check if in emergency state."""
        return risk_state == RiskState.CRITICAL


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[RiskStateEngine] = None


def get_risk_state_engine() -> RiskStateEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = RiskStateEngine()
    return _engine
