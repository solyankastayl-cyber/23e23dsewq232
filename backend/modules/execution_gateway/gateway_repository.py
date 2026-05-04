"""
Execution Gateway Repository

PHASE 39 — Execution Gateway Layer

MongoDB persistence for execution data.

Collections:
- gateway_orders: All orders
- gateway_fills: All fills
- gateway_approvals: Pending and completed approvals
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .gateway_types import (
    ExecutionOrder,
    ExecutionFill,
    ApprovalRequest,
    ExecutionResult,
    OrderStatus,
)


class GatewayRepository:
    """
    MongoDB repository for Execution Gateway.
    """
    
    def __init__(self):
        self._db = None
    
    def _get_db(self):
        """Get database connection."""
        if self._db is None:
            try:
                from core.database import get_database
                self._db = get_database()
            except Exception:
                pass
        return self._db
    
    # ═══════════════════════════════════════════════════════════
    # Orders
    # ═══════════════════════════════════════════════════════════
    
    def save_order(self, order: ExecutionOrder) -> bool:
        """Save execution order."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "order_id": order.order_id,
                "request_id": order.request_id,
                "exchange": order.exchange,
                "symbol": order.symbol,
                "exchange_symbol": order.exchange_symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "size_base": order.size_base,
                "size_quote": order.size_quote,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "expected_price": order.expected_price,
                "time_in_force": order.time_in_force,
                "reduce_only": order.reduce_only,
                "strategy": order.strategy,
                "status": order.status.value,
                "exchange_order_id": order.exchange_order_id,
                "created_at": order.created_at,
                "submitted_at": order.submitted_at,
                "metadata": order.metadata,
            }
            
            db.gateway_orders.update_one(
                {"order_id": order.order_id},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[GatewayRepository] Error saving order: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            return db.gateway_orders.find_one({"order_id": order_id}, {"_id": 0})
        except Exception:
            return None
    
    def get_orders(
        self,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get orders with filters."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            query = {}
            if status:
                query["status"] = status
            if strategy:
                query["strategy"] = strategy
            if exchange:
                query["exchange"] = exchange
            if symbol:
                query["symbol"] = symbol
            
            return list(
                db.gateway_orders.find(query, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception:
            return []
    
    def update_order_status(
        self,
        order_id: str,
        status: str,
        exchange_order_id: Optional[str] = None,
    ) -> bool:
        """Update order status."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            update = {"status": status}
            if exchange_order_id:
                update["exchange_order_id"] = exchange_order_id
            
            db.gateway_orders.update_one(
                {"order_id": order_id},
                {"$set": update}
            )
            return True
        except Exception:
            return False
    
    # ═══════════════════════════════════════════════════════════
    # Fills
    # ═══════════════════════════════════════════════════════════
    
    def save_fill(self, fill: ExecutionFill) -> bool:
        """Save execution fill."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "fill_id": fill.fill_id,
                "order_id": fill.order_id,
                "request_id": fill.request_id,
                "exchange_order_id": fill.exchange_order_id,
                "exchange": fill.exchange,
                "symbol": fill.symbol,
                "side": fill.side.value,
                "filled_size": fill.filled_size,
                "filled_value": fill.filled_value,
                "avg_price": fill.avg_price,
                "expected_price": fill.expected_price,
                "slippage_bps": fill.slippage_bps,
                "fee": fill.fee,
                "fee_asset": fill.fee_asset,
                "is_complete": fill.is_complete,
                "remaining_size": fill.remaining_size,
                "strategy": fill.strategy,
                "filled_at": fill.filled_at,
            }
            
            db.gateway_fills.insert_one(doc)
            return True
        except Exception as e:
            print(f"[GatewayRepository] Error saving fill: {e}")
            return False
    
    def get_fill(self, fill_id: str) -> Optional[Dict]:
        """Get fill by ID."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            return db.gateway_fills.find_one({"fill_id": fill_id}, {"_id": 0})
        except Exception:
            return None
    
    def get_fills(
        self,
        order_id: Optional[str] = None,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get fills with filters."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            query = {}
            if order_id:
                query["order_id"] = order_id
            if strategy:
                query["strategy"] = strategy
            if symbol:
                query["symbol"] = symbol
            
            return list(
                db.gateway_fills.find(query, {"_id": 0})
                .sort("filled_at", -1)
                .limit(limit)
            )
        except Exception:
            return []
    
    def get_fill_statistics(self, hours_back: int = 24) -> Dict:
        """Get fill statistics."""
        db = self._get_db()
        if db is None:
            return {}
        
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            pipeline = [
                {"$match": {"filled_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": None,
                        "total_volume": {"$sum": "$filled_value"},
                        "total_fills": {"$sum": 1},
                        "avg_slippage": {"$avg": "$slippage_bps"},
                        "total_fees": {"$sum": "$fee"},
                    }
                }
            ]
            
            result = list(db.gateway_fills.aggregate(pipeline))
            
            if result:
                return {
                    "total_volume_usd": round(result[0]["total_volume"], 2),
                    "total_fills": result[0]["total_fills"],
                    "avg_slippage_bps": round(result[0]["avg_slippage"] or 0, 2),
                    "total_fees_usd": round(result[0]["total_fees"], 2),
                    "period_hours": hours_back,
                }
            
            return {"total_volume_usd": 0, "total_fills": 0}
        except Exception:
            return {}
    
    # ═══════════════════════════════════════════════════════════
    # Approvals
    # ═══════════════════════════════════════════════════════════
    
    def save_approval(self, approval: ApprovalRequest) -> bool:
        """Save approval request."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "approval_id": approval.approval_id,
                "request_id": approval.request_id,
                "order_id": approval.order_id,
                "symbol": approval.symbol,
                "exchange": approval.exchange,
                "side": approval.side.value,
                "size_usd": approval.size_usd,
                "size_base": approval.size_base,
                "order_type": approval.order_type.value,
                "strategy": approval.strategy,
                "hypothesis_id": approval.hypothesis_id,
                "portfolio_risk": approval.portfolio_risk,
                "strategy_risk": approval.strategy_risk,
                "expected_slippage_bps": approval.expected_slippage_bps,
                "liquidity_impact": approval.liquidity_impact,
                "system_recommendation": approval.system_recommendation,
                "recommendation_reason": approval.recommendation_reason,
                "suggested_size_usd": approval.suggested_size_usd,
                "expires_at": approval.expires_at,
                "created_at": approval.created_at,
                "status": approval.status,
                "approved_by": approval.approved_by,
                "decision_at": approval.decision_at,
                "approved_size_usd": approval.approved_size_usd,
            }
            
            db.gateway_approvals.update_one(
                {"approval_id": approval.approval_id},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[GatewayRepository] Error saving approval: {e}")
            return False
    
    def get_approval(self, approval_id: str) -> Optional[Dict]:
        """Get approval by ID."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            return db.gateway_approvals.find_one({"approval_id": approval_id}, {"_id": 0})
        except Exception:
            return None
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get pending approvals."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            return list(
                db.gateway_approvals.find(
                    {"status": "PENDING"},
                    {"_id": 0}
                ).sort("created_at", -1)
            )
        except Exception:
            return []
    
    def update_approval(
        self,
        approval_id: str,
        status: str,
        approved_by: Optional[str] = None,
        approved_size_usd: Optional[float] = None,
    ) -> bool:
        """Update approval status."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            update = {
                "status": status,
                "decision_at": datetime.now(timezone.utc),
            }
            if approved_by:
                update["approved_by"] = approved_by
            if approved_size_usd:
                update["approved_size_usd"] = approved_size_usd
            
            db.gateway_approvals.update_one(
                {"approval_id": approval_id},
                {"$set": update}
            )
            return True
        except Exception:
            return False
    
    # ═══════════════════════════════════════════════════════════
    # Execution Results
    # ═══════════════════════════════════════════════════════════
    
    def save_result(self, result: ExecutionResult) -> bool:
        """Save execution result."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "request_id": result.request_id,
                "success": result.success,
                "status": result.status.value,
                "order_id": result.order_id,
                "exchange_order_id": result.exchange_order_id,
                "exchange": result.exchange,
                "symbol": result.symbol,
                "side": result.side.value,
                "requested_size_usd": result.requested_size_usd,
                "filled_size_usd": result.filled_size_usd,
                "filled_size_base": result.filled_size_base,
                "avg_price": result.avg_price,
                "expected_price": result.expected_price,
                "slippage_bps": result.slippage_bps,
                "fee": result.fee,
                "total_cost": result.total_cost,
                "safety_check_passed": result.safety_check_passed,
                "safety_adjustments": result.safety_adjustments,
                "failure_reason": result.failure_reason,
                "latency_ms": result.latency_ms,
                "created_at": result.created_at,
                "completed_at": result.completed_at,
            }
            
            db.gateway_results.insert_one(doc)
            return True
        except Exception as e:
            print(f"[GatewayRepository] Error saving result: {e}")
            return False
    
    def get_results(
        self,
        success: Optional[bool] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get execution results."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            query = {}
            if success is not None:
                query["success"] = success
            if symbol:
                query["symbol"] = symbol
            
            return list(
                db.gateway_results.find(query, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    # Collections Setup
    # ═══════════════════════════════════════════════════════════
    
    def ensure_collections(self) -> bool:
        """Ensure MongoDB collections and indexes exist."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            collections = [
                "gateway_orders",
                "gateway_fills",
                "gateway_approvals",
                "gateway_results",
            ]
            
            existing = db.list_collection_names()
            
            for col in collections:
                if col not in existing:
                    db.create_collection(col)
            
            # Indexes
            db.gateway_orders.create_index([("order_id", 1)], unique=True)
            db.gateway_orders.create_index([("request_id", 1)])
            db.gateway_orders.create_index([("status", 1)])
            db.gateway_orders.create_index([("created_at", -1)])
            
            db.gateway_fills.create_index([("fill_id", 1)], unique=True)
            db.gateway_fills.create_index([("order_id", 1)])
            db.gateway_fills.create_index([("filled_at", -1)])
            
            db.gateway_approvals.create_index([("approval_id", 1)], unique=True)
            db.gateway_approvals.create_index([("status", 1)])
            
            db.gateway_results.create_index([("request_id", 1)])
            db.gateway_results.create_index([("created_at", -1)])
            
            return True
        except Exception as e:
            print(f"[GatewayRepository] Error ensuring collections: {e}")
            return False


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_repository: Optional[GatewayRepository] = None


def get_gateway_repository() -> GatewayRepository:
    """Get singleton instance."""
    global _repository
    if _repository is None:
        _repository = GatewayRepository()
        _repository.ensure_collections()
    return _repository
