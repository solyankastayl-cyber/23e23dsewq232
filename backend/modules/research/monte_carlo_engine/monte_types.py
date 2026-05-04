"""
PHASE 6.3 - Monte Carlo Engine Types
=====================================
Core data types for Monte Carlo risk analysis.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class MonteCarloMethod(str, Enum):
    """Simulation methods"""
    BOOTSTRAP = "BOOTSTRAP"           # Resample trades with replacement
    SHUFFLE = "SHUFFLE"               # Random trade order
    NOISE_INJECTION = "NOISE_INJECTION"  # Add random noise to returns
    COMBINED = "COMBINED"             # All methods combined


class MonteCarloVerdict(str, Enum):
    """Risk assessment verdict"""
    ROBUST = "ROBUST"           # Excellent risk profile
    ACCEPTABLE = "ACCEPTABLE"   # Good enough for trading
    RISKY = "RISKY"             # High risk, use caution
    UNTRADABLE = "UNTRADABLE"   # Too risky


class MonteCarloStatus(str, Enum):
    """Run status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TradeRecord:
    """Single trade for simulation"""
    trade_id: str
    return_pct: float
    duration_candles: int = 1
    win: bool = True
    risk_taken: float = 0.02
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "return_pct": round(self.return_pct, 4),
            "duration_candles": self.duration_candles,
            "win": self.win,
            "risk_taken": round(self.risk_taken, 4)
        }


@dataclass
class EquityCurve:
    """Single equity curve path"""
    path_id: int
    equity_values: List[float]
    final_return: float
    max_drawdown: float
    peak_equity: float
    min_equity: float
    
    def to_dict(self) -> Dict:
        return {
            "path_id": self.path_id,
            "final_return": round(self.final_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "peak_equity": round(self.peak_equity, 2),
            "min_equity": round(self.min_equity, 2),
            "data_points": len(self.equity_values)
        }


@dataclass
class DrawdownDistribution:
    """Drawdown statistics across simulations"""
    p50_drawdown: float      # Median drawdown
    p75_drawdown: float      # 75th percentile
    p90_drawdown: float      # 90th percentile
    p95_drawdown: float      # 95th percentile (VaR)
    p99_drawdown: float      # 99th percentile
    mean_drawdown: float
    max_observed: float
    
    def to_dict(self) -> Dict:
        return {
            "p50_drawdown": round(self.p50_drawdown, 4),
            "p75_drawdown": round(self.p75_drawdown, 4),
            "p90_drawdown": round(self.p90_drawdown, 4),
            "p95_drawdown": round(self.p95_drawdown, 4),
            "p99_drawdown": round(self.p99_drawdown, 4),
            "mean_drawdown": round(self.mean_drawdown, 4),
            "max_observed": round(self.max_observed, 4)
        }


@dataclass
class RiskOfRuinMetrics:
    """Probability of account loss"""
    prob_loss_30pct: float   # P(loss > 30%)
    prob_loss_50pct: float   # P(loss > 50%)
    prob_loss_80pct: float   # P(loss > 80%)
    prob_loss_100pct: float  # P(total wipeout)
    expected_loss_if_ruin: float
    median_time_to_ruin: Optional[int] = None  # In trades
    
    def to_dict(self) -> Dict:
        return {
            "prob_loss_30pct": round(self.prob_loss_30pct, 4),
            "prob_loss_50pct": round(self.prob_loss_50pct, 4),
            "prob_loss_80pct": round(self.prob_loss_80pct, 4),
            "prob_loss_100pct": round(self.prob_loss_100pct, 4),
            "expected_loss_if_ruin": round(self.expected_loss_if_ruin, 4),
            "median_time_to_ruin": self.median_time_to_ruin
        }


@dataclass
class ReturnDistribution:
    """Return statistics across simulations"""
    median_return: float
    mean_return: float
    best_case: float         # 95th percentile
    worst_case: float        # 5th percentile
    p10_return: float
    p25_return: float
    p75_return: float
    p90_return: float
    std_dev: float
    skewness: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "median_return": round(self.median_return, 4),
            "mean_return": round(self.mean_return, 4),
            "best_case": round(self.best_case, 4),
            "worst_case": round(self.worst_case, 4),
            "p10_return": round(self.p10_return, 4),
            "p25_return": round(self.p25_return, 4),
            "p75_return": round(self.p75_return, 4),
            "p90_return": round(self.p90_return, 4),
            "std_dev": round(self.std_dev, 4),
            "skewness": round(self.skewness, 4)
        }


@dataclass
class MonteCarloRun:
    """Monte Carlo simulation run"""
    run_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    
    # Simulation parameters
    iterations: int = 1000
    method: MonteCarloMethod = MonteCarloMethod.COMBINED
    noise_level: float = 0.1  # For noise injection
    
    # Dataset info
    trades_count: int = 0
    dataset_start: Optional[datetime] = None
    dataset_end: Optional[datetime] = None
    
    # Run info
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: MonteCarloStatus = MonteCarloStatus.PENDING
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "iterations": self.iterations,
            "method": self.method.value if isinstance(self.method, Enum) else self.method,
            "noise_level": self.noise_level,
            "trades_count": self.trades_count,
            "dataset_start": self.dataset_start.isoformat() if self.dataset_start else None,
            "dataset_end": self.dataset_end.isoformat() if self.dataset_end else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "error": self.error
        }


@dataclass
class MonteCarloResult:
    """Complete Monte Carlo analysis result"""
    run_id: str
    strategy_id: str
    iterations: int
    
    # Core metrics
    return_distribution: ReturnDistribution
    drawdown_distribution: DrawdownDistribution
    risk_of_ruin: RiskOfRuinMetrics
    
    # Summary metrics
    profit_probability: float      # P(return > 0)
    sharpe_ratio_median: float
    sortino_ratio_median: float
    
    # Confidence intervals
    ci_95_lower: float
    ci_95_upper: float
    ci_99_lower: float
    ci_99_upper: float
    
    # Verdict
    verdict: MonteCarloVerdict = MonteCarloVerdict.RISKY
    verdict_reason: str = ""
    risk_score: float = 0.5  # 0-1, lower is better
    
    # Timestamp
    computed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "strategy_id": self.strategy_id,
            "iterations": self.iterations,
            "return_distribution": self.return_distribution.to_dict(),
            "drawdown_distribution": self.drawdown_distribution.to_dict(),
            "risk_of_ruin": self.risk_of_ruin.to_dict(),
            "profit_probability": round(self.profit_probability, 4),
            "sharpe_ratio_median": round(self.sharpe_ratio_median, 3),
            "sortino_ratio_median": round(self.sortino_ratio_median, 3),
            "ci_95_lower": round(self.ci_95_lower, 4),
            "ci_95_upper": round(self.ci_95_upper, 4),
            "ci_99_lower": round(self.ci_99_lower, 4),
            "ci_99_upper": round(self.ci_99_upper, 4),
            "verdict": self.verdict.value if isinstance(self.verdict, Enum) else self.verdict,
            "verdict_reason": self.verdict_reason,
            "risk_score": round(self.risk_score, 3),
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }


# Verdict thresholds
VERDICT_THRESHOLDS = {
    "ROBUST": {
        "max_risk_score": 0.25,
        "min_profit_prob": 0.6,
        "max_p95_drawdown": 0.20,
        "max_ruin_30pct": 0.05
    },
    "ACCEPTABLE": {
        "max_risk_score": 0.45,
        "min_profit_prob": 0.5,
        "max_p95_drawdown": 0.35,
        "max_ruin_30pct": 0.15
    },
    "RISKY": {
        "max_risk_score": 0.65,
        "min_profit_prob": 0.4,
        "max_p95_drawdown": 0.50,
        "max_ruin_30pct": 0.30
    }
    # Below RISKY = UNTRADABLE
}
