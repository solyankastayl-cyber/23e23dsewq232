"""
Trailing Stop Engine
====================

Engine for trailing stop management (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .position_policy_types import (
    TrailingStopType,
    TrailingActivation,
    TrailingStopConfig
)


@dataclass
class TrailingUpdate:
    """Result of trailing stop update"""
    trailing_type: TrailingStopType
    original_stop: float
    new_stop: float
    stop_moved: bool
    current_price: float
    profit_pct: float
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trailingType": self.trailing_type.value,
            "originalStop": round(self.original_stop, 8),
            "newStop": round(self.new_stop, 8),
            "stopMoved": self.stop_moved,
            "currentPrice": round(self.current_price, 8),
            "profitPct": round(self.profit_pct, 4),
            "notes": self.notes
        }


class TrailingStopEngine:
    """
    Engine for calculating and managing trailing stops.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, TrailingStopConfig]:
        """Build default trailing configs per strategy"""
        
        return {
            # TREND_CONFIRMATION - Structure trailing
            "TREND_CONFIRMATION": TrailingStopConfig(
                trailing_type=TrailingStopType.STRUCTURE_TRAILING,
                activation=TrailingActivation.AT_FIRST_TP,
                structure_lookback=5,
                activation_profit_pct=0.5
            ),
            
            # MOMENTUM_BREAKOUT - ATR trailing
            "MOMENTUM_BREAKOUT": TrailingStopConfig(
                trailing_type=TrailingStopType.ATR_TRAILING,
                activation=TrailingActivation.AT_BREAKEVEN,
                atr_multiplier=1.5,
                atr_period=14,
                activation_profit_pct=0.3
            ),
            
            # MEAN_REVERSION - No trailing (exit at targets)
            "MEAN_REVERSION": TrailingStopConfig(
                trailing_type=TrailingStopType.NONE,
                activation=TrailingActivation.AT_FIRST_TP
            )
        }
    
    def calculate_trailing_stop(
        self,
        strategy: str,
        entry_price: float,
        current_stop: float,
        current_price: float,
        direction: str,  # LONG or SHORT
        atr: Optional[float] = None,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None,
        bars_in_trade: int = 0
    ) -> TrailingUpdate:
        """
        Calculate new trailing stop position.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        is_long = direction.upper() == "LONG"
        new_stop = current_stop
        stop_moved = False
        notes = []
        
        # Calculate current profit
        if is_long:
            profit = current_price - entry_price
        else:
            profit = entry_price - current_price
        profit_pct = (profit / entry_price) * 100
        
        # Check if trailing is active
        if config.trailing_type == TrailingStopType.NONE:
            notes.append("No trailing for this strategy")
            return TrailingUpdate(
                trailing_type=config.trailing_type,
                original_stop=current_stop,
                new_stop=current_stop,
                stop_moved=False,
                current_price=current_price,
                profit_pct=profit_pct,
                notes=notes
            )
        
        # Check activation conditions
        trailing_active = profit_pct >= config.activation_profit_pct
        
        if not trailing_active:
            notes.append(f"Trailing not active yet (need {config.activation_profit_pct}% profit, have {profit_pct:.2f}%)")
            return TrailingUpdate(
                trailing_type=config.trailing_type,
                original_stop=current_stop,
                new_stop=current_stop,
                stop_moved=False,
                current_price=current_price,
                profit_pct=profit_pct,
                notes=notes
            )
        
        # Calculate new trailing stop based on type
        if config.trailing_type == TrailingStopType.ATR_TRAILING:
            atr_value = atr or (current_price * 0.01)
            trail_distance = atr_value * config.atr_multiplier
            
            if is_long:
                potential_stop = current_price - trail_distance
                if potential_stop > current_stop:
                    new_stop = potential_stop
                    stop_moved = True
                    notes.append(f"ATR trailing: moved stop up by {(new_stop - current_stop)/entry_price*100:.2f}%")
            else:
                potential_stop = current_price + trail_distance
                if potential_stop < current_stop:
                    new_stop = potential_stop
                    stop_moved = True
                    notes.append(f"ATR trailing: moved stop down by {(current_stop - new_stop)/entry_price*100:.2f}%")
        
        elif config.trailing_type == TrailingStopType.STRUCTURE_TRAILING:
            if is_long:
                # Trail to swing lows for long
                if swing_low and swing_low > current_stop:
                    buffer = swing_low * 0.001  # Small buffer
                    new_stop = swing_low - buffer
                    stop_moved = True
                    notes.append(f"Structure trailing: moved stop to swing low at {swing_low}")
            else:
                # Trail to swing highs for short
                if swing_high and swing_high < current_stop:
                    buffer = swing_high * 0.001
                    new_stop = swing_high + buffer
                    stop_moved = True
                    notes.append(f"Structure trailing: moved stop to swing high at {swing_high}")
        
        elif config.trailing_type == TrailingStopType.TIME_TRAILING:
            # Tighten stop over time
            if bars_in_trade >= config.tighten_after_bars:
                tighten_amount = profit * config.tighten_amount_pct
                
                if is_long:
                    potential_stop = current_stop + tighten_amount
                    if potential_stop < current_price:  # Don't pass current price
                        new_stop = potential_stop
                        stop_moved = True
                        notes.append(f"Time trailing: tightened stop by {config.tighten_amount_pct*100}%")
                else:
                    potential_stop = current_stop - tighten_amount
                    if potential_stop > current_price:
                        new_stop = potential_stop
                        stop_moved = True
                        notes.append(f"Time trailing: tightened stop by {config.tighten_amount_pct*100}%")
        
        if not stop_moved:
            notes.append("Stop not moved (conditions not met)")
        
        return TrailingUpdate(
            trailing_type=config.trailing_type,
            original_stop=current_stop,
            new_stop=new_stop,
            stop_moved=stop_moved,
            current_price=current_price,
            profit_pct=profit_pct,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> TrailingStopConfig:
        """Get trailing config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_trailing_types(self) -> List[Dict[str, Any]]:
        """Get all trailing types with descriptions"""
        return [
            {
                "type": TrailingStopType.ATR_TRAILING.value,
                "name": "ATR Trailing",
                "description": "Stop moves with price at ATR distance",
                "useCases": ["Breakout trades", "Volatile markets"],
                "activationConditions": ["At breakeven", "After N bars"]
            },
            {
                "type": TrailingStopType.STRUCTURE_TRAILING.value,
                "name": "Structure Trailing",
                "description": "Stop moves to new swing lows/highs",
                "useCases": ["Trend following", "Clean structure"],
                "activationConditions": ["After first TP", "Strong momentum"]
            },
            {
                "type": TrailingStopType.TIME_TRAILING.value,
                "name": "Time Trailing",
                "description": "Stop tightens over time if position stagnates",
                "useCases": ["Long holds", "Slow moves"],
                "activationConditions": ["After N bars holding"]
            },
            {
                "type": TrailingStopType.NONE.value,
                "name": "No Trailing",
                "description": "Stop remains fixed, exit at targets only",
                "useCases": ["Mean Reversion", "Quick exits"],
                "activationConditions": []
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-trailing matrix"""
        return {
            strategy: {
                "trailingType": config.trailing_type.value,
                "activation": config.activation.value,
                "activationProfitPct": config.activation_profit_pct
            }
            for strategy, config in self._configs.items()
        }


# Global singleton
trailing_stop_engine = TrailingStopEngine()
