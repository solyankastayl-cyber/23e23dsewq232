"""
AF1 - Alpha Repository
======================
In-memory storage for Alpha Factory data. Can be replaced with MongoDB later.
"""

from typing import Dict, List, Optional
from .alpha_models import AlphaMetrics, AlphaEvaluation, AlphaAction


class AlphaRepository:
    """In-memory storage for Alpha Factory results"""
    
    def __init__(self):
        self.metrics_store: Dict[str, List[AlphaMetrics]] = {
            "symbol": [],
            "entry_mode": [],
        }
        self.evaluations_store: Dict[str, List[AlphaEvaluation]] = {
            "symbol": [],
            "entry_mode": [],
        }
        self.actions_store: List[AlphaAction] = []
        self.last_run_timestamp: Optional[str] = None

    # Metrics
    def save_metrics(self, scope: str, items: List[AlphaMetrics]) -> List[AlphaMetrics]:
        self.metrics_store[scope] = items
        return items

    def get_metrics(self, scope: str) -> List[AlphaMetrics]:
        return self.metrics_store.get(scope, [])

    def get_metrics_by_key(self, scope: str, scope_key: str) -> Optional[AlphaMetrics]:
        for m in self.metrics_store.get(scope, []):
            if m.scope_key == scope_key:
                return m
        return None

    # Evaluations
    def save_evaluations(self, scope: str, items: List[AlphaEvaluation]) -> List[AlphaEvaluation]:
        self.evaluations_store[scope] = items
        return items

    def get_evaluations(self, scope: str) -> List[AlphaEvaluation]:
        return self.evaluations_store.get(scope, [])

    def get_evaluation_by_key(self, scope: str, scope_key: str) -> Optional[AlphaEvaluation]:
        for e in self.evaluations_store.get(scope, []):
            if e.scope_key == scope_key:
                return e
        return None

    # Actions
    def save_actions(self, items: List[AlphaAction]) -> List[AlphaAction]:
        self.actions_store = items
        return items

    def get_actions(self) -> List[AlphaAction]:
        return self.actions_store

    def get_actions_by_scope(self, scope: str) -> List[AlphaAction]:
        return [a for a in self.actions_store if a.scope == scope]

    def get_pending_actions(self) -> List[AlphaAction]:
        """Get actions that haven't been applied yet"""
        return [a for a in self.actions_store if a.action != "KEEP"]

    # Summary
    def get_summary(self) -> Dict:
        all_evals = self.evaluations_store.get("symbol", []) + self.evaluations_store.get("entry_mode", [])
        
        return {
            "strong_edge": sum(1 for e in all_evals if e.verdict == "STRONG_EDGE"),
            "weak_edge": sum(1 for e in all_evals if e.verdict == "WEAK_EDGE"),
            "unstable_edge": sum(1 for e in all_evals if e.verdict == "UNSTABLE_EDGE"),
            "no_edge": sum(1 for e in all_evals if e.verdict == "NO_EDGE"),
            "pending_actions": len(self.get_pending_actions()),
            "last_run": self.last_run_timestamp,
        }

    def set_last_run(self, timestamp: str):
        self.last_run_timestamp = timestamp

    def clear(self):
        """Reset all data"""
        self.__init__()
