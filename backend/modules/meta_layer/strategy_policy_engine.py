"""
Strategy Policy Engine
======================

Generates meta-level policy actions based on strategy allocations.

Actions:
- BOOST_STRATEGY: Increase strategy's allocation multiplier
- CAP_STRATEGY: Limit strategy's maximum allocation
- DISABLE_STRATEGY: Temporarily disable strategy
- RESTRICT_SYMBOLS: Limit symbols for strategy
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StrategyPolicyEngine:
    """Strategy-level policy decision engine."""
    
    def generate_actions(
        self,
        allocations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate policy actions based on allocations.
        
        Args:
            allocations: List of strategy allocations
        
        Returns:
            List of policy actions
        """
        actions = []
        
        for alloc in allocations:
            strategy_id = alloc["strategy_id"]
            weight = alloc["weight"]
            score = alloc["score"]
            capital = alloc["capital"]
            
            # 1. LOW ALLOCATION CAP
            if weight < 0.1:
                actions.append({
                    "type": "CAP_STRATEGY",
                    "strategy_id": strategy_id,
                    "reason": "low_meta_weight",
                    "weight": weight,
                    "priority": "MEDIUM",
                })
                logger.info(f"[StrategyPolicy] CAP {strategy_id}: weight={weight:.2%}")
            
            # 2. HIGH ALLOCATION BOOST
            if weight > 0.45:
                actions.append({
                    "type": "BOOST_STRATEGY",
                    "strategy_id": strategy_id,
                    "reason": "high_meta_weight",
                    "weight": weight,
                    "priority": "LOW",
                })
                logger.info(f"[StrategyPolicy] BOOST {strategy_id}: weight={weight:.2%}")
            
            # 3. VERY LOW SCORE DISABLE
            if score < 0.5:
                actions.append({
                    "type": "DISABLE_STRATEGY",
                    "strategy_id": strategy_id,
                    "reason": "very_low_score",
                    "score": score,
                    "priority": "HIGH",
                })
                logger.warning(f"[StrategyPolicy] DISABLE {strategy_id}: score={score:.2f}")
            
            # 4. DOMINANT STRATEGY WARNING
            if weight > 0.65:
                actions.append({
                    "type": "DIVERSIFY_WARNING",
                    "strategy_id": strategy_id,
                    "reason": "over_concentration",
                    "weight": weight,
                    "priority": "MEDIUM",
                })
                logger.warning(f"[StrategyPolicy] DIVERSIFY WARNING {strategy_id}: weight={weight:.2%}")
            
            # 5. NEGATIVE METRICS
            metrics = alloc.get("metrics", {})
            pf = metrics.get("profit_factor")
            
            if pf is not None and pf < 0.8:
                actions.append({
                    "type": "REDUCE_STRATEGY",
                    "strategy_id": strategy_id,
                    "reason": "negative_metrics",
                    "profit_factor": pf,
                    "priority": "HIGH",
                })
                logger.warning(f"[StrategyPolicy] REDUCE {strategy_id}: PF={pf:.2f}")
        
        # Sort by priority (HIGH > MEDIUM > LOW)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        actions.sort(key=lambda a: priority_order.get(a.get("priority", "LOW"), 2))
        
        return actions


# Singleton instance
_engine: StrategyPolicyEngine = None


def get_strategy_policy_engine() -> StrategyPolicyEngine:
    """Get or create singleton strategy policy engine."""
    global _engine
    if _engine is None:
        _engine = StrategyPolicyEngine()
    return _engine
