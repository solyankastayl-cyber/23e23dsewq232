"""
Trade Health Engine
===================

Monitors and calculates Trade Health Score (PHASE 3.1)
"""

import time
import random
from typing import Dict, List, Optional, Any

from .position_quality_types import (
    TradeHealthScore,
    HealthStatus
)


class TradeHealthEngine:
    """
    Monitors trade health in real-time.
    
    Components:
    - Price Action Health
    - Structure Health
    - Momentum Health
    - Time Health
    - P&L Health
    
    Output: Health 0-100, Status EXCELLENT to TERMINAL
    """
    
    def __init__(self):
        # Health thresholds
        self._thresholds = {
            HealthStatus.EXCELLENT: 80,
            HealthStatus.GOOD: 60,
            HealthStatus.WARNING: 40,
            HealthStatus.CRITICAL: 20,
            HealthStatus.TERMINAL: 0
        }
        
        # Action mapping
        self._action_map = {
            HealthStatus.EXCELLENT: ("HOLD", "LOW"),
            HealthStatus.GOOD: ("HOLD", "LOW"),
            HealthStatus.WARNING: ("REDUCE", "MEDIUM"),
            HealthStatus.CRITICAL: ("EXIT", "HIGH"),
            HealthStatus.TERMINAL: ("EXIT", "IMMEDIATE")
        }
        
        print("[TradeHealthEngine] Initialized (PHASE 3.1)")
    
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
        indicators: Dict[str, float] = None
    ) -> TradeHealthScore:
        """
        Calculate current trade health.
        """
        
        indicators = indicators or {}
        
        health = TradeHealthScore(
            position_id=position_id,
            previous_health=previous_health,
            computed_at=int(time.time() * 1000)
        )
        
        # Calculate P&L health
        health.pnl_health = self._calculate_pnl_health(
            entry_price=entry_price,
            current_price=current_price,
            stop_price=stop_price,
            target_price=target_price,
            direction=direction
        )
        
        # Calculate price action health
        health.price_action_health = self._calculate_price_action_health(
            entry_price=entry_price,
            current_price=current_price,
            stop_price=stop_price,
            direction=direction,
            indicators=indicators
        )
        
        # Calculate structure health
        health.structure_health = self._calculate_structure_health(
            entry_price=entry_price,
            current_price=current_price,
            stop_price=stop_price,
            direction=direction
        )
        
        # Calculate momentum health
        health.momentum_health = self._calculate_momentum_health(
            direction=direction,
            indicators=indicators
        )
        
        # Calculate time health
        health.time_health = self._calculate_time_health(
            bars_in_trade=bars_in_trade,
            max_bars=max_bars,
            pnl_health=health.pnl_health
        )
        
        # Calculate overall health
        health.current_health = (
            health.pnl_health * 0.30 +
            health.price_action_health * 0.25 +
            health.structure_health * 0.20 +
            health.momentum_health * 0.15 +
            health.time_health * 0.10
        )
        
        # Calculate change
        health.health_change = health.current_health - previous_health
        
        # Determine trend
        if health.health_change > 5:
            health.health_trend = "IMPROVING"
        elif health.health_change < -5:
            health.health_trend = "DETERIORATING"
        else:
            health.health_trend = "STABLE"
        
        # Determine status
        health.status = self._get_status(health.current_health)
        
        # Generate warnings and alerts
        health.warnings, health.critical_alerts = self._generate_alerts(health)
        
        # Determine recommended action
        action, urgency = self._action_map.get(
            health.status,
            ("HOLD", "LOW")
        )
        health.recommended_action = action
        health.action_urgency = urgency
        
        return health
    
    def _calculate_pnl_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str
    ) -> float:
        """Calculate health based on current P&L"""
        
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
        
        # Calculate R-multiple
        r_multiple = current_pnl / risk
        
        # Map R-multiple to health
        if r_multiple >= 2.0:
            return 100.0
        elif r_multiple >= 1.0:
            return 90.0
        elif r_multiple >= 0.5:
            return 80.0
        elif r_multiple >= 0:
            return 70.0
        elif r_multiple >= -0.5:
            return 50.0
        elif r_multiple >= -0.8:
            return 30.0
        else:
            return 10.0
    
    def _calculate_price_action_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        direction: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate health based on price action"""
        
        # Distance from stop as percentage
        if direction == "LONG":
            total_range = entry_price - stop_price
            current_buffer = current_price - stop_price
        else:
            total_range = stop_price - entry_price
            current_buffer = stop_price - current_price
        
        if total_range <= 0:
            return 50.0
        
        buffer_pct = (current_buffer / total_range) * 100
        
        # Map buffer to health
        if buffer_pct >= 200:  # 2x buffer
            return 95.0
        elif buffer_pct >= 150:
            return 85.0
        elif buffer_pct >= 100:  # At entry
            return 75.0
        elif buffer_pct >= 50:
            return 55.0
        elif buffer_pct >= 25:
            return 35.0
        else:
            return 15.0
    
    def _calculate_structure_health(
        self,
        entry_price: float,
        current_price: float,
        stop_price: float,
        direction: str
    ) -> float:
        """Calculate health based on market structure"""
        
        # Simulated structure analysis
        # In real implementation, would check support/resistance levels
        
        # Check if price is moving favorably
        if direction == "LONG":
            favorable = current_price > entry_price
        else:
            favorable = current_price < entry_price
        
        if favorable:
            return random.uniform(70, 95)
        else:
            # Check how close to stop
            if direction == "LONG":
                distance_to_stop = current_price - stop_price
                entry_to_stop = entry_price - stop_price
            else:
                distance_to_stop = stop_price - current_price
                entry_to_stop = stop_price - entry_price
            
            if entry_to_stop > 0:
                pct_to_stop = distance_to_stop / entry_to_stop
                return max(20, min(70, pct_to_stop * 70))
            return 40
    
    def _calculate_momentum_health(
        self,
        direction: str,
        indicators: Dict[str, float]
    ) -> float:
        """Calculate health based on momentum indicators"""
        
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macdHist", 0)
        
        momentum_score = 50
        
        if direction == "LONG":
            # Bullish momentum
            if rsi > 50 and rsi < 70:
                momentum_score += 20
            elif rsi > 70:
                momentum_score += 10  # Overbought risk
            elif rsi < 40:
                momentum_score -= 20  # Losing momentum
            
            if macd > 0:
                momentum_score += 15
            elif macd < 0:
                momentum_score -= 15
        else:
            # Bearish momentum
            if rsi < 50 and rsi > 30:
                momentum_score += 20
            elif rsi < 30:
                momentum_score += 10  # Oversold risk
            elif rsi > 60:
                momentum_score -= 20
            
            if macd < 0:
                momentum_score += 15
            elif macd > 0:
                momentum_score -= 15
        
        return max(10, min(100, momentum_score))
    
    def _calculate_time_health(
        self,
        bars_in_trade: int,
        max_bars: int,
        pnl_health: float
    ) -> float:
        """Calculate health based on time in trade"""
        
        time_pct = bars_in_trade / max_bars if max_bars > 0 else 0
        
        # If profitable, time matters less
        if pnl_health >= 70:
            time_penalty = time_pct * 20  # Max 20% penalty
        else:
            time_penalty = time_pct * 50  # Max 50% penalty if not profitable
        
        return max(20, 100 - time_penalty)
    
    def _get_status(self, health: float) -> HealthStatus:
        """Convert health score to status"""
        
        if health >= self._thresholds[HealthStatus.EXCELLENT]:
            return HealthStatus.EXCELLENT
        elif health >= self._thresholds[HealthStatus.GOOD]:
            return HealthStatus.GOOD
        elif health >= self._thresholds[HealthStatus.WARNING]:
            return HealthStatus.WARNING
        elif health >= self._thresholds[HealthStatus.CRITICAL]:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.TERMINAL
    
    def _generate_alerts(
        self,
        health: TradeHealthScore
    ) -> tuple[List[str], List[str]]:
        """Generate warnings and critical alerts"""
        
        warnings = []
        critical = []
        
        # P&L warnings
        if health.pnl_health < 40:
            warnings.append(f"P&L health declining ({health.pnl_health:.0f})")
        if health.pnl_health < 20:
            critical.append("P&L near stop loss!")
        
        # Structure warnings
        if health.structure_health < 50:
            warnings.append("Market structure weakening")
        if health.structure_health < 30:
            critical.append("Structure breakdown imminent")
        
        # Momentum warnings
        if health.momentum_health < 40:
            warnings.append("Momentum fading")
        
        # Time warnings
        if health.time_health < 40:
            warnings.append("Trade duration excessive")
        
        # Trend warnings
        if health.health_trend == "DETERIORATING":
            warnings.append("Health trend deteriorating")
        
        # Overall health
        if health.current_health < 30:
            critical.append(f"Critical health level: {health.current_health:.0f}")
        
        return warnings, critical
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "TradeHealthEngine",
            "status": "active",
            "version": "1.0.0",
            "components": ["pnl", "priceAction", "structure", "momentum", "time"],
            "statuses": [s.value for s in HealthStatus],
            "thresholds": {k.value: v for k, v in self._thresholds.items()},
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
trade_health_engine = TradeHealthEngine()
