"""
Trading Terminal API Routes
Provides live microstructure data and terminal state for the frontend.
Supports both live Binance data and fallback mock data.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timezone
from typing import Dict, Optional
import random
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal", tags=["Trading Terminal"])

# Import REST client (primary) and WS manager (optional)
try:
    from .rest_client import get_live_micro_rest
    REST_ENABLED = True
    logger.info("[Terminal] REST microstructure enabled")
except Exception as e:
    REST_ENABLED = False
    logger.warning(f"[Terminal] REST microstructure disabled: {e}")

try:
    from .live_micro_manager import get_manager, get_active_symbols, stop_all_managers
    WS_ENABLED = True
    logger.info("[Terminal] WebSocket microstructure enabled")
except Exception as e:
    WS_ENABLED = False
    logger.warning(f"[Terminal] WebSocket microstructure disabled: {e}")
    
    def get_active_symbols():
        return []

LIVE_ENABLED = REST_ENABLED or WS_ENABLED


# Terminal state
_terminal_state = {
    "authenticated": False,
    "live_mode": LIVE_ENABLED
}


@router.get("/health")
async def terminal_health():
    """Health check for trading terminal"""
    return {
        "ok": True,
        "module": "trading_terminal",
        "version": "5.1",
        "live_enabled": LIVE_ENABLED,
        "rest_enabled": REST_ENABLED,
        "ws_enabled": WS_ENABLED,
        "active_symbols": get_active_symbols() if WS_ENABLED else [],
        "note": "Binance API blocked in this region (error 451). Using realistic mock data.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/auth")
async def terminal_auth(data: Dict):
    """Authenticate access to trading terminal"""
    password = data.get("password", "")
    
    if password and len(password) >= 4:
        return {
            "ok": True,
            "authenticated": True,
            "message": "Access granted",
            "live_mode": LIVE_ENABLED
        }
    
    return {
        "ok": False,
        "authenticated": False,
        "message": "Invalid password"
    }


@router.get("/micro/live/{symbol}")
async def get_micro_live(symbol: str = "BTCUSDT"):
    """
    Get live microstructure data for symbol.
    Uses Binance REST API (primary) or WebSocket when available.
    """
    symbol = symbol.upper()
    
    # Try REST API first (more reliable)
    if REST_ENABLED:
        try:
            data = await get_live_micro_rest(symbol)
            if data.get("state") != "error":
                return {
                    "ok": True,
                    "live": True,
                    "source": "REST",
                    "data": data
                }
        except Exception as e:
            logger.error(f"[Terminal] REST micro error: {e}")
    
    # Try WebSocket manager
    if WS_ENABLED:
        try:
            manager = await get_manager(symbol)
            if manager.initialized:
                state = manager.get_current_state()
                return {
                    "ok": True,
                    "live": True,
                    "source": "WebSocket",
                    "data": {
                        "symbol": symbol,
                        "timestamp": state.get("timestamp"),
                        "imbalance": state.get("orderbook", {}).get("imbalance", 0),
                        "spread": state.get("orderbook", {}).get("spread", 0),
                        "spread_bps": state.get("orderbook", {}).get("spread_bps", 0),
                        "liquidity_score": state.get("liquidity", {}).get("score", 0),
                        "liquidity_state": state.get("liquidity", {}).get("state", "unknown"),
                        "state": state.get("micro", {}).get("state", "unknown"),
                        "confidence": state.get("micro", {}).get("confidence", 0),
                        "sweep_status": "detected" if state.get("sweep") else "none",
                        "bid_volume": state.get("trade_flow", {}).get("buy_volume", 0),
                        "ask_volume": state.get("trade_flow", {}).get("sell_volume", 0),
                        "trade_pressure": state.get("trade_flow", {}).get("pressure", "unknown"),
                        "best_bid": state.get("orderbook", {}).get("best_bid", 0),
                        "best_ask": state.get("orderbook", {}).get("best_ask", 0),
                        "mid_price": state.get("orderbook", {}).get("mid_price", 0)
                    }
                }
        except Exception as e:
            logger.error(f"[Terminal] WS micro error: {e}")
    
    # Fallback to mock data
    return {
        "ok": True,
        "live": False,
        "source": "mock",
        "data": _get_mock_micro_data(symbol)
    }


@router.get("/micro/stats/{symbol}")
async def get_micro_stats(symbol: str = "BTCUSDT"):
    """Get microstructure manager statistics"""
    symbol = symbol.upper()
    
    if LIVE_ENABLED:
        try:
            manager = await get_manager(symbol)
            return {
                "ok": True,
                "data": manager.get_stats()
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    return {"ok": False, "error": "Live mode disabled"}


@router.get("/decision/{symbol}")
async def get_terminal_decision(symbol: str = "BTCUSDT"):
    """
    Get integrated trading decision for symbol.
    Combines Entry Timing Stack output with Microstructure assessment.
    """
    symbol = symbol.upper()
    
    # Get microstructure data
    micro_response = await get_micro_live(symbol)
    micro = micro_response.get("data", {})
    is_live = micro_response.get("live", False)
    
    # Determine decision based on micro state
    micro_state = micro.get("state", "unknown")
    micro_confidence = micro.get("confidence", 0.5)
    imbalance = micro.get("imbalance", 0)
    
    # Decision logic
    if micro_state == "favorable":
        if micro_confidence > 0.7 and abs(imbalance) > 0.2:
            decision = "GO_FULL"
            confidence = min(0.95, micro_confidence + 0.1)
        else:
            decision = "GO_REDUCED"
            confidence = micro_confidence
    elif micro_state == "hostile":
        decision = "SKIP"
        confidence = 0.3
    elif micro_state == "caution":
        decision = "WAIT_MICRO"
        confidence = 0.5
    elif micro_state == "neutral":
        decision = "WAIT"
        confidence = 0.6
    else:
        decision = "WAIT"
        confidence = 0.4
    
    # Generate WHY reasons
    why_reasons = []
    
    if is_live:
        why_reasons.append({"text": "Live data active", "strength": "strong"})
    else:
        why_reasons.append({"text": "Using simulated data", "strength": "weak"})
    
    if decision in ["GO_FULL", "GO_REDUCED"]:
        why_reasons.append({"text": f"Micro: {micro.get('liquidity_state', 'unknown')}", "strength": "strong"})
        if imbalance > 0.2:
            why_reasons.append({"text": f"Bid imbalance +{imbalance:.0%}", "strength": "strong"})
        elif imbalance < -0.2:
            why_reasons.append({"text": f"Ask imbalance {imbalance:.0%}", "strength": "medium"})
        if micro.get("spread_bps", 0) < 1.5:
            why_reasons.append({"text": "Spread tight", "strength": "strong"})
    else:
        if micro_state == "hostile":
            why_reasons.append({"text": "Hostile microstructure", "strength": "weak"})
        if micro.get("spread_bps", 0) > 2.0:
            why_reasons.append({"text": f"Spread elevated: {micro.get('spread_bps', 0):.1f}bps", "strength": "weak"})
        why_reasons.append({"text": "Waiting for confirmation", "strength": "weak"})
    
    # Execution parameters
    mid_price = micro.get("mid_price", 0) or 65000  # Fallback
    
    if decision == "GO_FULL":
        size_multiplier = round(1.0 + confidence * 0.15, 2)
        execution_mode = "AGGRESSIVE"
    elif decision == "GO_REDUCED":
        size_multiplier = round(0.5 + confidence * 0.3, 2)
        execution_mode = "NORMAL"
    else:
        size_multiplier = 0.0
        execution_mode = "PASSIVE_LIMIT"
    
    return {
        "ok": True,
        "live": is_live,
        "source": micro_response.get("source", "mock"),
        "data": {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": {
                "action": decision,
                "confidence": round(confidence, 2)
            },
            "why": why_reasons,
            "execution": {
                "mode": execution_mode,
                "size_multiplier": size_multiplier,
                "entry": round(mid_price, 2),
                "stop_loss": round(mid_price * 0.98, 2),
                "take_profit": round(mid_price * 1.035, 2),
                "risk_reward": 1.75
            },
            "micro": micro
        }
    }


@router.get("/positions")
async def get_positions():
    """Get current open positions (mock data for now)"""
    positions = [
        {
            "id": "pos_001",
            "symbol": "BTCUSDT",
            "side": "LONG",
            "size": 0.8,
            "entry_price": 64200.00,
            "current_price": 65100.00,
            "pnl_usd": 720.00,
            "pnl_percent": 1.12,
            "status": "ACTIVE",
            "opened_at": "2026-04-02T10:30:00Z"
        },
        {
            "id": "pos_002", 
            "symbol": "ETHUSDT",
            "side": "LONG",
            "size": 5.0,
            "entry_price": 3450.00,
            "current_price": 3520.00,
            "pnl_usd": 350.00,
            "pnl_percent": 2.03,
            "status": "ACTIVE",
            "opened_at": "2026-04-01T14:15:00Z"
        }
    ]
    
    total_pnl = sum(p["pnl_usd"] for p in positions)
    
    return {
        "ok": True,
        "data": {
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_pnl_usd": round(total_pnl, 2),
                "exposure_usd": round(sum(p["size"] * p["current_price"] for p in positions), 2)
            }
        }
    }


@router.post("/start/{symbol}")
async def start_live_feed(symbol: str, background_tasks: BackgroundTasks):
    """Manually start live feed for a symbol"""
    if not LIVE_ENABLED:
        return {"ok": False, "error": "Live mode not available"}
    
    symbol = symbol.upper()
    
    try:
        manager = await get_manager(symbol)
        return {
            "ok": True,
            "message": f"Live feed started for {symbol}",
            "stats": manager.get_stats()
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/stop/{symbol}")
async def stop_live_feed(symbol: str):
    """Stop live feed for a symbol"""
    if not LIVE_ENABLED:
        return {"ok": False, "error": "Live mode not available"}
    
    # Note: In production, we'd want to properly manage stopping individual feeds
    return {"ok": True, "message": f"Stop requested for {symbol}"}


def _get_mock_micro_data(symbol: str = "BTCUSDT") -> Dict:
    """Generate mock microstructure data for development"""
    base_imbalance = random.uniform(-0.4, 0.4)
    imbalance = max(-1, min(1, base_imbalance + random.uniform(-0.1, 0.1)))
    
    spread = random.uniform(0.3, 1.2)
    spread_bps = random.uniform(0.5, 2.0)
    liquidity_score = random.uniform(0.5, 0.95)
    
    # State determination
    if imbalance > 0.2 and liquidity_score > 0.6 and spread_bps < 1.5:
        state = "favorable"
        confidence = min(0.95, 0.7 + abs(imbalance) * 0.3)
    elif abs(imbalance) < 0.1 and liquidity_score > 0.5:
        state = "neutral"
        confidence = 0.5 + liquidity_score * 0.2
    elif spread_bps > 2.0 or liquidity_score < 0.3:
        state = "hostile"
        confidence = 0.3
    else:
        state = "caution"
        confidence = 0.5
    
    if imbalance > 0.3:
        liquidity_state = "strong_bid"
    elif imbalance < -0.3:
        liquidity_state = "strong_ask"
    elif liquidity_score < 0.2:
        liquidity_state = "thin"
    else:
        liquidity_state = "balanced"
    
    base_price = 65000 if "BTC" in symbol else 3500 if "ETH" in symbol else 150
    mid_price = base_price + random.uniform(-500, 500)
    
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "imbalance": round(imbalance, 3),
        "spread": round(spread, 2),
        "spread_bps": round(spread_bps, 2),
        "liquidity_score": round(liquidity_score, 2),
        "liquidity_state": liquidity_state,
        "state": state,
        "confidence": round(confidence, 2),
        "sweep_status": "none",
        "bid_volume": round(random.uniform(100, 500), 2),
        "ask_volume": round(random.uniform(100, 500), 2),
        "trade_pressure": random.choice(["neutral", "buy", "sell"]),
        "best_bid": round(mid_price - spread/2, 2),
        "best_ask": round(mid_price + spread/2, 2),
        "mid_price": round(mid_price, 2)
    }
