"""
PHASE 22.1 — Portfolio VaR Engine
=================================
Sub-engine for calculating Portfolio Value at Risk.

Computes VaR at 95% and 99% confidence levels.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone

from modules.institutional_risk.var_engine.var_types import (
    VOLATILITY_MULTIPLIERS,
    REGIME_MULTIPLIERS,
)


class PortfolioVaREngine:
    """
    Portfolio VaR Sub-Engine.
    
    Calculates Portfolio VaR based on:
    - Gross exposure
    - Volatility state
    - Market regime
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_var_coefficient = 0.08  # 8% base daily VaR
        self._var_99_multiplier = 1.35      # VaR99 = VaR95 * 1.35
    
    def compute_var(
        self,
        gross_exposure: float = 0.5,
        volatility_state: str = "NORMAL",
        regime: str = "MIXED",
        position_concentration: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Compute Portfolio VaR at 95% and 99% confidence.
        
        Formula:
        portfolio_var_95 = gross_exposure × volatility_mult × regime_mult × base_coef
        portfolio_var_99 = portfolio_var_95 × 1.35
        
        Returns:
            {
                "portfolio_var_95": float,
                "portfolio_var_99": float,
                "components": dict,
            }
        """
        vol_upper = volatility_state.upper()
        regime_upper = regime.upper()
        
        # Get multipliers
        vol_mult = VOLATILITY_MULTIPLIERS.get(vol_upper, 1.0)
        regime_mult = REGIME_MULTIPLIERS.get(regime_upper, 1.0)
        
        # Concentration adjustment (higher concentration = higher VaR)
        concentration_mult = 1.0 + (position_concentration * 0.3)
        
        # Calculate VaR 95
        portfolio_var_95 = (
            gross_exposure *
            vol_mult *
            regime_mult *
            concentration_mult *
            self._base_var_coefficient
        )
        
        # Calculate VaR 99
        portfolio_var_99 = portfolio_var_95 * self._var_99_multiplier
        
        components = {
            "gross_exposure": gross_exposure,
            "volatility_multiplier": vol_mult,
            "regime_multiplier": regime_mult,
            "concentration_multiplier": concentration_mult,
            "base_coefficient": self._base_var_coefficient,
        }
        
        return {
            "portfolio_var_95": portfolio_var_95,
            "portfolio_var_99": portfolio_var_99,
            "components": components,
        }
    
    def get_var_breakdown(
        self,
        var_result: Dict[str, Any],
    ) -> Dict[str, float]:
        """Get breakdown of VaR components."""
        components = var_result.get("components", {})
        
        return {
            "exposure_contribution": components.get("gross_exposure", 0) * 0.4,
            "volatility_contribution": components.get("volatility_multiplier", 1) * 0.3,
            "regime_contribution": components.get("regime_multiplier", 1) * 0.2,
            "concentration_contribution": components.get("concentration_multiplier", 1) * 0.1,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[PortfolioVaREngine] = None


def get_portfolio_var_engine() -> PortfolioVaREngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PortfolioVaREngine()
    return _engine
