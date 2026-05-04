"""
AF3 — Validation → Alpha Bridge
Connects Alpha Factory (TT4 closed trades) with V1 Validation (live/shadow truth)
"""
from .validation_bridge_routes import router as validation_bridge_router

__all__ = ["validation_bridge_router"]
