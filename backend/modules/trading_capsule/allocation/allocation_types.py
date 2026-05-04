"""
Allocation Types (S3)
=====================

Type definitions for Capital Allocation Layer.

Includes:
- EligibleStrategy: Strategy that passed selection filters
- StrategyAllocation: Allocation assignment for one strategy
- CapitalAllocationPlan: Complete allocation plan
- AllocationSnapshot: Historical snapshot
- AllocationPolicy: Configuration for allocation rules
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class AllocationStatus(Enum):
    """Allocation plan lifecycle"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    REBALANCING = "REBALANCING"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class SelectionReason(Enum):
    """Reason for strategy selection/rejection"""
    SELECTED = "SELECTED"
    OVERFIT = "REJECTED_OVERFIT"
    UNSTABLE = "REJECTED_UNSTABLE"
    LOW_RANKING = "REJECTED_LOW_RANKING"
    HIGH_DRAWDOWN = "REJECTED_HIGH_DRAWDOWN"
    LOW_TRADES = "REJECTED_LOW_TRADES"
    LOW_SHARPE = "REJECTED_LOW_SHARPE"


# ===========================================
# Allocation Policy
# ===========================================

@dataclass
class AllocationPolicy:
    """
    Configuration for allocation rules.
    """
    policy_id: str = "default"
    name: str = "Default Policy"
    
    # Selection thresholds
    min_ranking_score: float = 0.40
    min_trades_count: int = 20
    max_drawdown_threshold: float = 0.35  # 35%
    min_sharpe_threshold: float = 0.3
    
    # Robustness requirements
    require_robust: bool = False  # Only ROBUST verdict
    allow_weak: bool = True       # Allow WEAK verdict
    allow_overfit: bool = False   # Reject OVERFIT
    allow_unstable: bool = False  # Reject UNSTABLE
    
    # Weight constraints
    max_strategies: int = 5
    max_weight_per_strategy: float = 0.35  # 35%
    min_weight_per_strategy: float = 0.05  # 5%
    
    # Rebalance rules
    rebalance_threshold: float = 0.05  # 5% drift triggers rebalance
    min_rebalance_interval_hours: int = 24
    
    # Allocation score weights
    weight_ranking: float = 0.40
    weight_robustness: float = 0.30
    weight_calmar: float = 0.15
    weight_low_dd: float = 0.15
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "selection": {
                "min_ranking_score": self.min_ranking_score,
                "min_trades_count": self.min_trades_count,
                "max_drawdown_threshold": self.max_drawdown_threshold,
                "min_sharpe_threshold": self.min_sharpe_threshold
            },
            "robustness": {
                "require_robust": self.require_robust,
                "allow_weak": self.allow_weak,
                "allow_overfit": self.allow_overfit,
                "allow_unstable": self.allow_unstable
            },
            "weights": {
                "max_strategies": self.max_strategies,
                "max_weight": self.max_weight_per_strategy,
                "min_weight": self.min_weight_per_strategy
            },
            "rebalance": {
                "threshold": self.rebalance_threshold,
                "min_interval_hours": self.min_rebalance_interval_hours
            },
            "score_weights": {
                "ranking": self.weight_ranking,
                "robustness": self.weight_robustness,
                "calmar": self.weight_calmar,
                "low_dd": self.weight_low_dd
            }
        }


# ===========================================
# Eligible Strategy (S3.1)
# ===========================================

@dataclass
class EligibleStrategy:
    """
    Strategy that passed selection filters.
    
    Output of Strategy Selector.
    """
    strategy_id: str = ""
    experiment_id: str = ""
    
    # Scores
    ranking_score: float = 0.0
    robustness_score: float = 0.0
    composite_score: float = 0.0
    
    # Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    expectancy: float = 0.0
    win_rate: float = 0.0
    
    # Stats
    trades_count: int = 0
    
    # Walk Forward
    robustness_verdict: str = ""  # ROBUST, STABLE, WEAK
    avg_train_sharpe: float = 0.0
    avg_test_sharpe: float = 0.0
    sharpe_degradation: float = 0.0
    
    # Selection
    is_eligible: bool = True
    selection_reason: SelectionReason = SelectionReason.SELECTED
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "experiment_id": self.experiment_id,
            "scores": {
                "ranking_score": round(self.ranking_score, 4),
                "robustness_score": round(self.robustness_score, 4),
                "composite_score": round(self.composite_score, 4)
            },
            "metrics": {
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "calmar_ratio": round(self.calmar_ratio, 4),
                "profit_factor": round(self.profit_factor, 4),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "expectancy": round(self.expectancy, 2),
                "win_rate": round(self.win_rate, 4)
            },
            "trades_count": self.trades_count,
            "walk_forward": {
                "verdict": self.robustness_verdict,
                "avg_train_sharpe": round(self.avg_train_sharpe, 4),
                "avg_test_sharpe": round(self.avg_test_sharpe, 4),
                "sharpe_degradation": round(self.sharpe_degradation, 4)
            },
            "selection": {
                "is_eligible": self.is_eligible,
                "reason": self.selection_reason.value,
                "warnings": self.warnings
            }
        }


# ===========================================
# Strategy Allocation (S3.2)
# ===========================================

@dataclass
class StrategyAllocation:
    """
    Allocation assignment for one strategy.
    """
    strategy_id: str = ""
    
    # Target allocation
    target_weight: float = 0.0          # 0-1 scale
    target_capital_usd: float = 0.0
    
    # Raw score before caps
    allocation_score: float = 0.0
    raw_weight: float = 0.0
    
    # Underlying metrics
    ranking_score: float = 0.0
    robustness_score: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Status
    enabled: bool = True
    capped: bool = False
    cap_reason: str = ""
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "allocation": {
                "target_weight": round(self.target_weight, 4),
                "target_weight_pct": f"{self.target_weight * 100:.1f}%",
                "target_capital_usd": round(self.target_capital_usd, 2)
            },
            "scores": {
                "allocation_score": round(self.allocation_score, 4),
                "raw_weight": round(self.raw_weight, 4),
                "ranking_score": round(self.ranking_score, 4),
                "robustness_score": round(self.robustness_score, 4)
            },
            "metrics": {
                "calmar_ratio": round(self.calmar_ratio, 4),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4)
            },
            "status": {
                "enabled": self.enabled,
                "capped": self.capped,
                "cap_reason": self.cap_reason
            },
            "warnings": self.warnings
        }


# ===========================================
# Capital Allocation Plan (S3.3)
# ===========================================

@dataclass
class CapitalAllocationPlan:
    """
    Complete allocation plan.
    
    Output of Allocation Engine.
    """
    plan_id: str = field(default_factory=lambda: f"alloc_{uuid.uuid4().hex[:8]}")
    
    # Source
    experiment_id: str = ""
    walkforward_experiment_id: str = ""
    
    # Capital
    total_capital_usd: float = 0.0
    allocated_capital_usd: float = 0.0
    cash_reserve_usd: float = 0.0
    
    # Policy
    policy_id: str = "default"
    
    # Allocations
    strategies: List[StrategyAllocation] = field(default_factory=list)
    
    # Selection stats
    total_strategies_evaluated: int = 0
    strategies_selected: int = 0
    strategies_rejected: int = 0
    
    # Status
    status: AllocationStatus = AllocationStatus.DRAFT
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    last_rebalance_at: Optional[datetime] = None
    
    # Metadata
    version: int = 1
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "experiment_id": self.experiment_id,
            "walkforward_experiment_id": self.walkforward_experiment_id,
            "capital": {
                "total_usd": round(self.total_capital_usd, 2),
                "allocated_usd": round(self.allocated_capital_usd, 2),
                "cash_reserve_usd": round(self.cash_reserve_usd, 2)
            },
            "policy_id": self.policy_id,
            "strategies": [s.to_dict() for s in self.strategies],
            "selection_stats": {
                "evaluated": self.total_strategies_evaluated,
                "selected": self.strategies_selected,
                "rejected": self.strategies_rejected
            },
            "status": self.status.value,
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "activated_at": self.activated_at.isoformat() if self.activated_at else None,
                "last_rebalance_at": self.last_rebalance_at.isoformat() if self.last_rebalance_at else None
            },
            "version": self.version,
            "notes": self.notes
        }


# ===========================================
# Allocation Snapshot
# ===========================================

@dataclass
class AllocationSnapshot:
    """
    Historical snapshot of allocation state.
    """
    snapshot_id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:8]}")
    plan_id: str = ""
    
    # Snapshot data
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_capital_usd: float = 0.0
    
    # Strategy allocations at snapshot time
    strategies: List[StrategyAllocation] = field(default_factory=list)
    
    # Snapshot reason
    reason: str = ""  # CREATION, REBALANCE, MANUAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "plan_id": self.plan_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_capital_usd": round(self.total_capital_usd, 2),
            "strategies": [s.to_dict() for s in self.strategies],
            "reason": self.reason
        }


# ===========================================
# Rebalance Preview
# ===========================================

@dataclass
class RebalancePreview:
    """
    Preview of rebalance changes before execution.
    """
    plan_id: str = ""
    current_snapshot_id: str = ""
    
    # Changes
    changes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary
    strategies_added: int = 0
    strategies_removed: int = 0
    weights_adjusted: int = 0
    
    # Recommendation
    should_rebalance: bool = False
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "current_snapshot_id": self.current_snapshot_id,
            "changes": self.changes,
            "summary": {
                "strategies_added": self.strategies_added,
                "strategies_removed": self.strategies_removed,
                "weights_adjusted": self.weights_adjusted
            },
            "recommendation": {
                "should_rebalance": self.should_rebalance,
                "reason": self.reason
            }
        }
