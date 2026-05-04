"""
Stop Policy Engine
==================

Engine for stop loss management (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .position_policy_types import (
    StopLossType,
    StopPlacement,
    StopLossConfig
)


@dataclass
class StopCalculation:
    """Result of stop calculation"""
    stop_type: StopLossType
    entry_price: float
    stop_price: float
    stop_distance: float
    stop_distance_pct: float
    placement: StopPlacement
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stopType": self.stop_type.value,
            "entryPrice": round(self.entry_price, 8),
            "stopPrice": round(self.stop_price, 8),
            "stopDistance": round(self.stop_distance, 8),
            "stopDistancePct": round(self.stop_distance_pct, 4),
            "placement": self.placement.value,
            "notes": self.notes
        }


class StopPolicyEngine:
    """
    Engine for calculating and managing stop losses.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, StopLossConfig]:
        """Build default stop configs per strategy"""
        
        return {
            # TREND_CONFIRMATION - Structure-based stop
            "TREND_CONFIRMATION": StopLossConfig(
                stop_type=StopLossType.STRUCTURE_STOP,
                placement=StopPlacement.SWING_LOW,
                structure_buffer_pct=0.1,
                lookback_bars=20,
                max_stop_distance_pct=2.5,
                min_stop_distance_pct=0.3
            ),
            
            # MOMENTUM_BREAKOUT - Hard stop
            "MOMENTUM_BREAKOUT": StopLossConfig(
                stop_type=StopLossType.HARD_STOP,
                placement=StopPlacement.FIXED_DISTANCE,
                risk_distance_pct=1.0,
                max_stop_distance_pct=2.0,
                min_stop_distance_pct=0.5
            ),
            
            # MEAN_REVERSION - Structure-based stop
            "MEAN_REVERSION": StopLossConfig(
                stop_type=StopLossType.STRUCTURE_STOP,
                placement=StopPlacement.SUPPORT_LEVEL,
                structure_buffer_pct=0.15,
                lookback_bars=30,
                max_stop_distance_pct=3.0,
                min_stop_distance_pct=0.4
            )
        }
    
    def calculate_stop(
        self,
        strategy: str,
        entry_price: float,
        direction: str,  # LONG or SHORT
        atr: Optional[float] = None,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None,
        support: Optional[float] = None,
        resistance: Optional[float] = None
    ) -> StopCalculation:
        """
        Calculate stop loss for given parameters.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        is_long = direction.upper() == "LONG"
        stop_price = 0.0
        notes = []
        
        if config.stop_type == StopLossType.HARD_STOP:
            # Fixed distance stop
            distance = entry_price * (config.risk_distance_pct / 100)
            if is_long:
                stop_price = entry_price - distance
            else:
                stop_price = entry_price + distance
            notes.append(f"Hard stop at {config.risk_distance_pct}% from entry")
        
        elif config.stop_type == StopLossType.STRUCTURE_STOP:
            # Structure-based stop
            if is_long:
                # Use swing low or support for long
                structure_level = swing_low or support or (entry_price * 0.98)
                buffer = structure_level * (config.structure_buffer_pct / 100)
                stop_price = structure_level - buffer
                notes.append(f"Structure stop below swing low/support with {config.structure_buffer_pct}% buffer")
            else:
                # Use swing high or resistance for short
                structure_level = swing_high or resistance or (entry_price * 1.02)
                buffer = structure_level * (config.structure_buffer_pct / 100)
                stop_price = structure_level + buffer
                notes.append(f"Structure stop above swing high/resistance with {config.structure_buffer_pct}% buffer")
        
        elif config.stop_type == StopLossType.VOLATILITY_STOP:
            # ATR-based stop
            atr_value = atr or (entry_price * 0.01)  # Default 1% if no ATR
            distance = atr_value * config.atr_multiplier
            if is_long:
                stop_price = entry_price - distance
            else:
                stop_price = entry_price + distance
            notes.append(f"ATR stop at {config.atr_multiplier}x ATR")
        
        # Calculate distance
        stop_distance = abs(entry_price - stop_price)
        stop_distance_pct = (stop_distance / entry_price) * 100
        
        # Apply limits
        if stop_distance_pct > config.max_stop_distance_pct:
            max_distance = entry_price * (config.max_stop_distance_pct / 100)
            if is_long:
                stop_price = entry_price - max_distance
            else:
                stop_price = entry_price + max_distance
            stop_distance = max_distance
            stop_distance_pct = config.max_stop_distance_pct
            notes.append(f"Stop capped at max {config.max_stop_distance_pct}%")
        
        elif stop_distance_pct < config.min_stop_distance_pct:
            min_distance = entry_price * (config.min_stop_distance_pct / 100)
            if is_long:
                stop_price = entry_price - min_distance
            else:
                stop_price = entry_price + min_distance
            stop_distance = min_distance
            stop_distance_pct = config.min_stop_distance_pct
            notes.append(f"Stop expanded to min {config.min_stop_distance_pct}%")
        
        return StopCalculation(
            stop_type=config.stop_type,
            entry_price=entry_price,
            stop_price=stop_price,
            stop_distance=stop_distance,
            stop_distance_pct=stop_distance_pct,
            placement=config.placement,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> StopLossConfig:
        """Get stop config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_stop_types(self) -> List[Dict[str, Any]]:
        """Get all stop types with descriptions"""
        return [
            {
                "type": StopLossType.HARD_STOP.value,
                "name": "Hard Stop",
                "description": "Fixed distance from entry price",
                "useCases": ["Momentum Breakout", "Clear invalidation"],
                "riskLevel": "LOW"
            },
            {
                "type": StopLossType.STRUCTURE_STOP.value,
                "name": "Structure Stop",
                "description": "Stop based on market structure (swing low/high, support/resistance)",
                "useCases": ["Trend Confirmation", "Mean Reversion"],
                "riskLevel": "MODERATE"
            },
            {
                "type": StopLossType.VOLATILITY_STOP.value,
                "name": "Volatility Stop",
                "description": "ATR-based stop that adapts to market volatility",
                "useCases": ["Volatile markets", "Momentum trades"],
                "riskLevel": "MODERATE"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-stop matrix"""
        return {
            strategy: {
                "stopType": config.stop_type.value,
                "placement": config.placement.value,
                "maxDistancePct": config.max_stop_distance_pct
            }
            for strategy, config in self._configs.items()
        }


# Global singleton
stop_policy_engine = StopPolicyEngine()
