"""
PHASE 9 - Flow Pressure Engine
===============================
Evaluates short-term buying/selling pressure.

Detects:
- Building buying pressure
- Building selling pressure
- Exhaustion signals
- Absorption patterns
- Fake pushes
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from .microstructure_types import (
    PressureState, FlowPressure, FlowState, DEFAULT_MICROSTRUCTURE_CONFIG
)
from .order_flow_engine import OrderFlowSnapshot


class FlowPressureEngine:
    """
    Flow Pressure Analysis Engine
    
    Analyzes short-term pressure dynamics to identify:
    - Building momentum
    - Exhaustion points
    - Absorption (hidden strength/weakness)
    - Fake moves
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MICROSTRUCTURE_CONFIG
        self.history: List[FlowPressure] = []
        self.max_history = 100
        self.flow_history: List[OrderFlowSnapshot] = []
    
    def analyze_pressure(
        self,
        current_flow: OrderFlowSnapshot,
        recent_flows: List[OrderFlowSnapshot],
        price_change_pct: float = 0.0,
        volume_change_pct: float = 0.0,
        symbol: str = "BTCUSDT"
    ) -> FlowPressure:
        """
        Analyze flow pressure.
        
        Args:
            current_flow: Current flow snapshot
            recent_flows: Recent flow history (for trend analysis)
            price_change_pct: Recent price change (%)
            volume_change_pct: Recent volume change (%)
            symbol: Trading symbol
            
        Returns:
            FlowPressure analysis
        """
        now = datetime.now(timezone.utc)
        
        if not recent_flows:
            recent_flows = [current_flow]
        
        # Update flow history
        self.flow_history = recent_flows[-self.config["persistence_window"]:]
        
        # Determine pressure direction
        pressure_direction = self._determine_direction(current_flow, recent_flows)
        
        # Calculate pressure strength
        pressure_strength = self._calculate_strength(current_flow, recent_flows)
        
        # Detect exhaustion
        exhaustion_prob, exhaustion_type = self._detect_exhaustion(
            recent_flows, price_change_pct, volume_change_pct
        )
        
        # Detect building pressure
        building_detected, building_direction = self._detect_building(recent_flows)
        
        # Calculate absorption
        absorption_score = self._calculate_absorption(
            current_flow, price_change_pct, volume_change_pct
        )
        
        # Detect fake push
        fake_push_prob = self._detect_fake_push(
            current_flow, recent_flows, price_change_pct
        )
        
        # Calculate persistence
        persistence = self._calculate_persistence(recent_flows)
        
        # Determine pressure state
        pressure_state = self._determine_state(
            pressure_direction,
            pressure_strength,
            exhaustion_prob,
            exhaustion_type,
            building_detected,
            absorption_score,
            fake_push_prob
        )
        
        pressure = FlowPressure(
            symbol=symbol,
            timestamp=now,
            flow_pressure_state=pressure_state,
            pressure_direction=pressure_direction,
            pressure_strength=pressure_strength,
            exhaustion_probability=exhaustion_prob,
            exhaustion_type=exhaustion_type,
            building_detected=building_detected,
            building_direction=building_direction,
            absorption_score=absorption_score,
            fake_push_probability=fake_push_prob,
            pressure_persistence=persistence
        )
        
        # Save to history
        self._add_to_history(pressure)
        
        return pressure
    
    def _determine_direction(
        self,
        current: OrderFlowSnapshot,
        history: List[OrderFlowSnapshot]
    ) -> str:
        """Determine overall pressure direction."""
        # Weight recent flows more heavily
        if len(history) < 3:
            return "UP" if current.flow_ratio > 0.55 else "DOWN" if current.flow_ratio < 0.45 else "NEUTRAL"
        
        # Calculate weighted average
        weights = [1, 2, 3, 4, 5]  # Most recent = highest weight
        recent = history[-5:] if len(history) >= 5 else history
        
        weighted_sum = sum(
            f.flow_ratio * weights[i] for i, f in enumerate(recent[-len(weights):])
        )
        total_weight = sum(weights[:len(recent)])
        weighted_avg = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        if weighted_avg > 0.55:
            return "UP"
        elif weighted_avg < 0.45:
            return "DOWN"
        return "NEUTRAL"
    
    def _calculate_strength(
        self,
        current: OrderFlowSnapshot,
        history: List[OrderFlowSnapshot]
    ) -> float:
        """Calculate pressure strength (0-1)."""
        # Factors: flow ratio deviation, aggression, persistence
        
        # Flow ratio strength (how far from 0.5)
        ratio_strength = abs(current.flow_ratio - 0.5) * 2
        
        # Aggression strength
        aggression_strength = abs(current.aggression_score)
        
        # Consistency with history
        if len(history) >= 3:
            recent_ratios = [f.flow_ratio for f in history[-3:]]
            direction_consistent = all(
                (r > 0.5) == (current.flow_ratio > 0.5) for r in recent_ratios
            )
            consistency_bonus = 0.2 if direction_consistent else 0
        else:
            consistency_bonus = 0
        
        strength = ratio_strength * 0.4 + aggression_strength * 0.4 + consistency_bonus
        
        return min(1.0, strength)
    
    def _detect_exhaustion(
        self,
        history: List[OrderFlowSnapshot],
        price_change: float,
        volume_change: float
    ) -> tuple:
        """
        Detect exhaustion signals.
        
        Returns: (probability, type)
        """
        if len(history) < 3:
            return 0.0, None
        
        recent = history[-5:]
        
        # Check for declining strength despite continued direction
        ratios = [f.flow_ratio for f in recent]
        aggressions = [f.aggression_score for f in recent]
        
        # Buyer exhaustion: ratio declining but still above 0.5
        if all(r > 0.5 for r in ratios):
            if ratios[-1] < ratios[-3]:  # Declining ratio
                # High volume + low price change = exhaustion
                if volume_change > 0.2 and abs(price_change) < 0.1:
                    return 0.7, "BUY"
                # Declining aggression
                if aggressions[-1] < aggressions[-3] * 0.7:
                    return 0.6, "BUY"
        
        # Seller exhaustion: ratio rising but still below 0.5
        if all(r < 0.5 for r in ratios):
            if ratios[-1] > ratios[-3]:  # Rising ratio
                if volume_change > 0.2 and abs(price_change) < 0.1:
                    return 0.7, "SELL"
                if aggressions[-1] > aggressions[-3] * 0.7:  # Less negative
                    return 0.6, "SELL"
        
        return 0.0, None
    
    def _detect_building(
        self,
        history: List[OrderFlowSnapshot]
    ) -> tuple:
        """
        Detect building pressure.
        
        Returns: (detected, direction)
        """
        if len(history) < 3:
            return False, None
        
        recent = history[-5:]
        ratios = [f.flow_ratio for f in recent]
        
        # Building buy pressure: consistently increasing ratio
        if all(ratios[i] < ratios[i+1] for i in range(len(ratios)-1)):
            if ratios[-1] > 0.55:
                return True, "UP"
        
        # Building sell pressure: consistently decreasing ratio
        if all(ratios[i] > ratios[i+1] for i in range(len(ratios)-1)):
            if ratios[-1] < 0.45:
                return True, "DOWN"
        
        return False, None
    
    def _calculate_absorption(
        self,
        current: OrderFlowSnapshot,
        price_change: float,
        volume_change: float
    ) -> float:
        """
        Calculate absorption score.
        
        High absorption = large volume absorbed with small price impact
        """
        if not current.absorption_detected:
            return 0.0
        
        # Absorption indicator: high volume, low price movement
        if abs(price_change) < 0.1 and volume_change > 0.3:
            return 0.7 + min(0.3, volume_change * 0.5)
        
        return 0.3 if current.absorption_detected else 0.0
    
    def _detect_fake_push(
        self,
        current: OrderFlowSnapshot,
        history: List[OrderFlowSnapshot],
        price_change: float
    ) -> float:
        """
        Detect fake push (move without conviction).
        
        Signs:
        - Strong price move
        - Weak flow support
        - Low aggression
        - Quick reversal in flow
        """
        if len(history) < 2:
            return 0.0
        
        prob = 0.0
        
        # Strong price move
        if abs(price_change) > 0.3:
            # But flow ratio is moderate
            if 0.4 < current.flow_ratio < 0.6:
                prob += 0.3
            
            # And aggression doesn't match direction
            if price_change > 0 and current.aggression_score < 0:
                prob += 0.2
            elif price_change < 0 and current.aggression_score > 0:
                prob += 0.2
        
        # Flow reversal: direction changed from last period
        prev = history[-2] if len(history) >= 2 else history[-1]
        if (current.flow_ratio > 0.5) != (prev.flow_ratio > 0.5):
            prob += 0.2
        
        return min(1.0, prob)
    
    def _calculate_persistence(
        self,
        history: List[OrderFlowSnapshot]
    ) -> float:
        """Calculate how persistent the current pressure is."""
        if len(history) < 2:
            return 0.0
        
        window = self.config["persistence_window"]
        recent = history[-window:]
        
        # Count consecutive same-direction periods
        if not recent:
            return 0.0
        
        current_direction = recent[-1].flow_ratio > 0.5
        consecutive = 0
        
        for f in reversed(recent):
            if (f.flow_ratio > 0.5) == current_direction:
                consecutive += 1
            else:
                break
        
        return consecutive / window
    
    def _determine_state(
        self,
        direction: str,
        strength: float,
        exhaustion_prob: float,
        exhaustion_type: Optional[str],
        building: bool,
        absorption: float,
        fake_push: float
    ) -> PressureState:
        """Determine overall pressure state."""
        
        # Fake push takes priority
        if fake_push > 0.6:
            return PressureState.FAKE_PUSH
        
        # Absorption takes priority
        if absorption > 0.6:
            return PressureState.ABSORPTION
        
        # Exhaustion
        if exhaustion_prob > self.config["exhaustion_threshold"]:
            if exhaustion_type == "BUY":
                return PressureState.EXHAUSTION_BUY
            else:
                return PressureState.EXHAUSTION_SELL
        
        # Building pressure
        if building and strength > 0.4:
            if direction == "UP":
                return PressureState.BUILDING_BUY
            else:
                return PressureState.BUILDING_SELL
        
        return PressureState.NEUTRAL
    
    def _add_to_history(self, pressure: FlowPressure):
        """Add pressure to history."""
        self.history.append(pressure)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_pressure_summary(self, periods: int = 10) -> Dict:
        """Get summary of recent pressure analysis."""
        if len(self.history) < periods:
            return {"summary": "INSUFFICIENT_DATA", "periods": len(self.history)}
        
        recent = self.history[-periods:]
        
        # Count states
        state_counts = {}
        for p in recent:
            s = p.flow_pressure_state.value
            state_counts[s] = state_counts.get(s, 0) + 1
        
        # Calculate averages
        avg_strength = sum(p.pressure_strength for p in recent) / len(recent)
        avg_exhaustion = sum(p.exhaustion_probability for p in recent) / len(recent)
        
        # Dominant direction
        up_count = sum(1 for p in recent if p.pressure_direction == "UP")
        down_count = sum(1 for p in recent if p.pressure_direction == "DOWN")
        
        if up_count > down_count * 1.5:
            dominant = "UP"
        elif down_count > up_count * 1.5:
            dominant = "DOWN"
        else:
            dominant = "MIXED"
        
        return {
            "dominant_direction": dominant,
            "avg_strength": round(avg_strength, 3),
            "avg_exhaustion_prob": round(avg_exhaustion, 3),
            "state_distribution": state_counts,
            "current_state": recent[-1].flow_pressure_state.value,
            "periods": periods
        }
