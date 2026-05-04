"""
Strategy Selection Types (STG5)
===============================

Type definitions for Strategy Comparison and Selection.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


# ===========================================
# Score Components
# ===========================================

@dataclass
class ScoreBreakdown:
    """Breakdown of component scores"""
    performance: float = 0.0      # From win rate, PF, expectancy
    stability: float = 0.0        # From drawdown, streaks, variance
    regime_fit: float = 0.0       # Regime compatibility
    profile_fit: float = 0.0      # Profile compatibility
    diagnostics: float = 0.0      # From block rate, veto rate
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "performance": round(self.performance, 4),
            "stability": round(self.stability, 4),
            "regimeFit": round(self.regime_fit, 4),
            "profileFit": round(self.profile_fit, 4),
            "diagnostics": round(self.diagnostics, 4)
        }


@dataclass
class Penalties:
    """Penalties applied to strategy score"""
    high_drawdown: float = 0.0
    high_block_rate: float = 0.0
    degradation: float = 0.0
    wrong_regime: float = 0.0
    instability: float = 0.0
    
    @property
    def total(self) -> float:
        return (
            self.high_drawdown +
            self.high_block_rate +
            self.degradation +
            self.wrong_regime +
            self.instability
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "highDrawdown": round(self.high_drawdown, 4),
            "highBlockRate": round(self.high_block_rate, 4),
            "degradation": round(self.degradation, 4),
            "wrongRegime": round(self.wrong_regime, 4),
            "instability": round(self.instability, 4),
            "total": round(self.total, 4)
        }


# ===========================================
# Selection Score
# ===========================================

@dataclass
class StrategySelectionScore:
    """Complete selection score for a strategy"""
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Total score (0-1)
    total_score: float = 0.0
    
    # Component scores (0-1 each)
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    
    # Penalties applied
    penalties: Penalties = field(default_factory=Penalties)
    
    # Raw score before penalties
    raw_score: float = 0.0
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Strengths and weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "totalScore": round(self.total_score, 4),
            "rawScore": round(self.raw_score, 4),
            "breakdown": self.breakdown.to_dict(),
            "penalties": self.penalties.to_dict(),
            "warnings": self.warnings,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses
        }


# ===========================================
# Ranking Entry
# ===========================================

@dataclass
class StrategyRankingEntry:
    """Entry in strategy ranking"""
    rank: int = 0
    strategy_id: str = ""
    strategy_name: str = ""
    
    total_score: float = 0.0
    
    recommended: bool = False
    
    reason_summary: List[str] = field(default_factory=list)
    
    # Key metrics for quick comparison
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "totalScore": round(self.total_score, 4),
            "recommended": self.recommended,
            "reasonSummary": self.reason_summary,
            "keyMetrics": {
                "winRate": round(self.win_rate, 4),
                "profitFactor": round(self.profit_factor, 2),
                "maxDrawdown": round(self.max_drawdown, 4)
            }
        }


# ===========================================
# Selection Result
# ===========================================

@dataclass
class StrategySelectionResult:
    """Result of strategy selection"""
    selection_id: str = field(default_factory=lambda: f"sel_{uuid.uuid4().hex[:8]}")
    
    # Context
    symbol: Optional[str] = None
    regime: Optional[str] = None
    profile_id: Optional[str] = None
    
    # Winner
    best_strategy_id: str = ""
    best_strategy_name: str = ""
    best_strategy_score: float = 0.0
    
    # Full ranking
    ranking: List[StrategyRankingEntry] = field(default_factory=list)
    
    # Metadata
    strategies_evaluated: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selectionId": self.selection_id,
            "context": {
                "symbol": self.symbol,
                "regime": self.regime,
                "profileId": self.profile_id
            },
            "bestStrategy": {
                "strategyId": self.best_strategy_id,
                "strategyName": self.best_strategy_name,
                "score": round(self.best_strategy_score, 4)
            },
            "ranking": [r.to_dict() for r in self.ranking],
            "strategiesEvaluated": self.strategies_evaluated,
            "generatedAt": self.generated_at.isoformat() if self.generated_at else None
        }


# ===========================================
# Comparison Entry
# ===========================================

@dataclass
class StrategyComparisonEntry:
    """Entry for side-by-side comparison"""
    strategy_id: str = ""
    strategy_name: str = ""
    strategy_type: str = ""
    
    # Scores (0-1)
    performance_score: float = 0.0
    stability_score: float = 0.0
    regime_fit_score: float = 0.0
    profile_fit_score: float = 0.0
    diagnostics_score: float = 0.0
    total_score: float = 0.0
    
    # Raw stats
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    
    # Compatibility
    compatible_regimes: List[str] = field(default_factory=list)
    compatible_profiles: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "strategyType": self.strategy_type,
            "scores": {
                "performance": round(self.performance_score, 4),
                "stability": round(self.stability_score, 4),
                "regimeFit": round(self.regime_fit_score, 4),
                "profileFit": round(self.profile_fit_score, 4),
                "diagnostics": round(self.diagnostics_score, 4),
                "total": round(self.total_score, 4)
            },
            "stats": {
                "totalTrades": self.total_trades,
                "winRate": round(self.win_rate, 4),
                "profitFactor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 4),
                "maxDrawdown": round(self.max_drawdown, 4)
            },
            "compatibility": {
                "regimes": self.compatible_regimes,
                "profiles": self.compatible_profiles
            }
        }


# ===========================================
# Selection Config
# ===========================================

@dataclass
class SelectionConfig:
    """Configuration for selection algorithm"""
    # Score weights (must sum to 1.0)
    performance_weight: float = 0.30
    stability_weight: float = 0.25
    regime_fit_weight: float = 0.20
    profile_fit_weight: float = 0.15
    diagnostics_weight: float = 0.10
    
    # Penalty thresholds
    max_drawdown_threshold: float = 0.15  # 15%
    max_block_rate_threshold: float = 0.50  # 50%
    degradation_threshold: float = 0.20  # 20% worse than average
    
    # Penalty amounts
    drawdown_penalty: float = 0.15
    block_rate_penalty: float = 0.10
    degradation_penalty: float = 0.10
    wrong_regime_penalty: float = 0.20
    instability_penalty: float = 0.05
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "weights": {
                "performance": self.performance_weight,
                "stability": self.stability_weight,
                "regimeFit": self.regime_fit_weight,
                "profileFit": self.profile_fit_weight,
                "diagnostics": self.diagnostics_weight
            },
            "thresholds": {
                "maxDrawdown": self.max_drawdown_threshold,
                "maxBlockRate": self.max_block_rate_threshold,
                "degradation": self.degradation_threshold
            },
            "penalties": {
                "drawdown": self.drawdown_penalty,
                "blockRate": self.block_rate_penalty,
                "degradation": self.degradation_penalty,
                "wrongRegime": self.wrong_regime_penalty,
                "instability": self.instability_penalty
            }
        }
