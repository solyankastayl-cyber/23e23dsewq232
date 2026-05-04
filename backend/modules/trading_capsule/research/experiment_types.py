"""
Experiment Types (S2)
=====================

Type definitions for Research Lab.

Includes:
- ResearchExperiment: Main experiment container
- ExperimentRun: Links experiment to simulation
- StrategyScorecard: Metrics per strategy
- StrategyRankingEntry: Ranked strategy result
- StrategyLeaderboard: Final ranking output
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class ExperimentStatus(Enum):
    """Experiment lifecycle status"""
    CREATED = "CREATED"
    GENERATING = "GENERATING"  # Creating runs
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunStatus(Enum):
    """Individual run status within experiment"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ===========================================
# Research Experiment (S2.1)
# ===========================================

@dataclass
class ResearchExperiment:
    """
    Research experiment container.
    
    Holds configuration and links to runs.
    Single asset / single dataset / N strategies.
    """
    experiment_id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    
    # Experiment name/description
    name: str = ""
    description: str = ""
    
    # Asset configuration
    asset: str = "BTCUSDT"  # Single asset
    
    # Dataset configuration
    dataset_id: str = ""
    start_date: str = ""
    end_date: str = ""
    timeframe: str = "1D"  # 1D, 4H, 1H
    
    # Strategies to compare
    strategies: List[str] = field(default_factory=list)
    
    # Capital configuration
    capital_profile: str = "SMALL"  # SMALL, MEDIUM, LARGE
    initial_capital_usd: float = 10000.0
    
    # Status
    status: ExperimentStatus = ExperimentStatus.CREATED
    error_message: str = ""
    
    # Run tracking
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results (populated after completion)
    winner_strategy_id: str = ""
    winner_composite_score: float = 0.0
    
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
            "strategies": self.strategies,
            "capital_profile": self.capital_profile,
            "initial_capital_usd": self.initial_capital_usd,
            "status": self.status.value,
            "error_message": self.error_message,
            "total_runs": self.total_runs,
            "completed_runs": self.completed_runs,
            "failed_runs": self.failed_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "winner_strategy_id": self.winner_strategy_id,
            "winner_composite_score": round(self.winner_composite_score, 4)
        }


# ===========================================
# Experiment Run (S2.2)
# ===========================================

@dataclass
class ExperimentRun:
    """
    Links experiment to simulation run.
    
    Each strategy in experiment gets one ExperimentRun.
    """
    run_id: str = field(default_factory=lambda: f"exprun_{uuid.uuid4().hex[:8]}")
    
    # Links
    experiment_id: str = ""
    strategy_id: str = ""
    simulation_run_id: str = ""  # Links to SimulationRun
    
    # Status
    status: RunStatus = RunStatus.PENDING
    error_message: str = ""
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Result reference
    metrics_snapshot_id: str = ""  # Reference to saved metrics
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "strategy_id": self.strategy_id,
            "simulation_run_id": self.simulation_run_id,
            "status": self.status.value,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics_snapshot_id": self.metrics_snapshot_id
        }


# ===========================================
# Strategy Scorecard (S2.3)
# ===========================================

@dataclass
class StrategyScorecard:
    """
    Complete metrics for a strategy run.
    
    Used for comparison and ranking.
    """
    experiment_id: str = ""
    strategy_id: str = ""
    simulation_run_id: str = ""
    
    # Performance Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Return Metrics
    total_return_pct: float = 0.0
    annual_return_pct: float = 0.0
    
    # Risk Metrics
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0
    
    # Trade Stats
    win_rate: float = 0.0
    volatility_annual: float = 0.0
    trades_count: int = 0
    
    # Composite (calculated by ranking engine)
    composite_score: float = 0.0
    
    # Validation
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "strategy_id": self.strategy_id,
            "simulation_run_id": self.simulation_run_id,
            
            "performance": {
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "profit_factor": round(self.profit_factor, 4),
                "expectancy": round(self.expectancy, 2)
            },
            
            "returns": {
                "total_return_pct": round(self.total_return_pct, 4),
                "annual_return_pct": round(self.annual_return_pct, 4)
            },
            
            "risk": {
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "calmar_ratio": round(self.calmar_ratio, 4),
                "recovery_factor": round(self.recovery_factor, 4)
            },
            
            "trade_stats": {
                "win_rate": round(self.win_rate, 4),
                "volatility_annual": round(self.volatility_annual, 4),
                "trades_count": self.trades_count
            },
            
            "composite_score": round(self.composite_score, 4),
            "is_valid": self.is_valid,
            "warnings": self.warnings
        }


# ===========================================
# Comparable Strategy (S2.3)
# ===========================================

@dataclass
class ComparableStrategy:
    """
    Strategy with normalized metrics for comparison.
    
    All metrics normalized to 0-1 scale.
    """
    strategy_id: str = ""
    experiment_id: str = ""
    
    # Normalized metrics (0-1 scale)
    normalized_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Raw metrics for reference
    raw_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Warnings from analysis
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "experiment_id": self.experiment_id,
            "normalized_metrics": {
                k: round(v, 4) for k, v in self.normalized_metrics.items()
            },
            "raw_metrics": {
                k: round(v, 4) for k, v in self.raw_metrics.items()
            },
            "warnings": self.warnings
        }


# ===========================================
# Ranking Entry (S2.4)
# ===========================================

@dataclass
class StrategyRankingEntry:
    """
    Single entry in strategy ranking.
    """
    rank: int = 0
    
    experiment_id: str = ""
    strategy_id: str = ""
    simulation_run_id: str = ""
    
    # Composite score
    composite_score: float = 0.0
    
    # Score components (for transparency)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Penalties applied
    penalties: Dict[str, float] = field(default_factory=dict)
    total_penalty: float = 0.0
    
    # Metrics
    normalized_metrics: Dict[str, float] = field(default_factory=dict)
    raw_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "strategy_id": self.strategy_id,
            "simulation_run_id": self.simulation_run_id,
            "composite_score": round(self.composite_score, 4),
            "score_breakdown": {
                k: round(v, 4) for k, v in self.score_breakdown.items()
            },
            "penalties": {
                k: round(v, 4) for k, v in self.penalties.items()
            },
            "total_penalty": round(self.total_penalty, 4),
            "normalized_metrics": {
                k: round(v, 4) for k, v in self.normalized_metrics.items()
            },
            "raw_metrics": {
                k: round(v, 4) for k, v in self.raw_metrics.items()
            },
            "warnings": self.warnings
        }


# ===========================================
# Leaderboard (S2.4)
# ===========================================

@dataclass
class StrategyLeaderboard:
    """
    Final ranking output for an experiment.
    """
    experiment_id: str = ""
    
    # Ranked entries
    entries: List[StrategyRankingEntry] = field(default_factory=list)
    
    # Winner info
    winner_strategy_id: str = ""
    winner_score: float = 0.0
    
    # Stats
    total_strategies: int = 0
    valid_strategies: int = 0
    
    # Ranking config used
    ranking_policy: str = "default"
    
    # Timestamp
    generated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "entries": [e.to_dict() for e in self.entries],
            "winner": {
                "strategy_id": self.winner_strategy_id,
                "score": round(self.winner_score, 4)
            },
            "stats": {
                "total_strategies": self.total_strategies,
                "valid_strategies": self.valid_strategies
            },
            "ranking_policy": self.ranking_policy,
            "generated_at": self.generated_at
        }
