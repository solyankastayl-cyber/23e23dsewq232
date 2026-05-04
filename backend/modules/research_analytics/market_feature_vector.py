"""
Market Feature Vector — PHASE TA-FINAL

Aggregates all indicator signals into a unified feature vector
that can be used by:
- Hypothesis Engine
- Scenario Probability Engine
- Trading Decision Engine
- Signal Explanation

This is the core multi-factor model aggregation layer.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np

from .indicator_signal_engine import (
    IndicatorSignal,
    IndicatorSignalBatch,
    get_indicator_signal_engine,
    INDICATOR_WEIGHTS,
    INDICATOR_TYPES,
)


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class MarketFeatureVector(BaseModel):
    """
    Unified feature vector representing market state.
    
    All scores are normalized to [-1, +1] range:
    - Positive = Bullish
    - Negative = Bearish
    - Zero = Neutral
    """
    symbol: str
    timeframe: str
    updated_at: str
    
    # Category scores (-1 to +1)
    trend_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    momentum_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    volatility_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    breakout_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    mean_reversion_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    structure_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Direction scores
    bullish_score: float = Field(default=0.0, ge=0.0, le=1.0)
    bearish_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Net score (main signal)
    net_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Confidence in the signal
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Signal agreement ratio
    agreement_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Raw indicator signals
    indicator_signals: List[IndicatorSignal] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeatureWeights(BaseModel):
    """Weights for different feature types in hypothesis scoring."""
    trend: float = 0.35
    momentum: float = 0.25
    volatility: float = 0.15
    breakout: float = 0.20
    mean_reversion: float = 0.05


# ═══════════════════════════════════════════════════════════════
# Feature Vector Service
# ═══════════════════════════════════════════════════════════════

class MarketFeatureVectorService:
    """
    Service to build and manage market feature vectors.
    
    Pipeline:
    candles → indicator signals → weighted aggregation → feature vector
    """
    
    def __init__(self):
        self.signal_engine = get_indicator_signal_engine()
        self.weights = FeatureWeights()
    
    def build_feature_vector(
        self,
        candles: List[Dict[str, Any]],
        symbol: str = "UNKNOWN",
        timeframe: str = "1H"
    ) -> MarketFeatureVector:
        """
        Build complete feature vector from candle data.
        
        Args:
            candles: OHLCV candle data
            symbol: Trading symbol
            timeframe: Chart timeframe
        
        Returns:
            MarketFeatureVector with all scores calculated
        """
        # Extract signals
        signal_batch = self.signal_engine.extract_signals(candles, symbol, timeframe)
        
        if not signal_batch.signals:
            return MarketFeatureVector(
                symbol=symbol,
                timeframe=timeframe,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        
        # Calculate category scores
        trend_score = self._calculate_category_score(signal_batch.trend_signals)
        momentum_score = self._calculate_category_score(signal_batch.momentum_signals)
        volatility_score = self._calculate_category_score(signal_batch.volatility_signals)
        breakout_score = self._calculate_category_score(signal_batch.breakout_signals)
        
        # Mean reversion is inverse of momentum at extremes
        mean_reversion_score = self._calculate_mean_reversion_score(signal_batch.momentum_signals)
        
        # Structure score from pattern detection (simplified)
        structure_score = self._calculate_structure_score(candles)
        
        # Calculate directional scores
        bullish_score, bearish_score = self._calculate_directional_scores(signal_batch.signals)
        
        # Calculate net score (weighted combination)
        net_score = self._calculate_net_score(
            trend_score, momentum_score, volatility_score, 
            breakout_score, mean_reversion_score
        )
        
        # Calculate confidence and agreement
        confidence = self._calculate_confidence(signal_batch.signals)
        agreement_ratio = self._calculate_agreement_ratio(signal_batch.signals)
        
        return MarketFeatureVector(
            symbol=symbol,
            timeframe=timeframe,
            updated_at=datetime.now(timezone.utc).isoformat(),
            trend_score=round(trend_score, 3),
            momentum_score=round(momentum_score, 3),
            volatility_score=round(volatility_score, 3),
            breakout_score=round(breakout_score, 3),
            mean_reversion_score=round(mean_reversion_score, 3),
            structure_score=round(structure_score, 3),
            bullish_score=round(bullish_score, 3),
            bearish_score=round(bearish_score, 3),
            net_score=round(net_score, 3),
            confidence=round(confidence, 3),
            agreement_ratio=round(agreement_ratio, 3),
            indicator_signals=signal_batch.signals,
            metadata={
                "num_signals": len(signal_batch.signals),
                "trend_count": len(signal_batch.trend_signals),
                "momentum_count": len(signal_batch.momentum_signals),
                "volatility_count": len(signal_batch.volatility_signals),
                "breakout_count": len(signal_batch.breakout_signals),
            }
        )
    
    def _calculate_category_score(
        self,
        signals: List[IndicatorSignal]
    ) -> float:
        """Calculate weighted score for a category of signals."""
        if not signals:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = INDICATOR_WEIGHTS.get(signal.indicator, 1.0)
            weighted_sum += signal.score * weight * signal.strength
            total_weight += weight * signal.strength
        
        if total_weight == 0:
            return 0.0
        
        return max(-1.0, min(1.0, weighted_sum / total_weight))
    
    def _calculate_mean_reversion_score(
        self,
        momentum_signals: List[IndicatorSignal]
    ) -> float:
        """
        Calculate mean reversion score.
        High when momentum indicators are at extremes (overbought/oversold).
        """
        if not momentum_signals:
            return 0.0
        
        extreme_signals = []
        for signal in momentum_signals:
            # RSI, CCI, Williams%R, Stochastic at extremes
            if signal.indicator in ["rsi", "cci", "williams_r", "stochastic"]:
                # Check if at extremes based on metadata
                if signal.indicator == "rsi":
                    rsi = signal.metadata.get("rsi", 50)
                    if rsi >= 70 or rsi <= 30:
                        # Reversal expected - opposite direction
                        extreme_signals.append(-signal.score * 0.8)
                elif signal.indicator == "cci":
                    cci = signal.metadata.get("cci", 0)
                    if abs(cci) >= 100:
                        extreme_signals.append(-signal.score * 0.7)
                elif signal.indicator == "stochastic":
                    k = signal.metadata.get("stochastic_k", 50)
                    if k >= 80 or k <= 20:
                        extreme_signals.append(-signal.score * 0.6)
        
        if not extreme_signals:
            return 0.0
        
        return max(-1.0, min(1.0, np.mean(extreme_signals)))
    
    def _calculate_structure_score(
        self,
        candles: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate market structure score.
        Based on higher highs/lows pattern.
        """
        if len(candles) < 20:
            return 0.0
        
        # Find swing highs and lows
        highs = [c["high"] for c in candles[-20:]]
        lows = [c["low"] for c in candles[-20:]]
        
        # Count higher highs and higher lows
        hh_count = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        hl_count = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
        ll_count = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        lh_count = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])
        
        total = len(highs) - 1
        
        bullish_structure = (hh_count + hl_count) / (2 * total) if total > 0 else 0
        bearish_structure = (ll_count + lh_count) / (2 * total) if total > 0 else 0
        
        return max(-1.0, min(1.0, (bullish_structure - bearish_structure) * 2))
    
    def _calculate_directional_scores(
        self,
        signals: List[IndicatorSignal]
    ) -> tuple:
        """Calculate bullish and bearish scores separately."""
        if not signals:
            return 0.0, 0.0
        
        bullish_sum = 0.0
        bearish_sum = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = INDICATOR_WEIGHTS.get(signal.indicator, 1.0)
            weighted_score = abs(signal.score) * weight * signal.strength
            
            if signal.direction == "bullish":
                bullish_sum += weighted_score
            elif signal.direction == "bearish":
                bearish_sum += weighted_score
            
            total_weight += weight * signal.strength
        
        if total_weight == 0:
            return 0.0, 0.0
        
        return (
            min(1.0, bullish_sum / total_weight),
            min(1.0, bearish_sum / total_weight)
        )
    
    def _calculate_net_score(
        self,
        trend: float,
        momentum: float,
        volatility: float,
        breakout: float,
        mean_reversion: float
    ) -> float:
        """
        Calculate weighted net score.
        
        Formula:
        net = w_trend * trend + w_momentum * momentum + 
              w_breakout * breakout + w_volatility * volatility +
              w_mean_reversion * mean_reversion
        """
        net = (
            self.weights.trend * trend +
            self.weights.momentum * momentum +
            self.weights.volatility * volatility +
            self.weights.breakout * breakout +
            self.weights.mean_reversion * mean_reversion
        )
        
        return max(-1.0, min(1.0, net))
    
    def _calculate_confidence(
        self,
        signals: List[IndicatorSignal]
    ) -> float:
        """
        Calculate confidence based on signal strength and agreement.
        High confidence when strong signals agree on direction.
        """
        if not signals:
            return 0.0
        
        # Average strength
        avg_strength = np.mean([s.strength for s in signals])
        
        # Direction consistency
        bullish = sum(1 for s in signals if s.direction == "bullish")
        bearish = sum(1 for s in signals if s.direction == "bearish")
        total = len(signals)
        
        dominant = max(bullish, bearish)
        consistency = dominant / total if total > 0 else 0
        
        # Confidence = strength * consistency
        confidence = avg_strength * consistency
        
        return min(1.0, confidence)
    
    def _calculate_agreement_ratio(
        self,
        signals: List[IndicatorSignal]
    ) -> float:
        """Calculate ratio of signals agreeing on direction."""
        if not signals:
            return 0.0
        
        bullish = sum(1 for s in signals if s.direction == "bullish")
        bearish = sum(1 for s in signals if s.direction == "bearish")
        neutral = sum(1 for s in signals if s.direction == "neutral")
        
        total = len(signals)
        dominant = max(bullish, bearish, neutral)
        
        return dominant / total if total > 0 else 0.0


# ═══════════════════════════════════════════════════════════════
# Scenario Probability Engine
# ═══════════════════════════════════════════════════════════════

class ScenarioProbabilityEngine:
    """
    Dynamically adjusts scenario probabilities based on feature vector.
    
    Base probabilities are modified by indicator signals:
    - Strong bullish → increases bull/extreme_bull, decreases bear
    - Strong bearish → increases bear/extreme_bear, decreases bull
    - High volatility → increases extreme scenarios
    """
    
    # Base probabilities
    BASE_PROBS = {
        "base": 0.40,
        "bull": 0.20,
        "bear": 0.20,
        "extreme_bull": 0.10,
        "extreme_bear": 0.10,
    }
    
    def calculate_scenario_probabilities(
        self,
        feature_vector: MarketFeatureVector
    ) -> Dict[str, float]:
        """
        Calculate dynamic scenario probabilities.
        
        Args:
            feature_vector: Current market feature vector
        
        Returns:
            Dict with scenario probabilities that sum to 1.0
        """
        net = feature_vector.net_score
        volatility = feature_vector.volatility_score
        breakout = feature_vector.breakout_score
        confidence = feature_vector.confidence
        
        # Start with base
        probs = self.BASE_PROBS.copy()
        
        # Adjust based on net score
        bull_bias = max(0, net)
        bear_bias = max(0, -net)
        
        # Net score influence
        probs["bull"] += 0.15 * bull_bias * confidence
        probs["bear"] += 0.15 * bear_bias * confidence
        
        # Reduce opposite direction
        probs["bull"] -= 0.10 * bear_bias * confidence
        probs["bear"] -= 0.10 * bull_bias * confidence
        
        # Base scenario shrinks with strong directional signals
        probs["base"] -= 0.15 * abs(net) * confidence
        
        # Extreme scenarios influenced by volatility and breakout
        extreme_modifier = max(abs(volatility), abs(breakout)) * 0.10
        
        if net > 0.3:
            probs["extreme_bull"] += extreme_modifier * confidence
            probs["extreme_bear"] -= extreme_modifier * 0.5
        elif net < -0.3:
            probs["extreme_bear"] += extreme_modifier * confidence
            probs["extreme_bull"] -= extreme_modifier * 0.5
        
        # Clamp to valid range
        for key in probs:
            probs[key] = max(0.02, min(0.60, probs[key]))
        
        # Normalize to sum to 1.0 with proper precision
        total = sum(probs.values())
        normalized = {k: v / total for k, v in probs.items()}
        
        # Round to 3 decimal places and ensure exact sum
        rounded = {k: round(v, 3) for k, v in normalized.items()}
        
        # Adjust the largest probability to ensure sum is exactly 1.0
        diff = 1.0 - sum(rounded.values())
        if diff != 0:
            max_key = max(rounded, key=rounded.get)
            rounded[max_key] = round(rounded[max_key] + diff, 3)
        
        return rounded
    
    def get_probability_explanation(
        self,
        feature_vector: MarketFeatureVector,
        probs: Dict[str, float]
    ) -> str:
        """Generate human-readable explanation of probabilities."""
        net = feature_vector.net_score
        confidence = feature_vector.confidence
        
        if net > 0.5 and confidence > 0.6:
            return f"Strong bullish signals ({confidence:.0%} confidence) shift probability toward bull scenarios"
        elif net < -0.5 and confidence > 0.6:
            return f"Strong bearish signals ({confidence:.0%} confidence) shift probability toward bear scenarios"
        elif abs(net) < 0.2:
            return "Mixed signals result in balanced scenario probabilities"
        else:
            direction = "bullish" if net > 0 else "bearish"
            return f"Moderate {direction} bias ({confidence:.0%} confidence) slightly shifts probabilities"


# ═══════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════

_feature_service: Optional[MarketFeatureVectorService] = None
_probability_engine: Optional[ScenarioProbabilityEngine] = None

def get_feature_vector_service() -> MarketFeatureVectorService:
    """Get singleton instance."""
    global _feature_service
    if _feature_service is None:
        _feature_service = MarketFeatureVectorService()
    return _feature_service

def get_scenario_probability_engine() -> ScenarioProbabilityEngine:
    """Get singleton instance."""
    global _probability_engine
    if _probability_engine is None:
        _probability_engine = ScenarioProbabilityEngine()
    return _probability_engine
