"""
PHASE 12.2 - Regime Switching Engine
=====================================
Automatically switches strategy regime based on market state.

Regimes:
- AGGRESSIVE_TREND: Momentum strategies ↑
- CONSERVATIVE_TREND: Careful trend following
- MEAN_REVERSION: Range strategies ↑
- VOLATILITY_HARVEST: Vol strategies active
- DEFENSIVE: Risk-off mode
- BALANCED: Normal operation
- RESEARCH_ONLY: No live trading
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta

from .system_types import (
    GlobalMarketState, RegimeProfile, RegimeSwitchRecommendation,
    DEFAULT_SYSTEM_CONFIG
)


class RegimeSwitchingEngine:
    """
    Multi-Regime Strategy Switching Engine
    
    Automatically adjusts strategy weights and activation
    based on detected market regime.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_SYSTEM_CONFIG
        self.current_profile = RegimeProfile.BALANCED
        self.switch_history: List[RegimeSwitchRecommendation] = []
        self.max_history = 100
        self.last_switch_time: Optional[datetime] = None
        
        # Strategy weight profiles for each regime
        self.regime_weights = {
            RegimeProfile.AGGRESSIVE_TREND: {
                "momentum": 1.5,
                "breakout": 1.3,
                "trend_following": 1.4,
                "mean_reversion": 0.3,
                "volatility": 0.5
            },
            RegimeProfile.CONSERVATIVE_TREND: {
                "momentum": 1.0,
                "breakout": 0.8,
                "trend_following": 1.2,
                "mean_reversion": 0.5,
                "volatility": 0.7
            },
            RegimeProfile.MEAN_REVERSION: {
                "momentum": 0.4,
                "breakout": 0.3,
                "trend_following": 0.5,
                "mean_reversion": 1.5,
                "volatility": 0.8
            },
            RegimeProfile.VOLATILITY_HARVEST: {
                "momentum": 0.6,
                "breakout": 0.7,
                "trend_following": 0.5,
                "mean_reversion": 0.6,
                "volatility": 1.5
            },
            RegimeProfile.DEFENSIVE: {
                "momentum": 0.3,
                "breakout": 0.2,
                "trend_following": 0.4,
                "mean_reversion": 0.5,
                "volatility": 0.3
            },
            RegimeProfile.BALANCED: {
                "momentum": 1.0,
                "breakout": 1.0,
                "trend_following": 1.0,
                "mean_reversion": 1.0,
                "volatility": 1.0
            },
            RegimeProfile.RESEARCH_ONLY: {
                "momentum": 0.0,
                "breakout": 0.0,
                "trend_following": 0.0,
                "mean_reversion": 0.0,
                "volatility": 0.0
            }
        }
    
    def evaluate_regime_switch(
        self,
        market_state: GlobalMarketState,
        state_confidence: float,
        system_health: float,
        edge_strength: float
    ) -> RegimeSwitchRecommendation:
        """
        Evaluate if regime should be switched.
        
        Args:
            market_state: Current market state
            state_confidence: Confidence in state
            system_health: System health score
            edge_strength: Overall edge strength
            
        Returns:
            RegimeSwitchRecommendation
        """
        now = datetime.now(timezone.utc)
        
        # Map market state to recommended profile
        recommended = self._map_state_to_profile(
            market_state, system_health, edge_strength
        )
        
        # Check if switch is needed
        if recommended == self.current_profile:
            recommendation = RegimeSwitchRecommendation(
                timestamp=now,
                current_profile=self.current_profile,
                recommended_profile=recommended,
                trigger_reason="No change needed",
                supporting_signals=[],
                strategy_adjustments={},
                confidence=state_confidence,
                urgency=0.0,
                execution_timing="N/A"
            )
        else:
            # Check cooldown
            cooldown_clear = self._check_cooldown()
            
            # Build supporting signals
            signals = self._build_supporting_signals(market_state, system_health)
            
            # Calculate strategy adjustments
            adjustments = self._calculate_adjustments(self.current_profile, recommended)
            
            # Determine urgency
            urgency = self._calculate_urgency(market_state, system_health)
            
            # Determine timing
            if not cooldown_clear:
                timing = "BLOCKED_COOLDOWN"
                urgency = 0.0
            elif urgency > 0.8:
                timing = "IMMEDIATE"
            elif urgency > 0.5:
                timing = "NEXT_SESSION"
            else:
                timing = "SCHEDULED"
            
            recommendation = RegimeSwitchRecommendation(
                timestamp=now,
                current_profile=self.current_profile,
                recommended_profile=recommended,
                trigger_reason=f"Market state: {market_state.value}",
                supporting_signals=signals,
                strategy_adjustments=adjustments,
                confidence=state_confidence,
                urgency=urgency,
                execution_timing=timing
            )
        
        # Save to history
        self.switch_history.append(recommendation)
        if len(self.switch_history) > self.max_history:
            self.switch_history = self.switch_history[-self.max_history:]
        
        return recommendation
    
    def _map_state_to_profile(
        self,
        market_state: GlobalMarketState,
        system_health: float,
        edge_strength: float
    ) -> RegimeProfile:
        """Map market state to regime profile."""
        
        # System health overrides
        if system_health < 0.3:
            return RegimeProfile.DEFENSIVE
        if system_health < 0.2:
            return RegimeProfile.RESEARCH_ONLY
        
        # Edge strength consideration
        if edge_strength < 0.3:
            return RegimeProfile.DEFENSIVE
        
        # Map based on market state
        state_to_profile = {
            GlobalMarketState.TRENDING: RegimeProfile.AGGRESSIVE_TREND if edge_strength > 0.6 else RegimeProfile.CONSERVATIVE_TREND,
            GlobalMarketState.RANGING: RegimeProfile.MEAN_REVERSION,
            GlobalMarketState.HIGH_VOLATILITY: RegimeProfile.VOLATILITY_HARVEST,
            GlobalMarketState.LOW_VOLATILITY: RegimeProfile.MEAN_REVERSION,
            GlobalMarketState.LOW_LIQUIDITY: RegimeProfile.DEFENSIVE,
            GlobalMarketState.RISK_OFF: RegimeProfile.DEFENSIVE,
            GlobalMarketState.RISK_ON: RegimeProfile.AGGRESSIVE_TREND,
            GlobalMarketState.MACRO_DOMINANT: RegimeProfile.CONSERVATIVE_TREND,
            GlobalMarketState.CRYPTO_NATIVE: RegimeProfile.BALANCED,
            GlobalMarketState.TRANSITION: RegimeProfile.BALANCED,
        }
        
        return state_to_profile.get(market_state, RegimeProfile.BALANCED)
    
    def _check_cooldown(self) -> bool:
        """Check if switch cooldown has passed."""
        if self.last_switch_time is None:
            return True
        
        hours_since = (datetime.now(timezone.utc) - self.last_switch_time).total_seconds() / 3600
        cooldown_hours = self.config["regime_switch_cooldown_hours"]
        
        return hours_since >= cooldown_hours
    
    def _build_supporting_signals(
        self,
        market_state: GlobalMarketState,
        system_health: float
    ) -> List[str]:
        """Build list of supporting signals."""
        signals = []
        
        signals.append(f"Market state: {market_state.value}")
        signals.append(f"System health: {system_health:.2%}")
        
        if market_state == GlobalMarketState.TRENDING:
            signals.append("Strong directional movement detected")
        elif market_state == GlobalMarketState.RANGING:
            signals.append("Consolidation pattern detected")
        elif market_state == GlobalMarketState.HIGH_VOLATILITY:
            signals.append("Elevated volatility environment")
        elif market_state == GlobalMarketState.RISK_OFF:
            signals.append("Risk-off sentiment detected")
        
        return signals
    
    def _calculate_adjustments(
        self,
        current: RegimeProfile,
        target: RegimeProfile
    ) -> Dict[str, float]:
        """Calculate strategy weight adjustments."""
        current_weights = self.regime_weights.get(current, {})
        target_weights = self.regime_weights.get(target, {})
        
        adjustments = {}
        for strategy in set(list(current_weights.keys()) + list(target_weights.keys())):
            curr = current_weights.get(strategy, 1.0)
            tgt = target_weights.get(strategy, 1.0)
            change = tgt - curr
            if abs(change) > 0.1:
                adjustments[strategy] = round(change, 2)
        
        return adjustments
    
    def _calculate_urgency(
        self,
        market_state: GlobalMarketState,
        system_health: float
    ) -> float:
        """Calculate urgency of regime switch."""
        urgency = 0.5
        
        # Emergency states
        if market_state in [GlobalMarketState.RISK_OFF, GlobalMarketState.LOW_LIQUIDITY]:
            urgency += 0.3
        
        # Health issues
        if system_health < 0.4:
            urgency += 0.2
        
        return min(1.0, urgency)
    
    def apply_switch(self, new_profile: RegimeProfile):
        """Apply a regime switch."""
        self.current_profile = new_profile
        self.last_switch_time = datetime.now(timezone.utc)
    
    def get_current_weights(self) -> Dict[str, float]:
        """Get current strategy weights based on regime."""
        return self.regime_weights.get(self.current_profile, {}).copy()
    
    def get_regime_summary(self) -> Dict:
        """Get summary of regime state."""
        return {
            "current_profile": self.current_profile.value,
            "current_weights": self.get_current_weights(),
            "last_switch": self.last_switch_time.isoformat() if self.last_switch_time else None,
            "cooldown_clear": self._check_cooldown(),
            "switch_count": len(self.switch_history)
        }
