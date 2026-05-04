"""
Behavior Diagnostics Types (STG4)
=================================

Type definitions for Strategy Behavior Diagnostics.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class ExplanationType(Enum):
    """Types of explanations"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    BLOCK = "BLOCK"
    HOLD = "HOLD"


class BlockingLayer(Enum):
    """Layer that blocked the action"""
    REGIME = "REGIME"
    PROFILE = "PROFILE"
    FILTER = "FILTER"
    RISK = "RISK"
    SAFETY = "SAFETY"
    STRATEGY = "STRATEGY"


# ===========================================
# Decision Trace
# ===========================================

@dataclass
class StrategyDecisionTrace:
    """Complete trace of a strategy decision"""
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:8]}")
    
    # Context
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    profile_id: str = ""
    config_id: str = ""
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Decision
    action: str = ""  # ENTER_LONG, ENTER_SHORT, EXIT, HOLD, BLOCK
    reason_code: str = ""
    reason_text: str = ""
    confidence: float = 0.0
    
    # Market context
    market_regime: str = ""
    signal_score: float = 0.0
    signal_direction: str = ""
    signal_type: str = ""
    current_price: float = 0.0
    
    # Filter results
    filters_passed: List[str] = field(default_factory=list)
    filters_blocked: List[str] = field(default_factory=list)
    filter_details: List[Dict] = field(default_factory=list)
    
    # Veto info
    risk_veto: bool = False
    risk_veto_reason: str = ""
    safety_veto: bool = False
    safety_veto_reason: str = ""
    
    # Position context (if any)
    has_position: bool = False
    position_side: str = ""
    position_pnl_pct: float = 0.0
    
    # Execution guidance (if entry)
    suggested_size: float = 0.0
    suggested_sl: float = 0.0
    suggested_tp: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "traceId": self.trace_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "symbol": self.symbol,
            "profileId": self.profile_id,
            "configId": self.config_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "decision": {
                "action": self.action,
                "reasonCode": self.reason_code,
                "reasonText": self.reason_text,
                "confidence": round(self.confidence, 4)
            },
            "marketContext": {
                "regime": self.market_regime,
                "signalScore": round(self.signal_score, 4),
                "signalDirection": self.signal_direction,
                "signalType": self.signal_type,
                "price": self.current_price
            },
            "filters": {
                "passed": self.filters_passed,
                "blocked": self.filters_blocked,
                "details": self.filter_details
            },
            "veto": {
                "riskVeto": self.risk_veto,
                "riskVetoReason": self.risk_veto_reason,
                "safetyVeto": self.safety_veto,
                "safetyVetoReason": self.safety_veto_reason
            },
            "position": {
                "hasPosition": self.has_position,
                "side": self.position_side,
                "pnlPct": round(self.position_pnl_pct, 4)
            } if self.has_position else None,
            "execution": {
                "suggestedSize": round(self.suggested_size, 4),
                "suggestedSL": round(self.suggested_sl, 2),
                "suggestedTP": round(self.suggested_tp, 2)
            } if self.action.startswith("ENTER") else None
        }


# ===========================================
# Entry Explanation
# ===========================================

@dataclass
class EntryExplanation:
    """Explanation for an entry decision"""
    explanation_id: str = field(default_factory=lambda: f"entry_{uuid.uuid4().hex[:8]}")
    
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    profile_id: str = ""
    
    entry_allowed: bool = False
    entry_direction: str = ""  # LONG / SHORT
    
    # Primary reason
    primary_reason: str = ""
    primary_reason_code: str = ""
    
    # Supporting reasons
    supporting_reasons: List[str] = field(default_factory=list)
    
    # Context that enabled entry
    signal_score: float = 0.0
    signal_threshold: float = 0.0
    regime_ok: bool = True
    profile_ok: bool = True
    risk_ok: bool = True
    
    # Filters that passed
    confirmation_filters: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanationId": self.explanation_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "symbol": self.symbol,
            "profileId": self.profile_id,
            "entryAllowed": self.entry_allowed,
            "entryDirection": self.entry_direction,
            "primaryReason": {
                "text": self.primary_reason,
                "code": self.primary_reason_code
            },
            "supportingReasons": self.supporting_reasons,
            "context": {
                "signalScore": round(self.signal_score, 4),
                "signalThreshold": round(self.signal_threshold, 4),
                "regimeOk": self.regime_ok,
                "profileOk": self.profile_ok,
                "riskOk": self.risk_ok
            },
            "confirmationFilters": self.confirmation_filters,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Exit Explanation
# ===========================================

@dataclass
class ExitExplanation:
    """Explanation for an exit decision"""
    explanation_id: str = field(default_factory=lambda: f"exit_{uuid.uuid4().hex[:8]}")
    
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    
    exit_triggered: bool = False
    
    # Exit reason
    exit_reason: str = ""
    exit_reason_code: str = ""
    
    # What triggered the exit
    stop_loss_hit: bool = False
    take_profit_hit: bool = False
    invalidation_triggered: bool = False
    time_exit_triggered: bool = False
    opposing_signal_triggered: bool = False
    structure_break_triggered: bool = False
    
    # Position context
    position_pnl_pct: float = 0.0
    position_bars_held: int = 0
    
    # Thresholds
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    max_bars: int = 0
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanationId": self.explanation_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "symbol": self.symbol,
            "exitTriggered": self.exit_triggered,
            "exitReason": {
                "text": self.exit_reason,
                "code": self.exit_reason_code
            },
            "triggers": {
                "stopLossHit": self.stop_loss_hit,
                "takeProfitHit": self.take_profit_hit,
                "invalidationTriggered": self.invalidation_triggered,
                "timeExitTriggered": self.time_exit_triggered,
                "opposingSignalTriggered": self.opposing_signal_triggered,
                "structureBreakTriggered": self.structure_break_triggered
            },
            "position": {
                "pnlPct": round(self.position_pnl_pct, 4),
                "barsHeld": self.position_bars_held
            },
            "thresholds": {
                "stopLossPct": round(self.stop_loss_pct, 4),
                "takeProfitPct": round(self.take_profit_pct, 4),
                "maxBars": self.max_bars
            },
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Block Explanation
# ===========================================

@dataclass
class BlockExplanation:
    """Explanation for a block decision"""
    explanation_id: str = field(default_factory=lambda: f"block_{uuid.uuid4().hex[:8]}")
    
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    profile_id: str = ""
    
    blocked: bool = True
    
    # Block reason
    block_reason: str = ""
    block_reason_code: str = ""
    
    # What layer blocked
    blocking_layer: str = ""  # REGIME, FILTER, PROFILE, RISK, SAFETY
    
    # Context that caused block
    regime_mismatch: bool = False
    current_regime: str = ""
    required_regimes: List[str] = field(default_factory=list)
    hostile_regime: bool = False
    
    low_confidence: bool = False
    signal_score: float = 0.0
    signal_threshold: float = 0.0
    
    profile_mismatch: bool = False
    
    risk_veto: bool = False
    risk_veto_detail: str = ""
    
    safety_veto: bool = False
    safety_veto_detail: str = ""
    
    filter_blocked: str = ""
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanationId": self.explanation_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "symbol": self.symbol,
            "profileId": self.profile_id,
            "blocked": self.blocked,
            "blockReason": {
                "text": self.block_reason,
                "code": self.block_reason_code
            },
            "blockingLayer": self.blocking_layer,
            "regimeAnalysis": {
                "mismatch": self.regime_mismatch,
                "hostile": self.hostile_regime,
                "current": self.current_regime,
                "required": self.required_regimes
            } if self.regime_mismatch or self.hostile_regime else None,
            "confidenceAnalysis": {
                "lowConfidence": self.low_confidence,
                "signalScore": round(self.signal_score, 4),
                "threshold": round(self.signal_threshold, 4)
            } if self.low_confidence else None,
            "profileMismatch": self.profile_mismatch,
            "riskVeto": {
                "vetoed": self.risk_veto,
                "detail": self.risk_veto_detail
            } if self.risk_veto else None,
            "safetyVeto": {
                "vetoed": self.safety_veto,
                "detail": self.safety_veto_detail
            } if self.safety_veto else None,
            "filterBlocked": self.filter_blocked,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Hold Explanation
# ===========================================

@dataclass
class HoldExplanation:
    """Explanation for a hold decision"""
    explanation_id: str = field(default_factory=lambda: f"hold_{uuid.uuid4().hex[:8]}")
    
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    
    hold_reason: str = ""
    hold_reason_code: str = ""
    
    # What's keeping us on hold
    no_signal: bool = False
    weak_signal: bool = False
    waiting_confirmation: bool = False
    position_management: bool = False
    
    # Signal context
    signal_score: float = 0.0
    signal_threshold: float = 0.0
    
    # What filters need to pass
    pending_filters: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanationId": self.explanation_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "symbol": self.symbol,
            "holdReason": {
                "text": self.hold_reason,
                "code": self.hold_reason_code
            },
            "holdFactors": {
                "noSignal": self.no_signal,
                "weakSignal": self.weak_signal,
                "waitingConfirmation": self.waiting_confirmation,
                "positionManagement": self.position_management
            },
            "signalContext": {
                "score": round(self.signal_score, 4),
                "threshold": round(self.signal_threshold, 4)
            },
            "pendingFilters": self.pending_filters,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
