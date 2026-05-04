"""
Report Types (S2.5)
===================

Data models for Research Reports.

Key entities:
- ResearchReport: Complete experiment report
- LeaderboardEntry: Strategy ranking entry for report
- WalkForwardAnalysis: Walk-forward stability analysis
- StrategyDiagnostics: Per-strategy metrics and warnings
- AllocationReadiness: S2 -> S3 transition readiness
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class WarningLevel(Enum):
    """Warning severity level"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RobustnessVerdict(Enum):
    """Walk-forward robustness verdict"""
    ROBUST = "ROBUST"
    STABLE = "STABLE"
    WEAK = "WEAK"
    OVERFIT = "OVERFIT"
    UNSTABLE = "UNSTABLE"
    UNKNOWN = "UNKNOWN"


# ===========================================
# Report Warning
# ===========================================

@dataclass
class ReportWarning:
    """Warning entry in report"""
    code: str = ""
    level: WarningLevel = WarningLevel.INFO
    strategy_id: str = ""
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "level": self.level.value,
            "strategy_id": self.strategy_id,
            "message": self.message
        }


# ===========================================
# Leaderboard Entry (for report)
# ===========================================

@dataclass
class LeaderboardEntry:
    """Leaderboard entry for report display"""
    rank: int = 0
    strategy_id: str = ""
    
    # Key metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    trades_count: int = 0
    
    # Composite score
    composite_score: float = 0.0
    
    # Is winner
    is_winner: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "strategy_id": self.strategy_id,
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "profit_factor": round(self.profit_factor, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "win_rate": round(self.win_rate, 4),
            "trades_count": self.trades_count,
            "composite_score": round(self.composite_score, 4),
            "is_winner": self.is_winner
        }


# ===========================================
# Walk-Forward Analysis
# ===========================================

@dataclass
class WalkForwardAnalysis:
    """Walk-forward stability analysis for a strategy"""
    strategy_id: str = ""
    
    # Verdict
    verdict: RobustnessVerdict = RobustnessVerdict.UNKNOWN
    
    # Scores
    robustness_score: float = 0.0
    stability_score: float = 0.0
    degradation_score: float = 0.0
    
    # Train vs Test
    avg_train_sharpe: float = 0.0
    avg_test_sharpe: float = 0.0
    sharpe_degradation_pct: float = 0.0
    
    # Windows info
    windows_analyzed: int = 0
    valid_windows: int = 0
    
    # Verdict reasons
    verdict_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "verdict": self.verdict.value,
            "scores": {
                "robustness": round(self.robustness_score, 4),
                "stability": round(self.stability_score, 4),
                "degradation": round(self.degradation_score, 4)
            },
            "train_vs_test": {
                "avg_train_sharpe": round(self.avg_train_sharpe, 4),
                "avg_test_sharpe": round(self.avg_test_sharpe, 4),
                "sharpe_degradation_pct": round(self.sharpe_degradation_pct, 2)
            },
            "windows": {
                "analyzed": self.windows_analyzed,
                "valid": self.valid_windows
            },
            "verdict_reasons": self.verdict_reasons
        }


# ===========================================
# Strategy Diagnostics
# ===========================================

@dataclass
class StrategyDiagnostics:
    """Detailed diagnostics for a strategy"""
    strategy_id: str = ""
    
    # Performance metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Risk metrics
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0
    volatility_annual: float = 0.0
    
    # Trade stats
    trades_count: int = 0
    win_rate: float = 0.0
    
    # Return stats
    total_return_pct: float = 0.0
    annual_return_pct: float = 0.0
    
    # Warnings for this strategy
    warnings: List[str] = field(default_factory=list)
    
    # Quality flags
    has_valid_metrics: bool = True
    has_sufficient_trades: bool = True
    has_acceptable_drawdown: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "performance": {
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "profit_factor": round(self.profit_factor, 4),
                "expectancy": round(self.expectancy, 2)
            },
            "risk": {
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "calmar_ratio": round(self.calmar_ratio, 4),
                "recovery_factor": round(self.recovery_factor, 4),
                "volatility_annual": round(self.volatility_annual, 4)
            },
            "trade_stats": {
                "trades_count": self.trades_count,
                "win_rate": round(self.win_rate, 4)
            },
            "returns": {
                "total_return_pct": round(self.total_return_pct, 4),
                "annual_return_pct": round(self.annual_return_pct, 4)
            },
            "warnings": self.warnings,
            "quality_flags": {
                "has_valid_metrics": self.has_valid_metrics,
                "has_sufficient_trades": self.has_sufficient_trades,
                "has_acceptable_drawdown": self.has_acceptable_drawdown
            }
        }


# ===========================================
# Allocation Readiness (S2 -> S3 Bridge)
# ===========================================

@dataclass
class AllocationReadiness:
    """
    Allocation readiness assessment for a strategy.
    
    This is the bridge between Research (S2) and Allocation (S3).
    """
    strategy_id: str = ""
    
    # Overall eligibility
    eligible_for_allocation: bool = False
    
    # Recommended weight (0-1)
    recommended_weight: float = 0.0
    
    # Scores that contribute to allocation decision
    ranking_score: float = 0.0
    robustness_score: float = 0.0
    combined_score: float = 0.0
    
    # Rejection reason (if not eligible)
    rejection_reason: str = ""
    
    # Factors affecting eligibility
    passes_ranking_threshold: bool = False
    passes_robustness_check: bool = False
    passes_risk_check: bool = False
    passes_sample_size_check: bool = False
    
    # Allocation recommendations
    max_recommended_weight: float = 0.35
    risk_adjustment_factor: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "eligible_for_allocation": self.eligible_for_allocation,
            "recommended_weight": round(self.recommended_weight, 4),
            "scores": {
                "ranking": round(self.ranking_score, 4),
                "robustness": round(self.robustness_score, 4),
                "combined": round(self.combined_score, 4)
            },
            "rejection_reason": self.rejection_reason,
            "eligibility_checks": {
                "passes_ranking": self.passes_ranking_threshold,
                "passes_robustness": self.passes_robustness_check,
                "passes_risk": self.passes_risk_check,
                "passes_sample_size": self.passes_sample_size_check
            },
            "allocation_params": {
                "max_recommended_weight": round(self.max_recommended_weight, 4),
                "risk_adjustment_factor": round(self.risk_adjustment_factor, 4)
            }
        }


# ===========================================
# Main Research Report
# ===========================================

@dataclass
class ResearchReport:
    """
    Complete research report for an experiment.
    
    Includes:
    - Experiment summary
    - Leaderboard
    - Walk-forward analysis
    - Strategy diagnostics
    - Warnings
    - Allocation readiness
    """
    report_id: str = field(default_factory=lambda: f"report_{uuid.uuid4().hex[:8]}")
    
    # Source experiment
    experiment_id: str = ""
    walkforward_experiment_id: str = ""
    
    # Experiment Summary
    experiment_name: str = ""
    asset: str = ""
    timeframe: str = ""
    start_date: str = ""
    end_date: str = ""
    initial_capital_usd: float = 0.0
    strategies_tested: int = 0
    
    # Winner
    winner_strategy_id: str = ""
    winner_score: float = 0.0
    
    # Leaderboard
    leaderboard: List[LeaderboardEntry] = field(default_factory=list)
    
    # Walk-Forward Analysis
    walkforward_analyses: List[WalkForwardAnalysis] = field(default_factory=list)
    has_walkforward_data: bool = False
    
    # Strategy Diagnostics
    strategy_diagnostics: List[StrategyDiagnostics] = field(default_factory=list)
    
    # Warnings
    warnings: List[ReportWarning] = field(default_factory=list)
    
    # Allocation Readiness
    allocation_candidates: List[AllocationReadiness] = field(default_factory=list)
    total_eligible_for_allocation: int = 0
    
    # Report metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    report_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "experiment_id": self.experiment_id,
            "walkforward_experiment_id": self.walkforward_experiment_id,
            
            "experiment_summary": {
                "name": self.experiment_name,
                "asset": self.asset,
                "timeframe": self.timeframe,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "initial_capital_usd": self.initial_capital_usd,
                "strategies_tested": self.strategies_tested
            },
            
            "winner": {
                "strategy_id": self.winner_strategy_id,
                "score": round(self.winner_score, 4)
            },
            
            "leaderboard": [e.to_dict() for e in self.leaderboard],
            
            "walk_forward_analysis": {
                "has_data": self.has_walkforward_data,
                "strategies": [a.to_dict() for a in self.walkforward_analyses]
            },
            
            "strategy_diagnostics": [d.to_dict() for d in self.strategy_diagnostics],
            
            "warnings": [w.to_dict() for w in self.warnings],
            
            "allocation_readiness": {
                "total_eligible": self.total_eligible_for_allocation,
                "candidates": [c.to_dict() for c in self.allocation_candidates]
            },
            
            "metadata": {
                "generated_at": self.generated_at.isoformat() if self.generated_at else None,
                "report_version": self.report_version
            }
        }
