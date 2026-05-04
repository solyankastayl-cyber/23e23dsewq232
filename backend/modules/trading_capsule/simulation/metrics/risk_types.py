"""
Risk Metrics Types (S1.4C)
==========================

Type definitions for risk metrics.

Includes:
- RiskMetrics: Max Drawdown, Avg Drawdown, Calmar, Recovery Factor
- DrawdownInfo: Detailed drawdown information
- RiskMetricsSnapshot: Combined risk metrics for a run
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


# ===========================================
# Drawdown Information
# ===========================================

@dataclass
class DrawdownInfo:
    """
    Detailed information about a drawdown period.
    """
    start_timestamp: str = ""
    end_timestamp: str = ""
    
    peak_equity: float = 0.0
    trough_equity: float = 0.0
    
    drawdown_pct: float = 0.0
    drawdown_value: float = 0.0
    
    duration_bars: int = 0
    recovery_bars: int = 0
    
    is_recovered: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "peak_equity": round(self.peak_equity, 2),
            "trough_equity": round(self.trough_equity, 2),
            "drawdown_pct": round(self.drawdown_pct * 100, 4),
            "drawdown_value": round(self.drawdown_value, 2),
            "duration_bars": self.duration_bars,
            "recovery_bars": self.recovery_bars,
            "is_recovered": self.is_recovered
        }


# ===========================================
# Risk Metrics
# ===========================================

@dataclass
class RiskMetrics:
    """
    Risk metrics for simulation run.
    
    Calculated from equity curve.
    """
    run_id: str = ""
    
    # Drawdown Metrics
    max_drawdown_pct: float = 0.0        # Maximum drawdown percentage
    max_drawdown_value: float = 0.0      # Maximum drawdown in USD
    avg_drawdown_pct: float = 0.0        # Average drawdown percentage
    
    # Duration Metrics  
    max_drawdown_duration_bars: int = 0  # Longest drawdown in bars
    avg_drawdown_duration_bars: float = 0.0
    
    # Recovery Metrics
    recovery_factor: float = 0.0         # Net profit / Max drawdown
    
    # Ratio Metrics
    calmar_ratio: float = 0.0            # Annual return / Max drawdown
    
    # Underwater Time
    underwater_pct: float = 0.0          # % of time in drawdown
    
    # Capital Info
    peak_equity_usd: float = 0.0
    trough_equity_usd: float = 0.0
    
    # Calculation metadata
    trading_days: int = 0
    annual_return_pct: float = 0.0       # For Calmar calculation
    net_profit_usd: float = 0.0          # For Recovery calculation
    
    calculated_at: str = ""
    is_valid: bool = True
    validation_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            
            # Drawdown
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "max_drawdown_value": round(self.max_drawdown_value, 2),
            "avg_drawdown_pct": round(self.avg_drawdown_pct, 4),
            
            # Duration
            "max_drawdown_duration_bars": self.max_drawdown_duration_bars,
            "avg_drawdown_duration_bars": round(self.avg_drawdown_duration_bars, 2),
            
            # Recovery
            "recovery_factor": round(self.recovery_factor, 4),
            
            # Ratios
            "calmar_ratio": round(self.calmar_ratio, 4),
            
            # Time
            "underwater_pct": round(self.underwater_pct, 4),
            
            # Capital
            "peak_equity_usd": round(self.peak_equity_usd, 2),
            "trough_equity_usd": round(self.trough_equity_usd, 2),
            
            # Metadata
            "trading_days": self.trading_days,
            "annual_return_pct": round(self.annual_return_pct, 4),
            "net_profit_usd": round(self.net_profit_usd, 2),
            "is_valid": self.is_valid,
            "validation_message": self.validation_message,
            "calculated_at": self.calculated_at
        }


# ===========================================
# Combined Metrics Snapshot
# ===========================================

@dataclass
class MetricsSnapshot:
    """
    Combined performance and risk metrics snapshot.
    
    Full metrics output for S1.4D API.
    """
    run_id: str = ""
    
    # Performance Metrics (S1.4B)
    total_return_pct: float = 0.0
    annual_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_trade_return: float = 0.0
    volatility_annual: float = 0.0
    
    # Risk Metrics (S1.4C)
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    max_drawdown_duration_bars: int = 0
    recovery_factor: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade Stats (S1.4A)
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Capital Info
    initial_capital_usd: float = 0.0
    final_equity_usd: float = 0.0
    net_profit_usd: float = 0.0
    trading_days: int = 0
    
    # Metadata
    calculated_at: str = ""
    is_valid: bool = True
    validation_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            
            # Performance
            "performance": {
                "total_return_pct": round(self.total_return_pct, 4),
                "annual_return_pct": round(self.annual_return_pct, 4),
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "profit_factor": round(self.profit_factor, 4),
                "expectancy": round(self.expectancy, 2),
                "avg_trade_return": round(self.avg_trade_return, 2),
                "volatility_annual": round(self.volatility_annual, 4)
            },
            
            # Risk
            "risk": {
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "avg_drawdown_pct": round(self.avg_drawdown_pct, 4),
                "max_drawdown_duration_bars": self.max_drawdown_duration_bars,
                "recovery_factor": round(self.recovery_factor, 4),
                "calmar_ratio": round(self.calmar_ratio, 4)
            },
            
            # Trade Stats
            "trade_stats": {
                "trades_count": self.trades_count,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": round(self.win_rate, 4)
            },
            
            # Capital
            "capital": {
                "initial_capital_usd": round(self.initial_capital_usd, 2),
                "final_equity_usd": round(self.final_equity_usd, 2),
                "net_profit_usd": round(self.net_profit_usd, 2),
                "trading_days": self.trading_days
            },
            
            # Metadata
            "is_valid": self.is_valid,
            "validation_message": self.validation_message,
            "calculated_at": self.calculated_at
        }
