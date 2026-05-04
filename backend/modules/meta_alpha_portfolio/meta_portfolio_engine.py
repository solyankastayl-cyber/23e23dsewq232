"""
Meta-Alpha Portfolio Engine

PHASE 45 — Meta-Alpha Portfolio Engine

Distributes capital between alpha types (not assets).

Key insight:
System learns which type of intelligence currently works best.

Pipeline:
Alpha Engines → Meta-Alpha Weights → Hypothesis Modifier → Portfolio Allocation
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from .meta_portfolio_types import (
    AlphaFamily,
    PatternClass,
    MetaAlphaWeight,
    MetaAlphaPortfolioState,
    MetaAlphaConfig,
    TradeOutcome,
    META_SCORE_WEIGHTS,
    PATTERN_THRESHOLDS,
)


class MetaAlphaPortfolioEngine:
    """
    Meta-Alpha Portfolio Engine — PHASE 45
    
    Tracks alpha family performance and adjusts weights.
    
    System learns:
    - Which alpha type works best in current market
    - How to weight signals from different intelligence layers
    """
    
    def __init__(self, config: Optional[MetaAlphaConfig] = None):
        self._config = config or MetaAlphaConfig()
        
        # Initialize weights for all alpha families
        self._alpha_weights: Dict[AlphaFamily, MetaAlphaWeight] = {}
        for family in AlphaFamily:
            self._alpha_weights[family] = MetaAlphaWeight(
                alpha_family=family,
                meta_weight=1.0 / len(AlphaFamily),  # Equal initial weight
            )
        
        # Trade history
        self._trade_history: List[TradeOutcome] = []
        
        # Stats
        self._total_rebalances: int = 0
        self._last_rebalance: Optional[datetime] = None
    
    # ═══════════════════════════════════════════════════════════
    # 1. Core Operations
    # ═══════════════════════════════════════════════════════════
    
    def record_outcome(
        self,
        hypothesis_id: str,
        alpha_family: AlphaFamily,
        symbol: str,
        pnl_pct: float,
        regime_at_entry: str = "UNKNOWN",
        signal_age_at_execution: int = 0,
        entry_price: float = 0.0,
        exit_price: float = 0.0,
    ) -> TradeOutcome:
        """
        Record a trade outcome for learning.
        
        Called after trade closes.
        """
        outcome = TradeOutcome(
            hypothesis_id=hypothesis_id,
            alpha_family=alpha_family,
            symbol=symbol,
            entry_time=datetime.now(timezone.utc) - timedelta(minutes=signal_age_at_execution),
            exit_time=datetime.now(timezone.utc),
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            is_winner=pnl_pct > 0,
            regime_at_entry=regime_at_entry,
            signal_age_at_execution=signal_age_at_execution,
        )
        
        self._trade_history.append(outcome)
        
        # Update family stats
        self._update_family_stats(alpha_family)
        
        return outcome
    
    def recompute_weights(self) -> MetaAlphaPortfolioState:
        """
        Recompute all alpha family weights based on recent performance.
        
        Called periodically (every 30 min default).
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self._config.lookback_hours)
        
        # Filter recent trades
        recent_trades = [t for t in self._trade_history if t.recorded_at > cutoff]
        
        # Group by alpha family
        trades_by_family: Dict[AlphaFamily, List[TradeOutcome]] = defaultdict(list)
        for trade in recent_trades:
            trades_by_family[trade.alpha_family].append(trade)
        
        # Update each family's metrics
        for family in AlphaFamily:
            family_trades = trades_by_family[family]
            weight = self._alpha_weights[family]
            
            if len(family_trades) >= self._config.min_trades_for_stats:
                # Calculate metrics
                weight.total_trades = len(family_trades)
                weight.winning_trades = sum(1 for t in family_trades if t.is_winner)
                weight.losing_trades = weight.total_trades - weight.winning_trades
                weight.recent_success_rate = weight.winning_trades / weight.total_trades
                weight.recent_avg_pnl = sum(t.pnl_pct for t in family_trades) / len(family_trades)
                
                # Get regime fit (simplified - could be enhanced)
                weight.regime_fit_score = self._calculate_regime_fit(family)
                
                # Get decay adjustment
                weight.decay_adjusted_score = self._calculate_decay_adjustment(family_trades)
            else:
                # Not enough data - use defaults
                weight.recent_success_rate = 0.5
                weight.recent_avg_pnl = 0.0
                weight.regime_fit_score = 0.5
                weight.decay_adjusted_score = 0.5
            
            # Compute meta score
            weight.compute_meta_score()
            weight.updated_at = now
        
        # Normalize weights (sum = 1)
        total_score = sum(w.meta_score for w in self._alpha_weights.values())
        if total_score > 0:
            for weight in self._alpha_weights.values():
                weight.meta_weight = weight.meta_score / total_score
        
        self._total_rebalances += 1
        self._last_rebalance = now
        
        return self.get_state()
    
    def _update_family_stats(self, family: AlphaFamily):
        """Update stats for a single family after new trade."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self._config.lookback_hours)
        
        recent_trades = [
            t for t in self._trade_history 
            if t.alpha_family == family and t.recorded_at > cutoff
        ]
        
        weight = self._alpha_weights[family]
        
        if recent_trades:
            weight.total_trades = len(recent_trades)
            weight.winning_trades = sum(1 for t in recent_trades if t.is_winner)
            weight.losing_trades = weight.total_trades - weight.winning_trades
            
            if weight.total_trades > 0:
                weight.recent_success_rate = weight.winning_trades / weight.total_trades
                weight.recent_avg_pnl = sum(t.pnl_pct for t in recent_trades) / len(recent_trades)
        
        weight.compute_meta_score()
        weight.updated_at = now
    
    def _calculate_regime_fit(self, family: AlphaFamily) -> float:
        """
        Calculate how well alpha family fits current regime.
        
        Simplified version - could integrate with RegimeEngine.
        """
        try:
            from modules.regime.regime_engine import get_regime_engine
            engine = get_regime_engine()
            
            # Get current regime
            state = engine.get_current_state("BTC")
            if not state:
                return 0.5
            
            regime_type = state.regime_type.value
            
            # Regime-family fit matrix
            fit_matrix = {
                "TRENDING_UP": {
                    AlphaFamily.TREND_BREAKOUT: 0.85,
                    AlphaFamily.MEAN_REVERSION: 0.30,
                    AlphaFamily.FRACTAL: 0.65,
                    AlphaFamily.CAPITAL_FLOW: 0.70,
                    AlphaFamily.REFLEXIVITY: 0.60,
                },
                "TRENDING_DOWN": {
                    AlphaFamily.TREND_BREAKOUT: 0.75,
                    AlphaFamily.MEAN_REVERSION: 0.35,
                    AlphaFamily.FRACTAL: 0.60,
                    AlphaFamily.CAPITAL_FLOW: 0.75,
                    AlphaFamily.REFLEXIVITY: 0.70,
                },
                "RANGING": {
                    AlphaFamily.TREND_BREAKOUT: 0.35,
                    AlphaFamily.MEAN_REVERSION: 0.85,
                    AlphaFamily.FRACTAL: 0.70,
                    AlphaFamily.CAPITAL_FLOW: 0.50,
                    AlphaFamily.REFLEXIVITY: 0.55,
                },
                "VOLATILE": {
                    AlphaFamily.TREND_BREAKOUT: 0.50,
                    AlphaFamily.MEAN_REVERSION: 0.40,
                    AlphaFamily.FRACTAL: 0.55,
                    AlphaFamily.CAPITAL_FLOW: 0.65,
                    AlphaFamily.REFLEXIVITY: 0.80,
                },
            }
            
            regime_fits = fit_matrix.get(regime_type, {})
            return regime_fits.get(family, 0.5)
            
        except Exception:
            return 0.5
    
    def _calculate_decay_adjustment(self, trades: List[TradeOutcome]) -> float:
        """Calculate decay-adjusted score based on signal ages."""
        if not trades:
            return 0.5
        
        # Trades with younger signals at execution are better
        avg_age = sum(t.signal_age_at_execution for t in trades) / len(trades)
        
        # Normalize: 0 min = 1.0, 60 min = 0.5, 120 min = 0.25
        decay_score = max(0.25, 1.0 - (avg_age / 120))
        
        return decay_score
    
    # ═══════════════════════════════════════════════════════════
    # 2. Integration Methods
    # ═══════════════════════════════════════════════════════════
    
    def get_hypothesis_modifier(self, alpha_family: AlphaFamily) -> Dict:
        """
        Get hypothesis modifier for a specific alpha family.
        
        For Hypothesis Engine integration.
        """
        weight = self._alpha_weights.get(alpha_family)
        if not weight:
            return {
                "modifier": 1.0,
                "meta_score": 0.5,
                "pattern_class": "MODERATE",
                "has_stats": False,
            }
        
        return {
            "modifier": round(weight.hypothesis_modifier, 4),
            "meta_score": round(weight.meta_score, 4),
            "meta_weight": round(weight.meta_weight, 4),
            "pattern_class": weight.pattern_class.value,
            "success_rate": round(weight.recent_success_rate, 4),
            "avg_pnl": round(weight.recent_avg_pnl, 4),
            "total_trades": weight.total_trades,
            "has_stats": weight.total_trades >= self._config.min_trades_for_stats,
        }
    
    def get_portfolio_allocation_weights(self) -> Dict[str, float]:
        """
        Get recommended portfolio weights by alpha family.
        
        For Portfolio Manager integration.
        """
        return {
            family.value: round(weight.meta_weight, 4)
            for family, weight in self._alpha_weights.items()
        }
    
    def get_risk_budget_weights(self) -> Dict[str, float]:
        """
        Get risk budget allocation by alpha family.
        
        Strong families get more risk budget.
        """
        weights = {}
        
        for family, weight in self._alpha_weights.items():
            if weight.pattern_class == PatternClass.STRONG:
                budget_weight = weight.meta_weight * 1.2
            elif weight.pattern_class == PatternClass.WEAK:
                budget_weight = weight.meta_weight * 0.8
            else:
                budget_weight = weight.meta_weight
            
            weights[family.value] = round(budget_weight, 4)
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v/total, 4) for k, v in weights.items()}
        
        return weights
    
    # ═══════════════════════════════════════════════════════════
    # 3. Getters
    # ═══════════════════════════════════════════════════════════
    
    def get_state(self) -> MetaAlphaPortfolioState:
        """Get current portfolio state."""
        weights_dict = {
            family.value: weight 
            for family, weight in self._alpha_weights.items()
        }
        
        # Find dominant family
        dominant = max(self._alpha_weights.items(), key=lambda x: x[1].meta_weight)
        
        # Find best/worst
        best = max(self._alpha_weights.items(), key=lambda x: x[1].meta_score)
        worst = min(self._alpha_weights.items(), key=lambda x: x[1].meta_score)
        
        # Calculate diversification (inverse of concentration)
        weights_list = [w.meta_weight for w in self._alpha_weights.values()]
        herfindahl = sum(w**2 for w in weights_list)
        diversification = 1 - herfindahl
        
        return MetaAlphaPortfolioState(
            alpha_weights=weights_dict,
            dominant_alpha_family=dominant[0].value,
            diversification_score=round(diversification, 4),
            total_signals_tracked=len(self._trade_history),
            best_performing_family=best[0].value,
            worst_performing_family=worst[0].value,
            avg_meta_score=round(sum(w.meta_score for w in self._alpha_weights.values()) / len(self._alpha_weights), 4),
        )
    
    def get_family_stats(self, family: AlphaFamily) -> Dict:
        """Get detailed stats for an alpha family."""
        weight = self._alpha_weights.get(family)
        if not weight:
            return {"error": f"Unknown family: {family}"}
        
        return {
            "alpha_family": family.value,
            "meta_score": round(weight.meta_score, 4),
            "meta_weight": round(weight.meta_weight, 4),
            "pattern_class": weight.pattern_class.value,
            "hypothesis_modifier": round(weight.hypothesis_modifier, 4),
            "performance": {
                "success_rate": round(weight.recent_success_rate, 4),
                "avg_pnl": round(weight.recent_avg_pnl, 4),
                "total_trades": weight.total_trades,
                "winning_trades": weight.winning_trades,
                "losing_trades": weight.losing_trades,
            },
            "fit_scores": {
                "regime_fit": round(weight.regime_fit_score, 4),
                "decay_adjusted": round(weight.decay_adjusted_score, 4),
            },
            "updated_at": weight.updated_at.isoformat(),
        }
    
    def get_summary(self) -> Dict:
        """Get summary of all alpha families."""
        state = self.get_state()
        
        return {
            "phase": "45",
            "dominant_family": state.dominant_alpha_family,
            "diversification": state.diversification_score,
            "total_signals": state.total_signals_tracked,
            "best_family": state.best_performing_family,
            "worst_family": state.worst_performing_family,
            "avg_meta_score": state.avg_meta_score,
            "weights": self.get_portfolio_allocation_weights(),
            "families": [
                {
                    "family": family.value,
                    "score": round(weight.meta_score, 4),
                    "weight": round(weight.meta_weight, 4),
                    "class": weight.pattern_class.value,
                    "modifier": round(weight.hypothesis_modifier, 4),
                }
                for family, weight in self._alpha_weights.items()
            ],
            "last_rebalance": self._last_rebalance.isoformat() if self._last_rebalance else None,
            "total_rebalances": self._total_rebalances,
        }
    
    def get_config(self) -> MetaAlphaConfig:
        """Get configuration."""
        return self._config


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_meta_alpha_engine: Optional[MetaAlphaPortfolioEngine] = None


def get_meta_alpha_engine() -> MetaAlphaPortfolioEngine:
    """Get singleton instance."""
    global _meta_alpha_engine
    if _meta_alpha_engine is None:
        _meta_alpha_engine = MetaAlphaPortfolioEngine()
    return _meta_alpha_engine
