"""Market Intelligence API Routes"""

from fastapi import APIRouter
from typing import Dict, Any

from .scanner_runtime import get_market_opportunities, run_scanner


router = APIRouter(prefix="/api/market", tags=["market_intelligence"])


@router.get("/opportunities")
async def get_opportunities() -> Dict[str, Any]:
    """Get current market opportunities (signals).
    
    Returns cached signals or triggers fresh scan if needed.
    """
    return await get_market_opportunities()


@router.post("/scan")
async def trigger_scan() -> Dict[str, Any]:
    """Trigger immediate market scan.
    
    Forces fresh scan regardless of cache.
    """
    signals = await run_scanner()
    return {
        "status": "completed",
        "signals_count": len(signals),
        "signals": signals,
    }
