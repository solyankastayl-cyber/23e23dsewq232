"""
Metrics Routes (S1.4A/S1.4B/S1.4C/S1.4D)
========================================

REST API for trade normalization, performance metrics, and risk metrics.

Endpoints:

# Trade Normalization (S1.4A)
GET  /api/trading/simulation/runs/{runId}/trades         - Get closed trades
GET  /api/trading/simulation/runs/{runId}/trades/stats   - Get trade statistics
GET  /api/trading/simulation/runs/{runId}/trades/{id}    - Get specific trade
POST /api/trading/simulation/runs/{runId}/trades/normalize - Trigger normalization

# Performance Metrics (S1.4B)
GET /api/trading/simulation/runs/{runId}/performance     - Get performance metrics
GET /api/trading/simulation/runs/{runId}/performance/curve - Get processed equity curve

# Risk Metrics (S1.4C)
GET /api/trading/simulation/runs/{runId}/risk           - Get risk metrics
GET /api/trading/simulation/runs/{runId}/risk/drawdowns - Get drawdown history

# Combined Metrics API (S1.4D)
GET /api/trading/simulation/runs/{runId}/metrics        - Get all metrics combined
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone

from .trade_types import ClosedTrade, TradeStats
from .trade_normalizer_service import trade_normalizer_service
from .performance_metrics_service import performance_metrics_service
from .performance_types import MetricsConfig
from .risk_metrics_service import risk_metrics_service
from .risk_types import MetricsSnapshot


router = APIRouter(tags=["Trade Metrics (S1.4)"])


# ===========================================
# Trade Endpoints (specific routes BEFORE generic {trade_id})
# ===========================================

@router.get("/runs/{run_id}/trades/stats")
async def get_trade_stats(run_id: str):
    """
    Get aggregate trade statistics.
    
    Includes win rate, profit factor, expectancy, etc.
    """
    stats = trade_normalizer_service.get_trade_stats(run_id)
    
    return {
        "run_id": run_id,
        "stats": stats.to_dict()
    }


@router.get("/runs/{run_id}/trades/summary")
async def get_trade_summary(run_id: str):
    """
    Get full trade summary with stats and all trades.
    """
    summary = trade_normalizer_service.get_trade_summary(run_id)
    return summary


@router.post("/runs/{run_id}/trades/normalize")
async def normalize_trades(
    run_id: str,
    close_open: bool = Query(True, description="Close open positions at final price")
):
    """
    Trigger trade normalization.
    
    Reconstructs closed trades from fills.
    Usually called automatically after simulation completes.
    """
    trades = trade_normalizer_service.normalize_from_broker(run_id, close_open)
    
    return {
        "run_id": run_id,
        "trades_normalized": len(trades),
        "success": True
    }


@router.get("/runs/{run_id}/trades")
async def get_trades(
    run_id: str,
    filter: Optional[str] = Query(None, description="Filter: 'winners' or 'losers'"),
    limit: int = Query(100, description="Max trades to return")
):
    """
    Get closed trades for simulation run.
    
    Trades are reconstructed from fills.
    """
    trades = trade_normalizer_service.get_trades(run_id)
    
    # Apply filter
    if filter == "winners":
        trades = [t for t in trades if t.is_winner]
    elif filter == "losers":
        trades = [t for t in trades if not t.is_winner]
    
    # Apply limit
    trades = trades[:limit]
    
    return {
        "run_id": run_id,
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


@router.get("/runs/{run_id}/trades/{trade_id}")
async def get_trade(run_id: str, trade_id: str):
    """Get specific trade by ID"""
    trade = trade_normalizer_service.get_trade(run_id, trade_id)
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade.to_dict()


# ===========================================
# Performance Metrics (S1.4B)
# ===========================================

@router.get("/runs/{run_id}/performance")
async def get_performance_metrics(
    run_id: str,
    initial_capital: Optional[float] = Query(None, description="Override initial capital"),
    risk_free_rate: float = Query(0.0, description="Risk-free rate (annualized)"),
    trading_days: int = Query(365, description="Trading days per year (365 for crypto)")
):
    """
    Get performance metrics for simulation run.
    
    Includes:
    - Total Return (%)
    - Annual Return (CAGR)
    - Sharpe Ratio
    - Sortino Ratio
    - Volatility (annualized)
    """
    config = MetricsConfig(
        risk_free_rate=risk_free_rate,
        trading_days_per_year=trading_days
    )
    
    metrics = performance_metrics_service.calculate_metrics(
        run_id,
        initial_capital=initial_capital,
        config=config
    )
    
    return {
        "run_id": run_id,
        "metrics": metrics.to_dict()
    }


@router.get("/runs/{run_id}/performance/curve")
async def get_performance_curve(
    run_id: str,
    initial_capital: Optional[float] = Query(None, description="Override initial capital")
):
    """
    Get processed equity curve with returns and drawdowns.
    
    Each point includes:
    - Equity value
    - Period return %
    - Cumulative return %
    - Current drawdown %
    """
    curve = performance_metrics_service.get_processed_equity_curve(
        run_id,
        initial_capital=initial_capital
    )
    
    if not curve:
        raise HTTPException(status_code=404, detail="No equity data available")
    
    return {
        "run_id": run_id,
        "curve": [p.to_dict() for p in curve],
        "points": len(curve)
    }


@router.get("/runs/{run_id}/performance/summary")
async def get_performance_summary(
    run_id: str,
    initial_capital: Optional[float] = Query(None)
):
    """
    Get combined performance summary.
    
    Includes both trade stats and performance metrics.
    """
    # Get trade stats
    trade_stats = trade_normalizer_service.get_trade_stats(run_id)
    
    # Get performance metrics
    perf_metrics = performance_metrics_service.calculate_metrics(
        run_id,
        initial_capital=initial_capital
    )
    
    return {
        "run_id": run_id,
        "trade_stats": trade_stats.to_dict(),
        "performance": perf_metrics.to_dict(),
        "summary": {
            "total_trades": trade_stats.total_trades,
            "win_rate": trade_stats.win_rate,
            "profit_factor": trade_stats.profit_factor,
            "total_return_pct": perf_metrics.total_return_pct,
            "sharpe_ratio": perf_metrics.sharpe_ratio,
            "sortino_ratio": perf_metrics.sortino_ratio
        }
    }


# ===========================================
# Risk Metrics (S1.4C)
# ===========================================

@router.get("/runs/{run_id}/risk")
async def get_risk_metrics(
    run_id: str,
    initial_capital: Optional[float] = Query(None, description="Override initial capital"),
    trading_days: int = Query(365, description="Trading days per year (365 for crypto)")
):
    """
    Get risk metrics for simulation run.
    
    Includes:
    - Max Drawdown (%)
    - Average Drawdown (%)
    - Max Drawdown Duration (bars)
    - Recovery Factor
    - Calmar Ratio
    """
    metrics = risk_metrics_service.calculate_metrics(
        run_id,
        initial_capital=initial_capital,
        trading_days_per_year=trading_days
    )
    
    return {
        "run_id": run_id,
        "risk_metrics": metrics.to_dict()
    }


@router.get("/runs/{run_id}/risk/drawdowns")
async def get_drawdown_history(
    run_id: str,
    limit: int = Query(10, description="Max drawdown periods to return")
):
    """
    Get drawdown periods for simulation run.
    
    Returns list of drawdown periods with:
    - Start/end timestamps
    - Peak/trough equity
    - Drawdown percentage
    - Duration in bars
    - Recovery status
    """
    drawdowns = risk_metrics_service.get_largest_drawdowns(run_id, limit)
    
    return {
        "run_id": run_id,
        "drawdowns": [d.to_dict() for d in drawdowns],
        "count": len(drawdowns)
    }


# ===========================================
# Combined Metrics API (S1.4D)
# ===========================================

@router.get("/runs/{run_id}/metrics")
async def get_combined_metrics(
    run_id: str,
    initial_capital: Optional[float] = Query(None, description="Override initial capital"),
    risk_free_rate: float = Query(0.0, description="Risk-free rate (annualized)"),
    trading_days: int = Query(365, description="Trading days per year (365 for crypto)")
):
    """
    Get combined performance and risk metrics (S1.4D).
    
    Returns complete metrics snapshot including:
    - Performance: Sharpe, Sortino, Profit Factor, Expectancy, etc.
    - Risk: Max Drawdown, Calmar, Recovery Factor, etc.
    - Trade Stats: Win rate, trade count, etc.
    
    This is the primary endpoint for metrics consumption.
    """
    config = MetricsConfig(
        risk_free_rate=risk_free_rate,
        trading_days_per_year=trading_days
    )
    
    # Get all components
    perf_metrics = performance_metrics_service.calculate_metrics(
        run_id,
        initial_capital=initial_capital,
        config=config
    )
    
    risk_metrics = risk_metrics_service.calculate_metrics(
        run_id,
        initial_capital=initial_capital,
        trading_days_per_year=trading_days
    )
    
    trade_stats = trade_normalizer_service.get_trade_stats(run_id)
    
    # Build combined snapshot
    snapshot = MetricsSnapshot(
        run_id=run_id,
        
        # Performance Metrics
        total_return_pct=perf_metrics.total_return_pct,
        annual_return_pct=perf_metrics.annual_return_pct,
        sharpe_ratio=perf_metrics.sharpe_ratio,
        sortino_ratio=perf_metrics.sortino_ratio,
        profit_factor=perf_metrics.profit_factor,
        expectancy=perf_metrics.expectancy,
        avg_trade_return=perf_metrics.avg_trade_return,
        volatility_annual=perf_metrics.volatility_annual,
        
        # Risk Metrics
        max_drawdown_pct=risk_metrics.max_drawdown_pct * 100,  # Convert to percentage
        avg_drawdown_pct=risk_metrics.avg_drawdown_pct * 100,
        max_drawdown_duration_bars=risk_metrics.max_drawdown_duration_bars,
        recovery_factor=risk_metrics.recovery_factor,
        calmar_ratio=risk_metrics.calmar_ratio,
        
        # Trade Stats
        trades_count=trade_stats.total_trades,
        winning_trades=trade_stats.winning_trades,
        losing_trades=trade_stats.losing_trades,
        win_rate=trade_stats.win_rate,
        
        # Capital
        initial_capital_usd=perf_metrics.initial_capital_usd,
        final_equity_usd=perf_metrics.final_equity_usd,
        net_profit_usd=risk_metrics.net_profit_usd,
        trading_days=perf_metrics.trading_days,
        
        # Metadata
        calculated_at=datetime.now(timezone.utc).isoformat(),
        is_valid=perf_metrics.is_valid and risk_metrics.is_valid,
        validation_message=perf_metrics.validation_message if perf_metrics.is_valid else risk_metrics.validation_message
    )
    
    return snapshot.to_dict()


@router.get("/runs/{run_id}/metrics/health")
async def metrics_health():
    """
    Health check for metrics engine.
    """
    return {
        "status": "healthy",
        "version": "S1.4D",
        "services": {
            "trade_normalizer": "ready",
            "performance_metrics": "ready",
            "risk_metrics": "ready"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
