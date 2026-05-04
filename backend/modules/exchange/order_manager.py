"""
Order Manager — Critical Layer for Real Execution

Handles order lifecycle:
- PENDING → NEW → PARTIALLY_FILLED → FILLED / CANCELED
- DB persistence (source of truth)
- Fail-safe on exchange errors
"""

import uuid
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Order lifecycle manager.
    
    Ensures:
    - All orders are persisted BEFORE exchange submission
    - Order state is tracked (PENDING → NEW → FILLED)
    - Failed orders are logged
    """
    
    def __init__(self, exchange_adapter, db):
        """
        Args:
            exchange_adapter: ExchangeAdapter instance
            db: MongoDB database instance
        """
        self.adapter = exchange_adapter
        self.db = db
        self.orders_collection = db.orders
        self.fills_collection = db.fills
        
        logger.info("[OrderManager] Initialized")
    
    async def place_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order with full lifecycle tracking.
        
        Args:
            request: {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quantity": 0.001,
                "price": None (for MARKET),
                "client_order_id": "optional"
            }
        
        Returns:
            Order result with status
        
        Flow:
        1. Validate order request (CRITICAL)
        2. Create order record (PENDING)
        3. Submit to exchange
        4. Update status (NEW/FILLED/FAILED)
        5. Store fills
        """
        # CRITICAL: Validate order request has 'type' field
        from modules.exchange.order_builder import validate_order_request
        
        try:
            validate_order_request(order_request)
        except ValueError as e:
            logger.error(f"[OrderManager] Invalid order request: {e}")
            raise RuntimeError(f"Order validation failed: {e}")
        
        # 1. Create order record (PENDING)
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        client_order_id = order_request.get("client_order_id", order_id)
        
        order_doc = {
            "order_id": order_id,
            "client_order_id": client_order_id,
            "symbol": order_request["symbol"],
            "side": order_request["side"],
            "type": order_request["type"],
            "quantity": order_request["quantity"],
            "price": order_request.get("price"),
            "status": "PENDING",
            "exchange_order_id": None,
            "filled_qty": 0.0,
            "avg_price": None,
            "error": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        await self.orders_collection.insert_one(order_doc.copy())
        logger.info(f"[OrderManager] Created order {order_id} (PENDING)")
        
        # Log step: order created
        try:
            from modules.execution_logger import get_execution_logger
            exec_logger = get_execution_logger()
            await exec_logger.log_event({
                "type": "OM_STEP_1_ORDER_CREATED",
                "order_id": order_id,
                "symbol": order_request["symbol"]
            })
        except:
            pass  # Non-critical
        
        # 2. Submit to exchange
        try:
            # Fail-safe: check connection
            if not self.adapter.connected:
                raise RuntimeError("Exchange adapter not connected")
            
            # Log step: before adapter call
            try:
                await exec_logger.log_event({
                    "type": "OM_STEP_2_BEFORE_ADAPTER",
                    "order_id": order_id
                })
            except:
                pass
            
            result = await self.adapter.place_order(order_request)
            
            # Log step: after adapter call
            try:
                await exec_logger.log_event({
                    "type": "OM_STEP_3_AFTER_ADAPTER",
                    "order_id": order_id,
                    "status": str(getattr(result, 'status', 'UNKNOWN'))[:50]
                })
            except:
                pass
            
            # 3. Update order status
            # Handle both dict and Pydantic model responses
            if hasattr(result, 'dict'):
                # Pydantic model (Order)
                result_dict = result.dict()
                exchange_order_id = result_dict.get("order_id")
                status = result_dict.get("status", "NEW")
                filled_qty = result_dict.get("filled_qty", 0.0)
                avg_price = result_dict.get("price")  # For Order model, avg price is in 'price' field
            else:
                # Plain dict
                exchange_order_id = result.get("order_id") or result.get("orderId")
                status = result.get("status", "NEW")
                filled_qty = result.get("filled_qty", result.get("executedQty", 0.0))
                avg_price = result.get("avg_price")
            
            update_doc = {
                "status": status,
                "exchange_order_id": exchange_order_id,
                "filled_qty": float(filled_qty),
                "avg_price": float(avg_price) if avg_price else None,
                "updated_at": datetime.now(timezone.utc),
            }
            
            await self.orders_collection.update_one(
                {"order_id": order_id},
                {"$set": update_doc}
            )
            
            logger.info(f"[OrderManager] Order {order_id} submitted: {status} (exchange_id={exchange_order_id})")
            
            # 4. Store fills (if FILLED)
            if status == "FILLED" and filled_qty > 0:
                await self._store_fill(order_id, exchange_order_id, order_request, filled_qty, avg_price)
            
            return {
                "order_id": order_id,
                "exchange_order_id": exchange_order_id,
                "status": status,
                "filled_qty": float(filled_qty),
                "avg_price": float(avg_price) if avg_price else None,
            }
        
        except Exception as e:
            # 3. Mark as FAILED
            logger.error(f"[OrderManager] Order {order_id} FAILED: {e}")
            
            await self.orders_collection.update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": "FAILED",
                    "error": str(e),
                    "updated_at": datetime.now(timezone.utc),
                }}
            )
            
            raise RuntimeError(f"Order submission failed: {e}")
    
    async def _store_fill(
        self,
        order_id: str,
        exchange_order_id: str,
        request: Dict[str, Any],
        filled_qty: float,
        avg_price: float
    ):
        """Store fill record."""
        fill_doc = {
            "fill_id": f"fill_{uuid.uuid4().hex[:12]}",
            "order_id": order_id,
            "exchange_order_id": exchange_order_id,
            "symbol": request["symbol"],
            "side": request["side"],
            "qty": filled_qty,
            "price": avg_price,
            "quote_qty": filled_qty * avg_price,
            "fee": (filled_qty * avg_price) * 0.001,  # 0.1% default
            "fee_asset": "USDT",
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.fills_collection.insert_one(fill_doc)
        logger.info(f"[OrderManager] Stored fill: {filled_qty} @ ${avg_price}")
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order status from DB.
        
        Returns:
            Order document or None
        """
        order = await self.orders_collection.find_one({"order_id": order_id}, {"_id": 0})
        return order
    
    async def sync_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Sync order status from exchange.
        
        For orders stuck in PENDING/NEW.
        """
        order = await self.get_order_status(order_id)
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        exchange_order_id = order.get("exchange_order_id")
        
        if not exchange_order_id:
            logger.warning(f"[OrderManager] Order {order_id} has no exchange_order_id, cannot sync")
            return order
        
        # Query exchange for order status
        # (This requires exchange adapter to implement get_order_by_id)
        # For now, we skip this and rely on webhook/polling
        
        return order



# Singleton
_order_manager = None


def init_order_manager(exchange_adapter, db):
    """Initialize OrderManager singleton."""
    global _order_manager
    _order_manager = OrderManager(exchange_adapter, db)
    logger.info("[OrderManager] Singleton initialized")
    return _order_manager


def get_order_manager():
    """Get OrderManager singleton."""
    if _order_manager is None:
        raise RuntimeError("OrderManager not initialized. Call init_order_manager() first.")
    return _order_manager
