"""
PHASE 21.2 — Dry Powder Engine
==============================
Sub-engine for dry powder management.

Maintains capital for:
- New opportunities
- Squeeze events
- Crashes
- Re-entry after deleveraging
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone


class DryPowderEngine:
    """
    Dry Powder Sub-Engine.
    
    Determines how much capital to keep available for:
    - Opportunistic deployment
    - Crash buying
    - Squeeze events
    - Re-entry opportunities
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_dry_powder = 0.08  # 8% default
    
    def compute_dry_powder(
        self,
        total_capital: float,
        regime: str = "MIXED",
        volatility_state: str = "NORMAL",
        opportunity_score: float = 0.5,
        squeeze_probability: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Compute dry powder allocation.
        
        Rules:
        - squeeze / crash-prone / high opportunity → higher dry powder
        - clean range → lower dry powder
        - high vol expansion → higher dry powder
        
        Returns:
            {
                "dry_powder_ratio": float,
                "dry_powder": float,
                "components": dict,
            }
        """
        regime_upper = regime.upper()
        vol_upper = volatility_state.upper()
        
        # Base dry powder
        dry_powder_ratio = self._base_dry_powder
        
        components = {
            "base": self._base_dry_powder,
            "regime_adjustment": 0.0,
            "volatility_adjustment": 0.0,
            "opportunity_adjustment": 0.0,
            "squeeze_adjustment": 0.0,
        }
        
        # Regime adjustments
        if regime_upper in ["SQUEEZE", "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT"]:
            components["regime_adjustment"] = 0.08
            dry_powder_ratio += 0.08
        elif regime_upper in ["CRASH", "CRISIS"]:
            components["regime_adjustment"] = 0.10
            dry_powder_ratio += 0.10
        elif regime_upper in ["VOL", "VOL_EXPANSION", "HIGH_VOL"]:
            components["regime_adjustment"] = 0.05
            dry_powder_ratio += 0.05
        elif regime_upper in ["RANGE", "RANGE_LOW_VOL"]:
            components["regime_adjustment"] = -0.03
            dry_powder_ratio -= 0.03
        elif regime_upper in ["TREND", "TREND_UP"]:
            components["regime_adjustment"] = -0.02
            dry_powder_ratio -= 0.02
        
        # Volatility adjustments
        if vol_upper in ["HIGH", "EXTREME", "EXPANSION"]:
            components["volatility_adjustment"] = 0.04
            dry_powder_ratio += 0.04
        elif vol_upper in ["LOW", "COMPRESSED"]:
            components["volatility_adjustment"] = 0.02  # Squeeze potential
            dry_powder_ratio += 0.02
        
        # Opportunity score
        if opportunity_score > 0.7:
            components["opportunity_adjustment"] = 0.05
            dry_powder_ratio += 0.05
        elif opportunity_score < 0.3:
            components["opportunity_adjustment"] = -0.02
            dry_powder_ratio -= 0.02
        
        # Squeeze probability
        if squeeze_probability > 0.6:
            components["squeeze_adjustment"] = 0.06
            dry_powder_ratio += 0.06
        elif squeeze_probability > 0.4:
            components["squeeze_adjustment"] = 0.03
            dry_powder_ratio += 0.03
        
        # Clamp to reasonable range
        dry_powder_ratio = max(0.03, min(0.25, dry_powder_ratio))
        
        # Calculate dry powder capital
        dry_powder = total_capital * dry_powder_ratio
        
        return {
            "dry_powder_ratio": dry_powder_ratio,
            "dry_powder": dry_powder,
            "components": components,
        }
    
    def get_min_dry_powder(self) -> float:
        """Get minimum dry powder ratio."""
        return 0.03
    
    def get_max_dry_powder(self) -> float:
        """Get maximum dry powder ratio."""
        return 0.25


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[DryPowderEngine] = None


def get_dry_powder_engine() -> DryPowderEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DryPowderEngine()
    return _engine
