"""
Capital Types
=============

Core types for PHASE 3.4 Capital Optimization Engine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class AllocationStatus(str, Enum):
    """Strategy allocation status"""
    ACTIVE = "ACTIVE"           # Full allocation allowed
    REDUCED = "REDUCED"         # Reduced due to underperformance
    SUSPENDED = "SUSPENDED"     # Temporarily suspended
    LOCKED = "LOCKED"           # Locked at current level


class PerformanceGrade(str, Enum):
    """Strategy performance grade"""
    EXCELLENT = "EXCELLENT"     # Top performer
    GOOD = "GOOD"               # Above average
    AVERAGE = "AVERAGE"         # Meeting expectations
    BELOW = "BELOW"             # Below expectations
    POOR = "POOR"               # Significant underperformance


class RebalanceAction(str, Enum):
    """Rebalance action type"""
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    MAINTAIN = "MAINTAIN"
    SUSPEND = "SUSPEND"


# ===========================================
# Strategy Performance
# ===========================================

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Core metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Return metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    # Ratios
    win_rate: float = 0.0          # % of winning trades
    profit_factor: float = 0.0     # Gross profit / Gross loss
    expectancy: float = 0.0        # Expected $ per trade
    
    # Risk metrics
    max_drawdown: float = 0.0      # Maximum drawdown %
    avg_win: float = 0.0           # Average winning trade
    avg_loss: float = 0.0          # Average losing trade
    risk_reward: float = 0.0       # Avg win / Avg loss
    
    # Consistency
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    consistency_score: float = 0.0  # 0-100
    
    # Performance grade
    grade: PerformanceGrade = PerformanceGrade.AVERAGE
    
    # Time metrics
    avg_trade_duration: float = 0.0  # Hours
    last_trade_at: int = 0
    evaluation_period_days: int = 30
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades
            },
            "returns": {
                "totalPnl": round(self.total_pnl, 2),
                "grossProfit": round(self.gross_profit, 2),
                "grossLoss": round(self.gross_loss, 2)
            },
            "ratios": {
                "winRate": round(self.win_rate, 1),
                "profitFactor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 2),
                "riskReward": round(self.risk_reward, 2)
            },
            "risk": {
                "maxDrawdown": round(self.max_drawdown, 2),
                "avgWin": round(self.avg_win, 2),
                "avgLoss": round(self.avg_loss, 2)
            },
            "consistency": {
                "sharpeRatio": round(self.sharpe_ratio, 2),
                "sortinoRatio": round(self.sortino_ratio, 2),
                "consistencyScore": round(self.consistency_score, 1)
            },
            "grade": self.grade.value,
            "time": {
                "avgDuration": round(self.avg_trade_duration, 1),
                "lastTradeAt": self.last_trade_at,
                "evaluationDays": self.evaluation_period_days
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Strategy Allocation
# ===========================================

@dataclass
class StrategyAllocation:
    """Capital allocation for a strategy"""
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Allocation
    base_allocation_pct: float = 0.0     # Original allocation %
    current_allocation_pct: float = 0.0  # Current after adjustments
    min_allocation_pct: float = 0.0      # Minimum allowed
    max_allocation_pct: float = 0.0      # Maximum allowed
    
    # Status
    status: AllocationStatus = AllocationStatus.ACTIVE
    
    # Adjustment factors
    performance_adjustment: float = 1.0   # Based on performance
    regime_adjustment: float = 1.0        # Based on market regime
    risk_adjustment: float = 1.0          # Based on risk metrics
    
    # Capital
    allocated_capital: float = 0.0        # Actual $ allocated
    utilized_capital: float = 0.0         # Currently in positions
    available_capital: float = 0.0        # Available for new trades
    
    # Performance link
    performance: Optional[StrategyPerformance] = None
    
    # History
    last_adjustment_at: int = 0
    adjustment_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "allocation": {
                "base": round(self.base_allocation_pct, 1),
                "current": round(self.current_allocation_pct, 1),
                "min": round(self.min_allocation_pct, 1),
                "max": round(self.max_allocation_pct, 1)
            },
            "status": self.status.value,
            "adjustments": {
                "performance": round(self.performance_adjustment, 2),
                "regime": round(self.regime_adjustment, 2),
                "risk": round(self.risk_adjustment, 2),
                "combined": round(self.performance_adjustment * self.regime_adjustment * self.risk_adjustment, 2)
            },
            "capital": {
                "allocated": round(self.allocated_capital, 2),
                "utilized": round(self.utilized_capital, 2),
                "available": round(self.available_capital, 2)
            },
            "performance": self.performance.to_dict() if self.performance else None,
            "lastAdjustment": {
                "at": self.last_adjustment_at,
                "reason": self.adjustment_reason
            }
        }


# ===========================================
# Capital Efficiency
# ===========================================

@dataclass
class CapitalEfficiency:
    """Capital efficiency metrics for a strategy"""
    strategy_id: str = ""
    
    # Core efficiency
    return_on_capital: float = 0.0       # Return / Capital used
    return_per_risk_unit: float = 0.0    # Return / Risk taken
    capital_utilization: float = 0.0     # % of allocated capital used
    
    # Efficiency ratios
    efficiency_score: float = 0.0        # 0-100 overall efficiency
    capital_turnover: float = 0.0        # How often capital is reused
    
    # Opportunity metrics
    missed_opportunities: int = 0        # Trades skipped due to capital
    capital_locked_pct: float = 0.0      # % in losing positions
    
    # Comparison
    vs_benchmark: float = 0.0            # Performance vs benchmark
    vs_average: float = 0.0              # Vs portfolio average
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "efficiency": {
                "returnOnCapital": round(self.return_on_capital, 2),
                "returnPerRiskUnit": round(self.return_per_risk_unit, 2),
                "capitalUtilization": round(self.capital_utilization, 1),
                "efficiencyScore": round(self.efficiency_score, 1),
                "capitalTurnover": round(self.capital_turnover, 2)
            },
            "opportunities": {
                "missed": self.missed_opportunities,
                "capitalLocked": round(self.capital_locked_pct, 1)
            },
            "comparison": {
                "vsBenchmark": round(self.vs_benchmark, 2),
                "vsAverage": round(self.vs_average, 2)
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Portfolio Capital State
# ===========================================

@dataclass
class PortfolioCapital:
    """Overall portfolio capital state"""
    # Total capital
    total_capital: float = 0.0
    allocated_capital: float = 0.0
    utilized_capital: float = 0.0
    available_capital: float = 0.0
    reserved_capital: float = 0.0        # Emergency reserve
    
    # Metrics
    utilization_pct: float = 0.0
    at_risk_pct: float = 0.0
    
    # Strategy breakdown
    strategy_allocations: Dict[str, float] = field(default_factory=dict)
    strategy_utilizations: Dict[str, float] = field(default_factory=dict)
    
    # Performance
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    portfolio_return_pct: float = 0.0
    
    # Risk
    portfolio_drawdown: float = 0.0
    max_drawdown: float = 0.0
    
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "capital": {
                "total": round(self.total_capital, 2),
                "allocated": round(self.allocated_capital, 2),
                "utilized": round(self.utilized_capital, 2),
                "available": round(self.available_capital, 2),
                "reserved": round(self.reserved_capital, 2)
            },
            "metrics": {
                "utilizationPct": round(self.utilization_pct, 1),
                "atRiskPct": round(self.at_risk_pct, 1)
            },
            "strategies": {
                "allocations": {k: round(v, 1) for k, v in self.strategy_allocations.items()},
                "utilizations": {k: round(v, 2) for k, v in self.strategy_utilizations.items()}
            },
            "performance": {
                "totalPnl": round(self.total_pnl, 2),
                "dailyPnl": round(self.daily_pnl, 2),
                "returnPct": round(self.portfolio_return_pct, 2)
            },
            "risk": {
                "currentDrawdown": round(self.portfolio_drawdown, 2),
                "maxDrawdown": round(self.max_drawdown, 2)
            },
            "updatedAt": self.updated_at
        }


# ===========================================
# Rebalance Recommendation
# ===========================================

@dataclass
class RebalanceRecommendation:
    """Recommendation for rebalancing"""
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Current vs Target
    current_allocation_pct: float = 0.0
    target_allocation_pct: float = 0.0
    change_pct: float = 0.0
    
    # Action
    action: RebalanceAction = RebalanceAction.MAINTAIN
    priority: int = 0  # 1-5, 1 being highest
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    performance_grade: PerformanceGrade = PerformanceGrade.AVERAGE
    
    # Impact
    capital_change: float = 0.0
    expected_improvement: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "allocation": {
                "current": round(self.current_allocation_pct, 1),
                "target": round(self.target_allocation_pct, 1),
                "change": round(self.change_pct, 1)
            },
            "action": self.action.value,
            "priority": self.priority,
            "reasons": self.reasons,
            "performanceGrade": self.performance_grade.value,
            "impact": {
                "capitalChange": round(self.capital_change, 2),
                "expectedImprovement": round(self.expected_improvement, 2)
            }
        }


# ===========================================
# Rebalance Plan
# ===========================================

@dataclass
class RebalancePlan:
    """Complete rebalancing plan"""
    recommendations: List[RebalanceRecommendation] = field(default_factory=list)
    
    # Summary
    total_reallocation: float = 0.0
    strategies_to_increase: int = 0
    strategies_to_decrease: int = 0
    strategies_to_suspend: int = 0
    
    # Expected outcome
    expected_efficiency_gain: float = 0.0
    expected_risk_reduction: float = 0.0
    
    # Timing
    recommended_execution: str = "GRADUAL"  # IMMEDIATE, GRADUAL, SCHEDULED
    execution_steps: int = 1
    
    created_at: int = 0
    valid_until: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "summary": {
                "totalReallocation": round(self.total_reallocation, 1),
                "increase": self.strategies_to_increase,
                "decrease": self.strategies_to_decrease,
                "suspend": self.strategies_to_suspend
            },
            "expectedOutcome": {
                "efficiencyGain": round(self.expected_efficiency_gain, 2),
                "riskReduction": round(self.expected_risk_reduction, 2)
            },
            "execution": {
                "recommended": self.recommended_execution,
                "steps": self.execution_steps
            },
            "timing": {
                "createdAt": self.created_at,
                "validUntil": self.valid_until
            }
        }
