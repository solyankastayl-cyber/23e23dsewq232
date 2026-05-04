"""
Forward Repository
==================

Storage for forward simulation results (PHASE 2.3)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .forward_types import SimulationRun, SimulationStatus


class ForwardRepository:
    """
    In-memory repository for forward simulation runs.
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
        
        self._runs: Dict[str, SimulationRun] = {}
        self._latest_run: Optional[SimulationRun] = None
        
        self._initialized = True
        print("[ForwardRepository] Initialized (PHASE 2.3)")
    
    # ==========================================
    # Run Management
    # ==========================================
    
    def save_run(self, run: SimulationRun) -> None:
        """Save simulation run"""
        self._runs[run.run_id] = run
        self._latest_run = run
        
        # Keep only last 50 runs
        if len(self._runs) > 50:
            oldest = min(self._runs.keys(), key=lambda k: self._runs[k].started_at)
            del self._runs[oldest]
    
    def get_run(self, run_id: str) -> Optional[SimulationRun]:
        """Get run by ID"""
        return self._runs.get(run_id)
    
    def get_latest_run(self) -> Optional[SimulationRun]:
        """Get most recent run"""
        return self._latest_run
    
    def get_runs(self, limit: int = 20) -> List[SimulationRun]:
        """Get recent runs"""
        runs = list(self._runs.values())
        runs.sort(key=lambda x: x.started_at, reverse=True)
        return runs[:limit]
    
    def get_completed_runs(self, limit: int = 10) -> List[SimulationRun]:
        """Get completed runs only"""
        runs = [r for r in self._runs.values() if r.status == SimulationStatus.COMPLETED]
        runs.sort(key=lambda x: x.completed_at, reverse=True)
        return runs[:limit]
    
    # ==========================================
    # Stats
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        completed = [r for r in self._runs.values() if r.status == SimulationStatus.COMPLETED]
        
        return {
            "totalRuns": len(self._runs),
            "completedRuns": len(completed),
            "latestRunId": self._latest_run.run_id if self._latest_run else None,
            "latestStatus": self._latest_run.status.value if self._latest_run else None
        }
    
    def clear(self) -> None:
        """Clear all runs"""
        self._runs.clear()
        self._latest_run = None


# Global singleton
forward_repository = ForwardRepository()
