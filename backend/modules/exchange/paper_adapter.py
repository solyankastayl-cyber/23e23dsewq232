"""Paper Exchange Adapter — EXECUTION QUALITY LAYER

Simulates exchange execution with PRODUCTION-GRADE REALISM:
- Partial fills (2+ fills per order for large notionals)
- Trading fees (0.1% taker, 0.05% maker)
- Symbol-specific slippage (BTC better than altcoins)
- Size-dependent slippage (larger orders = worse fills)
- Order rejection taxonomy (balance, notional, lot size, etc)
- Execution quality scoring (0-100)
- Latency simulation
- Prices from PriceService (NO MOCKS)

This is PRE-LIVE VALIDATION level execution simulator.
"""

import uuid
import asyncio
import random
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from .base_adapter import BaseExchangeAdapter
from .models import (
    OrderRequest,
    OrderResponse,
    AccountInfo,
    Balance,
    Position,
)
from modules.market_data.price_service import get_price_service
from .execution_quality_config import (
    calculate_slippage,
    calculate_fee,
    should_partial_fill,
    REJECTION_CONFIG,
    PARTIAL_FILL_CONFIG,
)

logger = logging.getLogger(__name__)


class PaperExchangeAdapter(BaseExchangeAdapter):
    """Paper trading adapter (simulated execution)."""

    def __init__(self, config: dict, db_client: AsyncIOMotorClient):
        super().__init__(config)
        self.db = db_client.trading_db
        self.account_id = config.get("account_id", "paper_default")
        self.initial_balance = config.get("initial_balance", 10000.0)

    async def connect(self) -> bool:
        """Initialize paper account."""
        # Check if account exists
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        if not account:
            # Create new paper account
            await self.db.exchange_accounts.insert_one({
                "account_id": self.account_id,
                "exchange": "PAPER",
                "account_type": "SPOT",
                "balance_usdt": self.initial_balance,
                "equity": self.initial_balance,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            logger.info(f"[PaperAdapter] Created account {self.account_id} with ${self.initial_balance}")
        
        self.connected = True
        return True

    async def disconnect(self) -> bool:
        self.connected = False
        return True

    async def ping(self) -> bool:
        return self.connected

    async def get_account_info(self) -> AccountInfo:
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        if not account:
            raise ValueError(f"Account {self.account_id} not found")
        
        balances = [
            Balance(
                asset="USDT",
                free=account["balance_usdt"],
                locked=0.0,
                total=account["balance_usdt"],
            )
        ]
        
        return AccountInfo(
            exchange="PAPER",
            account_id=self.account_id,
            account_type="SPOT",
            balances=balances,
            total_equity=account["equity"],
        )

    async def get_balances(self) -> List[Balance]:
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        return [
            Balance(
                asset="USDT",
                free=account["balance_usdt"] if account else 0.0,
                locked=0.0,
                total=account["balance_usdt"] if account else 0.0,
            )
        ]

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place paper order with EXECUTION QUALITY LAYER integration.
        
        MARKET orders:
        - Validation (balance, notional, limits, rejection taxonomy)
        - Partial fills for large orders (2+ fill records)
        - Realistic slippage (symbol + size dependent)
        - Trading fees (0.1% taker)
        - Latency simulation
        - Execution quality scoring (0-100)
        
        LIMIT orders:
        - Saved as NEW (would need price monitoring for fills)
        
        Returns:
            OrderResponse with full execution metrics
        """
        from .paper_execution_quality import (
            validate_order,
            execute_market_order,
            OrderRejection,
        )
        
        logger.info(f"[PaperAdapter] Placing order: {order.symbol} {order.side} {order.quantity}")
        
        # Get current LIVE mark price from PriceService
        price_service = await get_price_service()
        
        try:
            mark_price = await price_service.get_mark_price(order.symbol)
        except Exception as e:
            logger.error(f"[PaperAdapter] Failed to get mark price for {order.symbol}: {e}")
            return self._create_rejected_response(
                order,
                "PRICE_UNAVAILABLE",
                f"Failed to get mark price: {e}"
            )
        
        # Get account info for validation
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        account_balance = account.get("balance_usdt", 0) if account else 0  # Fixed: use balance_usdt
        
        open_positions = await self.db.positions.count_documents({
            "account_id": self.account_id,
            "status": "OPEN"
        })
        
        # VALIDATION with rejection taxonomy
        try:
            await validate_order(
                order,
                account_balance,
                open_positions,
                self.db
            )
        except OrderRejection as e:
            logger.warning(f"[PaperAdapter] Order REJECTED: {e.reason} - {e.message}")
            return self._create_rejected_response(order, e.reason, e.message)
        
        # EXECUTION
        if order.order_type == "MARKET":
            try:
                # Execute with full execution quality simulation
                exec_result = await execute_market_order(
                    order,
                    mark_price,
                    self.account_id,
                    self.db
                )
                
                # Save order to DB with execution metrics
                order_doc = {
                    "order_id": exec_result["order_id"],
                    "client_order_id": exec_result["client_order_id"],
                    "account_id": self.account_id,
                    "exchange": "PAPER",
                    "symbol": order.symbol,
                    "side": order.side,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": exec_result["status"],
                    "filled_quantity": exec_result["total_filled_qty"],
                    "remaining_quantity": exec_result["remaining_qty"],
                    "avg_fill_price": exec_result["avg_fill_price"],
                    "total_fee": exec_result["total_fee"],
                    "execution_quality_score": exec_result["execution_quality_score"],
                    "latency_ms": exec_result["latency_ms"],
                    "slippage_bps": exec_result["slippage_bps"],
                    "fill_count": len(exec_result["fills"]),
                    "stop_loss": order.stop_loss,
                    "take_profit": order.take_profit,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                
                await self.db.exchange_orders.insert_one(order_doc.copy())
                
                logger.info(
                    f"[PaperAdapter] Order {exec_result['status']}: {exec_result['order_id']} "
                    f"{order.symbol} {order.side} {exec_result['total_filled_qty']:.6f} @ "
                    f"${exec_result['avg_fill_price']:.2f}, fee=${exec_result['total_fee']:.4f}, "
                    f"quality={exec_result['execution_quality_score']:.1f}/100, "
                    f"fills={len(exec_result['fills'])}"
                )
                
                # Remove _id from response
                order_doc.pop('_id', None)
                
                return OrderResponse(
                    success=True,
                    exchange="PAPER",
                    order_id=exec_result["order_id"],
                    client_order_id=exec_result["client_order_id"],
                    status=exec_result["status"],
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    filled_quantity=exec_result["total_filled_qty"],
                    avg_fill_price=exec_result["avg_fill_price"],
                    raw=order_doc,
                )
            
            except Exception as e:
                logger.error(f"[PaperAdapter] Execution error: {e}", exc_info=True)
                return self._create_rejected_response(
                    order,
                    "EXECUTION_ERROR",
                    f"Execution failed: {e}"
                )
        
        else:  # LIMIT order
            order_id = f"paper-{uuid.uuid4().hex[:12]}"
            client_order_id = order.client_order_id or order_id
            
            fill_price = order.price
            status = "NEW"
            filled_quantity = 0.0
            
            logger.info(f"[PaperAdapter] LIMIT order placed: {order.symbol} @ ${fill_price:.2f}")
            
            order_doc = {
                "order_id": order_id,
                "client_order_id": client_order_id,
                "account_id": self.account_id,
                "exchange": "PAPER",
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "quantity": order.quantity,
                "price": order.price,
                "status": status,
                "filled_quantity": filled_quantity,
                "remaining_quantity": order.quantity,
                "avg_fill_price": None,
                "total_fee": 0.0,
                "execution_quality_score": None,
                "latency_ms": None,
                "slippage_bps": None,
                "fill_count": 0,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            await self.db.exchange_orders.insert_one(order_doc.copy())
            order_doc.pop('_id', None)
            
            return OrderResponse(
                success=True,
                exchange="PAPER",
                order_id=order_id,
                client_order_id=client_order_id,
                status=status,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=filled_quantity,
                avg_fill_price=None,
                raw=order_doc,
            )
    
    def _create_rejected_response(
        self,
        order: OrderRequest,
        reject_reason: str,
        reject_message: str
    ) -> OrderResponse:
        """Create OrderResponse for rejected order."""
        return OrderResponse(
            success=False,
            exchange="PAPER",
            order_id="",
            client_order_id=order.client_order_id or "",
            status="REJECTED",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=0.0,
            avg_fill_price=None,
            raw={
                "reject_reason": reject_reason,
                "reject_message": reject_message,
            },
        )

    async def cancel_order(self, order_id: str) -> bool:
        result = await self.db.exchange_orders.update_one(
            {"order_id": order_id, "status": {"$in": ["NEW", "PARTIALLY_FILLED"]}},
            {"$set": {"status": "CANCELED", "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def get_order(self, order_id: str) -> Optional[OrderResponse]:
        order = await self.db.exchange_orders.find_one({" order_id": order_id})
        
        if not order:
            return None
        
        # Remove _id
        order.pop('_id', None)
        
        return OrderResponse(
            success=True,
            exchange="PAPER",
            order_id=order["order_id"],
            client_order_id=order["client_order_id"],
            status=order["status"],
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            filled_quantity=order.get("filled_quantity", 0.0),
            avg_fill_price=order.get("avg_fill_price"),
            raw=order,
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        query = {"account_id": self.account_id, "status": {"$in": ["NEW", "PARTIALLY_FILLED"]}}
        if symbol:
            query["symbol"] = symbol
        
        orders = await self.db.exchange_orders.find(query).to_list(length=100)
        
        return [
            OrderResponse(
                success=True,
                exchange="PAPER",
                order_id=o["order_id"],
                client_order_id=o["client_order_id"],
                status=o["status"],
                symbol=o["symbol"],
                side=o["side"],
                quantity=o["quantity"],
                filled_quantity=o.get("filled_quantity", 0.0),
                avg_fill_price=o.get("avg_fill_price"),
                raw=o,
            )
            for o in orders
        ]

    async def get_positions(self) -> List[Position]:
        positions = await self.db.exchange_positions.find(
            {"account_id": self.account_id, "status": "OPEN"}
        ).to_list(length=100)
        
        return [
            Position(
                symbol=p["symbol"],
                side=p["side"],
                size=p["size"],
                entry_price=p["entry_price"],
                mark_price=p.get("mark_price", p["entry_price"]),
                unrealized_pnl=p.get("unrealized_pnl", 0.0),
                leverage=p.get("leverage", 1.0),
            )
            for p in positions
        ]

    async def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[dict]:
        query = {"account_id": self.account_id}
        if symbol:
            query["symbol"] = symbol
        
        fills = await self.db.exchange_fills.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return fills
