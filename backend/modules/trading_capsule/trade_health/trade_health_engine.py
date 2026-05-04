"""
Advanced Trade Health Engine
============================

PHASE 3.2 - Enhanced health monitoring with events, decay, and stability.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .health_types import (
    HealthStatus,
    EventType,
    AdvancedTradeHealthScore,
    HealthEvent,
    TradeStabilityScore
)


class AdvancedTradeHealthEngine:
    """
    Advanced Trade Health Engine with:
    - Multi-component health calculation
    - Real-time event detection
    - Health decay modeling
    - Stability scoring
    - Recovery blocking logic
    """
    
    def __init__(self):
        # Health thresholds
        self._thresholds = {
            HealthStatus.EXCELLENT: 80,
            HealthStatus.GOOD: 60,
            HealthStatus.STABLE: 40,
            HealthStatus.WEAK: 20,
            HealthStatus.CRITICAL: 10,
            HealthStatus.TERMINAL: 0
        }
        
        # Component weights
        self._weights = {
            "price_action": 0.25,
            "structure": 0.20,
            "momentum": 0.15,
            "time": 0.10,
            "pnl": 0.20,
            "volatility": 0.10
        }
        
        # Action mapping
        self._action_map = {
            HealthStatus.EXCELLENT: ("HOLD", "LOW"),
            HealthStatus.GOOD: ("HOLD", "LOW"),
            HealthStatus.STABLE: ("MONITOR", "LOW"),
            HealthStatus.WEAK: ("REDUCE", "MEDIUM"),
            HealthStatus.CRITICAL: ("CLOSE", "HIGH"),
            HealthStatus.TERMINAL: ("CLOSE", "IMMEDIATE")
        }
        
        # Track position health history
        self._health_history: Dict[str, List[float]] = {}
        
        print("[AdvancedTradeHealthEngine] Initialized (PHASE 3.2)")
    
    def calculate_health(
        self,
        position_id: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str,
        bars_in_trade: int,
        max_bars: int = 100,
        previous_health: float = 100.0,
        indicators: Optional[Dict[str, float]] = None,
        events: Optional[List[HealthEvent]] = None,
        decay_applied: float = 0.0
    ) -> AdvancedTradeHealthScore:
        """
        Calculate comprehensive trade health score.
        """
        
        indicators = indicators or {}
        events = events or []
        
        health = AdvancedTradeHealthScore(
            position_id=position_id,
            previous_health=previous_health,
            computed_at=int(time.time() * 1000)
        )
        
        # Calculate component healths
        health.pnl_health = self._calculate_pnl_health(
            entry_price, current_price, stop_price, target_price, direction
        )
        
        health.price_action_health = self._calculate_price_action_health(
            entry_price, current_price, stop_price, direction, indicators
        )
        
        health.structure_health = self._calculate_structure_health(
            entry_price, current_price, stop_price, direction, indicators
        )
        
        health.momentum_health = self._calculate_momentum_health(
            direction, indicators
        )
        
        health.time_health = self._calculate_time_health(
            bars_in_trade, max_bars, health.pnl_health
        )
        
        health.volatility_health = self._calculate_volatility_health(indicators)
        
        # Calculate weighted health
        base_health = (
            health.price_action_health * self._weights["price_action"] +
            health.structure_health * self._weights["structure"] +
            health.momentum_health * self._weights["momentum"] +
            health.time_health * self._weights["time"] +
            health.pnl_health * self._weights["pnl"] +
            health.volatility_health * self._weights["volatility"]
        )
        
        # Apply event impact
        event_impact = sum(e.impact for e in events if e.detected_at > time.time() * 1000 - 3600000)
        health.event_balance = event_impact
        health.recent_events = events[-10:]  # Keep last 10 events
        
        # Apply decay
        health.total_decay = decay_applied
        
        # Final health
        health.current_health = max(0, min(100, base_health + event_impact - decay_applied))
        health.health_change = health.current_health - previous_health
        
        # Update history
        if position_id not in self._health_history:
            self._health_history[position_id] = []
        self._health_history[position_id].append(health.current_health)
        
        # Calculate trend
        health.health_trend, health.trend_strength = self._calculate_trend(
            self._health_history.get(position_id, [])
        )
        
        # Calculate stability
        health.stability = self._calculate_stability(
            position_id, health, events, indicators
        )
        
        # Determine status
        health.status = self._get_status(health.current_health)
        
        # Determine action
        action, urgency = self._action_map.get(health.status, ("HOLD", "LOW"))
        health.recommended_action = action
        health.action_urgency = urgency
        
        # Generate action reasons
        health.action_reasons = self._generate_action_reasons(health)
        
        # Check recovery blocking
        health.recovery_blocked, health.recovery_block_reason = self._check_recovery_block(health)
        
        return health
    
    def _calculate_pnl_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str
    ) -> float:
        """Calculate health based on current P&L position"""
        
        if direction == "LONG":
            risk = entry_price - stop_price
            reward = target_price - entry_price
            current_pnl = current_price - entry_price
        else:
            risk = stop_price - entry_price
            reward = entry_price - target_price
            current_pnl = entry_price - current_price
        
        if risk <= 0:
            return 50.0
        
        r_multiple = current_pnl / risk
        
        if r_multiple >= 2.5:
            return 100.0
        elif r_multiple >= 2.0:
            return 95.0
        elif r_multiple >= 1.5:
            return 88.0
        elif r_multiple >= 1.0:
            return 80.0
        elif r_multiple >= 0.5:
            return 70.0
        elif r_multiple >= 0:
            return 60.0
        elif r_multiple >= -0.3:
            return 45.0
        elif r_multiple >= -0.5:
            return 35.0
        elif r_multiple >= -0.7:
            return 25.0
        elif r_multiple >= -0.9:
            return 15.0
        else:
            return 5.0
    
    def _calculate_price_action_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        direction: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate health based on price action"""
        
        if direction == "LONG":
            total_range = entry_price - stop_price
            current_buffer = current_price - stop_price
        else:
            total_range = stop_price - entry_price
            current_buffer = stop_price - current_price
        
        if total_range <= 0:
            return 50.0
        
        buffer_ratio = current_buffer / total_range
        
        # Map buffer ratio to health
        if buffer_ratio >= 3.0:
            base_health = 100.0
        elif buffer_ratio >= 2.0:
            base_health = 90.0
        elif buffer_ratio >= 1.5:
            base_health = 80.0
        elif buffer_ratio >= 1.0:
            base_health = 70.0
        elif buffer_ratio >= 0.5:
            base_health = 50.0
        elif buffer_ratio >= 0.25:
            base_health = 30.0
        else:
            base_health = 10.0
        
        # Adjust for recent price action
        atr = indicators.get("atr", 0)
        if atr > 0 and current_price > 0:
            atr_pct = atr / current_price
            if atr_pct > 0.05:  # High volatility
                base_health -= 5
        
        return max(0, min(100, base_health))
    
    def _calculate_structure_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        direction: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate health based on market structure"""
        
        # Check support/resistance levels
        support = indicators.get("support", stop_price)
        resistance = indicators.get("resistance", entry_price * 1.05)
        
        if direction == "LONG":
            # Price above support is healthy
            if current_price > entry_price:
                structure_health = 85 + min(15, (current_price - entry_price) / entry_price * 500)
            elif current_price > support:
                distance_to_support = (current_price - support) / (entry_price - support)
                structure_health = 40 + distance_to_support * 45
            else:
                structure_health = 20
        else:
            # Price below resistance is healthy
            if current_price < entry_price:
                structure_health = 85 + min(15, (entry_price - current_price) / entry_price * 500)
            elif current_price < resistance:
                distance_to_resistance = (resistance - current_price) / (resistance - entry_price)
                structure_health = 40 + distance_to_resistance * 45
            else:
                structure_health = 20
        
        return max(0, min(100, structure_health))
    
    def _calculate_momentum_health(
        self,
        direction: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate health based on momentum"""
        
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macdHist", 0)
        adx = indicators.get("adx", 25)
        
        momentum_score = 50
        
        if direction == "LONG":
            # RSI analysis
            if 40 <= rsi <= 65:
                momentum_score += 15  # Healthy range
            elif 65 < rsi <= 75:
                momentum_score += 5   # Strong but overbought risk
            elif rsi > 75:
                momentum_score -= 5   # Overbought
            elif rsi < 40:
                momentum_score -= 15  # Weak momentum
            
            # MACD analysis
            if macd > 0:
                momentum_score += min(20, macd * 5)
            else:
                momentum_score += max(-20, macd * 5)
        else:
            # RSI for shorts
            if 35 <= rsi <= 60:
                momentum_score += 15
            elif 25 <= rsi < 35:
                momentum_score += 5
            elif rsi < 25:
                momentum_score -= 5
            elif rsi > 60:
                momentum_score -= 15
            
            # MACD for shorts
            if macd < 0:
                momentum_score += min(20, abs(macd) * 5)
            else:
                momentum_score -= min(20, macd * 5)
        
        # ADX trend strength
        if adx > 30:
            momentum_score += 10
        elif adx > 20:
            momentum_score += 5
        elif adx < 15:
            momentum_score -= 10
        
        return max(0, min(100, momentum_score))
    
    def _calculate_time_health(
        self,
        bars_in_trade: int,
        max_bars: int,
        pnl_health: float
    ) -> float:
        """Calculate health based on time in trade"""
        
        if max_bars <= 0:
            return 70.0
        
        time_ratio = bars_in_trade / max_bars
        
        # Base time health
        if time_ratio < 0.25:
            time_health = 95
        elif time_ratio < 0.5:
            time_health = 80
        elif time_ratio < 0.75:
            time_health = 60
        elif time_ratio < 1.0:
            time_health = 40
        else:
            time_health = 20
        
        # Adjust for profitability
        if pnl_health >= 80:
            time_health = max(time_health, 70)  # Profitable trades get time bonus
        elif pnl_health <= 40:
            time_health -= 10  # Losing trades should exit faster
        
        return max(0, min(100, time_health))
    
    def _calculate_volatility_health(self, indicators: Dict[str, float]) -> float:
        """Calculate health based on volatility conditions"""
        
        atr = indicators.get("atr", 0)
        atr_avg = indicators.get("atr_avg", atr)
        close = indicators.get("close", 40000)
        
        if close <= 0 or atr_avg <= 0:
            return 60.0
        
        # Normalized ATR
        atr_pct = (atr / close) * 100
        atr_ratio = atr / atr_avg if atr_avg > 0 else 1.0
        
        vol_health = 70
        
        # ATR ratio analysis
        if 0.8 <= atr_ratio <= 1.2:
            vol_health += 15  # Normal volatility
        elif 1.2 < atr_ratio <= 1.5:
            vol_health += 5   # Slightly elevated
        elif atr_ratio > 1.5:
            vol_health -= 15  # High volatility risk
        elif atr_ratio < 0.8:
            vol_health += 10  # Low volatility (safe)
        
        # Absolute volatility check
        if atr_pct > 5:
            vol_health -= 10  # Very high volatility
        elif atr_pct < 1:
            vol_health += 5   # Low volatility
        
        return max(0, min(100, vol_health))
    
    def _calculate_trend(self, history: List[float]) -> tuple:
        """Calculate health trend direction and strength"""
        
        if len(history) < 3:
            return "STABLE", 0.0
        
        recent = history[-5:]
        
        if len(recent) < 2:
            return "STABLE", 0.0
        
        # Calculate average change
        changes = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        # Determine trend
        if avg_change > 2:
            trend = "IMPROVING"
            strength = min(1.0, avg_change / 10)
        elif avg_change < -2:
            trend = "DETERIORATING"
            strength = min(1.0, abs(avg_change) / 10)
        else:
            trend = "STABLE"
            strength = 0.0
        
        return trend, strength
    
    def _calculate_stability(
        self,
        position_id: str,
        health: AdvancedTradeHealthScore,
        events: List[HealthEvent],
        indicators: Dict[str, float]
    ) -> TradeStabilityScore:
        """Calculate trade stability score"""
        
        stability = TradeStabilityScore(
            position_id=position_id,
            computed_at=int(time.time() * 1000)
        )
        
        history = self._health_history.get(position_id, [])
        
        # Price stability - based on health variance
        if len(history) >= 3:
            health_variance = sum((h - sum(history)/len(history))**2 for h in history) / len(history)
            stability.price_stability = max(0, 100 - health_variance)
        else:
            stability.price_stability = 70
        
        # Momentum stability
        stability.momentum_stability = health.momentum_health
        
        # Volume stability (simulated)
        stability.volume_stability = 60 + (indicators.get("volume_ratio", 1) - 0.5) * 40
        
        # Structure stability
        stability.structure_stability = health.structure_health
        
        # Event analysis
        positive = sum(1 for e in events if e.impact > 0)
        negative = sum(1 for e in events if e.impact < 0)
        stability.positive_events = positive
        stability.negative_events = negative
        stability.net_event_impact = sum(e.impact for e in events)
        
        # Health trajectory
        if len(history) >= 2:
            stability.health_changes = [history[i] - history[i-1] for i in range(1, len(history))]
            stability.avg_health_change = sum(stability.health_changes) / len(stability.health_changes)
            variance = sum((c - stability.avg_health_change)**2 for c in stability.health_changes)
            stability.health_volatility = (variance / len(stability.health_changes)) ** 0.5 if stability.health_changes else 0
        
        # Calculate overall stability
        stability.stability_score = (
            stability.price_stability * 0.30 +
            stability.momentum_stability * 0.25 +
            stability.volume_stability * 0.15 +
            stability.structure_stability * 0.30
        )
        
        # Predictions (simple extrapolation)
        if stability.avg_health_change != 0:
            stability.predicted_health_1h = health.current_health + stability.avg_health_change * 4
            stability.predicted_health_4h = health.current_health + stability.avg_health_change * 16
            stability.confidence = 0.7 if abs(stability.avg_health_change) < 5 else 0.4
        else:
            stability.predicted_health_1h = health.current_health
            stability.predicted_health_4h = health.current_health
            stability.confidence = 0.5
        
        return stability
    
    def _get_status(self, health: float) -> HealthStatus:
        """Convert health score to status"""
        
        if health >= self._thresholds[HealthStatus.EXCELLENT]:
            return HealthStatus.EXCELLENT
        elif health >= self._thresholds[HealthStatus.GOOD]:
            return HealthStatus.GOOD
        elif health >= self._thresholds[HealthStatus.STABLE]:
            return HealthStatus.STABLE
        elif health >= self._thresholds[HealthStatus.WEAK]:
            return HealthStatus.WEAK
        elif health >= self._thresholds[HealthStatus.CRITICAL]:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.TERMINAL
    
    def _generate_action_reasons(self, health: AdvancedTradeHealthScore) -> List[str]:
        """Generate reasons for recommended action"""
        
        reasons = []
        
        if health.pnl_health < 30:
            reasons.append(f"P&L health critical ({health.pnl_health:.0f})")
        elif health.pnl_health < 50:
            reasons.append(f"P&L health declining ({health.pnl_health:.0f})")
        
        if health.structure_health < 40:
            reasons.append("Market structure weakening")
        
        if health.momentum_health < 35:
            reasons.append("Momentum fading against position")
        
        if health.time_health < 30:
            reasons.append("Trade duration excessive")
        
        if health.health_trend == "DETERIORATING" and health.trend_strength > 0.5:
            reasons.append(f"Health deteriorating rapidly ({health.trend_strength:.0%})")
        
        if health.total_decay > 10:
            reasons.append(f"Significant decay applied ({health.total_decay:.1f})")
        
        if health.stability and health.stability.stability_score < 40:
            reasons.append("Trade stability low")
        
        if health.event_balance < -10:
            reasons.append(f"Negative event impact ({health.event_balance:.1f})")
        
        if not reasons:
            reasons.append("Trade within acceptable parameters")
        
        return reasons
    
    def _check_recovery_block(self, health: AdvancedTradeHealthScore) -> tuple:
        """Check if recovery trades should be blocked"""
        
        # Block recovery if health is critical
        if health.status in [HealthStatus.CRITICAL, HealthStatus.TERMINAL]:
            return True, f"Health status {health.status.value} - recovery blocked"
        
        # Block if rapid deterioration
        if health.health_trend == "DETERIORATING" and health.trend_strength > 0.7:
            return True, "Rapid health deterioration - recovery blocked"
        
        # Block if stability very low
        if health.stability and health.stability.stability_score < 25:
            return True, f"Stability score {health.stability.stability_score:.0f} too low"
        
        # Block if too many negative events
        if health.event_balance < -20:
            return True, f"Excessive negative events (balance: {health.event_balance:.1f})"
        
        return False, ""
    
    def clear_history(self, position_id: str):
        """Clear health history for a position"""
        if position_id in self._health_history:
            del self._health_history[position_id]
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health status"""
        return {
            "engine": "AdvancedTradeHealthEngine",
            "version": "2.0.0",
            "phase": "3.2",
            "status": "active",
            "components": list(self._weights.keys()),
            "statuses": [s.value for s in HealthStatus],
            "thresholds": {k.value: v for k, v in self._thresholds.items()},
            "trackedPositions": len(self._health_history),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
advanced_trade_health_engine = AdvancedTradeHealthEngine()
