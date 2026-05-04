"""
AF1 - Alpha Query Service
=========================
Query service for Alpha Factory data.
"""

from typing import List, Dict, Any
from .alpha_repository import AlphaRepository


class AlphaQueryService:
    """Service for querying Alpha Factory data"""
    
    def __init__(self, repo: AlphaRepository):
        self.repo = repo

    def get_metrics(self, scope: str) -> List[Dict[str, Any]]:
        """Get all metrics for a scope"""
        return [x.to_dict() for x in self.repo.get_metrics(scope)]

    def get_evaluations(self, scope: str) -> List[Dict[str, Any]]:
        """Get all evaluations for a scope"""
        return [x.to_dict() for x in self.repo.get_evaluations(scope)]

    def get_actions(self) -> List[Dict[str, Any]]:
        """Get all actions"""
        return [x.to_dict() for x in self.repo.get_actions()]

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get actions that need attention (not KEEP)"""
        return [x.to_dict() for x in self.repo.get_pending_actions()]

    def get_summary(self) -> Dict[str, Any]:
        """Get Alpha Factory summary for UI blocks"""
        return self.repo.get_summary()

    def get_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """Get status for specific symbol"""
        metrics = self.repo.get_metrics_by_key("symbol", symbol)
        evaluation = self.repo.get_evaluation_by_key("symbol", symbol)
        
        if not evaluation:
            return {
                "symbol": symbol,
                "found": False,
                "verdict": "UNKNOWN",
                "recommendation": "Run Alpha Factory first"
            }
            
        # Find action
        action = None
        for a in self.repo.get_actions():
            if a.scope == "symbol" and a.scope_key == symbol:
                action = a
                break
                
        return {
            "symbol": symbol,
            "found": True,
            "verdict": evaluation.verdict,
            "confidence": evaluation.confidence,
            "win_rate": metrics.win_rate if metrics else None,
            "profit_factor": metrics.profit_factor if metrics else None,
            "expectancy": metrics.expectancy if metrics else None,
            "trades": metrics.trades if metrics else 0,
            "action": action.action if action else "KEEP",
            "action_reason": action.reason if action else None,
        }

    def format_for_terminal_state(self) -> Dict[str, Any]:
        """Format Alpha Factory data for terminal state integration"""
        summary = self.repo.get_summary()
        pending = self.get_pending_actions()[:5]  # Top 5 pending actions
        
        return {
            "alpha_summary": {
                "strong_edge": summary["strong_edge"],
                "weak_edge": summary["weak_edge"],
                "unstable_edge": summary["unstable_edge"],
                "no_edge": summary["no_edge"],
                "pending_actions": summary["pending_actions"],
                "last_run": summary["last_run"],
            },
            "pending_actions_preview": pending,
        }
