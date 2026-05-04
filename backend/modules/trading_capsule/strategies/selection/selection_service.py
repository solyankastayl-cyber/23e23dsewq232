"""
Strategy Selection Service (STG5)
=================================

Main service for Strategy Comparison and Selection.

Answers: "Which strategy is best right now?"
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .selection_types import (
    StrategySelectionScore,
    StrategyRankingEntry,
    StrategySelectionResult,
    StrategyComparisonEntry,
    SelectionConfig,
    ScoreBreakdown,
    Penalties
)

from ..strategy_registry import strategy_registry
from ..strategy_types import StrategyDefinition, MarketRegime, ProfileType
from ..statistics.statistics_service import statistics_service
from ..diagnostics.behavior_service import behavior_diagnostics_service


class SelectionService:
    """
    Strategy Selection Service.
    
    Compares strategies and selects the best one based on:
    - Performance (win rate, PF, expectancy)
    - Stability (drawdown, streaks)
    - Regime fit
    - Profile fit
    - Diagnostics (block rate, veto rate)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config = SelectionConfig()
        
        # Cache
        self._last_selection: Optional[StrategySelectionResult] = None
        self._selection_history: List[StrategySelectionResult] = []
        self._max_history = 100
        
        self._initialized = True
        print("[SelectionService] Initialized (STG5)")
    
    # ===========================================
    # Score Calculation
    # ===========================================
    
    def calculate_score(
        self,
        strategy: StrategyDefinition,
        current_regime: Optional[str] = None,
        current_profile: Optional[str] = None
    ) -> StrategySelectionScore:
        """Calculate complete selection score for a strategy"""
        
        # Get statistics
        stats = statistics_service.get_statistics(strategy.strategy_id)
        decision_stats = statistics_service.get_decision_statistics(strategy.strategy_id)
        
        # Initialize
        breakdown = ScoreBreakdown()
        penalties = Penalties()
        warnings = []
        strengths = []
        weaknesses = []
        
        # ===========================================
        # 1. Performance Score (0-1)
        # ===========================================
        if stats and stats.total_trades > 0:
            # Win rate component (0-1)
            win_rate_score = min(stats.win_rate * 1.5, 1.0)  # 66%+ = 1.0
            
            # Profit factor component (0-1)
            pf_score = min(stats.profit_factor / 3.0, 1.0)  # PF 3+ = 1.0
            
            # Expectancy component (0-1)
            exp_score = min(max(stats.expectancy, 0) / 100, 1.0)  # Normalize
            
            # Recent performance boost/penalty
            recent_boost = 0.0
            if stats.trades_7d >= 3:
                if stats.win_rate_7d > stats.win_rate:
                    recent_boost = 0.1
                    strengths.append("Improving recent performance")
                elif stats.win_rate_7d < stats.win_rate * 0.8:
                    penalties.degradation = self._config.degradation_penalty
                    warnings.append("Recent performance degradation")
                    weaknesses.append("Recent performance below average")
            
            breakdown.performance = (win_rate_score * 0.4 + pf_score * 0.4 + exp_score * 0.2) + recent_boost
            breakdown.performance = min(breakdown.performance, 1.0)
            
            if stats.win_rate > 0.55:
                strengths.append(f"Strong win rate ({stats.win_rate:.1%})")
            if stats.profit_factor > 1.5:
                strengths.append(f"Good profit factor ({stats.profit_factor:.2f})")
        else:
            breakdown.performance = 0.5  # Neutral for strategies without trades
            warnings.append("No trade history")
        
        # ===========================================
        # 2. Stability Score (0-1)
        # ===========================================
        if stats and stats.total_trades > 0:
            # Drawdown component (lower is better)
            dd_score = max(0, 1.0 - stats.max_drawdown * 5)  # 20% dd = 0
            
            # Losing streak component (fewer is better)
            streak_score = max(0, 1.0 - stats.max_losing_streak * 0.15)  # 7+ streak = 0
            
            breakdown.stability = dd_score * 0.6 + streak_score * 0.4
            
            # Penalty for high drawdown
            if stats.max_drawdown > self._config.max_drawdown_threshold:
                penalties.high_drawdown = self._config.drawdown_penalty
                warnings.append(f"High drawdown: {stats.max_drawdown:.1%}")
                weaknesses.append(f"High max drawdown ({stats.max_drawdown:.1%})")
            
            if stats.max_losing_streak >= 5:
                penalties.instability = self._config.instability_penalty
                weaknesses.append(f"Long losing streaks ({stats.max_losing_streak})")
            
            if stats.max_drawdown < 0.08:
                strengths.append("Low drawdown risk")
        else:
            breakdown.stability = 0.5
        
        # ===========================================
        # 3. Regime Fit Score (0-1)
        # ===========================================
        if current_regime:
            try:
                regime_enum = MarketRegime(current_regime.upper())
                
                # Check hostile
                if regime_enum in strategy.hostile_regimes:
                    breakdown.regime_fit = 0.0
                    penalties.wrong_regime = self._config.wrong_regime_penalty
                    warnings.append(f"Hostile regime: {current_regime}")
                    weaknesses.append(f"Not suitable for {current_regime} markets")
                # Check compatible
                elif regime_enum in strategy.compatible_regimes:
                    breakdown.regime_fit = 1.0
                    strengths.append(f"Optimized for {current_regime} markets")
                else:
                    breakdown.regime_fit = 0.5  # Neutral
                
                # Boost if we have historical regime stats
                regime_stats = statistics_service.get_regime_stat(strategy.strategy_id, current_regime)
                if regime_stats and regime_stats.total_trades >= 3:
                    if regime_stats.win_rate > 0.55:
                        breakdown.regime_fit = min(breakdown.regime_fit + 0.2, 1.0)
                        strengths.append(f"Strong {current_regime} track record")
            except ValueError:
                breakdown.regime_fit = 0.5
        else:
            breakdown.regime_fit = 0.7  # No regime specified, slightly positive
        
        # ===========================================
        # 4. Profile Fit Score (0-1)
        # ===========================================
        if current_profile:
            try:
                profile_enum = ProfileType(current_profile.upper())
                
                if strategy.is_compatible_with_profile(profile_enum):
                    breakdown.profile_fit = 1.0
                    
                    # Check profile-specific stats
                    profile_stats = statistics_service.get_profile_stat(strategy.strategy_id, current_profile)
                    if profile_stats and profile_stats.total_trades >= 3:
                        if profile_stats.win_rate > 0.55:
                            strengths.append(f"Good {current_profile} profile track record")
                else:
                    breakdown.profile_fit = 0.2
                    weaknesses.append(f"Not optimized for {current_profile} profile")
            except ValueError:
                breakdown.profile_fit = 0.5
        else:
            breakdown.profile_fit = 0.7
        
        # ===========================================
        # 5. Diagnostics Score (0-1)
        # ===========================================
        if decision_stats and decision_stats.total_decisions > 0:
            # Block rate penalty (lower is better)
            block_score = max(0, 1.0 - decision_stats.block_rate * 2)
            
            # Entry rate bonus (higher is better but not too high)
            entry_rate = decision_stats.entry_rate
            if 0.05 <= entry_rate <= 0.30:
                entry_score = 0.8
            elif entry_rate < 0.05:
                entry_score = 0.4  # Too selective
            else:
                entry_score = 0.5  # Too aggressive
            
            breakdown.diagnostics = block_score * 0.6 + entry_score * 0.4
            
            # Penalty for high block rate
            if decision_stats.block_rate > self._config.max_block_rate_threshold:
                penalties.high_block_rate = self._config.block_rate_penalty
                warnings.append(f"High block rate: {decision_stats.block_rate:.1%}")
                weaknesses.append("Frequently blocked by filters")
        else:
            breakdown.diagnostics = 0.6  # Slightly positive default
        
        # ===========================================
        # Calculate Total Score
        # ===========================================
        raw_score = (
            breakdown.performance * self._config.performance_weight +
            breakdown.stability * self._config.stability_weight +
            breakdown.regime_fit * self._config.regime_fit_weight +
            breakdown.profile_fit * self._config.profile_fit_weight +
            breakdown.diagnostics * self._config.diagnostics_weight
        )
        
        # Apply penalties
        total_score = max(0, raw_score - penalties.total)
        
        return StrategySelectionScore(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            total_score=total_score,
            breakdown=breakdown,
            penalties=penalties,
            raw_score=raw_score,
            warnings=warnings,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    # ===========================================
    # Selection
    # ===========================================
    
    def select_best_strategy(
        self,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> StrategySelectionResult:
        """Select the best strategy for given context"""
        
        strategies = strategy_registry.list_strategies(enabled_only=True)
        
        if not strategies:
            return StrategySelectionResult(
                symbol=symbol,
                regime=regime,
                profile_id=profile_id,
                strategies_evaluated=0
            )
        
        # Calculate scores
        scores: List[StrategySelectionScore] = []
        for s in strategies:
            score = self.calculate_score(s, current_regime=regime, current_profile=profile_id)
            
            # Additional symbol filter if provided
            if symbol and symbol.upper() not in [a.upper() for a in s.allowed_assets]:
                score.total_score *= 0.5  # Reduce score for unsupported symbols
                score.warnings.append(f"Symbol {symbol} not in primary assets")
            
            scores.append(score)
        
        # Sort by total score
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        # Build ranking
        ranking: List[StrategyRankingEntry] = []
        for i, score in enumerate(scores):
            stats = statistics_service.get_statistics(score.strategy_id)
            
            entry = StrategyRankingEntry(
                rank=i + 1,
                strategy_id=score.strategy_id,
                strategy_name=score.strategy_name,
                total_score=score.total_score,
                recommended=(i == 0 and score.total_score >= 0.5),
                reason_summary=score.strengths[:3] if i == 0 else score.weaknesses[:2],
                win_rate=stats.win_rate if stats else 0,
                profit_factor=stats.profit_factor if stats else 0,
                max_drawdown=stats.max_drawdown if stats else 0
            )
            ranking.append(entry)
        
        # Build result
        best = scores[0] if scores else None
        
        result = StrategySelectionResult(
            symbol=symbol,
            regime=regime,
            profile_id=profile_id,
            best_strategy_id=best.strategy_id if best else "",
            best_strategy_name=best.strategy_name if best else "",
            best_strategy_score=best.total_score if best else 0,
            ranking=ranking,
            strategies_evaluated=len(strategies)
        )
        
        # Cache
        self._last_selection = result
        self._selection_history.append(result)
        if len(self._selection_history) > self._max_history:
            self._selection_history = self._selection_history[-self._max_history//2:]
        
        return result
    
    # ===========================================
    # Comparison
    # ===========================================
    
    def compare_strategies(
        self,
        strategy_ids: Optional[List[str]] = None,
        regime: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> List[StrategyComparisonEntry]:
        """Compare strategies side by side"""
        
        if strategy_ids:
            strategies = [strategy_registry.get_strategy(sid) for sid in strategy_ids]
            strategies = [s for s in strategies if s]
        else:
            strategies = strategy_registry.list_strategies(enabled_only=True)
        
        comparisons: List[StrategyComparisonEntry] = []
        
        for s in strategies:
            score = self.calculate_score(s, current_regime=regime, current_profile=profile_id)
            stats = statistics_service.get_statistics(s.strategy_id)
            
            entry = StrategyComparisonEntry(
                strategy_id=s.strategy_id,
                strategy_name=s.name,
                strategy_type=s.strategy_type.value,
                performance_score=score.breakdown.performance,
                stability_score=score.breakdown.stability,
                regime_fit_score=score.breakdown.regime_fit,
                profile_fit_score=score.breakdown.profile_fit,
                diagnostics_score=score.breakdown.diagnostics,
                total_score=score.total_score,
                total_trades=stats.total_trades if stats else 0,
                win_rate=stats.win_rate if stats else 0,
                profit_factor=stats.profit_factor if stats else 0,
                expectancy=stats.expectancy if stats else 0,
                max_drawdown=stats.max_drawdown if stats else 0,
                compatible_regimes=[r.value for r in s.compatible_regimes],
                compatible_profiles=[p.value for p in s.compatible_profiles]
            )
            comparisons.append(entry)
        
        # Sort by total score
        comparisons.sort(key=lambda x: x.total_score, reverse=True)
        
        return comparisons
    
    # ===========================================
    # Specific Selections
    # ===========================================
    
    def select_for_symbol(self, symbol: str) -> StrategySelectionResult:
        """Select best strategy for a specific symbol"""
        return self.select_best_strategy(symbol=symbol)
    
    def select_for_regime(self, regime: str) -> StrategySelectionResult:
        """Select best strategy for a specific regime"""
        return self.select_best_strategy(regime=regime)
    
    def select_for_profile(self, profile_id: str) -> StrategySelectionResult:
        """Select best strategy for a specific profile"""
        return self.select_best_strategy(profile_id=profile_id)
    
    # ===========================================
    # Getters
    # ===========================================
    
    def get_last_selection(self) -> Optional[StrategySelectionResult]:
        """Get last selection result"""
        return self._last_selection
    
    def get_selection_history(self, limit: int = 20) -> List[StrategySelectionResult]:
        """Get selection history"""
        return self._selection_history[-limit:]
    
    def get_strategy_score(
        self,
        strategy_id: str,
        regime: Optional[str] = None,
        profile_id: Optional[str] = None
    ) -> Optional[StrategySelectionScore]:
        """Get detailed score for a specific strategy"""
        strategy = strategy_registry.get_strategy(strategy_id)
        if not strategy:
            return None
        return self.calculate_score(strategy, current_regime=regime, current_profile=profile_id)
    
    def get_config(self) -> Dict[str, Any]:
        """Get selection configuration"""
        return self._config.to_dict()
    
    def update_config(self, updates: Dict[str, Any]):
        """Update selection configuration"""
        if "weights" in updates:
            w = updates["weights"]
            if "performance" in w:
                self._config.performance_weight = w["performance"]
            if "stability" in w:
                self._config.stability_weight = w["stability"]
            if "regimeFit" in w:
                self._config.regime_fit_weight = w["regimeFit"]
            if "profileFit" in w:
                self._config.profile_fit_weight = w["profileFit"]
            if "diagnostics" in w:
                self._config.diagnostics_weight = w["diagnostics"]
        
        if "thresholds" in updates:
            t = updates["thresholds"]
            if "maxDrawdown" in t:
                self._config.max_drawdown_threshold = t["maxDrawdown"]
            if "maxBlockRate" in t:
                self._config.max_block_rate_threshold = t["maxBlockRate"]
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Strategy Selection",
            "phase": "STG5",
            "status": "healthy",
            "strategiesAvailable": len(strategy_registry.list_strategies(enabled_only=True)),
            "selectionsPerformed": len(self._selection_history),
            "lastSelection": self._last_selection.best_strategy_id if self._last_selection else None
        }


# Global singleton
selection_service = SelectionService()
