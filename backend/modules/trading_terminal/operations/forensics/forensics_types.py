"""
OPS3 Forensics Types
====================

Data structures for trade forensics and investigation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class RootCauseType(str, Enum):
    """Types of root causes for trades"""
    BREAKOUT_SIGNAL = "BREAKOUT_SIGNAL"
    TREND_CONFIRMATION = "TREND_CONFIRMATION"
    MEAN_REVERSION_SIGNAL = "MEAN_REVERSION_SIGNAL"
    REGIME_SHIFT = "REGIME_SHIFT"
    PROFILE_OVERRIDE = "PROFILE_OVERRIDE"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    MTF_ALIGNMENT = "MTF_ALIGNMENT"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"


class ExitReasonType(str, Enum):
    """Types of exit reasons"""
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_EXIT = "TIME_EXIT"
    INVALIDATION = "INVALIDATION"
    OPPOSING_SIGNAL = "OPPOSING_SIGNAL"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    LIQUIDATION = "LIQUIDATION"
    RISK_VETO = "RISK_VETO"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"


class BlockReasonType(str, Enum):
    """Types of block reasons"""
    VOLATILITY_FILTER = "VOLATILITY_FILTER"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    RISK_LIMIT = "RISK_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    DAILY_LIMIT = "DAILY_LIMIT"
    PROFILE_MISMATCH = "PROFILE_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SAFETY_VETO = "SAFETY_VETO"
    KILL_SWITCH = "KILL_SWITCH"
    HOSTILE_REGIME = "HOSTILE_REGIME"


@dataclass
class MarketContextSnapshot:
    """
    Market context at the moment of trade.
    """
    symbol: str = ""
    timeframe: str = ""
    
    # Price data
    price: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    
    # Trend metrics
    trend_strength: float = 0.0
    trend_direction: str = ""  # UP / DOWN / NEUTRAL
    
    # Volatility
    volatility_level: float = 0.0
    atr: float = 0.0
    atr_pct: float = 0.0
    
    # Structure
    range_compression: float = 0.0
    breakout_pressure: float = 0.0
    
    # Regime
    regime: str = ""
    regime_confidence: float = 0.0
    
    # Momentum
    momentum_score: float = 0.0
    rsi: float = 0.0
    
    # Volume
    volume_ratio: float = 0.0
    
    captured_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "price": {
                "current": self.price,
                "open": self.open_price,
                "high": self.high_price,
                "low": self.low_price
            },
            "trend": {
                "strength": round(self.trend_strength, 4),
                "direction": self.trend_direction
            },
            "volatility": {
                "level": round(self.volatility_level, 4),
                "atr": round(self.atr, 6),
                "atrPct": round(self.atr_pct, 4)
            },
            "structure": {
                "rangeCompression": round(self.range_compression, 4),
                "breakoutPressure": round(self.breakout_pressure, 4)
            },
            "regime": {
                "type": self.regime,
                "confidence": round(self.regime_confidence, 4)
            },
            "momentum": {
                "score": round(self.momentum_score, 4),
                "rsi": round(self.rsi, 2)
            },
            "volumeRatio": round(self.volume_ratio, 4),
            "capturedAt": self.captured_at
        }


@dataclass
class StrategyDiagnosticsSnapshot:
    """
    Strategy diagnostics at the moment of decision.
    """
    strategy_id: str = ""
    strategy_name: str = ""
    profile_id: str = ""
    config_id: str = ""
    
    # Signal
    signal_score: float = 0.0
    signal_direction: str = ""
    signal_type: str = ""
    signal_confidence: float = 0.0
    
    # Filters
    filters_passed: List[str] = field(default_factory=list)
    filters_failed: List[str] = field(default_factory=list)
    filter_details: List[Dict[str, Any]] = field(default_factory=list)
    
    # Veto info
    risk_veto: bool = False
    risk_veto_reason: str = ""
    safety_veto: bool = False
    safety_veto_reason: str = ""
    
    # Decision
    decision_action: str = ""
    decision_confidence: float = 0.0
    decision_reason: str = ""
    
    captured_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "profileId": self.profile_id,
            "configId": self.config_id,
            "signal": {
                "score": round(self.signal_score, 4),
                "direction": self.signal_direction,
                "type": self.signal_type,
                "confidence": round(self.signal_confidence, 4)
            },
            "filters": {
                "passed": self.filters_passed,
                "failed": self.filters_failed,
                "details": self.filter_details
            },
            "veto": {
                "riskVeto": self.risk_veto,
                "riskVetoReason": self.risk_veto_reason,
                "safetyVeto": self.safety_veto,
                "safetyVetoReason": self.safety_veto_reason
            },
            "decision": {
                "action": self.decision_action,
                "confidence": round(self.decision_confidence, 4),
                "reason": self.decision_reason
            },
            "capturedAt": self.captured_at
        }


@dataclass
class DecisionTrace:
    """
    Complete trace of how system reached decision.
    This is the core of forensics.
    """
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    
    # Identity
    trade_id: Optional[str] = None
    position_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Timing
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    
    # Pipeline stages
    market_features: Dict[str, Any] = field(default_factory=dict)
    regime_classification: Dict[str, Any] = field(default_factory=dict)
    strategy_filters: List[Dict[str, Any]] = field(default_factory=list)
    risk_checks: List[Dict[str, Any]] = field(default_factory=list)
    safety_checks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Final decision
    final_decision: str = ""  # ENTER_LONG, ENTER_SHORT, EXIT, HOLD, BLOCK
    decision_confidence: float = 0.0
    
    # Execution (if entry)
    execution_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "traceId": self.trace_id,
            "tradeId": self.trade_id,
            "positionId": self.position_id,
            "decisionId": self.decision_id,
            "timestamp": self.timestamp,
            "pipeline": {
                "marketFeatures": self.market_features,
                "regimeClassification": self.regime_classification,
                "strategyFilters": self.strategy_filters,
                "riskChecks": self.risk_checks,
                "safetyChecks": self.safety_checks
            },
            "finalDecision": self.final_decision,
            "decisionConfidence": round(self.decision_confidence, 4),
            "executionDetails": self.execution_details
        }


@dataclass
class RootCause:
    """
    Root cause analysis for a trade.
    Answers: WHAT led to this trade?
    """
    root_cause_type: RootCauseType = RootCauseType.STRATEGY_SIGNAL
    
    # Primary cause
    primary_factor: str = ""
    primary_factor_value: float = 0.0
    
    # Contributing factors
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Confidence in root cause
    confidence: float = 0.0
    
    # Explanation
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.root_cause_type.value,
            "primaryFactor": {
                "name": self.primary_factor,
                "value": round(self.primary_factor_value, 4)
            },
            "contributingFactors": self.contributing_factors,
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation
        }


@dataclass
class BlockAnalysis:
    """
    Analysis of why a trade was blocked.
    Answers: WHY did trade NOT happen?
    """
    block_id: str = field(default_factory=lambda: f"block_{uuid.uuid4().hex[:8]}")
    
    symbol: str = ""
    strategy_id: str = ""
    
    # Block info
    blocked: bool = True
    block_reason_type: BlockReasonType = BlockReasonType.LOW_CONFIDENCE
    block_reason: str = ""
    blocking_layer: str = ""  # REGIME, FILTER, RISK, SAFETY
    
    # Signal that was blocked
    signal_score: float = 0.0
    signal_direction: str = ""
    
    # Context
    regime_at_block: str = ""
    filters_at_block: List[str] = field(default_factory=list)
    
    # Impact estimate
    estimated_pnl_if_taken: Optional[float] = None
    
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "blockId": self.block_id,
            "symbol": self.symbol,
            "strategyId": self.strategy_id,
            "blocked": self.blocked,
            "blockReason": {
                "type": self.block_reason_type.value,
                "text": self.block_reason,
                "layer": self.blocking_layer
            },
            "signal": {
                "score": round(self.signal_score, 4),
                "direction": self.signal_direction
            },
            "context": {
                "regime": self.regime_at_block,
                "failedFilters": self.filters_at_block
            },
            "estimatedPnlIfTaken": self.estimated_pnl_if_taken,
            "timestamp": self.timestamp
        }


@dataclass
class ForensicsTimeline:
    """
    Complete timeline of a trade from signal to close.
    """
    trade_id: str = ""
    position_id: str = ""
    
    # Timeline events
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Key timestamps
    signal_at: Optional[int] = None
    decision_at: Optional[int] = None
    order_at: Optional[int] = None
    fill_at: Optional[int] = None
    position_open_at: Optional[int] = None
    position_close_at: Optional[int] = None
    
    # Durations
    signal_to_decision_ms: int = 0
    decision_to_fill_ms: int = 0
    total_duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "positionId": self.position_id,
            "events": self.events,
            "timestamps": {
                "signalAt": self.signal_at,
                "decisionAt": self.decision_at,
                "orderAt": self.order_at,
                "fillAt": self.fill_at,
                "positionOpenAt": self.position_open_at,
                "positionCloseAt": self.position_close_at
            },
            "durations": {
                "signalToDecisionMs": self.signal_to_decision_ms,
                "decisionToFillMs": self.decision_to_fill_ms,
                "totalDurationMs": self.total_duration_ms
            }
        }


@dataclass
class TradeForensicsReport:
    """
    Complete forensics report for a trade.
    This is the main output of OPS3.
    """
    report_id: str = field(default_factory=lambda: f"forensics_{uuid.uuid4().hex[:12]}")
    
    # Trade identity
    trade_id: str = ""
    position_id: str = ""
    
    # Symbol info
    symbol: str = ""
    exchange: str = ""
    
    # Trade details
    side: str = ""  # LONG / SHORT
    quantity: float = 0.0
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    
    # PnL
    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0
    
    # Ownership
    strategy_id: str = ""
    strategy_name: str = ""
    profile_id: str = ""
    config_id: str = ""
    
    # Market context at entry
    regime: str = ""
    market_context: Optional[MarketContextSnapshot] = None
    
    # Strategy diagnostics
    strategy_diagnostics: Optional[StrategyDiagnosticsSnapshot] = None
    
    # Root cause
    root_cause: Optional[RootCause] = None
    
    # Decision trace
    decision_trace: Optional[DecisionTrace] = None
    
    # Exit analysis
    exit_reason: str = ""
    exit_reason_type: Optional[ExitReasonType] = None
    
    # Timeline
    timeline: Optional[ForensicsTimeline] = None
    
    # Human-readable explanation
    explanation: str = ""
    
    generated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reportId": self.report_id,
            "tradeId": self.trade_id,
            "positionId": self.position_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "trade": {
                "side": self.side,
                "quantity": self.quantity,
                "entryPrice": self.entry_price,
                "exitPrice": self.exit_price
            },
            "pnl": {
                "realized": round(self.realized_pnl, 2),
                "realizedPct": round(self.realized_pnl_pct, 4)
            },
            "ownership": {
                "strategyId": self.strategy_id,
                "strategyName": self.strategy_name,
                "profileId": self.profile_id,
                "configId": self.config_id
            },
            "regime": self.regime,
            "marketContext": self.market_context.to_dict() if self.market_context else None,
            "strategyDiagnostics": self.strategy_diagnostics.to_dict() if self.strategy_diagnostics else None,
            "rootCause": self.root_cause.to_dict() if self.root_cause else None,
            "decisionTrace": self.decision_trace.to_dict() if self.decision_trace else None,
            "exit": {
                "reason": self.exit_reason,
                "type": self.exit_reason_type.value if self.exit_reason_type else None
            } if self.exit_price else None,
            "timeline": self.timeline.to_dict() if self.timeline else None,
            "explanation": self.explanation,
            "generatedAt": self.generated_at
        }


@dataclass
class StrategyBehaviorAnalysis:
    """
    Analysis of strategy behavior patterns.
    """
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Trade counts
    total_signals: int = 0
    signals_taken: int = 0
    signals_blocked: int = 0
    
    # Block reasons breakdown
    block_reasons: Dict[str, int] = field(default_factory=dict)
    
    # Win/loss by regime
    regime_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Filter effectiveness
    filter_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # False signal analysis
    false_signal_rate: float = 0.0
    false_signals_by_regime: Dict[str, float] = field(default_factory=dict)
    
    analyzed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "signals": {
                "total": self.total_signals,
                "taken": self.signals_taken,
                "blocked": self.signals_blocked,
                "blockRate": round(self.signals_blocked / max(1, self.total_signals), 4)
            },
            "blockReasons": self.block_reasons,
            "regimePerformance": self.regime_performance,
            "filterStats": self.filter_stats,
            "falseSignals": {
                "rate": round(self.false_signal_rate, 4),
                "byRegime": self.false_signals_by_regime
            },
            "analyzedAt": self.analyzed_at
        }
