"""
Portfolio Risk Policy
=====================

Portfolio-level risk rules and enforcement.

Rules:
- If heat > 0.4 → BLOCK new entries
- If drawdown < -10% → REDUCE all positions
- If drawdown < -15% → HARD STOP trading
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PortfolioPolicy:
    """Portfolio risk policy engine."""
    
    def evaluate(
        self,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate portfolio state and generate policy decisions.
        
        Args:
            portfolio_state: Current portfolio state with equity, heat, drawdown
        
        Returns:
            Policy decision with actions and flags
        """
        heat = portfolio_state.get("heat", {}).get("heat", 0.0)
        drawdown_pct = portfolio_state.get("drawdown", {}).get("current_dd_pct", 0.0)
        equity = portfolio_state.get("equity", {}).get("equity", 0.0)
        
        actions = []
        block_new_entries = False
        reduce_all = False
        hard_stop = False
        reason_chain = []
        
        # 1. HEAT RULES
        if heat > 0.4:
            block_new_entries = True
            reason_chain.append("heat_limit_exceeded")
            logger.warning(f"[PortfolioPolicy] Heat {heat:.2f} > 0.4 → blocking new entries")
            actions.append({
                "action_type": "BLOCK_NEW_ENTRIES",
                "reason": "portfolio_heat_limit",
                "priority": "HIGH",
                "payload": {"heat": heat},
            })
        
        # 2. DRAWDOWN RULES
        if drawdown_pct < -15.0:
            hard_stop = True
            reduce_all = True
            block_new_entries = True
            reason_chain.append("drawdown_critical_hard_stop")
            logger.error(f"[PortfolioPolicy] Drawdown {drawdown_pct:.1f}% → HARD STOP")
            actions.append({
                "action_type": "HARD_STOP_TRADING",
                "reason": "portfolio_drawdown_critical",
                "priority": "CRITICAL",
                "payload": {"drawdown_pct": drawdown_pct},
            })
            actions.append({
                "action_type": "CLOSE_ALL_POSITIONS",
                "reason": "portfolio_drawdown_critical",
                "priority": "CRITICAL",
                "payload": {},
            })
        elif drawdown_pct < -10.0:
            reduce_all = True
            reason_chain.append("drawdown_high_reduce_all")
            logger.warning(f"[PortfolioPolicy] Drawdown {drawdown_pct:.1f}% → reducing all positions")
            actions.append({
                "action_type": "REDUCE_ALL_POSITIONS",
                "reason": "portfolio_drawdown_high",
                "priority": "HIGH",
                "payload": {
                    "reduce_pct": 0.5,
                    "drawdown_pct": drawdown_pct,
                },
            })
        
        # 3. EQUITY PROTECTION
        if equity < 5000:  # Below minimum capital
            hard_stop = True
            block_new_entries = True
            reason_chain.append("equity_below_minimum")
            logger.error(f"[PortfolioPolicy] Equity ${equity:,.2f} below minimum → HARD STOP")
            actions.append({
                "action_type": "HARD_STOP_TRADING",
                "reason": "portfolio_equity_minimum",
                "priority": "CRITICAL",
                "payload": {"equity": equity},
            })
        
        return {
            "can_trade": not hard_stop,
            "can_open_new": not block_new_entries,
            "must_reduce_all": reduce_all,
            "hard_stop": hard_stop,
            "actions": actions,
            "reason_chain": reason_chain,
            "actions_count": len(actions),
        }


# Singleton instance
_policy: PortfolioPolicy = None


def get_portfolio_policy() -> PortfolioPolicy:
    """Get or create singleton portfolio policy."""
    global _policy
    if _policy is None:
        _policy = PortfolioPolicy()
    return _policy
