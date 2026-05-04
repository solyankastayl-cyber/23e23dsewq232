"""
Metrics Store Service (S1.4D Complete)
======================================

Persists metrics snapshots to MongoDB.

Collections:
- simulation_metrics: Stores MetricsSnapshot for each completed run

When metrics are saved:
- After simulation STOP
- calculate_metrics() → persist_snapshot()

API reads from store (no recalculation):
- GET /api/trading/simulation/runs/{runId}/metrics
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading
import os

from .risk_types import MetricsSnapshot


class MetricsStoreService:
    """
    Service for persisting metrics to MongoDB.
    
    Thread-safe singleton.
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
        
        # In-memory cache
        self._cache: Dict[str, MetricsSnapshot] = {}
        
        # MongoDB client (lazy init)
        self._db = None
        self._collection = None
        
        self._initialized = True
        print("[MetricsStoreService] Initialized")
    
    def _get_collection(self):
        """Get MongoDB collection (lazy init)"""
        if self._collection is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._collection = self._db["simulation_metrics"]
                
                # Create indexes
                self._collection.create_index("run_id", unique=True)
                self._collection.create_index("strategy_id")
                self._collection.create_index("experiment_id")
                self._collection.create_index("calculated_at")
                
                print("[MetricsStoreService] MongoDB connected")
            except Exception as e:
                print(f"[MetricsStoreService] MongoDB connection failed: {e}")
                return None
        
        return self._collection
    
    # ===========================================
    # Save Metrics
    # ===========================================
    
    def save_snapshot(
        self,
        snapshot: MetricsSnapshot,
        strategy_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        experiment_id: Optional[str] = None
    ) -> bool:
        """
        Save metrics snapshot to store.
        
        Args:
            snapshot: MetricsSnapshot to save
            strategy_id: Associated strategy
            dataset_id: Associated dataset
            experiment_id: Associated experiment (if part of research)
            
        Returns:
            Success status
        """
        # Build document
        doc = {
            "run_id": snapshot.run_id,
            "strategy_id": strategy_id,
            "dataset_id": dataset_id,
            "experiment_id": experiment_id,
            
            # Performance Metrics
            "performance": {
                "total_return_pct": snapshot.total_return_pct,
                "annual_return_pct": snapshot.annual_return_pct,
                "sharpe_ratio": snapshot.sharpe_ratio,
                "sortino_ratio": snapshot.sortino_ratio,
                "profit_factor": snapshot.profit_factor,
                "expectancy": snapshot.expectancy,
                "avg_trade_return": snapshot.avg_trade_return,
                "volatility_annual": snapshot.volatility_annual
            },
            
            # Risk Metrics
            "risk": {
                "max_drawdown_pct": snapshot.max_drawdown_pct,
                "avg_drawdown_pct": snapshot.avg_drawdown_pct,
                "max_drawdown_duration_bars": snapshot.max_drawdown_duration_bars,
                "recovery_factor": snapshot.recovery_factor,
                "calmar_ratio": snapshot.calmar_ratio
            },
            
            # Trade Stats
            "trade_stats": {
                "trades_count": snapshot.trades_count,
                "winning_trades": snapshot.winning_trades,
                "losing_trades": snapshot.losing_trades,
                "win_rate": snapshot.win_rate
            },
            
            # Capital
            "capital": {
                "initial_capital_usd": snapshot.initial_capital_usd,
                "final_equity_usd": snapshot.final_equity_usd,
                "net_profit_usd": snapshot.net_profit_usd,
                "trading_days": snapshot.trading_days
            },
            
            # Metadata
            "is_valid": snapshot.is_valid,
            "validation_message": snapshot.validation_message,
            "calculated_at": snapshot.calculated_at or datetime.now(timezone.utc).isoformat(),
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Cache
        self._cache[snapshot.run_id] = snapshot
        
        # Persist to MongoDB
        collection = self._get_collection()
        if collection is not None:
            try:
                collection.replace_one(
                    {"run_id": snapshot.run_id},
                    doc,
                    upsert=True
                )
                print(f"[MetricsStore] Saved snapshot for run: {snapshot.run_id}")
                return True
            except Exception as e:
                print(f"[MetricsStore] Save failed: {e}")
                return False
        
        return True  # Cached only
    
    # ===========================================
    # Get Metrics
    # ===========================================
    
    def get_snapshot(self, run_id: str) -> Optional[MetricsSnapshot]:
        """
        Get metrics snapshot by run ID.
        
        Checks cache first, then MongoDB.
        """
        # Check cache
        if run_id in self._cache:
            return self._cache[run_id]
        
        # Query MongoDB
        collection = self._get_collection()
        if collection is not None:
            try:
                doc = collection.find_one({"run_id": run_id}, {"_id": 0})
                if doc:
                    snapshot = self._doc_to_snapshot(doc)
                    self._cache[run_id] = snapshot
                    return snapshot
            except Exception as e:
                print(f"[MetricsStore] Query failed: {e}")
        
        return None
    
    def get_snapshots_by_experiment(
        self,
        experiment_id: str
    ) -> List[MetricsSnapshot]:
        """
        Get all snapshots for an experiment.
        """
        snapshots = []
        
        collection = self._get_collection()
        if collection is not None:
            try:
                cursor = collection.find(
                    {"experiment_id": experiment_id},
                    {"_id": 0}
                )
                for doc in cursor:
                    snapshot = self._doc_to_snapshot(doc)
                    snapshots.append(snapshot)
            except Exception as e:
                print(f"[MetricsStore] Query failed: {e}")
        
        return snapshots
    
    def get_snapshots_by_strategy(
        self,
        strategy_id: str,
        limit: int = 100
    ) -> List[MetricsSnapshot]:
        """
        Get recent snapshots for a strategy.
        """
        snapshots = []
        
        collection = self._get_collection()
        if collection is not None:
            try:
                cursor = collection.find(
                    {"strategy_id": strategy_id},
                    {"_id": 0}
                ).sort("calculated_at", -1).limit(limit)
                
                for doc in cursor:
                    snapshot = self._doc_to_snapshot(doc)
                    snapshots.append(snapshot)
            except Exception as e:
                print(f"[MetricsStore] Query failed: {e}")
        
        return snapshots
    
    # ===========================================
    # List / Query
    # ===========================================
    
    def list_snapshots(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent snapshots (summary view).
        """
        results = []
        
        collection = self._get_collection()
        if collection is not None:
            try:
                cursor = collection.find(
                    {},
                    {
                        "_id": 0,
                        "run_id": 1,
                        "strategy_id": 1,
                        "experiment_id": 1,
                        "performance.sharpe_ratio": 1,
                        "risk.max_drawdown_pct": 1,
                        "trade_stats.trades_count": 1,
                        "is_valid": 1,
                        "calculated_at": 1
                    }
                ).sort("calculated_at", -1).skip(offset).limit(limit)
                
                for doc in cursor:
                    results.append(doc)
            except Exception as e:
                print(f"[MetricsStore] List failed: {e}")
        
        return results
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _doc_to_snapshot(self, doc: Dict[str, Any]) -> MetricsSnapshot:
        """Convert MongoDB document to MetricsSnapshot"""
        perf = doc.get("performance", {})
        risk = doc.get("risk", {})
        trades = doc.get("trade_stats", {})
        capital = doc.get("capital", {})
        
        return MetricsSnapshot(
            run_id=doc.get("run_id", ""),
            
            # Performance
            total_return_pct=perf.get("total_return_pct", 0),
            annual_return_pct=perf.get("annual_return_pct", 0),
            sharpe_ratio=perf.get("sharpe_ratio", 0),
            sortino_ratio=perf.get("sortino_ratio", 0),
            profit_factor=perf.get("profit_factor", 0),
            expectancy=perf.get("expectancy", 0),
            avg_trade_return=perf.get("avg_trade_return", 0),
            volatility_annual=perf.get("volatility_annual", 0),
            
            # Risk
            max_drawdown_pct=risk.get("max_drawdown_pct", 0),
            avg_drawdown_pct=risk.get("avg_drawdown_pct", 0),
            max_drawdown_duration_bars=risk.get("max_drawdown_duration_bars", 0),
            recovery_factor=risk.get("recovery_factor", 0),
            calmar_ratio=risk.get("calmar_ratio", 0),
            
            # Trades
            trades_count=trades.get("trades_count", 0),
            winning_trades=trades.get("winning_trades", 0),
            losing_trades=trades.get("losing_trades", 0),
            win_rate=trades.get("win_rate", 0),
            
            # Capital
            initial_capital_usd=capital.get("initial_capital_usd", 0),
            final_equity_usd=capital.get("final_equity_usd", 0),
            net_profit_usd=capital.get("net_profit_usd", 0),
            trading_days=capital.get("trading_days", 0),
            
            # Metadata
            is_valid=doc.get("is_valid", False),
            validation_message=doc.get("validation_message", ""),
            calculated_at=doc.get("calculated_at", "")
        )
    
    # ===========================================
    # Delete
    # ===========================================
    
    def delete_snapshot(self, run_id: str) -> bool:
        """Delete snapshot by run ID"""
        self._cache.pop(run_id, None)
        
        collection = self._get_collection()
        if collection is not None:
            try:
                result = collection.delete_one({"run_id": run_id})
                return result.deleted_count > 0
            except Exception:
                pass
        
        return True
    
    def delete_by_experiment(self, experiment_id: str) -> int:
        """Delete all snapshots for an experiment"""
        deleted = 0
        
        # Clear cache
        to_remove = [
            k for k, v in self._cache.items()
            if hasattr(v, 'experiment_id') and v.experiment_id == experiment_id
        ]
        for k in to_remove:
            del self._cache[k]
            deleted += 1
        
        collection = self._get_collection()
        if collection is not None:
            try:
                result = collection.delete_many({"experiment_id": experiment_id})
                deleted = result.deleted_count
            except Exception:
                pass
        
        return deleted
    
    def clear_cache(self) -> int:
        """Clear in-memory cache"""
        count = len(self._cache)
        self._cache.clear()
        return count


# Global singleton
metrics_store_service = MetricsStoreService()
