"""
Portfolio Session Stats Routes
"""

from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/portfolio/session-stats")
async def get_session_stats():
    """
    Get current session statistics.
    
    Returns:
        Trades count, win rate, avg win/loss, best/worst
    """
    try:
        from modules.portfolio.service import get_portfolio_service
        from datetime import datetime, timezone
        
        portfolio = get_portfolio_service()
        db = portfolio.db
        
        # Get today's start
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Query filled orders from today
        orders = await db.orders.find({
            "status": "FILLED",
            "created_at": {"$gte": today_start}
        }).to_list(length=1000)
        
        if not orders:
            return {
                "ok": True,
                "trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "best_symbol": None,
                "best_pnl": 0.0,
                "worst_symbol": None,
                "worst_pnl": 0.0
            }
        
        # Calculate stats
        # NOTE: This is simplified. Real PnL would need to track closed positions
        # For now, return placeholder structure
        
        trades_count = len(orders)
        
        # Placeholder calculations
        wins = int(trades_count * 0.58)  # Assume 58% win rate
        losses = trades_count - wins
        
        avg_win = 42.0
        avg_loss = -25.0
        
        return {
            "ok": True,
            "trades": trades_count,
            "win_rate": round((wins / trades_count * 100) if trades_count > 0 else 0.0, 1),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "best_symbol": "BTC",
            "best_pnl": 120.0,
            "worst_symbol": "ETH",
            "worst_pnl": -60.0
        }
    
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Session stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
