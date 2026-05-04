"""
Portfolio Service (TR2)
=======================

Main service for unified portfolio monitoring.

Features:
- Get unified portfolio state
- Get balances/positions
- Get exposure/metrics
- Store snapshots
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .portfolio_types import (
    UnifiedPortfolioState,
    PortfolioBalance,
    PortfolioPosition,
    PortfolioMetrics,
    ExposureBreakdown,
    PortfolioSnapshot
)
from .portfolio_aggregator import portfolio_aggregator


class PortfolioService:
    """
    Unified Portfolio Monitoring Service.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Snapshots history
        self._snapshots: List[PortfolioSnapshot] = []
        self._max_snapshots = 1000
        
        # Last state cache
        self._last_state: Optional[UnifiedPortfolioState] = None
        self._last_state_time: Optional[datetime] = None
        self._cache_ttl = 10  # seconds
        
        self._initialized = True
        print("[PortfolioService] Initialized")
    
    # ===========================================
    # Portfolio State
    # ===========================================
    
    def get_portfolio_state(self, force_refresh: bool = False) -> UnifiedPortfolioState:
        """
        Get unified portfolio state.
        """
        # Check cache
        if not force_refresh and self._last_state and self._last_state_time:
            cache_age = (datetime.now(timezone.utc) - self._last_state_time).total_seconds()
            if cache_age < self._cache_ttl:
                return self._last_state
        
        # Aggregate from all accounts
        state = portfolio_aggregator.aggregate()
        
        # Update cache
        self._last_state = state
        self._last_state_time = datetime.now(timezone.utc)
        
        # Store snapshot
        self._store_snapshot(state)
        
        return state
    
    # ===========================================
    # Individual Components
    # ===========================================
    
    def get_balances(self) -> List[PortfolioBalance]:
        """Get all balances"""
        state = self.get_portfolio_state()
        return state.balances
    
    def get_positions(self) -> List[PortfolioPosition]:
        """Get all positions"""
        state = self.get_portfolio_state()
        return state.positions
    
    def get_equity(self) -> Dict[str, float]:
        """Get equity summary"""
        state = self.get_portfolio_state()
        return {
            "total_equity": state.total_equity,
            "available_margin": state.available_margin,
            "used_margin": state.used_margin,
            "total_balance_usd": state.total_balance_usd
        }
    
    def get_pnl(self) -> Dict[str, float]:
        """Get PnL summary"""
        state = self.get_portfolio_state()
        return {
            "daily_pnl": state.metrics.daily_pnl,
            "daily_pnl_pct": state.metrics.daily_pnl_pct,
            "total_unrealized_pnl": state.metrics.total_unrealized_pnl,
            "total_realized_pnl": state.metrics.total_realized_pnl
        }
    
    def get_exposure(self) -> ExposureBreakdown:
        """Get exposure breakdown"""
        state = self.get_portfolio_state()
        return state.exposure
    
    def get_metrics(self) -> PortfolioMetrics:
        """Get portfolio metrics"""
        state = self.get_portfolio_state()
        return state.metrics
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data (compact format)"""
        state = self.get_portfolio_state()
        return state.to_dashboard_dict()
    
    # ===========================================
    # Snapshots
    # ===========================================
    
    def _store_snapshot(self, state: UnifiedPortfolioState) -> None:
        """Store portfolio snapshot"""
        snapshot = PortfolioSnapshot(
            equity=state.total_equity,
            total_pnl=state.metrics.total_unrealized_pnl,
            positions_count=state.positions_count,
            net_exposure=state.exposure.net_exposure,
            leverage=state.metrics.portfolio_leverage
        )
        
        self._snapshots.append(snapshot)
        
        # Limit history
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
    
    def get_snapshots(self, limit: int = 100) -> List[PortfolioSnapshot]:
        """Get snapshot history"""
        return list(reversed(self._snapshots[-limit:]))
    
    def get_equity_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get equity curve data"""
        snapshots = self.get_snapshots(limit)
        return [
            {
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "equity": s.equity,
                "pnl": s.total_pnl
            }
            for s in snapshots
        ]
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "PortfolioService",
            "status": "healthy",
            "phase": "TR2",
            "snapshots_stored": len(self._snapshots),
            "cache_age_sec": (
                (datetime.now(timezone.utc) - self._last_state_time).total_seconds()
                if self._last_state_time else None
            )
        }


# Global singleton
portfolio_service = PortfolioService()
