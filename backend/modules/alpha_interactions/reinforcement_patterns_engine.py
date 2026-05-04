"""
PHASE 16.2 — Reinforcement Patterns Engine
============================================
Detects specific signal combinations that provide strong edge.

Patterns:
1. Trend + Momentum Alignment
2. Breakout + Volatility Expansion
3. Flow + Short Squeeze
4. Trend + Structure Break

Integration:
    reinforcement_score += pattern_strength * 0.3
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.reinforcement_patterns import (
    ReinforcementPattern,
    REINFORCEMENT_PATTERNS,
    PATTERN_WEIGHTS,
    PATTERN_MODIFIER_CONFIG,
    TrendMomentumInput,
    BreakoutVolatilityInput,
    FlowSqueezeInput,
    TrendStructureInput,
    PatternDetectionResult,
    ReinforcementPatternState,
)

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# THRESHOLDS
# ══════════════════════════════════════════════════════════════

PATTERN_THRESHOLDS = {
    "trend_momentum": {
        "trend_strength_min": 0.6,
        "momentum_strength_min": 0.5,
    },
    "breakout_volatility": {
        "breakout_strength_min": 0.5,
        "volatility_expansion_min": 0.4,
    },
    "flow_squeeze": {
        "flow_intensity_min": 0.5,
        "squeeze_probability_min": 0.5,
    },
    "trend_structure": {
        "trend_strength_min": 0.5,
        "structure_quality_min": 0.5,
    },
}


# ══════════════════════════════════════════════════════════════
# REINFORCEMENT PATTERNS ENGINE
# ══════════════════════════════════════════════════════════════

class ReinforcementPatternsEngine:
    """
    Reinforcement Patterns Engine - PHASE 16.2
    
    Detects specific signal combinations that historically 
    provide strong trading edge.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load upstream engines
        self._ta_hypothesis_builder = None
        self._exchange_aggregator = None
        self._market_state_builder = None
    
    # ═══════════════════════════════════════════════════════════
    # LAZY LOADERS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def ta_hypothesis_builder(self):
        if self._ta_hypothesis_builder is None:
            try:
                from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_ta_hypothesis_builder
                self._ta_hypothesis_builder = get_ta_hypothesis_builder()
            except ImportError:
                pass
        return self._ta_hypothesis_builder
    
    @property
    def exchange_aggregator(self):
        if self._exchange_aggregator is None:
            try:
                from modules.exchange_intelligence.exchange_context_aggregator import get_exchange_aggregator
                self._exchange_aggregator = get_exchange_aggregator()
            except ImportError:
                pass
        return self._exchange_aggregator
    
    @property
    def market_state_builder(self):
        if self._market_state_builder is None:
            try:
                from modules.trading_decision.market_state.market_state_builder import get_market_state_builder
                self._market_state_builder = get_market_state_builder()
            except ImportError:
                pass
        return self._market_state_builder
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def analyze(self, symbol: str) -> ReinforcementPatternState:
        """
        Analyze reinforcement patterns for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            ReinforcementPatternState with detected patterns
        """
        now = datetime.now(timezone.utc)
        
        # Gather inputs from upstream
        trend_momentum_input = self._get_trend_momentum_input(symbol)
        breakout_volatility_input = self._get_breakout_volatility_input(symbol)
        flow_squeeze_input = self._get_flow_squeeze_input(symbol)
        trend_structure_input = self._get_trend_structure_input(symbol)
        
        # Detect patterns
        pattern_results = []
        
        # Pattern 1: Trend + Momentum Alignment
        tm_result = self._detect_trend_momentum(trend_momentum_input)
        pattern_results.append(tm_result)
        
        # Pattern 2: Breakout + Volatility Expansion
        bv_result = self._detect_breakout_volatility(breakout_volatility_input)
        pattern_results.append(bv_result)
        
        # Pattern 3: Flow + Squeeze Alignment
        fs_result = self._detect_flow_squeeze(flow_squeeze_input)
        pattern_results.append(fs_result)
        
        # Pattern 4: Trend + Structure Break
        ts_result = self._detect_trend_structure(trend_structure_input)
        pattern_results.append(ts_result)
        
        # Aggregate results
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        # Calculate reinforcement strength
        reinforcement_strength = self._calculate_strength(pattern_results)
        
        # Calculate modifier
        reinforcement_modifier = self._calculate_modifier(pattern_count, reinforcement_strength)
        
        # Find dominant pattern
        dominant_pattern = self._find_dominant_pattern(pattern_results)
        
        return ReinforcementPatternState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            reinforcement_strength=reinforcement_strength,
            reinforcement_modifier=reinforcement_modifier,
            dominant_pattern=dominant_pattern,
        )
    
    def analyze_from_inputs(
        self,
        symbol: str,
        trend_momentum: TrendMomentumInput,
        breakout_volatility: BreakoutVolatilityInput,
        flow_squeeze: FlowSqueezeInput,
        trend_structure: TrendStructureInput,
    ) -> ReinforcementPatternState:
        """
        Analyze with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        pattern_results = []
        
        tm_result = self._detect_trend_momentum(trend_momentum)
        pattern_results.append(tm_result)
        
        bv_result = self._detect_breakout_volatility(breakout_volatility)
        pattern_results.append(bv_result)
        
        fs_result = self._detect_flow_squeeze(flow_squeeze)
        pattern_results.append(fs_result)
        
        ts_result = self._detect_trend_structure(trend_structure)
        pattern_results.append(ts_result)
        
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        reinforcement_strength = self._calculate_strength(pattern_results)
        reinforcement_modifier = self._calculate_modifier(pattern_count, reinforcement_strength)
        dominant_pattern = self._find_dominant_pattern(pattern_results)
        
        return ReinforcementPatternState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            reinforcement_strength=reinforcement_strength,
            reinforcement_modifier=reinforcement_modifier,
            dominant_pattern=dominant_pattern,
        )
    
    # ═══════════════════════════════════════════════════════════
    # PATTERN DETECTION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _detect_trend_momentum(self, input: TrendMomentumInput) -> PatternDetectionResult:
        """
        Pattern 1: Trend + Momentum Alignment
        
        Detects when trend and momentum point same direction with strength.
        """
        pattern_name = ReinforcementPattern.TREND_MOMENTUM_ALIGNMENT.value
        thresholds = PATTERN_THRESHOLDS["trend_momentum"]
        
        # Check if directions align
        directions_align = (
            input.trend_direction == input.momentum_direction
            and input.trend_direction in ["LONG", "SHORT"]
        )
        
        # Check strength thresholds
        trend_strong = input.trend_strength >= thresholds["trend_strength_min"]
        momentum_strong = input.momentum_strength >= thresholds["momentum_strength_min"]
        
        detected = directions_align and trend_strong and momentum_strong
        
        if detected:
            # Strength is average of both components
            strength = (input.trend_strength + input.momentum_strength) / 2
            confidence = min(input.trend_strength, input.momentum_strength)
            reason = f"Trend {input.trend_direction} aligned with momentum"
        else:
            strength = 0.0
            confidence = 0.0
            if not directions_align:
                reason = "Trend and momentum directions not aligned"
            elif not trend_strong:
                reason = f"Trend strength {input.trend_strength:.2f} below threshold"
            else:
                reason = f"Momentum strength {input.momentum_strength:.2f} below threshold"
        
        return PatternDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            confidence=confidence,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_breakout_volatility(self, input: BreakoutVolatilityInput) -> PatternDetectionResult:
        """
        Pattern 2: Breakout + Volatility Expansion
        
        Detects breakout confirmation with expanding volatility.
        """
        pattern_name = ReinforcementPattern.BREAKOUT_VOLATILITY_EXPANSION.value
        thresholds = PATTERN_THRESHOLDS["breakout_volatility"]
        
        # Check conditions
        breakout_valid = (
            input.breakout_detected
            and input.breakout_strength >= thresholds["breakout_strength_min"]
        )
        
        volatility_expanding = (
            input.volatility_state in ["HIGH", "EXPANDING"]
            or input.volatility_expansion_rate >= thresholds["volatility_expansion_min"]
        )
        
        detected = breakout_valid and volatility_expanding
        
        if detected:
            strength = (input.breakout_strength + input.volatility_expansion_rate) / 2
            confidence = input.breakout_strength
            reason = f"Breakout {input.breakout_direction} with volatility {input.volatility_state}"
        else:
            strength = 0.0
            confidence = 0.0
            if not input.breakout_detected:
                reason = "No breakout detected"
            elif not breakout_valid:
                reason = f"Breakout strength {input.breakout_strength:.2f} below threshold"
            else:
                reason = f"Volatility not expanding ({input.volatility_state})"
        
        return PatternDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            confidence=confidence,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_flow_squeeze(self, input: FlowSqueezeInput) -> PatternDetectionResult:
        """
        Pattern 3: Flow + Squeeze Alignment
        
        Detects flow direction aligned with squeeze probability.
        """
        pattern_name = ReinforcementPattern.FLOW_SQUEEZE_ALIGNMENT.value
        thresholds = PATTERN_THRESHOLDS["flow_squeeze"]
        
        # Check if flow and squeeze align
        flow_buy = input.flow_direction == "BUY" and input.squeeze_type == "SHORT_SQUEEZE"
        flow_sell = input.flow_direction == "SELL" and input.squeeze_type == "LONG_SQUEEZE"
        
        alignment = flow_buy or flow_sell
        
        # Check thresholds
        flow_strong = input.flow_intensity >= thresholds["flow_intensity_min"]
        squeeze_likely = input.squeeze_probability >= thresholds["squeeze_probability_min"]
        
        detected = alignment and flow_strong and squeeze_likely
        
        if detected:
            strength = (input.flow_intensity + input.squeeze_probability) / 2
            confidence = input.squeeze_probability
            squeeze_dir = "short squeeze" if flow_buy else "long squeeze"
            reason = f"Flow {input.flow_direction} aligned with {squeeze_dir}"
        else:
            strength = 0.0
            confidence = 0.0
            if not alignment:
                reason = f"Flow {input.flow_direction} not aligned with {input.squeeze_type}"
            elif not flow_strong:
                reason = f"Flow intensity {input.flow_intensity:.2f} below threshold"
            else:
                reason = f"Squeeze probability {input.squeeze_probability:.2f} below threshold"
        
        return PatternDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            confidence=confidence,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_trend_structure(self, input: TrendStructureInput) -> PatternDetectionResult:
        """
        Pattern 4: Trend + Structure Break
        
        Detects trend direction confirmed by structure break.
        """
        pattern_name = ReinforcementPattern.TREND_STRUCTURE_BREAK.value
        thresholds = PATTERN_THRESHOLDS["trend_structure"]
        
        # Check alignment
        trend_long_bullish = (
            input.trend_direction == "LONG"
            and input.structure_break_direction == "BULLISH"
        )
        trend_short_bearish = (
            input.trend_direction == "SHORT"
            and input.structure_break_direction == "BEARISH"
        )
        
        alignment = input.structure_break_detected and (trend_long_bullish or trend_short_bearish)
        
        # Check thresholds
        trend_strong = input.trend_strength >= thresholds["trend_strength_min"]
        structure_quality = input.structure_quality >= thresholds["structure_quality_min"]
        
        detected = alignment and trend_strong and structure_quality
        
        if detected:
            strength = (input.trend_strength + input.structure_quality) / 2
            confidence = input.structure_quality
            reason = f"Trend {input.trend_direction} confirmed by {input.structure_break_direction} structure break"
        else:
            strength = 0.0
            confidence = 0.0
            if not input.structure_break_detected:
                reason = "No structure break detected"
            elif not alignment:
                reason = f"Trend {input.trend_direction} not aligned with {input.structure_break_direction} break"
            elif not trend_strong:
                reason = f"Trend strength {input.trend_strength:.2f} below threshold"
            else:
                reason = f"Structure quality {input.structure_quality:.2f} below threshold"
        
        return PatternDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            confidence=confidence,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_strength(self, pattern_results: List[PatternDetectionResult]) -> float:
        """
        Calculate overall reinforcement strength from patterns.
        
        Uses weighted average of detected pattern strengths.
        """
        total_weight = 0.0
        weighted_strength = 0.0
        
        for result in pattern_results:
            if result.detected:
                weight = PATTERN_WEIGHTS.get(result.pattern_name, 0.25)
                weighted_strength += result.strength * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize to 0-1
        return min(1.0, weighted_strength / total_weight)
    
    def _calculate_modifier(self, pattern_count: int, strength: float) -> float:
        """
        Calculate reinforcement modifier based on pattern count and strength.
        """
        if pattern_count == 0:
            return PATTERN_MODIFIER_CONFIG["no_patterns"]["modifier"]
        
        if pattern_count == 1:
            config = PATTERN_MODIFIER_CONFIG["single_pattern"]
        elif pattern_count == 2:
            config = PATTERN_MODIFIER_CONFIG["dual_patterns"]
        else:  # 3+
            config = PATTERN_MODIFIER_CONFIG["multi_patterns"]
        
        # Scale modifier by strength within range
        mod_min = config["modifier_min"]
        mod_max = config["modifier_max"]
        
        modifier = mod_min + (mod_max - mod_min) * strength
        
        return max(1.0, min(1.15, modifier))
    
    def _find_dominant_pattern(self, pattern_results: List[PatternDetectionResult]) -> Optional[str]:
        """Find the strongest detected pattern."""
        detected = [p for p in pattern_results if p.detected]
        
        if not detected:
            return None
        
        # Sort by strength
        detected.sort(key=lambda p: p.strength, reverse=True)
        return detected[0].pattern_name
    
    # ═══════════════════════════════════════════════════════════
    # INPUT GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_trend_momentum_input(self, symbol: str) -> TrendMomentumInput:
        """Get trend and momentum data."""
        if self.ta_hypothesis_builder is None:
            return TrendMomentumInput(
                trend_direction="NEUTRAL",
                trend_strength=0.5,
                momentum_direction="NEUTRAL",
                momentum_strength=0.5,
            )
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            # Get momentum from detailed signal if available
            momentum_dir = ta_result.direction.value
            momentum_str = 0.5
            
            if ta_result.momentum_signal:
                momentum_dir = ta_result.momentum_signal.direction.value
                momentum_str = ta_result.momentum_signal.strength
            
            return TrendMomentumInput(
                trend_direction=ta_result.direction.value,
                trend_strength=ta_result.trend_strength,
                momentum_direction=momentum_dir,
                momentum_strength=momentum_str,
            )
        except Exception:
            return TrendMomentumInput(
                trend_direction="NEUTRAL",
                trend_strength=0.5,
                momentum_direction="NEUTRAL",
                momentum_strength=0.5,
            )
    
    def _get_breakout_volatility_input(self, symbol: str) -> BreakoutVolatilityInput:
        """Get breakout and volatility data."""
        default = BreakoutVolatilityInput(
            breakout_detected=False,
            breakout_direction="NEUTRAL",
            breakout_strength=0.0,
            volatility_state="NORMAL",
            volatility_expansion_rate=0.3,
        )
        
        if self.ta_hypothesis_builder is None:
            return default
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            # Check for breakout signal
            breakout_detected = False
            breakout_dir = "NEUTRAL"
            breakout_str = 0.0
            
            if ta_result.breakout_signal:
                breakout_detected = ta_result.breakout_signal.detected
                breakout_dir = ta_result.breakout_signal.direction.value
                breakout_str = ta_result.breakout_signal.strength
            
            # Get volatility state from market state builder
            vol_state = "NORMAL"
            vol_rate = 0.3
            
            if self.market_state_builder:
                try:
                    market_state = self.market_state_builder.build_state(symbol)
                    vol_state = market_state.volatility_state.value
                    vol_rate = market_state.raw_scores.get("volatility_score", 0.3)
                except Exception:
                    pass
            
            return BreakoutVolatilityInput(
                breakout_detected=breakout_detected,
                breakout_direction=breakout_dir,
                breakout_strength=breakout_str,
                volatility_state=vol_state,
                volatility_expansion_rate=vol_rate,
            )
        except Exception:
            return default
    
    def _get_flow_squeeze_input(self, symbol: str) -> FlowSqueezeInput:
        """Get flow and squeeze data."""
        default = FlowSqueezeInput(
            flow_direction="NEUTRAL",
            flow_intensity=0.5,
            squeeze_probability=0.3,
            squeeze_type="NONE",
        )
        
        if self.exchange_aggregator is None:
            return default
        
        try:
            exchange = self.exchange_aggregator.aggregate(symbol)
            
            # Flow direction
            flow_dir = "NEUTRAL"
            if exchange.flow_pressure > 0.2:
                flow_dir = "BUY"
            elif exchange.flow_pressure < -0.2:
                flow_dir = "SELL"
            
            # Squeeze type
            squeeze_type = "NONE"
            if exchange.squeeze_probability > 0.4:
                if exchange.derivatives_pressure > 0:
                    squeeze_type = "SHORT_SQUEEZE"
                else:
                    squeeze_type = "LONG_SQUEEZE"
            
            return FlowSqueezeInput(
                flow_direction=flow_dir,
                flow_intensity=abs(exchange.flow_pressure),
                squeeze_probability=exchange.squeeze_probability,
                squeeze_type=squeeze_type,
            )
        except Exception:
            return default
    
    def _get_trend_structure_input(self, symbol: str) -> TrendStructureInput:
        """Get trend and structure data."""
        default = TrendStructureInput(
            trend_direction="NEUTRAL",
            trend_strength=0.5,
            structure_break_detected=False,
            structure_break_direction="NONE",
            structure_quality=0.5,
        )
        
        if self.ta_hypothesis_builder is None:
            return default
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            # Structure break from detailed signal
            structure_detected = False
            structure_dir = "NONE"
            structure_qual = 0.5
            
            if ta_result.structure_signal:
                structure_detected = (
                    ta_result.structure_signal.recent_bos
                    or ta_result.structure_signal.recent_choch
                )
                structure_dir = ta_result.structure_signal.bias.value
                if structure_dir == "LONG":
                    structure_dir = "BULLISH"
                elif structure_dir == "SHORT":
                    structure_dir = "BEARISH"
                structure_qual = ta_result.structure_signal.structure_score
            
            return TrendStructureInput(
                trend_direction=ta_result.direction.value,
                trend_strength=ta_result.trend_strength,
                structure_break_detected=structure_detected,
                structure_break_direction=structure_dir,
                structure_quality=structure_qual,
            )
        except Exception:
            return default
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_pattern_strength_for_interaction(self, symbol: str) -> Dict[str, Any]:
        """
        Get pattern strength for Interaction Engine integration.
        
        Returns strength contribution for reinforcement_score.
        """
        result = self.analyze(symbol)
        
        return {
            "pattern_reinforcement_strength": result.reinforcement_strength,
            "pattern_modifier": result.reinforcement_modifier,
            "patterns_detected": result.patterns_detected,
            "pattern_count": result.pattern_count,
            "dominant_pattern": result.dominant_pattern,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[ReinforcementPatternsEngine] = None


def get_reinforcement_patterns_engine() -> ReinforcementPatternsEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ReinforcementPatternsEngine()
    return _engine
