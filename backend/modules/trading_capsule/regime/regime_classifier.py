"""
Regime Classifier
=================

Rule-based classifier for market regimes.
"""

from typing import Dict, List, Tuple, Optional
from .regime_types import (
    MarketRegimeType,
    RegimeState,
    RegimeFeatureSet,
    RegimeConfig
)


class RegimeClassifier:
    """
    Rule-based regime classifier.
    
    Classifies market into one of 5 regimes based on features:
    - TRENDING
    - RANGE
    - HIGH_VOLATILITY
    - LOW_VOLATILITY
    - TRANSITION
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
    
    def classify(self, features: RegimeFeatureSet) -> Tuple[MarketRegimeType, Dict[str, float], List[str]]:
        """
        Classify regime based on features.
        
        Returns:
        - Primary regime classification
        - Probability distribution across regimes
        - Reasons for classification
        """
        
        # Calculate scores for each regime
        scores = self._compute_regime_scores(features)
        
        # Normalize to probabilities
        total = sum(scores.values())
        probabilities = {k: v / total for k, v in scores.items()} if total > 0 else scores
        
        # Get primary classification
        primary_regime, reasons = self._determine_primary_regime(features, scores)
        
        return primary_regime, probabilities, reasons
    
    def _compute_regime_scores(self, features: RegimeFeatureSet) -> Dict[str, float]:
        """Compute raw scores for each regime"""
        
        scores = {
            MarketRegimeType.TRENDING.value: 0.0,
            MarketRegimeType.RANGE.value: 0.0,
            MarketRegimeType.HIGH_VOLATILITY.value: 0.0,
            MarketRegimeType.LOW_VOLATILITY.value: 0.0,
            MarketRegimeType.TRANSITION.value: 0.0
        }
        
        # TRENDING score
        # High trend strength + high structure clarity + not low volatility compression
        trending_score = (
            features.trend_strength * 0.40 +
            features.structure_clarity * 0.30 +
            features.directional_consistency * 0.15 +
            features.ma_separation * 0.15
        )
        # Penalty for compression (trending doesn't happen in tight ranges)
        if features.range_compression > 0.7:
            trending_score *= 0.6
        scores[MarketRegimeType.TRENDING.value] = trending_score
        
        # RANGE score
        # Low trend strength + moderate volatility + clear swing structure
        range_score = (
            (1 - features.trend_strength) * 0.35 +
            (1 - features.directional_consistency) * 0.25 +
            features.structure_clarity * 0.20 +  # Clear HH/LL still matter for range
            (1 - abs(features.volatility_level - 0.5) * 2) * 0.20  # Moderate vol
        )
        # Bonus for sideways structure
        if features.trend_strength < 0.4 and features.structure_clarity > 0.5:
            range_score += 0.15
        scores[MarketRegimeType.RANGE.value] = range_score
        
        # HIGH_VOLATILITY score
        # High volatility + large ATR ratio
        high_vol_score = (
            features.volatility_level * 0.45 +
            min(features.atr_ratio / 2, 1.0) * 0.30 +  # ATR ratio > 2 = very high
            (1 - features.range_compression) * 0.15 +
            features.breakout_pressure * 0.10
        )
        scores[MarketRegimeType.HIGH_VOLATILITY.value] = high_vol_score
        
        # LOW_VOLATILITY score
        # Low volatility + high compression
        low_vol_score = (
            (1 - features.volatility_level) * 0.35 +
            features.range_compression * 0.35 +
            max(0, 1 - features.atr_ratio) * 0.20 +  # ATR ratio < 1
            (1 - abs(features.candle_body_ratio - 0.3)) * 0.10  # Small bodies
        )
        scores[MarketRegimeType.LOW_VOLATILITY.value] = low_vol_score
        
        # TRANSITION score
        # Conflicting signals, low clarity
        conflict_score = self._compute_conflict_score(features)
        transition_score = (
            conflict_score * 0.40 +
            (1 - features.structure_clarity) * 0.30 +
            (1 - features.directional_consistency) * 0.20 +
            features.breakout_pressure * 0.10  # Pressure suggests change coming
        )
        scores[MarketRegimeType.TRANSITION.value] = transition_score
        
        return scores
    
    def _compute_conflict_score(self, features: RegimeFeatureSet) -> float:
        """Compute how conflicting the signals are"""
        
        conflicts = 0.0
        
        # Trend vs compression conflict
        if features.trend_strength > 0.6 and features.range_compression > 0.6:
            conflicts += 0.3
        
        # High vol with compression conflict
        if features.volatility_level > 0.6 and features.range_compression > 0.6:
            conflicts += 0.2
        
        # Low vol with trend conflict
        if features.volatility_level < 0.3 and features.trend_strength > 0.6:
            conflicts += 0.15
        
        # Inconsistent direction with high trend strength
        if features.directional_consistency < 0.6 and features.trend_strength > 0.5:
            conflicts += 0.2
        
        # Structure clarity vs trend mismatch
        if features.structure_clarity > 0.7 and features.trend_strength < 0.3:
            conflicts += 0.15
        
        return min(conflicts, 1.0)
    
    def _determine_primary_regime(
        self,
        features: RegimeFeatureSet,
        scores: Dict[str, float]
    ) -> Tuple[MarketRegimeType, List[str]]:
        """Determine primary regime with rule-based logic"""
        
        reasons = []
        
        # Check explicit conditions first
        
        # HIGH_VOLATILITY takes precedence if very high
        if features.volatility_level > self.config.high_vol_threshold:
            if features.atr_ratio > 1.5:
                reasons.append(f"Very high volatility ({features.volatility_level:.2f})")
                reasons.append(f"ATR ratio elevated ({features.atr_ratio:.2f}x)")
                return MarketRegimeType.HIGH_VOLATILITY, reasons
        
        # TRENDING if strong and clear
        if (features.trend_strength > self.config.trending_threshold and 
            features.structure_clarity > 0.5 and
            features.range_compression < 0.6):
            reasons.append(f"Strong trend ({features.trend_strength:.2f})")
            reasons.append(f"Clear structure ({features.structure_clarity:.2f})")
            if features.directional_consistency > 0.6:
                reasons.append(f"Consistent direction ({features.directional_consistency:.2f})")
            return MarketRegimeType.TRENDING, reasons
        
        # LOW_VOLATILITY if compressed
        if (features.volatility_level < self.config.low_vol_threshold and
            features.range_compression > self.config.compression_threshold):
            reasons.append(f"Low volatility ({features.volatility_level:.2f})")
            reasons.append(f"High compression ({features.range_compression:.2f})")
            if features.breakout_pressure > 0.5:
                reasons.append(f"Breakout pressure building ({features.breakout_pressure:.2f})")
            return MarketRegimeType.LOW_VOLATILITY, reasons
        
        # RANGE if no trend
        if (features.trend_strength < self.config.range_threshold and
            features.directional_consistency < 0.6 and
            features.volatility_level < 0.6):
            reasons.append(f"Low trend strength ({features.trend_strength:.2f})")
            reasons.append(f"Inconsistent direction ({features.directional_consistency:.2f})")
            return MarketRegimeType.RANGE, reasons
        
        # Check for TRANSITION (conflicting signals)
        conflict_score = self._compute_conflict_score(features)
        if conflict_score > 0.4:
            reasons.append(f"Conflicting signals detected ({conflict_score:.2f})")
            reasons.append("Market structure unclear")
            
            # Add specific conflicts
            if features.trend_strength > 0.5 and features.range_compression > 0.5:
                reasons.append("Trend vs compression conflict")
            if features.volatility_level > 0.5 and features.range_compression > 0.5:
                reasons.append("Volatility vs compression conflict")
            
            return MarketRegimeType.TRANSITION, reasons
        
        # Fall back to highest score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_regime = MarketRegimeType(sorted_scores[0][0])
        
        reasons.append(f"Highest score classification ({sorted_scores[0][1]:.2f})")
        
        # Add feature-based reasons
        if best_regime == MarketRegimeType.TRENDING:
            reasons.append(f"Trend strength: {features.trend_strength:.2f}")
        elif best_regime == MarketRegimeType.RANGE:
            reasons.append(f"Sideways structure detected")
        elif best_regime == MarketRegimeType.HIGH_VOLATILITY:
            reasons.append(f"Elevated volatility: {features.volatility_level:.2f}")
        elif best_regime == MarketRegimeType.LOW_VOLATILITY:
            reasons.append(f"Compressed range: {features.range_compression:.2f}")
        
        return best_regime, reasons


# Global classifier instance
regime_classifier = RegimeClassifier()
