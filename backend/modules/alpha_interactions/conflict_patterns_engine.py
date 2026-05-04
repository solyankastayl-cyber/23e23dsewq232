"""
PHASE 16.3 — Conflict Patterns Engine
======================================
Detects specific signal conflicts that increase trading risk.

Conflict Patterns:
1. TA vs Exchange Direction - Direct opposite signals
2. Trend vs Mean Reversion - Strategy logic conflict
3. Flow vs Structure - Liquidity trap risk
4. Derivatives vs Trend - Crowding conflict

Integration:
    conflict_score += conflict_pattern_strength * 0.35

Key Insight:
    Different conflicts have different consequences.
    - ta_exchange conflict = normal conflict
    - derivatives vs trend = dangerous conflict (crowding)
    - flow vs structure = liquidity trap
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.conflict_patterns import (
    ConflictPattern,
    ConflictSeverity,
    CONFLICT_PATTERNS,
    CONFLICT_PATTERN_WEIGHTS,
    CONFLICT_MODIFIER_CONFIG,
    SEVERITY_THRESHOLDS,
    TAExchangeConflictInput,
    TrendMeanReversionInput,
    FlowStructureInput,
    DerivativesTrendInput,
    ConflictDetectionResult,
    ConflictPatternState,
)

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# CONFLICT THRESHOLDS
# ══════════════════════════════════════════════════════════════

CONFLICT_THRESHOLDS = {
    "ta_exchange": {
        "conviction_min": 0.5,
        "confidence_min": 0.5,
    },
    "trend_mean_reversion": {
        "trend_strength_min": 0.5,
        "reversion_strength_min": 0.4,
    },
    "flow_structure": {
        "flow_intensity_min": 0.5,
        "structure_quality_min": 0.5,
    },
    "derivatives_trend": {
        "trend_strength_min": 0.4,
        "crowding_risk_min": 0.5,
    },
}


# ══════════════════════════════════════════════════════════════
# CONFLICT PATTERNS ENGINE
# ══════════════════════════════════════════════════════════════

class ConflictPatternsEngine:
    """
    Conflict Patterns Engine - PHASE 16.3
    
    Detects specific signal conflict patterns that increase risk.
    Different conflicts have different consequences and danger levels.
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
    
    def analyze(self, symbol: str) -> ConflictPatternState:
        """
        Analyze conflict patterns for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            ConflictPatternState with detected conflicts
        """
        now = datetime.now(timezone.utc)
        
        # Gather inputs from upstream
        ta_exchange_input = self._get_ta_exchange_input(symbol)
        trend_reversion_input = self._get_trend_reversion_input(symbol)
        flow_structure_input = self._get_flow_structure_input(symbol)
        derivatives_trend_input = self._get_derivatives_trend_input(symbol)
        
        # Detect conflict patterns
        pattern_results = []
        
        # Pattern 1: TA vs Exchange Direction
        te_result = self._detect_ta_exchange_conflict(ta_exchange_input)
        pattern_results.append(te_result)
        
        # Pattern 2: Trend vs Mean Reversion
        tr_result = self._detect_trend_reversion_conflict(trend_reversion_input)
        pattern_results.append(tr_result)
        
        # Pattern 3: Flow vs Structure
        fs_result = self._detect_flow_structure_conflict(flow_structure_input)
        pattern_results.append(fs_result)
        
        # Pattern 4: Derivatives vs Trend
        dt_result = self._detect_derivatives_trend_conflict(derivatives_trend_input)
        pattern_results.append(dt_result)
        
        # Aggregate results
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        # Calculate conflict strength
        conflict_strength = self._calculate_strength(pattern_results)
        
        # Calculate modifier
        conflict_modifier = self._calculate_modifier(pattern_count, conflict_strength)
        
        # Determine severity
        conflict_severity = self._determine_severity(conflict_strength)
        
        # Find dominant (most dangerous) conflict
        dominant_conflict = self._find_dominant_conflict(pattern_results)
        
        return ConflictPatternState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            conflict_strength=conflict_strength,
            conflict_modifier=conflict_modifier,
            conflict_severity=conflict_severity,
            dominant_conflict=dominant_conflict,
        )
    
    def analyze_from_inputs(
        self,
        symbol: str,
        ta_exchange: TAExchangeConflictInput,
        trend_reversion: TrendMeanReversionInput,
        flow_structure: FlowStructureInput,
        derivatives_trend: DerivativesTrendInput,
    ) -> ConflictPatternState:
        """
        Analyze with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        pattern_results = []
        
        te_result = self._detect_ta_exchange_conflict(ta_exchange)
        pattern_results.append(te_result)
        
        tr_result = self._detect_trend_reversion_conflict(trend_reversion)
        pattern_results.append(tr_result)
        
        fs_result = self._detect_flow_structure_conflict(flow_structure)
        pattern_results.append(fs_result)
        
        dt_result = self._detect_derivatives_trend_conflict(derivatives_trend)
        pattern_results.append(dt_result)
        
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        conflict_strength = self._calculate_strength(pattern_results)
        conflict_modifier = self._calculate_modifier(pattern_count, conflict_strength)
        conflict_severity = self._determine_severity(conflict_strength)
        dominant_conflict = self._find_dominant_conflict(pattern_results)
        
        return ConflictPatternState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            conflict_strength=conflict_strength,
            conflict_modifier=conflict_modifier,
            conflict_severity=conflict_severity,
            dominant_conflict=dominant_conflict,
        )
    
    # ═══════════════════════════════════════════════════════════
    # CONFLICT DETECTION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _detect_ta_exchange_conflict(self, input: TAExchangeConflictInput) -> ConflictDetectionResult:
        """
        Pattern 1: TA vs Exchange Direction Conflict
        
        Detects when TA and Exchange signals point opposite directions.
        """
        pattern_name = ConflictPattern.TA_EXCHANGE_DIRECTION.value
        thresholds = CONFLICT_THRESHOLDS["ta_exchange"]
        
        # Map directions
        ta_numeric = self._direction_to_numeric(input.ta_direction)
        exchange_numeric = self._bias_to_numeric(input.exchange_bias)
        
        # Check if opposite directions
        opposite = (ta_numeric * exchange_numeric) < 0
        
        # Check strength thresholds
        ta_strong = input.ta_conviction >= thresholds["conviction_min"]
        exchange_strong = input.exchange_confidence >= thresholds["confidence_min"]
        
        detected = opposite and ta_strong and exchange_strong
        
        if detected:
            # Strength is product of both convictions
            strength = (input.ta_conviction + input.exchange_confidence) / 2
            danger = self._classify_danger(strength)
            reason = f"TA {input.ta_direction} conflicts with Exchange {input.exchange_bias}"
        else:
            strength = 0.0
            danger = "LOW"
            if not opposite:
                reason = "TA and Exchange are aligned or neutral"
            elif not ta_strong:
                reason = f"TA conviction {input.ta_conviction:.2f} below threshold"
            else:
                reason = f"Exchange confidence {input.exchange_confidence:.2f} below threshold"
        
        return ConflictDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            danger_level=danger,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_trend_reversion_conflict(self, input: TrendMeanReversionInput) -> ConflictDetectionResult:
        """
        Pattern 2: Trend vs Mean Reversion Conflict
        
        Detects when trend signal conflicts with mean reversion signal.
        Strategy logic conflict.
        """
        pattern_name = ConflictPattern.TREND_VS_MEAN_REVERSION.value
        thresholds = CONFLICT_THRESHOLDS["trend_mean_reversion"]
        
        # Check if trend is active
        trend_active = (
            input.trend_state in ["TREND_UP", "TREND_DOWN"]
            and input.trend_strength >= thresholds["trend_strength_min"]
        )
        
        # Check if mean reversion is signaling
        reversion_active = (
            input.mean_reversion_signal
            and input.mean_reversion_strength >= thresholds["reversion_strength_min"]
        )
        
        # RSI extreme adds to conflict
        rsi_conflict = input.rsi_extreme and trend_active
        
        detected = trend_active and (reversion_active or rsi_conflict)
        
        if detected:
            strength = (input.trend_strength + input.mean_reversion_strength) / 2
            if rsi_conflict:
                strength = min(1.0, strength * 1.2)  # RSI extreme increases severity
            danger = self._classify_danger(strength)
            reason = f"Trend {input.trend_state} conflicts with mean reversion signal"
            if rsi_conflict:
                reason += " (RSI extreme)"
        else:
            strength = 0.0
            danger = "LOW"
            if not trend_active:
                reason = "No strong trend active"
            else:
                reason = "No mean reversion signal"
        
        return ConflictDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            danger_level=danger,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_flow_structure_conflict(self, input: FlowStructureInput) -> ConflictDetectionResult:
        """
        Pattern 3: Flow vs Structure Conflict
        
        Detects when order flow opposes structure break.
        This often indicates a liquidity trap.
        """
        pattern_name = ConflictPattern.FLOW_VS_STRUCTURE.value
        thresholds = CONFLICT_THRESHOLDS["flow_structure"]
        
        # Map directions
        flow_bullish = input.flow_direction == "BUY"
        flow_bearish = input.flow_direction == "SELL"
        structure_bullish = input.structure_break_direction == "BULLISH"
        structure_bearish = input.structure_break_direction == "BEARISH"
        
        # Detect conflict: flow opposite to structure
        conflict = (
            (flow_bullish and structure_bearish) or
            (flow_bearish and structure_bullish)
        )
        
        # Check thresholds
        flow_strong = input.flow_intensity >= thresholds["flow_intensity_min"]
        structure_valid = (
            input.structure_break_direction != "NONE"
            and input.structure_quality >= thresholds["structure_quality_min"]
        )
        
        detected = conflict and flow_strong and structure_valid
        
        if detected:
            strength = (input.flow_intensity + input.structure_quality) / 2
            danger = self._classify_danger(strength)
            reason = f"Flow {input.flow_direction} conflicts with {input.structure_break_direction} structure break (liquidity trap risk)"
        else:
            strength = 0.0
            danger = "LOW"
            if not conflict:
                reason = "Flow and structure are aligned"
            elif not flow_strong:
                reason = f"Flow intensity {input.flow_intensity:.2f} below threshold"
            else:
                reason = "No valid structure break"
        
        return ConflictDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            danger_level=danger,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_derivatives_trend_conflict(self, input: DerivativesTrendInput) -> ConflictDetectionResult:
        """
        Pattern 4: Derivatives vs Trend Conflict
        
        Detects when derivatives crowding opposes trend direction.
        This is a dangerous conflict - crowded trades often reverse.
        """
        pattern_name = ConflictPattern.DERIVATIVES_VS_TREND.value
        thresholds = CONFLICT_THRESHOLDS["derivatives_trend"]
        
        # Check if trend is active
        trend_long = input.trend_direction == "LONG"
        trend_short = input.trend_direction == "SHORT"
        trend_active = (
            (trend_long or trend_short)
            and input.trend_strength >= thresholds["trend_strength_min"]
        )
        
        # Check crowding
        long_crowded = input.funding_state in ["LONG_CROWDED", "EXTREME_LONG"]
        short_crowded = input.funding_state in ["SHORT_CROWDED", "EXTREME_SHORT"]
        
        # Conflict: trend direction matches crowding direction (dangerous)
        # If everyone is long and trend is up → potential reversal
        crowded_same_direction = (
            (trend_long and long_crowded) or
            (trend_short and short_crowded)
        )
        
        crowding_high = input.crowding_risk >= thresholds["crowding_risk_min"]
        
        detected = trend_active and crowded_same_direction and crowding_high
        
        if detected:
            # This is particularly dangerous - use higher strength
            strength = max(input.trend_strength, input.crowding_risk)
            if input.funding_state.startswith("EXTREME"):
                strength = min(1.0, strength * 1.3)  # Extreme crowding is worse
            danger = "HIGH" if strength > 0.6 else "MEDIUM"
            reason = f"Trend {input.trend_direction} while market is {input.funding_state} (crowding risk)"
        else:
            strength = 0.0
            danger = "LOW"
            if not trend_active:
                reason = "No strong trend active"
            elif not crowded_same_direction:
                reason = "Crowding direction doesn't conflict with trend"
            else:
                reason = f"Crowding risk {input.crowding_risk:.2f} below threshold"
        
        return ConflictDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            danger_level=danger,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_strength(self, pattern_results: List[ConflictDetectionResult]) -> float:
        """
        Calculate overall conflict strength from patterns.
        
        Uses weighted average of detected pattern strengths.
        """
        total_weight = 0.0
        weighted_strength = 0.0
        
        for result in pattern_results:
            if result.detected:
                weight = CONFLICT_PATTERN_WEIGHTS.get(result.pattern_name, 0.25)
                weighted_strength += result.strength * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, weighted_strength / total_weight)
    
    def _calculate_modifier(self, pattern_count: int, strength: float) -> float:
        """
        Calculate conflict modifier based on pattern count and strength.
        
        More conflicts = lower modifier (more risk).
        """
        if pattern_count == 0:
            return CONFLICT_MODIFIER_CONFIG["no_conflicts"]["modifier"]
        
        if pattern_count == 1:
            config = CONFLICT_MODIFIER_CONFIG["single_conflict"]
        elif pattern_count == 2:
            config = CONFLICT_MODIFIER_CONFIG["dual_conflicts"]
        else:  # 3+
            config = CONFLICT_MODIFIER_CONFIG["multi_conflicts"]
        
        # Scale modifier by strength within range (higher strength = lower modifier)
        mod_min = config["modifier_min"]
        mod_max = config["modifier_max"]
        
        # Inverse: higher strength = closer to mod_min
        modifier = mod_max - (mod_max - mod_min) * strength
        
        return max(0.5, min(1.0, modifier))
    
    def _determine_severity(self, conflict_strength: float) -> ConflictSeverity:
        """Determine conflict severity from strength."""
        if conflict_strength >= SEVERITY_THRESHOLDS["high_min"]:
            return ConflictSeverity.HIGH_CONFLICT
        elif conflict_strength >= SEVERITY_THRESHOLDS["medium_min"]:
            return ConflictSeverity.MEDIUM_CONFLICT
        else:
            return ConflictSeverity.LOW_CONFLICT
    
    def _find_dominant_conflict(self, pattern_results: List[ConflictDetectionResult]) -> Optional[str]:
        """Find the most dangerous detected conflict."""
        detected = [p for p in pattern_results if p.detected]
        
        if not detected:
            return None
        
        # Sort by danger level first, then strength
        danger_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        detected.sort(key=lambda p: (danger_order.get(p.danger_level, 3), -p.strength))
        return detected[0].pattern_name
    
    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _direction_to_numeric(self, direction: str) -> float:
        """Convert TA direction to numeric."""
        return {"LONG": 1.0, "SHORT": -1.0, "NEUTRAL": 0.0}.get(direction, 0.0)
    
    def _bias_to_numeric(self, bias: str) -> float:
        """Convert exchange bias to numeric."""
        return {"BULLISH": 1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}.get(bias, 0.0)
    
    def _classify_danger(self, strength: float) -> str:
        """Classify danger level from strength."""
        if strength >= 0.6:
            return "HIGH"
        elif strength >= 0.35:
            return "MEDIUM"
        else:
            return "LOW"
    
    # ═══════════════════════════════════════════════════════════
    # INPUT GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_ta_exchange_input(self, symbol: str) -> TAExchangeConflictInput:
        """Get TA and Exchange data for conflict detection."""
        default = TAExchangeConflictInput(
            ta_direction="NEUTRAL",
            ta_conviction=0.5,
            exchange_bias="NEUTRAL",
            exchange_confidence=0.5,
        )
        
        ta_dir = "NEUTRAL"
        ta_conv = 0.5
        ex_bias = "NEUTRAL"
        ex_conf = 0.5
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                ta_dir = ta_result.direction.value
                ta_conv = ta_result.conviction
            except Exception:
                pass
        
        if self.exchange_aggregator:
            try:
                exchange = self.exchange_aggregator.aggregate(symbol)
                ex_bias = exchange.exchange_bias.value
                ex_conf = exchange.confidence
            except Exception:
                pass
        
        return TAExchangeConflictInput(
            ta_direction=ta_dir,
            ta_conviction=ta_conv,
            exchange_bias=ex_bias,
            exchange_confidence=ex_conf,
        )
    
    def _get_trend_reversion_input(self, symbol: str) -> TrendMeanReversionInput:
        """Get trend and mean reversion data."""
        default = TrendMeanReversionInput(
            trend_state="RANGE",
            trend_strength=0.5,
            mean_reversion_signal=False,
            mean_reversion_strength=0.0,
            rsi_extreme=False,
        )
        
        if self.ta_hypothesis_builder is None:
            return default
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            # Check RSI extreme
            rsi_extreme = False
            rsi_value = 50
            if ta_result.momentum_signal:
                rsi_value = ta_result.momentum_signal.rsi_value
                rsi_extreme = rsi_value < 30 or rsi_value > 70
            
            # Mean reversion signal when RSI is extreme opposite to trend
            mean_reversion = False
            reversion_strength = 0.0
            
            trend_up = ta_result.regime.value == "TREND_UP"
            trend_down = ta_result.regime.value == "TREND_DOWN"
            
            if trend_up and rsi_value > 70:
                mean_reversion = True
                reversion_strength = (rsi_value - 70) / 30  # 0-1 based on how extreme
            elif trend_down and rsi_value < 30:
                mean_reversion = True
                reversion_strength = (30 - rsi_value) / 30
            
            return TrendMeanReversionInput(
                trend_state=ta_result.regime.value,
                trend_strength=ta_result.trend_strength,
                mean_reversion_signal=mean_reversion,
                mean_reversion_strength=reversion_strength,
                rsi_extreme=rsi_extreme,
            )
        except Exception:
            return default
    
    def _get_flow_structure_input(self, symbol: str) -> FlowStructureInput:
        """Get flow and structure data."""
        default = FlowStructureInput(
            flow_direction="NEUTRAL",
            flow_intensity=0.5,
            structure_break_direction="NONE",
            structure_quality=0.5,
        )
        
        flow_dir = "NEUTRAL"
        flow_int = 0.5
        struct_dir = "NONE"
        struct_qual = 0.5
        
        if self.exchange_aggregator:
            try:
                exchange = self.exchange_aggregator.aggregate(symbol)
                if exchange.flow_pressure > 0.2:
                    flow_dir = "BUY"
                elif exchange.flow_pressure < -0.2:
                    flow_dir = "SELL"
                flow_int = abs(exchange.flow_pressure)
            except Exception:
                pass
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                if ta_result.structure_signal:
                    if ta_result.structure_signal.recent_bos or ta_result.structure_signal.recent_choch:
                        struct_dir = ta_result.structure_signal.bias.value
                        if struct_dir == "LONG":
                            struct_dir = "BULLISH"
                        elif struct_dir == "SHORT":
                            struct_dir = "BEARISH"
                        struct_qual = ta_result.structure_signal.structure_score
            except Exception:
                pass
        
        return FlowStructureInput(
            flow_direction=flow_dir,
            flow_intensity=flow_int,
            structure_break_direction=struct_dir,
            structure_quality=struct_qual,
        )
    
    def _get_derivatives_trend_input(self, symbol: str) -> DerivativesTrendInput:
        """Get derivatives and trend data."""
        default = DerivativesTrendInput(
            trend_direction="NEUTRAL",
            trend_strength=0.5,
            funding_state="NEUTRAL",
            crowding_risk=0.3,
            leverage_index=0.3,
        )
        
        trend_dir = "NEUTRAL"
        trend_str = 0.5
        funding = "NEUTRAL"
        crowd_risk = 0.3
        leverage = 0.3
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                trend_dir = ta_result.direction.value
                trend_str = ta_result.trend_strength
            except Exception:
                pass
        
        if self.exchange_aggregator:
            try:
                exchange = self.exchange_aggregator.aggregate(symbol)
                funding = exchange.funding_state.value
                crowd_risk = exchange.crowding_risk
                # Estimate leverage from derivatives pressure
                leverage = abs(exchange.derivatives_pressure)
            except Exception:
                pass
        
        return DerivativesTrendInput(
            trend_direction=trend_dir,
            trend_strength=trend_str,
            funding_state=funding,
            crowding_risk=crowd_risk,
            leverage_index=leverage,
        )
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_conflict_strength_for_interaction(self, symbol: str) -> Dict[str, Any]:
        """
        Get conflict strength for Interaction Engine integration.
        
        Returns strength contribution for conflict_score.
        """
        result = self.analyze(symbol)
        
        return {
            "pattern_conflict_strength": result.conflict_strength,
            "conflict_modifier": result.conflict_modifier,
            "conflict_patterns": result.patterns_detected,
            "conflict_count": result.pattern_count,
            "conflict_severity": result.conflict_severity.value,
            "dominant_conflict": result.dominant_conflict,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[ConflictPatternsEngine] = None


def get_conflict_patterns_engine() -> ConflictPatternsEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ConflictPatternsEngine()
    return _engine
