"""
P1.1: Binance REST Adapter with Retry/Backoff Layer

Мок для Milestone A: возвращает stub ответ в формате Binance.
После прохождения DoD — заменить на реальный REST.

P1.1 Enhancement: Integrated retry policy for execution safety
"""

import uuid
from typing import Dict, Any, Optional
import logging

# P1.1: Retry/Backoff imports
from modules.execution_reality.reliability import (
    RetryPolicy,
    classify_binance_error
)

logger = logging.getLogger(__name__)


class BinanceRestAdapter:
    """
    Mock адаптер Binance REST API с P1.1 Retry Layer
    
    CRITICAL PATHS WITH RETRY:
    - submit_limit_order
    - submit_market_order  
    - cancel_order (when added)
    - get_order_status
    - get_position
    - get_ticker
    """

    def __init__(self, use_real: bool = False, audit_callback: Optional[callable] = None):
        """
        Args:
            use_real: Если True — будет использовать реальный Binance API (пока stub)
            audit_callback: Callback for retry attempt auditing (P1.1)
        """
        self.use_real = use_real
        if use_real:
            logger.warning("Реальный Binance REST пока не реализован, используем mock")
        
        # P1.1: Retry policy for execution safety
        self.retry_policy = RetryPolicy(
            max_attempts=3,
            base_delay_ms=100.0,
            max_delay_ms=3000.0,
            jitter=True,
            audit_callback=audit_callback
        )
        
        logger.info("✅ BinanceRestAdapter initialized with P1.1 Retry Layer")

    async def submit_limit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        client_order_id: str = None
    ) -> Dict[str, Any]:
        """
        Отправить LIMIT ордер с P1.1 retry policy.
        
        Args:
            client_order_id: Custom client order ID (optional)
        
        Returns:
            Binance order response
        
        Raises:
            Exception if all retries exhausted
        """
        # P1.1: Wrap with retry policy
        return await self.retry_policy.execute_async(
            self._submit_limit_order_impl,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            client_order_id=client_order_id,
            error_classifier=classify_binance_error,
            context={
                "operation": "submit_limit_order",
                "symbol": symbol,
                "side": side,
                "client_order_id": client_order_id
            }
        )
    
    async def _submit_limit_order_impl(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        client_order_id: str = None
    ) -> Dict[str, Any]:
        """
        Internal implementation (wrapped by retry policy).
        
        Args:
            client_order_id: Custom client order ID (optional)
        """
        logger.info(
            f"[MOCK Binance] Submitting LIMIT order: {side} {qty} {symbol} @ {price} | "
            f"client_order_id={client_order_id}"
        )

        # Mock response в формате Binance
        mock_response = {
            "symbol": symbol,
            "orderId": str(uuid.uuid4())[:8],  # fake exchange order ID
            "orderListId": -1,
            "clientOrderId": client_order_id or str(uuid.uuid4())[:12],
            "transactTime": 1699999999999,
            "price": str(price),
            "origQty": str(qty),
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": []
        }

        logger.info(f"[MOCK Binance] ACK: orderId={mock_response['orderId']}")
        return {"status": "ACK", "exchange_order_id": mock_response["orderId"], **mock_response}

    
    async def submit_market_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        client_order_id: str = None
    ) -> Dict[str, Any]:
        """
        Отправить MARKET ордер с P1.1 retry policy (для STOP_LOSS).
        
        MARKET orders execute immediately at best available price.
        Used for STOP_LOSS / CLOSE intents where price is less important than execution.
        
        Args:
            client_order_id: Custom client order ID (optional)
        
        Returns:
            Binance order response
        
        Raises:
            Exception if all retries exhausted
        """
        # P1.1: Wrap with retry policy
        return await self.retry_policy.execute_async(
            self._submit_market_order_impl,
            symbol=symbol,
            side=side,
            qty=qty,
            client_order_id=client_order_id,
            error_classifier=classify_binance_error,
            context={
                "operation": "submit_market_order",
                "symbol": symbol,
                "side": side,
                "client_order_id": client_order_id
            }
        )
    
    async def _submit_market_order_impl(
        self,
        symbol: str,
        side: str,
        qty: float,
        client_order_id: str = None
    ) -> Dict[str, Any]:
        """
        Internal implementation (wrapped by retry policy).
        
        Args:
            client_order_id: Custom client order ID (optional)
        """
        # P1.2 LIVE: Mark submit timestamp
        try:
            from ..latency import get_latency_tracker
            latency_tracker = get_latency_tracker()
            if client_order_id:
                latency_tracker.mark_submit(client_order_id)
        except Exception as e:
            logger.debug(f"[P1.2] Latency mark_submit failed: {e}")
        
        logger.info(
            f"[MOCK Binance] Submitting MARKET order: {side} {qty} {symbol} | "
            f"client_order_id={client_order_id}"
        )

        # Mock response - MARKET order fills immediately
        fill_price = 50000.0 if "BTC" in symbol else 1.0  # Mock price
        
        mock_response = {
            "symbol": symbol,
            "orderId": str(uuid.uuid4())[:8],
            "orderListId": -1,
            "clientOrderId": client_order_id or str(uuid.uuid4())[:12],
            "transactTime": 1699999999999,
            "price": "0.0",  # MARKET orders don't have price
            "origQty": str(qty),
            "executedQty": str(qty),  # MARKET fills immediately
            "cummulativeQuoteQty": str(qty * fill_price),
            "status": "FILLED",  # MARKET orders fill immediately (in mock)
            "timeInForce": "GTC",
            "type": "MARKET",
            "side": side,
            "fills": [{
                "price": str(fill_price),
                "qty": str(qty),
                "commission": "0.0",
                "commissionAsset": symbol.replace("USDT", "")
            }]
        }
        
        # P1.2 LIVE: Mark ACK immediately (mock response instant)
        try:
            if client_order_id:
                latency_tracker.mark_ack(client_order_id)
        except Exception as e:
            logger.debug(f"[P1.2] Latency mark_ack failed: {e}")
        
        # P1.2 LIVE: Mark fill immediately (MARKET fills instantly in mock)
        try:
            if client_order_id:
                # Calculate slippage (mock: 0.1% random slippage)
                import random
                slippage_pct = random.uniform(0.05, 0.15)
                pnl_impact_usdt = -0.5 * qty  # Mock small PnL impact
                
                latency_tracker.mark_fill(
                    client_order_id,
                    slippage_pct=slippage_pct,
                    pnl_impact_usdt=pnl_impact_usdt
                )
        except Exception as e:
            logger.debug(f"[P1.2] Latency mark_fill failed: {e}")

        logger.info(
            f"[MOCK Binance] MARKET FILLED: orderId={mock_response['orderId']} | "
            f"price={fill_price}"
        )
        return {"status": "FILLED", "exchange_order_id": mock_response["orderId"], **mock_response}

    
    async def get_order_status(
        self,
        symbol: str,
        client_order_id: str = None,
        order_id: str = None
    ) -> Dict[str, Any]:
        """
        P1.5.1: Get order status via REST with P1.1 retry policy (fallback for stream delays).
        
        Args:
            symbol: Trading symbol
            client_order_id: Client order ID (preferred)
            order_id: Exchange order ID
        
        Returns:
            Order status dict
        
        Raises:
            Exception if all retries exhausted
        """
        # P1.1: Wrap with retry policy
        return await self.retry_policy.execute_async(
            self._get_order_status_impl,
            symbol=symbol,
            client_order_id=client_order_id,
            order_id=order_id,
            error_classifier=classify_binance_error,
            context={
                "operation": "get_order_status",
                "symbol": symbol,
                "client_order_id": client_order_id,
                "order_id": order_id
            }
        )
    
    async def _get_order_status_impl(
        self,
        symbol: str,
        client_order_id: str = None,
        order_id: str = None
    ) -> Dict[str, Any]:
        """Internal implementation (wrapped by retry policy)"""
        logger.info(
            f"[MOCK Binance] Query order status: symbol={symbol} | "
            f"client_order_id={client_order_id} | order_id={order_id}"
        )
        
        # Mock: assume order filled (REST fallback simulation)
        mock_status = {
            "symbol": symbol,
            "orderId": order_id or str(uuid.uuid4())[:8],
            "clientOrderId": client_order_id or "",
            "status": "FILLED",  # Optimistic: assume stream lag, order actually filled
            "executedQty": "1.0",
            "origQty": "1.0",
            "price": "50000.0",
            "side": "SELL",
            "type": "MARKET",
            "updateTime": 1699999999999
        }
        
        logger.info(f"[MOCK Binance] Order status: {mock_status['status']}")
        return mock_status
    
    async def get_position(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        P1.5.1: Get current position via REST with P1.1 retry policy (for indirect fill confirmation).
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Position dict
        
        Raises:
            Exception if all retries exhausted
        """
        # P1.1: Wrap with retry policy
        return await self.retry_policy.execute_async(
            self._get_position_impl,
            symbol=symbol,
            error_classifier=classify_binance_error,
            context={
                "operation": "get_position",
                "symbol": symbol
            }
        )
    
    async def _get_position_impl(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Internal implementation (wrapped by retry policy)"""
        logger.info(f"[MOCK Binance] Query position: symbol={symbol}")
        
        # Mock: assume position closed (for STOP_LOSS confirmation)
        mock_position = {
            "symbol": symbol,
            "positionAmt": "0.0",  # Closed
            "entryPrice": "0.0",
            "markPrice": "50000.0",
            "unRealizedProfit": "0.0",
            "liquidationPrice": "0"
        }
        
        logger.info(f"[MOCK Binance] Position: {mock_position['positionAmt']}")
        return mock_position
    
    async def get_ticker(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        P1.5.2: Get ticker (bid/ask/last) via REST with P1.1 retry policy (for spread check).
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Ticker dict
        
        Raises:
            Exception if all retries exhausted
        """
        # P1.1: Wrap with retry policy
        return await self.retry_policy.execute_async(
            self._get_ticker_impl,
            symbol=symbol,
            error_classifier=classify_binance_error,
            context={
                "operation": "get_ticker",
                "symbol": symbol
            }
        )
    
    async def _get_ticker_impl(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Internal implementation (wrapped by retry policy)"""
        logger.info(f"[MOCK Binance] Query ticker: symbol={symbol}")
        
        # Mock ticker
        base_price = 50000.0 if "BTC" in symbol else 1.0
        spread_bps = 5  # 0.05% normal spread
        spread = base_price * (spread_bps / 10000)
        
        mock_ticker = {
            "symbol": symbol,
            "bidPrice": str(base_price - spread / 2),
            "askPrice": str(base_price + spread / 2),
            "lastPrice": str(base_price)
        }
        
        logger.info(f"[MOCK Binance] Ticker: bid={mock_ticker['bidPrice']}, ask={mock_ticker['askPrice']}")
        return mock_ticker


