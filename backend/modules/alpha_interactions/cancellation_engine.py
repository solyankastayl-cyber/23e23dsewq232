"""
PHASE 16.5 — Cancellation Engine
=================================
Detects patterns that should VOID a trade entirely.

Cancellation vs Conflict:
- Conflict: reduces confidence
- Cancellation: invalidates setup

Cancellation Patterns:
1. Extreme Crowding Reversal - Market overloaded
2. Liquidity Trap - Fake breakout
3. Volatility Fake Expansion - No volume confirmation
4. Trend Exhaustion - Divergence signals end

Integration:
    reinforcement_score -= cancellation_strength * 0.4

Key Principle:
    Even strong synergy can be cancelled.
    This is the protective layer.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.cancellation_patterns import (
    CancellationPattern,
    CANCELLATION_PATTERNS,
    CANCELLATION_PATTERN_WEIGHTS,
    CANCELLATION_MODIFIER_CONFIG,
    CrowdingReversalInput,
    LiquidityTrapInput,
    FakeExpansionInput,
    TrendExhaustionInput,
    CancellationDetectionResult,
    CancellationState,
)

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# CANCELLATION THRESHOLDS
# ══════════════════════════════════════════════════════════════

CANCELLATION_THRESHOLDS = {
    "crowding_reversal": {
        "crowding_score_min": 0.8,
        "leverage_index_min": 0.6,
    },
    "liquidity_trap": {
        "flow_intensity_min": 0.5,
        "wick_ratio_min": 0.4,
    },
    "fake_expansion": {
        "volatility_change_min": 0.4,
        "volume_ratio_max": 0.8,  # Below average = fake
    },
    "trend_exhaustion": {
        "trend_strength_min": 0.8,
        "divergence_strength_min": 0.5,
    },
}


# ══════════════════════════════════════════════════════════════
# CANCELLATION ENGINE
# ══════════════════════════════════════════════════════════════

class CancellationEngine:
    """
    Cancellation Engine - PHASE 16.5
    
    Detects patterns that should VOID a trade entirely.
    Even strong reinforcement + synergy can be cancelled.
    
    This is the protective layer of the trading system.
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
    
    def analyze(self, symbol: str) -> CancellationState:
        """
        Analyze cancellation patterns for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            CancellationState with detected cancellation patterns
        """
        now = datetime.now(timezone.utc)
        
        # Gather inputs from upstream
        crowding_input = self._get_crowding_input(symbol)
        liquidity_input = self._get_liquidity_trap_input(symbol)
        fake_expansion_input = self._get_fake_expansion_input(symbol)
        exhaustion_input = self._get_trend_exhaustion_input(symbol)
        
        # Detect cancellation patterns
        pattern_results = []
        
        # Pattern 1: Extreme Crowding Reversal
        cr_result = self._detect_crowding_reversal(crowding_input)
        pattern_results.append(cr_result)
        
        # Pattern 2: Liquidity Trap
        lt_result = self._detect_liquidity_trap(liquidity_input)
        pattern_results.append(lt_result)
        
        # Pattern 3: Volatility Fake Expansion
        fe_result = self._detect_fake_expansion(fake_expansion_input)
        pattern_results.append(fe_result)
        
        # Pattern 4: Trend Exhaustion
        te_result = self._detect_trend_exhaustion(exhaustion_input)
        pattern_results.append(te_result)
        
        # Aggregate results
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        # Calculate cancellation strength
        cancellation_strength = self._calculate_strength(pattern_results)
        
        # Calculate modifier
        cancellation_modifier = self._calculate_modifier(pattern_count, cancellation_strength)
        
        # Determine if trade should be cancelled
        trade_cancelled = self._should_cancel_trade(pattern_results, cancellation_strength)
        
        # Find dominant (most critical) cancellation
        dominant_cancellation = self._find_dominant_cancellation(pattern_results)
        
        return CancellationState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            cancellation_strength=cancellation_strength,
            cancellation_modifier=cancellation_modifier,
            trade_cancelled=trade_cancelled,
            dominant_cancellation=dominant_cancellation,
        )
    
    def analyze_from_inputs(
        self,
        symbol: str,
        crowding: CrowdingReversalInput,
        liquidity: LiquidityTrapInput,
        fake_expansion: FakeExpansionInput,
        exhaustion: TrendExhaustionInput,
    ) -> CancellationState:
        """
        Analyze with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        pattern_results = []
        
        cr_result = self._detect_crowding_reversal(crowding)
        pattern_results.append(cr_result)
        
        lt_result = self._detect_liquidity_trap(liquidity)
        pattern_results.append(lt_result)
        
        fe_result = self._detect_fake_expansion(fake_expansion)
        pattern_results.append(fe_result)
        
        te_result = self._detect_trend_exhaustion(exhaustion)
        pattern_results.append(te_result)
        
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        cancellation_strength = self._calculate_strength(pattern_results)
        cancellation_modifier = self._calculate_modifier(pattern_count, cancellation_strength)
        trade_cancelled = self._should_cancel_trade(pattern_results, cancellation_strength)
        dominant_cancellation = self._find_dominant_cancellation(pattern_results)
        
        return CancellationState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            cancellation_strength=cancellation_strength,
            cancellation_modifier=cancellation_modifier,
            trade_cancelled=trade_cancelled,
            dominant_cancellation=dominant_cancellation,
        )
    
    # ═══════════════════════════════════════════════════════════
    # CANCELLATION DETECTION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _detect_crowding_reversal(self, input: CrowdingReversalInput) -> CancellationDetectionResult:
        """
        Pattern 1: Extreme Crowding Reversal
        
        Market is overloaded with positions in one direction.
        Violent reversal is likely.
        """
        pattern_name = CancellationPattern.EXTREME_CROWDING_REVERSAL.value
        thresholds = CANCELLATION_THRESHOLDS["crowding_reversal"]
        
        # Check extreme crowding
        crowding_extreme = input.crowding_score >= thresholds["crowding_score_min"]
        funding_extreme = input.funding_extreme
        leverage_high = input.leverage_index >= thresholds["leverage_index_min"]
        
        detected = crowding_extreme and (funding_extreme or leverage_high)
        
        if detected:
            strength = input.crowding_score
            if funding_extreme:
                strength = min(1.0, strength * 1.2)  # Boost for extreme funding
            severity = self._classify_severity(strength)
            reason = f"Extreme crowding ({input.funding_direction}), reversal likely"
        else:
            strength = 0.0
            severity = "WARNING"
            reason = "No extreme crowding detected"
        
        return CancellationDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            severity=severity,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_liquidity_trap(self, input: LiquidityTrapInput) -> CancellationDetectionResult:
        """
        Pattern 2: Liquidity Trap
        
        Flow direction opposite to structure break with price rejection.
        Classic fake breakout setup.
        """
        pattern_name = CancellationPattern.LIQUIDITY_TRAP.value
        thresholds = CANCELLATION_THRESHOLDS["liquidity_trap"]
        
        # Check flow vs structure conflict
        flow_bullish = input.flow_direction == "BUY"
        flow_bearish = input.flow_direction == "SELL"
        structure_bullish = input.structure_break_direction == "BULLISH"
        structure_bearish = input.structure_break_direction == "BEARISH"
        
        # Trap: flow opposite to structure
        trap_setup = (
            (flow_bullish and structure_bearish) or
            (flow_bearish and structure_bullish)
        )
        
        # Strong flow
        flow_strong = input.flow_intensity >= thresholds["flow_intensity_min"]
        
        # Price rejection (wick)
        rejection = input.price_rejection or input.wick_ratio >= thresholds["wick_ratio_min"]
        
        detected = trap_setup and flow_strong and rejection
        
        if detected:
            strength = (input.flow_intensity + input.wick_ratio) / 2
            severity = self._classify_severity(strength)
            reason = f"Liquidity trap: Flow {input.flow_direction} vs {input.structure_break_direction} break with rejection"
        else:
            strength = 0.0
            severity = "WARNING"
            if not trap_setup:
                reason = "No flow-structure conflict"
            elif not flow_strong:
                reason = "Flow not strong enough"
            else:
                reason = "No price rejection detected"
        
        return CancellationDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            severity=severity,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_fake_expansion(self, input: FakeExpansionInput) -> CancellationDetectionResult:
        """
        Pattern 3: Volatility Fake Expansion
        
        Volatility expanding but without volume confirmation.
        Move is likely fake.
        """
        pattern_name = CancellationPattern.VOLATILITY_FAKE_EXPANSION.value
        thresholds = CANCELLATION_THRESHOLDS["fake_expansion"]
        
        # Check volatility expanding
        vol_expanding = (
            input.volatility_expanding
            and input.volatility_change_rate >= thresholds["volatility_change_min"]
        )
        
        # Check NO volume confirmation
        no_volume = not input.volume_spike and input.volume_ratio <= thresholds["volume_ratio_max"]
        
        # Check no follow through
        no_follow = not input.price_follow_through
        
        detected = vol_expanding and no_volume and no_follow
        
        if detected:
            strength = input.volatility_change_rate * (1 - input.volume_ratio)
            severity = self._classify_severity(strength)
            reason = f"Fake expansion: Volatility up but volume ratio only {input.volume_ratio:.2f}"
        else:
            strength = 0.0
            severity = "WARNING"
            if not vol_expanding:
                reason = "No volatility expansion"
            elif not no_volume:
                reason = "Volume confirmed the move"
            else:
                reason = "Price followed through"
        
        return CancellationDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            severity=severity,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_trend_exhaustion(self, input: TrendExhaustionInput) -> CancellationDetectionResult:
        """
        Pattern 4: Trend Exhaustion
        
        Strong trend with momentum divergence.
        End of trend is likely.
        """
        pattern_name = CancellationPattern.TREND_EXHAUSTION.value
        thresholds = CANCELLATION_THRESHOLDS["trend_exhaustion"]
        
        # Check strong trend
        trend_strong = (
            input.trend_direction in ["LONG", "SHORT"]
            and input.trend_strength >= thresholds["trend_strength_min"]
        )
        
        # Check divergence
        divergence_active = (
            input.momentum_divergence
            and input.divergence_strength >= thresholds["divergence_strength_min"]
        )
        
        # RSI extreme adds confidence
        rsi_confirms = input.rsi_extreme
        
        detected = trend_strong and divergence_active
        
        if detected:
            strength = (input.trend_strength + input.divergence_strength) / 2
            if rsi_confirms:
                strength = min(1.0, strength * 1.15)
            severity = self._classify_severity(strength)
            reason = f"Trend exhaustion: {input.trend_direction} trend with momentum divergence"
        else:
            strength = 0.0
            severity = "WARNING"
            if not trend_strong:
                reason = "Trend not strong enough for exhaustion signal"
            else:
                reason = "No momentum divergence detected"
        
        return CancellationDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            severity=severity,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_strength(self, pattern_results: List[CancellationDetectionResult]) -> float:
        """
        Calculate overall cancellation strength from patterns.
        """
        total_weight = 0.0
        weighted_strength = 0.0
        
        for result in pattern_results:
            if result.detected:
                weight = CANCELLATION_PATTERN_WEIGHTS.get(result.pattern_name, 0.25)
                weighted_strength += result.strength * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, weighted_strength / total_weight)
    
    def _calculate_modifier(self, pattern_count: int, strength: float) -> float:
        """
        Calculate cancellation modifier.
        
        More cancellation = lower modifier = weaker trade.
        """
        if pattern_count == 0:
            return CANCELLATION_MODIFIER_CONFIG["no_cancellation"]["modifier"]
        
        if pattern_count == 1:
            config = CANCELLATION_MODIFIER_CONFIG["single_cancellation"]
        elif pattern_count == 2:
            config = CANCELLATION_MODIFIER_CONFIG["dual_cancellation"]
        else:  # 3+
            config = CANCELLATION_MODIFIER_CONFIG["multi_cancellation"]
        
        # Scale modifier by strength (higher strength = lower modifier)
        mod_min = config["modifier_min"]
        mod_max = config["modifier_max"]
        
        modifier = mod_max - (mod_max - mod_min) * strength
        
        return max(0.5, min(1.0, modifier))
    
    def _should_cancel_trade(
        self, 
        pattern_results: List[CancellationDetectionResult],
        cancellation_strength: float
    ) -> bool:
        """
        Determine if trade should be completely cancelled.
        """
        # Any CRITICAL severity = cancel
        for result in pattern_results:
            if result.detected and result.severity == "CRITICAL":
                return True
        
        # Multiple cancellations with high strength = cancel
        detected_count = sum(1 for r in pattern_results if r.detected)
        if detected_count >= 2 and cancellation_strength >= 0.7:
            return True
        
        return False
    
    def _find_dominant_cancellation(
        self, 
        pattern_results: List[CancellationDetectionResult]
    ) -> Optional[str]:
        """Find the most critical detected cancellation."""
        detected = [p for p in pattern_results if p.detected]
        
        if not detected:
            return None
        
        # Sort by severity first, then strength
        severity_order = {"CRITICAL": 0, "CANCEL": 1, "WARNING": 2}
        detected.sort(key=lambda p: (severity_order.get(p.severity, 3), -p.strength))
        return detected[0].pattern_name
    
    def _classify_severity(self, strength: float) -> str:
        """Classify severity from strength."""
        if strength >= 0.8:
            return "CRITICAL"
        elif strength >= 0.6:
            return "CANCEL"
        else:
            return "WARNING"
    
    # ═══════════════════════════════════════════════════════════
    # INPUT GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_crowding_input(self, symbol: str) -> CrowdingReversalInput:
        """Get crowding data."""
        default = CrowdingReversalInput(
            crowding_score=0.5,
            funding_extreme=False,
            funding_direction="NEUTRAL",
            leverage_index=0.3,
            open_interest_change=0.0,
        )
        
        if self.exchange_aggregator is None:
            return default
        
        try:
            exchange = self.exchange_aggregator.aggregate(symbol)
            
            funding_dir = "NEUTRAL"
            funding_extreme = False
            
            if exchange.funding_state.value in ["EXTREME_LONG", "LONG_CROWDED"]:
                funding_dir = "LONG_CROWDED"
                funding_extreme = "EXTREME" in exchange.funding_state.value
            elif exchange.funding_state.value in ["EXTREME_SHORT", "SHORT_CROWDED"]:
                funding_dir = "SHORT_CROWDED"
                funding_extreme = "EXTREME" in exchange.funding_state.value
            
            return CrowdingReversalInput(
                crowding_score=exchange.crowding_risk,
                funding_extreme=funding_extreme,
                funding_direction=funding_dir,
                leverage_index=abs(exchange.derivatives_pressure),
                open_interest_change=0.0,  # Would need OI data
            )
        except Exception:
            return default
    
    def _get_liquidity_trap_input(self, symbol: str) -> LiquidityTrapInput:
        """Get liquidity trap data."""
        default = LiquidityTrapInput(
            flow_direction="NEUTRAL",
            flow_intensity=0.5,
            structure_break_direction="NONE",
            price_rejection=False,
            wick_ratio=0.2,
        )
        
        flow_dir = "NEUTRAL"
        flow_int = 0.5
        struct_dir = "NONE"
        rejection = False
        wick = 0.2
        
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
                
                # Estimate rejection from candle patterns
                if ta_result.candle_signal:
                    rejection = ta_result.candle_signal.rejection_candle
                    wick = ta_result.candle_signal.wick_ratio
            except Exception:
                pass
        
        return LiquidityTrapInput(
            flow_direction=flow_dir,
            flow_intensity=flow_int,
            structure_break_direction=struct_dir,
            price_rejection=rejection,
            wick_ratio=wick,
        )
    
    def _get_fake_expansion_input(self, symbol: str) -> FakeExpansionInput:
        """Get fake expansion data."""
        default = FakeExpansionInput(
            volatility_expanding=False,
            volatility_change_rate=0.2,
            volume_spike=False,
            volume_ratio=0.8,
            price_follow_through=True,
        )
        
        vol_expanding = False
        vol_rate = 0.2
        vol_spike = False
        vol_ratio = 0.8
        follow_through = True
        
        if self.market_state_builder:
            try:
                market_state = self.market_state_builder.build_state(symbol)
                vol_expanding = market_state.volatility_state.value in ["EXPANDING", "HIGH_VOL"]
                vol_rate = market_state.raw_scores.get("volatility_score", 0.3)
            except Exception:
                pass
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                if ta_result.volume_signal:
                    vol_spike = ta_result.volume_signal.volume_spike
                    vol_ratio = ta_result.volume_signal.volume_ratio
                follow_through = ta_result.setup_quality > 0.5
            except Exception:
                pass
        
        return FakeExpansionInput(
            volatility_expanding=vol_expanding,
            volatility_change_rate=vol_rate,
            volume_spike=vol_spike,
            volume_ratio=vol_ratio,
            price_follow_through=follow_through,
        )
    
    def _get_trend_exhaustion_input(self, symbol: str) -> TrendExhaustionInput:
        """Get trend exhaustion data."""
        default = TrendExhaustionInput(
            trend_direction="NEUTRAL",
            trend_strength=0.5,
            momentum_divergence=False,
            divergence_strength=0.0,
            rsi_extreme=False,
        )
        
        if self.ta_hypothesis_builder is None:
            return default
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            divergence = False
            div_strength = 0.0
            rsi_extreme = False
            
            if ta_result.momentum_signal:
                divergence = ta_result.momentum_signal.divergence_detected
                div_strength = ta_result.momentum_signal.divergence_strength
                rsi_value = ta_result.momentum_signal.rsi_value
                rsi_extreme = rsi_value < 30 or rsi_value > 70
            
            return TrendExhaustionInput(
                trend_direction=ta_result.direction.value,
                trend_strength=ta_result.trend_strength,
                momentum_divergence=divergence,
                divergence_strength=div_strength,
                rsi_extreme=rsi_extreme,
            )
        except Exception:
            return default
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_cancellation_for_interaction(self, symbol: str) -> Dict[str, Any]:
        """
        Get cancellation data for Interaction Engine integration.
        
        Returns data to reduce reinforcement_score.
        """
        result = self.analyze(symbol)
        
        return {
            "cancellation_strength": result.cancellation_strength,
            "cancellation_modifier": result.cancellation_modifier,
            "cancellation_patterns": result.patterns_detected,
            "cancellation_count": result.pattern_count,
            "trade_cancelled": result.trade_cancelled,
            "dominant_cancellation": result.dominant_cancellation,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[CancellationEngine] = None


def get_cancellation_engine() -> CancellationEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = CancellationEngine()
    return _engine
