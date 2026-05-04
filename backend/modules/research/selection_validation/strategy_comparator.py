"""
Strategy Comparator
===================

Compares all strategies in parallel for validation (PHASE 2.4)
"""

import time
import random
from typing import Dict, List, Optional, Any

from .selection_types import StrategyResult, SelectionComparison


class StrategyComparator:
    """
    Runs all strategies in parallel and compares results.
    
    For each market condition:
    1. Generates signal for each strategy
    2. Simulates trade outcome for each
    3. Determines which was best
    """
    
    def __init__(self):
        # Strategy characteristics (from Trading Doctrine)
        self._strategy_configs = {
            "TREND_CONFIRMATION": {
                "ideal_regimes": ["TRENDING"],
                "acceptable_regimes": ["TRANSITION"],
                "avoid_regimes": ["RANGE", "HIGH_VOLATILITY"],
                "base_win_rate": 0.52,
                "base_r_target": 2.0,
                "signal_rate": 0.08
            },
            "MOMENTUM_BREAKOUT": {
                "ideal_regimes": ["TRENDING", "HIGH_VOLATILITY"],
                "acceptable_regimes": ["TRANSITION"],
                "avoid_regimes": ["RANGE", "LOW_VOLATILITY"],
                "base_win_rate": 0.45,
                "base_r_target": 3.0,
                "signal_rate": 0.12
            },
            "MEAN_REVERSION": {
                "ideal_regimes": ["RANGE", "LOW_VOLATILITY"],
                "acceptable_regimes": ["TRANSITION"],
                "avoid_regimes": ["TRENDING", "HIGH_VOLATILITY"],
                "base_win_rate": 0.58,
                "base_r_target": 1.5,
                "signal_rate": 0.15
            }
        }
        
        # Regime rankings for strategy selection
        self._regime_rankings = {
            "TRENDING": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"],
            "RANGE": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "HIGH_VOLATILITY": ["MOMENTUM_BREAKOUT", "TREND_CONFIRMATION", "MEAN_REVERSION"],
            "LOW_VOLATILITY": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "TRANSITION": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
        }
        
        print("[StrategyComparator] Initialized (PHASE 2.4)")
    
    def compare_strategies(
        self,
        bar_index: int,
        regime: str,
        indicators: Dict[str, float],
        selected_strategy: str,
        strategies: List[str]
    ) -> SelectionComparison:
        """
        Compare all strategies for a given market condition.
        """
        
        comparison = SelectionComparison(
            bar_index=bar_index,
            timestamp=int(time.time() * 1000),
            regime=regime,
            selected_strategy=selected_strategy
        )
        
        results = []
        
        for strategy in strategies:
            result = self._simulate_strategy(
                strategy=strategy,
                regime=regime,
                indicators=indicators,
                is_selected=(strategy == selected_strategy)
            )
            results.append(result)
        
        comparison.all_results = results
        
        # Find best strategy
        strategies_with_trades = [r for r in results if r.trade_taken]
        
        if strategies_with_trades:
            best = max(strategies_with_trades, key=lambda x: x.r_multiple)
            comparison.best_strategy = best.strategy
            comparison.best_result = best.pnl
            comparison.best_r = best.r_multiple
        else:
            # No trades taken - use ranking
            rankings = self._regime_rankings.get(regime, strategies)
            for strat in rankings:
                if strat in strategies:
                    comparison.best_strategy = strat
                    break
            comparison.best_result = 0.0
            comparison.best_r = 0.0
        
        # Get selected result
        selected_result = next((r for r in results if r.was_selected), None)
        if selected_result:
            comparison.selected_result = selected_result.pnl
            comparison.selected_r = selected_result.r_multiple
        
        # Calculate if correct
        comparison.is_correct = (selected_strategy == comparison.best_strategy)
        
        # Calculate performance gap
        comparison.performance_gap = comparison.best_result - comparison.selected_result
        if comparison.selected_result != 0:
            comparison.performance_gap_pct = comparison.performance_gap / abs(comparison.selected_result)
        else:
            comparison.performance_gap_pct = 0.0 if comparison.performance_gap == 0 else 1.0
        
        return comparison
    
    def _simulate_strategy(
        self,
        strategy: str,
        regime: str,
        indicators: Dict[str, float],
        is_selected: bool
    ) -> StrategyResult:
        """
        Simulate a strategy's performance.
        """
        
        result = StrategyResult(
            strategy=strategy,
            was_selected=is_selected
        )
        
        config = self._strategy_configs.get(strategy)
        if not config:
            return result
        
        # Determine if signal would be generated
        signal_rate = config["signal_rate"]
        
        # Adjust by regime
        if regime in config["ideal_regimes"]:
            signal_rate *= 1.3
        elif regime in config["avoid_regimes"]:
            signal_rate *= 0.5
        
        result.signal_generated = random.random() < signal_rate
        
        if not result.signal_generated:
            return result
        
        # Trade taken
        result.trade_taken = True
        
        # Calculate expected outcome
        base_wr = config["base_win_rate"]
        base_r = config["base_r_target"]
        
        # Adjust by regime
        if regime in config["ideal_regimes"]:
            wr_modifier = 0.10
            r_modifier = 0.5
        elif regime in config["acceptable_regimes"]:
            wr_modifier = 0.0
            r_modifier = 0.0
        else:  # avoid regime
            wr_modifier = -0.15
            r_modifier = -0.5
        
        effective_wr = max(0.30, min(0.75, base_wr + wr_modifier))
        effective_r = max(1.0, base_r + r_modifier)
        
        # Simulate outcome
        is_winner = random.random() < effective_wr
        
        if is_winner:
            result.r_multiple = random.uniform(0.5 * effective_r, 1.5 * effective_r)
        else:
            result.r_multiple = random.uniform(-1.5, -0.5)
        
        # Calculate P&L (assuming $100 risk)
        result.pnl = result.r_multiple * 100
        
        return result
    
    def get_optimal_strategy(self, regime: str, strategies: List[str]) -> str:
        """Get optimal strategy for regime"""
        rankings = self._regime_rankings.get(regime, strategies)
        
        for strat in rankings:
            if strat in strategies:
                return strat
        
        return strategies[0] if strategies else "TREND_CONFIRMATION"
    
    def get_regime_rankings(self) -> Dict[str, List[str]]:
        """Get all regime rankings"""
        return self._regime_rankings.copy()


# Global singleton
strategy_comparator = StrategyComparator()
