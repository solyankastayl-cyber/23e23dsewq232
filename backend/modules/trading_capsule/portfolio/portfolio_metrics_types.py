"""
Portfolio Metrics Types (S4.3)
==============================

Type definitions for Portfolio Metrics and Correlation Analysis.

Includes:
- PortfolioMetrics: Aggregated portfolio metrics
- StrategyMetrics: Per-strategy metrics
- CorrelationMatrix: Strategy correlation data
- EquityCurvePoint: Equity curve data point
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math


# ===========================================
# EquityCurvePoint (S4.3.1)
# ===========================================

@dataclass
class EquityCurvePoint:
    """Single point in equity curve"""
    timestamp: datetime
    equity_usd: float
    cash_usd: float
    pnl_usd: float
    pnl_pct: float
    drawdown_usd: float
    drawdown_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "equity_usd": round(self.equity_usd, 2),
            "cash_usd": round(self.cash_usd, 2),
            "pnl_usd": round(self.pnl_usd, 2),
            "pnl_pct": round(self.pnl_pct, 4),
            "drawdown_usd": round(self.drawdown_usd, 2),
            "drawdown_pct": round(self.drawdown_pct, 4)
        }


# ===========================================
# StrategyMetrics (S4.3.2)
# ===========================================

@dataclass
class StrategyMetrics:
    """Metrics for a single strategy in portfolio"""
    strategy_id: str = ""
    slot_id: str = ""
    
    # Returns
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    
    # Risk
    volatility: float = 0.0              # Annualized volatility
    max_drawdown_pct: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL
    total_pnl_usd: float = 0.0
    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Allocation
    current_weight: float = 0.0
    target_weight: float = 0.0
    
    # Daily returns for correlation
    daily_returns: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "slot_id": self.slot_id,
            "returns": {
                "total_return_pct": round(self.total_return_pct, 4),
                "annualized_return_pct": round(self.annualized_return_pct, 4)
            },
            "risk": {
                "volatility": round(self.volatility, 4),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4)
            },
            "risk_adjusted": {
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "calmar_ratio": round(self.calmar_ratio, 4)
            },
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "win_rate": round(self.win_rate, 4)
            },
            "pnl": {
                "total_usd": round(self.total_pnl_usd, 2),
                "avg_win_usd": round(self.avg_win_usd, 2),
                "avg_loss_usd": round(self.avg_loss_usd, 2),
                "profit_factor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 2)
            },
            "allocation": {
                "current_weight": round(self.current_weight, 4),
                "target_weight": round(self.target_weight, 4)
            }
        }


# ===========================================
# CorrelationMatrix (S4.3.3)
# ===========================================

@dataclass
class CorrelationMatrix:
    """Correlation matrix between strategies"""
    simulation_id: str = ""
    
    # Strategy IDs (row/column labels)
    strategy_ids: List[str] = field(default_factory=list)
    
    # Correlation values: Dict[strategy_pair] = correlation
    # Key format: "strat_a:strat_b"
    correlations: Dict[str, float] = field(default_factory=dict)
    
    # Statistics
    avg_correlation: float = 0.0
    max_correlation: float = 0.0
    min_correlation: float = 0.0
    
    # Timestamp
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_correlation(self, strat_a: str, strat_b: str) -> float:
        """Get correlation between two strategies"""
        if strat_a == strat_b:
            return 1.0
        
        key1 = f"{strat_a}:{strat_b}"
        key2 = f"{strat_b}:{strat_a}"
        
        return self.correlations.get(key1, self.correlations.get(key2, 0.0))
    
    def to_matrix(self) -> List[List[float]]:
        """Convert to 2D matrix format"""
        n = len(self.strategy_ids)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i, strat_a in enumerate(self.strategy_ids):
            for j, strat_b in enumerate(self.strategy_ids):
                matrix[i][j] = self.get_correlation(strat_a, strat_b)
        
        return matrix
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "strategy_ids": self.strategy_ids,
            "matrix": self.to_matrix(),
            "correlations": {k: round(v, 4) for k, v in self.correlations.items()},
            "stats": {
                "avg_correlation": round(self.avg_correlation, 4),
                "max_correlation": round(self.max_correlation, 4),
                "min_correlation": round(self.min_correlation, 4)
            },
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


# ===========================================
# PortfolioMetrics (S4.3.4)
# ===========================================

@dataclass
class PortfolioMetrics:
    """Aggregated portfolio-level metrics"""
    simulation_id: str = ""
    
    # Capital
    initial_capital_usd: float = 0.0
    final_equity_usd: float = 0.0
    
    # Returns
    total_return_usd: float = 0.0
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    
    # Risk
    volatility: float = 0.0
    max_drawdown_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade aggregates
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL aggregates
    gross_profit_usd: float = 0.0
    gross_loss_usd: float = 0.0
    profit_factor: float = 0.0
    expectancy_usd: float = 0.0
    
    # Diversification
    num_strategies: int = 0
    effective_num_strategies: float = 0.0  # Based on weights
    diversification_ratio: float = 0.0
    
    # Correlation stats
    avg_strategy_correlation: float = 0.0
    
    # Time
    simulation_days: int = 0
    
    # Timestamp
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "capital": {
                "initial_usd": round(self.initial_capital_usd, 2),
                "final_usd": round(self.final_equity_usd, 2)
            },
            "returns": {
                "total_usd": round(self.total_return_usd, 2),
                "total_pct": round(self.total_return_pct, 4),
                "annualized_pct": round(self.annualized_return_pct, 4)
            },
            "risk": {
                "volatility": round(self.volatility, 4),
                "max_drawdown_usd": round(self.max_drawdown_usd, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "avg_drawdown_pct": round(self.avg_drawdown_pct, 4)
            },
            "risk_adjusted": {
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "calmar_ratio": round(self.calmar_ratio, 4)
            },
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "win_rate": round(self.win_rate, 4)
            },
            "pnl": {
                "gross_profit_usd": round(self.gross_profit_usd, 2),
                "gross_loss_usd": round(self.gross_loss_usd, 2),
                "profit_factor": round(self.profit_factor, 2),
                "expectancy_usd": round(self.expectancy_usd, 2)
            },
            "diversification": {
                "num_strategies": self.num_strategies,
                "effective_num_strategies": round(self.effective_num_strategies, 2),
                "diversification_ratio": round(self.diversification_ratio, 4),
                "avg_correlation": round(self.avg_strategy_correlation, 4)
            },
            "simulation_days": self.simulation_days,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


# ===========================================
# Risk Contribution
# ===========================================

@dataclass
class RiskContribution:
    """Risk contribution per strategy"""
    strategy_id: str = ""
    slot_id: str = ""
    
    weight: float = 0.0
    volatility: float = 0.0
    
    marginal_contribution: float = 0.0
    component_contribution: float = 0.0
    pct_contribution: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "slot_id": self.slot_id,
            "weight": round(self.weight, 4),
            "volatility": round(self.volatility, 4),
            "marginal_contribution": round(self.marginal_contribution, 4),
            "component_contribution": round(self.component_contribution, 4),
            "pct_contribution": round(self.pct_contribution, 4)
        }
