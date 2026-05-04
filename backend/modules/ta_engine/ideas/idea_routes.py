"""
Idea API Routes
================
REST API endpoints for Idea System.

Endpoints:
- POST /api/ta/ideas — Create new idea
- GET /api/ta/ideas — List ideas
- GET /api/ta/ideas/{idea_id} — Get idea details
- POST /api/ta/ideas/{idea_id}/update — Update idea (new version)
- POST /api/ta/ideas/{idea_id}/validate — Validate idea
- GET /api/ta/ideas/{idea_id}/timeline — Get idea timeline
- DELETE /api/ta/ideas/{idea_id} — Delete idea
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from modules.ta_engine.ideas.idea_service import get_idea_service

router = APIRouter(prefix="/api/ta/ideas", tags=["ta-ideas"])


class CreateIdeaRequest(BaseModel):
    asset: str
    timeframe: str = "1d"
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = ""
    snapshot: Optional[dict] = None  # Full TA snapshot from frontend


class ValidateIdeaRequest(BaseModel):
    current_price: Optional[float] = None


# ═══════════════════════════════════════════════════════════════
# CREATE IDEA
# ═══════════════════════════════════════════════════════════════

@router.post("")
async def create_idea(request: CreateIdeaRequest):
    """
    Create a new trading idea.
    
    If snapshot is provided, uses it directly.
    Otherwise, runs setup analysis and saves the result.
    """
    service = get_idea_service()
    
    idea = service.create_idea(
        asset=request.asset,
        timeframe=request.timeframe,
        user_id=request.user_id,
        tags=request.tags,
        notes=request.notes or "",
        snapshot=request.snapshot,  # Pass frontend snapshot
    )
    
    return {
        "ok": True,
        "message": "Idea created successfully",
        "idea": idea.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# LIST IDEAS
# ═══════════════════════════════════════════════════════════════

@router.get("")
async def list_ideas(
    user_id: Optional[str] = None,
    asset: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    full: bool = Query(False, description="Return full idea data with versions"),
):
    """
    List saved ideas with optional filters.
    """
    service = get_idea_service()
    
    ideas = service.list_ideas(
        user_id=user_id,
        asset=asset,
        status=status,
        limit=limit,
    )
    
    return {
        "ok": True,
        "ideas": [idea.to_dict() if full else idea.to_summary_dict() for idea in ideas],
        "count": len(ideas),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# GET IDEA
# ═══════════════════════════════════════════════════════════════

@router.get("/{idea_id}")
async def get_idea(idea_id: str):
    """
    Get full idea details including all versions and validations.
    """
    service = get_idea_service()
    
    idea = service.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return {
        "ok": True,
        "idea": idea.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# UPDATE IDEA (NEW VERSION)
# ═══════════════════════════════════════════════════════════════

@router.post("/{idea_id}/update")
async def update_idea(idea_id: str):
    """
    Update idea with fresh analysis, creating a new version.
    """
    service = get_idea_service()
    
    idea = service.update_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return {
        "ok": True,
        "message": f"Idea updated to version {idea.current_version}",
        "idea": idea.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# VALIDATE IDEA
# ═══════════════════════════════════════════════════════════════

@router.post("/{idea_id}/validate")
async def validate_idea(idea_id: str, request: Optional[ValidateIdeaRequest] = None):
    """
    Validate an idea by checking if the prediction was correct.
    """
    service = get_idea_service()
    
    current_price = request.current_price if request else None
    idea = service.validate_idea(idea_id, current_price)
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    latest_validation = idea.validations[-1] if idea.validations else None
    
    return {
        "ok": True,
        "message": "Idea validated",
        "validation_result": latest_validation.result.value if latest_validation else None,
        "idea": idea.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# GET TIMELINE
# ═══════════════════════════════════════════════════════════════

@router.get("/{idea_id}/timeline")
async def get_idea_timeline(idea_id: str):
    """
    Get timeline view of idea evolution.
    
    Shows all versions and validations in chronological order.
    """
    service = get_idea_service()
    
    timeline = service.get_idea_timeline(idea_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return {
        "ok": True,
        **timeline,
    }


# ═══════════════════════════════════════════════════════════════
# DELETE IDEA
# ═══════════════════════════════════════════════════════════════

@router.delete("/{idea_id}")
async def delete_idea(idea_id: str):
    """
    Delete an idea.
    """
    service = get_idea_service()
    
    success = service.delete_idea(idea_id)
    if not success:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return {
        "ok": True,
        "message": "Idea deleted",
    }


# ═══════════════════════════════════════════════════════════════
# ARCHIVE IDEA
# ═══════════════════════════════════════════════════════════════

@router.post("/{idea_id}/archive")
async def archive_idea(idea_id: str):
    """
    Archive an idea (soft delete).
    """
    service = get_idea_service()
    
    idea = service.archive_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return {
        "ok": True,
        "message": "Idea archived",
        "idea": idea.to_summary_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# SEED DEMO IDEAS
# ═══════════════════════════════════════════════════════════════

@router.post("/seed")
async def seed_demo_ideas():
    """
    Seed database with demo ideas for the Ideas tab.
    Idempotent — won't duplicate if already seeded.
    """
    import time
    
    service = get_idea_service()
    now_ts = int(time.time())
    
    # Check if already seeded
    existing = service.list_ideas(limit=1)
    if existing:
        return {"ok": True, "message": "Ideas already seeded", "count": len(service.list_ideas())}
    
    # Seed data matching the frontend expected format
    seed_ideas = [
        {
            "idea_id": "idea-001",
            "asset": "BTCUSDT",
            "timeframe": "4H",
            "status": "completed",
            "current_version": 2,
            "technical_bias": "bullish",
            "confidence": 0.78,
            "setup_type": "triangle",
            "accuracy_score": 1.0,
            "total_predictions": 1,
            "correct_predictions": 1,
            "versions": [
                {
                    "version": 1,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 7, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "rectangle",
                        "lifecycle": "forming",
                        "probability": {"up": 0.62, "down": 0.28},
                        "confidence": 0.62,
                        "levels": {
                            "top": 72171,
                            "bottom": 64821,
                            "start_time": now_ts - 86400 * 9,
                            "end_time": now_ts - 86400 * 5,
                        },
                        "interpretation": "Market consolidating in tight range",
                        "context": {"market_state": "compression", "volatility": 0.02},
                    },
                    "technical_bias": "bullish",
                    "confidence": 0.62,
                    "price_at_creation": 68000,
                },
                {
                    "version": 2,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 2, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "triangle",
                        "lifecycle": "compression",
                        "probability": {"up": 0.78, "down": 0.18},
                        "confidence": 0.78,
                        "levels": {
                            "top": 73500,
                            "bottom": 68200,
                            "start_time": now_ts - 86400 * 5,
                            "end_time": now_ts - 86400 * 1,
                        },
                        "interpretation": "Market was consolidating \u2192 breakout confirmed",
                        "context": {"market_state": "breakout", "volatility": 0.03},
                    },
                    "technical_bias": "bullish",
                    "confidence": 0.78,
                    "price_at_creation": 72500,
                },
            ],
            "validations": [
                {
                    "validated_at": datetime.fromtimestamp(now_ts - 86400, tz=timezone.utc).isoformat(),
                    "result": "correct",
                    "price_at_validation": 74200,
                    "price_change_pct": 6.2,
                    "target_hit": True,
                    "invalidation_hit": False,
                    "notes": "Breakout UP confirmed",
                }
            ],
            "created_at": datetime.fromtimestamp(now_ts - 86400 * 7, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(now_ts - 86400, tz=timezone.utc).isoformat(),
            "tags": ["breakout", "bullish"],
            "notes": "",
        },
        {
            "idea_id": "idea-002",
            "asset": "ETHUSDT",
            "timeframe": "1D",
            "status": "active",
            "current_version": 1,
            "technical_bias": "bullish",
            "confidence": 0.72,
            "setup_type": "ascending_triangle",
            "versions": [
                {
                    "version": 1,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 3, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "ascending_triangle",
                        "lifecycle": "confirmed",
                        "probability": {"up": 0.72, "down": 0.24},
                        "confidence": 0.72,
                        "levels": {
                            "top": 3850,
                            "bottom": 3420,
                            "start_time": now_ts - 86400 * 6,
                            "end_time": now_ts - 86400 * 1,
                        },
                        "interpretation": "Strong accumulation pattern forming",
                        "context": {"market_state": "compression", "volatility": 0.015},
                    },
                    "technical_bias": "bullish",
                    "confidence": 0.72,
                    "price_at_creation": 3650,
                },
            ],
            "validations": [],
            "created_at": datetime.fromtimestamp(now_ts - 86400 * 3, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(now_ts - 86400 * 3, tz=timezone.utc).isoformat(),
            "tags": ["accumulation"],
            "notes": "",
        },
        {
            "idea_id": "idea-003",
            "asset": "SOLUSDT",
            "timeframe": "4H",
            "status": "invalidated",
            "current_version": 1,
            "technical_bias": "bearish",
            "confidence": 0.55,
            "setup_type": "head_and_shoulders",
            "accuracy_score": 0,
            "total_predictions": 1,
            "correct_predictions": 0,
            "versions": [
                {
                    "version": 1,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 10, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "head_and_shoulders",
                        "lifecycle": "forming",
                        "probability": {"up": 0.35, "down": 0.58},
                        "confidence": 0.55,
                        "levels": {
                            "top": 185,
                            "bottom": 142,
                            "start_time": now_ts - 86400 * 13,
                            "end_time": now_ts - 86400 * 8,
                        },
                        "interpretation": "Distribution pattern detected",
                        "context": {"market_state": "volatile", "volatility": 0.04},
                    },
                    "technical_bias": "bearish",
                    "confidence": 0.55,
                    "price_at_creation": 165,
                },
            ],
            "validations": [
                {
                    "validated_at": datetime.fromtimestamp(now_ts - 86400 * 5, tz=timezone.utc).isoformat(),
                    "result": "invalidated",
                    "price_at_validation": 190,
                    "price_change_pct": 15.2,
                    "target_hit": False,
                    "invalidation_hit": True,
                    "notes": "Pattern invalidated",
                }
            ],
            "created_at": datetime.fromtimestamp(now_ts - 86400 * 10, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(now_ts - 86400 * 5, tz=timezone.utc).isoformat(),
            "tags": ["distribution"],
            "notes": "",
        },
        {
            "idea_id": "idea-004",
            "asset": "BTCUSDT",
            "timeframe": "1D",
            "status": "completed",
            "current_version": 3,
            "technical_bias": "bullish",
            "confidence": 0.85,
            "setup_type": "ascending_triangle",
            "accuracy_score": 1.0,
            "total_predictions": 1,
            "correct_predictions": 1,
            "versions": [
                {
                    "version": 1,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 14, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "rectangle",
                        "lifecycle": "forming",
                        "probability": {"up": 0.55, "down": 0.35},
                        "confidence": 0.55,
                        "levels": {
                            "top": 68000,
                            "bottom": 62000,
                            "start_time": now_ts - 86400 * 18,
                            "end_time": now_ts - 86400 * 12,
                        },
                        "interpretation": "Accumulation zone forming",
                    },
                    "technical_bias": "neutral",
                    "confidence": 0.55,
                    "price_at_creation": 65000,
                },
                {
                    "version": 2,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 10, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "ascending_triangle",
                        "lifecycle": "confirmed",
                        "probability": {"up": 0.72, "down": 0.22},
                        "confidence": 0.72,
                        "levels": {
                            "top": 69500,
                            "bottom": 64000,
                            "start_time": now_ts - 86400 * 12,
                            "end_time": now_ts - 86400 * 7,
                        },
                        "interpretation": "Rising lows confirmed \u2014 bullish structure",
                    },
                    "technical_bias": "bullish",
                    "confidence": 0.72,
                    "price_at_creation": 67000,
                },
                {
                    "version": 3,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 6, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "ascending_triangle",
                        "lifecycle": "breakout",
                        "probability": {"up": 0.85, "down": 0.10},
                        "confidence": 0.85,
                        "levels": {
                            "top": 70500,
                            "bottom": 66500,
                            "start_time": now_ts - 86400 * 7,
                            "end_time": now_ts - 86400 * 4,
                        },
                        "interpretation": "Breakout confirmed with volume",
                    },
                    "technical_bias": "bullish",
                    "confidence": 0.85,
                    "price_at_creation": 71000,
                },
            ],
            "validations": [
                {
                    "validated_at": datetime.fromtimestamp(now_ts - 86400 * 4, tz=timezone.utc).isoformat(),
                    "result": "correct",
                    "price_at_validation": 73500,
                    "price_change_pct": 8.5,
                    "target_hit": True,
                    "invalidation_hit": False,
                    "notes": "Strong breakout UP",
                }
            ],
            "created_at": datetime.fromtimestamp(now_ts - 86400 * 14, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(now_ts - 86400 * 4, tz=timezone.utc).isoformat(),
            "tags": ["breakout", "multi-version"],
            "notes": "",
        },
        {
            "idea_id": "idea-005",
            "asset": "ETHUSDT",
            "timeframe": "4H",
            "status": "completed",
            "current_version": 2,
            "technical_bias": "bearish",
            "confidence": 0.68,
            "setup_type": "descending_triangle",
            "accuracy_score": 1.0,
            "total_predictions": 1,
            "correct_predictions": 1,
            "versions": [
                {
                    "version": 1,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 8, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "rectangle",
                        "lifecycle": "forming",
                        "probability": {"up": 0.40, "down": 0.50},
                        "confidence": 0.50,
                        "levels": {
                            "top": 3200,
                            "bottom": 2900,
                            "start_time": now_ts - 86400 * 11,
                            "end_time": now_ts - 86400 * 6,
                        },
                        "interpretation": "Distribution forming at resistance",
                    },
                    "technical_bias": "neutral",
                    "confidence": 0.50,
                    "price_at_creation": 3050,
                },
                {
                    "version": 2,
                    "timestamp": datetime.fromtimestamp(now_ts - 86400 * 4, tz=timezone.utc).isoformat(),
                    "setup_snapshot": {
                        "pattern": "descending_triangle",
                        "lifecycle": "confirmed",
                        "probability": {"up": 0.28, "down": 0.68},
                        "confidence": 0.68,
                        "levels": {
                            "top": 3100,
                            "bottom": 2850,
                            "start_time": now_ts - 86400 * 6,
                            "end_time": now_ts - 86400 * 2,
                        },
                        "interpretation": "Breakdown confirmed \u2014 bearish continuation",
                    },
                    "technical_bias": "bearish",
                    "confidence": 0.68,
                    "price_at_creation": 2920,
                },
            ],
            "validations": [
                {
                    "validated_at": datetime.fromtimestamp(now_ts - 86400 * 2, tz=timezone.utc).isoformat(),
                    "result": "correct",
                    "price_at_validation": 2780,
                    "price_change_pct": -8.9,
                    "target_hit": True,
                    "invalidation_hit": False,
                    "notes": "Breakdown confirmed",
                }
            ],
            "created_at": datetime.fromtimestamp(now_ts - 86400 * 8, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(now_ts - 86400 * 2, tz=timezone.utc).isoformat(),
            "tags": ["breakdown"],
            "notes": "",
        },
    ]
    
    db = service.collection
    for idea_data in seed_ideas:
        db.update_one(
            {"idea_id": idea_data["idea_id"]},
            {"$set": idea_data},
            upsert=True,
        )
    
    return {
        "ok": True,
        "message": f"Seeded {len(seed_ideas)} demo ideas",
        "count": len(seed_ideas),
    }
