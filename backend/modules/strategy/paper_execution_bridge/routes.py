"""
Paper Performance API Routes
==============================

Phase 3.0A: Independent API layer for paper execution performance.

ARCHITECTURE NOTE:
  This router is DECOUPLED from experiments router.
  Paper performance is operational visibility - must be stable.

Endpoints:
  GET /api/paper-performance  - Get paper execution performance
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import os

logger = logging.getLogger(__name__)

# Independent router
router = APIRouter(
    prefix="/api/paper-performance",
    tags=["Phase 3.0A - Paper Performance"]
)


async def get_db():
    """Get MongoDB database."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        return db
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database not available: {e}")


@router.get("")
async def get_paper_performance(
    experiment_id: str = "market_dynamic",
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get paper execution performance.
    
    Provides operational visibility into paper positions:
      - Open positions count (for position limit check)
      - Closed positions count
      - Performance metrics (winrate, avg PnL)
    
    Args:
        experiment_id: Experiment ID (default: market_dynamic)
    
    Returns:
        {
            "ok": True,
            "performance": {
                "open_positions": int,
                "closed_positions": int,
                "total_positions": int,
                "winrate": float,
                "avg_pnl": float,
                "total_pnl": float
            }
        }
    """
    try:
        from modules.strategy.paper_execution_bridge.paper_position_repository import PaperPositionRepository
        
        repo = PaperPositionRepository(db)
        
        # Get open positions
        open_positions = await repo.count_open_positions(experiment_id)
        
        # Get all closed positions
        closed_positions_cursor = repo.collection.find({
            "experiment_id": experiment_id,
            "status": "CLOSED"
        })
        
        closed_positions_list = await closed_positions_cursor.to_list(length=None)
        closed_count = len(closed_positions_list)
        
        # Calculate metrics
        if closed_count > 0:
            wins = sum(1 for p in closed_positions_list if p.get("pnl_pct", 0) > 0)
            winrate = wins / closed_count
            
            avg_pnl = sum(p.get("pnl_pct", 0) for p in closed_positions_list) / closed_count
            total_pnl = sum(p.get("pnl_usd", 0) for p in closed_positions_list)
        else:
            winrate = 0.0
            avg_pnl = 0.0
            total_pnl = 0.0
        
        return {
            "ok": True,
            "performance": {
                "open_positions": open_positions,
                "closed_positions": closed_count,
                "total_positions": open_positions + closed_count,
                "winrate": round(winrate, 4),
                "avg_pnl": round(avg_pnl, 6),
                "total_pnl": round(total_pnl, 2)
            }
        }
    except Exception as e:
        logger.error(f"[PaperPerformanceAPI] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
