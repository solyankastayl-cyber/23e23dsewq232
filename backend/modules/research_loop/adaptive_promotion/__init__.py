"""
PHASE 20.3 — Adaptive Promotion / Demotion Module
=================================================
Recommends lifecycle state transitions for factors.

Components:
- adaptive_promotion_types: Type definitions
- adaptive_promotion_policy: Transition rules
- adaptive_promotion_engine: Main engine
- adaptive_promotion_registry: History tracking
- adaptive_promotion_routes: API endpoints
"""

from modules.research_loop.adaptive_promotion.adaptive_promotion_types import (
    LifecycleState,
    TransitionAction,
    TransitionStrength,
    AdaptivePromotionDecision,
    AdaptivePromotionSummary,
    ALLOWED_TRANSITIONS,
)

from modules.research_loop.adaptive_promotion.adaptive_promotion_engine import (
    AdaptivePromotionEngine,
    get_adaptive_promotion_engine,
)

from modules.research_loop.adaptive_promotion.adaptive_promotion_registry import (
    AdaptivePromotionRegistry,
    get_adaptive_promotion_registry,
)

__all__ = [
    # Types
    "LifecycleState",
    "TransitionAction",
    "TransitionStrength",
    "AdaptivePromotionDecision",
    "AdaptivePromotionSummary",
    "ALLOWED_TRANSITIONS",
    # Engine
    "AdaptivePromotionEngine",
    "get_adaptive_promotion_engine",
    # Registry
    "AdaptivePromotionRegistry",
    "get_adaptive_promotion_registry",
]
