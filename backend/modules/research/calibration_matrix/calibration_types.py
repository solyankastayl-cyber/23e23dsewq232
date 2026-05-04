"""
Calibration Types
=================

Core types for Strategy Calibration Matrix (PHASE 2.1)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class CalibrationStatus(str, Enum):
    """Status of calibration run"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyGrade(str, Enum):
    """Grade based on calibration results"""
    A = "A"      # WR >= 60%, PF >= 2.0
    B = "B"      # WR >= 55%, PF >= 1.5
    C = "C"      # WR >= 50%, PF >= 1.2
    D = "D"      # WR >= 45%, PF >= 1.0
    F = "F"      # Below thresholds


@dataclass
class CalibrationConfig:
    """Configuration for calibration run"""
    strategies: List[str] = field(default_factory=lambda: [
        "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"
    ])
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    timeframes: List[str] = field(default_factory=lambda: ["15m", "1h", "4h", "1d"])
    regimes: List[str] = field(default_factory=lambda: [
        "TRENDING", "RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY", "TRANSITION"
    ])
    
    # Simulation params
    min_sample_size: int = 30
    risk_per_trade_pct: float = 1.0
    initial_capital: float = 10000.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategies": self.strategies,
            "symbols": self.symbols,
            "timeframes": self.timeframes,
            "regimes": self.regimes,
            "minSampleSize": self.min_sample_size,
            "riskPerTradePct": self.risk_per_trade_pct,
            "initialCapital": self.initial_capital
        }


@dataclass
class CalibrationMetrics:
    """Metrics for a single calibration cell"""
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    average_trade: float = 0.0
    sample_size: int = 0
    block_rate: float = 0.0  # % of signals blocked by filters
    
    # Additional metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_r_multiple: float = 0.0
    sharpe_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "winRate": round(self.win_rate, 4),
            "profitFactor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 4),
            "maxDrawdown": round(self.max_drawdown, 4),
            "averageTrade": round(self.average_trade, 4),
            "sampleSize": self.sample_size,
            "blockRate": round(self.block_rate, 4),
            "details": {
                "totalTrades": self.total_trades,
                "winningTrades": self.winning_trades,
                "losingTrades": self.losing_trades,
                "grossProfit": round(self.gross_profit, 2),
                "grossLoss": round(self.gross_loss, 2),
                "largestWin": round(self.largest_win, 2),
                "largestLoss": round(self.largest_loss, 2),
                "avgWin": round(self.avg_win, 4),
                "avgLoss": round(self.avg_loss, 4),
                "avgRMultiple": round(self.avg_r_multiple, 2),
                "sharpeRatio": round(self.sharpe_ratio, 2)
            }
        }
    
    def get_grade(self) -> StrategyGrade:
        """Calculate grade based on metrics"""
        if self.sample_size < 30:
            return StrategyGrade.F
        
        if self.win_rate >= 0.60 and self.profit_factor >= 2.0:
            return StrategyGrade.A
        elif self.win_rate >= 0.55 and self.profit_factor >= 1.5:
            return StrategyGrade.B
        elif self.win_rate >= 0.50 and self.profit_factor >= 1.2:
            return StrategyGrade.C
        elif self.win_rate >= 0.45 and self.profit_factor >= 1.0:
            return StrategyGrade.D
        else:
            return StrategyGrade.F


@dataclass
class CalibrationResult:
    """Result for single strategy x symbol x timeframe x regime combination"""
    strategy: str = ""
    symbol: str = ""
    timeframe: str = ""
    regime: str = ""
    metrics: CalibrationMetrics = field(default_factory=CalibrationMetrics)
    grade: StrategyGrade = StrategyGrade.F
    is_valid: bool = False  # Has enough sample size
    notes: List[str] = field(default_factory=list)
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "metrics": self.metrics.to_dict(),
            "grade": self.grade.value,
            "isValid": self.is_valid,
            "notes": self.notes,
            "computedAt": self.computed_at
        }


@dataclass
class CalibrationMatrix:
    """Complete calibration matrix"""
    results: List[CalibrationResult] = field(default_factory=list)
    config: CalibrationConfig = field(default_factory=CalibrationConfig)
    
    # Aggregated stats
    total_combinations: int = 0
    valid_combinations: int = 0
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Best/worst performers
    best_performers: List[Dict[str, Any]] = field(default_factory=list)
    worst_performers: List[Dict[str, Any]] = field(default_factory=list)
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "config": self.config.to_dict(),
            "summary": {
                "totalCombinations": self.total_combinations,
                "validCombinations": self.valid_combinations,
                "gradeDistribution": self.grade_distribution,
                "bestPerformers": self.best_performers[:5],
                "worstPerformers": self.worst_performers[:5]
            },
            "computedAt": self.computed_at
        }


@dataclass
class CalibrationRun:
    """Calibration run record"""
    run_id: str = ""
    status: CalibrationStatus = CalibrationStatus.PENDING
    config: CalibrationConfig = field(default_factory=CalibrationConfig)
    matrix: Optional[CalibrationMatrix] = None
    
    started_at: int = 0
    completed_at: int = 0
    duration_ms: int = 0
    
    error: Optional[str] = None
    progress: float = 0.0  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "matrix": self.matrix.to_dict() if self.matrix else None,
            "timing": {
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
                "durationMs": self.duration_ms
            },
            "error": self.error,
            "progress": round(self.progress, 1)
        }
