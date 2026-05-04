"""
Market Data Routes - PHASE 5.2
==============================

REST API endpoints for Live Market Data Engine.

Endpoints:
- POST /api/market-data/start
- POST /api/market-data/stop
- GET  /api/market-data/status
- GET  /api/market-data/snapshot/{symbol}
- GET  /api/market-data/ticker/{symbol}
- GET  /api/market-data/orderbook/{symbol}
- GET  /api/market-data/candles/{symbol}/{timeframe}
- GET  /api/market-data/volume/{symbol}
- GET  /api/market-data/exchanges
- GET  /api/market-data/history/{symbol}
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .market_data_types import (
    StartFeedRequest,
    StopFeedRequest,
    MarketFeedConfig
)
from .market_data_engine import get_market_data_engine
from .market_data_repository import MarketDataRepository


router = APIRouter(prefix="/api/market-data", tags=["Market Data Engine"])

# Initialize
repository = MarketDataRepository()


# ============================================
# Request Models
# ============================================

class StartRequest(BaseModel):
    """Start feed request"""
    exchange: str = "BINANCE"
    symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT"])
    subscribe_ticker: bool = True
    subscribe_orderbook: bool = True
    subscribe_candles: bool = True
    candle_timeframes: List[str] = Field(default_factory=lambda: ["1m", "5m", "1h"])


class StopRequest(BaseModel):
    """Stop feed request"""
    exchange: str = "BINANCE"
    symbols: List[str] = Field(default_factory=list)


# ============================================
# Health & Status
# ============================================

@router.get("/health")
async def market_data_health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "phase_5.2",
        "components": [
            "market_data_engine",
            "ticker_processor",
            "orderbook_processor",
            "candle_builder",
            "volume_processor",
            "snapshot_builder"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def get_status(exchange: Optional[str] = Query(default=None)):
    """Get market data engine status"""
    engine = get_market_data_engine()
    
    if exchange:
        return {
            "exchange": exchange.upper(),
            "feed_status": engine.get_feed_status(exchange),
            "subscribed_symbols": engine.get_subscribed_symbols(exchange),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "engine_status": engine.get_engine_status(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Feed Management
# ============================================

@router.post("/start")
async def start_feed(request: StartRequest):
    """Start market data feed"""
    engine = get_market_data_engine()
    
    config = MarketFeedConfig(
        exchange=request.exchange.upper(),
        symbols=request.symbols,
        subscribe_ticker=request.subscribe_ticker,
        subscribe_orderbook=request.subscribe_orderbook,
        subscribe_candles=request.subscribe_candles,
        candle_timeframes=request.candle_timeframes
    )
    
    success = await engine.start_feed(config)
    
    return {
        "started": success,
        "exchange": request.exchange.upper(),
        "symbols": request.symbols,
        "subscriptions": {
            "ticker": request.subscribe_ticker,
            "orderbook": request.subscribe_orderbook,
            "candles": request.subscribe_candles
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/stop")
async def stop_feed(request: StopRequest):
    """Stop market data feed"""
    engine = get_market_data_engine()
    
    success = await engine.stop_feed(
        request.exchange,
        request.symbols if request.symbols else None
    )
    
    return {
        "stopped": success,
        "exchange": request.exchange.upper(),
        "symbols": request.symbols,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/stop-all")
async def stop_all_feeds():
    """Stop all market data feeds"""
    engine = get_market_data_engine()
    success = await engine.stop_all()
    
    return {
        "stopped": success,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Live Data Access
# ============================================

@router.get("/snapshot/{symbol}")
async def get_snapshot(symbol: str):
    """Get live market snapshot for symbol"""
    engine = get_market_data_engine()
    snapshot = engine.get_live_snapshot(symbol.upper())
    
    return {
        "snapshot": snapshot.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: str = Query(default="BINANCE")
):
    """Get live ticker for symbol"""
    engine = get_market_data_engine()
    tick = engine.get_live_ticker(exchange, symbol)
    
    if not tick:
        return {
            "error": "No ticker data available",
            "symbol": symbol,
            "exchange": exchange,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "ticker": tick.dict(),
        "spread": engine.get_spread_info(exchange, symbol),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query(default="BINANCE")
):
    """Get live orderbook for symbol"""
    engine = get_market_data_engine()
    orderbook = engine.get_live_orderbook(exchange, symbol)
    
    if not orderbook:
        return {
            "error": "No orderbook data available",
            "symbol": symbol,
            "exchange": exchange,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "orderbook": orderbook.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/candles/{symbol}/{timeframe}")
async def get_candles(
    symbol: str,
    timeframe: str,
    exchange: str = Query(default="BINANCE"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """Get live candles for symbol"""
    engine = get_market_data_engine()
    candles = engine.get_live_candles(exchange, symbol, timeframe, limit)
    
    return {
        "exchange": exchange.upper(),
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "count": len(candles),
        "candles": [c.dict() for c in candles],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/current-candle/{symbol}/{timeframe}")
async def get_current_candle(
    symbol: str,
    timeframe: str,
    exchange: str = Query(default="BINANCE")
):
    """Get current open candle"""
    engine = get_market_data_engine()
    candle = engine.get_current_candle(exchange, symbol, timeframe)
    
    if not candle:
        return {
            "error": "No current candle",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "candle": candle.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/volume/{symbol}")
async def get_volume(
    symbol: str,
    exchange: str = Query(default="BINANCE")
):
    """Get volume metrics for symbol"""
    engine = get_market_data_engine()
    metrics = engine.get_volume_metrics(exchange, symbol)
    
    if not metrics:
        return {
            "error": "No volume data available",
            "symbol": symbol,
            "exchange": exchange,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "volume_metrics": metrics.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/price/{symbol}")
async def get_price(
    symbol: str,
    exchange: str = Query(default="BINANCE")
):
    """Get latest price for symbol"""
    engine = get_market_data_engine()
    price = engine.get_price(exchange, symbol)
    
    return {
        "exchange": exchange.upper(),
        "symbol": symbol.upper(),
        "price": price,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Exchange Info
# ============================================

@router.get("/exchanges")
async def get_exchanges():
    """Get list of active exchanges"""
    engine = get_market_data_engine()
    
    return {
        "active_exchanges": engine.get_active_feeds(),
        "subscriptions": engine.get_subscribed_symbols(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Historical Data
# ============================================

@router.get("/history/candles/{symbol}/{timeframe}")
async def get_candle_history(
    symbol: str,
    timeframe: str,
    exchange: str = Query(default="BINANCE"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get historical candles from database"""
    candles = repository.get_candles(
        exchange, symbol, timeframe, limit=limit
    )
    
    return {
        "exchange": exchange.upper(),
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/ticks/{symbol}")
async def get_tick_history(
    symbol: str,
    exchange: str = Query(default="BINANCE"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get historical ticks from database"""
    ticks = repository.get_ticks(exchange, symbol, limit=limit)
    
    return {
        "exchange": exchange.upper(),
        "symbol": symbol.upper(),
        "count": len(ticks),
        "ticks": ticks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/snapshots/{symbol}")
async def get_snapshot_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get historical snapshots from database"""
    snapshots = repository.get_snapshots(symbol, limit=limit)
    
    return {
        "symbol": symbol.upper(),
        "count": len(snapshots),
        "snapshots": snapshots,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats/candles/{symbol}")
async def get_candle_stats(
    symbol: str,
    timeframe: str = Query(default="1h"),
    days: int = Query(default=7, ge=1, le=30)
):
    """Get candle statistics"""
    stats = repository.get_candle_stats(symbol, timeframe, days)
    
    return {
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
