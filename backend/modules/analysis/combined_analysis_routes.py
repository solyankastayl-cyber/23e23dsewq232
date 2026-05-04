"""
Analysis Unification Layer — HTTP routes (Pass 3).

  GET /api/analysis/combined?symbol=BTCUSDT&tf=4H
  GET /api/analysis/health
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from modules.analysis.combined_analysis_service import get_combined_analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis-unification"])


@router.get("/health")
async def health():
    return {
        "ok": True,
        "module": "analysis_unification",
        "layer": "ANALYTICS_ONLY",
        "trading": False,
        "note": "This endpoint produces knowledge, not decisions.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/combined")
async def combined(
    symbol: str = Query("BTCUSDT", description="Trading pair, e.g. BTCUSDT"),
    tf: str = Query("4H", description="Canonical timeframe: 1H, 4H, 1D"),
):
    """
    Unified analytical view: TA + Prediction + Hypothesis with agreement scoring.

    See modules/analysis/combined_analysis_service.py for the contract.

    Honesty notes:
      * If no completed hypothesis run exists for (symbol, tf) → hypothesis is null.
      * If prediction unavailable → confidence = 0.
      * Direction conflicts produce LOW quality (no hidden inflation).
    """
    service = get_combined_analysis_service()
    return await service.get_combined(symbol=symbol, timeframe=tf)
