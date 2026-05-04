"""
Position Policy Types
=====================

Core types for Position Management Policy (PHASE 1.3)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


# ===========================================
# Stop Loss Types
# ===========================================

class StopLossType(str, Enum):
    """Stop loss types"""
    HARD_STOP = "HARD_STOP"           # Fixed distance from entry
    STRUCTURE_STOP = "STRUCTURE_STOP"  # Based on market structure
    VOLATILITY_STOP = "VOLATILITY_STOP"  # ATR-based stop


class StopPlacement(str, Enum):
    """Stop placement method"""
    FIXED_DISTANCE = "FIXED_DISTANCE"
    SWING_LOW = "SWING_LOW"
    SWING_HIGH = "SWING_HIGH"
    SUPPORT_LEVEL = "SUPPORT_LEVEL"
    RESISTANCE_LEVEL = "RESISTANCE_LEVEL"
    ATR_MULTIPLE = "ATR_MULTIPLE"
    LIQUIDITY_ZONE = "LIQUIDITY_ZONE"


# ===========================================
# Take Profit Types
# ===========================================

class TakeProfitType(str, Enum):
    """Take profit types"""
    FIXED_RR = "FIXED_RR"           # Fixed risk/reward ratio
    STRUCTURE_TP = "STRUCTURE_TP"   # Based on structure levels
    TRAILING_TP = "TRAILING_TP"     # Trail with price


class TPPlacement(str, Enum):
    """TP placement method"""
    RR_RATIO = "RR_RATIO"           # 1R, 2R, 3R etc
    RESISTANCE = "RESISTANCE"
    SUPPORT = "SUPPORT"
    LIQUIDITY_ZONE = "LIQUIDITY_ZONE"
    VWAP = "VWAP"
    TRAILING = "TRAILING"


# ===========================================
# Trailing Stop Types
# ===========================================

class TrailingStopType(str, Enum):
    """Trailing stop types"""
    ATR_TRAILING = "ATR_TRAILING"         # Move with ATR
    STRUCTURE_TRAILING = "STRUCTURE_TRAILING"  # Move with structure
    TIME_TRAILING = "TIME_TRAILING"       # Tighten over time
    NONE = "NONE"                         # No trailing


class TrailingActivation(str, Enum):
    """When trailing activates"""
    IMMEDIATE = "IMMEDIATE"
    AT_BREAKEVEN = "AT_BREAKEVEN"
    AT_FIRST_TP = "AT_FIRST_TP"
    AFTER_N_BARS = "AFTER_N_BARS"


# ===========================================
# Partial Close Types
# ===========================================

class PartialCloseType(str, Enum):
    """Partial close types"""
    FIXED_LEVELS = "FIXED_LEVELS"   # Close at predefined levels
    DYNAMIC = "DYNAMIC"             # Close based on conditions
    NONE = "NONE"                   # No partial close


# ===========================================
# Time Stop Types
# ===========================================

class TimeStopType(str, Enum):
    """Time stop types"""
    BAR_BASED = "BAR_BASED"         # Exit after N bars
    TIME_BASED = "TIME_BASED"       # Exit after X minutes/hours
    SESSION_BASED = "SESSION_BASED"  # Exit at session end
    NONE = "NONE"                   # No time stop


# ===========================================
# Forced Exit Types
# ===========================================

class ForcedExitTrigger(str, Enum):
    """Forced exit triggers"""
    REGIME_SWITCH = "REGIME_SWITCH"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"
    CORRELATION_SPIKE = "CORRELATION_SPIKE"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"


# ===========================================
# Policy Config Classes
# ===========================================

@dataclass
class StopLossConfig:
    """Stop loss configuration"""
    stop_type: StopLossType = StopLossType.HARD_STOP
    placement: StopPlacement = StopPlacement.FIXED_DISTANCE
    
    # Hard stop params
    risk_distance_pct: float = 1.0  # % from entry
    
    # Structure stop params
    structure_buffer_pct: float = 0.1  # Buffer below/above structure
    lookback_bars: int = 20  # Bars to find structure
    
    # Volatility stop params
    atr_multiplier: float = 1.5
    atr_period: int = 14
    
    # Common
    max_stop_distance_pct: float = 3.0  # Maximum stop distance
    min_stop_distance_pct: float = 0.3  # Minimum stop distance
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stopType": self.stop_type.value,
            "placement": self.placement.value,
            "hardStop": {
                "riskDistancePct": round(self.risk_distance_pct, 4)
            },
            "structureStop": {
                "bufferPct": round(self.structure_buffer_pct, 4),
                "lookbackBars": self.lookback_bars
            },
            "volatilityStop": {
                "atrMultiplier": round(self.atr_multiplier, 2),
                "atrPeriod": self.atr_period
            },
            "limits": {
                "maxDistancePct": round(self.max_stop_distance_pct, 4),
                "minDistancePct": round(self.min_stop_distance_pct, 4)
            }
        }


@dataclass
class TakeProfitConfig:
    """Take profit configuration"""
    tp_type: TakeProfitType = TakeProfitType.FIXED_RR
    placement: TPPlacement = TPPlacement.RR_RATIO
    
    # Fixed RR params
    rr_ratio: float = 2.0  # Risk/Reward ratio
    
    # Structure TP params
    structure_levels: List[str] = field(default_factory=lambda: ["resistance", "liquidity"])
    
    # Trailing TP params
    trailing_activation_pct: float = 0.5  # Activate at 50% of target
    trailing_distance_pct: float = 0.3  # Trail 0.3% behind
    
    # Multi-target
    use_multiple_targets: bool = False
    targets: List[Dict[str, float]] = field(default_factory=list)
    # Example: [{"rr": 1.0, "sizePct": 0.5}, {"rr": 2.0, "sizePct": 0.5}]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tpType": self.tp_type.value,
            "placement": self.placement.value,
            "fixedRR": {
                "rrRatio": round(self.rr_ratio, 2)
            },
            "structureTP": {
                "levels": self.structure_levels
            },
            "trailingTP": {
                "activationPct": round(self.trailing_activation_pct, 4),
                "distancePct": round(self.trailing_distance_pct, 4)
            },
            "multiTarget": {
                "enabled": self.use_multiple_targets,
                "targets": self.targets
            }
        }


@dataclass
class TrailingStopConfig:
    """Trailing stop configuration"""
    trailing_type: TrailingStopType = TrailingStopType.NONE
    activation: TrailingActivation = TrailingActivation.AT_BREAKEVEN
    
    # ATR trailing
    atr_multiplier: float = 1.0
    atr_period: int = 14
    
    # Structure trailing
    structure_lookback: int = 5  # Bars for swing detection
    
    # Time trailing
    tighten_after_bars: int = 20
    tighten_amount_pct: float = 0.2  # Tighten by 20%
    
    # Activation conditions
    activation_profit_pct: float = 0.5  # 0.5% profit to activate
    activation_bars: int = 5  # Bars before activation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trailingType": self.trailing_type.value,
            "activation": self.activation.value,
            "atrTrailing": {
                "multiplier": round(self.atr_multiplier, 2),
                "period": self.atr_period
            },
            "structureTrailing": {
                "lookbackBars": self.structure_lookback
            },
            "timeTrailing": {
                "tightenAfterBars": self.tighten_after_bars,
                "tightenAmountPct": round(self.tighten_amount_pct, 4)
            },
            "activationConditions": {
                "profitPct": round(self.activation_profit_pct, 4),
                "bars": self.activation_bars
            }
        }


@dataclass
class PartialCloseConfig:
    """Partial close configuration"""
    partial_type: PartialCloseType = PartialCloseType.NONE
    
    # Levels for partial close
    levels: List[Dict[str, float]] = field(default_factory=list)
    # Example: [{"targetPct": 0.5, "closePct": 0.5}, {"targetPct": 1.0, "closePct": 0.5}]
    
    # Move stop to breakeven after first partial
    move_to_breakeven: bool = True
    breakeven_buffer_pct: float = 0.1  # Small buffer above entry
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "partialType": self.partial_type.value,
            "levels": self.levels,
            "breakeven": {
                "moveToBreakeven": self.move_to_breakeven,
                "bufferPct": round(self.breakeven_buffer_pct, 4)
            }
        }


@dataclass
class TimeStopConfig:
    """Time stop configuration"""
    time_stop_type: TimeStopType = TimeStopType.NONE
    
    # Bar-based
    max_bars: int = 20
    
    # Time-based
    max_minutes: int = 0
    max_hours: int = 0
    
    # Exit behavior
    exit_at_loss: bool = True  # Exit even if at loss
    reduce_only: bool = False  # Only reduce position, don't add
    partial_exit_pct: float = 1.0  # 100% = full exit
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeStopType": self.time_stop_type.value,
            "barBased": {
                "maxBars": self.max_bars
            },
            "timeBased": {
                "maxMinutes": self.max_minutes,
                "maxHours": self.max_hours
            },
            "exitBehavior": {
                "exitAtLoss": self.exit_at_loss,
                "reduceOnly": self.reduce_only,
                "partialExitPct": round(self.partial_exit_pct, 4)
            }
        }


@dataclass
class ForcedExitConfig:
    """Forced exit configuration"""
    triggers: List[ForcedExitTrigger] = field(default_factory=list)
    
    # Regime switch
    exit_on_regime_switch: bool = True
    allowed_regime_transitions: List[str] = field(default_factory=list)
    
    # Volatility
    volatility_exit_threshold: float = 2.0  # Exit if volatility > 2x normal
    
    # Structure
    structure_break_exit: bool = True
    
    # Risk
    max_position_loss_pct: float = 2.0
    max_daily_loss_pct: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggers": [t.value for t in self.triggers],
            "regimeSwitch": {
                "exitOnSwitch": self.exit_on_regime_switch,
                "allowedTransitions": self.allowed_regime_transitions
            },
            "volatility": {
                "exitThreshold": round(self.volatility_exit_threshold, 2)
            },
            "structure": {
                "breakExit": self.structure_break_exit
            },
            "riskLimits": {
                "maxPositionLossPct": round(self.max_position_loss_pct, 4),
                "maxDailyLossPct": round(self.max_daily_loss_pct, 4)
            }
        }


# ===========================================
# Complete Position Policy
# ===========================================

@dataclass
class PositionPolicy:
    """Complete position management policy"""
    policy_id: str = ""
    name: str = ""
    description: str = ""
    
    # Components
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = field(default_factory=TakeProfitConfig)
    trailing_stop: TrailingStopConfig = field(default_factory=TrailingStopConfig)
    partial_close: PartialCloseConfig = field(default_factory=PartialCloseConfig)
    time_stop: TimeStopConfig = field(default_factory=TimeStopConfig)
    forced_exit: ForcedExitConfig = field(default_factory=ForcedExitConfig)
    
    # Strategy associations
    compatible_strategies: List[str] = field(default_factory=list)
    primary_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policyId": self.policy_id,
            "name": self.name,
            "description": self.description,
            "stopLoss": self.stop_loss.to_dict(),
            "takeProfit": self.take_profit.to_dict(),
            "trailingStop": self.trailing_stop.to_dict(),
            "partialClose": self.partial_close.to_dict(),
            "timeStop": self.time_stop.to_dict(),
            "forcedExit": self.forced_exit.to_dict(),
            "compatibleStrategies": self.compatible_strategies,
            "primaryStrategy": self.primary_strategy
        }
