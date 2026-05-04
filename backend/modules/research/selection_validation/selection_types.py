"""
Selection Validation Types
==========================

Core types for Selection Validation (PHASE 2.4)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class ValidationStatus(str, Enum):
    """Status of validation run"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MistakeSeverity(str, Enum):
    """Severity of selection mistake"""
    MINOR = "MINOR"       # Small performance gap
    MODERATE = "MODERATE" # Notable gap
    MAJOR = "MAJOR"       # Significant gap
    CRITICAL = "CRITICAL" # Huge gap, wrong direction


# ===========================================
# Configuration
# ===========================================

@dataclass
class SelectionValidationConfig:
    """Configuration for selection validation"""
    # Strategies to validate
    strategies: List[str] = field(default_factory=lambda: [
        "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"
    ])
    
    # Market settings
    symbol: str = "BTC"
    timeframe: str = "4h"
    candle_count: int = 300
    
    # Simulation settings
    initial_capital: float = 10000.0
    risk_per_trade_pct: float = 1.0
    
    # Validation thresholds
    accuracy_threshold: float = 0.70  # 70% minimum accuracy
    performance_gap_threshold: float = 0.10  # 10% max gap
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategies": self.strategies,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "candleCount": self.candle_count,
            "capital": self.initial_capital,
            "riskPerTrade": self.risk_per_trade_pct,
            "thresholds": {
                "accuracy": self.accuracy_threshold,
                "performanceGap": self.performance_gap_threshold
            }
        }


# ===========================================
# Selection Comparison
# ===========================================

@dataclass
class StrategyResult:
    """Result for a single strategy on a signal"""
    strategy: str = ""
    was_selected: bool = False
    signal_generated: bool = False
    trade_taken: bool = False
    pnl: float = 0.0
    r_multiple: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "wasSelected": self.was_selected,
            "signalGenerated": self.signal_generated,
            "tradeTaken": self.trade_taken,
            "pnl": round(self.pnl, 2),
            "rMultiple": round(self.r_multiple, 2)
        }


@dataclass
class SelectionComparison:
    """Comparison of selected vs best strategy for one decision"""
    bar_index: int = 0
    timestamp: int = 0
    regime: str = ""
    
    # What system chose
    selected_strategy: str = ""
    selected_score: float = 0.0
    selected_result: float = 0.0  # P&L
    selected_r: float = 0.0
    
    # What was actually best
    best_strategy: str = ""
    best_result: float = 0.0
    best_r: float = 0.0
    
    # All results
    all_results: List[StrategyResult] = field(default_factory=list)
    
    # Analysis
    is_correct: bool = False  # Was selected == best?
    performance_gap: float = 0.0  # best - selected
    performance_gap_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "barIndex": self.bar_index,
            "timestamp": self.timestamp,
            "regime": self.regime,
            "selected": {
                "strategy": self.selected_strategy,
                "score": round(self.selected_score, 2),
                "result": round(self.selected_result, 2),
                "rMultiple": round(self.selected_r, 2)
            },
            "best": {
                "strategy": self.best_strategy,
                "result": round(self.best_result, 2),
                "rMultiple": round(self.best_r, 2)
            },
            "allResults": [r.to_dict() for r in self.all_results],
            "analysis": {
                "isCorrect": self.is_correct,
                "performanceGap": round(self.performance_gap, 2),
                "performanceGapPct": round(self.performance_gap_pct, 4)
            }
        }


# ===========================================
# Selection Mistake
# ===========================================

@dataclass
class SelectionMistake:
    """A selection mistake record"""
    bar_index: int = 0
    timestamp: int = 0
    regime: str = ""
    
    # Mistake details
    selected_strategy: str = ""
    best_strategy: str = ""
    
    # Impact
    selected_pnl: float = 0.0
    best_pnl: float = 0.0
    opportunity_cost: float = 0.0
    opportunity_cost_pct: float = 0.0
    
    # Severity
    severity: MistakeSeverity = MistakeSeverity.MINOR
    
    # Context
    reason: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "barIndex": self.bar_index,
            "timestamp": self.timestamp,
            "regime": self.regime,
            "mistake": {
                "selected": self.selected_strategy,
                "shouldHaveBeen": self.best_strategy
            },
            "impact": {
                "selectedPnl": round(self.selected_pnl, 2),
                "bestPnl": round(self.best_pnl, 2),
                "opportunityCost": round(self.opportunity_cost, 2),
                "opportunityCostPct": round(self.opportunity_cost_pct, 4)
            },
            "severity": self.severity.value,
            "reason": self.reason,
            "notes": self.notes
        }


# ===========================================
# Selection Metrics
# ===========================================

@dataclass
class SelectionMetrics:
    """Aggregated selection validation metrics"""
    # Counts
    total_selections: int = 0
    correct_selections: int = 0
    incorrect_selections: int = 0
    
    # Accuracy
    selection_accuracy: float = 0.0
    
    # Performance gap
    total_performance_gap: float = 0.0
    avg_performance_gap: float = 0.0
    avg_performance_gap_pct: float = 0.0
    max_performance_gap: float = 0.0
    
    # By regime
    accuracy_by_regime: Dict[str, float] = field(default_factory=dict)
    
    # By strategy
    selection_count_by_strategy: Dict[str, int] = field(default_factory=dict)
    correct_by_strategy: Dict[str, int] = field(default_factory=dict)
    accuracy_by_strategy: Dict[str, float] = field(default_factory=dict)
    
    # Mistake analysis
    mistake_count_by_severity: Dict[str, int] = field(default_factory=dict)
    most_common_mistakes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Validation result
    passes_accuracy_threshold: bool = False
    passes_gap_threshold: bool = False
    validation_passed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "counts": {
                "total": self.total_selections,
                "correct": self.correct_selections,
                "incorrect": self.incorrect_selections
            },
            "accuracy": {
                "overall": round(self.selection_accuracy, 4),
                "byRegime": {k: round(v, 4) for k, v in self.accuracy_by_regime.items()},
                "byStrategy": {k: round(v, 4) for k, v in self.accuracy_by_strategy.items()}
            },
            "performanceGap": {
                "total": round(self.total_performance_gap, 2),
                "average": round(self.avg_performance_gap, 2),
                "averagePct": round(self.avg_performance_gap_pct, 4),
                "max": round(self.max_performance_gap, 2)
            },
            "selectionsByStrategy": self.selection_count_by_strategy,
            "mistakeAnalysis": {
                "bySeverity": self.mistake_count_by_severity,
                "mostCommon": self.most_common_mistakes[:5]
            },
            "validation": {
                "passesAccuracyThreshold": self.passes_accuracy_threshold,
                "passesGapThreshold": self.passes_gap_threshold,
                "overallPassed": self.validation_passed
            }
        }


# ===========================================
# Validation Run
# ===========================================

@dataclass
class SelectionValidationRun:
    """Complete selection validation run"""
    run_id: str = ""
    status: ValidationStatus = ValidationStatus.PENDING
    config: SelectionValidationConfig = field(default_factory=SelectionValidationConfig)
    
    # Progress
    current_bar: int = 0
    total_bars: int = 0
    progress_pct: float = 0.0
    
    # Results
    comparisons: List[SelectionComparison] = field(default_factory=list)
    mistakes: List[SelectionMistake] = field(default_factory=list)
    metrics: SelectionMetrics = field(default_factory=SelectionMetrics)
    
    # Timing
    started_at: int = 0
    completed_at: int = 0
    duration_ms: int = 0
    
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "progress": {
                "currentBar": self.current_bar,
                "totalBars": self.total_bars,
                "progressPct": round(self.progress_pct, 1)
            },
            "comparisonsCount": len(self.comparisons),
            "recentComparisons": [c.to_dict() for c in self.comparisons[-10:]],
            "mistakesCount": len(self.mistakes),
            "recentMistakes": [m.to_dict() for m in self.mistakes[-10:]],
            "metrics": self.metrics.to_dict(),
            "timing": {
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
                "durationMs": self.duration_ms
            },
            "error": self.error
        }
