"""
Margin Engine - PHASE 5.4
=========================

Calculates and monitors margin across the portfolio.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .account_types import MarginInfo
from .account_aggregator import get_account_aggregator
from .position_aggregator import get_position_aggregator


class MarginEngine:
    """
    Margin calculation and monitoring engine.
    
    Responsibilities:
    - Calculate used margin
    - Calculate free margin
    - Monitor margin utilization
    - Track leverage exposure
    - Generate margin stress flags
    """
    
    def __init__(self):
        self._account_aggregator = get_account_aggregator()
        self._position_aggregator = get_position_aggregator()
        self._margin_info: Dict[str, MarginInfo] = {}
        self._last_calculation: Optional[datetime] = None
        
        # Risk thresholds
        self._utilization_warning = 0.6  # 60%
        self._utilization_critical = 0.8  # 80%
        self._leverage_warning = 5.0
        self._leverage_critical = 10.0
    
    def calculate_margin(self, exchanges: Optional[List[str]] = None) -> Dict[str, MarginInfo]:
        """Calculate margin info for all or specified exchanges"""
        target_exchanges = exchanges or ["BINANCE", "BYBIT", "OKX"]
        
        self._margin_info.clear()
        
        for exchange in target_exchanges:
            try:
                margin = self._calculate_exchange_margin(exchange)
                self._margin_info[exchange] = margin
            except Exception as e:
                print(f"Error calculating margin for {exchange}: {e}")
                self._margin_info[exchange] = MarginInfo(
                    exchange=exchange,
                    risk_level="UNKNOWN",
                    timestamp=datetime.utcnow()
                )
        
        self._last_calculation = datetime.utcnow()
        return self._margin_info
    
    def _calculate_exchange_margin(self, exchange: str) -> MarginInfo:
        """Calculate margin for specific exchange"""
        # Get account data
        account = self._account_aggregator.get_account(exchange)
        positions = self._position_aggregator.get_positions_by_exchange(exchange)
        
        if not account:
            return MarginInfo(
                exchange=exchange,
                risk_level="UNKNOWN",
                timestamp=datetime.utcnow()
            )
        
        # Calculate margin metrics
        total_margin = account.equity
        used_margin = account.used_margin
        free_margin = total_margin - used_margin
        
        # Calculate margin utilization
        utilization = (used_margin / total_margin) if total_margin > 0 else 0
        
        # Calculate leverage exposure
        total_notional = sum(p.notional_value for p in positions)
        leverage_exposure = (total_notional / total_margin) if total_margin > 0 else 0
        
        # Calculate maintenance and initial margin (simplified)
        maintenance_margin = used_margin * 0.5  # Typically 50% of initial
        initial_margin = used_margin
        
        # Determine risk level
        risk_level = self._assess_risk(utilization, leverage_exposure)
        is_at_risk = risk_level in ["HIGH", "CRITICAL"]
        
        return MarginInfo(
            exchange=exchange,
            total_margin=round(total_margin, 2),
            used_margin=round(used_margin, 2),
            free_margin=round(free_margin, 2),
            margin_ratio=round(account.margin_ratio, 2),
            margin_utilization=round(utilization * 100, 2),
            maintenance_margin=round(maintenance_margin, 2),
            initial_margin=round(initial_margin, 2),
            leverage_exposure=round(leverage_exposure, 2),
            is_at_risk=is_at_risk,
            risk_level=risk_level,
            timestamp=datetime.utcnow()
        )
    
    def _assess_risk(self, utilization: float, leverage: float) -> str:
        """Assess margin risk level"""
        if utilization >= self._utilization_critical or leverage >= self._leverage_critical:
            return "CRITICAL"
        elif utilization >= self._utilization_warning or leverage >= self._leverage_warning:
            return "HIGH"
        elif utilization >= 0.4 or leverage >= 3.0:
            return "MEDIUM"
        return "LOW"
    
    def get_margin_info(self, exchange: str) -> Optional[MarginInfo]:
        """Get margin info for specific exchange"""
        return self._margin_info.get(exchange.upper())
    
    def get_all_margin_info(self) -> Dict[str, MarginInfo]:
        """Get margin info for all exchanges"""
        return self._margin_info
    
    def get_portfolio_margin(self) -> Dict[str, Any]:
        """Get aggregated portfolio margin"""
        total_margin = 0.0
        total_used = 0.0
        total_free = 0.0
        total_leverage_exposure = 0.0
        risk_count = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        
        for exchange, info in self._margin_info.items():
            total_margin += info.total_margin
            total_used += info.used_margin
            total_free += info.free_margin
            total_leverage_exposure += info.leverage_exposure * info.total_margin
            risk_count[info.risk_level] = risk_count.get(info.risk_level, 0) + 1
        
        avg_leverage = (total_leverage_exposure / total_margin) if total_margin > 0 else 0
        utilization = (total_used / total_margin) if total_margin > 0 else 0
        
        # Determine overall risk
        if risk_count.get("CRITICAL", 0) > 0:
            overall_risk = "CRITICAL"
        elif risk_count.get("HIGH", 0) > 0:
            overall_risk = "HIGH"
        elif risk_count.get("MEDIUM", 0) > 0:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"
        
        return {
            "total_margin": round(total_margin, 2),
            "total_used_margin": round(total_used, 2),
            "total_free_margin": round(total_free, 2),
            "margin_utilization_pct": round(utilization * 100, 2),
            "avg_leverage_exposure": round(avg_leverage, 2),
            "overall_risk_level": overall_risk,
            "risk_breakdown": risk_count,
            "exchanges_at_risk": [
                ex for ex, info in self._margin_info.items()
                if info.is_at_risk
            ],
            "last_calculation": self._last_calculation.isoformat() if self._last_calculation else None
        }
    
    def get_stress_flags(self) -> List[Dict[str, Any]]:
        """Get margin stress flags/warnings"""
        flags = []
        
        for exchange, info in self._margin_info.items():
            if info.margin_utilization >= self._utilization_critical * 100:
                flags.append({
                    "exchange": exchange,
                    "type": "MARGIN_CRITICAL",
                    "message": f"Margin utilization at {info.margin_utilization:.1f}%",
                    "severity": "CRITICAL",
                    "value": info.margin_utilization
                })
            elif info.margin_utilization >= self._utilization_warning * 100:
                flags.append({
                    "exchange": exchange,
                    "type": "MARGIN_WARNING",
                    "message": f"Margin utilization at {info.margin_utilization:.1f}%",
                    "severity": "WARNING",
                    "value": info.margin_utilization
                })
            
            if info.leverage_exposure >= self._leverage_critical:
                flags.append({
                    "exchange": exchange,
                    "type": "LEVERAGE_CRITICAL",
                    "message": f"Leverage exposure at {info.leverage_exposure:.1f}x",
                    "severity": "CRITICAL",
                    "value": info.leverage_exposure
                })
            elif info.leverage_exposure >= self._leverage_warning:
                flags.append({
                    "exchange": exchange,
                    "type": "LEVERAGE_WARNING",
                    "message": f"Leverage exposure at {info.leverage_exposure:.1f}x",
                    "severity": "WARNING",
                    "value": info.leverage_exposure
                })
        
        return sorted(flags, key=lambda x: (
            0 if x["severity"] == "CRITICAL" else 1
        ))
    
    def get_margin_headroom(self) -> Dict[str, float]:
        """Get margin headroom per exchange"""
        headroom = {}
        
        for exchange, info in self._margin_info.items():
            if info.total_margin > 0:
                # How much more margin can be used before hitting critical
                max_safe_usage = info.total_margin * self._utilization_warning
                current_headroom = max_safe_usage - info.used_margin
                headroom[exchange] = round(max(0, current_headroom), 2)
            else:
                headroom[exchange] = 0.0
        
        return headroom
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "exchanges_tracked": len(self._margin_info),
            "last_calculation": self._last_calculation.isoformat() if self._last_calculation else None,
            "warning_threshold": f"{self._utilization_warning * 100}%",
            "critical_threshold": f"{self._utilization_critical * 100}%"
        }


# Global instance
_margin_engine: Optional[MarginEngine] = None


def get_margin_engine() -> MarginEngine:
    """Get or create global margin engine"""
    global _margin_engine
    if _margin_engine is None:
        _margin_engine = MarginEngine()
    return _margin_engine
