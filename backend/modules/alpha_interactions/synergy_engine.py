"""
PHASE 16.4 — Synergy Engine
============================
Detects signal combinations that create emergent trading edge.

Synergy vs Reinforcement:
- Reinforcement: signals say the same thing
- Synergy: signals create NEW edge together

Synergy Patterns:
1. Trend + Compression + Breakout = Volatility Expansion Setup
2. Flow + Liquidation = Cascade Move Setup
3. Volatility Expansion + Trend = Trend Acceleration Setup
4. Structure Break + Momentum = Strong Continuation Setup

Integration:
    reinforcement_score += synergy_strength * 0.25
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.synergy_patterns import (
    SynergyPattern,
    SYNERGY_PATTERNS,
    SYNERGY_PATTERN_WEIGHTS,
    SYNERGY_MODIFIER_CONFIG,
    TrendCompressionInput,
    FlowLiquidationInput,
    VolatilityTrendInput,
    StructureMomentumInput,
    SynergyDetectionResult,
    SynergyState,
)

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# SYNERGY THRESHOLDS
# ══════════════════════════════════════════════════════════════

SYNERGY_THRESHOLDS = {
    "trend_compression": {
        "trend_strength_min": 0.6,
        "volatility_percentile_max": 0.3,  # Low vol = compression
        "breakout_strength_min": 0.4,
    },
    "flow_liquidation": {
        "flow_intensity_min": 0.5,
        "liquidation_risk_min": 0.5,
    },
    "volatility_trend": {
        "volatility_change_min": 0.3,
        "trend_strength_min": 0.4,
    },
    "structure_momentum": {
        "structure_quality_min": 0.5,
        "momentum_strength_min": 0.5,
    },
}


# ══════════════════════════════════════════════════════════════
# SYNERGY ENGINE
# ══════════════════════════════════════════════════════════════

class SynergyEngine:
    """
    Synergy Engine - PHASE 16.4
    
    Detects signal combinations that create emergent edge.
    These are setups where each signal alone is weak,
    but together they produce powerful moves.
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
    
    def analyze(self, symbol: str) -> SynergyState:
        """
        Analyze synergy patterns for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            SynergyState with detected synergy patterns
        """
        now = datetime.now(timezone.utc)
        
        # Gather inputs from upstream
        trend_compression_input = self._get_trend_compression_input(symbol)
        flow_liquidation_input = self._get_flow_liquidation_input(symbol)
        volatility_trend_input = self._get_volatility_trend_input(symbol)
        structure_momentum_input = self._get_structure_momentum_input(symbol)
        
        # Detect synergy patterns
        pattern_results = []
        
        # Pattern 1: Trend + Compression + Breakout
        tcb_result = self._detect_trend_compression_breakout(trend_compression_input)
        pattern_results.append(tcb_result)
        
        # Pattern 2: Flow + Liquidation Cascade
        flc_result = self._detect_flow_liquidation_cascade(flow_liquidation_input)
        pattern_results.append(flc_result)
        
        # Pattern 3: Volatility Expansion + Trend
        vet_result = self._detect_volatility_expansion_trend(volatility_trend_input)
        pattern_results.append(vet_result)
        
        # Pattern 4: Structure Break + Momentum
        sbm_result = self._detect_structure_break_momentum(structure_momentum_input)
        pattern_results.append(sbm_result)
        
        # Aggregate results
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        # Calculate synergy strength
        synergy_strength = self._calculate_strength(pattern_results)
        
        # Calculate modifier
        synergy_modifier = self._calculate_modifier(pattern_count, synergy_strength)
        
        # Find dominant synergy
        dominant_synergy = self._find_dominant_synergy(pattern_results)
        
        # Determine overall potential
        synergy_potential = self._determine_potential(synergy_strength, pattern_count)
        
        return SynergyState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            synergy_strength=synergy_strength,
            synergy_modifier=synergy_modifier,
            dominant_synergy=dominant_synergy,
            synergy_potential=synergy_potential,
        )
    
    def analyze_from_inputs(
        self,
        symbol: str,
        trend_compression: TrendCompressionInput,
        flow_liquidation: FlowLiquidationInput,
        volatility_trend: VolatilityTrendInput,
        structure_momentum: StructureMomentumInput,
    ) -> SynergyState:
        """
        Analyze with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        pattern_results = []
        
        tcb_result = self._detect_trend_compression_breakout(trend_compression)
        pattern_results.append(tcb_result)
        
        flc_result = self._detect_flow_liquidation_cascade(flow_liquidation)
        pattern_results.append(flc_result)
        
        vet_result = self._detect_volatility_expansion_trend(volatility_trend)
        pattern_results.append(vet_result)
        
        sbm_result = self._detect_structure_break_momentum(structure_momentum)
        pattern_results.append(sbm_result)
        
        patterns_detected = [p.pattern_name for p in pattern_results if p.detected]
        pattern_count = len(patterns_detected)
        
        synergy_strength = self._calculate_strength(pattern_results)
        synergy_modifier = self._calculate_modifier(pattern_count, synergy_strength)
        dominant_synergy = self._find_dominant_synergy(pattern_results)
        synergy_potential = self._determine_potential(synergy_strength, pattern_count)
        
        return SynergyState(
            symbol=symbol,
            timestamp=now,
            patterns_detected=patterns_detected,
            pattern_count=pattern_count,
            pattern_results=pattern_results,
            synergy_strength=synergy_strength,
            synergy_modifier=synergy_modifier,
            dominant_synergy=dominant_synergy,
            synergy_potential=synergy_potential,
        )
    
    # ═══════════════════════════════════════════════════════════
    # SYNERGY DETECTION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _detect_trend_compression_breakout(self, input: TrendCompressionInput) -> SynergyDetectionResult:
        """
        Pattern 1: Trend + Compression + Breakout
        
        Classic volatility expansion setup.
        Trend provides direction, compression stores energy, breakout triggers release.
        """
        pattern_name = SynergyPattern.TREND_COMPRESSION_BREAKOUT.value
        thresholds = SYNERGY_THRESHOLDS["trend_compression"]
        
        # Check trend
        trend_active = (
            input.trend_direction in ["LONG", "SHORT"]
            and input.trend_strength >= thresholds["trend_strength_min"]
        )
        
        # Check compression (low volatility)
        compressed = (
            input.volatility_state == "LOW_VOL"
            or input.volatility_percentile <= thresholds["volatility_percentile_max"]
        )
        
        # Check breakout
        breakout_valid = (
            input.breakout_detected
            and input.breakout_strength >= thresholds["breakout_strength_min"]
        )
        
        detected = trend_active and compressed and breakout_valid
        
        if detected:
            # Synergy strength is multiplicative - each component matters
            strength = (input.trend_strength * (1 - input.volatility_percentile) * input.breakout_strength) ** 0.33
            strength = min(1.0, strength * 1.3)  # Boost synergy
            potential = self._classify_potential(strength)
            reason = f"Trend {input.trend_direction} + Compression + Breakout = Volatility Expansion Setup"
        else:
            strength = 0.0
            potential = "LOW"
            missing = []
            if not trend_active:
                missing.append("trend")
            if not compressed:
                missing.append("compression")
            if not breakout_valid:
                missing.append("breakout")
            reason = f"Missing components: {', '.join(missing)}"
        
        return SynergyDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            potential=potential,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_flow_liquidation_cascade(self, input: FlowLiquidationInput) -> SynergyDetectionResult:
        """
        Pattern 2: Flow + Liquidation Cascade
        
        Flow pressure combined with liquidation risk creates cascade moves.
        Market can accelerate rapidly when liquidations trigger.
        """
        pattern_name = SynergyPattern.FLOW_LIQUIDATION_CASCADE.value
        thresholds = SYNERGY_THRESHOLDS["flow_liquidation"]
        
        # Check flow
        flow_strong = (
            input.flow_direction in ["BUY", "SELL"]
            and input.flow_intensity >= thresholds["flow_intensity_min"]
        )
        
        # Check liquidation risk
        liquidation_risk_high = input.liquidation_risk >= thresholds["liquidation_risk_min"]
        
        # Check alignment: flow direction should trigger opposing liquidations
        # BUY flow triggers SHORT liquidations
        # SELL flow triggers LONG liquidations
        aligned = (
            (input.flow_direction == "BUY" and input.liquidation_direction == "SHORT_LIQUIDATION") or
            (input.flow_direction == "SELL" and input.liquidation_direction == "LONG_LIQUIDATION")
        )
        
        detected = flow_strong and liquidation_risk_high and aligned
        
        if detected:
            # Cascade potential increases with leverage
            strength = (input.flow_intensity + input.liquidation_risk) / 2
            strength = min(1.0, strength * (1 + input.leverage_index * 0.3))
            potential = self._classify_potential(strength)
            cascade_type = "short squeeze" if input.flow_direction == "BUY" else "long flush"
            reason = f"Flow {input.flow_direction} + {input.liquidation_direction} = {cascade_type} cascade"
        else:
            strength = 0.0
            potential = "LOW"
            missing = []
            if not flow_strong:
                missing.append("strong flow")
            if not liquidation_risk_high:
                missing.append("liquidation risk")
            if not aligned:
                missing.append("flow-liquidation alignment")
            reason = f"Missing components: {', '.join(missing)}"
        
        return SynergyDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            potential=potential,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_volatility_expansion_trend(self, input: VolatilityTrendInput) -> SynergyDetectionResult:
        """
        Pattern 3: Volatility Expansion + Trend
        
        Expanding volatility with existing trend often leads to trend acceleration.
        """
        pattern_name = SynergyPattern.VOLATILITY_EXPANSION_TREND.value
        thresholds = SYNERGY_THRESHOLDS["volatility_trend"]
        
        # Check volatility expansion
        vol_expanding = (
            input.volatility_state in ["HIGH_VOL", "EXPANDING"]
            or input.volatility_change_rate >= thresholds["volatility_change_min"]
        )
        
        # Check trend
        trend_active = (
            input.trend_direction in ["LONG", "SHORT"]
            and input.trend_strength >= thresholds["trend_strength_min"]
        )
        
        detected = vol_expanding and trend_active
        
        if detected:
            strength = (input.volatility_change_rate + input.trend_strength) / 2
            strength = min(1.0, strength * 1.2)
            potential = self._classify_potential(strength)
            reason = f"Volatility {input.volatility_state} + Trend {input.trend_direction} = Acceleration Phase"
        else:
            strength = 0.0
            potential = "LOW"
            missing = []
            if not vol_expanding:
                missing.append("volatility expansion")
            if not trend_active:
                missing.append("trend")
            reason = f"Missing components: {', '.join(missing)}"
        
        return SynergyDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            potential=potential,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    def _detect_structure_break_momentum(self, input: StructureMomentumInput) -> SynergyDetectionResult:
        """
        Pattern 4: Structure Break + Momentum
        
        Structure break confirmed by momentum creates strong continuation setup.
        """
        pattern_name = SynergyPattern.STRUCTURE_BREAK_MOMENTUM.value
        thresholds = SYNERGY_THRESHOLDS["structure_momentum"]
        
        # Check structure break
        structure_valid = (
            input.structure_break_detected
            and input.structure_break_direction in ["BULLISH", "BEARISH"]
            and input.structure_quality >= thresholds["structure_quality_min"]
        )
        
        # Check momentum
        momentum_strong = input.momentum_strength >= thresholds["momentum_strength_min"]
        
        # Check alignment
        aligned = (
            (input.structure_break_direction == "BULLISH" and input.momentum_direction == "LONG") or
            (input.structure_break_direction == "BEARISH" and input.momentum_direction == "SHORT")
        )
        
        detected = structure_valid and momentum_strong and aligned
        
        if detected:
            strength = (input.structure_quality + input.momentum_strength) / 2
            strength = min(1.0, strength * 1.15)
            potential = self._classify_potential(strength)
            reason = f"Structure {input.structure_break_direction} + Momentum = Strong Continuation"
        else:
            strength = 0.0
            potential = "LOW"
            missing = []
            if not structure_valid:
                missing.append("valid structure break")
            if not momentum_strong:
                missing.append("strong momentum")
            if not aligned:
                missing.append("structure-momentum alignment")
            reason = f"Missing components: {', '.join(missing)}"
        
        return SynergyDetectionResult(
            pattern_name=pattern_name,
            detected=detected,
            strength=strength,
            potential=potential,
            reason=reason,
            inputs=input.to_dict(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_strength(self, pattern_results: List[SynergyDetectionResult]) -> float:
        """
        Calculate overall synergy strength from patterns.
        
        Uses weighted average of detected pattern strengths.
        """
        total_weight = 0.0
        weighted_strength = 0.0
        
        for result in pattern_results:
            if result.detected:
                weight = SYNERGY_PATTERN_WEIGHTS.get(result.pattern_name, 0.25)
                weighted_strength += result.strength * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, weighted_strength / total_weight)
    
    def _calculate_modifier(self, pattern_count: int, strength: float) -> float:
        """
        Calculate synergy modifier based on pattern count and strength.
        """
        if pattern_count == 0:
            return SYNERGY_MODIFIER_CONFIG["no_synergy"]["modifier"]
        
        if pattern_count == 1:
            config = SYNERGY_MODIFIER_CONFIG["single_synergy"]
        elif pattern_count == 2:
            config = SYNERGY_MODIFIER_CONFIG["dual_synergy"]
        else:  # 3+
            config = SYNERGY_MODIFIER_CONFIG["multi_synergy"]
        
        # Scale modifier by strength within range
        mod_min = config["modifier_min"]
        mod_max = config["modifier_max"]
        
        modifier = mod_min + (mod_max - mod_min) * strength
        
        return max(1.0, min(1.15, modifier))
    
    def _find_dominant_synergy(self, pattern_results: List[SynergyDetectionResult]) -> Optional[str]:
        """Find the strongest detected synergy pattern."""
        detected = [p for p in pattern_results if p.detected]
        
        if not detected:
            return None
        
        # Sort by potential first, then strength
        potential_order = {"EXPLOSIVE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        detected.sort(key=lambda p: (potential_order.get(p.potential, 4), -p.strength))
        return detected[0].pattern_name
    
    def _determine_potential(self, strength: float, pattern_count: int) -> str:
        """Determine overall synergy potential."""
        if pattern_count >= 3 and strength >= 0.7:
            return "EXPLOSIVE"
        elif pattern_count >= 2 and strength >= 0.6:
            return "HIGH"
        elif pattern_count >= 1 and strength >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _classify_potential(self, strength: float) -> str:
        """Classify single pattern potential from strength."""
        if strength >= 0.8:
            return "EXPLOSIVE"
        elif strength >= 0.6:
            return "HIGH"
        elif strength >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    # ═══════════════════════════════════════════════════════════
    # INPUT GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_trend_compression_input(self, symbol: str) -> TrendCompressionInput:
        """Get trend, compression, and breakout data."""
        default = TrendCompressionInput(
            trend_direction="NEUTRAL",
            trend_strength=0.5,
            volatility_state="NORMAL",
            volatility_percentile=0.5,
            breakout_detected=False,
            breakout_strength=0.0,
        )
        
        trend_dir = "NEUTRAL"
        trend_str = 0.5
        vol_state = "NORMAL"
        vol_pct = 0.5
        breakout = False
        breakout_str = 0.0
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                trend_dir = ta_result.direction.value
                trend_str = ta_result.trend_strength
                
                if ta_result.breakout_signal:
                    breakout = ta_result.breakout_signal.detected
                    breakout_str = ta_result.breakout_signal.strength
            except Exception:
                pass
        
        if self.market_state_builder:
            try:
                market_state = self.market_state_builder.build_state(symbol)
                vol_state = market_state.volatility_state.value
                vol_pct = market_state.raw_scores.get("volatility_score", 0.5)
            except Exception:
                pass
        
        return TrendCompressionInput(
            trend_direction=trend_dir,
            trend_strength=trend_str,
            volatility_state=vol_state,
            volatility_percentile=vol_pct,
            breakout_detected=breakout,
            breakout_strength=breakout_str,
        )
    
    def _get_flow_liquidation_input(self, symbol: str) -> FlowLiquidationInput:
        """Get flow and liquidation data."""
        default = FlowLiquidationInput(
            flow_direction="NEUTRAL",
            flow_intensity=0.5,
            liquidation_risk=0.3,
            liquidation_direction="NONE",
            leverage_index=0.3,
        )
        
        if self.exchange_aggregator is None:
            return default
        
        try:
            exchange = self.exchange_aggregator.aggregate(symbol)
            
            flow_dir = "NEUTRAL"
            if exchange.flow_pressure > 0.2:
                flow_dir = "BUY"
            elif exchange.flow_pressure < -0.2:
                flow_dir = "SELL"
            
            liq_dir = "NONE"
            if exchange.liquidation_risk > 0.4:
                # Flow direction determines liquidation direction
                if flow_dir == "BUY":
                    liq_dir = "SHORT_LIQUIDATION"
                elif flow_dir == "SELL":
                    liq_dir = "LONG_LIQUIDATION"
            
            return FlowLiquidationInput(
                flow_direction=flow_dir,
                flow_intensity=abs(exchange.flow_pressure),
                liquidation_risk=exchange.liquidation_risk,
                liquidation_direction=liq_dir,
                leverage_index=abs(exchange.derivatives_pressure),
            )
        except Exception:
            return default
    
    def _get_volatility_trend_input(self, symbol: str) -> VolatilityTrendInput:
        """Get volatility and trend data."""
        default = VolatilityTrendInput(
            volatility_state="NORMAL",
            volatility_change_rate=0.0,
            trend_direction="NEUTRAL",
            trend_strength=0.5,
            regime="RANGE",
        )
        
        vol_state = "NORMAL"
        vol_rate = 0.0
        trend_dir = "NEUTRAL"
        trend_str = 0.5
        regime = "RANGE"
        
        if self.ta_hypothesis_builder:
            try:
                ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
                trend_dir = ta_result.direction.value
                trend_str = ta_result.trend_strength
                regime = ta_result.regime.value
            except Exception:
                pass
        
        if self.market_state_builder:
            try:
                market_state = self.market_state_builder.build_state(symbol)
                vol_state = market_state.volatility_state.value
                # Estimate change rate from state
                if vol_state == "EXPANDING":
                    vol_rate = 0.6
                elif vol_state == "HIGH_VOL":
                    vol_rate = 0.4
                else:
                    vol_rate = 0.2
            except Exception:
                pass
        
        return VolatilityTrendInput(
            volatility_state=vol_state,
            volatility_change_rate=vol_rate,
            trend_direction=trend_dir,
            trend_strength=trend_str,
            regime=regime,
        )
    
    def _get_structure_momentum_input(self, symbol: str) -> StructureMomentumInput:
        """Get structure and momentum data."""
        default = StructureMomentumInput(
            structure_break_detected=False,
            structure_break_direction="NONE",
            structure_quality=0.5,
            momentum_direction="NEUTRAL",
            momentum_strength=0.5,
        )
        
        if self.ta_hypothesis_builder is None:
            return default
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            
            # Structure
            struct_detected = False
            struct_dir = "NONE"
            struct_qual = 0.5
            
            if ta_result.structure_signal:
                struct_detected = (
                    ta_result.structure_signal.recent_bos or
                    ta_result.structure_signal.recent_choch
                )
                if struct_detected:
                    struct_dir = ta_result.structure_signal.bias.value
                    if struct_dir == "LONG":
                        struct_dir = "BULLISH"
                    elif struct_dir == "SHORT":
                        struct_dir = "BEARISH"
                    struct_qual = ta_result.structure_signal.structure_score
            
            # Momentum
            mom_dir = "NEUTRAL"
            mom_str = 0.5
            
            if ta_result.momentum_signal:
                mom_dir = ta_result.momentum_signal.direction.value
                mom_str = ta_result.momentum_signal.strength
            
            return StructureMomentumInput(
                structure_break_detected=struct_detected,
                structure_break_direction=struct_dir,
                structure_quality=struct_qual,
                momentum_direction=mom_dir,
                momentum_strength=mom_str,
            )
        except Exception:
            return default
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_synergy_strength_for_interaction(self, symbol: str) -> Dict[str, Any]:
        """
        Get synergy strength for Interaction Engine integration.
        
        Returns strength contribution for reinforcement_score.
        """
        result = self.analyze(symbol)
        
        return {
            "synergy_strength": result.synergy_strength,
            "synergy_modifier": result.synergy_modifier,
            "synergy_patterns": result.patterns_detected,
            "synergy_count": result.pattern_count,
            "synergy_potential": result.synergy_potential,
            "dominant_synergy": result.dominant_synergy,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[SynergyEngine] = None


def get_synergy_engine() -> SynergyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = SynergyEngine()
    return _engine
