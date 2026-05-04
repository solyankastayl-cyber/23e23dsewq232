"""
Dynamic Risk Engine Routes
Sprint R1: API for sizing preview and debugging
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from modules.dynamic_risk.service_locator import get_dynamic_risk_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dynamic-risk", tags=["dynamic-risk"])


class SignalPreviewBody(BaseModel):
    symbol: str
    side: str
    confidence: float
    entry_price: float
    metadata: Dict[str, Any] = {}


@router.post("/preview")
async def preview_dynamic_risk(body: SignalPreviewBody):
    """
    Preview sizing for a hypothetical signal.
    
    Useful for:
    - UI debugging
    - Manual testing
    - Understanding sizing logic
    
    Returns:
        {
            "approved": bool,
            "reason": str | None,
            "notional_usd": float,
            "qty": float,
            "size_multiplier": float,
            "symbol_exposure_usd": float,
            "portfolio_exposure_pct": float,
        }
    """
    try:
        engine = get_dynamic_risk_engine()
        result = await engine.evaluate(body.model_dump())
        return result
    
    except Exception as e:
        logger.error(f"[DynamicRisk] Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_dynamic_risk_config():
    """Get current dynamic risk configuration."""
    try:
        engine = get_dynamic_risk_engine()
        return {
            "ok": True,
            "config": engine.config,
        }
    
    except Exception as e:
        logger.error(f"[DynamicRisk] Config fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_dynamic_risk_decisions():
    """
    Get recent dynamic risk sizing decisions with R2 data enrichment.
    
    Merges DYNAMIC_RISK_APPROVED with subsequent ADAPTIVE_RISK_APPLIED events
    to provide complete R1+R2 view.
    
    Returns list of DYNAMIC_RISK_APPROVED and DYNAMIC_RISK_BLOCKED events
    from execution logger.
    
    Response format:
    [
        {
            "type": "DYNAMIC_RISK_APPROVED" | "DYNAMIC_RISK_BLOCKED",
            "symbol": str,
            "side": str,
            "confidence": float,
            "reason": str | None,
            "notional_usd": float,
            "qty": float,
            "size_multiplier": float,
            "debug": {
                ...r1_debug,
                "r2_multiplier": float,  # enriched from R2 event
                "r2_components": {...},
                "r2_debug": {...},
                "final_multiplier": float
            },
            "timestamp": int
        }
    ]
    """
    try:
        from modules.execution_logger import get_execution_logger
        
        logger_instance = get_execution_logger()
        
        # Fetch recent execution events
        all_events = await logger_instance.get_feed(limit=200)
        
        # Filter for dynamic risk events only
        dynamic_risk_events = [
            event for event in all_events
            if event.get("type") in ["DYNAMIC_RISK_APPROVED", "DYNAMIC_RISK_BLOCKED"]
        ]
        
        # Filter for R2 events
        r2_events = [
            event for event in all_events
            if event.get("type") == "ADAPTIVE_RISK_APPLIED"
        ]
        
        # Create R2 lookup by (symbol, timestamp window)
        r2_lookup = {}
        for r2_event in r2_events:
            symbol = r2_event.get("symbol")
            r2_ts = r2_event.get("timestamp", 0)
            key = (symbol, r2_ts)
            r2_lookup[key] = r2_event
        
        # Enrich R1 events with R2 data
        enriched_events = []
        for r1_event in dynamic_risk_events:
            enriched = r1_event.copy()
            
            # Only enrich APPROVED events (BLOCKED don't go through R2)
            if r1_event.get("type") == "DYNAMIC_RISK_APPROVED":
                symbol = r1_event.get("symbol")
                r1_ts = r1_event.get("timestamp", 0)
                
                # Find matching R2 event (within 1 second window)
                r2_match = None
                for (r2_symbol, r2_ts), r2_event in r2_lookup.items():
                    if r2_symbol == symbol and abs(r2_ts - r1_ts) < 1000:  # 1 sec window
                        r2_match = r2_event
                        break
                
                # Enrich debug with R2 data
                if r2_match:
                    if "debug" not in enriched:
                        enriched["debug"] = {}
                    
                    enriched["debug"]["r2_multiplier"] = r2_match.get("r2_multiplier")
                    enriched["debug"]["r2_components"] = r2_match.get("r2_components")
                    enriched["debug"]["r2_debug"] = r2_match.get("r2_debug")
                    enriched["debug"]["final_multiplier"] = r2_match.get("final_multiplier")
                    
                    # Update top-level qty/notional with final values
                    enriched["qty"] = r2_match.get("final_qty", enriched.get("qty"))
                    enriched["notional_usd"] = r2_match.get("final_notional_usd", enriched.get("notional_usd"))
            
            enriched_events.append(enriched)
        
        # Sort by timestamp descending (newest first)
        enriched_events.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Take last 50
        recent = enriched_events[:50]
        
        return recent
    
    except Exception as e:
        logger.error(f"[DynamicRisk] Recent fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_dynamic_risk_stats():
    """
    Get aggregated statistics for dynamic risk decisions.
    
    Response format:
    {
        "approved_count": int,
        "blocked_count": int,
        "avg_multiplier": float,
        "avg_notional_usd": float,
        "top_block_reasons": [{"reason": str, "count": int}]
    }
    """
    try:
        from modules.execution_logger import get_execution_logger
        from collections import Counter
        
        logger_instance = get_execution_logger()
        
        # Fetch recent execution events
        all_events = await logger_instance.get_feed(limit=500)
        
        # Filter for dynamic risk events
        approved_events = [
            e for e in all_events
            if e.get("type") == "DYNAMIC_RISK_APPROVED"
        ]
        
        blocked_events = [
            e for e in all_events
            if e.get("type") == "DYNAMIC_RISK_BLOCKED"
        ]
        
        # Calculate stats
        approved_count = len(approved_events)
        blocked_count = len(blocked_events)
        
        # Average multiplier (only for approved)
        multipliers = [
            float(e.get("size_multiplier", 0))
            for e in approved_events
            if e.get("size_multiplier") is not None
        ]
        avg_multiplier = round(sum(multipliers) / len(multipliers), 3) if multipliers else 0
        
        # Average notional (only for approved)
        notionals = [
            float(e.get("notional_usd", 0))
            for e in approved_events
            if e.get("notional_usd") is not None
        ]
        avg_notional_usd = round(sum(notionals) / len(notionals), 2) if notionals else 0
        
        # Top block reasons
        block_reasons = [
            e.get("reason", "UNKNOWN")
            for e in blocked_events
            if e.get("reason")
        ]
        reason_counts = Counter(block_reasons)
        top_block_reasons = [
            {"reason": reason, "count": count}
            for reason, count in reason_counts.most_common(5)
        ]
        
        return {
            "approved_count": approved_count,
            "blocked_count": blocked_count,
            "avg_multiplier": avg_multiplier,
            "avg_notional_usd": avg_notional_usd,
            "top_block_reasons": top_block_reasons,
        }
    
    except Exception as e:
        logger.error(f"[DynamicRisk] Stats fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
