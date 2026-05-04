"""
PHASE 9 - Execution Timing Engine
==================================
Recommends optimal execution timing based on microstructure.

Signals:
- ENTER_NOW: Good conditions, enter
- WAIT_PULLBACK: Wait for better price
- PARTIAL_ENTRY: Enter partial position
- REDUCE_ONLY: Only reduce, don't add
- EXIT_NOW: Conditions deteriorating, exit
- HOLD: No action needed
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone

from .microstructure_types import (
    TimingSignal, ExecutionTiming, FlowState, AggressorSide,
    ImbalanceType, PressureState, DEFAULT_MICROSTRUCTURE_CONFIG
)
from .order_flow_engine import OrderFlowSnapshot
from .aggressor_detector import AggressorAnalysis
from .micro_imbalance_engine import MicroImbalance
from .flow_pressure_engine import FlowPressure


class ExecutionTimingEngine:
    """
    Execution Timing Recommendation Engine
    
    Analyzes microstructure conditions to recommend:
    - Whether to enter now
    - How much to enter
    - Whether to wait for better conditions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MICROSTRUCTURE_CONFIG
        self.history: List[ExecutionTiming] = []
        self.max_history = 100
    
    def calculate_timing(
        self,
        flow: OrderFlowSnapshot,
        aggressor: AggressorAnalysis,
        imbalance: MicroImbalance,
        pressure: FlowPressure,
        intended_direction: str,  # LONG or SHORT
        spread_bps: float = 1.0,
        symbol: str = "BTCUSDT"
    ) -> ExecutionTiming:
        """
        Calculate execution timing recommendation.
        
        Args:
            flow: Order flow analysis
            aggressor: Aggressor detection results
            imbalance: Micro-imbalance analysis
            pressure: Flow pressure analysis
            intended_direction: LONG or SHORT
            spread_bps: Current spread in basis points
            symbol: Trading symbol
            
        Returns:
            ExecutionTiming with recommendations
        """
        now = datetime.now(timezone.utc)
        
        # Check factor alignment
        flow_aligned = self._check_flow_alignment(flow, intended_direction)
        aggressor_aligned = self._check_aggressor_alignment(aggressor, intended_direction)
        imbalance_aligned = self._check_imbalance_alignment(imbalance, intended_direction)
        pressure_aligned = self._check_pressure_alignment(pressure, intended_direction)
        
        # Check spread and liquidity
        spread_favorable = spread_bps < 3.0  # Less than 3 bps is favorable
        liquidity_available = imbalance.vacuum_risk < 0.5
        
        # Count aligned factors
        aligned_count = sum([
            flow_aligned,
            aggressor_aligned,
            imbalance_aligned,
            pressure_aligned,
            spread_favorable,
            liquidity_available
        ])
        
        # Calculate timing quality (0-1)
        timing_quality = aligned_count / 6.0
        
        # Calculate urgency based on conditions
        urgency_score = self._calculate_urgency(flow, pressure, intended_direction)
        
        # Calculate execution readiness
        execution_readiness = timing_quality * 0.6 + (1 - urgency_score * 0.5) * 0.4
        
        # Determine signal and entry size
        signal, entry_size, delay_ms, notes = self._determine_signal(
            timing_quality,
            urgency_score,
            aligned_count,
            flow,
            aggressor,
            imbalance,
            pressure,
            intended_direction
        )
        
        timing = ExecutionTiming(
            symbol=symbol,
            timestamp=now,
            timing_signal=signal,
            timing_quality=timing_quality,
            urgency_score=urgency_score,
            execution_readiness=execution_readiness,
            micro_flow_aligned=flow_aligned,
            spread_favorable=spread_favorable,
            liquidity_available=liquidity_available,
            aggressor_aligned=aggressor_aligned,
            entry_size_pct=entry_size,
            delay_recommendation_ms=delay_ms,
            notes=notes
        )
        
        # Save to history
        self._add_to_history(timing)
        
        return timing
    
    def _check_flow_alignment(self, flow: OrderFlowSnapshot, direction: str) -> bool:
        """Check if flow aligns with intended direction."""
        if direction == "LONG":
            return flow.flow_state in [FlowState.BUYER_DOMINANT, FlowState.BURST_BUY]
        else:
            return flow.flow_state in [FlowState.SELLER_DOMINANT, FlowState.BURST_SELL]
    
    def _check_aggressor_alignment(self, aggressor: AggressorAnalysis, direction: str) -> bool:
        """Check if aggressor aligns with intended direction."""
        if direction == "LONG":
            return aggressor.aggressor_side == AggressorSide.BUYER
        else:
            return aggressor.aggressor_side == AggressorSide.SELLER
    
    def _check_imbalance_alignment(self, imbalance: MicroImbalance, direction: str) -> bool:
        """Check if imbalance aligns with intended direction."""
        if direction == "LONG":
            return imbalance.dominant_micro_side == "BID" or \
                   imbalance.imbalance_type == ImbalanceType.BID_DOMINANT
        else:
            return imbalance.dominant_micro_side == "ASK" or \
                   imbalance.imbalance_type == ImbalanceType.ASK_DOMINANT
    
    def _check_pressure_alignment(self, pressure: FlowPressure, direction: str) -> bool:
        """Check if pressure aligns with intended direction."""
        if direction == "LONG":
            return pressure.pressure_direction == "UP" and \
                   pressure.flow_pressure_state not in [PressureState.EXHAUSTION_BUY]
        else:
            return pressure.pressure_direction == "DOWN" and \
                   pressure.flow_pressure_state not in [PressureState.EXHAUSTION_SELL]
    
    def _calculate_urgency(
        self,
        flow: OrderFlowSnapshot,
        pressure: FlowPressure,
        direction: str
    ) -> float:
        """
        Calculate urgency score.
        
        High urgency = should act now
        Low urgency = can wait
        """
        urgency = 0.5  # Base
        
        # Burst activity increases urgency
        if flow.burst_detected:
            if (direction == "LONG" and flow.burst_direction == "BUY") or \
               (direction == "SHORT" and flow.burst_direction == "SELL"):
                urgency += 0.2
            else:
                urgency -= 0.1  # Wrong direction burst
        
        # Building pressure increases urgency
        if pressure.building_detected:
            if (direction == "LONG" and pressure.building_direction == "UP") or \
               (direction == "SHORT" and pressure.building_direction == "DOWN"):
                urgency += 0.15
        
        # Exhaustion reduces urgency (wait for confirmation)
        if pressure.exhaustion_probability > 0.6:
            urgency -= 0.2
        
        # Fake push reduces urgency significantly
        if pressure.fake_push_probability > 0.5:
            urgency -= 0.3
        
        return max(0, min(1, urgency))
    
    def _determine_signal(
        self,
        quality: float,
        urgency: float,
        aligned: int,
        flow: OrderFlowSnapshot,
        aggressor: AggressorAnalysis,
        imbalance: MicroImbalance,
        pressure: FlowPressure,
        direction: str
    ) -> tuple:
        """Determine timing signal, entry size, delay, and notes."""
        notes = []
        
        # Excellent conditions
        if quality >= 0.8 and aligned >= 5:
            signal = TimingSignal.ENTER_NOW
            entry_size = 100.0
            delay = 0
            notes.append("All microstructure factors aligned")
            notes.append(f"Flow: {flow.flow_state.value}")
            return signal, entry_size, delay, notes
        
        # Good conditions
        if quality >= 0.6 and aligned >= 4:
            signal = TimingSignal.ENTER_NOW
            entry_size = 80.0
            delay = 0
            notes.append("Most factors aligned, good entry conditions")
            return signal, entry_size, delay, notes
        
        # Mixed conditions - partial entry
        if quality >= 0.4 and aligned >= 3:
            signal = TimingSignal.PARTIAL_ENTRY
            entry_size = 50.0
            delay = 0
            notes.append("Mixed signals, consider partial position")
            
            if not self._check_flow_alignment(flow, direction):
                notes.append(f"Flow not aligned: {flow.flow_state.value}")
            if not self._check_aggressor_alignment(aggressor, direction):
                notes.append(f"Aggressor against: {aggressor.aggressor_side.value}")
            
            return signal, entry_size, delay, notes
        
        # Poor flow - wait for pullback
        if flow.flow_state in [FlowState.CHOPPY]:
            signal = TimingSignal.WAIT_PULLBACK
            entry_size = 0.0
            delay = 5000  # Wait 5 seconds
            notes.append("Choppy flow, wait for stabilization")
            return signal, entry_size, delay, notes
        
        # Exhaustion detected
        if pressure.exhaustion_probability > self.config["exhaustion_threshold"]:
            if (direction == "LONG" and pressure.exhaustion_type == "BUY") or \
               (direction == "SHORT" and pressure.exhaustion_type == "SELL"):
                signal = TimingSignal.REDUCE_ONLY
                entry_size = 0.0
                delay = 10000
                notes.append(f"{pressure.exhaustion_type} exhaustion detected")
                return signal, entry_size, delay, notes
        
        # Vacuum risk - reduce only
        if imbalance.vacuum_risk > 0.6:
            signal = TimingSignal.REDUCE_ONLY
            entry_size = 0.0
            delay = 5000
            notes.append("Liquidity vacuum detected, high slippage risk")
            return signal, entry_size, delay, notes
        
        # Counter-trend conditions - might want to exit
        if aligned <= 1 and quality < 0.3:
            # Check if this is strong counter signal
            if (direction == "LONG" and flow.flow_state == FlowState.SELLER_DOMINANT) or \
               (direction == "SHORT" and flow.flow_state == FlowState.BUYER_DOMINANT):
                signal = TimingSignal.EXIT_NOW
                entry_size = 0.0
                delay = 0
                notes.append("Strong counter-flow, consider exit")
                return signal, entry_size, delay, notes
        
        # Default: wait
        signal = TimingSignal.WAIT_PULLBACK
        entry_size = 0.0
        delay = 3000
        notes.append("Conditions not optimal, waiting")
        
        return signal, entry_size, delay, notes
    
    def _add_to_history(self, timing: ExecutionTiming):
        """Add timing to history."""
        self.history.append(timing)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_timing_summary(self, periods: int = 10) -> Dict:
        """Get summary of recent timing signals."""
        if len(self.history) < periods:
            return {"summary": "INSUFFICIENT_DATA", "periods": len(self.history)}
        
        recent = self.history[-periods:]
        
        # Count signals
        signal_counts = {}
        for t in recent:
            s = t.timing_signal.value
            signal_counts[s] = signal_counts.get(s, 0) + 1
        
        # Calculate averages
        avg_quality = sum(t.timing_quality for t in recent) / len(recent)
        avg_readiness = sum(t.execution_readiness for t in recent) / len(recent)
        
        return {
            "avg_timing_quality": round(avg_quality, 3),
            "avg_execution_readiness": round(avg_readiness, 3),
            "signal_distribution": signal_counts,
            "current_signal": recent[-1].timing_signal.value,
            "periods": periods
        }
