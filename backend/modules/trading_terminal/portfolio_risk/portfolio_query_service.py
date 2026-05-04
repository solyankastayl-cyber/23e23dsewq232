"""
TT3 - Portfolio Query Service
=============================
Provides preview/summary views for UI components.
"""

from typing import Dict


class PortfolioQueryService:
    """Service for portfolio/risk UI queries"""
    
    def get_portfolio_preview(self, portfolio_summary: Dict) -> Dict:
        """Get compact portfolio preview for status block"""
        return {
            "equity": portfolio_summary.get("equity"),
            "free_capital": portfolio_summary.get("free_capital"),
            "used_capital": portfolio_summary.get("used_capital"),
            "realized_pnl": portfolio_summary.get("realized_pnl"),
            "unrealized_pnl": portfolio_summary.get("unrealized_pnl"),
            "open_positions": portfolio_summary.get("open_positions"),
            "open_orders": portfolio_summary.get("open_orders"),
        }

    def get_risk_preview(self, risk_summary: Dict) -> Dict:
        """Get compact risk preview for status block"""
        return {
            "heat": risk_summary.get("heat"),
            "daily_drawdown": risk_summary.get("daily_drawdown"),
            "max_drawdown": risk_summary.get("max_drawdown"),
            "status": risk_summary.get("status"),
            "kill_switch": risk_summary.get("kill_switch"),
            "active_guardrails_count": len(risk_summary.get("active_guardrails", [])),
            "block_reasons_count": len(risk_summary.get("block_reasons", [])),
        }

    def get_portfolio_exposure_preview(self, exposure_breakdown: Dict) -> Dict:
        """Get exposure preview"""
        by_symbol = exposure_breakdown.get("by_symbol", [])
        by_direction = exposure_breakdown.get("by_direction", {})
        
        # Top 3 symbols by exposure
        top_symbols = by_symbol[:3] if len(by_symbol) > 3 else by_symbol
        
        return {
            "top_symbols": top_symbols,
            "by_direction": by_direction,
            "total_symbols": len(by_symbol),
        }

    def format_for_terminal_state(
        self, 
        portfolio_summary: Dict,
        exposure_breakdown: Dict,
        risk_summary: Dict
    ) -> Dict:
        """Format all data for terminal state orchestrator"""
        return {
            "portfolio": portfolio_summary,
            "portfolio_exposure": exposure_breakdown,
            "risk": risk_summary,
            "portfolio_preview": self.get_portfolio_preview(portfolio_summary),
            "risk_preview": self.get_risk_preview(risk_summary),
        }
