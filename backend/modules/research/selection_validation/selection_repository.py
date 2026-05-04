"""
Selection Repository
====================

Storage for selection validation results (PHASE 2.4)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .selection_types import (
    SelectionValidationRun,
    SelectionComparison,
    SelectionMistake,
    ValidationStatus
)


class SelectionRepository:
    """
    In-memory repository for selection validation runs.
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
        
        self._runs: Dict[str, SelectionValidationRun] = {}
        self._latest_run: Optional[SelectionValidationRun] = None
        
        self._initialized = True
        print("[SelectionRepository] Initialized (PHASE 2.4)")
    
    # ==========================================
    # Run Management
    # ==========================================
    
    def save_run(self, run: SelectionValidationRun) -> None:
        """Save validation run"""
        self._runs[run.run_id] = run
        self._latest_run = run
        
        # Keep only last 30 runs
        if len(self._runs) > 30:
            oldest = min(self._runs.keys(), key=lambda k: self._runs[k].started_at)
            del self._runs[oldest]
    
    def get_run(self, run_id: str) -> Optional[SelectionValidationRun]:
        """Get run by ID"""
        return self._runs.get(run_id)
    
    def get_latest_run(self) -> Optional[SelectionValidationRun]:
        """Get most recent run"""
        return self._latest_run
    
    def get_runs(self, limit: int = 20) -> List[SelectionValidationRun]:
        """Get recent runs"""
        runs = list(self._runs.values())
        runs.sort(key=lambda x: x.started_at, reverse=True)
        return runs[:limit]
    
    # ==========================================
    # Query Methods
    # ==========================================
    
    def get_comparisons(
        self,
        regime: str = None,
        correct_only: bool = False,
        limit: int = 50
    ) -> List[SelectionComparison]:
        """Get comparisons from latest run"""
        if not self._latest_run:
            return []
        
        comparisons = self._latest_run.comparisons
        
        if regime:
            comparisons = [c for c in comparisons if c.regime == regime.upper()]
        
        if correct_only:
            comparisons = [c for c in comparisons if c.is_correct]
        
        return comparisons[:limit]
    
    def get_mistakes(
        self,
        severity: str = None,
        limit: int = 50
    ) -> List[SelectionMistake]:
        """Get mistakes from latest run"""
        if not self._latest_run:
            return []
        
        mistakes = self._latest_run.mistakes
        
        if severity:
            mistakes = [m for m in mistakes if m.severity.value == severity.upper()]
        
        return mistakes[:limit]
    
    # ==========================================
    # Stats
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        if not self._latest_run:
            return {
                "hasRun": False,
                "totalRuns": len(self._runs)
            }
        
        return {
            "hasRun": True,
            "totalRuns": len(self._runs),
            "latestRunId": self._latest_run.run_id,
            "latestStatus": self._latest_run.status.value,
            "latestAccuracy": self._latest_run.metrics.selection_accuracy if self._latest_run.metrics else 0,
            "validationPassed": self._latest_run.metrics.validation_passed if self._latest_run.metrics else False
        }
    
    def clear(self) -> None:
        """Clear all runs"""
        self._runs.clear()
        self._latest_run = None


# Global singleton
selection_repository = SelectionRepository()
