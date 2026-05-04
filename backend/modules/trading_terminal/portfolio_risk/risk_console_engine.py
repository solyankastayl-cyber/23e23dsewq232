"""
TT3 - Risk Console Engine
=========================
Calculates risk metrics, detects guardrail breaches, manages kill switch.
"""

from typing import Dict, List
from .portfolio_models import RiskSummary
from .portfolio_repository import PortfolioRepository


class RiskConsoleEngine:
    """Risk calculation and guardrail detection"""
    
    # Risk thresholds
    SYMBOL_CAP = 0.35          # Max 35% exposure per symbol
    DIRECTION_CAP = 0.60       # Max 60% in one direction
    HEAT_WARNING = 0.45        # Warning at 45% heat
    HEAT_CRITICAL = 0.70       # Critical at 70% heat
    DD_WARNING = 0.05          # Warning at 5% drawdown
    DD_CRITICAL = 0.10         # Critical at 10% drawdown

    def __init__(self, repo: PortfolioRepository):
        self.repo = repo

    def build_risk_summary(
        self, 
        portfolio_summary: Dict, 
        exposure_breakdown: Dict
    ) -> RiskSummary:
        """
        Build complete risk summary with guardrail detection.
        
        Args:
            portfolio_summary: From PortfolioEngine
            exposure_breakdown: From ExposureEngine
            
        Returns:
            RiskSummary with heat, status, guardrails, blocks
        """
        gross_exposure = float(portfolio_summary.get("gross_exposure", 0.0) or 0.0)
        daily_dd = self.repo.get_daily_drawdown()
        max_dd = self.repo.get_max_drawdown()
        kill_switch = self.repo.get_kill_switch()

        active_guardrails = list(self.repo.get_active_guardrails())
        block_reasons = list(self.repo.get_block_reasons())

        # Heat = gross exposure (can be enhanced later)
        heat = gross_exposure

        # Check symbol cap breaches
        for item in exposure_breakdown.get("by_symbol", []):
            symbol = item.get("symbol", "")
            exp = float(item.get("exposure", 0.0) or 0.0)
            if exp > self.SYMBOL_CAP:
                tag = f"symbol_cap_{symbol.lower()}"
                if tag not in active_guardrails:
                    active_guardrails.append(tag)
                reason = f"{symbol} exposure ({exp:.1%}) exceeds cap ({self.SYMBOL_CAP:.0%})"
                if reason not in block_reasons:
                    block_reasons.append(reason)

        # Check direction cap breaches
        by_direction = exposure_breakdown.get("by_direction", {})
        long_exp = float(by_direction.get("long", 0.0) or 0.0)
        short_exp = float(by_direction.get("short", 0.0) or 0.0)
        
        if long_exp > self.DIRECTION_CAP:
            tag = "direction_cap_long"
            if tag not in active_guardrails:
                active_guardrails.append(tag)
            reason = f"Long exposure ({long_exp:.1%}) exceeds cap ({self.DIRECTION_CAP:.0%})"
            if reason not in block_reasons:
                block_reasons.append(reason)
                
        if short_exp > self.DIRECTION_CAP:
            tag = "direction_cap_short"
            if tag not in active_guardrails:
                active_guardrails.append(tag)
            reason = f"Short exposure ({short_exp:.1%}) exceeds cap ({self.DIRECTION_CAP:.0%})"
            if reason not in block_reasons:
                block_reasons.append(reason)

        # Determine status based on heat and drawdown
        if kill_switch:
            status = "KILL_SWITCH"
        elif heat >= self.HEAT_CRITICAL or daily_dd >= self.DD_CRITICAL:
            status = "CRITICAL"
            if "portfolio_heat_guard" not in active_guardrails:
                active_guardrails.append("portfolio_heat_guard")
            if heat >= self.HEAT_CRITICAL and "portfolio heat critical" not in block_reasons:
                block_reasons.append("portfolio heat critical")
            if daily_dd >= self.DD_CRITICAL and "daily drawdown critical" not in block_reasons:
                block_reasons.append("daily drawdown critical")
        elif heat >= self.HEAT_WARNING or daily_dd >= self.DD_WARNING:
            status = "WARNING"
            if heat >= self.HEAT_WARNING and "portfolio_heat_guard" not in active_guardrails:
                active_guardrails.append("portfolio_heat_guard")
        else:
            status = "NORMAL"

        # Determine if new positions can be opened
        can_open_new = status == "NORMAL" and not kill_switch and len(block_reasons) == 0
        
        # Generate risk alerts
        risk_alerts = []
        if heat >= self.HEAT_WARNING:
            risk_alerts.append(f"Portfolio heat at {heat:.1%}")
        if daily_dd >= self.DD_WARNING:
            risk_alerts.append(f"Daily drawdown at {daily_dd:.1%}")
        if max_dd >= self.DD_WARNING:
            risk_alerts.append(f"Max drawdown at {max_dd:.1%}")

        return RiskSummary(
            heat=round(heat, 4),
            daily_drawdown=round(daily_dd, 4),
            max_drawdown=round(max_dd, 4),
            status=status,
            kill_switch=kill_switch,
            can_open_new=can_open_new,
            active_guardrails=active_guardrails,
            block_reasons=block_reasons,
            risk_alerts=risk_alerts,
        )

    def can_open_new_position(
        self, 
        portfolio_summary: Dict, 
        exposure_breakdown: Dict,
        new_symbol: str = None,
        new_side: str = None,
        new_notional: float = 0.0
    ) -> Dict:
        """
        Check if a new position can be opened.
        
        Returns:
            {"allowed": bool, "reasons": list}
        """
        risk = self.build_risk_summary(portfolio_summary, exposure_breakdown)
        
        if risk.kill_switch:
            return {"allowed": False, "reasons": ["Kill switch active"]}
            
        if risk.status == "CRITICAL":
            return {"allowed": False, "reasons": risk.block_reasons}
            
        if risk.status == "KILL_SWITCH":
            return {"allowed": False, "reasons": ["System in kill switch mode"]}

        # Check if new position would breach caps
        equity = float(portfolio_summary.get("equity", 1.0))
        new_exposure = new_notional / equity if equity > 0 else 0.0
        
        reasons = []
        
        # Check symbol cap with new position
        if new_symbol:
            current_symbol_exp = 0.0
            for item in exposure_breakdown.get("by_symbol", []):
                if item.get("symbol") == new_symbol:
                    current_symbol_exp = float(item.get("exposure", 0.0))
                    break
            if current_symbol_exp + new_exposure > self.SYMBOL_CAP:
                reasons.append(f"{new_symbol} would exceed symbol cap")

        # Check direction cap with new position  
        if new_side:
            by_direction = exposure_breakdown.get("by_direction", {})
            if new_side.upper() == "LONG":
                current_dir_exp = float(by_direction.get("long", 0.0))
            else:
                current_dir_exp = float(by_direction.get("short", 0.0))
            if current_dir_exp + new_exposure > self.DIRECTION_CAP:
                reasons.append(f"{new_side} direction would exceed cap")

        # Check gross exposure with new position
        current_gross = float(portfolio_summary.get("gross_exposure", 0.0))
        if current_gross + new_exposure >= self.HEAT_CRITICAL:
            reasons.append("Portfolio heat would reach critical level")

        return {
            "allowed": len(reasons) == 0,
            "reasons": reasons
        }
