"""
Exchange Routes - PHASE 5.1
===========================

REST API endpoints for Exchange Adapter Layer.

Endpoints:
- POST /api/exchange/connect
- POST /api/exchange/disconnect
- GET  /api/exchange/status
- GET  /api/exchange/balances
- GET  /api/exchange/positions
- GET  /api/exchange/open-orders
- GET  /api/exchange/order-status/{order_id}
- GET  /api/exchange/ticker/{symbol}
- GET  /api/exchange/orderbook/{symbol}
- POST /api/exchange/create-order
- POST /api/exchange/cancel-order
- POST /api/exchange/cancel-all
- POST /api/exchange/stream/start
- POST /api/exchange/stream/stop
- GET  /api/exchange/stream/status
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .exchange_types import (
    ExchangeId,
    OrderSide,
    OrderType,
    TimeInForce,
    StreamType,
    ExchangeOrderRequest,
    ConnectRequest,
    CreateOrderRequest,
    CancelOrderRequest,
    StreamRequest
)
from .exchange_router import get_exchange_router
from .ws_manager import get_ws_manager, StreamConfig
from .exchange_repository import ExchangeRepository


router = APIRouter(prefix="/api/exchange", tags=["Exchange Adapter"])

# Initialize
repository = ExchangeRepository()


# ============================================
# Request/Response Models
# ============================================

class ConnectRequestModel(BaseModel):
    """Connect request"""
    exchange: str = "BINANCE"
    testnet: bool = False
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None


class CreateOrderRequestModel(BaseModel):
    """Create order request"""
    exchange: str = "BINANCE"
    symbol: str
    side: str = "BUY"
    order_type: str = "MARKET"
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False
    client_order_id: Optional[str] = None


class CancelOrderRequestModel(BaseModel):
    """Cancel order request"""
    exchange: str
    order_id: str
    symbol: Optional[str] = None


class StreamRequestModel(BaseModel):
    """Stream request"""
    exchange: str = "BINANCE"
    stream_type: str = "TICKER"
    symbols: List[str] = Field(default_factory=list)


# ============================================
# Health & Status
# ============================================

@router.get("/health")
async def exchange_health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "phase_5.1",
        "supported_exchanges": ["BINANCE", "BYBIT", "OKX"],
        "features": [
            "connect/disconnect",
            "balances",
            "positions",
            "orders",
            "market_data",
            "websocket_streams"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def get_status(exchange: Optional[str] = Query(default=None)):
    """Get exchange connection status"""
    router_instance = get_exchange_router()
    
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
            status = router_instance.get_connection_status(exchange_id)
            
            if status:
                return {
                    "exchange": exchange.upper(),
                    "status": status[exchange_id].dict() if exchange_id in status else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            return {"exchange": exchange.upper(), "status": "NOT_CONNECTED"}
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    return {
        "router_status": router_instance.get_router_status(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Connection Management
# ============================================

@router.post("/connect")
async def connect_exchange(request: ConnectRequestModel):
    """Connect to exchange"""
    try:
        exchange_id = ExchangeId(request.exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {request.exchange}")
    
    router_instance = get_exchange_router()
    
    success = await router_instance.connect(
        exchange_id,
        api_key=request.api_key,
        api_secret=request.api_secret,
        passphrase=request.passphrase,
        testnet=request.testnet
    )
    
    status = router_instance.get_connection_status(exchange_id)
    
    return {
        "exchange": request.exchange.upper(),
        "connected": success,
        "testnet": request.testnet,
        "status": status[exchange_id].dict() if exchange_id in status else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/disconnect")
async def disconnect_exchange(exchange: str):
    """Disconnect from exchange"""
    try:
        exchange_id = ExchangeId(exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    router_instance = get_exchange_router()
    success = await router_instance.disconnect(exchange_id)
    
    return {
        "exchange": exchange.upper(),
        "disconnected": success,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Account Operations
# ============================================

@router.get("/balances")
async def get_balances(
    exchange: Optional[str] = Query(default=None),
    asset: Optional[str] = Query(default=None)
):
    """Get account balances"""
    router_instance = get_exchange_router()
    
    exchange_id = None
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    balances = await router_instance.get_balances(exchange_id, asset)
    
    # Convert to serializable format
    result = {}
    for ex, bal_list in balances.items():
        result[ex.value] = [b.dict() for b in bal_list]
    
    return {
        "balances": result,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/positions")
async def get_positions(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None)
):
    """Get open positions"""
    router_instance = get_exchange_router()
    
    exchange_id = None
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    positions = await router_instance.get_positions(exchange_id, symbol)
    
    # Convert to serializable format
    result = {}
    for ex, pos_list in positions.items():
        result[ex.value] = [p.dict() for p in pos_list]
    
    return {
        "positions": result,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/open-orders")
async def get_open_orders(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None)
):
    """Get open orders"""
    router_instance = get_exchange_router()
    
    exchange_id = None
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    orders = await router_instance.get_open_orders(exchange_id, symbol)
    
    # Convert to serializable format
    result = {}
    for ex, order_list in orders.items():
        result[ex.value] = [o.dict() for o in order_list]
    
    return {
        "open_orders": result,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/order-status/{order_id}")
async def get_order_status(
    order_id: str,
    exchange: str = Query(...),
    symbol: Optional[str] = Query(default=None)
):
    """Get order status"""
    try:
        exchange_id = ExchangeId(exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    router_instance = get_exchange_router()
    
    try:
        order = await router_instance.get_order_status(exchange_id, order_id, symbol)
        return {
            "order": order.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================
# Order Operations
# ============================================

@router.post("/create-order")
async def create_order(request: CreateOrderRequestModel):
    """Create a new order"""
    try:
        exchange_id = ExchangeId(request.exchange.upper())
        side = OrderSide(request.side.upper())
        order_type = OrderType(request.order_type.upper())
        tif = TimeInForce(request.time_in_force.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    order_request = ExchangeOrderRequest(
        exchange=exchange_id,
        symbol=request.symbol,
        side=side,
        order_type=order_type,
        size=request.size,
        price=request.price,
        stop_price=request.stop_price,
        time_in_force=tif,
        reduce_only=request.reduce_only,
        client_order_id=request.client_order_id
    )
    
    router_instance = get_exchange_router()
    
    try:
        order = await router_instance.create_order(exchange_id, order_request)
        
        # Save to repository
        repository.save_order(order)
        
        return {
            "order": order.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel-order")
async def cancel_order(request: CancelOrderRequestModel):
    """Cancel an order"""
    try:
        exchange_id = ExchangeId(request.exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {request.exchange}")
    
    router_instance = get_exchange_router()
    
    try:
        order = await router_instance.cancel_order(
            exchange_id,
            request.order_id,
            request.symbol
        )
        
        # Save to repository
        repository.save_order(order)
        
        return {
            "order": order.dict(),
            "cancelled": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel-all")
async def cancel_all_orders(
    exchange: str,
    symbol: Optional[str] = Query(default=None)
):
    """Cancel all open orders"""
    try:
        exchange_id = ExchangeId(exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    router_instance = get_exchange_router()
    
    try:
        orders = await router_instance.cancel_all_orders(exchange_id, symbol)
        
        return {
            "exchange": exchange.upper(),
            "symbol": symbol,
            "cancelled_count": len(orders),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Market Data
# ============================================

@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: Optional[str] = Query(default=None)
):
    """Get ticker for symbol"""
    router_instance = get_exchange_router()
    
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
            ticker = await router_instance.get_ticker(exchange_id, symbol)
            return {
                "ticker": ticker.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Get from all connected exchanges
    tickers = await router_instance.get_tickers(symbol)
    
    return {
        "tickers": {ex.value: t.dict() for ex, t in tickers.items()},
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query(...),
    depth: int = Query(default=20, ge=1, le=100)
):
    """Get orderbook for symbol"""
    try:
        exchange_id = ExchangeId(exchange.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    router_instance = get_exchange_router()
    
    try:
        orderbook = await router_instance.get_orderbook(exchange_id, symbol, depth)
        return {
            "orderbook": orderbook.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/best-price/{symbol}")
async def get_best_price(
    symbol: str,
    side: str = Query(default="BUY")
):
    """Get best price across exchanges"""
    router_instance = get_exchange_router()
    result = await router_instance.get_best_price(symbol, side)
    
    return {
        "best_price": result,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# WebSocket Streams
# ============================================

@router.post("/stream/start")
async def start_stream(request: StreamRequestModel):
    """Start a WebSocket stream"""
    try:
        exchange_id = ExchangeId(request.exchange.upper())
        stream_type = StreamType(request.stream_type.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    ws_manager = get_ws_manager()
    
    config = StreamConfig(
        exchange=exchange_id,
        stream_type=stream_type,
        symbols=request.symbols
    )
    
    success = await ws_manager.start_stream(config)
    
    return {
        "started": success,
        "exchange": request.exchange.upper(),
        "stream_type": request.stream_type.upper(),
        "symbols": request.symbols,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/stream/stop")
async def stop_stream(request: StreamRequestModel):
    """Stop a WebSocket stream"""
    try:
        exchange_id = ExchangeId(request.exchange.upper())
        stream_type = StreamType(request.stream_type.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    ws_manager = get_ws_manager()
    
    success = await ws_manager.stop_stream(
        exchange_id,
        stream_type,
        request.symbols if request.symbols else None
    )
    
    return {
        "stopped": success,
        "exchange": request.exchange.upper(),
        "stream_type": request.stream_type.upper(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stream/status")
async def get_stream_status(
    exchange: Optional[str] = Query(default=None),
    stream_type: Optional[str] = Query(default=None)
):
    """Get WebSocket stream status"""
    ws_manager = get_ws_manager()
    
    exchange_id = None
    st = None
    
    if exchange:
        try:
            exchange_id = ExchangeId(exchange.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown exchange: {exchange}")
    
    if stream_type:
        try:
            st = StreamType(stream_type.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown stream type: {stream_type}")
    
    status = ws_manager.get_stream_status(exchange_id, st)
    
    return {
        "streams": status,
        "active_streams": ws_manager.get_active_streams(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# History & Statistics
# ============================================

@router.get("/history/orders")
async def get_order_history(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get order history from database"""
    orders = repository.get_order_history(exchange, symbol, status, limit)
    
    return {
        "orders": orders,
        "count": len(orders),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/positions")
async def get_position_history(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get position history from database"""
    positions = repository.get_position_history(exchange, symbol, limit)
    
    return {
        "positions": positions,
        "count": len(positions),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/balances")
async def get_balance_history(
    exchange: Optional[str] = Query(default=None),
    asset: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get balance history from database"""
    balances = repository.get_balance_history(exchange, asset, limit)
    
    return {
        "balances": balances,
        "count": len(balances),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats/orders")
async def get_order_stats(days: int = Query(default=7, ge=1, le=30)):
    """Get order statistics"""
    stats = repository.get_order_stats(days)
    
    return {
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
