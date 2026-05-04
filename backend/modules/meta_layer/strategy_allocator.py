"""
Strategy Allocator
==================

Distributes capital across strategies based on scores.

Uses weighted allocation:
- Higher score → higher capital allocation
- Zero score → zero capital
- Normalizes weights to sum to 1.0
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StrategyAllocator:
    """Strategy capital allocation engine."""
    
    def allocate(
        self,
        scores: List[Dict[str, Any]],
        total_capital: float
    ) -> List[Dict[str, Any]]:
        """
        Allocate capital across strategies based on scores.
        
        Args:
            scores: List of strategy scores from StrategyScoreEngine
            total_capital: Total capital available for allocation
        
        Returns:
            List of allocations with strategy_id, weight, capital
        """
        # Filter enabled strategies (score > 0)
        enabled = [s for s in scores if s["score"] > 0]
        
        if not enabled:
            logger.warning("[StrategyAllocator] No enabled strategies (all scores <= 0)")
            return []
        
        # Calculate total score
        total_score = sum(s["score"] for s in enabled)
        
        if total_score <= 0:
            logger.warning("[StrategyAllocator] Total score <= 0, equal allocation")
            # Fallback to equal allocation
            total_score = len(enabled)
            for s in enabled:
                s["score"] = 1.0
        
        allocations = []
        
        for s in enabled:
            weight = s["score"] / total_score
            capital = total_capital * weight
            
            allocation = {
                "strategy_id": s["strategy_id"],
                "weight": round(weight, 4),
                "capital": round(capital, 2),
                "score": s["score"],
                "reasons": s.get("reasons", []),
                "metrics": s.get("metrics", {}),
            }
            
            allocations.append(allocation)
            
            logger.info(
                f"[StrategyAllocator] {allocation['strategy_id']}: "
                f"weight={weight:.2%}, capital=${capital:,.2f}"
            )
        
        # Sort by capital (descending)
        allocations.sort(key=lambda x: x["capital"], reverse=True)
        
        return allocations


# Singleton instance
_allocator: StrategyAllocator = None


def get_strategy_allocator() -> StrategyAllocator:
    """Get or create singleton strategy allocator."""
    global _allocator
    if _allocator is None:
        _allocator = StrategyAllocator()
    return _allocator
