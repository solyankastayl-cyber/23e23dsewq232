"""
OPS2 Lifecycle Service
======================

Main service for position lifecycle management.
"""

import os
import time
import threading
from typing import Dict, List, Optional, Any

from .lifecycle_types import (
    PositionLifecycle,
    LifecycleEvent,
    LifecyclePhase,
    LifecycleStats
)
from .lifecycle_builder import lifecycle_builder

# MongoDB connection
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[LifecycleService] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class LifecycleService:
    """
    Main service for OPS2 Position Lifecycle.
    
    Provides:
    - Build lifecycle from Event Ledger
    - Timeline queries
    - MAE/MFE analytics
    - Lifecycle by strategy/symbol
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
        
        # Cache for built lifecycles
        self._lifecycle_cache: Dict[str, PositionLifecycle] = {}
        
        self._initialized = True
        print("[LifecycleService] Initialized (OPS2)")
    
    # ===========================================
    # Build Lifecycle
    # ===========================================
    
    def get_lifecycle(self, position_id: str) -> Optional[PositionLifecycle]:
        """
        Get lifecycle for a position.
        
        Builds from Event Ledger if not cached.
        """
        
        # Check cache
        if position_id in self._lifecycle_cache:
            return self._lifecycle_cache[position_id]
        
        # Fetch events from ledger
        events = self._fetch_position_events(position_id)
        
        if not events:
            return None
        
        # Build lifecycle
        lifecycle = lifecycle_builder.build(position_id, events)
        
        # Cache
        self._lifecycle_cache[position_id] = lifecycle
        
        return lifecycle
    
    def rebuild_lifecycle(self, position_id: str) -> Optional[PositionLifecycle]:
        """
        Force rebuild lifecycle from Event Ledger.
        """
        
        # Clear cache
        self._lifecycle_cache.pop(position_id, None)
        
        return self.get_lifecycle(position_id)
    
    def _fetch_position_events(self, position_id: str) -> List[Dict]:
        """Fetch events for position from Event Ledger"""
        
        if not MONGO_AVAILABLE:
            return []
        
        try:
            # Query event_ledger for position events
            cursor = db.event_ledger.find({
                "$or": [
                    {"aggregate_id": position_id},
                    {"payload.position_id": position_id},
                    {"payload.positionId": position_id}
                ]
            }).sort("created_at", 1)
            
            return list(cursor)
        except Exception as e:
            print(f"[LifecycleService] Fetch events error: {e}")
            return []
    
    # ===========================================
    # Timeline
    # ===========================================
    
    def get_timeline(self, position_id: str) -> List[Dict]:
        """
        Get simplified timeline for position.
        """
        
        lifecycle = self.get_lifecycle(position_id)
        
        if not lifecycle:
            return []
        
        return lifecycle.get_timeline()
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_stats(self, position_id: str) -> Optional[LifecycleStats]:
        """
        Get lifecycle statistics for position.
        """
        
        lifecycle = self.get_lifecycle(position_id)
        
        if not lifecycle:
            return None
        
        return lifecycle.stats
    
    def get_mae_mfe(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Get MAE/MFE for position.
        """
        
        stats = self.get_stats(position_id)
        
        if not stats:
            return None
        
        return {
            "mae": stats.mae,
            "maePct": stats.mae_pct,
            "maeTimestamp": stats.mae_timestamp,
            "mfe": stats.mfe,
            "mfePct": stats.mfe_pct,
            "mfeTimestamp": stats.mfe_timestamp,
            "captureEfficiency": stats.capture_efficiency
        }
    
    # ===========================================
    # Queries
    # ===========================================
    
    def get_lifecycles_by_symbol(
        self,
        symbol: str,
        limit: int = 50
    ) -> List[PositionLifecycle]:
        """
        Get lifecycles for a symbol.
        """
        
        position_ids = self._find_positions_by_filter(
            {"symbol": symbol.upper()},
            limit
        )
        
        return [
            lc for lc in [self.get_lifecycle(pid) for pid in position_ids]
            if lc is not None
        ]
    
    def get_lifecycles_by_strategy(
        self,
        strategy_id: str,
        limit: int = 50
    ) -> List[PositionLifecycle]:
        """
        Get lifecycles for a strategy.
        """
        
        position_ids = self._find_positions_by_filter(
            {"$or": [
                {"payload.strategy_id": strategy_id},
                {"payload.strategyId": strategy_id}
            ]},
            limit
        )
        
        return [
            lc for lc in [self.get_lifecycle(pid) for pid in position_ids]
            if lc is not None
        ]
    
    def get_recent_lifecycles(self, limit: int = 20) -> List[PositionLifecycle]:
        """
        Get most recent lifecycles.
        """
        
        position_ids = self._get_recent_position_ids(limit)
        
        return [
            lc for lc in [self.get_lifecycle(pid) for pid in position_ids]
            if lc is not None
        ]
    
    def _find_positions_by_filter(
        self,
        filter_query: Dict,
        limit: int
    ) -> List[str]:
        """Find position IDs by filter"""
        
        if not MONGO_AVAILABLE:
            return []
        
        try:
            # Find POSITION_OPENED events matching filter
            base_query = {
                "event_type": "POSITION_OPENED",
                **filter_query
            }
            
            cursor = db.event_ledger.find(
                base_query,
                {"aggregate_id": 1}
            ).sort("created_at", DESCENDING).limit(limit)
            
            return [doc["aggregate_id"] for doc in cursor]
        except Exception as e:
            print(f"[LifecycleService] Find positions error: {e}")
            return []
    
    def _get_recent_position_ids(self, limit: int) -> List[str]:
        """Get recent position IDs"""
        
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.event_ledger.find(
                {"event_type": "POSITION_OPENED"},
                {"aggregate_id": 1}
            ).sort("created_at", DESCENDING).limit(limit)
            
            return [doc["aggregate_id"] for doc in cursor]
        except Exception as e:
            print(f"[LifecycleService] Get recent error: {e}")
            return []
    
    # ===========================================
    # Analytics
    # ===========================================
    
    def get_lifecycle_summary(self) -> Dict[str, Any]:
        """
        Get summary of all lifecycles.
        """
        
        recent = self.get_recent_lifecycles(50)
        
        total_mae = 0.0
        total_mfe = 0.0
        total_pnl = 0.0
        closed_count = 0
        avg_duration = 0.0
        avg_efficiency = 0.0
        
        by_phase = {}
        
        for lc in recent:
            # Phase distribution
            phase = lc.current_phase.value
            if phase not in by_phase:
                by_phase[phase] = 0
            by_phase[phase] += 1
            
            # Stats
            if lc.stats:
                total_mae += lc.stats.mae
                total_mfe += lc.stats.mfe
                total_pnl += lc.stats.realized_pnl
                avg_duration += lc.stats.total_duration_minutes
                
                if lc.is_closed:
                    closed_count += 1
                    avg_efficiency += lc.stats.capture_efficiency
        
        n = len(recent) or 1
        
        return {
            "totalLifecycles": len(recent),
            "closedLifecycles": closed_count,
            "byPhase": by_phase,
            "avgMae": round(total_mae / n, 2),
            "avgMfe": round(total_mfe / n, 2),
            "avgPnl": round(total_pnl / n, 2),
            "avgDurationMinutes": round(avg_duration / n, 1),
            "avgCaptureEfficiency": round(avg_efficiency / closed_count, 4) if closed_count else 0,
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        
        return {
            "module": "OPS2 Position Lifecycle",
            "status": "healthy",
            "cachedLifecycles": len(self._lifecycle_cache),
            "mongoAvailable": MONGO_AVAILABLE,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
lifecycle_service = LifecycleService()
