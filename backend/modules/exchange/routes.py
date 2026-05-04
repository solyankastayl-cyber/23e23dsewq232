"""Exchange API Routes — Week 3 + Binance Demo Integration"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .service import exchange_service
from .service_v2 import get_exchange_service
from .models import OrderRequest

router = APIRouter(prefix="/api/exchange", tags=["exchange"])


class ConnectRequest(BaseModel):
    """Exchange connection request."""
    mode: str  # PAPER, BINANCE_TESTNET, BYBIT_DEMO
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    config: Dict[str, Any] = {}


@router.post("/connect")
async def connect_exchange(request: ConnectRequest) -> Dict[str, Any]:
    """Connect to exchange (V2 — uses ExchangeService V2).
    
    For PAPER mode: no credentials needed
    For BINANCE_TESTNET: requires api_key and api_secret
    """
    try:
        service = get_exchange_service()
        
        # Disconnect current
        if service.is_connected():
            await service.disconnect()
        
        # Prepare config
        config = request.config.copy()
        config["account_id"] = f"{request.mode.lower()}_default"
        
        if request.mode == "BINANCE_TESTNET":
            if not request.api_key or not request.api_secret:
                raise HTTPException(status_code=400, detail="BINANCE_TESTNET requires api_key and api_secret")
            
            config["api_key"] = request.api_key
            config["api_secret"] = request.api_secret
        
        elif request.mode == "PAPER":
            config["initial_balance"] = 10000.0
        
        # Connect
        success = await service.connect(request.mode, config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to connect to exchange")
        
        # Get account info after connection
        adapter = service.get_adapter()
        account_info = await adapter.get_account_info()
        
        return {
            "ok": True,
            "connected": True,
            "mode": request.mode,
            "account": account_info.dict(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_exchange() -> Dict[str, Any]:
    """Disconnect from exchange."""
    success = await exchange_service.disconnect()
    
    return {
        "ok": True,
        "disconnected": success,
    }


@router.get("/status")
async def get_exchange_status() -> Dict[str, Any]:
    """Get exchange connection status (V2 — uses ExchangeService V2)."""
    try:
        service = get_exchange_service()
        
        if not service.is_connected():
            return {
                "ok": True,
                "connected": False,
                "mode": None,
                "account_id": None
            }
        
        adapter = service.get_adapter()
        account_info = await adapter.get_account_info()
        
        return {
            "ok": True,
            "connected": True,
            "mode": service.current_mode,
            "exchange": account_info.exchange,
            "account_id": account_info.account_id,
            "can_trade": account_info.can_trade,
            "status": account_info.status,
            "adapter_type": adapter.__class__.__name__
        }
    except Exception as e:
        return {
            "ok": False,
            "connected": False,
            "error": str(e)
        }


@router.get("/account")
async def get_account() -> Dict[str, Any]:
    """Get account information."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        adapter = exchange_service.get_adapter()
        account_info = await adapter.get_account_info()
        
        return {
            "ok": True,
            "account": account_info.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances")
async def get_balances() -> Dict[str, Any]:
    """Get account balances."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        adapter = exchange_service.get_adapter()
        balances = await adapter.get_balances()
        
        return {
            "ok": True,
            "balances": [b.dict() for b in balances],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-order")
async def submit_test_order() -> Dict[str, Any]:
    """Submit a small test order to verify exchange connection."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        import time
        adapter = exchange_service.get_adapter()
        
        # Create small test order with unique client_order_id
        test_order = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,  # $67 worth
            client_order_id=f"test-order-{int(time.time() * 1000)}",
        )
        
        response = await adapter.place_order(test_order)
        
        return {
            "ok": True,
            "test_order": response.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_exchange_positions() -> Dict[str, Any]:
    """Get positions from exchange."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        adapter = exchange_service.get_adapter()
        positions = await adapter.get_positions()
        
        return {
            "ok": True,
            "positions": [p.dict() for p in positions],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_exchange_orders(symbol: Optional[str] = None) -> Dict[str, Any]:
    """Get open orders from exchange."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        adapter = exchange_service.get_adapter()
        orders = await adapter.get_open_orders(symbol=symbol)
        
        return {
            "ok": True,
            "orders": [o.dict() for o in orders],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fills")
async def get_exchange_fills(symbol: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Get recent fills from exchange."""
    if not exchange_service.is_connected():
        raise HTTPException(status_code=400, detail="Exchange not connected")
    
    try:
        adapter = exchange_service.get_adapter()
        fills = await adapter.get_recent_fills(symbol=symbol, limit=limit)
        
        return {
            "ok": True,
            "fills": fills,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/health")
async def get_exchange_health() -> Dict[str, Any]:
    """
    Get exchange health metrics (latency, sync status, error rate).
    """
    try:
        from modules.exchange.sync_service import get_sync_service
        
        service = get_exchange_service()
        
        if not service.is_connected():
            return {
                "ok": False,
                "connected": False,
                "latency_ms": None,
                "last_sync_seconds": None,
                "error_rate": None
            }
        
        # Get sync status
        try:
            sync_service = get_sync_service()
            sync_status = await sync_service.get_sync_status()
            
            last_sync_at = sync_status.get("last_sync_at")
            last_sync_seconds = int(time.time()) - last_sync_at if last_sync_at else None
        except:
            last_sync_seconds = None
        
        # TODO: Measure actual latency (ping exchange)
        
        return {
            "ok": True,
            "connected": True,
            "latency_ms": 120,  # Placeholder
            "last_sync_seconds": last_sync_seconds,
            "error_rate": 0.0  # Placeholder
        }
    
    except Exception as e:
        logger.error(f"[ExchangeRoutes] Health check failed: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@router.post("/sync")
async def force_exchange_sync():
    """Force immediate exchange sync."""
    try:
        from modules.exchange.sync_service import get_sync_service
        
        sync_service = get_sync_service()
        result = await sync_service.sync()
        
        return result
    
    except Exception as e:
        logger.error(f"[ExchangeRoutes] Force sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
