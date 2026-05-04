"""
Regime Confidence Calculator
============================

Calculates confidence, stability, and transition risk metrics.
"""

from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass

from .regime_types import (
    MarketRegimeType,
    RegimeFeatureSet,
    RegimeState,
    RegimeConfig
)


@dataclass
class ConfidenceMetrics:
    """Confidence calculation result"""
    confidence: float = 0.0
    stability_score: float = 0.0
    transition_risk: float = 0.0
    components: Dict[str, float] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = {}


class RegimeConfidenceCalculator:
    """
    Calculates regime confidence metrics.
    
    Answers:
    - How confident are we in the classification?
    - How stable is this regime?
    - What's the risk of regime transition?
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
        
        # History for stability calculation
        self._regime_history: Dict[str, deque] = {}  # symbol -> recent regimes
        self._feature_history: Dict[str, deque] = {}  # symbol -> recent features
        
        self._max_history = 20
    
    def calculate_confidence(
        self,
        regime: MarketRegimeType,
        features: RegimeFeatureSet,
        probabilities: Dict[str, float]
    ) -> ConfidenceMetrics:
        """
        Calculate confidence metrics for classification.
        """
        
        components = {}
        
        # 1. Probability margin
        # How much higher is the top regime vs second?
        sorted_probs = sorted(probabilities.values(), reverse=True)
        if len(sorted_probs) >= 2:
            margin = sorted_probs[0] - sorted_probs[1]
            margin_confidence = min(margin * 3, 1.0)  # 33%+ margin = full confidence
        else:
            margin_confidence = 0.5
        components['margin'] = margin_confidence
        
        # 2. Feature clarity
        # Do the features strongly support this regime?
        feature_confidence = self._compute_feature_confidence(regime, features)
        components['features'] = feature_confidence
        
        # 3. No conflicting signals
        conflict_penalty = self._compute_conflict_penalty(features)
        components['conflict_penalty'] = conflict_penalty
        
        # Combine for overall confidence
        confidence = (
            margin_confidence * 0.35 +
            feature_confidence * 0.45 +
            (1 - conflict_penalty) * 0.20
        )
        
        # Calculate stability
        stability = self._calculate_stability(features.symbol, regime)
        components['stability'] = stability
        
        # Calculate transition risk
        transition_risk = self._calculate_transition_risk(
            features, confidence, regime
        )
        components['transition_risk'] = transition_risk
        
        # Update history
        self._update_history(features.symbol, regime, features)
        
        return ConfidenceMetrics(
            confidence=round(confidence, 4),
            stability_score=round(stability, 4),
            transition_risk=round(transition_risk, 4),
            components={k: round(v, 4) for k, v in components.items()}
        )
    
    def _compute_feature_confidence(
        self,
        regime: MarketRegimeType,
        features: RegimeFeatureSet
    ) -> float:
        """Compute how well features support the regime"""
        
        if regime == MarketRegimeType.TRENDING:
            # High trend strength + structure clarity = high confidence
            score = (
                features.trend_strength * 0.4 +
                features.structure_clarity * 0.3 +
                features.directional_consistency * 0.2 +
                features.ma_separation * 0.1
            )
            # Penalize if compressed
            if features.range_compression > 0.5:
                score *= 0.8
            return score
        
        elif regime == MarketRegimeType.RANGE:
            # Low trend + stable vol = high confidence
            score = (
                (1 - features.trend_strength) * 0.35 +
                (1 - features.directional_consistency) * 0.25 +
                (1 - abs(features.volatility_level - 0.5) * 2) * 0.20 +  # Moderate vol
                features.structure_clarity * 0.20
            )
            return score
        
        elif regime == MarketRegimeType.HIGH_VOLATILITY:
            # High vol + high ATR = high confidence
            score = (
                features.volatility_level * 0.45 +
                min(features.atr_ratio / 2, 1.0) * 0.35 +
                (1 - features.range_compression) * 0.20
            )
            return score
        
        elif regime == MarketRegimeType.LOW_VOLATILITY:
            # Low vol + compression = high confidence
            score = (
                (1 - features.volatility_level) * 0.35 +
                features.range_compression * 0.35 +
                max(0, 1 - features.atr_ratio) * 0.30
            )
            return score
        
        elif regime == MarketRegimeType.TRANSITION:
            # Transition confidence is based on conflict level
            conflict = self._compute_conflict_penalty(features)
            score = conflict * 0.6 + (1 - features.structure_clarity) * 0.4
            return score
        
        return 0.5
    
    def _compute_conflict_penalty(self, features: RegimeFeatureSet) -> float:
        """Compute penalty for conflicting signals"""
        
        conflicts = 0.0
        
        # Trend vs compression
        if features.trend_strength > 0.6 and features.range_compression > 0.6:
            conflicts += 0.25
        
        # High vol with compression
        if features.volatility_level > 0.6 and features.range_compression > 0.6:
            conflicts += 0.20
        
        # Direction inconsistency with trend
        if features.directional_consistency < 0.5 and features.trend_strength > 0.5:
            conflicts += 0.20
        
        # Structure clarity mismatch
        if features.structure_clarity > 0.6 and features.trend_strength < 0.3:
            conflicts += 0.15
        
        # Breakout pressure with no volatility
        if features.breakout_pressure > 0.6 and features.volatility_level < 0.3:
            conflicts += 0.15
        
        return min(conflicts, 1.0)
    
    def _calculate_stability(self, symbol: str, current_regime: MarketRegimeType) -> float:
        """
        Calculate regime stability based on history.
        
        High stability = same regime for several bars.
        """
        
        key = f"{symbol}"
        
        if key not in self._regime_history:
            return 0.5  # No history = neutral stability
        
        history = list(self._regime_history[key])
        
        if len(history) < 3:
            return 0.5
        
        # Count how many recent bars had same regime
        same_count = sum(1 for r in history[-self.config.stability_lookback:] if r == current_regime)
        total = min(len(history), self.config.stability_lookback)
        
        stability = same_count / total
        
        return stability
    
    def _calculate_transition_risk(
        self,
        features: RegimeFeatureSet,
        confidence: float,
        current_regime: MarketRegimeType
    ) -> float:
        """
        Calculate risk of imminent regime transition.
        
        High risk when:
        - Low confidence
        - Features changing rapidly
        - Breakout pressure building
        """
        
        risk_factors = []
        
        # Factor 1: Low confidence
        confidence_risk = max(0, 1 - confidence * 1.3)  # 77%+ confidence = 0 risk
        risk_factors.append(confidence_risk * 0.30)
        
        # Factor 2: Breakout pressure (especially in LOW_VOL or RANGE)
        if current_regime in [MarketRegimeType.LOW_VOLATILITY, MarketRegimeType.RANGE]:
            pressure_risk = features.breakout_pressure * 0.5
        else:
            pressure_risk = features.breakout_pressure * 0.2
        risk_factors.append(pressure_risk)
        
        # Factor 3: Volatility change
        if current_regime == MarketRegimeType.LOW_VOLATILITY:
            # Risk of vol expansion
            if features.atr_ratio > 0.8:
                risk_factors.append(0.15)
        elif current_regime == MarketRegimeType.HIGH_VOLATILITY:
            # Risk of vol compression
            if features.atr_ratio < 1.2:
                risk_factors.append(0.15)
        
        # Factor 4: Structure degradation for trending
        if current_regime == MarketRegimeType.TRENDING:
            if features.structure_clarity < 0.5:
                risk_factors.append(0.20)
        
        # Factor 5: Feature instability from history
        key = f"{features.symbol}"
        if key in self._feature_history and len(self._feature_history[key]) >= 3:
            feature_volatility = self._compute_feature_volatility(key)
            risk_factors.append(feature_volatility * 0.20)
        
        return min(sum(risk_factors), 1.0)
    
    def _compute_feature_volatility(self, key: str) -> float:
        """Compute how much features are changing"""
        
        history = list(self._feature_history[key])
        if len(history) < 3:
            return 0.3
        
        recent = history[-3:]
        
        # Check variance in key features
        trend_var = self._variance([f.trend_strength for f in recent])
        vol_var = self._variance([f.volatility_level for f in recent])
        comp_var = self._variance([f.range_compression for f in recent])
        
        avg_var = (trend_var + vol_var + comp_var) / 3
        
        # Normalize (0.1 variance = high instability)
        return min(avg_var / 0.1, 1.0)
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)
    
    def _update_history(
        self,
        symbol: str,
        regime: MarketRegimeType,
        features: RegimeFeatureSet
    ):
        """Update history for stability calculations"""
        
        key = f"{symbol}"
        
        # Regime history
        if key not in self._regime_history:
            self._regime_history[key] = deque(maxlen=self._max_history)
        self._regime_history[key].append(regime)
        
        # Feature history
        if key not in self._feature_history:
            self._feature_history[key] = deque(maxlen=self._max_history)
        self._feature_history[key].append(features)
    
    def get_regime_history(self, symbol: str, limit: int = 10) -> List[str]:
        """Get recent regime history for symbol"""
        key = f"{symbol}"
        if key not in self._regime_history:
            return []
        return [r.value for r in list(self._regime_history[key])[-limit:]]
    
    def clear_history(self, symbol: Optional[str] = None):
        """Clear history for a symbol or all"""
        if symbol:
            key = f"{symbol}"
            self._regime_history.pop(key, None)
            self._feature_history.pop(key, None)
        else:
            self._regime_history.clear()
            self._feature_history.clear()


# Global calculator instance
confidence_calculator = RegimeConfidenceCalculator()
