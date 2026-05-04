"""
PHASE 22.2 — Crash Sensitivity Engine
=====================================
Sub-engine for estimating crash sensitivity.

Measures how sensitive the portfolio is to sudden market shocks.
"""

from typing import Dict, Optional, Any

from modules.institutional_risk.tail_risk.tail_risk_types import (
    CRASH_VOLATILITY_MULTIPLIERS,
    CRASH_CONCENTRATION_MULTIPLIERS,
)


class CrashSensitivityEngine:
    """
    Crash Sensitivity Sub-Engine.
    
    Calculates crash_sensitivity based on:
    - Gross exposure
    - Volatility state
    - Position concentration
    """

    def compute_crash_sensitivity(
        self,
        gross_exposure: float = 0.5,
        volatility_state: str = "NORMAL",
        concentration_score: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Compute crash sensitivity.
        
        Formula:
        crash_sensitivity = gross_exposure × vol_mult × conc_mult
        
        Capped at 1.0 for normalization.
        
        Returns:
            {
                "crash_sensitivity": float,
                "components": dict,
            }
        """
        vol_upper = volatility_state.upper()
        vol_mult = CRASH_VOLATILITY_MULTIPLIERS.get(vol_upper, 1.0)

        # Map concentration score to category
        conc_category = self._classify_concentration(concentration_score)
        conc_mult = CRASH_CONCENTRATION_MULTIPLIERS.get(conc_category, 1.0)

        # Raw crash sensitivity
        raw_sensitivity = gross_exposure * vol_mult * conc_mult

        # Normalize to 0..1
        crash_sensitivity = min(raw_sensitivity, 1.0)

        components = {
            "gross_exposure": gross_exposure,
            "volatility_multiplier": vol_mult,
            "concentration_multiplier": conc_mult,
            "concentration_category": conc_category,
            "raw_sensitivity": raw_sensitivity,
        }

        return {
            "crash_sensitivity": crash_sensitivity,
            "components": components,
        }

    def _classify_concentration(self, concentration_score: float) -> str:
        """Classify concentration level."""
        if concentration_score < 0.25:
            return "LOW"
        elif concentration_score < 0.45:
            return "MEDIUM"
        elif concentration_score < 0.65:
            return "HIGH"
        else:
            return "VERY_HIGH"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[CrashSensitivityEngine] = None


def get_crash_sensitivity_engine() -> CrashSensitivityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = CrashSensitivityEngine()
    return _engine
