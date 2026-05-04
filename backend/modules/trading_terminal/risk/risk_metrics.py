"""
Risk Metrics Calculator (TR4)
=============================

Calculates core risk metrics: drawdown, daily loss, exposure, leverage.
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from .risk_types import RiskMetrics, ExposureMetrics, ConcentrationMetrics, TailRiskMetrics, RiskLevel


class RiskMetricsCalculator:
    """Calculates all risk metrics from portfolio data."""
    
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
        
        # Peak equity tracking
        self._peak_equity = 0.0
        self._start_of_day_equity = 0.0
        self._last_day_reset: Optional[datetime] = None
        self._drawdown_start: Optional[datetime] = None
        
        # Thresholds for risk level
        self._thresholds = {
            "drawdown_moderate": 0.08, "drawdown_high": 0.12, "drawdown_critical": 0.18,
            "daily_loss_moderate": 0.03, "daily_loss_high": 0.04, "daily_loss_critical": 0.05,
            "leverage_moderate": 2.0, "leverage_high": 3.0, "leverage_critical": 5.0,
            "concentration_moderate": 0.35, "concentration_high": 0.50,
            "var95_moderate": 0.15, "var95_high": 0.25, "var95_critical": 0.35
        }
        
        self._initialized = True
        print("[RiskMetricsCalculator] Initialized")
    
    def calculate_risk_metrics(self, current_equity: float) -> RiskMetrics:
        """Calculate drawdown and daily loss metrics."""
        now = datetime.now(timezone.utc)
        
        # Reset daily tracking at midnight
        if self._last_day_reset is None or now.date() != self._last_day_reset.date():
            self._start_of_day_equity = current_equity
            self._last_day_reset = now
        
        # Update peak
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
            self._drawdown_start = None
        
        # Calculate drawdown
        drawdown_pct = 0.0
        if self._peak_equity > 0:
            drawdown_pct = (self._peak_equity - current_equity) / self._peak_equity
            if drawdown_pct > 0 and self._drawdown_start is None:
                self._drawdown_start = now
        
        # Calculate drawdown duration
        drawdown_duration = 0.0
        if self._drawdown_start:
            drawdown_duration = (now - self._drawdown_start).total_seconds() / 3600
        
        # Calculate daily loss
        daily_loss_pct = 0.0
        if self._start_of_day_equity > 0:
            daily_loss_pct = max(0, (self._start_of_day_equity - current_equity) / self._start_of_day_equity)
        
        return RiskMetrics(
            current_drawdown_pct=drawdown_pct,
            max_drawdown_pct=max(drawdown_pct, getattr(self, '_max_dd', 0)),
            drawdown_duration_hours=drawdown_duration,
            daily_loss_pct=daily_loss_pct,
            daily_loss_limit_pct=0.05,
            daily_loss_remaining_pct=max(0, 0.05 - daily_loss_pct),
            peak_equity=self._peak_equity,
            current_equity=current_equity,
            start_of_day_equity=self._start_of_day_equity
        )
    
    def calculate_exposure_metrics(self, portfolio_state) -> ExposureMetrics:
        """Calculate exposure and leverage metrics from portfolio."""
        equity = portfolio_state.total_equity if portfolio_state else 0
        if equity <= 0:
            return ExposureMetrics()
        
        long_value = sum(p.notional_value for p in portfolio_state.positions if p.side == "LONG")
        short_value = sum(p.notional_value for p in portfolio_state.positions if p.side == "SHORT")
        gross = long_value + short_value
        net = long_value - short_value
        
        return ExposureMetrics(
            gross_exposure_usd=gross, gross_exposure_pct=gross / equity if equity else 0,
            net_exposure_usd=net, net_exposure_pct=net / equity if equity else 0,
            long_exposure_pct=long_value / equity if equity else 0,
            short_exposure_pct=short_value / equity if equity else 0,
            current_leverage=gross / equity if equity else 1.0,
            max_leverage=max(p.leverage for p in portfolio_state.positions) if portfolio_state.positions else 1.0
        )
    
    def calculate_concentration_metrics(self, portfolio_state) -> ConcentrationMetrics:
        """Calculate asset concentration metrics."""
        if not portfolio_state or not portfolio_state.balances:
            return ConcentrationMetrics()
        
        total_value = sum(b.usd_value for b in portfolio_state.balances)
        if total_value <= 0:
            return ConcentrationMetrics()
        
        # Sort by value
        sorted_balances = sorted(portfolio_state.balances, key=lambda b: b.usd_value, reverse=True)
        
        # Max asset
        max_bal = sorted_balances[0]
        max_weight = max_bal.usd_value / total_value
        
        # Top 3
        top_3_weight = sum(b.usd_value for b in sorted_balances[:3]) / total_value
        
        # By category
        categories = {"stablecoin": 0, "btc": 0, "eth": 0, "altcoin": 0}
        stables = ["USDT", "USDC", "BUSD", "DAI"]
        for b in portfolio_state.balances:
            weight = b.usd_value / total_value
            if b.asset in stables:
                categories["stablecoin"] += weight
            elif b.asset == "BTC":
                categories["btc"] += weight
            elif b.asset == "ETH":
                categories["eth"] += weight
            else:
                categories["altcoin"] += weight
        
        # HHI concentration score
        weights = [b.usd_value / total_value for b in portfolio_state.balances]
        hhi = sum(w**2 for w in weights)
        
        return ConcentrationMetrics(
            max_asset=max_bal.asset, max_asset_weight_pct=max_weight,
            top_3_assets_weight_pct=top_3_weight,
            stablecoin_weight_pct=categories["stablecoin"],
            btc_weight_pct=categories["btc"], eth_weight_pct=categories["eth"],
            altcoin_weight_pct=categories["altcoin"], concentration_score=hhi
        )
    
    def calculate_risk_level(self, metrics: RiskMetrics, exposure: ExposureMetrics, concentration: ConcentrationMetrics, tail: TailRiskMetrics) -> tuple:
        """Calculate overall risk level."""
        level = RiskLevel.LOW
        reasons = []
        
        # Check drawdown
        if metrics.current_drawdown_pct >= self._thresholds["drawdown_critical"]:
            level = RiskLevel.CRITICAL
            reasons.append(f"Drawdown {metrics.current_drawdown_pct*100:.1f}%")
        elif metrics.current_drawdown_pct >= self._thresholds["drawdown_high"]:
            level = max(level, RiskLevel.HIGH, key=lambda x: x.value)
            reasons.append(f"Drawdown {metrics.current_drawdown_pct*100:.1f}%")
        elif metrics.current_drawdown_pct >= self._thresholds["drawdown_moderate"]:
            level = max(level, RiskLevel.MODERATE, key=lambda x: x.value)
        
        # Check daily loss
        if metrics.daily_loss_pct >= self._thresholds["daily_loss_critical"]:
            level = RiskLevel.CRITICAL
            reasons.append(f"Daily loss {metrics.daily_loss_pct*100:.1f}%")
        elif metrics.daily_loss_pct >= self._thresholds["daily_loss_high"]:
            level = max(level, RiskLevel.HIGH, key=lambda x: x.value)
            reasons.append(f"Daily loss {metrics.daily_loss_pct*100:.1f}%")
        
        # Check leverage
        if exposure.current_leverage >= self._thresholds["leverage_critical"]:
            level = RiskLevel.CRITICAL
            reasons.append(f"Leverage {exposure.current_leverage:.1f}x")
        elif exposure.current_leverage >= self._thresholds["leverage_high"]:
            level = max(level, RiskLevel.HIGH, key=lambda x: x.value)
            reasons.append(f"Leverage {exposure.current_leverage:.1f}x")
        
        # Check concentration
        if concentration.max_asset_weight_pct >= self._thresholds["concentration_high"]:
            level = max(level, RiskLevel.HIGH, key=lambda x: x.value)
            reasons.append(f"Concentration {concentration.max_asset_weight_pct*100:.0f}%")
        
        # Check VaR
        if abs(tail.var_95_pct) >= self._thresholds["var95_critical"]:
            level = max(level, RiskLevel.HIGH, key=lambda x: x.value)
            reasons.append(f"VaR95 {tail.var_95_pct*100:.1f}%")
        
        reason = "; ".join(reasons) if reasons else "All metrics normal"
        return level, reason
    
    def get_thresholds(self) -> Dict[str, float]:
        return self._thresholds.copy()
    
    def get_health(self) -> Dict[str, Any]:
        return {"service": "RiskMetricsCalculator", "status": "healthy", "phase": "TR4", "peak_equity": round(self._peak_equity, 2)}


risk_metrics_calculator = RiskMetricsCalculator()
