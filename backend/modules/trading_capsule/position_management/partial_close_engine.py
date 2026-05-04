"""
Partial Close Engine
====================

Engine for partial position closing (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .position_policy_types import (
    PartialCloseType,
    PartialCloseConfig
)


@dataclass
class PartialCloseDecision:
    """Decision for partial close"""
    should_close: bool
    close_size_pct: float
    reason: str
    remaining_size_pct: float
    move_stop_to_breakeven: bool
    new_stop_price: Optional[float]
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shouldClose": self.should_close,
            "closeSizePct": round(self.close_size_pct, 4),
            "reason": self.reason,
            "remainingSizePct": round(self.remaining_size_pct, 4),
            "moveStopToBreakeven": self.move_stop_to_breakeven,
            "newStopPrice": round(self.new_stop_price, 8) if self.new_stop_price else None,
            "notes": self.notes
        }


class PartialCloseEngine:
    """
    Engine for calculating and managing partial closes.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, PartialCloseConfig]:
        """Build default partial close configs per strategy"""
        
        return {
            # TREND_CONFIRMATION - Multiple partial closes
            "TREND_CONFIRMATION": PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.5, "closePct": 0.3},   # Close 30% at 50% of target
                    {"targetPct": 1.0, "closePct": 0.3},   # Close 30% at target
                    {"targetPct": 2.0, "closePct": 0.4}    # Close 40% at 2x target
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.1
            ),
            
            # MOMENTUM_BREAKOUT - Two-part exit
            "MOMENTUM_BREAKOUT": PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.5, "closePct": 0.5},   # Close 50% at 50% target
                    {"targetPct": 1.0, "closePct": 0.5}    # Close 50% at target
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.1
            ),
            
            # MEAN_REVERSION - Full exit or two-part
            "MEAN_REVERSION": PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.7, "closePct": 0.5},   # Close 50% at 70% target
                    {"targetPct": 1.0, "closePct": 0.5}    # Close 50% at target
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.15
            )
        }
    
    def evaluate_partial_close(
        self,
        strategy: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str,  # LONG or SHORT
        current_position_size: float = 1.0,  # 1.0 = 100%
        already_closed_pct: float = 0.0
    ) -> PartialCloseDecision:
        """
        Evaluate if partial close should happen.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        is_long = direction.upper() == "LONG"
        notes = []
        
        if config.partial_type == PartialCloseType.NONE:
            return PartialCloseDecision(
                should_close=False,
                close_size_pct=0,
                reason="Partial close disabled for strategy",
                remaining_size_pct=current_position_size,
                move_stop_to_breakeven=False,
                new_stop_price=None,
                notes=["Strategy uses full exits only"]
            )
        
        # Calculate progress to target
        if is_long:
            total_target_distance = target_price - entry_price
            current_progress = current_price - entry_price
        else:
            total_target_distance = entry_price - target_price
            current_progress = entry_price - current_price
        
        if total_target_distance <= 0:
            return PartialCloseDecision(
                should_close=False,
                close_size_pct=0,
                reason="Invalid target distance",
                remaining_size_pct=current_position_size,
                move_stop_to_breakeven=False,
                new_stop_price=None,
                notes=["Check target price configuration"]
            )
        
        progress_pct = current_progress / total_target_distance
        
        # Check each level
        for level in config.levels:
            target_pct = level["targetPct"]
            close_pct = level["closePct"]
            
            # Calculate what should have been closed by now
            cumulative_closed = sum(
                l["closePct"] for l in config.levels if l["targetPct"] <= target_pct
            )
            
            # Check if we've reached this level and haven't closed this portion
            if progress_pct >= target_pct and already_closed_pct < cumulative_closed:
                # Calculate how much to close
                size_to_close = min(close_pct, current_position_size)
                remaining = current_position_size - size_to_close
                
                # Calculate breakeven stop
                new_stop = None
                if config.move_to_breakeven and already_closed_pct == 0:
                    buffer = entry_price * (config.breakeven_buffer_pct / 100)
                    if is_long:
                        new_stop = entry_price + buffer
                    else:
                        new_stop = entry_price - buffer
                    notes.append(f"Move stop to breakeven + {config.breakeven_buffer_pct}% buffer")
                
                notes.append(f"Partial close triggered at {target_pct*100}% of target")
                notes.append(f"Progress: {progress_pct*100:.1f}%")
                
                return PartialCloseDecision(
                    should_close=True,
                    close_size_pct=size_to_close,
                    reason=f"Reached {target_pct*100:.0f}% of target",
                    remaining_size_pct=remaining,
                    move_stop_to_breakeven=config.move_to_breakeven and already_closed_pct == 0,
                    new_stop_price=new_stop,
                    notes=notes
                )
        
        notes.append(f"No partial close level reached (progress: {progress_pct*100:.1f}%)")
        return PartialCloseDecision(
            should_close=False,
            close_size_pct=0,
            reason="No level reached",
            remaining_size_pct=current_position_size,
            move_stop_to_breakeven=False,
            new_stop_price=None,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> PartialCloseConfig:
        """Get partial close config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_partial_types(self) -> List[Dict[str, Any]]:
        """Get all partial close types with descriptions"""
        return [
            {
                "type": PartialCloseType.FIXED_LEVELS.value,
                "name": "Fixed Levels",
                "description": "Close portions at predefined target levels",
                "useCases": ["All strategies", "Risk management"],
                "example": "Close 50% at 1R, 50% at 2R"
            },
            {
                "type": PartialCloseType.DYNAMIC.value,
                "name": "Dynamic",
                "description": "Close based on market conditions",
                "useCases": ["Advanced strategies", "Adaptive exits"],
                "example": "Close on momentum loss"
            },
            {
                "type": PartialCloseType.NONE.value,
                "name": "No Partial",
                "description": "Full exits only",
                "useCases": ["Quick trades", "Clear targets"],
                "example": "Exit 100% at target"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-partial close matrix"""
        return {
            strategy: {
                "partialType": config.partial_type.value,
                "levels": config.levels,
                "moveToBreakeven": config.move_to_breakeven
            }
            for strategy, config in self._configs.items()
        }


# Global singleton
partial_close_engine = PartialCloseEngine()
