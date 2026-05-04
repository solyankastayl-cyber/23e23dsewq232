"""
PHASE 13.2 - Feature Routes
============================
API endpoints for Alpha Feature Library.

Endpoints:
- GET  /api/alpha-features/health
- GET  /api/alpha-features
- GET  /api/alpha-features/{feature_id}
- POST /api/alpha-features
- PUT  /api/alpha-features/{feature_id}
- GET  /api/alpha-features/categories
- GET  /api/alpha-features/transforms
- GET  /api/alpha-features/search
- GET  /api/alpha-features/stats
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .feature_registry import get_feature_registry, FeatureRegistry
from .feature_types import Feature, FeatureCategory, FeatureTransform, FeatureStatus
from .feature_transforms import FeatureTransformer
from .feature_repository import FeatureRepository

router = APIRouter(prefix="/api/alpha-features", tags=["Alpha Features"])


# ===== Pydantic Models =====

class FeatureCreateRequest(BaseModel):
    feature_id: str
    category: str = "price"
    inputs: List[str] = []
    transform: str = "raw"
    params: dict = {}
    output_type: str = "numeric"
    value_range: Optional[List[float]] = None
    description: str = ""
    tags: List[str] = []
    depends_on: List[str] = []
    regime_dependency: List[str] = []


class FeatureUpdateRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    params: Optional[dict] = None
    regime_dependency: Optional[List[str]] = None
    status: Optional[str] = None


class TransformRequest(BaseModel):
    transform: str
    values: List[float]
    params: dict = {}
    secondary_values: Optional[List[float]] = None


# ===== Singleton instances =====

_registry: Optional[FeatureRegistry] = None
_repository: Optional[FeatureRepository] = None


def get_registry() -> FeatureRegistry:
    global _registry
    if _registry is None:
        _registry = get_feature_registry()
    return _registry


def get_repository() -> FeatureRepository:
    global _repository
    if _repository is None:
        _repository = FeatureRepository()
    return _repository


# ===== Health & Stats =====

@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "module": "alpha_feature_library",
        "version": "phase13.2_feature_library",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get Feature Library statistics."""
    registry = get_registry()
    repo = get_repository()
    
    registry_stats = registry.get_stats()
    repo_stats = repo.get_stats()
    
    return {
        "registry": registry_stats,
        "repository": repo_stats,
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Feature CRUD =====

@router.get("")
async def list_features(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    transform: Optional[str] = Query(None, description="Filter by transform"),
    status: str = Query("active", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all features."""
    registry = get_registry()
    
    cat = FeatureCategory(category) if category else None
    tr = FeatureTransform(transform) if transform else None
    st = FeatureStatus(status) if status else FeatureStatus.ACTIVE
    tags = [tag] if tag else None
    
    features = registry.list_features(
        category=cat,
        tags=tags,
        transform=tr,
        status=st,
        limit=limit
    )
    
    return {
        "count": len(features),
        "features": [f.to_dict() for f in features],
        "filters": {
            "category": category,
            "tag": tag,
            "transform": transform,
            "status": status
        }
    }


@router.get("/categories")
async def get_categories():
    """Get available feature categories."""
    registry = get_registry()
    breakdown = registry.get_category_breakdown()
    
    return {
        "categories": [c.value for c in FeatureCategory],
        "counts": breakdown,
        "total": sum(breakdown.values())
    }


@router.get("/transforms")
async def get_transforms():
    """Get available transforms."""
    return {
        "transforms": FeatureTransformer.get_available_transforms(),
        "count": len(FeatureTransformer.get_available_transforms())
    }


@router.get("/search")
async def search_features(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200)
):
    """Search features by query."""
    registry = get_registry()
    results = registry.search_features(q, limit=limit)
    
    return {
        "query": q,
        "count": len(results),
        "features": [f.to_dict() for f in results]
    }


@router.get("/tags")
async def get_all_tags():
    """Get all unique tags across features."""
    registry = get_registry()
    tags = registry.get_all_tags()
    
    return {
        "tags": tags,
        "count": len(tags)
    }


@router.get("/by-category/{category}")
async def get_features_by_category(category: str):
    """Get all features of a specific category."""
    try:
        cat = FeatureCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    registry = get_registry()
    features = registry.get_features_by_category(cat)
    
    return {
        "category": category,
        "count": len(features),
        "features": [f.to_dict() for f in features]
    }


@router.get("/{feature_id}")
async def get_feature(feature_id: str):
    """Get a specific feature."""
    registry = get_registry()
    feature = registry.get_feature(feature_id)
    
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")
    
    return {
        "feature": feature.to_dict(),
        "dependencies": registry.get_dependencies(feature_id)
    }


@router.post("", status_code=201)
async def create_feature(request: FeatureCreateRequest):
    """Create a new feature."""
    registry = get_registry()
    
    # Check if exists
    existing = registry.get_feature(request.feature_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Feature '{request.feature_id}' already exists")
    
    # Create feature
    try:
        category = FeatureCategory(request.category)
        transform = FeatureTransform(request.transform)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    feature = Feature(
        feature_id=request.feature_id,
        category=category,
        inputs=request.inputs,
        transform=transform,
        params=request.params,
        output_type=request.output_type,
        value_range=request.value_range,
        description=request.description,
        tags=request.tags,
        depends_on=request.depends_on,
        regime_dependency=request.regime_dependency,
        created_at=datetime.now(timezone.utc)
    )
    
    success = registry.register_feature(feature)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register feature")
    
    return {
        "created": True,
        "feature_id": feature.feature_id,
        "feature": feature.to_dict()
    }


@router.put("/{feature_id}")
async def update_feature(feature_id: str, request: FeatureUpdateRequest):
    """Update an existing feature."""
    registry = get_registry()
    
    feature = registry.get_feature(feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")
    
    # Build updates
    updates = {}
    if request.description is not None:
        updates["description"] = request.description
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.params is not None:
        updates["params"] = request.params
    if request.regime_dependency is not None:
        updates["regime_dependency"] = request.regime_dependency
    if request.status is not None:
        updates["status"] = request.status
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = registry.update_feature(feature_id, updates)
    
    return {
        "updated": success,
        "feature_id": feature_id,
        "updates": updates
    }


@router.delete("/{feature_id}")
async def delete_feature(feature_id: str):
    """Delete (deprecate) a feature."""
    registry = get_registry()
    
    feature = registry.get_feature(feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")
    
    success = registry.delete_feature(feature_id)
    
    return {
        "deleted": success,
        "feature_id": feature_id,
        "status": "deprecated"
    }


# ===== Transform Operations =====

@router.post("/transform")
async def apply_transform(request: TransformRequest):
    """Apply transform to values."""
    try:
        result = FeatureTransformer.apply_transform(
            request.transform,
            request.values,
            request.params,
            request.secondary_values
        )
        
        return {
            "transform": request.transform,
            "input_count": len(request.values),
            "output_count": len(result),
            "result": result,
            "params": request.params
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transform error: {str(e)}")


@router.get("/{feature_id}/dependencies")
async def get_feature_dependencies(feature_id: str):
    """Get dependencies for a feature."""
    registry = get_registry()
    
    feature = registry.get_feature(feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")
    
    return {
        "feature_id": feature_id,
        "dependencies": registry.get_dependencies(feature_id),
        "computed_at": datetime.now(timezone.utc).isoformat()
    }
