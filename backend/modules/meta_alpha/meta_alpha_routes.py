"""
Meta-Alpha Routes

PHASE 31.1 — API endpoints for Meta-Alpha Pattern Engine.

Endpoints:
- GET  /api/v1/meta-alpha/patterns/{symbol}
- GET  /api/v1/meta-alpha/strong/{symbol}
- GET  /api/v1/meta-alpha/summary/{symbol}
- POST /api/v1/meta-alpha/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .meta_alpha_engine import (
    MetaAlphaEngine,
    get_meta_alpha_engine,
)
from .meta_alpha_registry import get_meta_alpha_registry
from .meta_alpha_types import META_ALPHA_MODIFIERS


router = APIRouter(prefix="/api/v1/meta-alpha", tags=["meta-alpha"])


@router.get("/patterns/{symbol}", response_model=Dict[str, Any])
async def get_meta_patterns(
    symbol: str,
    regime: Optional[str] = None,
    hypothesis: Optional[str] = None,
):
    """
    Get all meta-alpha patterns for symbol.
    
    Returns patterns with meta_score and classification.
    """
    engine = get_meta_alpha_engine()
    
    # Set context if provided
    if regime:
        engine.set_context(symbol.upper(), regime_type=regime)
    
    # Extract patterns (or use cached)
    patterns = engine.get_patterns(symbol.upper())
    
    if not patterns:
        patterns = engine.extract_patterns(symbol.upper())
        
        # Save to MongoDB
        registry = get_meta_alpha_registry()
        registry.save_patterns_batch(symbol.upper(), patterns)
    
    # Filter if hypothesis specified
    if hypothesis:
        patterns = [p for p in patterns if p.hypothesis_type == hypothesis]
    
    return {
        "symbol": symbol.upper(),
        "total_patterns": len(patterns),
        "patterns": [
            {
                "pattern_id": p.pattern_id,
                "regime_type": p.regime_type,
                "hypothesis_type": p.hypothesis_type,
                "microstructure_state": p.microstructure_state,
                "observations": p.observations,
                "success_rate": p.success_rate,
                "avg_pnl": p.avg_pnl,
                "meta_score": p.meta_score,
                "classification": p.classification,
                "modifier": META_ALPHA_MODIFIERS.get(p.classification, 1.0),
            }
            for p in sorted(patterns, key=lambda x: x.meta_score, reverse=True)
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/strong/{symbol}", response_model=Dict[str, Any])
async def get_strong_patterns(symbol: str):
    """
    Get only strong meta-alpha patterns.
    
    Returns patterns with meta_score >= 0.70.
    """
    engine = get_meta_alpha_engine()
    
    # Ensure patterns are extracted
    if not engine.get_patterns(symbol.upper()):
        engine.extract_patterns(symbol.upper())
    
    strong = engine.get_strong_patterns(symbol.upper())
    
    return {
        "symbol": symbol.upper(),
        "total_strong": len(strong),
        "patterns": [
            {
                "pattern_id": p.pattern_id,
                "description": f"{p.regime_type} + {p.hypothesis_type} + {p.microstructure_state}",
                "meta_score": p.meta_score,
                "success_rate": p.success_rate,
                "avg_pnl": p.avg_pnl,
                "observations": p.observations,
                "modifier": p.modifier,
            }
            for p in strong
        ],
        "total_modifier_boost": sum(p.modifier - 1.0 for p in strong) if strong else 0.0,
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_meta_summary(symbol: str):
    """
    Get meta-alpha summary for symbol.
    
    Returns pattern counts, averages, and best performer.
    """
    engine = get_meta_alpha_engine()
    
    # Ensure patterns exist
    if not engine.get_patterns(symbol.upper()):
        engine.extract_patterns(symbol.upper())
    
    summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "patterns": {
            "total": summary.total_patterns,
            "valid": summary.valid_patterns,
        },
        "classification": {
            "strong": summary.strong_count,
            "moderate": summary.moderate_count,
            "weak": summary.weak_count,
        },
        "averages": {
            "meta_score": summary.avg_meta_score,
            "success_rate": summary.avg_success_rate,
            "avg_pnl": summary.avg_pnl,
        },
        "best_pattern": {
            "pattern_id": summary.best_pattern_id,
            "score": summary.best_pattern_score,
            "description": summary.best_pattern_description,
        },
        "total_observations": summary.total_observations,
        "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_patterns(
    symbol: str,
    regime: Optional[str] = None,
    microstructure: Optional[str] = None,
):
    """
    Force recompute of meta-alpha patterns.
    
    Optionally set context for new regime/microstructure.
    """
    try:
        engine = get_meta_alpha_engine()
        
        # Update context if provided
        if regime or microstructure:
            current = engine.get_context(symbol.upper())
            engine.set_context(
                symbol.upper(),
                regime_type=regime or current.get("regime_type", "NEUTRAL"),
                microstructure_state=microstructure or current.get("microstructure_state", "BALANCED"),
            )
        
        # Recompute patterns
        patterns = engine.extract_patterns(symbol.upper())
        
        # Save to MongoDB
        registry = get_meta_alpha_registry()
        registry.save_patterns_batch(symbol.upper(), patterns)
        
        # Count classifications
        strong = sum(1 for p in patterns if p.classification == "STRONG_META_ALPHA")
        moderate = sum(1 for p in patterns if p.classification == "MODERATE_META_ALPHA")
        weak = sum(1 for p in patterns if p.classification == "WEAK_PATTERN")
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "patterns_computed": len(patterns),
            "classification": {
                "strong": strong,
                "moderate": moderate,
                "weak": weak,
            },
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "description": f"{p.regime_type}+{p.hypothesis_type}+{p.microstructure_state}",
                    "meta_score": p.meta_score,
                    "classification": p.classification,
                }
                for p in sorted(patterns, key=lambda x: x.meta_score, reverse=True)[:5]
            ],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Meta-alpha recompute failed: {str(e)}",
        )


@router.post("/context/{symbol}", response_model=Dict[str, Any])
async def set_market_context(
    symbol: str,
    regime: str = "NEUTRAL",
    microstructure: str = "BALANCED",
):
    """
    Set current market context for meta-alpha tracking.
    """
    engine = get_meta_alpha_engine()
    engine.set_context(symbol.upper(), regime, microstructure)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "context": {
            "regime_type": regime,
            "microstructure_state": microstructure,
        },
        "set_at": datetime.now(timezone.utc).isoformat(),
    }
