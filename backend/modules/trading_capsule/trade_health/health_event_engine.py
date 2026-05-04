"""
Health Event Engine
===================

PHASE 3.2 - Detects and tracks health events for positions.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .health_types import (
    EventType,
    HealthEvent
)


class HealthEventEngine:
    """
    Detects and tracks health events:
    - Positive: trend_confirmed, breakout, momentum_surge
    - Negative: structure_break, momentum_loss, volatility_spike
    - Neutral: consolidation, retest
    """
    
    def __init__(self):
        # Event impact scores
        self._event_impacts = {
            # Positive events
            EventType.TREND_CONFIRMED: 8.0,
            EventType.BREAKOUT_CONFIRMED: 12.0,
            EventType.MOMENTUM_SURGE: 10.0,
            EventType.STRUCTURE_SUPPORT: 6.0,
            EventType.VOLUME_CONFIRMATION: 5.0,
            EventType.TARGET_APPROACH: 15.0,
            
            # Negative events
            EventType.STRUCTURE_BREAK: -15.0,
            EventType.MOMENTUM_LOSS: -8.0,
            EventType.VOLATILITY_SPIKE: -10.0,
            EventType.REGIME_SWITCH: -12.0,
            EventType.VOLUME_DIVERGENCE: -6.0,
            EventType.TIME_DECAY: -3.0,
            EventType.STOP_APPROACH: -18.0,
            
            # Neutral events
            EventType.CONSOLIDATION: 0.0,
            EventType.RETEST: -2.0
        }
        
        # Event TTL (time-to-live) in ms
        self._event_ttl = {
            EventType.TREND_CONFIRMED: 4 * 3600 * 1000,  # 4 hours
            EventType.BREAKOUT_CONFIRMED: 2 * 3600 * 1000,
            EventType.MOMENTUM_SURGE: 1 * 3600 * 1000,
            EventType.STRUCTURE_BREAK: 6 * 3600 * 1000,
            EventType.VOLATILITY_SPIKE: 2 * 3600 * 1000,
            EventType.REGIME_SWITCH: 8 * 3600 * 1000,
        }
        
        # Tracking
        self._position_events: Dict[str, List[HealthEvent]] = {}
        
        print("[HealthEventEngine] Initialized (PHASE 3.2)")
    
    def detect_events(
        self,
        position_id: str,
        direction: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        current_health: float,
        previous_indicators: Optional[Dict[str, float]] = None,
        current_indicators: Optional[Dict[str, float]] = None
    ) -> List[HealthEvent]:
        """
        Detect events based on price action and indicators.
        """
        
        previous_indicators = previous_indicators or {}
        current_indicators = current_indicators or {}
        
        events = []
        now = int(time.time() * 1000)
        
        # Check for trend confirmation
        trend_event = self._check_trend_confirmation(
            position_id, direction, entry_price, current_price,
            current_health, current_indicators, now
        )
        if trend_event:
            events.append(trend_event)
        
        # Check for structure break
        structure_event = self._check_structure_break(
            position_id, direction, entry_price, current_price, stop_price,
            current_health, current_indicators, now
        )
        if structure_event:
            events.append(structure_event)
        
        # Check for momentum changes
        momentum_event = self._check_momentum_change(
            position_id, direction, current_health,
            previous_indicators, current_indicators, now
        )
        if momentum_event:
            events.append(momentum_event)
        
        # Check for volatility spike
        vol_event = self._check_volatility_spike(
            position_id, current_health, current_indicators, now
        )
        if vol_event:
            events.append(vol_event)
        
        # Check for target approach
        target_event = self._check_target_approach(
            position_id, direction, current_price, target_price,
            current_health, now
        )
        if target_event:
            events.append(target_event)
        
        # Check for stop approach
        stop_event = self._check_stop_approach(
            position_id, direction, current_price, stop_price, entry_price,
            current_health, now
        )
        if stop_event:
            events.append(stop_event)
        
        # Store events
        if position_id not in self._position_events:
            self._position_events[position_id] = []
        self._position_events[position_id].extend(events)
        
        # Clean old events
        self._clean_expired_events(position_id, now)
        
        return events
    
    def _check_trend_confirmation(
        self,
        position_id: str,
        direction: str,
        entry_price: float,
        current_price: float,
        current_health: float,
        indicators: Dict[str, float],
        now: int
    ) -> Optional[HealthEvent]:
        """Check for trend confirmation event"""
        
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macdHist", 0)
        adx = indicators.get("adx", 20)
        
        confirmed = False
        confidence = 0.0
        triggers = []
        
        if direction == "LONG":
            if current_price > entry_price * 1.01:  # 1% above entry
                confirmed = True
                confidence = 0.6
                triggers.append("price_above_entry")
            
            if macd > 0 and rsi > 50 and adx > 25:
                confidence += 0.3
                triggers.extend(["macd_positive", "rsi_above_50", "adx_strong"])
        else:
            if current_price < entry_price * 0.99:
                confirmed = True
                confidence = 0.6
                triggers.append("price_below_entry")
            
            if macd < 0 and rsi < 50 and adx > 25:
                confidence += 0.3
                triggers.extend(["macd_negative", "rsi_below_50", "adx_strong"])
        
        if confirmed and confidence >= 0.6:
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=EventType.TREND_CONFIRMED,
                description=f"Trend confirmed in {direction} direction",
                impact=self._event_impacts[EventType.TREND_CONFIRMED],
                confidence=min(1.0, confidence),
                price_at_event=current_price,
                health_before=current_health,
                health_after=current_health + self._event_impacts[EventType.TREND_CONFIRMED],
                trigger_indicators=triggers,
                trigger_values={"rsi": rsi, "macd": macd, "adx": adx},
                detected_at=now,
                expires_at=now + self._event_ttl.get(EventType.TREND_CONFIRMED, 3600000)
            )
        
        return None
    
    def _check_structure_break(
        self,
        position_id: str,
        direction: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        current_health: float,
        indicators: Dict[str, float],
        now: int
    ) -> Optional[HealthEvent]:
        """Check for structure break event"""
        
        support = indicators.get("support", stop_price)
        resistance = indicators.get("resistance", entry_price * 1.1)
        
        broken = False
        triggers = []
        
        if direction == "LONG":
            # Check if price broke below key support
            if current_price < support * 1.005:
                broken = True
                triggers.append("support_broken")
        else:
            # Check if price broke above key resistance
            if current_price > resistance * 0.995:
                broken = True
                triggers.append("resistance_broken")
        
        # Also check for significant adverse move
        if direction == "LONG":
            adverse_move = (entry_price - current_price) / entry_price
            if adverse_move > 0.02:  # 2% adverse
                broken = True
                triggers.append("adverse_move_2pct")
        else:
            adverse_move = (current_price - entry_price) / entry_price
            if adverse_move > 0.02:
                broken = True
                triggers.append("adverse_move_2pct")
        
        if broken:
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=EventType.STRUCTURE_BREAK,
                description="Market structure break detected",
                impact=self._event_impacts[EventType.STRUCTURE_BREAK],
                confidence=0.75,
                price_at_event=current_price,
                health_before=current_health,
                health_after=current_health + self._event_impacts[EventType.STRUCTURE_BREAK],
                trigger_indicators=triggers,
                trigger_values={"support": support, "resistance": resistance},
                detected_at=now,
                expires_at=now + self._event_ttl.get(EventType.STRUCTURE_BREAK, 6 * 3600000)
            )
        
        return None
    
    def _check_momentum_change(
        self,
        position_id: str,
        direction: str,
        current_health: float,
        prev_indicators: Dict[str, float],
        curr_indicators: Dict[str, float],
        now: int
    ) -> Optional[HealthEvent]:
        """Check for momentum change events"""
        
        prev_rsi = prev_indicators.get("rsi", 50)
        curr_rsi = curr_indicators.get("rsi", 50)
        prev_macd = prev_indicators.get("macdHist", 0)
        curr_macd = curr_indicators.get("macdHist", 0)
        
        triggers = []
        event_type = None
        
        if direction == "LONG":
            # Check for momentum surge
            if curr_macd > prev_macd + 0.5 and curr_rsi > prev_rsi + 5:
                event_type = EventType.MOMENTUM_SURGE
                triggers = ["macd_surge", "rsi_surge"]
            # Check for momentum loss
            elif curr_macd < prev_macd - 0.5 and curr_rsi < prev_rsi - 5:
                event_type = EventType.MOMENTUM_LOSS
                triggers = ["macd_decline", "rsi_decline"]
        else:
            # For shorts
            if curr_macd < prev_macd - 0.5 and curr_rsi < prev_rsi - 5:
                event_type = EventType.MOMENTUM_SURGE
                triggers = ["macd_decline", "rsi_decline"]
            elif curr_macd > prev_macd + 0.5 and curr_rsi > prev_rsi + 5:
                event_type = EventType.MOMENTUM_LOSS
                triggers = ["macd_surge", "rsi_surge"]
        
        if event_type:
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=event_type,
                description=f"{'Momentum surge' if event_type == EventType.MOMENTUM_SURGE else 'Momentum loss'} detected",
                impact=self._event_impacts[event_type],
                confidence=0.7,
                price_at_event=curr_indicators.get("close", 0),
                health_before=current_health,
                health_after=current_health + self._event_impacts[event_type],
                trigger_indicators=triggers,
                trigger_values={"prev_rsi": prev_rsi, "curr_rsi": curr_rsi, "prev_macd": prev_macd, "curr_macd": curr_macd},
                detected_at=now,
                expires_at=now + 3600000
            )
        
        return None
    
    def _check_volatility_spike(
        self,
        position_id: str,
        current_health: float,
        indicators: Dict[str, float],
        now: int
    ) -> Optional[HealthEvent]:
        """Check for volatility spike"""
        
        atr = indicators.get("atr", 0)
        atr_avg = indicators.get("atr_avg", atr)
        
        if atr_avg <= 0:
            return None
        
        atr_ratio = atr / atr_avg
        
        if atr_ratio > 1.5:  # 50% above average
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=EventType.VOLATILITY_SPIKE,
                description=f"Volatility spike detected (ATR {atr_ratio:.1f}x normal)",
                impact=self._event_impacts[EventType.VOLATILITY_SPIKE],
                confidence=0.8,
                price_at_event=indicators.get("close", 0),
                health_before=current_health,
                health_after=current_health + self._event_impacts[EventType.VOLATILITY_SPIKE],
                trigger_indicators=["atr_spike"],
                trigger_values={"atr": atr, "atr_avg": atr_avg, "ratio": atr_ratio},
                detected_at=now,
                expires_at=now + self._event_ttl.get(EventType.VOLATILITY_SPIKE, 2 * 3600000)
            )
        
        return None
    
    def _check_target_approach(
        self,
        position_id: str,
        direction: str,
        current_price: float,
        target_price: float,
        current_health: float,
        now: int
    ) -> Optional[HealthEvent]:
        """Check if price is approaching target"""
        
        if direction == "LONG":
            progress = (current_price - target_price) / target_price
            approaching = progress > -0.02  # Within 2% of target
        else:
            progress = (target_price - current_price) / target_price
            approaching = progress > -0.02
        
        if approaching:
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=EventType.TARGET_APPROACH,
                description=f"Price approaching target ({progress*100:.1f}% away)",
                impact=self._event_impacts[EventType.TARGET_APPROACH],
                confidence=0.9,
                price_at_event=current_price,
                health_before=current_health,
                health_after=current_health + self._event_impacts[EventType.TARGET_APPROACH],
                trigger_indicators=["target_proximity"],
                trigger_values={"progress": progress, "target": target_price},
                detected_at=now,
                expires_at=now + 1800000  # 30 min
            )
        
        return None
    
    def _check_stop_approach(
        self,
        position_id: str,
        direction: str,
        current_price: float,
        stop_price: float,
        entry_price: float,
        current_health: float,
        now: int
    ) -> Optional[HealthEvent]:
        """Check if price is approaching stop"""
        
        if direction == "LONG":
            total_risk = entry_price - stop_price
            current_buffer = current_price - stop_price
        else:
            total_risk = stop_price - entry_price
            current_buffer = stop_price - current_price
        
        if total_risk <= 0:
            return None
        
        buffer_pct = current_buffer / total_risk
        
        if buffer_pct < 0.25:  # Within 25% of stop
            return HealthEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                position_id=position_id,
                event_type=EventType.STOP_APPROACH,
                description=f"Price approaching stop ({buffer_pct*100:.0f}% buffer remaining)",
                impact=self._event_impacts[EventType.STOP_APPROACH],
                confidence=0.95,
                price_at_event=current_price,
                health_before=current_health,
                health_after=current_health + self._event_impacts[EventType.STOP_APPROACH],
                trigger_indicators=["stop_proximity"],
                trigger_values={"buffer_pct": buffer_pct, "stop": stop_price},
                detected_at=now,
                expires_at=now + 3600000
            )
        
        return None
    
    def _clean_expired_events(self, position_id: str, now: int):
        """Remove expired events"""
        if position_id in self._position_events:
            self._position_events[position_id] = [
                e for e in self._position_events[position_id]
                if e.expires_at > now
            ]
    
    def get_events(self, position_id: str) -> List[HealthEvent]:
        """Get all events for a position"""
        return self._position_events.get(position_id, [])
    
    def get_recent_events(self, position_id: str, hours: int = 4) -> List[HealthEvent]:
        """Get recent events within specified hours"""
        cutoff = int(time.time() * 1000) - hours * 3600 * 1000
        events = self._position_events.get(position_id, [])
        return [e for e in events if e.detected_at > cutoff]
    
    def clear_events(self, position_id: str):
        """Clear all events for a position"""
        if position_id in self._position_events:
            del self._position_events[position_id]
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        total_events = sum(len(e) for e in self._position_events.values())
        return {
            "engine": "HealthEventEngine",
            "version": "1.0.0",
            "phase": "3.2",
            "status": "active",
            "eventTypes": [e.value for e in EventType],
            "trackedPositions": len(self._position_events),
            "totalEvents": total_events,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
health_event_engine = HealthEventEngine()
