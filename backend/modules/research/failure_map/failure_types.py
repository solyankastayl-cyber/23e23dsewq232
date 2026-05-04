"""
Failure Types
=============

Core types for Failure Map (PHASE 2.2)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class FailureType(str, Enum):
    """Types of failures detected"""
    FALSE_SIGNAL = "FALSE_SIGNAL"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    STRATEGY_DEGRADATION = "STRATEGY_DEGRADATION"
    SELECTION_ERROR = "SELECTION_ERROR"


class FailureSeverity(str, Enum):
    """Severity of failure"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ===========================================
# False Signal
# ===========================================

@dataclass
class FalseSignal:
    """False signal detection result"""
    trade_id: str = ""
    strategy: str = ""
    symbol: str = ""
    timeframe: str = ""
    regime: str = ""
    
    # Signal details
    entry_price: float = 0.0
    exit_price: float = 0.0
    direction: str = ""  # LONG/SHORT
    r_multiple: float = 0.0
    
    # False signal indicators
    loss_exceeded_1r: bool = False
    duration_too_short: bool = False
    structure_break_after_entry: bool = False
    immediate_reversal: bool = False
    
    # Metadata
    severity: FailureSeverity = FailureSeverity.MEDIUM
    notes: List[str] = field(default_factory=list)
    detected_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "entry": {
                "price": round(self.entry_price, 8),
                "direction": self.direction
            },
            "exit": {
                "price": round(self.exit_price, 8),
                "rMultiple": round(self.r_multiple, 2)
            },
            "indicators": {
                "lossExceeded1R": self.loss_exceeded_1r,
                "durationTooShort": self.duration_too_short,
                "structureBreakAfterEntry": self.structure_break_after_entry,
                "immediateReversal": self.immediate_reversal
            },
            "severity": self.severity.value,
            "notes": self.notes,
            "detectedAt": self.detected_at
        }


# ===========================================
# Regime Mismatch
# ===========================================

@dataclass
class RegimeMismatch:
    """Regime mismatch detection result"""
    trade_id: str = ""
    strategy: str = ""
    symbol: str = ""
    timeframe: str = ""
    
    # Regime details
    expected_regime: str = ""  # What strategy needs
    actual_regime: str = ""    # What market was
    regime_confidence: float = 0.0
    
    # Performance impact
    trade_result: float = 0.0  # R-multiple
    expected_result: float = 0.0  # What it would be in correct regime
    
    # Analysis
    market_behavior: str = ""  # e.g. "trending up", "range bound"
    severity: FailureSeverity = FailureSeverity.MEDIUM
    notes: List[str] = field(default_factory=list)
    detected_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": {
                "expected": self.expected_regime,
                "actual": self.actual_regime,
                "confidence": round(self.regime_confidence, 2)
            },
            "impact": {
                "tradeResult": round(self.trade_result, 2),
                "expectedResult": round(self.expected_result, 2),
                "delta": round(self.expected_result - self.trade_result, 2)
            },
            "marketBehavior": self.market_behavior,
            "severity": self.severity.value,
            "notes": self.notes,
            "detectedAt": self.detected_at
        }


# ===========================================
# Strategy Degradation
# ===========================================

@dataclass
class StrategyDegradation:
    """Strategy degradation detection result"""
    strategy: str = ""
    symbol: str = ""
    timeframe: str = ""
    regime: str = ""
    
    # Historical baseline
    baseline_win_rate: float = 0.0
    baseline_profit_factor: float = 0.0
    baseline_expectancy: float = 0.0
    
    # Current rolling metrics
    rolling_win_rate: float = 0.0
    rolling_profit_factor: float = 0.0
    rolling_expectancy: float = 0.0
    rolling_window: int = 20  # Number of trades in rolling window
    
    # Degradation scores
    win_rate_degradation: float = 0.0  # % decrease
    pf_degradation: float = 0.0
    expectancy_degradation: float = 0.0
    overall_degradation_score: float = 0.0  # 0-100
    
    severity: FailureSeverity = FailureSeverity.MEDIUM
    notes: List[str] = field(default_factory=list)
    detected_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "baseline": {
                "winRate": round(self.baseline_win_rate, 4),
                "profitFactor": round(self.baseline_profit_factor, 2),
                "expectancy": round(self.baseline_expectancy, 4)
            },
            "rolling": {
                "winRate": round(self.rolling_win_rate, 4),
                "profitFactor": round(self.rolling_profit_factor, 2),
                "expectancy": round(self.rolling_expectancy, 4),
                "window": self.rolling_window
            },
            "degradation": {
                "winRate": round(self.win_rate_degradation, 2),
                "profitFactor": round(self.pf_degradation, 2),
                "expectancy": round(self.expectancy_degradation, 2),
                "overallScore": round(self.overall_degradation_score, 1)
            },
            "severity": self.severity.value,
            "notes": self.notes,
            "detectedAt": self.detected_at
        }


# ===========================================
# Selection Error
# ===========================================

@dataclass
class SelectionError:
    """Selection error detection result"""
    trade_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    regime: str = ""
    
    # Selection details
    selected_strategy: str = ""
    selected_score: float = 0.0
    
    # What would have been better
    best_strategy: str = ""
    best_score: float = 0.0
    best_result: float = 0.0  # R-multiple if best was selected
    
    # Actual result
    actual_result: float = 0.0  # R-multiple with selected strategy
    opportunity_cost: float = 0.0  # best_result - actual_result
    
    # All candidates
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    
    severity: FailureSeverity = FailureSeverity.MEDIUM
    notes: List[str] = field(default_factory=list)
    detected_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "selected": {
                "strategy": self.selected_strategy,
                "score": round(self.selected_score, 2),
                "result": round(self.actual_result, 2)
            },
            "optimal": {
                "strategy": self.best_strategy,
                "score": round(self.best_score, 2),
                "result": round(self.best_result, 2)
            },
            "opportunityCost": round(self.opportunity_cost, 2),
            "candidates": self.candidates,
            "severity": self.severity.value,
            "notes": self.notes,
            "detectedAt": self.detected_at
        }


# ===========================================
# Summary Types
# ===========================================

@dataclass
class FailureSummary:
    """Summary of all failures for a strategy"""
    strategy: str = ""
    
    # Counts
    total_trades: int = 0
    false_signals: int = 0
    regime_mismatches: int = 0
    degradation_events: int = 0
    selection_errors: int = 0
    
    # Rates
    false_signal_rate: float = 0.0
    regime_mismatch_rate: float = 0.0
    selection_error_rate: float = 0.0
    degradation_score: float = 0.0
    
    # Clusters (where failures concentrate)
    failure_clusters: List[Dict[str, Any]] = field(default_factory=list)
    
    # Impact
    total_impact_r: float = 0.0  # Total R lost to failures
    
    notes: List[str] = field(default_factory=list)
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "counts": {
                "totalTrades": self.total_trades,
                "falseSignals": self.false_signals,
                "regimeMismatches": self.regime_mismatches,
                "degradationEvents": self.degradation_events,
                "selectionErrors": self.selection_errors
            },
            "rates": {
                "falseSignalRate": round(self.false_signal_rate, 4),
                "regimeMismatchRate": round(self.regime_mismatch_rate, 4),
                "selectionErrorRate": round(self.selection_error_rate, 4),
                "degradationScore": round(self.degradation_score, 1)
            },
            "clusters": self.failure_clusters,
            "totalImpactR": round(self.total_impact_r, 2),
            "notes": self.notes,
            "computedAt": self.computed_at
        }


@dataclass
class FailureScan:
    """Complete failure scan result"""
    scan_id: str = ""
    
    # Configuration
    strategies: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    
    # Results
    false_signals: List[FalseSignal] = field(default_factory=list)
    regime_mismatches: List[RegimeMismatch] = field(default_factory=list)
    degradations: List[StrategyDegradation] = field(default_factory=list)
    selection_errors: List[SelectionError] = field(default_factory=list)
    
    # Summaries
    strategy_summaries: Dict[str, FailureSummary] = field(default_factory=dict)
    
    # Overall stats
    total_failures: int = 0
    failure_by_type: Dict[str, int] = field(default_factory=dict)
    failure_by_severity: Dict[str, int] = field(default_factory=dict)
    
    started_at: int = 0
    completed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scanId": self.scan_id,
            "config": {
                "strategies": self.strategies,
                "symbols": self.symbols,
                "timeframes": self.timeframes
            },
            "results": {
                "falseSignals": [f.to_dict() for f in self.false_signals[:20]],
                "regimeMismatches": [r.to_dict() for r in self.regime_mismatches[:20]],
                "degradations": [d.to_dict() for d in self.degradations[:10]],
                "selectionErrors": [s.to_dict() for s in self.selection_errors[:20]]
            },
            "summaries": {k: v.to_dict() for k, v in self.strategy_summaries.items()},
            "stats": {
                "totalFailures": self.total_failures,
                "byType": self.failure_by_type,
                "bySeverity": self.failure_by_severity
            },
            "timing": {
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
                "durationMs": self.completed_at - self.started_at
            }
        }
