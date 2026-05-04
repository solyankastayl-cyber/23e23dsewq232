"""
Calibration Repository
======================

Storage for Calibration Matrix results (PHASE 2.1)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .calibration_types import (
    CalibrationRun,
    CalibrationMatrix,
    CalibrationResult,
    CalibrationStatus
)


class CalibrationRepository:
    """
    In-memory repository for calibration runs and results.
    
    Stores:
    - Calibration runs history
    - Latest matrix
    - Results by strategy/symbol/timeframe/regime
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
        
        self._runs: Dict[str, CalibrationRun] = {}
        self._latest_matrix: Optional[CalibrationMatrix] = None
        self._results_index: Dict[str, CalibrationResult] = {}
        
        self._initialized = True
        print("[CalibrationRepository] Initialized (PHASE 2.1)")
    
    # ==========================================
    # Run Management
    # ==========================================
    
    def save_run(self, run: CalibrationRun) -> None:
        """Save calibration run"""
        self._runs[run.run_id] = run
        
        # Keep only last 100 runs
        if len(self._runs) > 100:
            oldest = sorted(self._runs.keys())[0]
            del self._runs[oldest]
    
    def get_run(self, run_id: str) -> Optional[CalibrationRun]:
        """Get run by ID"""
        return self._runs.get(run_id)
    
    def get_latest_run(self) -> Optional[CalibrationRun]:
        """Get most recent run"""
        if not self._runs:
            return None
        latest_id = max(self._runs.keys(), key=lambda x: self._runs[x].started_at)
        return self._runs[latest_id]
    
    def get_runs(self, limit: int = 20) -> List[CalibrationRun]:
        """Get recent runs"""
        runs = list(self._runs.values())
        runs.sort(key=lambda x: x.started_at, reverse=True)
        return runs[:limit]
    
    def update_run_status(
        self,
        run_id: str,
        status: CalibrationStatus,
        progress: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """Update run status"""
        if run_id in self._runs:
            self._runs[run_id].status = status
            self._runs[run_id].progress = progress
            if error:
                self._runs[run_id].error = error
    
    # ==========================================
    # Matrix Management
    # ==========================================
    
    def save_matrix(self, matrix: CalibrationMatrix) -> None:
        """Save calibration matrix"""
        self._latest_matrix = matrix
        
        # Index results for quick lookup
        for result in matrix.results:
            key = self._make_key(
                result.strategy,
                result.symbol,
                result.timeframe,
                result.regime
            )
            self._results_index[key] = result
    
    def get_latest_matrix(self) -> Optional[CalibrationMatrix]:
        """Get latest matrix"""
        return self._latest_matrix
    
    def get_result(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str
    ) -> Optional[CalibrationResult]:
        """Get specific result from matrix"""
        key = self._make_key(strategy, symbol, timeframe, regime)
        return self._results_index.get(key)
    
    # ==========================================
    # Query Methods
    # ==========================================
    
    def get_results_by_strategy(self, strategy: str) -> List[CalibrationResult]:
        """Get all results for a strategy"""
        return [
            r for r in self._results_index.values()
            if r.strategy.upper() == strategy.upper()
        ]
    
    def get_results_by_symbol(self, symbol: str) -> List[CalibrationResult]:
        """Get all results for a symbol"""
        return [
            r for r in self._results_index.values()
            if r.symbol.upper() == symbol.upper()
        ]
    
    def get_results_by_regime(self, regime: str) -> List[CalibrationResult]:
        """Get all results for a regime"""
        return [
            r for r in self._results_index.values()
            if r.regime.upper() == regime.upper()
        ]
    
    def get_results_by_timeframe(self, timeframe: str) -> List[CalibrationResult]:
        """Get all results for a timeframe"""
        return [
            r for r in self._results_index.values()
            if r.timeframe.lower() == timeframe.lower()
        ]
    
    def get_top_performers(self, limit: int = 10) -> List[CalibrationResult]:
        """Get top performing combinations by profit factor"""
        results = list(self._results_index.values())
        results.sort(key=lambda x: x.metrics.profit_factor, reverse=True)
        return [r for r in results[:limit] if r.is_valid]
    
    def get_worst_performers(self, limit: int = 10) -> List[CalibrationResult]:
        """Get worst performing combinations"""
        results = [r for r in self._results_index.values() if r.is_valid]
        results.sort(key=lambda x: x.metrics.profit_factor)
        return results[:limit]
    
    # ==========================================
    # Utility
    # ==========================================
    
    def _make_key(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str
    ) -> str:
        """Create index key"""
        return f"{strategy.upper()}:{symbol.upper()}:{timeframe.lower()}:{regime.upper()}"
    
    def clear(self) -> None:
        """Clear all data"""
        self._runs.clear()
        self._latest_matrix = None
        self._results_index.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        return {
            "totalRuns": len(self._runs),
            "hasMatrix": self._latest_matrix is not None,
            "indexedResults": len(self._results_index),
            "latestRunId": self.get_latest_run().run_id if self.get_latest_run() else None
        }


# Global singleton
calibration_repository = CalibrationRepository()
