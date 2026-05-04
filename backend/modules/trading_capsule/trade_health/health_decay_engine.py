"""
Health Decay Engine
===================

PHASE 3.2 - Models health decay over time based on various factors.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .health_types import (
    DecayType,
    HealthDecayRecord
)


class HealthDecayEngine:
    """
    Models health decay:
    - Time decay: Natural decay from holding too long
    - Volatility decay: Decay from volatility changes
    - Momentum decay: Decay from losing momentum
    - Structure decay: Decay from structure deterioration
    - Event decay: Decay from negative events
    """
    
    def __init__(self):
        # Base decay rates per bar
        self._base_rates = {
            DecayType.TIME_DECAY: 0.15,       # 0.15 per bar base
            DecayType.VOLATILITY_DECAY: 0.25,
            DecayType.MOMENTUM_DECAY: 0.3,
            DecayType.STRUCTURE_DECAY: 0.4,
            DecayType.EVENT_DECAY: 0.5
        }
        
        # Decay modifiers based on conditions
        self._time_decay_schedule = [
            (20, 0.05),   # 0-20 bars: minimal decay
            (40, 0.1),    # 20-40 bars: low decay
            (60, 0.2),    # 40-60 bars: moderate decay
            (80, 0.35),   # 60-80 bars: increased decay
            (100, 0.5),   # 80-100 bars: high decay
            (999, 0.75)   # 100+ bars: maximum decay
        ]
        
        # Profitability adjustments
        self._profit_adjustments = {
            "high_profit": 0.3,     # Above 2R: reduce decay to 30%
            "in_profit": 0.6,       # Above breakeven: reduce to 60%
            "small_loss": 1.0,      # Small loss: normal decay
            "moderate_loss": 1.3,   # Moderate loss: increase by 30%
            "large_loss": 1.6       # Large loss: increase by 60%
        }
        
        # Tracking
        self._decay_records: Dict[str, List[HealthDecayRecord]] = {}
        
        print("[HealthDecayEngine] Initialized (PHASE 3.2)")
    
    def calculate_decay(
        self,
        position_id: str,
        bars_in_trade: int,
        current_health: float,
        r_multiple: float,
        volatility_ratio: float = 1.0,
        momentum_declining: bool = False,
        structure_broken: bool = False,
        recent_negative_events: int = 0
    ) -> tuple[float, List[HealthDecayRecord]]:
        """
        Calculate total decay for current bar.
        
        Returns: (total_decay, list of decay records)
        """
        
        records = []
        total_decay = 0.0
        now = int(time.time() * 1000)
        
        # Get profitability adjustment
        profit_adjustment = self._get_profit_adjustment(r_multiple)
        
        # Time decay
        time_decay_rate = self._get_time_decay_rate(bars_in_trade)
        time_decay = time_decay_rate * profit_adjustment
        
        if time_decay > 0.01:
            record = HealthDecayRecord(
                position_id=position_id,
                decay_type=DecayType.TIME_DECAY,
                decay_amount=time_decay,
                decay_rate=time_decay_rate,
                health_before=current_health,
                health_after=current_health - time_decay,
                source_description=f"Time decay at bar {bars_in_trade}",
                applied_at=now
            )
            records.append(record)
            total_decay += time_decay
        
        # Volatility decay
        if volatility_ratio > 1.3:
            vol_decay = self._base_rates[DecayType.VOLATILITY_DECAY] * (volatility_ratio - 1.0)
            vol_decay *= profit_adjustment
            
            record = HealthDecayRecord(
                position_id=position_id,
                decay_type=DecayType.VOLATILITY_DECAY,
                decay_amount=vol_decay,
                decay_rate=self._base_rates[DecayType.VOLATILITY_DECAY],
                health_before=current_health - total_decay,
                health_after=current_health - total_decay - vol_decay,
                source_description=f"Volatility {volatility_ratio:.2f}x normal",
                applied_at=now
            )
            records.append(record)
            total_decay += vol_decay
        
        # Momentum decay
        if momentum_declining:
            mom_decay = self._base_rates[DecayType.MOMENTUM_DECAY] * profit_adjustment
            
            record = HealthDecayRecord(
                position_id=position_id,
                decay_type=DecayType.MOMENTUM_DECAY,
                decay_amount=mom_decay,
                decay_rate=self._base_rates[DecayType.MOMENTUM_DECAY],
                health_before=current_health - total_decay,
                health_after=current_health - total_decay - mom_decay,
                source_description="Momentum declining against position",
                applied_at=now
            )
            records.append(record)
            total_decay += mom_decay
        
        # Structure decay
        if structure_broken:
            struct_decay = self._base_rates[DecayType.STRUCTURE_DECAY] * profit_adjustment
            
            record = HealthDecayRecord(
                position_id=position_id,
                decay_type=DecayType.STRUCTURE_DECAY,
                decay_amount=struct_decay,
                decay_rate=self._base_rates[DecayType.STRUCTURE_DECAY],
                health_before=current_health - total_decay,
                health_after=current_health - total_decay - struct_decay,
                source_description="Market structure broken",
                applied_at=now
            )
            records.append(record)
            total_decay += struct_decay
        
        # Event decay
        if recent_negative_events > 0:
            event_decay = self._base_rates[DecayType.EVENT_DECAY] * recent_negative_events * profit_adjustment
            
            record = HealthDecayRecord(
                position_id=position_id,
                decay_type=DecayType.EVENT_DECAY,
                decay_amount=event_decay,
                decay_rate=self._base_rates[DecayType.EVENT_DECAY],
                health_before=current_health - total_decay,
                health_after=current_health - total_decay - event_decay,
                source_description=f"{recent_negative_events} recent negative events",
                applied_at=now
            )
            records.append(record)
            total_decay += event_decay
        
        # Store records
        if position_id not in self._decay_records:
            self._decay_records[position_id] = []
        self._decay_records[position_id].extend(records)
        
        # Calculate cumulative
        for record in records:
            record.cumulative_decay = self.get_cumulative_decay(position_id)
        
        return total_decay, records
    
    def _get_time_decay_rate(self, bars_in_trade: int) -> float:
        """Get time decay rate based on bars in trade"""
        for threshold, rate in self._time_decay_schedule:
            if bars_in_trade <= threshold:
                return rate
        return self._time_decay_schedule[-1][1]
    
    def _get_profit_adjustment(self, r_multiple: float) -> float:
        """Get decay adjustment based on R-multiple"""
        if r_multiple >= 2.0:
            return self._profit_adjustments["high_profit"]
        elif r_multiple >= 0:
            return self._profit_adjustments["in_profit"]
        elif r_multiple >= -0.5:
            return self._profit_adjustments["small_loss"]
        elif r_multiple >= -0.8:
            return self._profit_adjustments["moderate_loss"]
        else:
            return self._profit_adjustments["large_loss"]
    
    def get_cumulative_decay(self, position_id: str) -> float:
        """Get total cumulative decay for a position"""
        records = self._decay_records.get(position_id, [])
        return sum(r.decay_amount for r in records)
    
    def get_decay_breakdown(self, position_id: str) -> Dict[str, float]:
        """Get decay breakdown by type"""
        records = self._decay_records.get(position_id, [])
        
        breakdown = {dt.value: 0.0 for dt in DecayType}
        for record in records:
            breakdown[record.decay_type.value] += record.decay_amount
        
        return breakdown
    
    def get_decay_history(self, position_id: str, limit: int = 20) -> List[HealthDecayRecord]:
        """Get decay history for a position"""
        records = self._decay_records.get(position_id, [])
        return records[-limit:]
    
    def clear_decay(self, position_id: str):
        """Clear decay records for a position"""
        if position_id in self._decay_records:
            del self._decay_records[position_id]
    
    def get_decay_rate_info(self) -> Dict[str, Any]:
        """Get decay rate configuration"""
        return {
            "baseRates": {k.value: v for k, v in self._base_rates.items()},
            "timeDecaySchedule": [
                {"maxBars": t, "rate": r} for t, r in self._time_decay_schedule
            ],
            "profitAdjustments": self._profit_adjustments
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        total_records = sum(len(r) for r in self._decay_records.values())
        return {
            "engine": "HealthDecayEngine",
            "version": "1.0.0",
            "phase": "3.2",
            "status": "active",
            "decayTypes": [dt.value for dt in DecayType],
            "trackedPositions": len(self._decay_records),
            "totalRecords": total_records,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
health_decay_engine = HealthDecayEngine()
