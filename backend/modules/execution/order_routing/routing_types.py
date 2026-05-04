"""
Order Routing Types - PHASE 5.3
===============================

Unified types for smart order routing.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class RoutingPolicy(str, Enum):
    """Routing policy modes"""
    BEST_PRICE = "BEST_PRICE"           # Route by best price
    BEST_EXECUTION = "BEST_EXECUTION"   # Price + liquidity + slippage + latency
    SAFEST_VENUE = "SAFEST_VENUE"       # Prioritize exchange reliability
    LOW_SLIPPAGE = "LOW_SLIPPAGE"       # Minimize slippage
    LOWEST_FEE = "LOWEST_FEE"           # Minimize fees
    SPLIT_ORDER = "SPLIT_ORDER"         # Split across exchanges


class RoutingUrgency(str, Enum):
    """Order urgency level"""
    LOW = "LOW"           # Can wait for best price
    NORMAL = "NORMAL"     # Standard execution
    HIGH = "HIGH"         # Execute quickly
    IMMEDIATE = "IMMEDIATE"  # Execute now at any price


class ExecutionMode(str, Enum):
    """Execution mode"""
    SINGLE = "SINGLE"     # Single venue
    SPLIT = "SPLIT"       # Split across venues
    TWAP = "TWAP"         # Time-weighted
    VWAP = "VWAP"         # Volume-weighted
    ICEBERG = "ICEBERG"   # Hidden size


class VenueStatus(str, Enum):
    """Venue health status for routing"""
    OPTIMAL = "OPTIMAL"       # Best choice
    AVAILABLE = "AVAILABLE"   # Can use
    DEGRADED = "DEGRADED"     # Use with caution
    UNAVAILABLE = "UNAVAILABLE"  # Don't use


# ============================================
# Request/Decision Types
# ============================================

class RoutingRequest(BaseModel):
    """Request for routing decision"""
    symbol: str
    side: str  # BUY/SELL
    size: float
    order_type: str = "MARKET"  # MARKET, LIMIT
    limit_price: Optional[float] = None
    preferred_exchange: Optional[str] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False
    urgency: RoutingUrgency = RoutingUrgency.NORMAL
    max_slippage_bps: float = 50.0  # Max acceptable slippage in bps
    policy: RoutingPolicy = RoutingPolicy.BEST_EXECUTION
    
    # Constraints
    allowed_exchanges: List[str] = Field(default_factory=lambda: ["BINANCE", "BYBIT", "OKX"])
    excluded_exchanges: List[str] = Field(default_factory=list)
    
    # Extra
    client_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VenueScore(BaseModel):
    """Score for a single venue"""
    exchange: str
    symbol: str
    
    # Pricing
    price: float = 0.0
    spread_bps: float = 0.0
    
    # Liquidity
    available_liquidity: float = 0.0
    liquidity_score: float = 0.0  # 0-1
    
    # Execution Quality
    expected_slippage_bps: float = 0.0
    historical_slippage_bps: float = 0.0
    fill_rate: float = 1.0  # Historical fill rate
    
    # Health
    health_status: VenueStatus = VenueStatus.AVAILABLE
    health_score: float = 1.0  # 0-1
    latency_ms: float = 0.0
    
    # Fees
    fee_rate: float = 0.0
    estimated_fee: float = 0.0
    
    # Combined
    total_score: float = 0.0  # Final routing score
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoutingDecision(BaseModel):
    """Routing decision result"""
    request_id: str
    symbol: str
    side: str
    size: float
    
    # Selected venue
    selected_exchange: str
    selected_order_type: str
    
    # Pricing
    expected_price: float
    expected_slippage_bps: float
    expected_fee: float
    
    # Confidence
    confidence: float  # 0-1
    routing_reason: str
    
    # Alternatives
    alternative_venues: List[str] = Field(default_factory=list)
    venue_scores: List[VenueScore] = Field(default_factory=list)
    
    # Metadata
    policy_used: RoutingPolicy = RoutingPolicy.BEST_EXECUTION
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionLeg(BaseModel):
    """Single leg of execution plan"""
    exchange: str
    size: float
    percentage: float  # Percentage of total
    order_type: str
    limit_price: Optional[float] = None
    expected_price: float
    expected_slippage_bps: float
    priority: int = 1  # Execution order


class ExecutionPlan(BaseModel):
    """Multi-venue execution plan"""
    plan_id: str
    symbol: str
    side: str
    total_size: float
    
    # Legs
    legs: List[ExecutionLeg] = Field(default_factory=list)
    
    # Estimates
    estimated_avg_price: float = 0.0
    estimated_total_cost: float = 0.0
    estimated_slippage_bps: float = 0.0
    estimated_fees: float = 0.0
    
    # Mode
    execution_mode: ExecutionMode = ExecutionMode.SINGLE
    
    # Timing
    estimated_duration_ms: int = 0
    
    # Status
    status: str = "PENDING"  # PENDING, EXECUTING, COMPLETED, FAILED
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Venue Analysis Types
# ============================================

class VenueAnalysis(BaseModel):
    """Detailed venue analysis for a symbol"""
    exchange: str
    symbol: str
    
    # Current Market
    best_bid: float = 0.0
    best_ask: float = 0.0
    mid_price: float = 0.0
    spread_bps: float = 0.0
    
    # Depth
    bid_depth_usd: float = 0.0
    ask_depth_usd: float = 0.0
    depth_imbalance: float = 0.0
    
    # Liquidity for order size
    can_fill_size: float = 0.0
    slippage_for_size_bps: float = 0.0
    
    # Health
    venue_status: VenueStatus = VenueStatus.AVAILABLE
    health_score: float = 1.0
    failover_status: str = "NORMAL"
    
    # Historical Performance
    avg_slippage_bps: float = 0.0
    avg_latency_ms: float = 0.0
    fill_rate: float = 1.0
    
    # Recommendation
    recommended: bool = True
    rejection_reason: Optional[str] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoutingEvent(BaseModel):
    """Routing event for logging"""
    event_type: str  # ROUTING_DECISION, PLAN_CREATED, VENUE_REJECTED, etc.
    request_id: str
    symbol: str
    
    # Details
    selected_exchange: Optional[str] = None
    rejected_exchanges: List[str] = Field(default_factory=list)
    reason: str = ""
    
    # Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# API Models
# ============================================

class EvaluateRequest(BaseModel):
    """API request to evaluate routing"""
    symbol: str
    side: str
    size: float
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    policy: str = "BEST_EXECUTION"
    urgency: str = "NORMAL"
    max_slippage_bps: float = 50.0


class PlanRequest(BaseModel):
    """API request to create execution plan"""
    symbol: str
    side: str
    size: float
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    policy: str = "BEST_EXECUTION"
    split_threshold: float = 10.0  # Split if size > X% of liquidity


class ExecutePlanRequest(BaseModel):
    """API request to execute a plan"""
    plan_id: str
    dry_run: bool = False
