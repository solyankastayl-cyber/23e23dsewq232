"""
Risk Metrics Service (S1.4C)
============================

Service for calculating risk metrics from simulation results.

Metrics:
- Max Drawdown (%)
- Average Drawdown (%)
- Drawdown Duration (bars)
- Recovery Factor
- Calmar Ratio

Post-simulation analysis:
1. Get equity history from state service
2. Calculate drawdown series
3. Compute risk metrics
4. Cache results
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import threading

from .risk_types import (
    RiskMetrics,
    DrawdownInfo,
    MetricsSnapshot
)

from .metrics_calculators import (
    calculate_max_drawdown,
    calculate_max_drawdown_value,
    calculate_avg_drawdown,
    calculate_max_drawdown_duration,
    calculate_recovery_factor,
    calculate_calmar_ratio,
    calculate_cagr
)

from ..simulation_state_service import simulation_state_service


DEFAULT_TRADING_DAYS_PER_YEAR = 365


class RiskMetricsService:
    """
    Service for calculating risk metrics.
    
    Thread-safe singleton.
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
        
        # Metrics cache: run_id -> RiskMetrics
        self._metrics_cache: Dict[str, RiskMetrics] = {}
        
        # Drawdown history: run_id -> List[DrawdownInfo]
        self._drawdown_history: Dict[str, List[DrawdownInfo]] = {}
        
        self._initialized = True
        print("[RiskMetricsService] Initialized")
    
    # ===========================================
    # Main Calculation Methods
    # ===========================================
    
    def calculate_metrics(
        self,
        run_id: str,
        initial_capital: Optional[float] = None,
        trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR
    ) -> RiskMetrics:
        """
        Calculate all risk metrics for a simulation run.
        
        Args:
            run_id: Simulation run ID
            initial_capital: Override initial capital (optional)
            trading_days_per_year: Days per year for annualization
            
        Returns:
            RiskMetrics with all calculated values
        """
        # Get equity history from state service
        equity_history = simulation_state_service.get_equity_history(run_id)
        
        if not equity_history:
            return self._invalid_metrics(run_id, "No equity history available")
        
        # Get initial capital from state if not provided
        if initial_capital is None:
            initial_capital = equity_history[0].get("equity_usd", 0)
        
        if not initial_capital or initial_capital <= 0:
            return self._invalid_metrics(run_id, "Invalid initial capital")
        
        # Extract equity values
        equity_values = [p.get("equity_usd", 0) for p in equity_history]
        timestamps = [p.get("timestamp", "") for p in equity_history]
        
        if len(equity_values) < 2:
            return self._invalid_metrics(run_id, "Insufficient data for risk metrics")
        
        # Calculate metrics
        metrics = self._compute_all_metrics(
            run_id,
            equity_values,
            timestamps,
            initial_capital,
            trading_days_per_year
        )
        
        # Cache
        self._metrics_cache[run_id] = metrics
        
        print(f"[RiskMetrics] Calculated for run: {run_id}, Max DD: {metrics.max_drawdown_pct*100:.2f}%")
        return metrics
    
    def get_metrics(self, run_id: str) -> Optional[RiskMetrics]:
        """
        Get cached metrics or calculate if not available.
        """
        if run_id in self._metrics_cache:
            return self._metrics_cache[run_id]
        
        # Try to calculate
        return self.calculate_metrics(run_id)
    
    # ===========================================
    # Metrics Computation
    # ===========================================
    
    def _compute_all_metrics(
        self,
        run_id: str,
        equity_values: List[float],
        timestamps: List[str],
        initial_capital: float,
        trading_days_per_year: int
    ) -> RiskMetrics:
        """
        Compute all risk metrics from equity curve.
        """
        metrics = RiskMetrics(
            run_id=run_id,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            trading_days=len(equity_values)
        )
        
        final_equity = equity_values[-1]
        
        # Net profit
        metrics.net_profit_usd = final_equity - initial_capital
        
        # Find peak and trough
        metrics.peak_equity_usd = max(equity_values)
        metrics.trough_equity_usd = min(equity_values)
        
        # Max Drawdown
        max_dd, peak_idx, trough_idx = calculate_max_drawdown(equity_values)
        metrics.max_drawdown_pct = max_dd
        
        # Max drawdown value (in USD)
        if peak_idx < len(equity_values):
            peak_value = equity_values[peak_idx]
            metrics.max_drawdown_value = peak_value * max_dd
        
        # Average Drawdown
        metrics.avg_drawdown_pct = calculate_avg_drawdown(equity_values)
        
        # Max Drawdown Duration
        metrics.max_drawdown_duration_bars = calculate_max_drawdown_duration(equity_values)
        
        # Calculate average drawdown duration
        drawdown_periods = self._calculate_drawdown_periods(equity_values, timestamps)
        if drawdown_periods:
            metrics.avg_drawdown_duration_bars = sum(
                p.duration_bars for p in drawdown_periods
            ) / len(drawdown_periods)
            
            # Store drawdown history
            self._drawdown_history[run_id] = drawdown_periods
        
        # Underwater percentage (% of time in drawdown)
        underwater_count = sum(1 for i in range(len(equity_values)) if self._is_underwater(equity_values, i))
        metrics.underwater_pct = underwater_count / len(equity_values) if equity_values else 0
        
        # Annual return (for Calmar)
        years = len(equity_values) / trading_days_per_year
        metrics.annual_return_pct = calculate_cagr(initial_capital, final_equity, years) * 100
        
        # Recovery Factor
        if metrics.max_drawdown_value > 0:
            metrics.recovery_factor = metrics.net_profit_usd / metrics.max_drawdown_value
        else:
            metrics.recovery_factor = float('inf') if metrics.net_profit_usd > 0 else 0
        
        # Calmar Ratio
        if metrics.max_drawdown_pct > 0:
            annual_return_decimal = metrics.annual_return_pct / 100
            metrics.calmar_ratio = calculate_calmar_ratio(annual_return_decimal, metrics.max_drawdown_pct)
        else:
            metrics.calmar_ratio = float('inf') if metrics.annual_return_pct > 0 else 0
        
        metrics.is_valid = True
        metrics.validation_message = "Risk metrics calculated successfully"
        
        return metrics
    
    def _is_underwater(self, equity_values: List[float], index: int) -> bool:
        """
        Check if equity at index is below running peak.
        """
        if index == 0:
            return False
        
        peak = max(equity_values[:index+1])
        return equity_values[index] < peak
    
    def _calculate_drawdown_periods(
        self,
        equity_values: List[float],
        timestamps: List[str]
    ) -> List[DrawdownInfo]:
        """
        Calculate individual drawdown periods.
        """
        if len(equity_values) < 2:
            return []
        
        periods = []
        peak = equity_values[0]
        peak_idx = 0
        in_drawdown = False
        current_period = None
        
        for i, value in enumerate(equity_values):
            if value >= peak:
                # New high or recovery
                if in_drawdown and current_period:
                    # End of drawdown
                    current_period.end_timestamp = timestamps[i] if i < len(timestamps) else ""
                    current_period.recovery_bars = i - current_period.duration_bars - \
                        (timestamps.index(current_period.start_timestamp) if current_period.start_timestamp in timestamps else 0)
                    current_period.is_recovered = True
                    periods.append(current_period)
                    current_period = None
                
                peak = value
                peak_idx = i
                in_drawdown = False
            else:
                # In drawdown
                dd = (peak - value) / peak if peak > 0 else 0
                
                if not in_drawdown:
                    # Start of new drawdown
                    in_drawdown = True
                    current_period = DrawdownInfo(
                        start_timestamp=timestamps[peak_idx] if peak_idx < len(timestamps) else "",
                        peak_equity=peak,
                        trough_equity=value,
                        drawdown_pct=dd,
                        drawdown_value=peak - value,
                        duration_bars=1
                    )
                else:
                    # Continue drawdown
                    if current_period:
                        current_period.duration_bars += 1
                        
                        # Update trough if deeper
                        if value < current_period.trough_equity:
                            current_period.trough_equity = value
                            current_period.drawdown_pct = dd
                            current_period.drawdown_value = peak - value
        
        # Handle if still in drawdown at end
        if in_drawdown and current_period:
            current_period.end_timestamp = timestamps[-1] if timestamps else ""
            current_period.is_recovered = False
            periods.append(current_period)
        
        return periods
    
    # ===========================================
    # Drawdown History
    # ===========================================
    
    def get_drawdown_history(self, run_id: str) -> List[DrawdownInfo]:
        """
        Get drawdown periods for run.
        """
        if run_id not in self._drawdown_history:
            # Calculate metrics which will populate history
            self.calculate_metrics(run_id)
        
        return self._drawdown_history.get(run_id, [])
    
    def get_largest_drawdowns(
        self,
        run_id: str,
        count: int = 5
    ) -> List[DrawdownInfo]:
        """
        Get the N largest drawdowns for run.
        """
        periods = self.get_drawdown_history(run_id)
        sorted_periods = sorted(periods, key=lambda p: p.drawdown_pct, reverse=True)
        return sorted_periods[:count]
    
    # ===========================================
    # Utilities
    # ===========================================
    
    def _invalid_metrics(self, run_id: str, message: str) -> RiskMetrics:
        """Create invalid metrics response"""
        return RiskMetrics(
            run_id=run_id,
            is_valid=False,
            validation_message=message,
            calculated_at=datetime.now(timezone.utc).isoformat()
        )
    
    # ===========================================
    # Cache Management
    # ===========================================
    
    def invalidate_cache(self, run_id: str) -> None:
        """Invalidate cached metrics for run"""
        self._metrics_cache.pop(run_id, None)
        self._drawdown_history.pop(run_id, None)
    
    def clear_run(self, run_id: str) -> None:
        """Clear all data for run"""
        self.invalidate_cache(run_id)
    
    def clear_all(self) -> int:
        """Clear all cached data"""
        count = len(self._metrics_cache)
        self._metrics_cache.clear()
        self._drawdown_history.clear()
        return count


# Global singleton
risk_metrics_service = RiskMetricsService()
