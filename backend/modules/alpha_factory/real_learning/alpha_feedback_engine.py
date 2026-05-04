"""
Alpha Feedback Engine - AF6

Generates adaptive actions based on learning metrics.
Core intelligence: disable/reduce/upgrade modes based on real performance.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class AlphaFeedbackEngine:
    """
    Adaptive action generator.
    
    Converts learning metrics into concrete actions:
    - DISABLE_ENTRY_MODE: Low profit factor
    - REDUCE_ENTRY_MODE: High wrong_early rate
    - UPGRADE_ENTRY_MODE: Strong performance
    - REDUCE_ACTIVITY_IN_REGIME: Regime underperforming
    - DISABLE_SYMBOL: Symbol consistently losing
    """
    
    def generate_actions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate adaptive actions from metrics.
        
        Args:
            metrics: Metrics dict from LearningMetricsEngine
            
        Returns:
            List of action dicts
        """
        actions: List[Dict[str, Any]] = []
        
        # Entry mode learning
        for mode, m in metrics.get("by_entry_mode", {}).items():
            mode_actions = self._evaluate_entry_mode(mode, m)
            actions.extend(mode_actions)
        
        # Regime learning
        for regime, m in metrics.get("by_regime", {}).items():
            regime_actions = self._evaluate_regime(regime, m)
            actions.extend(regime_actions)
        
        # Symbol learning
        for symbol, m in metrics.get("by_symbol", {}).items():
            symbol_actions = self._evaluate_symbol(symbol, m)
            actions.extend(symbol_actions)
        
        # ORCH-7 PHASE 5: Strategy learning
        for strategy_id, m in metrics.get("by_strategy", {}).items():
            strategy_actions = self._evaluate_strategy(strategy_id, m)
            actions.extend(strategy_actions)
        
        logger.info(f"[AlphaFeedbackEngine] Generated {len(actions)} adaptive actions")
        
        return actions
    
    def _evaluate_entry_mode(self, mode: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate entry mode performance and generate actions."""
        actions = []
        
        count = metrics.get("count", 0)
        win_rate = metrics.get("win_rate", 0.0)
        pf = metrics.get("profit_factor")
        wrong_early = metrics.get("wrong_early_rate", 0.0)
        
        # Need minimum sample size
        if count < 5:
            return actions
        
        # Disable if profit factor too low
        if pf is not None and pf < 0.9:
            actions.append({
                "type": "DISABLE_ENTRY_MODE",
                "entry_mode": mode,
                "reason": "low_profit_factor",
                "metrics": {"pf": pf, "count": count},
            })
            logger.warning(
                f"[AlphaFeedbackEngine] DISABLE {mode}: PF={pf:.2f} < 0.9 (n={count})"
            )
        
        # Reduce if high wrong_early rate
        elif wrong_early > 0.35:
            actions.append({
                "type": "REDUCE_ENTRY_MODE",
                "entry_mode": mode,
                "reason": "high_wrong_early",
                "metrics": {"wrong_early": wrong_early, "count": count},
            })
            logger.info(
                f"[AlphaFeedbackEngine] REDUCE {mode}: wrong_early={wrong_early:.2%} > 35% (n={count})"
            )
        
        # Upgrade if strong performance
        elif pf is not None and pf > 1.8 and win_rate > 0.58:
            actions.append({
                "type": "UPGRADE_ENTRY_MODE",
                "entry_mode": mode,
                "reason": "strong_real_performance",
                "metrics": {"pf": pf, "win_rate": win_rate, "count": count},
            })
            logger.info(
                f"[AlphaFeedbackEngine] UPGRADE {mode}: PF={pf:.2f}, WR={win_rate:.2%} (n={count})"
            )
        
        return actions
    
    def _evaluate_regime(self, regime: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate regime performance and generate actions."""
        actions = []
        
        count = metrics.get("count", 0)
        pf = metrics.get("profit_factor")
        
        if count < 5:
            return actions
        
        # Reduce activity in underperforming regimes
        if pf is not None and pf < 0.9:
            actions.append({
                "type": "REDUCE_ACTIVITY_IN_REGIME",
                "regime": regime,
                "reason": "regime_underperforming",
                "metrics": {"pf": pf, "count": count},
            })
            logger.warning(
                f"[AlphaFeedbackEngine] REDUCE activity in {regime}: PF={pf:.2f} < 0.9 (n={count})"
            )
        
        return actions
    
    def _evaluate_symbol(self, symbol: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate symbol performance and generate actions."""
        actions = []
        
        count = metrics.get("count", 0)
        pf = metrics.get("profit_factor")
        
        if count < 5:
            return actions
        
        # Disable consistently losing symbols
        if pf is not None and pf < 0.8:
            actions.append({
                "type": "DISABLE_SYMBOL",
                "symbol": symbol,
                "reason": "symbol_underperforming",
                "metrics": {"pf": pf, "count": count},
            })
            logger.warning(
                f"[AlphaFeedbackEngine] DISABLE {symbol}: PF={pf:.2f} < 0.8 (n={count})"
            )
        
        return actions


    def _evaluate_strategy(self, strategy_id: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate strategy performance and generate meta-level actions.
        
        ORCH-7 PHASE 5: Strategy-level learning feedback.
        
        Actions:
        - DISABLE_STRATEGY: PF < 0.8 (poor performance)
        - CAP_STRATEGY: PF < 1.0 (weak performance)
        - BOOST_STRATEGY: PF > 1.8 + WR > 0.58 (strong performance)
        - REDUCE_STRATEGY: wrong_early_rate > 0.35 (bad timing)
        """
        actions = []
        
        count = metrics.get("count", 0)
        pf = metrics.get("profit_factor")
        win_rate = metrics.get("win_rate", 0.0)
        wrong_early = metrics.get("wrong_early_rate", 0.0)
        expectancy = metrics.get("expectancy")
        
        # Need minimum sample size for strategy-level decisions
        if count < 10:
            return actions
        
        # 1. DISABLE: Poor profit factor
        if pf is not None and pf < 0.8:
            actions.append({
                "type": "DISABLE_STRATEGY",
                "strategy_id": strategy_id,
                "reason": "low_pf",
                "metrics": {"pf": pf, "count": count, "win_rate": win_rate},
                "ttl": 7200,  # 2 hours cooldown
                "confidence": 0.9,
            })
            logger.warning(
                f"[AlphaFeedbackEngine] DISABLE_STRATEGY {strategy_id}: PF={pf:.2f} < 0.8 (n={count})"
            )
        
        # 2. CAP: Weak performance (only if not already disabled)
        elif pf is not None and pf < 1.0:
            actions.append({
                "type": "CAP_STRATEGY",
                "strategy_id": strategy_id,
                "reason": "weak_performance",
                "metrics": {"pf": pf, "count": count},
                "ttl": 3600,  # 1 hour cooldown
                "confidence": 0.7,
            })
            logger.info(
                f"[AlphaFeedbackEngine] CAP_STRATEGY {strategy_id}: PF={pf:.2f} < 1.0 (n={count})"
            )
        
        # 3. BOOST: Strong performance
        if pf is not None and pf > 1.8 and win_rate > 0.58:
            actions.append({
                "type": "BOOST_STRATEGY",
                "strategy_id": strategy_id,
                "reason": "strong_performance",
                "metrics": {"pf": pf, "win_rate": win_rate, "count": count},
                "ttl": 3600,  # 1 hour
                "confidence": 0.8,
            })
            logger.info(
                f"[AlphaFeedbackEngine] BOOST_STRATEGY {strategy_id}: PF={pf:.2f}, WR={win_rate:.2%} (n={count})"
            )
        
        # 4. REDUCE: Bad timing (high wrong_early rate)
        if wrong_early > 0.35:
            actions.append({
                "type": "REDUCE_STRATEGY",
                "strategy_id": strategy_id,
                "reason": "bad_timing",
                "metrics": {"wrong_early_rate": wrong_early, "count": count},
                "ttl": 1800,  # 30 minutes
                "confidence": 0.6,
            })
            logger.info(
                f"[AlphaFeedbackEngine] REDUCE_STRATEGY {strategy_id}: wrong_early={wrong_early:.2%} (n={count})"
            )
        
        return actions
