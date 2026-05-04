"""
Failure Repository
==================

Storage for failure scan results (PHASE 2.2)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .failure_types import (
    FailureScan,
    FailureSummary,
    FalseSignal,
    RegimeMismatch,
    StrategyDegradation,
    SelectionError
)


class FailureRepository:
    """
    In-memory repository for failure scan results.
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
        
        self._scans: Dict[str, FailureScan] = {}
        self._latest_scan: Optional[FailureScan] = None
        
        self._initialized = True
        print("[FailureRepository] Initialized (PHASE 2.2)")
    
    # ==========================================
    # Scan Management
    # ==========================================
    
    def save_scan(self, scan: FailureScan) -> None:
        """Save failure scan"""
        self._scans[scan.scan_id] = scan
        self._latest_scan = scan
        
        # Keep only last 50 scans
        if len(self._scans) > 50:
            oldest = sorted(self._scans.keys())[0]
            del self._scans[oldest]
    
    def get_scan(self, scan_id: str) -> Optional[FailureScan]:
        """Get scan by ID"""
        return self._scans.get(scan_id)
    
    def get_latest_scan(self) -> Optional[FailureScan]:
        """Get most recent scan"""
        return self._latest_scan
    
    def get_scans(self, limit: int = 20) -> List[FailureScan]:
        """Get recent scans"""
        scans = list(self._scans.values())
        scans.sort(key=lambda x: x.completed_at, reverse=True)
        return scans[:limit]
    
    # ==========================================
    # Query Methods
    # ==========================================
    
    def get_false_signals(
        self,
        strategy: str = None,
        symbol: str = None,
        regime: str = None,
        limit: int = 50
    ) -> List[FalseSignal]:
        """Get false signals with optional filters"""
        if not self._latest_scan:
            return []
        
        signals = self._latest_scan.false_signals
        
        if strategy:
            signals = [s for s in signals if s.strategy == strategy.upper()]
        if symbol:
            signals = [s for s in signals if s.symbol == symbol.upper()]
        if regime:
            signals = [s for s in signals if s.regime == regime.upper()]
        
        return signals[:limit]
    
    def get_regime_mismatches(
        self,
        strategy: str = None,
        limit: int = 50
    ) -> List[RegimeMismatch]:
        """Get regime mismatches"""
        if not self._latest_scan:
            return []
        
        mismatches = self._latest_scan.regime_mismatches
        
        if strategy:
            mismatches = [m for m in mismatches if m.strategy == strategy.upper()]
        
        return mismatches[:limit]
    
    def get_degradations(
        self,
        strategy: str = None,
        limit: int = 20
    ) -> List[StrategyDegradation]:
        """Get degradation events"""
        if not self._latest_scan:
            return []
        
        degradations = self._latest_scan.degradations
        
        if strategy:
            degradations = [d for d in degradations if d.strategy == strategy.upper()]
        
        return degradations[:limit]
    
    def get_selection_errors(
        self,
        regime: str = None,
        limit: int = 50
    ) -> List[SelectionError]:
        """Get selection errors"""
        if not self._latest_scan:
            return []
        
        errors = self._latest_scan.selection_errors
        
        if regime:
            errors = [e for e in errors if e.regime == regime.upper()]
        
        return errors[:limit]
    
    def get_strategy_summary(self, strategy: str) -> Optional[FailureSummary]:
        """Get failure summary for strategy"""
        if not self._latest_scan:
            return None
        
        return self._latest_scan.strategy_summaries.get(strategy.upper())
    
    # ==========================================
    # Stats
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        if not self._latest_scan:
            return {
                "hasScan": False,
                "totalScans": len(self._scans)
            }
        
        return {
            "hasScan": True,
            "totalScans": len(self._scans),
            "latestScanId": self._latest_scan.scan_id,
            "totalFailures": self._latest_scan.total_failures,
            "byType": self._latest_scan.failure_by_type,
            "bySeverity": self._latest_scan.failure_by_severity
        }
    
    def clear(self) -> None:
        """Clear all data"""
        self._scans.clear()
        self._latest_scan = None


# Global singleton
failure_repository = FailureRepository()
