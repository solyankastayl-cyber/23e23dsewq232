"""
Logic Types (STG2)
==================

Type definitions for Strategy Logic Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class DecisionReason(Enum):
    """Decision reason codes for audit trail"""
    # Entry reasons
    ENTRY_TREND_CONFIRMED = "ENTRY_TREND_CONFIRMED"
    ENTRY_BREAKOUT_CONFIRMED = "ENTRY_BREAKOUT_CONFIRMED"
    ENTRY_PULLBACK_REVERSAL = "ENTRY_PULLBACK_REVERSAL"
    ENTRY_SIGNAL_STRONG = "ENTRY_SIGNAL_STRONG"
    
    # Exit reasons
    EXIT_STOP_LOSS = "EXIT_STOP_LOSS"
    EXIT_TAKE_PROFIT = "EXIT_TAKE_PROFIT"
    EXIT_TIME_BASED = "EXIT_TIME_BASED"
    EXIT_STRUCTURE_BREAK = "EXIT_STRUCTURE_BREAK"
    EXIT_INVALIDATION = "EXIT_INVALIDATION"
    EXIT_OPPOSING_SIGNAL = "EXIT_OPPOSING_SIGNAL"
    EXIT_TRAILING_STOP = "EXIT_TRAILING_STOP"
    
    # Hold reasons
    HOLD_NO_SIGNAL = "HOLD_NO_SIGNAL"
    HOLD_WEAK_SIGNAL = "HOLD_WEAK_SIGNAL"
    HOLD_WAITING_CONFIRMATION = "HOLD_WAITING_CONFIRMATION"
    HOLD_POSITION_OPEN = "HOLD_POSITION_OPEN"
    
    # Block reasons
    BLOCK_LOW_CONFIDENCE = "BLOCK_LOW_CONFIDENCE"
    BLOCK_WRONG_REGIME = "BLOCK_WRONG_REGIME"
    BLOCK_HOSTILE_REGIME = "BLOCK_HOSTILE_REGIME"
    BLOCK_RISK_VETO = "BLOCK_RISK_VETO"
    BLOCK_DAILY_LIMIT = "BLOCK_DAILY_LIMIT"
    BLOCK_EXISTING_POSITION = "BLOCK_EXISTING_POSITION"
    BLOCK_INVALID_PROFILE = "BLOCK_INVALID_PROFILE"
    BLOCK_STRUCTURE_BROKEN = "BLOCK_STRUCTURE_BROKEN"
    BLOCK_NO_VOLUME = "BLOCK_NO_VOLUME"
    BLOCK_EXPOSURE_LIMIT = "BLOCK_EXPOSURE_LIMIT"
    BLOCK_STRATEGY_DISABLED = "BLOCK_STRATEGY_DISABLED"


# ===========================================
# Input Context
# ===========================================

@dataclass
class StrategyInputContext:
    """
    Complete input context for strategy evaluation.
    
    Contains all information needed to make a decision.
    """
    # Strategy context
    strategy_id: str = ""
    profile_id: str = "BALANCED"
    config_id: str = ""
    
    # Market context
    asset: str = "BTC"
    timeframe: str = "4h"
    market_regime: str = "TRENDING"
    
    # Signal data
    signal_score: float = 0.0
    signal_direction: str = ""  # LONG / SHORT / NEUTRAL
    signal_confidence: float = 0.0
    signal_type: str = ""  # breakout / trend / reversal
    
    # Price data
    current_price: float = 0.0
    entry_price: Optional[float] = None  # For exit evaluation
    
    # Indicators
    indicators: Dict[str, Any] = field(default_factory=dict)
    # Example: {"trend": "UP", "momentum": 0.7, "volume_expansion": True, "rsi": 65}
    
    # Structure
    structure_intact: bool = True
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    
    # Current position (if any)
    has_position: bool = False
    position_side: str = ""
    position_size: float = 0.0
    position_entry: float = 0.0
    position_pnl_pct: float = 0.0
    position_bars_held: int = 0
    
    # Portfolio state
    total_exposure_pct: float = 0.0
    daily_pnl_pct: float = 0.0
    entries_today: int = 0
    
    # Risk state
    risk_level: str = "LOW"
    drawdown_pct: float = 0.0
    kill_switch_active: bool = False
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "profileId": self.profile_id,
            "configId": self.config_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "marketRegime": self.market_regime,
            "signal": {
                "score": self.signal_score,
                "direction": self.signal_direction,
                "confidence": self.signal_confidence,
                "type": self.signal_type
            },
            "price": self.current_price,
            "indicators": self.indicators,
            "structure": {
                "intact": self.structure_intact,
                "support": self.support_level,
                "resistance": self.resistance_level
            },
            "position": {
                "hasPosition": self.has_position,
                "side": self.position_side,
                "size": self.position_size,
                "entry": self.position_entry,
                "pnlPct": self.position_pnl_pct,
                "barsHeld": self.position_bars_held
            } if self.has_position else None,
            "portfolio": {
                "exposurePct": self.total_exposure_pct,
                "dailyPnlPct": self.daily_pnl_pct,
                "entriesToday": self.entries_today
            },
            "risk": {
                "level": self.risk_level,
                "drawdownPct": self.drawdown_pct,
                "killSwitchActive": self.kill_switch_active
            },
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Filter Result
# ===========================================

@dataclass
class FilterResult:
    """Result of a filter check"""
    filter_name: str = ""
    passed: bool = True
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filterName": self.filter_name,
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details
        }


# ===========================================
# Strategy Decision
# ===========================================

@dataclass
class StrategyDecision:
    """
    Strategy decision output.
    
    Represents the final decision from strategy evaluation.
    """
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    
    # Strategy context
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Decision
    action: str = "HOLD"  # ENTER_LONG, ENTER_SHORT, EXIT, HOLD, BLOCK
    confidence: float = 0.0
    
    # Reasoning
    reason: DecisionReason = DecisionReason.HOLD_NO_SIGNAL
    reason_text: str = ""
    
    # Filter results
    filters_passed: List[str] = field(default_factory=list)
    filters_blocked: List[str] = field(default_factory=list)
    filter_details: List[FilterResult] = field(default_factory=list)
    
    # Risk veto
    risk_veto: bool = False
    risk_veto_reason: str = ""
    
    # Execution guidance (if ENTER)
    suggested_size_pct: float = 0.0
    suggested_stop_loss: float = 0.0
    suggested_take_profit: float = 0.0
    
    # Metadata
    evaluation_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "action": self.action,
            "confidence": round(self.confidence, 4),
            "reason": self.reason.value if isinstance(self.reason, DecisionReason) else self.reason,
            "reasonText": self.reason_text,
            "filtersPassed": self.filters_passed,
            "filtersBlocked": self.filters_blocked,
            "filterDetails": [f.to_dict() for f in self.filter_details],
            "riskVeto": self.risk_veto,
            "riskVetoReason": self.risk_veto_reason,
            "execution": {
                "suggestedSizePct": round(self.suggested_size_pct, 4),
                "suggestedStopLoss": round(self.suggested_stop_loss, 6) if self.suggested_stop_loss else None,
                "suggestedTakeProfit": round(self.suggested_take_profit, 6) if self.suggested_take_profit else None
            } if self.action.startswith("ENTER") else None,
            "evaluationTimeMs": round(self.evaluation_time_ms, 2),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @property
    def should_enter(self) -> bool:
        return self.action in ["ENTER_LONG", "ENTER_SHORT"] and not self.risk_veto
    
    @property
    def should_exit(self) -> bool:
        return self.action == "EXIT"
    
    @property
    def is_blocked(self) -> bool:
        return self.action == "BLOCK" or self.risk_veto
