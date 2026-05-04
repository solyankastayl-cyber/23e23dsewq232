"""
PHASE 21.2 — Regime Throttle Engine
===================================
Sub-engine for regime-based capital throttling.

Adjusts budget based on market regime.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    REGIME_THROTTLE,
)


class RegimeThrottleEngine:
    """
    Regime Throttle Sub-Engine.
    
    Throttles capital deployment based on market regime:
    - Clean trend → full deployment
    - Range → reduced
    - Squeeze → further reduced
    - Crisis → minimal
    """
    
    def __init__(self):
        """Initialize engine."""
        self._throttle_map = REGIME_THROTTLE.copy()
    
    def compute_throttle(
        self,
        regime: str = "MIXED",
        regime_confidence: float = 0.7,
        allocation_confidence: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Compute regime-based throttle multiplier.
        
        Rules:
        - TREND clean       → 1.00
        - RANGE             → 0.85
        - SQUEEZE           → 0.75
        - HIGH_VOL          → 0.70
        - MIXED / unclear   → 0.80
        - CRISIS / risk_off → 0.50
        
        Returns:
            {
                "regime_throttle": float,
                "base_throttle": float,
                "confidence_adjustment": float,
            }
        """
        regime_upper = regime.upper()
        
        # Get base throttle
        base_throttle = self._throttle_map.get(regime_upper, 0.80)
        
        # Confidence adjustment
        # Low confidence → reduce throttle further
        # High confidence → slight boost (up to 5%)
        confidence_avg = (regime_confidence + allocation_confidence) / 2
        
        if confidence_avg >= 0.8:
            confidence_adjustment = 0.05
        elif confidence_avg >= 0.6:
            confidence_adjustment = 0.0
        elif confidence_avg >= 0.4:
            confidence_adjustment = -0.05
        else:
            confidence_adjustment = -0.10
        
        # Calculate final throttle
        regime_throttle = base_throttle + confidence_adjustment
        
        # Clamp to reasonable range
        regime_throttle = max(0.40, min(1.05, regime_throttle))
        
        return {
            "regime_throttle": regime_throttle,
            "base_throttle": base_throttle,
            "confidence_adjustment": confidence_adjustment,
            "regime_input": regime_upper,
        }
    
    def get_throttle_for_regime(self, regime: str) -> float:
        """Get base throttle for a specific regime."""
        return self._throttle_map.get(regime.upper(), 0.80)
    
    def is_throttled(self, regime_throttle: float) -> bool:
        """Check if currently throttled."""
        return regime_throttle < 0.95
    
    def is_severely_throttled(self, regime_throttle: float) -> bool:
        """Check if severely throttled."""
        return regime_throttle < 0.70


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[RegimeThrottleEngine] = None


def get_regime_throttle_engine() -> RegimeThrottleEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = RegimeThrottleEngine()
    return _engine
