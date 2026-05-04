"""
PHASE 7 - Correlation Repository
==================================
MongoDB storage for correlation analysis data.

Collections:
- correlation_matrices: Full correlation matrices
- rolling_correlations: Time series of rolling correlations
- lead_lag_results: Lead/lag detection results
- correlation_regimes: Market regime classifications
- cross_asset_signals: Generated trading signals
- correlation_history: Historical correlation snapshots
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, DESCENDING

from .correlation_types import (
    CorrelationValue, RollingCorrelation, LeadLagResult,
    RegimeState, CrossAssetSignal, CorrelationRegime
)


class CorrelationRepository:
    """
    MongoDB repository for correlation intelligence data.
    """
    
    def __init__(self):
        self.mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = os.environ.get("DB_NAME", "ta_engine")
        self.client = None
        self.db = None
        
        # Collection names
        self.collections = {
            "matrices": "correlation_matrices",
            "rolling": "rolling_correlations",
            "lead_lag": "lead_lag_results",
            "regimes": "correlation_regimes",
            "signals": "cross_asset_signals",
            "history": "correlation_history"
        }
    
    def _get_db(self):
        """Get MongoDB database connection."""
        if self.db is None:
            self.client = MongoClient(self.mongo_url)
            self.db = self.client[self.db_name]
        return self.db
    
    def _serialize_for_mongo(self, data: Any) -> Any:
        """Convert data for MongoDB storage (handle enums, datetimes)."""
        if hasattr(data, 'to_dict'):
            return data.to_dict()
        elif hasattr(data, 'value'):
            return data.value
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._serialize_for_mongo(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_mongo(item) for item in data]
        return data
    
    # ===== Correlation Matrix =====
    
    def save_correlation_matrix(
        self,
        matrix: Dict[str, CorrelationValue],
        symbol: str = "MULTI",
        timeframe: str = "4h"
    ) -> str:
        """Save correlation matrix to MongoDB."""
        db = self._get_db()
        
        doc = {
            "symbol": symbol,
            "timeframe": timeframe,
            "matrix": {k: self._serialize_for_mongo(v) for k, v in matrix.items()},
            "pair_count": len(matrix),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["matrices"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_matrix(
        self,
        symbol: str = "MULTI",
        timeframe: str = "4h"
    ) -> Optional[Dict]:
        """Get most recent correlation matrix."""
        db = self._get_db()
        
        doc = db[self.collections["matrices"]].find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    def get_matrix_history(
        self,
        symbol: str = "MULTI",
        timeframe: str = "4h",
        limit: int = 50
    ) -> List[Dict]:
        """Get historical correlation matrices."""
        db = self._get_db()
        
        cursor = db[self.collections["matrices"]].find(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Rolling Correlations =====
    
    def save_rolling_correlation(
        self,
        rolling: RollingCorrelation,
        symbol: str = "MULTI",
        timeframe: str = "4h"
    ) -> str:
        """Save rolling correlation data."""
        db = self._get_db()
        
        doc = {
            "symbol": symbol,
            "timeframe": timeframe,
            "pair_id": rolling.pair.pair_id,
            "data": self._serialize_for_mongo(rolling),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["rolling"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_rolling_correlation(
        self,
        pair_id: str,
        timeframe: str = "4h"
    ) -> Optional[Dict]:
        """Get latest rolling correlation for a pair."""
        db = self._get_db()
        
        doc = db[self.collections["rolling"]].find_one(
            {"pair_id": pair_id, "timeframe": timeframe},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    # ===== Lead/Lag Results =====
    
    def save_lead_lag_result(
        self,
        result: LeadLagResult,
        symbol: str = "MULTI",
        timeframe: str = "4h"
    ) -> str:
        """Save lead/lag detection result."""
        db = self._get_db()
        
        doc = {
            "symbol": symbol,
            "timeframe": timeframe,
            "pair_id": result.pair.pair_id,
            "leader": result.leader,
            "follower": result.follower,
            "lag_candles": result.lag_candles,
            "data": self._serialize_for_mongo(result),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result_id = db[self.collections["lead_lag"]].insert_one(doc)
        return str(result_id.inserted_id)
    
    def get_lead_lag_results(
        self,
        timeframe: str = "4h",
        limit: int = 20
    ) -> List[Dict]:
        """Get recent lead/lag results."""
        db = self._get_db()
        
        cursor = db[self.collections["lead_lag"]].find(
            {"timeframe": timeframe},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_lead_lag_by_pair(
        self,
        pair_id: str,
        timeframe: str = "4h"
    ) -> Optional[Dict]:
        """Get latest lead/lag result for specific pair."""
        db = self._get_db()
        
        doc = db[self.collections["lead_lag"]].find_one(
            {"pair_id": pair_id, "timeframe": timeframe},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    # ===== Regime Classifications =====
    
    def save_regime(
        self,
        regime: RegimeState,
        timeframe: str = "4h"
    ) -> str:
        """Save regime classification."""
        db = self._get_db()
        
        doc = {
            "timeframe": timeframe,
            "regime": regime.regime.value if hasattr(regime.regime, 'value') else regime.regime,
            "confidence": regime.confidence,
            "data": self._serialize_for_mongo(regime),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["regimes"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_current_regime(
        self,
        timeframe: str = "4h"
    ) -> Optional[Dict]:
        """Get most recent regime classification."""
        db = self._get_db()
        
        doc = db[self.collections["regimes"]].find_one(
            {"timeframe": timeframe},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    def get_regime_history(
        self,
        timeframe: str = "4h",
        limit: int = 100,
        hours_back: int = 168  # 1 week
    ) -> List[Dict]:
        """Get regime history."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        cursor = db[self.collections["regimes"]].find(
            {
                "timeframe": timeframe,
                "created_at": {"$gte": cutoff}
            },
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_regime_stats(
        self,
        timeframe: str = "4h",
        hours_back: int = 168
    ) -> Dict:
        """Get regime distribution statistics."""
        history = self.get_regime_history(timeframe, limit=500, hours_back=hours_back)
        
        if not history:
            return {"total": 0}
        
        regime_counts = {}
        for entry in history:
            regime = entry.get("regime", "UNKNOWN")
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        total = sum(regime_counts.values())
        regime_pct = {k: round(v / total * 100, 1) for k, v in regime_counts.items()}
        
        return {
            "total": total,
            "counts": regime_counts,
            "percentages": regime_pct,
            "most_common": max(regime_counts.keys(), key=lambda k: regime_counts[k]) if regime_counts else None
        }
    
    # ===== Cross Asset Signals =====
    
    def save_signal(
        self,
        signal: CrossAssetSignal
    ) -> str:
        """Save cross-asset signal."""
        db = self._get_db()
        
        doc = {
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "trigger_asset": signal.trigger_asset,
            "target_asset": signal.target_asset,
            "direction": signal.direction,
            "strength": signal.strength,
            "data": self._serialize_for_mongo(signal),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["signals"]].insert_one(doc)
        return str(result.inserted_id)
    
    def save_signals_batch(
        self,
        signals: List[CrossAssetSignal]
    ) -> int:
        """Save multiple signals at once."""
        if not signals:
            return 0
        
        db = self._get_db()
        
        docs = []
        for signal in signals:
            docs.append({
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "trigger_asset": signal.trigger_asset,
                "target_asset": signal.target_asset,
                "direction": signal.direction,
                "strength": signal.strength,
                "data": self._serialize_for_mongo(signal),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        result = db[self.collections["signals"]].insert_many(docs)
        return len(result.inserted_ids)
    
    def get_active_signals(
        self,
        target_asset: str = None,
        signal_type: str = None,
        min_strength: float = 0.3,
        hours_back: int = 24
    ) -> List[Dict]:
        """Get active (recent) signals."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        query = {
            "created_at": {"$gte": cutoff},
            "strength": {"$gte": min_strength}
        }
        
        if target_asset:
            query["target_asset"] = target_asset
        
        if signal_type:
            query["signal_type"] = signal_type
        
        cursor = db[self.collections["signals"]].find(
            query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(100)
        
        return list(cursor)
    
    def get_signal_history(
        self,
        target_asset: str = "BTC",
        limit: int = 50
    ) -> List[Dict]:
        """Get signal history for an asset."""
        db = self._get_db()
        
        cursor = db[self.collections["signals"]].find(
            {"target_asset": target_asset},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Correlation History =====
    
    def save_correlation_snapshot(
        self,
        pair_id: str,
        correlation: float,
        timeframe: str = "4h"
    ) -> str:
        """Save single correlation value for historical tracking."""
        db = self._get_db()
        
        doc = {
            "pair_id": pair_id,
            "timeframe": timeframe,
            "correlation": correlation,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["history"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_correlation_timeseries(
        self,
        pair_id: str,
        timeframe: str = "4h",
        hours_back: int = 168
    ) -> List[Dict]:
        """Get correlation time series for a pair."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        cursor = db[self.collections["history"]].find(
            {
                "pair_id": pair_id,
                "timeframe": timeframe,
                "created_at": {"$gte": cutoff}
            },
            {"_id": 0}
        ).sort("created_at", DESCENDING)
        
        return list(cursor)
    
    # ===== Cleanup =====
    
    def cleanup_old_data(
        self,
        days_to_keep: int = 30
    ) -> Dict[str, int]:
        """Remove data older than specified days."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).isoformat()
        
        deleted = {}
        for name, collection in self.collections.items():
            result = db[collection].delete_many({"created_at": {"$lt": cutoff}})
            deleted[name] = result.deleted_count
        
        return deleted
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        db = self._get_db()
        
        stats = {}
        for name, collection in self.collections.items():
            count = db[collection].count_documents({})
            stats[name] = count
        
        return {
            "collections": stats,
            "total_documents": sum(stats.values())
        }
