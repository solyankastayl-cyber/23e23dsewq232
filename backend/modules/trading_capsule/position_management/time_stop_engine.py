"""
Time Stop Engine
================

Engine for time-based exits (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .position_policy_types import (
    TimeStopType,
    TimeStopConfig
)


@dataclass
class TimeStopDecision:
    """Decision for time-based exit"""
    should_exit: bool
    exit_type: str  # "full", "partial", "none"
    exit_size_pct: float
    reason: str
    bars_held: int
    max_bars: int
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shouldExit": self.should_exit,
            "exitType": self.exit_type,
            "exitSizePct": round(self.exit_size_pct, 4),
            "reason": self.reason,
            "barsHeld": self.bars_held,
            "maxBars": self.max_bars,
            "notes": self.notes
        }


class TimeStopEngine:
    """
    Engine for managing time-based exits.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, TimeStopConfig]:
        """Build default time stop configs per strategy"""
        
        return {
            # TREND_CONFIRMATION - Optional time stop
            "TREND_CONFIRMATION": TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=50,  # Long holding allowed
                exit_at_loss=False,  # Only exit if at profit or breakeven
                reduce_only=True,
                partial_exit_pct=0.5  # Reduce 50%
            ),
            
            # MOMENTUM_BREAKOUT - Required time stop
            "MOMENTUM_BREAKOUT": TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=10,  # Quick resolution required
                exit_at_loss=True,
                reduce_only=False,
                partial_exit_pct=1.0  # Full exit
            ),
            
            # MEAN_REVERSION - Required time stop
            "MEAN_REVERSION": TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=30,  # Medium term
                exit_at_loss=True,
                reduce_only=False,
                partial_exit_pct=1.0  # Full exit
            )
        }
    
    def evaluate_time_stop(
        self,
        strategy: str,
        bars_held: int,
        entry_price: float,
        current_price: float,
        direction: str,  # LONG or SHORT
        current_position_size: float = 1.0
    ) -> TimeStopDecision:
        """
        Evaluate if time stop should trigger.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        notes = []
        
        if config.time_stop_type == TimeStopType.NONE:
            return TimeStopDecision(
                should_exit=False,
                exit_type="none",
                exit_size_pct=0,
                reason="Time stop disabled",
                bars_held=bars_held,
                max_bars=0,
                notes=["Strategy does not use time stops"]
            )
        
        is_long = direction.upper() == "LONG"
        
        # Calculate P&L
        if is_long:
            pnl = current_price - entry_price
        else:
            pnl = entry_price - current_price
        
        is_profitable = pnl > 0
        is_at_loss = pnl < 0
        
        # Check if max time exceeded
        time_exceeded = bars_held >= config.max_bars
        
        if not time_exceeded:
            notes.append(f"Time stop not triggered ({bars_held}/{config.max_bars} bars)")
            return TimeStopDecision(
                should_exit=False,
                exit_type="none",
                exit_size_pct=0,
                reason="Time not exceeded",
                bars_held=bars_held,
                max_bars=config.max_bars,
                notes=notes
            )
        
        # Time exceeded - check exit conditions
        notes.append(f"Max holding time reached ({bars_held} bars)")
        
        if is_at_loss and not config.exit_at_loss:
            notes.append("Position at loss but exit_at_loss=False, holding")
            return TimeStopDecision(
                should_exit=False,
                exit_type="none",
                exit_size_pct=0,
                reason="At loss, time exit not forced",
                bars_held=bars_held,
                max_bars=config.max_bars,
                notes=notes
            )
        
        # Determine exit type and size
        exit_size = current_position_size * config.partial_exit_pct
        exit_type = "full" if config.partial_exit_pct >= 1.0 else "partial"
        
        if config.reduce_only:
            notes.append("Reduce-only mode: partial exit")
            exit_type = "partial"
            exit_size = min(exit_size, current_position_size * 0.5)
        
        pnl_status = "profitable" if is_profitable else "at loss" if is_at_loss else "breakeven"
        notes.append(f"Position is {pnl_status}")
        
        return TimeStopDecision(
            should_exit=True,
            exit_type=exit_type,
            exit_size_pct=exit_size,
            reason=f"Time stop after {bars_held} bars",
            bars_held=bars_held,
            max_bars=config.max_bars,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> TimeStopConfig:
        """Get time stop config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_time_stop_types(self) -> List[Dict[str, Any]]:
        """Get all time stop types with descriptions"""
        return [
            {
                "type": TimeStopType.BAR_BASED.value,
                "name": "Bar-Based",
                "description": "Exit after N bars/candles",
                "useCases": ["Momentum trades", "Short-term strategies"],
                "example": "Exit after 10 bars if trade not working"
            },
            {
                "type": TimeStopType.TIME_BASED.value,
                "name": "Time-Based",
                "description": "Exit after X minutes/hours",
                "useCases": ["Day trading", "Session-specific"],
                "example": "Exit after 4 hours"
            },
            {
                "type": TimeStopType.SESSION_BASED.value,
                "name": "Session-Based",
                "description": "Exit at end of trading session",
                "useCases": ["Intraday only", "No overnight holds"],
                "example": "Exit before market close"
            },
            {
                "type": TimeStopType.NONE.value,
                "name": "No Time Stop",
                "description": "Hold until target or stop hit",
                "useCases": ["Swing trades", "Position trades"],
                "example": "No time limit"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-time stop matrix"""
        return {
            strategy: {
                "timeStopType": config.time_stop_type.value,
                "maxBars": config.max_bars,
                "exitAtLoss": config.exit_at_loss,
                "required": config.time_stop_type != TimeStopType.NONE
            }
            for strategy, config in self._configs.items()
        }
    
    def is_time_stop_required(self, strategy: str) -> bool:
        """Check if time stop is required for strategy"""
        config = self.get_config_for_strategy(strategy)
        return config.time_stop_type != TimeStopType.NONE


# Global singleton
time_stop_engine = TimeStopEngine()
