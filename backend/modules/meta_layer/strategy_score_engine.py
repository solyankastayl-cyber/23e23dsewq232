"""
Strategy Score Engine
=====================

Evaluates strategy quality based on:
- Performance metrics (profit factor, win rate)
- Regime fit
- Portfolio contribution
- Recent outcomes
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StrategyScoreEngine:
    """Strategy scoring and evaluation engine."""
    
    def compute_score(
        self,
        strategy_state: Dict[str, Any],
        metrics: Dict[str, Any],
        regime: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute strategy score.
        
        Args:
            strategy_state: Strategy configuration from registry
            metrics: Performance metrics for this strategy
            regime: Current market regime
        
        Returns:
            Score result with score and reasons
        """
        base_score = 1.0
        score = base_score
        reasons = []
        
        strategy_id = strategy_state.get("strategy_id", "unknown")
        
        # 1. PROFIT FACTOR SCORING
        pf = metrics.get("profit_factor")
        if pf is not None:
            if pf > 1.8:
                score *= 1.3
                reasons.append("strong_pf")
                logger.info(f"[StrategyScore] {strategy_id}: Strong PF {pf:.2f}")
            elif pf > 1.2:
                score *= 1.1
                reasons.append("good_pf")
            elif pf < 0.9:
                score *= 0.5
                reasons.append("weak_pf")
                logger.warning(f"[StrategyScore] {strategy_id}: Weak PF {pf:.2f}")
            elif pf < 1.0:
                score *= 0.7
                reasons.append("poor_pf")
        
        # 2. WIN RATE SCORING
        win_rate = metrics.get("win_rate", 0.0)
        if win_rate > 0.58:
            score *= 1.15
            reasons.append("good_wr")
        elif win_rate < 0.45:
            score *= 0.8
            reasons.append("low_wr")
        
        # 3. EXPECTANCY SCORING
        expectancy = metrics.get("expectancy")
        if expectancy is not None:
            if expectancy > 50:
                score *= 1.2
                reasons.append("positive_expectancy")
            elif expectancy < 0:
                score *= 0.6
                reasons.append("negative_expectancy")
        
        # 4. DRAWDOWN CONTRIBUTION
        dd_contribution = metrics.get("drawdown_contribution", 0.0)
        if dd_contribution < -0.08:
            score *= 0.6
            reasons.append("high_dd_contribution")
            logger.warning(f"[StrategyScore] {strategy_id}: High DD contribution {dd_contribution:.2%}")
        elif dd_contribution < -0.05:
            score *= 0.8
            reasons.append("moderate_dd_contribution")
        
        # 5. REGIME FIT
        current_regime = regime.get("current", "NEUTRAL")
        preferred_regimes = strategy_state.get("preferred_regimes", [])
        
        if preferred_regimes and current_regime in preferred_regimes:
            score *= 1.2
            reasons.append("regime_fit")
            logger.info(f"[StrategyScore] {strategy_id}: Regime fit ({current_regime})")
        elif preferred_regimes and current_regime not in preferred_regimes:
            score *= 0.85
            reasons.append("regime_mismatch")
        
        # 6. RECENT PERFORMANCE (if available)
        recent_pf = metrics.get("recent_profit_factor")
        if recent_pf is not None:
            if recent_pf > 2.0:
                score *= 1.15
                reasons.append("hot_streak")
            elif recent_pf < 0.8:
                score *= 0.7
                reasons.append("cold_streak")
        
        # 7. SAMPLE SIZE CHECK
        trades_count = metrics.get("trades", 0)
        if trades_count < 10:
            score *= 0.9
            reasons.append("low_sample_size")
        elif trades_count > 50:
            score *= 1.05
            reasons.append("sufficient_sample")
        
        return {
            "strategy_id": strategy_id,
            "score": round(score, 4),
            "base_score": base_score,
            "reasons": reasons,
            "metrics": {
                "profit_factor": pf,
                "win_rate": win_rate,
                "expectancy": expectancy,
                "trades": trades_count,
            },
        }
    
    def compute_all(
        self,
        strategies: List[Dict[str, Any]],
        strategy_metrics: Dict[str, Dict[str, Any]],
        regime: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compute scores for all strategies.
        
        Args:
            strategies: List of strategy configs
            strategy_metrics: Dict of {strategy_id: metrics}
            regime: Current market regime
        
        Returns:
            List of score results
        """
        scores = []
        
        for strategy_state in strategies:
            strategy_id = strategy_state.get("strategy_id")
            
            # Get metrics for this strategy
            metrics = strategy_metrics.get(strategy_id, {})
            
            # Compute score
            score_result = self.compute_score(strategy_state, metrics, regime)
            scores.append(score_result)
        
        # Sort by score (descending)
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        return scores


# Singleton instance
_engine: StrategyScoreEngine = None


def get_strategy_score_engine() -> StrategyScoreEngine:
    """Get or create singleton strategy score engine."""
    global _engine
    if _engine is None:
        _engine = StrategyScoreEngine()
    return _engine
