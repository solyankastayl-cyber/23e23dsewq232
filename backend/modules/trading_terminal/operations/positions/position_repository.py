"""
Position Repository
===================

Storage for deep position states.
"""

import os
import time
import threading
from typing import Dict, List, Optional, Any

from .position_types import (
    DeepPositionState,
    PositionOwnership,
    PositionRiskView,
    PositionStatus,
    PositionSummary
)

# MongoDB connection
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[PositionRepository] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class PositionRepository:
    """
    Repository for deep position states.
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
        
        # In-memory cache for fast access
        self._positions: Dict[str, DeepPositionState] = {}
        
        if MONGO_AVAILABLE:
            self._ensure_indexes()
        
        self._initialized = True
        print("[PositionRepository] Initialized")
    
    def _ensure_indexes(self):
        """Create indexes"""
        try:
            db.deep_positions.create_index([("position_id", 1)], unique=True)
            db.deep_positions.create_index([("symbol", 1)])
            db.deep_positions.create_index([("exchange", 1)])
            db.deep_positions.create_index([("status", 1)])
            db.deep_positions.create_index([("ownership.strategy_id", 1)])
            db.deep_positions.create_index([("ownership.profile_id", 1)])
            db.deep_positions.create_index([("opened_at", DESCENDING)])
        except Exception as e:
            print(f"[PositionRepository] Index error: {e}")
    
    # ===========================================
    # Write Operations
    # ===========================================
    
    def save(self, position: DeepPositionState) -> bool:
        """Save or update position"""
        
        # Update cache
        self._positions[position.position_id] = position
        
        if not MONGO_AVAILABLE:
            return True
        
        try:
            doc = self._state_to_doc(position)
            
            db.deep_positions.update_one(
                {"position_id": position.position_id},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[PositionRepository] Save error: {e}")
            return False
    
    def save_batch(self, positions: List[DeepPositionState]) -> int:
        """Save multiple positions"""
        count = 0
        for pos in positions:
            if self.save(pos):
                count += 1
        return count
    
    def delete(self, position_id: str) -> bool:
        """Delete position"""
        
        self._positions.pop(position_id, None)
        
        if not MONGO_AVAILABLE:
            return True
        
        try:
            db.deep_positions.delete_one({"position_id": position_id})
            return True
        except Exception as e:
            print(f"[PositionRepository] Delete error: {e}")
            return False
    
    # ===========================================
    # Read Operations
    # ===========================================
    
    def get(self, position_id: str) -> Optional[DeepPositionState]:
        """Get position by ID"""
        
        # Check cache first
        if position_id in self._positions:
            return self._positions[position_id]
        
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.deep_positions.find_one({"position_id": position_id})
            if doc:
                position = self._doc_to_state(doc)
                self._positions[position_id] = position
                return position
            return None
        except Exception as e:
            print(f"[PositionRepository] Get error: {e}")
            return None
    
    def get_all(self, include_closed: bool = False) -> List[DeepPositionState]:
        """Get all positions"""
        
        if not MONGO_AVAILABLE:
            positions = list(self._positions.values())
            if not include_closed:
                positions = [p for p in positions if p.status != PositionStatus.CLOSED]
            return positions
        
        try:
            query = {} if include_closed else {"status": {"$ne": "CLOSED"}}
            cursor = db.deep_positions.find(query).sort("opened_at", DESCENDING)
            
            positions = []
            for doc in cursor:
                pos = self._doc_to_state(doc)
                self._positions[pos.position_id] = pos
                positions.append(pos)
            
            return positions
        except Exception as e:
            print(f"[PositionRepository] Get all error: {e}")
            return list(self._positions.values())
    
    def get_by_symbol(self, symbol: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by symbol"""
        
        if not MONGO_AVAILABLE:
            return [p for p in self._positions.values() 
                    if p.symbol == symbol and (include_closed or p.status != PositionStatus.CLOSED)]
        
        try:
            query = {"symbol": symbol.upper()}
            if not include_closed:
                query["status"] = {"$ne": "CLOSED"}
            
            cursor = db.deep_positions.find(query).sort("opened_at", DESCENDING)
            return [self._doc_to_state(doc) for doc in cursor]
        except Exception as e:
            print(f"[PositionRepository] Get by symbol error: {e}")
            return []
    
    def get_by_exchange(self, exchange: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by exchange"""
        
        if not MONGO_AVAILABLE:
            return [p for p in self._positions.values()
                    if p.exchange == exchange and (include_closed or p.status != PositionStatus.CLOSED)]
        
        try:
            query = {"exchange": exchange.upper()}
            if not include_closed:
                query["status"] = {"$ne": "CLOSED"}
            
            cursor = db.deep_positions.find(query).sort("opened_at", DESCENDING)
            return [self._doc_to_state(doc) for doc in cursor]
        except Exception as e:
            print(f"[PositionRepository] Get by exchange error: {e}")
            return []
    
    def get_by_strategy(self, strategy_id: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by strategy"""
        
        if not MONGO_AVAILABLE:
            return [p for p in self._positions.values()
                    if p.ownership and p.ownership.strategy_id == strategy_id
                    and (include_closed or p.status != PositionStatus.CLOSED)]
        
        try:
            query = {"ownership.strategy_id": strategy_id}
            if not include_closed:
                query["status"] = {"$ne": "CLOSED"}
            
            cursor = db.deep_positions.find(query).sort("opened_at", DESCENDING)
            return [self._doc_to_state(doc) for doc in cursor]
        except Exception as e:
            print(f"[PositionRepository] Get by strategy error: {e}")
            return []
    
    def get_by_profile(self, profile_id: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by profile"""
        
        if not MONGO_AVAILABLE:
            return [p for p in self._positions.values()
                    if p.ownership and p.ownership.profile_id == profile_id
                    and (include_closed or p.status != PositionStatus.CLOSED)]
        
        try:
            query = {"ownership.profile_id": profile_id}
            if not include_closed:
                query["status"] = {"$ne": "CLOSED"}
            
            cursor = db.deep_positions.find(query).sort("opened_at", DESCENDING)
            return [self._doc_to_state(doc) for doc in cursor]
        except Exception as e:
            print(f"[PositionRepository] Get by profile error: {e}")
            return []
    
    def get_by_status(self, status: str) -> List[DeepPositionState]:
        """Get positions by status"""
        
        if not MONGO_AVAILABLE:
            return [p for p in self._positions.values() if p.status.value == status]
        
        try:
            cursor = db.deep_positions.find({"status": status}).sort("opened_at", DESCENDING)
            return [self._doc_to_state(doc) for doc in cursor]
        except Exception as e:
            print(f"[PositionRepository] Get by status error: {e}")
            return []
    
    def get_open_count(self) -> int:
        """Get count of open positions"""
        if not MONGO_AVAILABLE:
            return len([p for p in self._positions.values() if p.status != PositionStatus.CLOSED])
        
        try:
            return db.deep_positions.count_documents({"status": {"$ne": "CLOSED"}})
        except:
            return 0
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _state_to_doc(self, state: DeepPositionState) -> Dict:
        """Convert state to MongoDB document"""
        return {
            "position_id": state.position_id,
            "exchange": state.exchange,
            "symbol": state.symbol,
            "side": state.side,
            "quantity": state.quantity,
            "entry_price": state.entry_price,
            "mark_price": state.mark_price,
            "avg_price": state.avg_price,
            "unrealized_pnl": state.unrealized_pnl,
            "realized_pnl": state.realized_pnl,
            "total_pnl": state.total_pnl,
            "pnl_pct": state.pnl_pct,
            "leverage": state.leverage,
            "margin_mode": state.margin_mode,
            "margin_used": state.margin_used,
            "ownership": state.ownership.to_dict() if state.ownership else None,
            "status": state.status.value,
            "opened_at": state.opened_at,
            "updated_at": state.updated_at,
            "closed_at": state.closed_at,
            "age_minutes": state.age_minutes,
            "scale_count": state.scale_count,
            "reduce_count": state.reduce_count,
            "last_scaled_at": state.last_scaled_at,
            "last_reduced_at": state.last_reduced_at,
            "risk_view": state.risk_view.to_dict() if state.risk_view else None,
            "stop_loss": state.stop_loss,
            "take_profit": state.take_profit,
            "last_event_id": state.last_event_id,
            "event_count": state.event_count,
            "tags": state.tags
        }
    
    def _doc_to_state(self, doc: Dict) -> DeepPositionState:
        """Convert MongoDB document to state"""
        from .position_types import RiskLevel
        
        # Parse ownership
        ownership = None
        if doc.get("ownership"):
            o = doc["ownership"]
            ownership = PositionOwnership(
                position_id=o.get("positionId", ""),
                strategy_id=o.get("strategyId"),
                strategy_name=o.get("strategyName"),
                profile_id=o.get("profileId"),
                profile_name=o.get("profileName"),
                config_id=o.get("configId"),
                config_version=o.get("configVersion"),
                decision_trace_id=o.get("decisionTraceId"),
                signal_id=o.get("signalId"),
                assigned_at=o.get("assignedAt", 0)
            )
        
        # Parse risk view
        risk_view = None
        if doc.get("risk_view"):
            r = doc["risk_view"]
            risk_view = PositionRiskView(
                position_id=r.get("positionId", ""),
                exposure_usd=r.get("exposureUsd", 0),
                exposure_pct=r.get("exposurePct", 0),
                risk_per_trade=r.get("riskPerTrade"),
                max_loss_usd=r.get("maxLossUsd"),
                distance_to_stop_pct=r.get("distanceToStopPct"),
                distance_to_take_profit_pct=r.get("distanceToTakeProfitPct"),
                liquidation_price=r.get("liquidationPrice"),
                liquidation_distance_pct=r.get("liquidationDistancePct"),
                risk_level=RiskLevel(r.get("riskLevel", "MODERATE")),
                risk_factors=r.get("riskFactors", [])
            )
        
        return DeepPositionState(
            position_id=doc.get("position_id", ""),
            exchange=doc.get("exchange", ""),
            symbol=doc.get("symbol", ""),
            side=doc.get("side", "LONG"),
            quantity=doc.get("quantity", 0),
            entry_price=doc.get("entry_price", 0),
            mark_price=doc.get("mark_price", 0),
            avg_price=doc.get("avg_price", 0),
            unrealized_pnl=doc.get("unrealized_pnl", 0),
            realized_pnl=doc.get("realized_pnl", 0),
            total_pnl=doc.get("total_pnl", 0),
            pnl_pct=doc.get("pnl_pct", 0),
            leverage=doc.get("leverage"),
            margin_mode=doc.get("margin_mode"),
            margin_used=doc.get("margin_used"),
            ownership=ownership,
            status=PositionStatus(doc.get("status", "OPEN")),
            opened_at=doc.get("opened_at", 0),
            updated_at=doc.get("updated_at", 0),
            closed_at=doc.get("closed_at"),
            age_minutes=doc.get("age_minutes", 0),
            scale_count=doc.get("scale_count", 0),
            reduce_count=doc.get("reduce_count", 0),
            last_scaled_at=doc.get("last_scaled_at"),
            last_reduced_at=doc.get("last_reduced_at"),
            risk_view=risk_view,
            stop_loss=doc.get("stop_loss"),
            take_profit=doc.get("take_profit"),
            last_event_id=doc.get("last_event_id"),
            event_count=doc.get("event_count", 0),
            tags=doc.get("tags", [])
        )


# Global repository
position_repository = PositionRepository()
