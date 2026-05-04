"""
Strategy Regime Engine Types
============================

Data structures for market regime classification.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class MarketRegimeType(str, Enum):
    """Market regime types for strategy optimization"""
    TRENDING = "TRENDING"              # Directional market
    RANGE = "RANGE"                    # Sideways/consolidation
    HIGH_VOLATILITY = "HIGH_VOLATILITY"  # Large moves, high risk
    LOW_VOLATILITY = "LOW_VOLATILITY"    # Compressed, pre-breakout
    TRANSITION = "TRANSITION"          # Unclear/dirty phase


@dataclass
class RegimeFeatureSet:
    """
    Feature set for regime classification.
    
    All features normalized to 0-1 range.
    """
    symbol: str = ""
    timeframe: str = ""
    
    # Core features
    trend_strength: float = 0.0        # 0 = no trend, 1 = strong trend
    volatility_level: float = 0.0      # 0 = low vol, 1 = high vol
    range_compression: float = 0.0     # 0 = no compression, 1 = tight range
    structure_clarity: float = 0.0     # 0 = unclear, 1 = clear HH/HL or LH/LL
    breakout_pressure: float = 0.0     # 0 = none, 1 = imminent breakout
    
    # Auxiliary features
    directional_consistency: float = 0.0  # How consistent the direction
    ma_separation: float = 0.0            # MA spread (normalized)
    atr_ratio: float = 0.0                # Current ATR vs SMA(ATR)
    volume_trend: float = 0.0             # Volume increasing/decreasing
    candle_body_ratio: float = 0.0        # Body vs wick ratio
    
    # Raw values (for debugging)
    raw_atr: float = 0.0
    raw_atr_sma: float = 0.0
    raw_range: float = 0.0
    raw_slope: float = 0.0
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "trendStrength": round(self.trend_strength, 4),
            "volatilityLevel": round(self.volatility_level, 4),
            "rangeCompression": round(self.range_compression, 4),
            "structureClarity": round(self.structure_clarity, 4),
            "breakoutPressure": round(self.breakout_pressure, 4),
            "directionalConsistency": round(self.directional_consistency, 4),
            "maSeparation": round(self.ma_separation, 4),
            "atrRatio": round(self.atr_ratio, 4),
            "volumeTrend": round(self.volume_trend, 4),
            "candleBodyRatio": round(self.candle_body_ratio, 4),
            "computedAt": self.computed_at
        }


@dataclass
class RegimeState:
    """
    Current regime state with confidence metrics.
    """
    regime_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    
    # Classification result
    regime: MarketRegimeType = MarketRegimeType.TRANSITION
    
    # Confidence metrics
    confidence: float = 0.0           # 0-1, how sure we are
    stability_score: float = 0.0      # 0-1, how stable the regime
    transition_risk: float = 0.0      # 0-1, risk of regime change
    
    # Secondary classifications (probabilities)
    regime_probabilities: Dict[str, float] = field(default_factory=dict)
    
    # Direction if trending
    trend_direction: str = "NEUTRAL"  # UP, DOWN, NEUTRAL
    
    # Features that led to classification
    features: Optional[RegimeFeatureSet] = None
    
    # Explanation
    classification_reasons: List[str] = field(default_factory=list)
    
    # Timing
    generated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    bars_in_regime: int = 0
    regime_start_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regimeId": self.regime_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime.value,
            "confidence": round(self.confidence, 4),
            "stabilityScore": round(self.stability_score, 4),
            "transitionRisk": round(self.transition_risk, 4),
            "regimeProbabilities": {k: round(v, 4) for k, v in self.regime_probabilities.items()},
            "trendDirection": self.trend_direction,
            "features": self.features.to_dict() if self.features else None,
            "classificationReasons": self.classification_reasons,
            "generatedAt": self.generated_at,
            "barsInRegime": self.bars_in_regime,
            "regimeStartAt": self.regime_start_at
        }


@dataclass
class RegimeTransitionEvent:
    """
    Record of a regime transition.
    """
    event_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    
    from_regime: MarketRegimeType = MarketRegimeType.TRANSITION
    to_regime: MarketRegimeType = MarketRegimeType.TRANSITION
    
    # Metrics at transition
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    confidence_drop: float = 0.0
    
    # Features at transition
    features_at_transition: Optional[RegimeFeatureSet] = None
    
    # Trigger indicators
    trigger_indicators: List[str] = field(default_factory=list)
    
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "fromRegime": self.from_regime.value,
            "toRegime": self.to_regime.value,
            "confidenceBefore": round(self.confidence_before, 4),
            "confidenceAfter": round(self.confidence_after, 4),
            "confidenceDrop": round(self.confidence_drop, 4),
            "triggerIndicators": self.trigger_indicators,
            "createdAt": self.created_at
        }


@dataclass
class RegimeConfig:
    """Configuration for regime classification"""
    
    # Thresholds for regime classification
    trending_threshold: float = 0.65        # trend_strength above this = TRENDING
    range_threshold: float = 0.35           # trend_strength below this = RANGE candidate
    high_vol_threshold: float = 0.70        # volatility above this = HIGH_VOL
    low_vol_threshold: float = 0.30         # volatility below this = LOW_VOL
    compression_threshold: float = 0.65     # compression above this = compressed
    
    # Confidence thresholds
    min_confidence_for_stable: float = 0.60  # Below this = TRANSITION candidate
    stability_lookback: int = 5              # Bars to check for stability
    
    # Feature weights for confidence
    feature_weights: Dict[str, float] = field(default_factory=lambda: {
        "trend_strength": 0.25,
        "volatility_level": 0.20,
        "range_compression": 0.15,
        "structure_clarity": 0.25,
        "breakout_pressure": 0.15
    })
    
    # Indicator periods
    atr_period: int = 14
    atr_sma_period: int = 14
    ma_short_period: int = 20
    ma_long_period: int = 50
    slope_period: int = 10
    structure_lookback: int = 20
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trendingThreshold": self.trending_threshold,
            "rangeThreshold": self.range_threshold,
            "highVolThreshold": self.high_vol_threshold,
            "lowVolThreshold": self.low_vol_threshold,
            "compressionThreshold": self.compression_threshold,
            "minConfidenceForStable": self.min_confidence_for_stable,
            "stabilityLookback": self.stability_lookback,
            "featureWeights": self.feature_weights,
            "indicatorPeriods": {
                "atr": self.atr_period,
                "atrSma": self.atr_sma_period,
                "maShort": self.ma_short_period,
                "maLong": self.ma_long_period,
                "slope": self.slope_period,
                "structureLookback": self.structure_lookback
            }
        }
