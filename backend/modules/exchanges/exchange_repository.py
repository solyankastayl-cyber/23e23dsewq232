"""
Exchange Repository - PHASE 5.1
===============================

Persistence layer for exchange data.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .exchange_types import (
    ExchangeId,
    ExchangeConnectionStatus,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeBalance
)


class ExchangeRepository:
    """Repository for exchange data persistence."""
    
    def __init__(self, mongo_uri: Optional[str] = None, db_name: str = "ta_engine"):
        self.mongo_uri = mongo_uri or os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = db_name
        self._client: Optional[MongoClient] = None
        self._db = None
    
    def _get_db(self):
        if self._db is None:
            self._client = MongoClient(self.mongo_uri)
            self._db = self._client[self.db_name]
            self._ensure_indexes()
        return self._db
    
    def _ensure_indexes(self):
        db = self._db
        
        # Connection history
        db.exchange_connections.create_index([("exchange", 1)])
        db.exchange_connections.create_index([("timestamp", DESCENDING)])
        
        # Order history
        db.exchange_orders.create_index([("exchange", 1), ("exchange_order_id", 1)])
        db.exchange_orders.create_index([("symbol", 1)])
        db.exchange_orders.create_index([("created_at", DESCENDING)])
        
        # Position snapshots
        db.exchange_positions.create_index([("exchange", 1), ("symbol", 1)])
        db.exchange_positions.create_index([("timestamp", DESCENDING)])
        
        # Balance snapshots
        db.exchange_balances.create_index([("exchange", 1), ("asset", 1)])
        db.exchange_balances.create_index([("timestamp", DESCENDING)])
        
        # Credentials references
        db.exchange_credentials.create_index([("exchange", 1), ("label", 1)], unique=True)
    
    # ============================================
    # Connection Status
    # ============================================
    
    def save_connection_status(self, status: ExchangeConnectionStatus) -> str:
        """Save connection status snapshot"""
        db = self._get_db()
        
        doc = {
            "exchange": status.exchange.value,
            "connected": status.connected,
            "authenticated": status.authenticated,
            "rest_available": status.rest_available,
            "rest_latency_ms": status.rest_latency_ms,
            "ws_connected": status.ws_connected,
            "ws_authenticated": status.ws_authenticated,
            "rate_limit_remaining": status.rate_limit_remaining,
            "last_error": status.last_error,
            "error_count": status.error_count,
            "connected_at": status.connected_at,
            "timestamp": datetime.utcnow()
        }
        
        result = db.exchange_connections.insert_one(doc)
        return str(result.inserted_id)
    
    def get_connection_history(
        self,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get connection history"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange.upper()
        
        cursor = db.exchange_connections.find(
            filter_query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Orders
    # ============================================
    
    def save_order(self, order: ExchangeOrderResponse) -> str:
        """Save order to history"""
        db = self._get_db()
        
        doc = {
            "exchange": order.exchange.value,
            "exchange_order_id": order.exchange_order_id,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "original_size": order.original_size,
            "filled_size": order.filled_size,
            "remaining_size": order.remaining_size,
            "price": order.price,
            "avg_fill_price": order.avg_fill_price,
            "stop_price": order.stop_price,
            "fees": order.fees,
            "fee_asset": order.fee_asset,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "raw_payload": order.raw_payload,
            "timestamp": datetime.utcnow()
        }
        
        # Upsert by exchange + order_id
        result = db.exchange_orders.update_one(
            {
                "exchange": order.exchange.value,
                "exchange_order_id": order.exchange_order_id
            },
            {"$set": doc},
            upsert=True
        )
        
        return order.exchange_order_id
    
    def get_order_history(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get order history"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange.upper()
        if symbol:
            filter_query["symbol"] = symbol.upper()
        if status:
            filter_query["status"] = status.upper()
        
        cursor = db.exchange_orders.find(
            filter_query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_order_by_id(
        self,
        exchange: str,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        db = self._get_db()
        
        return db.exchange_orders.find_one(
            {
                "exchange": exchange.upper(),
                "exchange_order_id": order_id
            },
            {"_id": 0}
        )
    
    # ============================================
    # Positions
    # ============================================
    
    def save_position_snapshot(self, position: ExchangePosition) -> str:
        """Save position snapshot"""
        db = self._get_db()
        
        doc = {
            "exchange": position.exchange.value,
            "symbol": position.symbol,
            "side": position.side.value,
            "size": position.size,
            "entry_price": position.entry_price,
            "mark_price": position.mark_price,
            "liquidation_price": position.liquidation_price,
            "unrealized_pnl": position.unrealized_pnl,
            "realized_pnl": position.realized_pnl,
            "leverage": position.leverage,
            "margin_mode": position.margin_mode.value,
            "margin": position.margin,
            "raw_payload": position.raw_payload,
            "timestamp": datetime.utcnow()
        }
        
        result = db.exchange_positions.insert_one(doc)
        return str(result.inserted_id)
    
    def get_position_history(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get position history"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange.upper()
        if symbol:
            filter_query["symbol"] = symbol.upper()
        
        cursor = db.exchange_positions.find(
            filter_query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Balances
    # ============================================
    
    def save_balance_snapshot(self, balance: ExchangeBalance) -> str:
        """Save balance snapshot"""
        db = self._get_db()
        
        doc = {
            "exchange": balance.exchange.value,
            "asset": balance.asset,
            "free": balance.free,
            "locked": balance.locked,
            "total": balance.total,
            "usd_value": balance.usd_value,
            "timestamp": datetime.utcnow()
        }
        
        result = db.exchange_balances.insert_one(doc)
        return str(result.inserted_id)
    
    def get_balance_history(
        self,
        exchange: Optional[str] = None,
        asset: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get balance history"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange.upper()
        if asset:
            filter_query["asset"] = asset.upper()
        
        cursor = db.exchange_balances.find(
            filter_query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Credentials References
    # ============================================
    
    def save_credentials_ref(
        self,
        exchange: str,
        label: str,
        api_key_ref: str,
        api_secret_ref: str,
        passphrase_ref: Optional[str] = None,
        testnet: bool = False
    ) -> str:
        """Save credentials reference (NOT actual secrets)"""
        db = self._get_db()
        
        doc = {
            "exchange": exchange.upper(),
            "label": label,
            "api_key_ref": api_key_ref,
            "api_secret_ref": api_secret_ref,
            "passphrase_ref": passphrase_ref,
            "testnet": testnet,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.exchange_credentials.update_one(
            {"exchange": exchange.upper(), "label": label},
            {"$set": doc},
            upsert=True
        )
        
        return f"{exchange}:{label}"
    
    def get_credentials_ref(
        self,
        exchange: str,
        label: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Get credentials reference"""
        db = self._get_db()
        
        return db.exchange_credentials.find_one(
            {"exchange": exchange.upper(), "label": label},
            {"_id": 0}
        )
    
    def list_credentials_refs(
        self,
        exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all credentials references"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange.upper()
        
        return list(db.exchange_credentials.find(
            filter_query,
            {"_id": 0, "api_key_ref": 0, "api_secret_ref": 0, "passphrase_ref": 0}
        ))
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_order_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get order statistics"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": {
                    "exchange": "$exchange",
                    "status": "$status"
                },
                "count": {"$sum": 1},
                "total_size": {"$sum": "$filled_size"},
                "total_fees": {"$sum": "$fees"}
            }}
        ]
        
        results = list(db.exchange_orders.aggregate(pipeline))
        
        stats = {}
        for r in results:
            exchange = r["_id"]["exchange"]
            status = r["_id"]["status"]
            
            if exchange not in stats:
                stats[exchange] = {}
            
            stats[exchange][status] = {
                "count": r["count"],
                "total_size": r["total_size"],
                "total_fees": r["total_fees"]
            }
        
        return {
            "period_days": days,
            "by_exchange": stats
        }
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Cleanup old snapshots"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        connections_deleted = db.exchange_connections.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        positions_deleted = db.exchange_positions.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        balances_deleted = db.exchange_balances.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        return {
            "connections_deleted": connections_deleted,
            "positions_deleted": positions_deleted,
            "balances_deleted": balances_deleted
        }
