"""
PHASE 24.1 — Fractal Context Routes

API endpoints for Fractal Intelligence module.

Endpoints:
- GET /api/v1/fractal-intelligence/context - Full FractalContext
- GET /api/v1/fractal-intelligence/summary - Compact summary
- GET /api/v1/fractal-intelligence/health - Service health check
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from .fractal_context_types import (
    FractalContext,
    FractalContextSummary,
    FractalHealthStatus,
)
from .fractal_context_engine import FractalContextEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fractal-intelligence", tags=["fractal-intelligence"])

# Singleton engine instance
_engine: Optional[FractalContextEngine] = None


def get_engine() -> FractalContextEngine:
    """Get or create engine singleton."""
    global _engine
    if _engine is None:
        _engine = FractalContextEngine()
    return _engine


@router.get("/context", response_model=FractalContext)
async def get_fractal_context(
    symbol: str = Query(default="BTC", description="Asset symbol")
) -> FractalContext:
    """
    Get full FractalContext with all computed fields.
    
    Returns complete fractal intelligence signal including:
    - Direction (LONG/SHORT/HOLD)
    - Confidence and reliability scores
    - Per-horizon breakdown
    - Market phase
    - Context state (SUPPORTIVE/NEUTRAL/CONFLICTED/BLOCKED)
    - Human-readable explanation
    """
    engine = get_engine()
    context = await engine.build_context(symbol)
    
    logger.info(
        f"Fractal context: {context.direction} "
        f"conf={context.confidence:.2f} rel={context.reliability:.2f} "
        f"state={context.context_state}"
    )
    
    return context


@router.get("/summary", response_model=FractalContextSummary)
async def get_fractal_summary(
    symbol: str = Query(default="BTC", description="Asset symbol")
) -> FractalContextSummary:
    """
    Get compact fractal summary for quick access.
    
    Returns:
    - direction
    - confidence
    - reliability
    - phase
    - dominant_horizon
    - context_state
    - fractal_strength
    """
    engine = get_engine()
    context = await engine.build_context(symbol)
    return engine.get_summary(context)


@router.get("/health", response_model=FractalHealthStatus)
async def get_fractal_health() -> FractalHealthStatus:
    """
    Check fractal service health.
    
    Returns:
    - connected: whether TS fractal service is reachable
    - governance_mode: current governance mode
    - status: OK/DEGRADED/ERROR/UNAVAILABLE
    - last_signal_ts: timestamp of last successful fetch
    - latency_ms: response latency
    """
    engine = get_engine()
    return await engine.get_health()


@router.get("/info")
async def get_fractal_info() -> dict:
    """
    Get module information.
    """
    return {
        "module": "fractal_intelligence",
        "version": "24.1",
        "phase": "PHASE 24.1 - Fractal Context Adapter",
        "description": "Isolated fractal intelligence layer providing third signal leg",
        "architecture": {
            "isolation": "strict",
            "dependencies": ["httpx"],
            "exports": ["FractalContext", "FractalContextSummary", "FractalHealthStatus"],
        },
        "endpoints": {
            "context": "GET /api/v1/fractal-intelligence/context",
            "summary": "GET /api/v1/fractal-intelligence/summary",
            "health": "GET /api/v1/fractal-intelligence/health",
            "info": "GET /api/v1/fractal-intelligence/info",
        },
        "context_states": {
            "SUPPORTIVE": "Strong directional signal with good reliability",
            "NEUTRAL": "No clear directional edge",
            "CONFLICTED": "Directional but low reliability or mixed horizons",
            "BLOCKED": "Governance restricted or very low reliability",
        },
        "source_endpoints": {
            "signal": "GET /api/fractal/v2.1/signal",
            "phase": "GET /api/fractal/v2.1/phase",
            "reliability": "GET /api/fractal/v2.1/reliability",
        },
    }
