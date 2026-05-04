"""
Calibration Runner
==================

Orchestrates calibration runs (PHASE 2.1)
"""

import time
import uuid
import threading
from typing import Dict, List, Optional, Any

from .calibration_types import (
    CalibrationConfig,
    CalibrationRun,
    CalibrationMatrix,
    CalibrationStatus
)
from .calibration_engine import calibration_engine
from .calibration_repository import calibration_repository


class CalibrationRunner:
    """
    Orchestrates calibration runs.
    
    Manages:
    - Run lifecycle
    - Progress tracking
    - Result storage
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
        
        self._current_run: Optional[CalibrationRun] = None
        self._initialized = True
        print("[CalibrationRunner] Initialized (PHASE 2.1)")
    
    def start_run(
        self,
        config: Optional[CalibrationConfig] = None
    ) -> CalibrationRun:
        """
        Start new calibration run.
        """
        
        cfg = config or CalibrationConfig()
        
        run = CalibrationRun(
            run_id=f"cal_{uuid.uuid4().hex[:12]}",
            status=CalibrationStatus.RUNNING,
            config=cfg,
            started_at=int(time.time() * 1000)
        )
        
        self._current_run = run
        calibration_repository.save_run(run)
        
        try:
            # Run calibration
            def progress_callback(progress: float):
                run.progress = progress
                calibration_repository.update_run_status(
                    run.run_id,
                    CalibrationStatus.RUNNING,
                    progress
                )
            
            matrix = calibration_engine.build_matrix(cfg, progress_callback)
            
            # Complete run
            run.matrix = matrix
            run.status = CalibrationStatus.COMPLETED
            run.completed_at = int(time.time() * 1000)
            run.duration_ms = run.completed_at - run.started_at
            run.progress = 100.0
            
            # Save results
            calibration_repository.save_run(run)
            calibration_repository.save_matrix(matrix)
            
        except Exception as e:
            run.status = CalibrationStatus.FAILED
            run.error = str(e)
            run.completed_at = int(time.time() * 1000)
            calibration_repository.save_run(run)
        
        self._current_run = None
        return run
    
    def get_current_run(self) -> Optional[CalibrationRun]:
        """Get currently running calibration"""
        return self._current_run
    
    def get_run(self, run_id: str) -> Optional[CalibrationRun]:
        """Get run by ID"""
        return calibration_repository.get_run(run_id)
    
    def get_latest_run(self) -> Optional[CalibrationRun]:
        """Get most recent run"""
        return calibration_repository.get_latest_run()
    
    def get_runs(self, limit: int = 20) -> List[CalibrationRun]:
        """Get recent runs"""
        return calibration_repository.get_runs(limit)
    
    def get_matrix(self) -> Optional[CalibrationMatrix]:
        """Get latest calibration matrix"""
        return calibration_repository.get_latest_matrix()
    
    def get_result(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific calibration result"""
        result = calibration_repository.get_result(strategy, symbol, timeframe, regime)
        return result.to_dict() if result else None
    
    def get_results_by_strategy(self, strategy: str) -> List[Dict[str, Any]]:
        """Get all results for a strategy"""
        results = calibration_repository.get_results_by_strategy(strategy)
        return [r.to_dict() for r in results]
    
    def get_results_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all results for a symbol"""
        results = calibration_repository.get_results_by_symbol(symbol)
        return [r.to_dict() for r in results]
    
    def get_strategy_summary(self, strategy: str) -> Dict[str, Any]:
        """Get summary for strategy"""
        matrix = self.get_matrix()
        if not matrix:
            return {"strategy": strategy, "hasData": False}
        return calibration_engine.get_strategy_summary(strategy, matrix)
    
    def get_top_performers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing combinations"""
        results = calibration_repository.get_top_performers(limit)
        return [r.to_dict() for r in results]
    
    def get_worst_performers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get worst performing combinations"""
        results = calibration_repository.get_worst_performers(limit)
        return [r.to_dict() for r in results]
    
    def get_health(self) -> Dict[str, Any]:
        """Get runner health"""
        latest = self.get_latest_run()
        matrix = self.get_matrix()
        
        return {
            "module": "PHASE 2.1 Calibration Matrix",
            "status": "healthy",
            "version": "1.0.0",
            "isRunning": self._current_run is not None,
            "latestRunId": latest.run_id if latest else None,
            "latestRunStatus": latest.status.value if latest else None,
            "hasMatrix": matrix is not None,
            "matrixSize": matrix.total_combinations if matrix else 0,
            "validCombinations": matrix.valid_combinations if matrix else 0,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
calibration_runner = CalibrationRunner()
