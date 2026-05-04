"""
Risk Engine V1 - System-level risk controls

Answers: "CAN WE TRADE RIGHT NOW?"

Controls:
1. Daily Loss Limit - Stop trading if daily PnL below threshold
2. Drawdown Control - Circuit breaker on portfolio drawdown
3. Overtrading Protection - Reduce risk if too many trades
4. Volatility Regime - Scale down in high volatility
5. Portfolio Heat - Reduce exposure when portfolio is hot

Output: RiskState with can_trade flag, risk_multiplier, restrictions
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class RiskState:
    """Risk assessment output"""
    can_trade: bool
    risk_multiplier: float  # 0.0 - 1.0
    max_positions: int
    max_size_per_trade: float  # fraction of equity
    reason: str
    restrictions: Dict[str, Any]


class RiskEngine:
    """System-level risk control engine"""
    
    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,  # 5% daily loss limit
        max_drawdown_pct: float = 0.10,  # 10% drawdown circuit breaker
        max_portfolio_heat: float = 0.70,  # 70% max risk heat
        max_trades_per_hour: int = 5,
        high_volatility_threshold: float = 0.03,  # 3% volatility threshold
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_portfolio_heat = max_portfolio_heat
        self.max_trades_per_hour = max_trades_per_hour
        self.high_volatility_threshold = high_volatility_threshold
        
        # State tracking
        self.last_evaluation = None
        self.circuit_breaker_triggered = False
        self.circuit_breaker_time = None
    
    def evaluate(
        self,
        portfolio: Dict[str, Any],
        metrics: Dict[str, Any],
        market_volatility: Optional[float] = None,
    ) -> RiskState:
        """
        Evaluate current risk state and determine trading permissions
        
        Args:
            portfolio: {equity, balance, pnl, risk_heat, drawdown, ...}
            metrics: {trades_last_hour, trades_today, ...}
            market_volatility: Current market volatility (optional)
        
        Returns:
            RiskState with can_trade flag and risk_multiplier
        """
        equity = portfolio.get("equity", 10000)
        daily_pnl = portfolio.get("daily_pnl", 0)
        drawdown = portfolio.get("drawdown", 0)
        risk_heat = portfolio.get("risk_heat", 0)
        
        trades_last_hour = metrics.get("trades_last_hour", 0)
        
        # Default state: can trade, full risk
        can_trade = True
        risk_multiplier = 1.0
        reason = "normal"
        restrictions = {}
        
        # 1. DAILY LOSS LIMIT (CRITICAL - STOP ALL TRADING)
        daily_loss_pct = daily_pnl / equity if equity > 0 else 0
        if daily_loss_pct <= -self.max_daily_loss_pct:
            can_trade = False
            risk_multiplier = 0.0
            reason = f"daily_loss_limit_breached_{daily_loss_pct:.2%}"
            self.circuit_breaker_triggered = True
            self.circuit_breaker_time = datetime.now(timezone.utc)
            restrictions["stop_reason"] = "daily_loss_limit"
            restrictions["loss_pct"] = daily_loss_pct
        
        # 2. DRAWDOWN CIRCUIT BREAKER (CRITICAL - STOP ALL TRADING)
        elif abs(drawdown) >= self.max_drawdown_pct:
            can_trade = False
            risk_multiplier = 0.0
            reason = f"drawdown_circuit_breaker_{drawdown:.2%}"
            self.circuit_breaker_triggered = True
            self.circuit_breaker_time = datetime.now(timezone.utc)
            restrictions["stop_reason"] = "drawdown_limit"
            restrictions["drawdown"] = drawdown
        
        # 3. PORTFOLIO HEAT (REDUCE RISK)
        elif risk_heat >= self.max_portfolio_heat:
            can_trade = True
            risk_multiplier = 0.4  # Reduce to 40% risk
            reason = f"high_portfolio_heat_{risk_heat:.2f}"
            restrictions["heat_warning"] = True
        
        # 4. OVERTRADING PROTECTION (REDUCE RISK)
        elif trades_last_hour > self.max_trades_per_hour:
            can_trade = True
            risk_multiplier = 0.5  # Reduce to 50% risk
            reason = f"overtrading_{trades_last_hour}_trades_last_hour"
            restrictions["throttle"] = True
        
        # 5. VOLATILITY REGIME (REDUCE RISK)
        elif market_volatility and market_volatility > self.high_volatility_threshold:
            can_trade = True
            risk_multiplier = 0.6  # Reduce to 60% risk in high vol
            reason = f"high_volatility_{market_volatility:.2%}"
            restrictions["vol_adjustment"] = True
        
        # Normal trading conditions
        else:
            # Apply soft scaling based on heat
            if risk_heat > 0.5:
                risk_multiplier = 1.0 - (risk_heat - 0.5) * 0.4  # Scale down from 50% heat
                reason = f"normal_with_heat_scaling_{risk_heat:.2f}"
        
        # Calculate position limits
        max_positions = self._calculate_max_positions(risk_heat, drawdown)
        max_size_per_trade = self._calculate_max_size(risk_multiplier)
        
        self.last_evaluation = RiskState(
            can_trade=can_trade,
            risk_multiplier=risk_multiplier,
            max_positions=max_positions,
            max_size_per_trade=max_size_per_trade,
            reason=reason,
            restrictions=restrictions,
        )
        
        return self.last_evaluation
    
    def _calculate_max_positions(self, risk_heat: float, drawdown: float) -> int:
        """Calculate maximum allowed open positions based on risk state"""
        base_max = 10
        
        # Reduce max positions in high heat
        if risk_heat > 0.6:
            base_max = 5
        elif risk_heat > 0.5:
            base_max = 7
        
        # Reduce max positions in drawdown
        if abs(drawdown) > 0.05:  # 5% drawdown
            base_max = min(base_max, 5)
        
        return base_max
    
    def _calculate_max_size(self, risk_multiplier: float) -> float:
        """Calculate maximum position size as fraction of equity"""
        base_max_size = 0.15  # 15% max per trade normally
        return base_max_size * risk_multiplier
    
    def reset_circuit_breaker(self) -> bool:
        """
        Manually reset circuit breaker (operator action)
        Should only be called after review and approval
        
        Returns:
            True if reset successful
        """
        if self.circuit_breaker_triggered:
            self.circuit_breaker_triggered = False
            self.circuit_breaker_time = None
            return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk engine status"""
        return {
            "circuit_breaker_active": self.circuit_breaker_triggered,
            "circuit_breaker_time": self.circuit_breaker_time.isoformat() if self.circuit_breaker_time else None,
            "last_evaluation": {
                "can_trade": self.last_evaluation.can_trade if self.last_evaluation else None,
                "risk_multiplier": self.last_evaluation.risk_multiplier if self.last_evaluation else None,
                "reason": self.last_evaluation.reason if self.last_evaluation else None,
            } if self.last_evaluation else None,
            "config": {
                "max_daily_loss_pct": self.max_daily_loss_pct,
                "max_drawdown_pct": self.max_drawdown_pct,
                "max_portfolio_heat": self.max_portfolio_heat,
                "max_trades_per_hour": self.max_trades_per_hour,
            }
        }


# Global instance
_risk_engine = None

def get_risk_engine() -> RiskEngine:
    """Get global risk engine instance"""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine
