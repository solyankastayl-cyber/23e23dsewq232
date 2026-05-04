"""
Visual Objects Routes — PHASE 49
"""

from fastapi import APIRouter
from datetime import datetime, timezone

from .models import ObjectType, ObjectCategory


router = APIRouter(prefix="/visual-objects", tags=["Visual Objects"])


@router.get("/health")
async def health():
    """Visual Objects API health."""
    return {
        "status": "ok",
        "phase": "49",
        "module": "visual_objects",
        "object_types": len(ObjectType),
        "categories": len(ObjectCategory),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/types")
async def get_object_types():
    """Get all supported object types."""
    return {
        "types": [t.value for t in ObjectType],
        "categories": [c.value for c in ObjectCategory],
        "count": len(ObjectType),
    }


visual_objects_router = router
