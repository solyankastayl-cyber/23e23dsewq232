"""
Capital Allocator
=================

Dynamically adjusts size_multiplier based on portfolio state.

Factors:
- Drawdown (primary)
- Heat
- Alpha quality
- Regime
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CapitalAllocator:
    """Dynamic capital allocation engine."""
    
    def calculate_multiplier(
        self,
        drawdown_pct: float,
        heat: float,
        alpha_verdict: str = "NEUTRAL",
        regime: str = "NEUTRAL"
    ) -> Dict[str, Any]:
        """
        Calculate size multiplier based on portfolio state.
        
        Args:
            drawdown_pct: Current drawdown percentage (e.g., -5.0 for -5%)
            heat: Current portfolio heat (0.0 - 1.0)
            alpha_verdict: Alpha Factory verdict
            regime: Market regime
        
        Returns:
            Allocation state with multiplier
        """
        base_multiplier = 1.0
        reason_chain = []
        
        # 1. DRAWDOWN ADJUSTMENT (Primary factor)
        if drawdown_pct >= -2.0:
            dd_multiplier = 1.0
            reason_chain.append("drawdown_healthy")
        elif drawdown_pct >= -5.0:
            dd_multiplier = 1.0
            reason_chain.append("drawdown_normal")
        elif drawdown_pct >= -10.0:
            dd_multiplier = 0.7
            reason_chain.append("drawdown_elevated_reduce_30pct")
            logger.warning(f"[CapitalAllocator] Drawdown {drawdown_pct:.1f}% → reducing size to 70%")
        elif drawdown_pct >= -15.0:
            dd_multiplier = 0.4
            reason_chain.append("drawdown_high_reduce_60pct")
            logger.warning(f"[CapitalAllocator] Drawdown {drawdown_pct:.1f}% → reducing size to 40%")
        else:
            dd_multiplier = 0.2
            reason_chain.append("drawdown_critical_reduce_80pct")
            logger.error(f"[CapitalAllocator] Drawdown {drawdown_pct:.1f}% → reducing size to 20%")
        
        # 2. HEAT ADJUSTMENT
        if heat > 0.4:
            heat_multiplier = 0.5
            reason_chain.append("heat_critical_halve")
            logger.warning(f"[CapitalAllocator] Heat {heat:.2f} > 0.4 → halving size")
        elif heat > 0.35:
            heat_multiplier = 0.8
            reason_chain.append("heat_high_reduce_20pct")
        else:
            heat_multiplier = 1.0
        
        # 3. ALPHA ADJUSTMENT
        if alpha_verdict == "STRONG_CONFIRMED_EDGE":
            alpha_multiplier = 1.2
            reason_chain.append("alpha_strong_boost_20pct")
        elif alpha_verdict == "CONFIRMED_EDGE":
            alpha_multiplier = 1.1
            reason_chain.append("alpha_confirmed_boost_10pct")
        elif alpha_verdict in ["WEAK", "BROKEN"]:
            alpha_multiplier = 0.6
            reason_chain.append("alpha_weak_reduce_40pct")
        else:
            alpha_multiplier = 1.0
        
        # 4. REGIME ADJUSTMENT
        if regime == "TRENDING":
            regime_multiplier = 1.1
            reason_chain.append("regime_trending_boost_10pct")
        elif regime == "CHOPPY":
            regime_multiplier = 0.8
            reason_chain.append("regime_choppy_reduce_20pct")
        else:
            regime_multiplier = 1.0
        
        # 5. COMBINE MULTIPLIERS
        final_multiplier = base_multiplier * dd_multiplier * heat_multiplier * alpha_multiplier * regime_multiplier
        
        # Cap at reasonable bounds
        final_multiplier = max(0.1, min(1.5, final_multiplier))
        
        return {
            "multiplier": round(final_multiplier, 2),
            "base": base_multiplier,
            "drawdown_factor": dd_multiplier,
            "heat_factor": heat_multiplier,
            "alpha_factor": alpha_multiplier,
            "regime_factor": regime_multiplier,
            "reason_chain": reason_chain,
        }


# Singleton instance
_allocator: CapitalAllocator = None


def get_capital_allocator() -> CapitalAllocator:
    """Get or create singleton capital allocator."""
    global _allocator
    if _allocator is None:
        _allocator = CapitalAllocator()
    return _allocator
