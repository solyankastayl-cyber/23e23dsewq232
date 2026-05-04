"""
Portfolio API Routes
"""

from fastapi import APIRouter, HTTPException
import logging

from .service import get_portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/portfolio/summary")
async def get_summary():
    """
    Get aggregated portfolio summary.
    
    Returns:
        PortfolioSummary: Current portfolio state
    """
    try:
        service = get_portfolio_service()
        summary = await service.get_summary()
        return summary
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/equity")
async def get_equity():
    """
    Get equity curve history.
    
    Returns:
        List[EquityPoint]: Historical equity snapshots
    """
    try:
        service = get_portfolio_service()
        curve = service.get_equity_curve()
        return curve
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting equity curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/allocations")
async def get_allocations():
    """
    Get asset allocation breakdown.
    
    Returns:
        List[AssetAllocation]: Asset allocations
    """
    try:
        service = get_portfolio_service()
        allocations = await service.get_allocations()
        return allocations
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting allocations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/assets")
async def get_assets():
    """
    Get asset breakdown (balances + positions).
    
    Returns:
        List[dict]: Assets with PnL and allocation
    """
    try:
        service = get_portfolio_service()
        assets = await service.get_assets()
        return assets
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/active-positions")
async def get_active_positions():
    """
    Get active positions with context.
    
    Returns:
        List[dict]: Active positions with strategy/duration
    """
    try:
        service = get_portfolio_service()
        positions = await service.get_active_positions()
        return positions
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting active positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/closed-positions")
async def get_closed_positions():
    """
    Get closed positions from cases.
    
    Returns:
        List[dict]: Closed positions with PnL
    """
    try:
        service = get_portfolio_service()
        positions = await service.get_closed_positions()
        return positions
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting closed positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/intelligence")
async def get_intelligence():
    """
    Get system intelligence metrics.
    
    Returns:
        dict: Exposure, contributions, best/worst, system mode
    """
    try:
        service = get_portfolio_service()
        intelligence = await service.get_intelligence()
        return intelligence
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/multi-equity")
async def get_multi_equity():
    """
    Get multi-asset equity breakdown (Total, BTC, ETH).
    
    Returns:
        List[dict]: Array of { timestamp, total, btc, eth }
    """
    try:
        service = get_portfolio_service()
        multi_equity = await service.get_multi_equity_curve()
        return multi_equity
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting multi-equity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/decision")
async def get_decision():
    """
    Get decision intelligence (regime, drivers, risk).
    
    Returns:
        dict: Decision layer
    """
    try:
        service = get_portfolio_service()
        decision = await service.get_decision()
        return decision
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/timeline-events")
async def get_timeline_events():
    """
    Get timeline events (entries, exits, regime changes).
    
    Returns:
        List[dict]: Timeline events
    """
    try:
        service = get_portfolio_service()
        events = await service.get_timeline_events()
        return events
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting timeline events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/narrative")
async def get_narrative():
    """
    Get portfolio narrative (summary, signals, action).
    
    Returns:
        dict: Narrative intelligence
    """
    try:
        service = get_portfolio_service()
        narrative = await service.get_narrative()
        return narrative
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting narrative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/asset-performance")
async def get_asset_performance(symbol: str):
    """
    Get asset performance over time (sparkline data).
    
    Args:
        symbol: Asset symbol (e.g., "BTC", "ETH")
    
    Returns:
        List[dict]: Performance points
    """
    try:
        service = get_portfolio_service()
        performance = await service.get_asset_performance(symbol)
        return performance
    except Exception as e:
        logger.error(f"[PortfolioRoutes] Error getting asset performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
