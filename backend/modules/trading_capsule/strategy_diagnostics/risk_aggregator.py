"""
Risk Aggregator (STR4)
======================

Aggregates risk metrics from various sources.

Metrics:
- Drawdown (current, max)
- Daily loss
- Exposure
- Leverage
- VaR/CVaR (if available)
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .diagnostics_types import RiskSummary


class RiskAggregator:
    """
    Aggregates risk metrics.
    
    Collects data from:
    - Risk module (T4)
    - Portfolio state
    - Monte Carlo (if available)
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
        
        # Risk state
        self._current_drawdown_pct = 0.0
        self._max_drawdown_pct = 0.0
        self._drawdown_start: Optional[datetime] = None
        
        self._daily_loss_pct = 0.0
        self._daily_loss_start: Optional[datetime] = None
        
        self._total_exposure_pct = 0.0
        self._current_leverage = 1.0
        
        # Limits
        self._daily_loss_limit = 0.05  # 5%
        self._max_exposure = 0.40      # 40%
        self._max_leverage = 3.0       # 3x
        
        # VaR (from Monte Carlo)
        self._var_95: Optional[float] = None
        self._cvar_95: Optional[float] = None
        
        # Protection status
        self._loss_protection_active = False
        self._drawdown_protection_active = False
        
        self._initialized = True
        print("[RiskAggregator] Initialized")
    
    # ===========================================
    # Main Aggregation
    # ===========================================
    
    def get_risk_summary(
        self,
        portfolio_state: Optional[Dict[str, Any]] = None,
        monte_carlo_results: Optional[Dict[str, Any]] = None
    ) -> RiskSummary:
        """
        Get aggregated risk summary.
        
        Args:
            portfolio_state: Current portfolio state
            monte_carlo_results: Results from Monte Carlo simulation
        
        Returns:
            RiskSummary with all metrics
        """
        # Update from portfolio state
        if portfolio_state:
            self._update_from_portfolio(portfolio_state)
        
        # Update VaR from Monte Carlo
        if monte_carlo_results:
            self._var_95 = monte_carlo_results.get("var_95")
            self._cvar_95 = monte_carlo_results.get("cvar_95")
        
        # Calculate drawdown duration
        drawdown_duration = 0.0
        if self._drawdown_start and self._current_drawdown_pct > 0:
            duration = datetime.now(timezone.utc) - self._drawdown_start
            drawdown_duration = duration.total_seconds() / 3600  # hours
        
        # Check protections
        self._check_protections()
        
        return RiskSummary(
            current_drawdown_pct=self._current_drawdown_pct,
            max_drawdown_pct=self._max_drawdown_pct,
            drawdown_duration_hours=drawdown_duration,
            daily_loss_pct=self._daily_loss_pct,
            daily_loss_limit_pct=self._daily_loss_limit,
            daily_loss_remaining_pct=max(0, self._daily_loss_limit - self._daily_loss_pct),
            total_exposure_pct=self._total_exposure_pct,
            max_exposure_pct=self._max_exposure,
            current_leverage=self._current_leverage,
            max_leverage=self._max_leverage,
            var_95_pct=self._var_95,
            cvar_95_pct=self._cvar_95,
            loss_protection_active=self._loss_protection_active,
            drawdown_protection_active=self._drawdown_protection_active
        )
    
    # ===========================================
    # Update Methods
    # ===========================================
    
    def _update_from_portfolio(self, portfolio_state: Dict[str, Any]) -> None:
        """Update risk state from portfolio"""
        # Drawdown
        new_drawdown = portfolio_state.get("drawdown_pct", 0.0)
        if new_drawdown > 0 and self._current_drawdown_pct == 0:
            self._drawdown_start = datetime.now(timezone.utc)
        elif new_drawdown == 0:
            self._drawdown_start = None
        
        self._current_drawdown_pct = new_drawdown
        self._max_drawdown_pct = max(self._max_drawdown_pct, new_drawdown)
        
        # Daily loss
        self._daily_loss_pct = portfolio_state.get("daily_loss_pct", 0.0)
        
        # Exposure
        self._total_exposure_pct = portfolio_state.get("exposure_pct", 0.0)
        
        # Leverage
        self._current_leverage = portfolio_state.get("leverage", 1.0)
    
    def update_drawdown(self, drawdown_pct: float) -> None:
        """Update drawdown value"""
        if drawdown_pct > 0 and self._current_drawdown_pct == 0:
            self._drawdown_start = datetime.now(timezone.utc)
        elif drawdown_pct == 0:
            self._drawdown_start = None
        
        self._current_drawdown_pct = drawdown_pct
        self._max_drawdown_pct = max(self._max_drawdown_pct, drawdown_pct)
    
    def update_daily_loss(self, loss_pct: float) -> None:
        """Update daily loss"""
        self._daily_loss_pct = loss_pct
    
    def update_exposure(self, exposure_pct: float) -> None:
        """Update exposure"""
        self._total_exposure_pct = exposure_pct
    
    def update_leverage(self, leverage: float) -> None:
        """Update leverage"""
        self._current_leverage = leverage
    
    def update_var(self, var_95: float, cvar_95: float) -> None:
        """Update VaR metrics"""
        self._var_95 = var_95
        self._cvar_95 = cvar_95
    
    # ===========================================
    # Protection Checks
    # ===========================================
    
    def _check_protections(self) -> None:
        """Check and update protection status"""
        # Loss protection
        self._loss_protection_active = self._daily_loss_pct >= self._daily_loss_limit
        
        # Drawdown protection
        self._drawdown_protection_active = self._current_drawdown_pct >= 0.10  # 10%
    
    def is_loss_limit_breached(self) -> bool:
        """Check if daily loss limit is breached"""
        return self._daily_loss_pct >= self._daily_loss_limit
    
    def is_drawdown_critical(self) -> bool:
        """Check if drawdown is critical"""
        return self._current_drawdown_pct >= 0.15  # 15%
    
    def is_exposure_high(self) -> bool:
        """Check if exposure is high"""
        return self._total_exposure_pct >= self._max_exposure * 0.8  # 80% of max
    
    # ===========================================
    # Limit Management
    # ===========================================
    
    def set_daily_loss_limit(self, limit_pct: float) -> None:
        """Set daily loss limit"""
        self._daily_loss_limit = limit_pct
    
    def set_max_exposure(self, max_pct: float) -> None:
        """Set max exposure"""
        self._max_exposure = max_pct
    
    def set_max_leverage(self, max_lev: float) -> None:
        """Set max leverage"""
        self._max_leverage = max_lev
    
    def get_limits(self) -> Dict[str, float]:
        """Get current limits"""
        return {
            "daily_loss_limit_pct": self._daily_loss_limit,
            "max_exposure_pct": self._max_exposure,
            "max_leverage": self._max_leverage
        }
    
    # ===========================================
    # Reset
    # ===========================================
    
    def reset_daily(self) -> None:
        """Reset daily metrics (called at start of new day)"""
        self._daily_loss_pct = 0.0
        self._daily_loss_start = datetime.now(timezone.utc)
        self._loss_protection_active = False
    
    def reset_max_drawdown(self) -> None:
        """Reset max drawdown tracking"""
        self._max_drawdown_pct = self._current_drawdown_pct
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get aggregator health"""
        return {
            "service": "RiskAggregator",
            "status": "healthy",
            "version": "str4",
            "current_drawdown_pct": round(self._current_drawdown_pct, 4),
            "daily_loss_pct": round(self._daily_loss_pct, 4),
            "protections": {
                "loss_protection_active": self._loss_protection_active,
                "drawdown_protection_active": self._drawdown_protection_active
            }
        }


# Global singleton
risk_aggregator = RiskAggregator()
