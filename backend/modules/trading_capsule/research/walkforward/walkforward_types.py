"""
Walk Forward Types (S2.6)
=========================

Type definitions for Walk Forward Analysis.

Includes:
- WalkForwardExperiment: Meta-experiment container
- WalkForwardWindow: Train/test window definition
- WalkForwardRun: Links window to simulation runs
- WindowComparison: Train vs test metrics
- StrategyRobustness: Final robustness assessment
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class WalkForwardStatus(Enum):
    """Walk Forward experiment lifecycle"""
    CREATED = "CREATED"
    GENERATING = "GENERATING"
    RUNNING = "RUNNING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WFRunStatus(Enum):
    """Individual run status"""
    PENDING = "PENDING"
    TRAIN_RUNNING = "TRAIN_RUNNING"
    TRAIN_COMPLETE = "TRAIN_COMPLETE"
    TEST_RUNNING = "TEST_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RobustnessVerdict(Enum):
    """Strategy robustness verdict"""
    ROBUST = "ROBUST"        # Low degradation, stable across windows
    STABLE = "STABLE"        # Acceptable degradation, fairly consistent
    WEAK = "WEAK"            # Higher degradation but not terrible
    OVERFIT = "OVERFIT"      # Strong train, weak test
    UNSTABLE = "UNSTABLE"    # High variance across windows


# ===========================================
# Walk Forward Experiment (S2.6A)
# ===========================================

@dataclass
class WalkForwardExperiment:
    """
    Walk Forward meta-experiment.
    
    Manages series of train/test experiments across rolling windows.
    """
    experiment_id: str = field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    
    # Name/description
    name: str = ""
    description: str = ""
    
    # Dataset configuration
    asset: str = "BTCUSDT"
    dataset_id: str = ""
    start_date: str = ""  # Overall dataset start
    end_date: str = ""    # Overall dataset end
    timeframe: str = "1D"
    
    # Window configuration (in bars)
    train_window_bars: int = 730    # ~2 years daily
    test_window_bars: int = 365     # ~1 year daily
    step_bars: int = 365            # Roll forward 1 year
    
    # Strategies to test
    strategies: List[str] = field(default_factory=list)
    
    # Capital
    capital_profile: str = "SMALL"
    initial_capital_usd: float = 10000.0
    
    # Status
    status: WalkForwardStatus = WalkForwardStatus.CREATED
    error_message: str = ""
    
    # Window tracking
    total_windows: int = 0
    completed_windows: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "asset": self.asset,
            "dataset_id": self.dataset_id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "timeframe": self.timeframe,
            "window_config": {
                "train_window_bars": self.train_window_bars,
                "test_window_bars": self.test_window_bars,
                "step_bars": self.step_bars
            },
            "strategies": self.strategies,
            "capital_profile": self.capital_profile,
            "initial_capital_usd": self.initial_capital_usd,
            "status": self.status.value,
            "error_message": self.error_message,
            "total_windows": self.total_windows,
            "completed_windows": self.completed_windows,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# ===========================================
# Walk Forward Window (S2.6A)
# ===========================================

@dataclass
class WalkForwardWindow:
    """
    Single train/test window in Walk Forward analysis.
    
    Critical: train_end < test_start (no look-ahead bias)
    """
    window_id: str = field(default_factory=lambda: f"wfwin_{uuid.uuid4().hex[:8]}")
    experiment_id: str = ""
    
    # Window index (0, 1, 2, ...)
    index: int = 0
    
    # Train period (bar indices)
    train_start_bar: int = 0
    train_end_bar: int = 0
    
    # Test period (bar indices)
    test_start_bar: int = 0
    test_end_bar: int = 0
    
    # Date representations (for display)
    train_start_date: str = ""
    train_end_date: str = ""
    test_start_date: str = ""
    test_end_date: str = ""
    
    # Window stats
    train_bars: int = 0
    test_bars: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "experiment_id": self.experiment_id,
            "index": self.index,
            "train": {
                "start_bar": self.train_start_bar,
                "end_bar": self.train_end_bar,
                "start_date": self.train_start_date,
                "end_date": self.train_end_date,
                "bars": self.train_bars
            },
            "test": {
                "start_bar": self.test_start_bar,
                "end_bar": self.test_end_bar,
                "start_date": self.test_start_date,
                "end_date": self.test_end_date,
                "bars": self.test_bars
            }
        }


# ===========================================
# Walk Forward Run (S2.6B)
# ===========================================

@dataclass
class WalkForwardRun:
    """
    Links a strategy to a specific window's train/test runs.
    """
    run_id: str = field(default_factory=lambda: f"wfrun_{uuid.uuid4().hex[:8]}")
    
    experiment_id: str = ""
    window_id: str = ""
    strategy_id: str = ""
    window_index: int = 0
    
    # Linked experiment IDs (regular S2 experiments)
    train_experiment_id: str = ""
    test_experiment_id: str = ""
    
    # Linked simulation run IDs
    train_simulation_run_id: str = ""
    test_simulation_run_id: str = ""
    
    # Status
    status: WFRunStatus = WFRunStatus.PENDING
    error_message: str = ""
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "window_id": self.window_id,
            "window_index": self.window_index,
            "strategy_id": self.strategy_id,
            "train_experiment_id": self.train_experiment_id,
            "test_experiment_id": self.test_experiment_id,
            "train_simulation_run_id": self.train_simulation_run_id,
            "test_simulation_run_id": self.test_simulation_run_id,
            "status": self.status.value,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# ===========================================
# Window Comparison (S2.6C)
# ===========================================

@dataclass
class WindowComparison:
    """
    Train vs Test metrics comparison for a single window.
    """
    strategy_id: str = ""
    window_id: str = ""
    window_index: int = 0
    
    # Train metrics
    train_sharpe: float = 0.0
    train_sortino: float = 0.0
    train_profit_factor: float = 0.0
    train_calmar: float = 0.0
    train_max_drawdown: float = 0.0
    train_expectancy: float = 0.0
    train_win_rate: float = 0.0
    train_trades_count: int = 0
    
    # Test metrics
    test_sharpe: float = 0.0
    test_sortino: float = 0.0
    test_profit_factor: float = 0.0
    test_calmar: float = 0.0
    test_max_drawdown: float = 0.0
    test_expectancy: float = 0.0
    test_win_rate: float = 0.0
    test_trades_count: int = 0
    
    # Degradation (test - train) / |train|
    sharpe_degradation: float = 0.0
    sortino_degradation: float = 0.0
    pf_degradation: float = 0.0
    calmar_degradation: float = 0.0
    
    # Is this window valid?
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "window_id": self.window_id,
            "window_index": self.window_index,
            "train_metrics": {
                "sharpe": round(self.train_sharpe, 4),
                "sortino": round(self.train_sortino, 4),
                "profit_factor": round(self.train_profit_factor, 4),
                "calmar": round(self.train_calmar, 4),
                "max_drawdown": round(self.train_max_drawdown, 4),
                "expectancy": round(self.train_expectancy, 2),
                "win_rate": round(self.train_win_rate, 4),
                "trades_count": self.train_trades_count
            },
            "test_metrics": {
                "sharpe": round(self.test_sharpe, 4),
                "sortino": round(self.test_sortino, 4),
                "profit_factor": round(self.test_profit_factor, 4),
                "calmar": round(self.test_calmar, 4),
                "max_drawdown": round(self.test_max_drawdown, 4),
                "expectancy": round(self.test_expectancy, 2),
                "win_rate": round(self.test_win_rate, 4),
                "trades_count": self.test_trades_count
            },
            "degradation": {
                "sharpe": round(self.sharpe_degradation, 4),
                "sortino": round(self.sortino_degradation, 4),
                "profit_factor": round(self.pf_degradation, 4),
                "calmar": round(self.calmar_degradation, 4)
            },
            "is_valid": self.is_valid
        }


# ===========================================
# Strategy Robustness (S2.6C)
# ===========================================

@dataclass
class StrategyRobustness:
    """
    Final robustness assessment for a strategy.
    """
    strategy_id: str = ""
    experiment_id: str = ""
    
    # Windows analyzed
    windows_count: int = 0
    valid_windows: int = 0
    
    # Average train metrics
    avg_train_sharpe: float = 0.0
    avg_train_sortino: float = 0.0
    avg_train_profit_factor: float = 0.0
    avg_train_calmar: float = 0.0
    avg_train_max_drawdown: float = 0.0
    
    # Average test metrics
    avg_test_sharpe: float = 0.0
    avg_test_sortino: float = 0.0
    avg_test_profit_factor: float = 0.0
    avg_test_calmar: float = 0.0
    avg_test_max_drawdown: float = 0.0
    
    # Degradation averages
    avg_sharpe_degradation: float = 0.0
    avg_pf_degradation: float = 0.0
    avg_calmar_degradation: float = 0.0
    
    # Stability (std dev across windows)
    train_sharpe_std: float = 0.0
    test_sharpe_std: float = 0.0
    
    # Scores
    stability_score: float = 0.0     # 0-1, higher = more stable
    degradation_score: float = 0.0   # 0-1, higher = less degradation
    robustness_score: float = 0.0    # 0-1, composite score
    
    # Final verdict
    verdict: RobustnessVerdict = RobustnessVerdict.WEAK
    verdict_reasons: List[str] = field(default_factory=list)
    
    # Per-window comparisons
    window_comparisons: List[WindowComparison] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "experiment_id": self.experiment_id,
            
            "windows": {
                "total": self.windows_count,
                "valid": self.valid_windows
            },
            
            "avg_train_metrics": {
                "sharpe": round(self.avg_train_sharpe, 4),
                "sortino": round(self.avg_train_sortino, 4),
                "profit_factor": round(self.avg_train_profit_factor, 4),
                "calmar": round(self.avg_train_calmar, 4),
                "max_drawdown": round(self.avg_train_max_drawdown, 4)
            },
            
            "avg_test_metrics": {
                "sharpe": round(self.avg_test_sharpe, 4),
                "sortino": round(self.avg_test_sortino, 4),
                "profit_factor": round(self.avg_test_profit_factor, 4),
                "calmar": round(self.avg_test_calmar, 4),
                "max_drawdown": round(self.avg_test_max_drawdown, 4)
            },
            
            "degradation": {
                "sharpe": round(self.avg_sharpe_degradation, 4),
                "profit_factor": round(self.avg_pf_degradation, 4),
                "calmar": round(self.avg_calmar_degradation, 4)
            },
            
            "stability": {
                "train_sharpe_std": round(self.train_sharpe_std, 4),
                "test_sharpe_std": round(self.test_sharpe_std, 4),
                "stability_score": round(self.stability_score, 4)
            },
            
            "scores": {
                "degradation_score": round(self.degradation_score, 4),
                "robustness_score": round(self.robustness_score, 4)
            },
            
            "verdict": self.verdict.value,
            "verdict_reasons": self.verdict_reasons
        }


# ===========================================
# Walk Forward Results
# ===========================================

@dataclass
class WalkForwardResults:
    """
    Complete Walk Forward analysis results.
    """
    experiment_id: str = ""
    
    # Results per strategy
    strategy_results: List[StrategyRobustness] = field(default_factory=list)
    
    # Best strategy
    best_strategy_id: str = ""
    best_robustness_score: float = 0.0
    
    # Summary stats
    total_strategies: int = 0
    robust_count: int = 0
    overfit_count: int = 0
    
    # Timestamp
    analyzed_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "strategy_results": [r.to_dict() for r in self.strategy_results],
            "best_strategy": {
                "strategy_id": self.best_strategy_id,
                "robustness_score": round(self.best_robustness_score, 4)
            },
            "summary": {
                "total_strategies": self.total_strategies,
                "robust_count": self.robust_count,
                "overfit_count": self.overfit_count
            },
            "analyzed_at": self.analyzed_at
        }
