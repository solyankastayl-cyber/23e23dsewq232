"""
Execution Quality API Routes
==============================

Phase 3.1: Independent API layer for execution quality validation.

ARCHITECTURE NOTE:
  This router is DECOUPLED from experiments router.
  Execution quality is a safety system - it cannot depend on unstable layers.

Endpoints:
  GET /api/execution-quality  - Get execution quality report

Purpose:
  Prove that paper execution does NOT destroy discovery system's alpha.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import os

logger = logging.getLogger(__name__)

# Independent router (not nested under experiments)
router = APIRouter(
    prefix="/api/execution-quality",
    tags=["Phase 3.1 - Execution Quality"]
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
async def get_execution_quality(
    experiment_id: str = "market_dynamic",
    horizon: str = "24h",
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get execution quality report.
    
    Compares shadow_trades (ideal) vs paper_positions (real execution)
    to prove that execution layer does NOT corrupt discovery edge.
    
    Args:
        experiment_id: Experiment ID (default: market_dynamic)
        horizon: Time horizon for comparison (default: 24h)
    
    Returns:
        {
            "ok": True,
            "report": {
                "summary": {
                    "matched_pairs": int,
                    "shadow_trades": int,
                    "paper_positions": int,
                    "match_coverage": float,
                    "execution_quality": float,
                    "shadow_winrate": float,
                    "paper_winrate": float,
                    "winrate_delta": float
                },
                "frictions": {
                    "policy_rejection_rate": float,
                    "cooldown_miss_rate": float,
                    "avg_entry_delay_pct": float,
                    "max_entry_delay_pct": float
                },
                "verdict": {
                    "state": "ready" | "limited" | "blocked",
                    "reason": str,
                    "gates_passed": [str],
                    "gates_failed": [str]
                },
                "thresholds": {...}
            }
        }
    
    Gates:
      1. match_coverage >= 0.7
      2. execution_quality > -0.001
      3. winrate_delta >= -0.05
      4. policy_rejection_rate <= 0.35
      5. cooldown_miss_rate <= 0.20
      6. matched_pairs >= 20
    
    Verdict:
      - ready: All gates pass → safe for auto-run
      - limited: Quality ok but warnings → review before auto-run
      - blocked: Quality issues → do NOT enable auto-run
    """
    try:
        from modules.strategy.execution_analysis.execution_quality_service import ExecutionQualityService
        
        service = ExecutionQualityService(db)
        report = await service.get_execution_quality(
            experiment_id=experiment_id,
            horizon=horizon
        )
        
        return {
            "ok": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"[ExecutionQualityAPI] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
