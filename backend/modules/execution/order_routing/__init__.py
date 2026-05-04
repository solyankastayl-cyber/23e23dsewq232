"""
Order Routing Module - PHASE 5.3
================================

Smart order routing with venue selection, slippage awareness, and failover handling.

Components:
- routing_types: Unified types for routing
- routing_engine: Main orchestrator
- venue_selector: Venue scoring and selection
- execution_plan_builder: Multi-venue execution plans
- slippage_aware_router: Slippage-optimized routing
- routing_repository: Persistence layer
- routing_routes: REST API endpoints
"""

from .routing_types import (
    RoutingPolicy,
    RoutingUrgency,
    ExecutionMode,
    VenueStatus,
    RoutingRequest,
    RoutingDecision,
    ExecutionPlan,
    ExecutionLeg,
    VenueScore,
    VenueAnalysis,
    RoutingEvent
)

from .routing_engine import RoutingEngine, get_routing_engine
from .venue_selector import VenueSelector, get_venue_selector
from .execution_plan_builder import ExecutionPlanBuilder, get_plan_builder
from .slippage_aware_router import SlippageAwareRouter, get_slippage_router

__all__ = [
    # Types
    "RoutingPolicy",
    "RoutingUrgency",
    "ExecutionMode",
    "VenueStatus",
    "RoutingRequest",
    "RoutingDecision",
    "ExecutionPlan",
    "ExecutionLeg",
    "VenueScore",
    "VenueAnalysis",
    "RoutingEvent",
    
    # Components
    "RoutingEngine",
    "get_routing_engine",
    "VenueSelector",
    "get_venue_selector",
    "ExecutionPlanBuilder",
    "get_plan_builder",
    "SlippageAwareRouter",
    "get_slippage_router"
]
