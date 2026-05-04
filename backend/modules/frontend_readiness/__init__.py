"""
Frontend Readiness Audit — PHASE 52

Pre-frontend verification:
1. API Consistency Audit
2. Response Size Audit
3. Pagination / Streaming support
4. Symbol / Timeframe standardization
5. Chart Object Stability
6. Indicator Extensibility
7. Object Limits verification
"""

from .audit import FrontendReadinessAudit, get_readiness_audit
from .routes import frontend_readiness_router

__all__ = [
    "FrontendReadinessAudit",
    "get_readiness_audit",
    "frontend_readiness_router",
]
