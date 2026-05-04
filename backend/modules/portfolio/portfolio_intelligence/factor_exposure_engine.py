"""
PHASE 18.1 — Factor Exposure Engine
====================================
Factor concentration analysis.

Calculates aggregated load on factors across the portfolio.

Example output:
{
  "trend": 0.62,
  "momentum": 0.48,
  "reversal": 0.14,
  "liquidation": 0.27
}
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    Position,
    FACTOR_CONCENTRATION_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# FACTOR CLASSIFICATION
# ══════════════════════════════════════════════════════════════

# Known factor categories
FACTOR_CATEGORIES = {
    # Trend factors
    "trend_breakout_factor": "trend",
    "trend_continuation_factor": "trend",
    "trend_exhaustion_factor": "trend",
    "structure_break_factor": "trend",
    
    # Momentum factors
    "momentum_factor": "momentum",
    "momentum_acceleration_factor": "momentum",
    "relative_strength_factor": "momentum",
    
    # Reversal factors
    "mean_reversion_factor": "reversal",
    "divergence_factor": "reversal",
    "oversold_factor": "reversal",
    "overbought_factor": "reversal",
    
    # Flow/Liquidation factors
    "flow_imbalance_factor": "flow",
    "liquidation_cascade_factor": "liquidation",
    "funding_arb_factor": "flow",
    
    # Volatility factors
    "volatility_regime_factor": "volatility",
    "volatility_breakout_factor": "volatility",
    
    # Dominance factors
    "dominance_shift_factor": "dominance",
    "alt_rotation_factor": "dominance",
}


def categorize_factor(factor_name: str) -> str:
    """Categorize a factor into a factor type."""
    if not factor_name:
        return "unknown"
    
    factor_lower = factor_name.lower()
    
    # Direct lookup
    if factor_lower in FACTOR_CATEGORIES:
        return FACTOR_CATEGORIES[factor_lower]
    
    # Pattern matching
    if "trend" in factor_lower or "breakout" in factor_lower:
        return "trend"
    elif "momentum" in factor_lower or "strength" in factor_lower:
        return "momentum"
    elif "reversion" in factor_lower or "divergence" in factor_lower:
        return "reversal"
    elif "flow" in factor_lower or "funding" in factor_lower:
        return "flow"
    elif "liquidation" in factor_lower:
        return "liquidation"
    elif "volatility" in factor_lower:
        return "volatility"
    elif "dominance" in factor_lower:
        return "dominance"
    else:
        return "unknown"


# ══════════════════════════════════════════════════════════════
# FACTOR EXPOSURE ENGINE
# ══════════════════════════════════════════════════════════════

class FactorExposureEngine:
    """
    Factor Exposure Engine - PHASE 18.1 STEP 5
    
    Calculates aggregated factor load across the portfolio.
    
    Uses position size weighted by confidence to determine
    factor exposure.
    """
    
    def calculate_factor_exposure(self, positions: List[Position]) -> Dict[str, float]:
        """
        Calculate factor exposure across portfolio.
        
        Args:
            positions: List of portfolio positions
        
        Returns:
            Dict mapping factor category to exposure (0-1)
        """
        factor_weights = defaultdict(float)
        total_weight = 0.0
        
        for pos in positions:
            weight = pos.position_size * pos.final_confidence
            total_weight += weight
            
            # Add primary factor contribution
            if pos.primary_factor:
                category = categorize_factor(pos.primary_factor)
                factor_weights[category] += weight * 0.7  # Primary factor gets 70%
            
            # Add secondary factor contribution
            if pos.secondary_factor:
                category = categorize_factor(pos.secondary_factor)
                factor_weights[category] += weight * 0.3  # Secondary factor gets 30%
        
        # Normalize to 0-1
        if total_weight > 0:
            factor_exposure = {
                k: min(v / total_weight, 1.0)
                for k, v in factor_weights.items()
            }
        else:
            factor_exposure = {}
        
        return factor_exposure
    
    def get_factor_breakdown(self, positions: List[Position]) -> Dict[str, Dict]:
        """
        Get detailed factor breakdown.
        
        Returns:
            Dict with factor breakdown including positions per factor
        """
        breakdown = defaultdict(lambda: {
            "exposure": 0.0,
            "positions": [],
            "count": 0,
            "avg_confidence": 0.0,
        })
        
        total_weight = sum(p.position_size * p.final_confidence for p in positions)
        
        for pos in positions:
            weight = pos.position_size * pos.final_confidence
            
            # Process primary factor
            if pos.primary_factor:
                category = categorize_factor(pos.primary_factor)
                breakdown[category]["positions"].append({
                    "symbol": pos.symbol,
                    "factor": pos.primary_factor,
                    "weight": weight * 0.7,
                    "is_primary": True,
                })
                breakdown[category]["count"] += 1
            
            # Process secondary factor
            if pos.secondary_factor:
                category = categorize_factor(pos.secondary_factor)
                breakdown[category]["positions"].append({
                    "symbol": pos.symbol,
                    "factor": pos.secondary_factor,
                    "weight": weight * 0.3,
                    "is_primary": False,
                })
        
        # Calculate exposure and avg confidence
        for category in breakdown:
            total_cat_weight = sum(p["weight"] for p in breakdown[category]["positions"])
            if total_weight > 0:
                breakdown[category]["exposure"] = min(total_cat_weight / total_weight, 1.0)
            
            positions_with_factor = [
                pos for pos in positions 
                if categorize_factor(pos.primary_factor) == category
                or categorize_factor(pos.secondary_factor) == category
            ]
            if positions_with_factor:
                breakdown[category]["avg_confidence"] = sum(
                    p.final_confidence for p in positions_with_factor
                ) / len(positions_with_factor)
        
        return dict(breakdown)
    
    def detect_factor_overload(
        self, 
        factor_exposure: Dict[str, float],
        threshold: float = FACTOR_CONCENTRATION_THRESHOLD
    ) -> Dict:
        """
        Detect if any factor is overloaded.
        
        Args:
            factor_exposure: Factor exposure dict
            threshold: Concentration threshold
        
        Returns:
            Dict with overload detection results
        """
        overloaded_factors = []
        max_factor = None
        max_exposure = 0.0
        
        for factor, exposure in factor_exposure.items():
            if exposure > threshold:
                overloaded_factors.append({
                    "factor": factor,
                    "exposure": exposure,
                    "threshold": threshold,
                })
            if exposure > max_exposure:
                max_factor = factor
                max_exposure = exposure
        
        return {
            "is_overloaded": len(overloaded_factors) > 0,
            "overloaded_factors": overloaded_factors,
            "max_factor": max_factor,
            "max_exposure": max_exposure,
            "threshold": threshold,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FactorExposureEngine] = None


def get_factor_exposure_engine() -> FactorExposureEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorExposureEngine()
    return _engine
