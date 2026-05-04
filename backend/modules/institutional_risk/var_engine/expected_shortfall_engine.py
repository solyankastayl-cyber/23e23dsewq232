"""
PHASE 22.1 — Expected Shortfall Engine
======================================
Sub-engine for calculating Expected Shortfall (CVaR).

Expected Shortfall measures tail risk beyond VaR.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone


class ExpectedShortfallEngine:
    """
    Expected Shortfall Sub-Engine.
    
    Calculates Expected Shortfall (CVaR) based on VaR values.
    ES represents average loss in worst cases beyond VaR.
    """
    
    def __init__(self):
        """Initialize engine."""
        self._es_95_multiplier = 1.20  # ES95 = VaR95 * 1.20
        self._es_99_multiplier = 1.25  # ES99 = VaR99 * 1.25
    
    def compute_expected_shortfall(
        self,
        portfolio_var_95: float,
        portfolio_var_99: float,
        volatility_state: str = "NORMAL",
        tail_risk_elevated: bool = False,
    ) -> Dict[str, Any]:
        """
        Compute Expected Shortfall at 95% and 99% confidence.
        
        Formula (simplified):
        ES_95 = VaR_95 × 1.20 (× tail adjustment)
        ES_99 = VaR_99 × 1.25 (× tail adjustment)
        
        Returns:
            {
                "expected_shortfall_95": float,
                "expected_shortfall_99": float,
                "tail_risk_ratio": float,
            }
        """
        # Base ES calculation
        es_95_mult = self._es_95_multiplier
        es_99_mult = self._es_99_multiplier
        
        # Adjust for volatility state
        vol_upper = volatility_state.upper()
        if vol_upper in ["HIGH", "EXPANDING", "EXTREME"]:
            es_95_mult *= 1.10
            es_99_mult *= 1.12
        elif vol_upper == "LOW":
            es_95_mult *= 0.95
            es_99_mult *= 0.95
        
        # Adjust for elevated tail risk
        if tail_risk_elevated:
            es_95_mult *= 1.15
            es_99_mult *= 1.18
        
        # Calculate ES
        expected_shortfall_95 = portfolio_var_95 * es_95_mult
        expected_shortfall_99 = portfolio_var_99 * es_99_mult
        
        # Calculate tail risk ratio (ES/VaR)
        tail_risk_ratio = expected_shortfall_95 / portfolio_var_95 if portfolio_var_95 > 0 else 1.0
        
        return {
            "expected_shortfall_95": expected_shortfall_95,
            "expected_shortfall_99": expected_shortfall_99,
            "tail_risk_ratio": tail_risk_ratio,
            "es_95_multiplier": es_95_mult,
            "es_99_multiplier": es_99_mult,
        }
    
    def is_tail_risk_elevated(
        self,
        tail_risk_ratio: float,
        threshold: float = 1.25,
    ) -> bool:
        """Check if tail risk is elevated."""
        return tail_risk_ratio > threshold
    
    def get_tail_severity(
        self,
        tail_risk_ratio: float,
    ) -> str:
        """Get severity of tail risk."""
        if tail_risk_ratio >= 1.40:
            return "CRITICAL"
        elif tail_risk_ratio >= 1.30:
            return "HIGH"
        elif tail_risk_ratio >= 1.22:
            return "ELEVATED"
        else:
            return "NORMAL"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ExpectedShortfallEngine] = None


def get_expected_shortfall_engine() -> ExpectedShortfallEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ExpectedShortfallEngine()
    return _engine
