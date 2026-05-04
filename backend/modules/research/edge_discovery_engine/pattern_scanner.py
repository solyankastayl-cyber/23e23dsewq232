"""
PHASE 6.4 - Pattern Scanner
============================
Scans market data for specific patterns.
"""

import random
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .edge_types import PatternType, PatternMatch, MarketFeatures
from .feature_extractor import FeatureExtractor


class PatternScanner:
    """
    Scans market data for trading patterns.
    """
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.pattern_configs = self._init_pattern_configs()
    
    def _init_pattern_configs(self) -> Dict[PatternType, Dict]:
        """Initialize pattern detection configurations"""
        return {
            PatternType.VOLATILITY_COMPRESSION: {
                "feature": "volatility_percentile",
                "condition": lambda x: x < 0.2,
                "min_duration": 5,
                "description": "Low volatility compression"
            },
            PatternType.VOLUME_ANOMALY: {
                "feature": "volume_spike",
                "condition": lambda x: x > 2.0,
                "min_duration": 1,
                "description": "Volume spike above 2x average"
            },
            PatternType.LIQUIDITY_EVENT: {
                "feature": "liquidity_score",
                "condition": lambda x: x < 0.3,
                "min_duration": 1,
                "description": "Low liquidity event"
            },
            PatternType.STRUCTURE_SHIFT: {
                "feature": "structure_type",
                "condition": lambda x: True,  # Checked separately
                "min_duration": 1,
                "description": "Market structure shift"
            },
            PatternType.FUNDING_EXTREME: {
                "feature": "funding_rate_zscore",
                "condition": lambda x: abs(x) > 1.5,
                "min_duration": 1,
                "description": "Extreme funding rate"
            },
            PatternType.ORDERBOOK_IMBALANCE: {
                "feature": "orderbook_imbalance",
                "condition": lambda x: abs(x) > 0.3,
                "min_duration": 1,
                "description": "Orderbook imbalance"
            },
            PatternType.PRICE_PATTERN: {
                "feature": "price_momentum",
                "condition": lambda x: abs(x) > 0.03,
                "min_duration": 1,
                "description": "Strong price movement"
            }
        }
    
    def scan(
        self,
        candles: List[Dict],
        pattern_types: List[PatternType] = None,
        min_confidence: float = 0.5
    ) -> List[PatternMatch]:
        """
        Scan candles for specified patterns.
        
        Args:
            candles: OHLCV data
            pattern_types: Types to scan for (None = all)
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of detected patterns
        """
        if pattern_types is None:
            pattern_types = list(PatternType)
        
        matches = []
        
        # Extract features for all candles
        features_list = self.feature_extractor.extract_features_batch(candles)
        
        for i, features in enumerate(features_list):
            candle_idx = i + self.feature_extractor.lookback_period
            
            for pattern_type in pattern_types:
                match = self._check_pattern(
                    pattern_type=pattern_type,
                    features=features,
                    candle_idx=candle_idx,
                    candles=candles
                )
                
                if match and match.confidence >= min_confidence:
                    matches.append(match)
        
        return matches
    
    def _check_pattern(
        self,
        pattern_type: PatternType,
        features: MarketFeatures,
        candle_idx: int,
        candles: List[Dict]
    ) -> Optional[PatternMatch]:
        """Check if a specific pattern exists"""
        
        config = self.pattern_configs.get(pattern_type)
        if not config:
            return None
        
        feature_name = config["feature"]
        condition = config["condition"]
        
        # Get feature value
        feature_value = getattr(features, feature_name, None)
        if feature_value is None:
            return None
        
        # Check condition
        if not condition(feature_value):
            return None
        
        # Calculate confidence
        confidence = self._calculate_pattern_confidence(
            pattern_type, features, candle_idx, candles
        )
        
        # Calculate outcome (for historical data)
        outcome_dir, outcome_ret = self._calculate_outcome(
            candle_idx, candles, lookforward=10
        )
        
        return PatternMatch(
            pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
            pattern_type=pattern_type,
            timestamp=features.timestamp,
            features=features,
            confidence=confidence,
            outcome_direction=outcome_dir,
            outcome_return=outcome_ret
        )
    
    def _calculate_pattern_confidence(
        self,
        pattern_type: PatternType,
        features: MarketFeatures,
        candle_idx: int,
        candles: List[Dict]
    ) -> float:
        """Calculate confidence score for pattern"""
        
        base_confidence = 0.5
        
        # Adjust based on pattern type specifics
        if pattern_type == PatternType.VOLATILITY_COMPRESSION:
            # Lower volatility = higher confidence
            base_confidence = 1.0 - features.volatility_percentile
            
        elif pattern_type == PatternType.VOLUME_ANOMALY:
            # Higher spike = higher confidence (capped)
            base_confidence = min(0.9, features.volume_spike / 4)
            
        elif pattern_type == PatternType.LIQUIDITY_EVENT:
            # Lower liquidity = higher confidence
            base_confidence = 1.0 - features.liquidity_score
            
        elif pattern_type == PatternType.FUNDING_EXTREME:
            # Higher z-score = higher confidence
            base_confidence = min(0.9, abs(features.funding_rate_zscore) / 3)
            
        elif pattern_type == PatternType.ORDERBOOK_IMBALANCE:
            base_confidence = min(0.9, abs(features.orderbook_imbalance) * 1.5)
            
        elif pattern_type == PatternType.PRICE_PATTERN:
            base_confidence = min(0.9, abs(features.price_momentum) * 10)
        
        # Add small random variation
        noise = random.uniform(-0.05, 0.05)
        
        return max(0.1, min(0.95, base_confidence + noise))
    
    def _calculate_outcome(
        self,
        candle_idx: int,
        candles: List[Dict],
        lookforward: int = 10
    ) -> Tuple[str, float]:
        """Calculate outcome after pattern (for historical validation)"""
        
        if candle_idx + lookforward >= len(candles):
            return None, None
        
        entry_price = candles[candle_idx]['close']
        future_prices = [c['close'] for c in candles[candle_idx:candle_idx + lookforward]]
        
        max_price = max(future_prices)
        min_price = min(future_prices)
        final_price = future_prices[-1]
        
        # Calculate return
        return_pct = (final_price - entry_price) / entry_price
        
        # Determine direction
        if return_pct > 0.01:
            direction = "LONG"
        elif return_pct < -0.01:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
        
        return direction, return_pct
    
    def scan_for_specific_pattern(
        self,
        candles: List[Dict],
        pattern_type: PatternType
    ) -> List[PatternMatch]:
        """Scan for a specific pattern type"""
        return self.scan(candles, pattern_types=[pattern_type])
    
    def get_pattern_summary(
        self,
        matches: List[PatternMatch]
    ) -> Dict:
        """Summarize pattern matches"""
        if not matches:
            return {"total": 0, "by_type": {}}
        
        by_type = {}
        for match in matches:
            ptype = match.pattern_type.value if hasattr(match.pattern_type, 'value') else str(match.pattern_type)
            if ptype not in by_type:
                by_type[ptype] = {
                    "count": 0,
                    "avg_confidence": 0,
                    "win_count": 0,
                    "loss_count": 0
                }
            
            by_type[ptype]["count"] += 1
            by_type[ptype]["avg_confidence"] += match.confidence
            
            if match.outcome_return:
                if match.outcome_return > 0:
                    by_type[ptype]["win_count"] += 1
                else:
                    by_type[ptype]["loss_count"] += 1
        
        # Calculate averages
        for ptype in by_type:
            count = by_type[ptype]["count"]
            by_type[ptype]["avg_confidence"] /= count
            
            total_outcomes = by_type[ptype]["win_count"] + by_type[ptype]["loss_count"]
            if total_outcomes > 0:
                by_type[ptype]["win_rate"] = by_type[ptype]["win_count"] / total_outcomes
        
        return {
            "total": len(matches),
            "by_type": by_type
        }
