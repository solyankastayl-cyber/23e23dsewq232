"""
Monte Carlo Types (S5)
======================

Type definitions for Monte Carlo Stress Engine.

Includes:
- MonteCarloExperiment: Main experiment entity
- MonteCarloPath: Single simulation path
- MonteCarloDistribution: Statistical distribution of outcomes
- TailRiskMetrics: VaR, CVaR, tail risk analysis
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
    """Monte Carlo experiment status"""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PathGeneratorType(Enum):
    """Type of random path generation"""
    BOOTSTRAP = "BOOTSTRAP"           # Shuffle historical returns
    NOISE_INJECTION = "NOISE_INJECTION"  # Add random noise
    CRASH_INJECTION = "CRASH_INJECTION"   # Add artificial crashes
    REGIME_SWITCH = "REGIME_SWITCH"       # Switch market regimes
    MIXED = "MIXED"                       # Combination of methods


class CrashType(Enum):
    """Types of crash scenarios"""
    FLASH_CRASH = "FLASH_CRASH"       # -10% to -20% in hours
    MARKET_CORRECTION = "MARKET_CORRECTION"  # -20% to -30% over days
    BEAR_MARKET = "BEAR_MARKET"       # -40% to -60% over weeks
    LIQUIDITY_FREEZE = "LIQUIDITY_FREEZE"   # No fills, gaps


# ===========================================
# MonteCarloExperiment (S5.1)
# ===========================================

@dataclass
class MonteCarloExperiment:
    """
    Monte Carlo experiment entity.
    
    Represents a stress test experiment with multiple simulation paths.
    """
    experiment_id: str = field(default_factory=lambda: f"mc_{uuid.uuid4().hex[:12]}")
    
    # Source portfolio
    portfolio_simulation_id: str = ""
    
    # Configuration
    num_paths: int = 1000                      # Number of simulation paths
    horizon_days: int = 365                    # Simulation horizon
    
    # Path generation settings
    generator_type: PathGeneratorType = PathGeneratorType.BOOTSTRAP
    
    # Noise settings
    noise_std: float = 0.02                    # Standard deviation for noise
    
    # Crash injection settings
    crash_probability: float = 0.05            # Probability of crash per path
    crash_severity_min: float = -0.20          # Min crash magnitude
    crash_severity_max: float = -0.50          # Max crash magnitude
    
    # Status
    status: ExperimentStatus = ExperimentStatus.CREATED
    
    # Progress
    completed_paths: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    name: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "portfolio_simulation_id": self.portfolio_simulation_id,
            "config": {
                "num_paths": self.num_paths,
                "horizon_days": self.horizon_days,
                "generator_type": self.generator_type.value,
                "noise_std": round(self.noise_std, 4),
                "crash_probability": round(self.crash_probability, 4),
                "crash_severity_range": [self.crash_severity_min, self.crash_severity_max]
            },
            "status": self.status.value,
            "progress": {
                "completed_paths": self.completed_paths,
                "total_paths": self.num_paths,
                "progress_pct": round(self.completed_paths / self.num_paths * 100, 1) if self.num_paths > 0 else 0
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None
            },
            "name": self.name,
            "description": self.description
        }


# ===========================================
# MonteCarloPath (S5.2)
# ===========================================

@dataclass
class MonteCarloPath:
    """
    Single Monte Carlo simulation path.
    
    Represents one possible future scenario.
    """
    path_id: str = field(default_factory=lambda: f"mcp_{uuid.uuid4().hex[:10]}")
    
    experiment_id: str = ""
    path_index: int = 0
    
    # Results
    initial_equity: float = 0.0
    final_equity: float = 0.0
    
    # Returns
    total_return_usd: float = 0.0
    total_return_pct: float = 0.0
    
    # Risk
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    
    # Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    volatility: float = 0.0
    
    # Path characteristics
    had_crash: bool = False
    crash_magnitude: float = 0.0
    recovery_days: int = 0
    
    # Equity curve (sampled points)
    equity_curve: List[float] = field(default_factory=list)
    
    # Timestamp
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "experiment_id": self.experiment_id,
            "path_index": self.path_index,
            "equity": {
                "initial": round(self.initial_equity, 2),
                "final": round(self.final_equity, 2)
            },
            "returns": {
                "total_usd": round(self.total_return_usd, 2),
                "total_pct": round(self.total_return_pct, 4)
            },
            "risk": {
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "max_drawdown_usd": round(self.max_drawdown_usd, 2)
            },
            "metrics": {
                "sharpe": round(self.sharpe_ratio, 4),
                "sortino": round(self.sortino_ratio, 4),
                "calmar": round(self.calmar_ratio, 4),
                "volatility": round(self.volatility, 4)
            },
            "crash": {
                "had_crash": self.had_crash,
                "magnitude": round(self.crash_magnitude, 4) if self.had_crash else None,
                "recovery_days": self.recovery_days if self.had_crash else None
            },
            "equity_curve_length": len(self.equity_curve),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }


# ===========================================
# MonteCarloDistribution (S5.3)
# ===========================================

@dataclass
class MonteCarloDistribution:
    """
    Statistical distribution of Monte Carlo outcomes.
    """
    experiment_id: str = ""
    
    # Return distribution
    mean_return_pct: float = 0.0
    median_return_pct: float = 0.0
    std_return_pct: float = 0.0
    
    min_return_pct: float = 0.0
    max_return_pct: float = 0.0
    
    # Percentiles
    percentile_5: float = 0.0
    percentile_10: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    percentile_90: float = 0.0
    percentile_95: float = 0.0
    
    # Drawdown distribution
    mean_max_dd_pct: float = 0.0
    median_max_dd_pct: float = 0.0
    worst_max_dd_pct: float = 0.0
    
    # Sharpe distribution
    mean_sharpe: float = 0.0
    median_sharpe: float = 0.0
    
    # Path counts
    total_paths: int = 0
    profitable_paths: int = 0
    crash_paths: int = 0
    
    # Calculated at
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "returns": {
                "mean_pct": round(self.mean_return_pct, 4),
                "median_pct": round(self.median_return_pct, 4),
                "std_pct": round(self.std_return_pct, 4),
                "min_pct": round(self.min_return_pct, 4),
                "max_pct": round(self.max_return_pct, 4)
            },
            "percentiles": {
                "p5": round(self.percentile_5, 4),
                "p10": round(self.percentile_10, 4),
                "p25": round(self.percentile_25, 4),
                "p50": round(self.median_return_pct, 4),
                "p75": round(self.percentile_75, 4),
                "p90": round(self.percentile_90, 4),
                "p95": round(self.percentile_95, 4)
            },
            "drawdown": {
                "mean_max_dd_pct": round(self.mean_max_dd_pct, 4),
                "median_max_dd_pct": round(self.median_max_dd_pct, 4),
                "worst_max_dd_pct": round(self.worst_max_dd_pct, 4)
            },
            "sharpe": {
                "mean": round(self.mean_sharpe, 4),
                "median": round(self.median_sharpe, 4)
            },
            "path_counts": {
                "total": self.total_paths,
                "profitable": self.profitable_paths,
                "profitable_pct": round(self.profitable_paths / self.total_paths * 100, 1) if self.total_paths > 0 else 0,
                "crash_paths": self.crash_paths
            },
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


# ===========================================
# TailRiskMetrics (S5.4)
# ===========================================

@dataclass
class TailRiskMetrics:
    """
    Tail risk analysis from Monte Carlo simulation.
    
    VaR (Value at Risk): Maximum loss at confidence level
    CVaR (Conditional VaR): Expected loss in worst cases
    """
    experiment_id: str = ""
    
    # VaR at different confidence levels
    var_90_pct: float = 0.0       # 90% confidence
    var_95_pct: float = 0.0       # 95% confidence (standard)
    var_99_pct: float = 0.0       # 99% confidence
    
    # CVaR (Expected Shortfall)
    cvar_90_pct: float = 0.0
    cvar_95_pct: float = 0.0
    cvar_99_pct: float = 0.0
    
    # In USD terms (for reference capital)
    reference_capital: float = 100000.0
    var_95_usd: float = 0.0
    cvar_95_usd: float = 0.0
    
    # Maximum observed loss
    max_loss_pct: float = 0.0
    max_loss_usd: float = 0.0
    
    # Probability of ruin (>50% loss)
    prob_ruin_50: float = 0.0
    prob_ruin_75: float = 0.0
    
    # Worst path details
    worst_path_id: str = ""
    worst_path_return_pct: float = 0.0
    worst_path_max_dd_pct: float = 0.0
    
    # Calculated at
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "var": {
                "var_90_pct": round(self.var_90_pct, 4),
                "var_95_pct": round(self.var_95_pct, 4),
                "var_99_pct": round(self.var_99_pct, 4)
            },
            "cvar": {
                "cvar_90_pct": round(self.cvar_90_pct, 4),
                "cvar_95_pct": round(self.cvar_95_pct, 4),
                "cvar_99_pct": round(self.cvar_99_pct, 4)
            },
            "usd_impact": {
                "reference_capital": round(self.reference_capital, 2),
                "var_95_usd": round(self.var_95_usd, 2),
                "cvar_95_usd": round(self.cvar_95_usd, 2)
            },
            "maximum_loss": {
                "pct": round(self.max_loss_pct, 4),
                "usd": round(self.max_loss_usd, 2)
            },
            "probability_of_ruin": {
                "prob_50pct_loss": round(self.prob_ruin_50, 4),
                "prob_75pct_loss": round(self.prob_ruin_75, 4)
            },
            "worst_path": {
                "path_id": self.worst_path_id,
                "return_pct": round(self.worst_path_return_pct, 4),
                "max_dd_pct": round(self.worst_path_max_dd_pct, 4)
            },
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


# ===========================================
# Scenario Summary
# ===========================================

@dataclass
class ScenarioSummary:
    """Summary of scenarios by outcome type"""
    experiment_id: str = ""
    
    # Scenario counts
    best_case_count: int = 0      # Top 10%
    good_case_count: int = 0      # 10-50%
    median_case_count: int = 0    # 40-60%
    bad_case_count: int = 0       # 50-90%
    worst_case_count: int = 0     # Bottom 10%
    
    # Representative paths
    best_case_path_id: str = ""
    median_case_path_id: str = ""
    worst_case_path_id: str = ""
    
    # Summary returns
    best_case_return_pct: float = 0.0
    median_case_return_pct: float = 0.0
    worst_case_return_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "scenario_counts": {
                "best_case": self.best_case_count,
                "good_case": self.good_case_count,
                "median_case": self.median_case_count,
                "bad_case": self.bad_case_count,
                "worst_case": self.worst_case_count
            },
            "representative_paths": {
                "best": self.best_case_path_id,
                "median": self.median_case_path_id,
                "worst": self.worst_case_path_id
            },
            "returns": {
                "best_case_pct": round(self.best_case_return_pct, 4),
                "median_case_pct": round(self.median_case_return_pct, 4),
                "worst_case_pct": round(self.worst_case_return_pct, 4)
            }
        }
