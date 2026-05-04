"""
PHASE 12.1 - Global Market State Engine
========================================
Determines global market state by combining all intelligence layers.

States:
- TRENDING / RANGING
- HIGH_VOLATILITY / LOW_VOLATILITY
- LOW_LIQUIDITY
- MACRO_DOMINANT / CRYPTO_NATIVE
- RISK_ON / RISK_OFF
- TRANSITION
"""

import random
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta

from .system_types import (
    GlobalMarketState, MarketStateSnapshot, DEFAULT_SYSTEM_CONFIG
)


class GlobalMarketStateEngine:
    """
    Global Market State Engine
    
    Synthesizes information from all intelligence layers
    to determine the current global market state.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_SYSTEM_CONFIG
        self.state_history: List[MarketStateSnapshot] = []
        self.max_history = 100
        self.current_state: Optional[GlobalMarketState] = None
        self.state_start_time: Optional[datetime] = None
    
    def analyze_market_state(
        self,
        volatility_data: Optional[Dict] = None,
        liquidity_data: Optional[Dict] = None,
        correlation_data: Optional[Dict] = None,
        microstructure_data: Optional[Dict] = None,
        macro_indicators: Optional[Dict] = None
    ) -> MarketStateSnapshot:
        """
        Analyze and determine global market state.
        
        Args:
            volatility_data: Volatility regime info
            liquidity_data: Liquidity intelligence data
            correlation_data: Correlation analysis
            microstructure_data: Microstructure analysis
            macro_indicators: Macro economic indicators
            
        Returns:
            MarketStateSnapshot with state determination
        """
        now = datetime.now(timezone.utc)
        
        # Get regime assessments from each layer
        vol_regime = self._assess_volatility_regime(volatility_data)
        liq_regime = self._assess_liquidity_regime(liquidity_data)
        corr_regime = self._assess_correlation_regime(correlation_data)
        micro_regime = self._assess_microstructure_regime(microstructure_data)
        
        # Extract key metrics
        market_vol = volatility_data.get("current_volatility", 0.15) if volatility_data else 0.15 + random.gauss(0, 0.03)
        avg_corr = correlation_data.get("avg_correlation", 0.4) if correlation_data else 0.4 + random.gauss(0, 0.1)
        liq_score = liquidity_data.get("liquidity_score", 0.7) if liquidity_data else 0.7 + random.gauss(0, 0.1)
        
        # Get flow pressure
        flow_pressure = microstructure_data.get("pressure_direction", "NEUTRAL") if microstructure_data else "NEUTRAL"
        
        # Calculate trend
        trend_strength, trend_direction = self._calculate_trend(volatility_data, microstructure_data)
        
        # Determine primary market state
        market_state, confidence = self._determine_state(
            vol_regime, liq_regime, corr_regime, micro_regime,
            market_vol, avg_corr, liq_score, trend_strength
        )
        
        # Track state duration
        state_duration = 0
        previous_state = None
        
        if self.current_state != market_state:
            previous_state = self.current_state.value if self.current_state else None
            self.current_state = market_state
            self.state_start_time = now
        elif self.state_start_time:
            state_duration = (now - self.state_start_time).total_seconds() / 3600
        
        snapshot = MarketStateSnapshot(
            timestamp=now,
            market_state=market_state,
            state_confidence=confidence,
            volatility_regime=vol_regime,
            liquidity_regime=liq_regime,
            correlation_regime=corr_regime,
            microstructure_regime=micro_regime,
            market_volatility=market_vol,
            avg_correlation=avg_corr,
            liquidity_score=liq_score,
            flow_pressure=flow_pressure,
            trend_strength=trend_strength,
            trend_direction=trend_direction,
            state_duration_hours=state_duration,
            previous_state=previous_state
        )
        
        # Save to history
        self._add_to_history(snapshot)
        
        return snapshot
    
    def _assess_volatility_regime(self, data: Optional[Dict]) -> str:
        """Assess volatility regime."""
        if not data:
            return "NORMAL"
        
        vol = data.get("current_volatility", 0.15)
        
        if vol > self.config["high_volatility_threshold"]:
            return "HIGH"
        elif vol < self.config["low_volatility_threshold"]:
            return "LOW"
        return "NORMAL"
    
    def _assess_liquidity_regime(self, data: Optional[Dict]) -> str:
        """Assess liquidity regime."""
        if not data:
            return "NORMAL"
        
        score = data.get("liquidity_score", 0.7)
        
        if score < self.config["low_liquidity_threshold"]:
            return "LOW"
        elif score > 0.8:
            return "HIGH"
        return "NORMAL"
    
    def _assess_correlation_regime(self, data: Optional[Dict]) -> str:
        """Assess correlation regime."""
        if not data:
            return "NORMAL"
        
        avg_corr = data.get("avg_correlation", 0.4)
        
        if avg_corr > 0.7:
            return "HIGH_CORRELATION"
        elif avg_corr < 0.2:
            return "DECORRELATED"
        return "NORMAL"
    
    def _assess_microstructure_regime(self, data: Optional[Dict]) -> str:
        """Assess microstructure regime."""
        if not data:
            return "NORMAL"
        
        flow_state = data.get("flow_state", "BALANCED")
        
        if flow_state in ["BUYER_DOMINANT", "BURST_BUY"]:
            return "AGGRESSIVE_BUYING"
        elif flow_state in ["SELLER_DOMINANT", "BURST_SELL"]:
            return "AGGRESSIVE_SELLING"
        return "BALANCED"
    
    def _calculate_trend(
        self,
        volatility_data: Optional[Dict],
        microstructure_data: Optional[Dict]
    ) -> tuple:
        """Calculate trend strength and direction."""
        # Mock trend calculation
        strength = random.uniform(0.3, 0.8)
        
        if microstructure_data:
            pressure = microstructure_data.get("pressure_direction", "NEUTRAL")
            if pressure == "UP":
                direction = "BULLISH"
                strength += 0.1
            elif pressure == "DOWN":
                direction = "BEARISH"
                strength += 0.1
            else:
                direction = "NEUTRAL"
        else:
            direction = random.choice(["BULLISH", "BEARISH", "NEUTRAL"])
        
        return min(1.0, strength), direction
    
    def _determine_state(
        self,
        vol_regime: str,
        liq_regime: str,
        corr_regime: str,
        micro_regime: str,
        market_vol: float,
        avg_corr: float,
        liq_score: float,
        trend_strength: float
    ) -> tuple:
        """Determine primary market state."""
        confidence = 0.5
        
        # Check for extreme conditions first
        if vol_regime == "HIGH":
            if avg_corr > 0.7:
                state = GlobalMarketState.RISK_OFF
                confidence = 0.8
            else:
                state = GlobalMarketState.HIGH_VOLATILITY
                confidence = 0.75
        
        elif liq_regime == "LOW":
            state = GlobalMarketState.LOW_LIQUIDITY
            confidence = 0.7
        
        elif trend_strength > self.config["trending_threshold"]:
            state = GlobalMarketState.TRENDING
            confidence = 0.7 + trend_strength * 0.2
        
        elif trend_strength < 0.3:
            state = GlobalMarketState.RANGING
            confidence = 0.65
        
        elif vol_regime == "LOW" and liq_regime != "LOW":
            state = GlobalMarketState.LOW_VOLATILITY
            confidence = 0.6
        
        elif corr_regime == "HIGH_CORRELATION":
            state = GlobalMarketState.MACRO_DOMINANT
            confidence = 0.65
        
        elif corr_regime == "DECORRELATED":
            state = GlobalMarketState.CRYPTO_NATIVE
            confidence = 0.6
        
        else:
            # Check for transition
            if self.state_history and len(self.state_history) > 2:
                recent_states = [s.market_state for s in self.state_history[-3:]]
                if len(set(recent_states)) > 1:
                    state = GlobalMarketState.TRANSITION
                    confidence = 0.5
                else:
                    state = GlobalMarketState.RANGING
                    confidence = 0.55
            else:
                state = GlobalMarketState.RANGING
                confidence = 0.55
        
        return state, confidence
    
    def _add_to_history(self, snapshot: MarketStateSnapshot):
        """Add snapshot to history."""
        self.state_history.append(snapshot)
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]
    
    def get_state_summary(self) -> Dict:
        """Get summary of market state analysis."""
        if not self.state_history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.state_history[-1]
        
        # Count state distribution
        state_counts = {}
        for s in self.state_history[-20:]:
            st = s.market_state.value
            state_counts[st] = state_counts.get(st, 0) + 1
        
        return {
            "current_state": recent.market_state.value,
            "confidence": round(recent.state_confidence, 3),
            "duration_hours": round(recent.state_duration_hours, 1),
            "state_distribution": state_counts,
            "volatility_regime": recent.volatility_regime,
            "liquidity_regime": recent.liquidity_regime
        }
