"""
PHASE 10 - Drawdown Control Engine
===================================
Reduces risk when portfolio is in drawdown.

drawdown > 5% → reduce risk
drawdown > 10% → significantly reduce exposure
drawdown > 15% → emergency risk reduction
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from .portfolio_types import (
    DrawdownControl, DrawdownState, DEFAULT_PORTFOLIO_CONFIG
)


class DrawdownControlEngine:
    """
    Drawdown Control Engine
    
    Monitors portfolio equity and reduces risk exposure
    when drawdowns exceed acceptable thresholds.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.history: List[DrawdownControl] = []
        self.max_history = 100
        
        # Track peak equity
        self.peak_equity: float = 0.0
        self.drawdown_start: Optional[datetime] = None
        self.equity_history: List[tuple] = []  # (timestamp, equity)
    
    def analyze_drawdown(
        self,
        current_equity: float,
        initial_equity: Optional[float] = None
    ) -> DrawdownControl:
        """
        Analyze drawdown and determine risk reduction.
        
        Args:
            current_equity: Current portfolio equity
            initial_equity: Initial/starting equity (optional)
            
        Returns:
            DrawdownControl with risk reduction recommendations
        """
        now = datetime.now(timezone.utc)
        
        # Update peak tracking
        if initial_equity and initial_equity > self.peak_equity:
            self.peak_equity = initial_equity
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.drawdown_start = None  # Reset drawdown tracking
        
        # Calculate drawdown
        if self.peak_equity > 0:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        else:
            current_drawdown = 0.0
        
        # Determine drawdown state
        drawdown_state = self._determine_state(current_drawdown)
        
        # Calculate risk reduction factor
        risk_reduction_factor = self._calculate_risk_reduction(current_drawdown)
        
        # Calculate capital deployment
        capital_deployment = self._calculate_capital_deployment(
            current_drawdown, drawdown_state
        )
        
        # Track drawdown duration
        if current_drawdown > 0.01 and self.drawdown_start is None:
            self.drawdown_start = now
        elif current_drawdown <= 0.01:
            self.drawdown_start = None
        
        days_in_drawdown = 0
        if self.drawdown_start:
            days_in_drawdown = (now - self.drawdown_start).days
        
        # Calculate recovery distance
        if current_equity > 0:
            recovery_distance = (self.peak_equity - current_equity) / current_equity
        else:
            recovery_distance = 0.0
        
        result = DrawdownControl(
            timestamp=now,
            current_drawdown=current_drawdown,
            max_drawdown_limit=self.config["max_drawdown_limit"],
            drawdown_state=drawdown_state,
            risk_reduction_factor=risk_reduction_factor,
            capital_deployment=capital_deployment,
            peak_equity=self.peak_equity,
            current_equity=current_equity,
            recovery_distance=recovery_distance,
            drawdown_start=self.drawdown_start,
            days_in_drawdown=days_in_drawdown
        )
        
        # Update history
        self._add_to_history(result)
        self._add_equity_history(now, current_equity)
        
        return result
    
    def _determine_state(self, drawdown: float) -> DrawdownState:
        """Determine drawdown state based on severity."""
        if drawdown < 0.03:
            return DrawdownState.NORMAL
        elif drawdown < 0.05:
            return DrawdownState.CAUTION
        elif drawdown < 0.10:
            return DrawdownState.WARNING
        elif drawdown < 0.15:
            return DrawdownState.CRITICAL
        else:
            return DrawdownState.EMERGENCY
    
    def _calculate_risk_reduction(self, drawdown: float) -> float:
        """
        Calculate risk reduction factor based on drawdown.
        
        Returns value 0-1:
        - 1.0 = no reduction (full risk)
        - 0.5 = 50% reduction
        - 0.0 = full risk off
        """
        max_dd = self.config["max_drawdown_limit"]
        reduction_rate = self.config["drawdown_reduction_rate"]
        
        if drawdown < 0.03:
            # No reduction below 3%
            return 1.0
        
        if drawdown >= max_dd:
            # Maximum reduction at limit
            return 0.2  # Keep 20% exposure minimum
        
        # Linear reduction between threshold and limit
        threshold = 0.03
        reduction_range = max_dd - threshold
        excess_dd = drawdown - threshold
        
        reduction = 1.0 - (excess_dd / reduction_range) * (1 - 0.2)
        
        return max(0.2, min(1.0, reduction))
    
    def _calculate_capital_deployment(
        self,
        drawdown: float,
        state: DrawdownState
    ) -> float:
        """Calculate recommended capital deployment level."""
        deployment_map = {
            DrawdownState.NORMAL: 1.0,
            DrawdownState.CAUTION: 0.85,
            DrawdownState.WARNING: 0.65,
            DrawdownState.CRITICAL: 0.40,
            DrawdownState.EMERGENCY: 0.20
        }
        
        return deployment_map.get(state, 0.5)
    
    def _add_to_history(self, result: DrawdownControl):
        """Add result to history."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def _add_equity_history(self, timestamp: datetime, equity: float):
        """Track equity history."""
        self.equity_history.append((timestamp, equity))
        if len(self.equity_history) > 252:  # Keep ~1 year of daily data
            self.equity_history = self.equity_history[-252:]
    
    def get_drawdown_summary(self) -> Dict:
        """Get summary of drawdown control."""
        if not self.history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.history[-1]
        
        # Determine action recommendation
        if recent.drawdown_state == DrawdownState.NORMAL:
            action = "NORMAL_OPERATION"
        elif recent.drawdown_state == DrawdownState.CAUTION:
            action = "MONITOR_CLOSELY"
        elif recent.drawdown_state == DrawdownState.WARNING:
            action = "REDUCE_NEW_POSITIONS"
        elif recent.drawdown_state == DrawdownState.CRITICAL:
            action = "REDUCE_EXPOSURE"
        else:
            action = "EMERGENCY_RISK_OFF"
        
        return {
            "current_drawdown": f"{recent.current_drawdown * 100:.2f}%",
            "drawdown_state": recent.drawdown_state.value,
            "risk_reduction": f"{(1 - recent.risk_reduction_factor) * 100:.1f}%",
            "capital_deployment": f"{recent.capital_deployment * 100:.1f}%",
            "days_in_drawdown": recent.days_in_drawdown,
            "recovery_needed": f"{recent.recovery_distance * 100:.2f}%",
            "action": action
        }
    
    def reset_peak(self, new_peak: Optional[float] = None):
        """Reset peak equity (e.g., after capital injection)."""
        if new_peak:
            self.peak_equity = new_peak
        else:
            self.peak_equity = 0.0
        self.drawdown_start = None
    
    def get_recovery_projection(self) -> Dict:
        """Get recovery projection based on history."""
        if not self.history or not self.equity_history:
            return {"projection": "INSUFFICIENT_DATA"}
        
        recent = self.history[-1]
        
        if recent.current_drawdown <= 0.01:
            return {
                "projection": "NOT_IN_DRAWDOWN",
                "current_drawdown": round(recent.current_drawdown, 4)
            }
        
        # Calculate average daily return from history
        if len(self.equity_history) >= 5:
            recent_equities = [e for _, e in self.equity_history[-20:]]
            if len(recent_equities) >= 2:
                returns = []
                for i in range(1, len(recent_equities)):
                    if recent_equities[i-1] > 0:
                        ret = (recent_equities[i] - recent_equities[i-1]) / recent_equities[i-1]
                        returns.append(ret)
                
                if returns:
                    avg_daily_return = sum(returns) / len(returns)
                    
                    # Days to recover at avg return
                    if avg_daily_return > 0:
                        days_to_recover = int(
                            recent.recovery_distance / avg_daily_return
                        )
                    else:
                        days_to_recover = -1  # Cannot recover with negative returns
                    
                    return {
                        "projection": "ESTIMATED",
                        "current_drawdown": round(recent.current_drawdown, 4),
                        "recovery_needed": round(recent.recovery_distance, 4),
                        "avg_daily_return": round(avg_daily_return, 4),
                        "estimated_days_to_recover": days_to_recover
                    }
        
        return {
            "projection": "INSUFFICIENT_DATA",
            "current_drawdown": round(recent.current_drawdown, 4)
        }
