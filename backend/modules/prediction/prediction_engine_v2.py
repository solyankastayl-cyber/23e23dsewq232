"""
Prediction Engine V2 (PHASE 2.2)

Decision-based prediction using confluence, quality, and regime signals.

KEY PRINCIPLES:
1. Direction from confluence (not pattern alone)
2. Confidence from quality signals (multiplicative)
3. WAIT/NO TRADE if low quality
4. Structural targets (not guessing)
5. Regime-aware adjustments

CRITICAL:
- DO NOT force predictions
- WAIT if uncertain
- Quality > Quantity
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple


@dataclass
class PredictionResultV2:
    """Enhanced prediction result with tradeability."""
    direction: str          # LONG / SHORT / NEUTRAL / WAIT
    direction_score: float  # Raw score before thresholding
    confidence: float       # 0.0 - 1.0 (quality-based)
    target: Optional[float]
    invalidation: Optional[float]
    expected_return: float
    tradeable: bool
    reason: str
    regime: str
    model: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": {
                "label": self.direction.lower() if self.direction in ["LONG", "SHORT"] else self.direction.lower(),
                "strength": abs(self.direction_score),
                "score": self.direction_score,
            },
            "target": {
                "start_price": self.invalidation or 0,  # For backward compat
                "target_price": self.target or 0,
                "expected_return": self.expected_return,
            },
            "confidence": {
                "value": self.confidence,
                "label": self._confidence_label(),
            },
            "tradeable": self.tradeable,
            "reason": self.reason,
            "regime": self.regime,
            "model": self.model,
        }
    
    def _confidence_label(self) -> str:
        if self.confidence >= 0.7:
            return "HIGH"
        elif self.confidence >= 0.5:
            return "MEDIUM"
        elif self.confidence >= 0.35:
            return "LOW"
        else:
            return "VERY_LOW"


class PredictionEngineV2:
    """
    Decision-based prediction engine.
    
    Uses 45+ feature signals from expanded adapter:
    - confluence (bullish_score, bearish_score, agreement, conflict)
    - quality (setup_quality, pattern_quality, breakout_quality, noise)
    - structure (regime, trend_direction, hh_hl_lh_ll, compression)
    - indicators (trend_bias, momentum_bias, volatility_state)
    """
    
    def __init__(self):
        # Thresholds (can be calibrated)
        self.direction_threshold = 0.12  # Min score to take direction
        self.min_confidence = 0.30       # Min confidence to trade
        self.max_conflict = 0.65         # Max conflict before WAIT
        self.max_noise = 0.75            # Max noise before WAIT
        self.min_quality = 0.35          # Min setup quality to trade
        
        # Target multipliers by regime
        self.target_multipliers = {
            "trend": 1.0,
            "range": 0.7,
            "compression": 1.2,
            "high_volatility": 0.8,
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # MAIN ENTRY
    # ═══════════════════════════════════════════════════════════════════
    
    def build_prediction(self, features: Dict[str, Any]) -> PredictionResultV2:
        """
        Build prediction from expanded feature set.
        
        Args:
            features: Dict with pattern, structure, indicators, confluence, quality
        
        Returns:
            PredictionResultV2 with direction, confidence, targets, tradeability
        """
        # Extract feature blocks
        pattern = features.get("pattern", {})
        structure = features.get("structure", {})
        indicators = features.get("indicators", {})
        confluence = features.get("confluence", {})
        quality = features.get("quality", {})
        price = float(features.get("price", 0))
        
        # Flatten for easier access
        f = self._flatten_features(pattern, structure, indicators, confluence, quality, price)
        
        # 1. Compute direction
        direction, direction_score = self._compute_direction(f)
        
        # 2. Compute confidence (quality-based)
        confidence = self._compute_confidence(f)
        
        # 3. Check tradeability
        tradeable, reason = self._compute_tradeability(f, confidence, direction)
        
        # 4. Compute targets (if tradeable)
        if tradeable and direction in ["LONG", "SHORT"]:
            target, invalidation = self._compute_targets(f, direction, price)
            expected_return = self._compute_expected_return(price, target)
        else:
            target = None
            invalidation = None
            expected_return = 0.0
        
        # 5. Get regime
        regime = self._detect_regime(f)
        model = self._select_model(regime)
        
        # 6. Apply regime modifier
        result = PredictionResultV2(
            direction=direction,
            direction_score=direction_score,
            confidence=confidence,
            target=target,
            invalidation=invalidation,
            expected_return=expected_return,
            tradeable=tradeable,
            reason=reason,
            regime=regime,
            model=model,
        )
        
        result = self._apply_regime_modifier(result, f)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # FEATURE FLATTENING
    # ═══════════════════════════════════════════════════════════════════
    
    def _flatten_features(
        self,
        pattern: Dict,
        structure: Dict,
        indicators: Dict,
        confluence: Dict,
        quality: Dict,
        price: float
    ) -> Dict[str, Any]:
        """Flatten all feature blocks into single dict for easy access."""
        return {
            # Price
            "price": price,
            
            # Pattern
            "pattern_type": pattern.get("type", "none"),
            "pattern_family": pattern.get("family", "none"),
            "pattern_direction": pattern.get("direction", "neutral"),
            "pattern_confidence": float(pattern.get("confidence", 0)),
            "pattern_lifecycle": pattern.get("lifecycle", "none"),
            "pattern_maturity": float(pattern.get("maturity", 0)),
            "breakout_level": pattern.get("breakout_level"),
            "invalidation_level": pattern.get("invalidation_level"),
            "range_width": float(pattern.get("range_width", 0)),
            "pattern_height": float(pattern.get("pattern_height", 0)),
            "touch_count": int(pattern.get("touch_count", 0)),
            
            # Structure
            "regime": structure.get("regime", "range"),
            "trend_direction": structure.get("trend_direction", "flat"),
            "trend_strength": float(structure.get("trend_strength", 0)),
            "range_score": float(structure.get("range_score", 0.5)),
            "compression_score": float(structure.get("compression_score", 0)),
            "volatility_score": float(structure.get("volatility_score", 0.5)),
            "hh_count": int(structure.get("hh_count", 0)),
            "hl_count": int(structure.get("hl_count", 0)),
            "lh_count": int(structure.get("lh_count", 0)),
            "ll_count": int(structure.get("ll_count", 0)),
            "last_event": structure.get("last_event", "none"),
            "market_phase": structure.get("market_phase", "range"),
            
            # Indicators
            "trend_bias": float(indicators.get("trend_bias", 0)),
            "momentum_bias": float(indicators.get("momentum_bias", 0)),
            "volatility_state": indicators.get("volatility_state", "normal"),
            "volume_support": float(indicators.get("volume_support", 0.5)),
            "rsi": indicators.get("rsi"),
            "macd_histogram": indicators.get("macd_histogram"),
            
            # Confluence
            "bullish_score": float(confluence.get("bullish_score", 0)),
            "bearish_score": float(confluence.get("bearish_score", 0)),
            "agreement": float(confluence.get("agreement", 0.5)),
            "conflict_score": float(confluence.get("conflict_score", 0)),
            
            # Quality
            "setup_quality": float(quality.get("setup_quality", 0.5)),
            "pattern_quality": float(quality.get("pattern_quality", 0.5)),
            "breakout_quality": float(quality.get("breakout_quality", 0.5)),
            "noise_score": float(quality.get("noise_score", 0.5)),
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # DIRECTION ENGINE
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_direction(self, f: Dict) -> Tuple[str, float]:
        """
        Compute direction from confluence signals.
        
        Uses: bullish_score, bearish_score, agreement, conflict, quality
        
        Returns: (direction, score)
        """
        bullish = f["bullish_score"]
        bearish = f["bearish_score"]
        agreement = f["agreement"]
        conflict = f["conflict_score"]
        quality = f["setup_quality"]
        
        # Base direction score
        direction_score = bullish - bearish
        
        # Amplify by agreement (aligned signals = stronger)
        direction_score *= (0.5 + agreement * 0.5)  # 0.5-1.0 multiplier
        
        # Amplify by quality
        direction_score *= (0.5 + quality * 0.5)  # 0.5-1.0 multiplier
        
        # Penalize conflict
        direction_score *= (1 - conflict * 0.5)  # 0.5-1.0 multiplier
        
        # Structure confirmation bonus
        trend_dir = f["trend_direction"]
        hh = f["hh_count"]
        hl = f["hl_count"]
        lh = f["lh_count"]
        ll = f["ll_count"]
        
        # Bullish structure: HH + HL
        if hh + hl > lh + ll and direction_score > 0:
            direction_score *= 1.1
        # Bearish structure: LH + LL
        elif lh + ll > hh + hl and direction_score < 0:
            direction_score *= 1.1
        # Structure conflict
        elif (hh + hl > lh + ll and direction_score < 0) or \
             (lh + ll > hh + hl and direction_score > 0):
            direction_score *= 0.8
        
        # Momentum alignment bonus
        momentum = f["momentum_bias"]
        if (direction_score > 0 and momentum > 0.1) or \
           (direction_score < 0 and momentum < -0.1):
            direction_score *= 1.05
        
        # Decision
        if abs(direction_score) < self.direction_threshold:
            return "NEUTRAL", direction_score
        
        if direction_score > 0:
            return "LONG", direction_score
        else:
            return "SHORT", direction_score
    
    # ═══════════════════════════════════════════════════════════════════
    # CONFIDENCE ENGINE
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_confidence(self, f: Dict) -> float:
        """
        Compute confidence from quality signals.
        
        Multiplicative formula:
        confidence = agreement * setup_quality * pattern_quality * breakout_quality * (1 - noise)
        """
        agreement = f["agreement"]
        setup_quality = f["setup_quality"]
        pattern_quality = f["pattern_quality"]
        breakout_quality = f["breakout_quality"]
        noise = f["noise_score"]
        
        # Base confidence (multiplicative)
        confidence = (
            agreement *
            setup_quality *
            (0.5 + pattern_quality * 0.5) *  # Pattern optional boost
            (0.5 + breakout_quality * 0.5) * # Breakout optional boost
            (1 - noise * 0.7)                # Noise penalty
        )
        
        # Volume support bonus
        volume = f["volume_support"]
        if volume > 0.6:
            confidence *= 1.1
        
        # Pattern lifecycle bonus
        lifecycle = f["pattern_lifecycle"]
        if lifecycle == "confirmed":
            confidence *= 1.15
        elif lifecycle == "forming":
            confidence *= 0.95
        
        # RSI extreme penalty
        rsi = f["rsi"]
        if rsi is not None:
            if rsi > 80 or rsi < 20:
                confidence *= 0.85  # Extreme RSI = less reliable
        
        return round(max(0.0, min(confidence, 1.0)), 3)
    
    # ═══════════════════════════════════════════════════════════════════
    # TRADEABILITY FILTER
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_tradeability(
        self,
        f: Dict,
        confidence: float,
        direction: str
    ) -> Tuple[bool, str]:
        """
        Determine if setup is tradeable.
        
        CRITICAL: Better to miss trades than take bad ones.
        """
        # Direction check
        if direction in ["NEUTRAL", "WAIT"]:
            return False, "No clear direction"
        
        # Confidence check
        if confidence < self.min_confidence:
            return False, f"Low confidence ({confidence:.2f} < {self.min_confidence})"
        
        # Conflict check
        conflict = f["conflict_score"]
        if conflict > self.max_conflict:
            return False, f"High conflict ({conflict:.2f} > {self.max_conflict})"
        
        # Noise check
        noise = f["noise_score"]
        if noise > self.max_noise:
            return False, f"Too noisy ({noise:.2f} > {self.max_noise})"
        
        # Quality check
        quality = f["setup_quality"]
        if quality < self.min_quality:
            return False, f"Low quality ({quality:.2f} < {self.min_quality})"
        
        # Compression wait
        compression = f["compression_score"]
        if compression > 0.75:
            return False, "Compression - waiting for expansion"
        
        # Extreme volatility
        vol_state = f["volatility_state"]
        if vol_state == "high" and confidence < 0.5:
            return False, "High volatility with low confidence"
        
        return True, "Valid setup"
    
    # ═══════════════════════════════════════════════════════════════════
    # TARGET ENGINE
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_targets(
        self,
        f: Dict,
        direction: str,
        price: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Compute structural targets.
        
        Uses: breakout_level, invalidation_level, range_width, regime
        
        FIX: Reduced target sizing - was 4-5%, now 2-3.5%
        """
        breakout = f["breakout_level"]
        invalidation = f["invalidation_level"]
        range_width = f["range_width"]
        regime = f["regime"]
        
        # Get regime multiplier (REDUCED)
        multiplier = {
            "trend": 0.7,       # Was 1.0
            "range": 0.5,       # Was 0.7
            "compression": 0.8, # Was 1.2
            "high_volatility": 0.6,  # Was 0.8
        }.get(regime, 0.6)
        
        # Use pattern levels if available
        if breakout and invalidation:
            # Use smaller fraction of range_width
            target_move = range_width * multiplier * 0.5  # Added 0.5 factor
            
            if direction == "LONG":
                target = breakout + target_move
                stop = invalidation
            else:
                target = breakout - target_move
                stop = invalidation
            
            return round(target, 2), round(stop, 2)
        
        # Fallback: CONSERVATIVE estimate (2-3.5%)
        trend_strength = f["trend_strength"]
        momentum = f["momentum_bias"]
        
        # REDUCED: Base move now 2-3.5% (was 3-6%)
        base_move = 0.02 + abs(trend_strength) * 0.01 + abs(momentum) * 0.005
        base_move *= multiplier
        base_move = min(base_move, 0.035)  # Cap at 3.5% (was 10%)
        
        if direction == "LONG":
            target = price * (1 + base_move)
            stop = price * (1 - base_move * 0.5)  # 2:1 risk/reward
        else:
            target = price * (1 - base_move)
            stop = price * (1 + base_move * 0.5)
        
        return round(target, 2), round(stop, 2)
    
    def _compute_expected_return(self, price: float, target: Optional[float]) -> float:
        """Compute expected return percentage."""
        if not target or not price:
            return 0.0
        return round((target - price) / price, 4)
    
    # ═══════════════════════════════════════════════════════════════════
    # REGIME DETECTION & MODIFIER
    # ═══════════════════════════════════════════════════════════════════
    
    def _detect_regime(self, f: Dict) -> str:
        """Detect market regime from structure."""
        regime = f["regime"]
        trend_strength = f["trend_strength"]
        compression = f["compression_score"]
        range_score = f["range_score"]
        vol_state = f["volatility_state"]
        
        # High volatility override
        if vol_state == "high":
            return "high_volatility"
        
        # Compression override
        if compression > 0.6:
            return "compression"
        
        # Strong trend
        if abs(trend_strength) > 0.04:
            return "trend"
        
        # Range
        if range_score > 0.6:
            return "range"
        
        return regime
    
    def _select_model(self, regime: str) -> str:
        """Select model name based on regime."""
        return {
            "trend": "trend_momentum_v2",
            "range": "range_mean_reversion_v2",
            "compression": "compression_breakout_v2",
            "high_volatility": "high_vol_momentum_v2",
        }.get(regime, "fallback_v2")
    
    def _apply_regime_modifier(
        self,
        result: PredictionResultV2,
        f: Dict
    ) -> PredictionResultV2:
        """Apply regime-specific adjustments."""
        regime = result.regime
        market_phase = f["market_phase"]
        compression = f["compression_score"]
        
        # Range regime - reduce breakout confidence
        if regime == "range" and f["pattern_family"] not in ["range", "reversal"]:
            result.confidence *= 0.85
            if result.confidence < self.min_confidence:
                result.tradeable = False
                result.reason = "Range regime with non-range pattern"
        
        # Trend regime - boost continuation
        if regime == "trend":
            trend_dir = f["trend_direction"]
            if (result.direction == "LONG" and trend_dir == "up") or \
               (result.direction == "SHORT" and trend_dir == "down"):
                result.confidence *= 1.1
                result.confidence = min(result.confidence, 1.0)
        
        # Compression - special handling
        if compression > 0.75:
            result.direction = "WAIT"
            result.tradeable = False
            result.reason = "Compression - waiting for expansion"
        
        # Markdown phase with bullish signal - cautious
        if market_phase == "markdown" and result.direction == "LONG":
            result.confidence *= 0.85
        
        # Markup phase with bearish signal - cautious
        if market_phase == "markup" and result.direction == "SHORT":
            result.confidence *= 0.85
        
        result.confidence = round(result.confidence, 3)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY WRAPPER
# ═══════════════════════════════════════════════════════════════════════════

_engine_v2 = None

def get_prediction_engine_v2() -> PredictionEngineV2:
    """Get singleton instance."""
    global _engine_v2
    if _engine_v2 is None:
        _engine_v2 = PredictionEngineV2()
    return _engine_v2


def build_prediction_v2(features: Dict[str, Any]) -> Dict[str, Any]:
    """Build prediction using V2 engine."""
    engine = get_prediction_engine_v2()
    result = engine.build_prediction(features)
    return result.to_dict()


def build_prediction_regime_aware(
    pred_input: Dict[str, Any],
    prev_regime: str = None
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for prediction_engine_v3 interface.
    
    Now uses V2 decision-based engine.
    """
    # Check if input has expanded features
    has_confluence = "confluence" in pred_input or "bullish_score" in pred_input.get("confluence", {})
    has_quality = "quality" in pred_input or "setup_quality" in pred_input.get("quality", {})
    
    if has_confluence and has_quality:
        # Use V2 engine with expanded features
        return build_prediction_v2(pred_input)
    
    # Fallback to old logic for non-expanded inputs
    from modules.prediction.prediction_engine_v3 import build_prediction_v3
    return build_prediction_v3(pred_input, prev_regime)
