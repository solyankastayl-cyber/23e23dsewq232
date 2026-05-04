"""
Idea API Routes — REST endpoints for idea management
===================================================

Endpoints:
  POST   /api/ideas                    - Create idea from analysis
  GET    /api/ideas/:id                - Get idea with history
  PUT    /api/ideas/:id/update         - Update idea (new version)
  POST   /api/ideas/:id/favorite       - Add to favorites
  DELETE /api/ideas/:id/favorite       - Remove from favorites
  GET    /api/ideas/user/:user_id      - Get user's ideas
  GET    /api/ideas/asset/:asset       - Get ideas for asset
  GET    /api/favorites/:user_id       - Get user's favorites
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from modules.idea import get_idea_engine_v1, get_idea_repository


router = APIRouter(prefix="/api/ideas", tags=["ideas"])


# ---------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------
class CreateIdeaRequest(BaseModel):
    """Request to create idea from analysis."""
    asset: str
    timeframe: str
    decision: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    explanation: Dict[str, Any]
    user_id: Optional[str] = None


class UpdateIdeaRequest(BaseModel):
    """Request to update idea."""
    decision: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    explanation: Dict[str, Any]


class FavoriteRequest(BaseModel):
    """Request to add/remove favorite."""
    user_id: str


# ---------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------

@router.get("")
async def list_ideas(
    user_id: str = Query("default"),
    symbol: str = Query(None),
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    full: bool = Query(False)
):
    """
    List all ideas with optional filters.
    
    GET /api/ideas?user_id=xxx&symbol=BTC&status=active
    """
    engine = get_idea_engine_v1()
    repo = get_idea_repository()
    
    try:
        # Get all ideas (filtered if needed)
        all_ideas = []
        
        if user_id and user_id != "all" and user_id != "default":
            all_ideas = engine.get_user_ideas(user_id, include_current_version=True)
        elif symbol:
            all_ideas = engine.get_asset_ideas(symbol.upper(), include_current_version=True)
        else:
            # Get all ideas from repository
            try:
                all_ideas = repo.get_all_ideas(limit=limit)
            except:
                all_ideas = []
        
        # Filter by status if needed
        if status:
            all_ideas = [i for i in all_ideas if i.get("status") == status]
        
        # Normalize for frontend compatibility
        items = []
        for idea in all_ideas[:limit]:
            # Transform to frontend format
            normalized = {
                "idea_id": idea.get("idea_id", idea.get("id", "")),
                "asset": idea.get("asset", idea.get("symbol", "UNKNOWN")) + "USDT",
                "symbol": idea.get("asset", idea.get("symbol", "UNKNOWN")),
                "timeframe": idea.get("timeframe", "4H"),
                "status": idea.get("status", "active"),
                "outcome": idea.get("outcome"),
                "score": idea.get("score", 0),
                "created_at": idea.get("created_at"),
                "versions": idea.get("versions", []),
            }
            
            # Calculate score from validations/result
            if idea.get("validations"):
                last_val = idea["validations"][-1] if idea["validations"] else None
                if last_val:
                    if last_val.get("result") in ["correct", "partially_correct"]:
                        normalized["score"] = 1
                        normalized["outcome"] = normalized["outcome"] or "success_up"
                    elif last_val.get("result") == "invalidated":
                        normalized["score"] = -1
                        normalized["outcome"] = normalized["outcome"] or "invalidated"
            
            items.append(normalized)
        
        return {
            "ok": True,
            "items": items,
            "ideas": items,
            "total": len(items),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"ok": False, "items": [], "ideas": [], "error": str(e)}


@router.post("")
async def create_idea(request: CreateIdeaRequest):
    """
    Create new idea from analysis.
    
    POST /api/ideas
    """
    engine = get_idea_engine_v1()
    
    try:
        result = engine.create_from_analysis(
            asset=request.asset,
            timeframe=request.timeframe,
            decision=request.decision,
            scenarios=request.scenarios,
            explanation=request.explanation,
            user_id=request.user_id,
        )
        
        return {
            "success": True,
            "idea": result["idea"],
            "version": result["version"],
            "message": f"Idea created for {request.asset} {request.timeframe}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{idea_id}")
async def get_idea(idea_id: str):
    """
    Get idea with full version history.
    
    GET /api/ideas/:id
    """
    engine = get_idea_engine_v1()
    
    result = engine.get_idea_with_history(idea_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Idea {idea_id} not found")
    
    return {
        "success": True,
        **result,
    }


@router.put("/{idea_id}/update")
async def update_idea(idea_id: str, request: UpdateIdeaRequest):
    """
    Update idea (creates new version).
    
    PUT /api/ideas/:id/update
    """
    engine = get_idea_engine_v1()
    repo = get_idea_repository()
    
    # Check idea exists
    idea = repo.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"Idea {idea_id} not found")
    
    try:
        version = engine.update_idea(
            idea_id=idea_id,
            decision=request.decision,
            scenarios=request.scenarios,
            explanation=request.explanation,
        )
        
        return {
            "success": True,
            "version": version,
            "message": f"Idea updated. Version {version['version_number']} created.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{idea_id}/favorite")
async def add_favorite(idea_id: str, request: FavoriteRequest):
    """
    Add idea to user's favorites.
    
    POST /api/ideas/:id/favorite
    """
    repo = get_idea_repository()
    
    # Check idea exists
    idea = repo.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail=f"Idea {idea_id} not found")
    
    favorite = repo.add_favorite(request.user_id, idea_id)
    
    return {
        "success": True,
        "favorite": favorite,
        "message": "Idea added to favorites",
    }


@router.delete("/{idea_id}/favorite")
async def remove_favorite(idea_id: str, user_id: str = Query(...)):
    """
    Remove idea from user's favorites.
    
    DELETE /api/ideas/:id/favorite?user_id=xxx
    """
    repo = get_idea_repository()
    
    removed = repo.remove_favorite(user_id, idea_id)
    
    return {
        "success": removed,
        "message": "Idea removed from favorites" if removed else "Favorite not found",
    }


@router.get("/user/{user_id}")
async def get_user_ideas(user_id: str):
    """
    Get all ideas for a user.
    
    GET /api/ideas/user/:user_id
    """
    engine = get_idea_engine_v1()
    
    ideas = engine.get_user_ideas(user_id, include_current_version=True)
    
    return {
        "success": True,
        "ideas": ideas,
        "count": len(ideas),
    }


@router.get("/asset/{asset}")
async def get_asset_ideas(asset: str):
    """
    Get all ideas for an asset.
    
    GET /api/ideas/asset/:asset
    """
    engine = get_idea_engine_v1()
    
    ideas = engine.get_asset_ideas(asset, include_current_version=True)
    
    return {
        "success": True,
        "ideas": ideas,
        "count": len(ideas),
    }


# ---------------------------------------------------------
# FAVORITES
# ---------------------------------------------------------

favorites_router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@favorites_router.get("/{user_id}")
async def get_user_favorites(user_id: str):
    """
    Get user's favorite ideas.
    
    GET /api/favorites/:user_id
    """
    repo = get_idea_repository()
    engine = get_idea_engine_v1()
    
    favorites = repo.get_favorites_by_user(user_id)
    
    # Enrich with idea data
    enriched = []
    for fav in favorites:
        idea_data = engine.get_idea_with_history(fav["idea_id"])
        if idea_data:
            enriched.append({
                "favorite": fav,
                **idea_data,
            })
    
    return {
        "success": True,
        "favorites": enriched,
        "count": len(enriched),
    }
