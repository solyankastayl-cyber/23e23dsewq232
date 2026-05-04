"""
Liquidation Cascade Probability — Engine

PHASE 28.4 — Core logic for liquidation cascade detection.

Features:
- Cascade direction detection (UP/DOWN/NONE)
- Cascade probability calculation with alignment multiplier
- Severity classification (LOW/MEDIUM/HIGH/EXTREME)
- State classification (STABLE/BUILDING/ACTIVE/CRITICAL)
- Integration with MicrostructureSnapshot, LiquidityVacuumState, OrderbookPressureMap
"""

from typing import Optional, Dict, Tuple
from datetime import datetime
import random

from .liquidation_cascade_types import (
    LiquidationCascadeState,
    CascadeInputContext,
    CascadeDirection,
    CascadeSeverity,
    CascadeState,
    CASCADE_WEIGHT_LIQUIDATION,
    CASCADE_WEIGHT_VACUUM,
    CASCADE_WEIGHT_SWEEP,
    CASCADE_WEIGHT_DEPTH,
    ALIGNMENT_FULL,
    ALIGNMENT_PARTIAL,
    ALIGNMENT_CONFLICT,
    SEVERITY_LOW_THRESHOLD,
    SEVERITY_MEDIUM_THRESHOLD,
    SEVERITY_HIGH_THRESHOLD,
    CONF_WEIGHT_LIQUIDATION,
    CONF_WEIGHT_VACUUM,
    CONF_WEIGHT_SWEEP,
    CONF_WEIGHT_ALIGNMENT,
)

from .microstructure_snapshot_engine import get_microstructure_snapshot_engine
from .liquidity_vacuum_engine import get_liquidity_vacuum_engine
from .orderbook_pressure_engine import get_orderbook_pressure_engine


class LiquidationCascadeEngine:
    """
    Liquidation Cascade Detection Engine.
    
    Aggregates microstructure signals to detect cascade probability.
    """
    
    def __init__(self):
        self._current_states: Dict[str, LiquidationCascadeState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Direction Detection
    # ═══════════════════════════════════════════════════════════
    
    def detect_cascade_direction(
        self,
        liquidation_pressure: float,
        vacuum_direction: str,
        sweep_risk: str,
        pressure_bias: str,
    ) -> CascadeDirection:
        """
        Detect cascade direction based on signal alignment.
        
        UP cascade: bullish liquidation + UP vacuum + UP sweep + BID_DOMINANT
        DOWN cascade: bearish liquidation + DOWN vacuum + DOWN sweep + ASK_DOMINANT
        NONE: signals not aligned
        """
        # Count UP signals
        up_signals = 0
        if liquidation_pressure > 0.15:  # Bullish (shorts squeezed)
            up_signals += 1
        if vacuum_direction == "UP":
            up_signals += 1
        if sweep_risk == "UP":
            up_signals += 1
        if pressure_bias == "BID_DOMINANT":
            up_signals += 1
        
        # Count DOWN signals
        down_signals = 0
        if liquidation_pressure < -0.15:  # Bearish (longs flushed)
            down_signals += 1
        if vacuum_direction == "DOWN":
            down_signals += 1
        if sweep_risk == "DOWN":
            down_signals += 1
        if pressure_bias == "ASK_DOMINANT":
            down_signals += 1
        
        # Determine direction
        if up_signals >= 2 and up_signals > down_signals:
            return "UP"
        elif down_signals >= 2 and down_signals > up_signals:
            return "DOWN"
        else:
            return "NONE"
    
    # ═══════════════════════════════════════════════════════════
    # Alignment Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_alignment_score(
        self,
        liquidation_pressure: float,
        vacuum_direction: str,
        sweep_risk: str,
        pressure_bias: str,
    ) -> Tuple[float, float]:
        """
        Calculate alignment score and multiplier.
        
        Returns: (alignment_score, multiplier)
        
        alignment_score: 0.0 to 1.0 (how aligned signals are)
        multiplier: 0.75 to 1.15 (cascade probability multiplier)
        """
        # Determine dominant direction
        up_signals = 0
        down_signals = 0
        neutral_signals = 0
        
        # Liquidation pressure
        if liquidation_pressure > 0.15:
            up_signals += 1
        elif liquidation_pressure < -0.15:
            down_signals += 1
        else:
            neutral_signals += 1
        
        # Vacuum direction
        if vacuum_direction == "UP":
            up_signals += 1
        elif vacuum_direction == "DOWN":
            down_signals += 1
        else:
            neutral_signals += 1
        
        # Sweep risk
        if sweep_risk == "UP":
            up_signals += 1
        elif sweep_risk == "DOWN":
            down_signals += 1
        else:
            neutral_signals += 1
        
        # Pressure bias
        if pressure_bias == "BID_DOMINANT":
            up_signals += 1
        elif pressure_bias == "ASK_DOMINANT":
            down_signals += 1
        else:
            neutral_signals += 1
        
        # Calculate alignment
        max_directional = max(up_signals, down_signals)
        total_directional = up_signals + down_signals
        
        if total_directional == 0:
            return 0.0, ALIGNMENT_CONFLICT
        
        # Alignment based on how many signals agree
        if max_directional >= 3:
            alignment_score = 1.0
            multiplier = ALIGNMENT_FULL
        elif max_directional == 2:
            alignment_score = 0.66
            multiplier = ALIGNMENT_PARTIAL
        elif max_directional == 1:
            alignment_score = 0.33
            multiplier = ALIGNMENT_CONFLICT
        else:
            alignment_score = 0.0
            multiplier = ALIGNMENT_CONFLICT
        
        return alignment_score, multiplier
    
    # ═══════════════════════════════════════════════════════════
    # Cascade Probability
    # ═══════════════════════════════════════════════════════════
    
    def calculate_cascade_probability(
        self,
        liquidation_pressure: float,
        vacuum_probability: float,
        sweep_probability: float,
        depth_score: float,
        alignment_multiplier: float,
    ) -> float:
        """
        Calculate cascade probability.
        
        Base formula:
        0.40 * abs(liquidation_pressure) +
        0.30 * vacuum_probability +
        0.20 * sweep_probability +
        0.10 * (1 - depth_score)
        
        Then multiply by alignment multiplier.
        """
        base_prob = (
            CASCADE_WEIGHT_LIQUIDATION * abs(liquidation_pressure) +
            CASCADE_WEIGHT_VACUUM * vacuum_probability +
            CASCADE_WEIGHT_SWEEP * sweep_probability +
            CASCADE_WEIGHT_DEPTH * (1 - depth_score)
        )
        
        # Apply alignment multiplier
        adjusted_prob = base_prob * alignment_multiplier
        
        return round(min(max(adjusted_prob, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Severity Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_severity(
        self,
        cascade_probability: float,
    ) -> CascadeSeverity:
        """
        Classify cascade severity based on probability.
        
        LOW: p < 0.25
        MEDIUM: 0.25 <= p < 0.45
        HIGH: 0.45 <= p < 0.70
        EXTREME: p >= 0.70
        """
        if cascade_probability >= SEVERITY_HIGH_THRESHOLD:
            return "EXTREME"
        elif cascade_probability >= SEVERITY_MEDIUM_THRESHOLD:
            return "HIGH"
        elif cascade_probability >= SEVERITY_LOW_THRESHOLD:
            return "MEDIUM"
        else:
            return "LOW"
    
    # ═══════════════════════════════════════════════════════════
    # State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_cascade_state(
        self,
        cascade_direction: CascadeDirection,
        cascade_severity: CascadeSeverity,
        depth_score: float,
        alignment_score: float,
    ) -> CascadeState:
        """
        Classify cascade state.
        
        STABLE: LOW severity, no direction
        BUILDING: MEDIUM severity, direction visible
        ACTIVE: HIGH severity, direction aligned
        CRITICAL: EXTREME severity, thin liquidity + strong alignment
        """
        # CRITICAL: extreme severity with thin liquidity and good alignment
        if cascade_severity == "EXTREME" and depth_score < 0.5 and alignment_score >= 0.66:
            return "CRITICAL"
        
        # ACTIVE: high severity with direction
        if cascade_severity == "HIGH" and cascade_direction != "NONE":
            return "ACTIVE"
        
        # Also ACTIVE for extreme without full conditions
        if cascade_severity == "EXTREME":
            return "ACTIVE"
        
        # BUILDING: medium severity with visible direction
        if cascade_severity == "MEDIUM" and cascade_direction != "NONE":
            return "BUILDING"
        
        # BUILDING: medium severity even without clear direction
        if cascade_severity == "MEDIUM":
            return "BUILDING"
        
        # STABLE: low severity
        return "STABLE"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        liquidation_pressure: float,
        vacuum_probability: float,
        sweep_probability: float,
        alignment_score: float,
    ) -> float:
        """
        Calculate confidence in cascade assessment.
        
        Formula:
        0.35 * abs(liquidation_pressure) +
        0.25 * vacuum_probability +
        0.20 * sweep_probability +
        0.20 * alignment_score
        """
        conf = (
            CONF_WEIGHT_LIQUIDATION * abs(liquidation_pressure) +
            CONF_WEIGHT_VACUUM * vacuum_probability +
            CONF_WEIGHT_SWEEP * sweep_probability +
            CONF_WEIGHT_ALIGNMENT * alignment_score
        )
        return round(min(max(conf, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        cascade_direction: CascadeDirection,
        liquidation_pressure: float,
        vacuum_direction: str,
        pressure_bias: str,
        alignment_score: float,
    ) -> str:
        """Generate human-readable reason for cascade state."""
        
        if cascade_direction == "UP":
            liq_desc = "short-side pressure" if liquidation_pressure > 0 else "liquidation pressure"
            return f"{liq_desc}, upside vacuum and bid-dominant sweep setup increase risk of upward liquidation cascade"
        
        elif cascade_direction == "DOWN":
            liq_desc = "long-side liquidation pressure" if liquidation_pressure < 0 else "liquidation pressure"
            return f"{liq_desc}, downside vacuum and ask-dominant pressure increase risk of downward cascade"
        
        else:
            if alignment_score < 0.5:
                return "liquidation, vacuum and pressure signals are not aligned enough for cascade formation"
            else:
                return "mixed signals with partial alignment, cascade risk present but direction unclear"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build
    # ═══════════════════════════════════════════════════════════
    
    def build_cascade_state(
        self,
        symbol: str,
        context: CascadeInputContext,
    ) -> LiquidationCascadeState:
        """
        Build liquidation cascade state from aggregated context.
        """
        # Detect direction
        cascade_direction = self.detect_cascade_direction(
            context.liquidation_pressure,
            context.vacuum_direction,
            context.sweep_risk,
            context.pressure_bias,
        )
        
        # Calculate alignment
        alignment_score, alignment_multiplier = self.calculate_alignment_score(
            context.liquidation_pressure,
            context.vacuum_direction,
            context.sweep_risk,
            context.pressure_bias,
        )
        
        # Calculate probability
        cascade_probability = self.calculate_cascade_probability(
            context.liquidation_pressure,
            context.vacuum_probability,
            context.sweep_probability,
            context.depth_score,
            alignment_multiplier,
        )
        
        # Classify severity
        cascade_severity = self.classify_severity(cascade_probability)
        
        # Classify state
        cascade_state = self.classify_cascade_state(
            cascade_direction,
            cascade_severity,
            context.depth_score,
            alignment_score,
        )
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            context.liquidation_pressure,
            context.vacuum_probability,
            context.sweep_probability,
            alignment_score,
        )
        
        # Generate reason
        reason = self.generate_reason(
            cascade_direction,
            context.liquidation_pressure,
            context.vacuum_direction,
            context.pressure_bias,
            alignment_score,
        )
        
        state = LiquidationCascadeState(
            symbol=symbol,
            cascade_direction=cascade_direction,
            cascade_probability=cascade_probability,
            liquidation_pressure=context.liquidation_pressure,
            vacuum_probability=context.vacuum_probability,
            sweep_probability=context.sweep_probability,
            cascade_severity=cascade_severity,
            cascade_state=cascade_state,
            confidence=confidence,
            reason=reason,
        )
        
        self._current_states[symbol] = state
        return state
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Build
    # ═══════════════════════════════════════════════════════════
    
    def build_cascade_state_simulated(
        self,
        symbol: str = "BTC",
    ) -> LiquidationCascadeState:
        """
        Build cascade state using data from existing engines.
        """
        ms_engine = get_microstructure_snapshot_engine()
        vacuum_engine = get_liquidity_vacuum_engine()
        pressure_engine = get_orderbook_pressure_engine()
        
        # Get or build snapshots
        ms_snapshot = ms_engine.get_snapshot(symbol)
        if not ms_snapshot:
            ms_snapshot = ms_engine.build_snapshot_simulated(symbol)
        
        vacuum_state = vacuum_engine.get_vacuum_state(symbol)
        if not vacuum_state:
            vacuum_state = vacuum_engine.build_vacuum_state_simulated(symbol)
        
        pressure_map = pressure_engine.get_pressure_map(symbol)
        if not pressure_map:
            pressure_map = pressure_engine.build_pressure_map_simulated(symbol)
        
        # Build context
        context = CascadeInputContext(
            liquidation_pressure=ms_snapshot.liquidation_pressure,
            funding_pressure=ms_snapshot.funding_pressure,
            oi_pressure=ms_snapshot.oi_pressure,
            depth_score=ms_snapshot.depth_score,
            vacuum_direction=vacuum_state.vacuum_direction,
            vacuum_probability=vacuum_state.vacuum_probability,
            liquidity_state=vacuum_state.liquidity_state,
            pressure_bias=pressure_map.pressure_bias,
            sweep_risk=pressure_map.sweep_risk,
            sweep_probability=pressure_map.sweep_probability,
            pressure_state=pressure_map.pressure_state,
        )
        
        return self.build_cascade_state(symbol, context)
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_cascade_state(
        self,
        symbol: str,
    ) -> Optional[LiquidationCascadeState]:
        """Get cached cascade state for symbol."""
        return self._current_states.get(symbol)
    
    def get_all_cascade_states(self) -> Dict[str, LiquidationCascadeState]:
        """Get all cached cascade states."""
        return self._current_states.copy()


# Singleton
_engine: Optional[LiquidationCascadeEngine] = None


def get_liquidation_cascade_engine() -> LiquidationCascadeEngine:
    """Get singleton instance of LiquidationCascadeEngine."""
    global _engine
    if _engine is None:
        _engine = LiquidationCascadeEngine()
    return _engine
