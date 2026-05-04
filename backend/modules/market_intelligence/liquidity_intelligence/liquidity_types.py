"""
PHASE 8 - Liquidity Intelligence Types
========================================
Core data types for liquidity analysis.

Provides understanding of:
- Where liquidity actually exists
- Where stops are clustered
- Where liquidations could cascade
- Where price is likely to sweep
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class LiquidityQuality(str, Enum):
    """Overall liquidity quality assessment"""
    EXCELLENT = "EXCELLENT"  # Deep, balanced book
    GOOD = "GOOD"           # Adequate depth
    MEDIUM = "MEDIUM"       # Some thin zones
    POOR = "POOR"           # Significant gaps
    CRITICAL = "CRITICAL"   # Very thin, high slippage risk


class DepthZoneType(str, Enum):
    """Type of depth zone"""
    THICK = "THICK"         # High liquidity
    THIN = "THIN"           # Low liquidity, gap prone
    WALL = "WALL"           # Large order wall
    VACUUM = "VACUUM"       # Near-empty zone
    BALANCED = "BALANCED"   # Symmetric bid/ask


class LiquidityZoneType(str, Enum):
    """Type of liquidity zone"""
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"      # Attracts price
    LOW_LIQUIDITY = "LOW_LIQUIDITY"        # Easy to break through
    MAGNET_ZONE = "MAGNET_ZONE"            # Strong attraction
    SWEEP_PRONE = "SWEEP_PRONE"            # Likely to be swept
    ABSORPTION_ZONE = "ABSORPTION_ZONE"    # Absorbs orders


class StopClusterSide(str, Enum):
    """Side of stop cluster"""
    LONG_STOPS = "LONG_STOPS"    # Stops from long positions (below)
    SHORT_STOPS = "SHORT_STOPS"  # Stops from short positions (above)


class SweepDirection(str, Enum):
    """Direction of potential sweep"""
    UPSIDE = "UPSIDE"    # Sweep above current price
    DOWNSIDE = "DOWNSIDE"  # Sweep below current price
    BOTH = "BOTH"        # Potential both ways


class PostSweepBias(str, Enum):
    """Expected bias after sweep"""
    BULLISH = "BULLISH"   # Expect upside after sweep
    BEARISH = "BEARISH"   # Expect downside after sweep
    NEUTRAL = "NEUTRAL"   # Unclear direction


class ImbalanceSide(str, Enum):
    """Dominant side of imbalance"""
    BID_DOMINANT = "BID_DOMINANT"
    ASK_DOMINANT = "ASK_DOMINANT"
    BALANCED = "BALANCED"


@dataclass
class OrderbookLevel:
    """Single level in orderbook"""
    price: float
    size: float
    cumulative_size: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "price": self.price,
            "size": self.size,
            "cumulative_size": self.cumulative_size
        }


@dataclass
class DepthProfile:
    """Orderbook depth analysis"""
    symbol: str
    timestamp: datetime
    
    # Depth metrics
    bid_depth: float           # Total bid volume
    ask_depth: float           # Total ask volume
    depth_ratio: float         # bid/ask ratio
    depth_imbalance: float     # -1 to 1 (negative = ask heavy)
    
    # Structure
    bid_levels: int
    ask_levels: int
    spread: float
    spread_bps: float
    
    # Walls and thin zones
    bid_walls: List[OrderbookLevel] = field(default_factory=list)
    ask_walls: List[OrderbookLevel] = field(default_factory=list)
    thin_zones: List[Dict] = field(default_factory=list)
    
    # Quality
    liquidity_quality: LiquidityQuality = LiquidityQuality.MEDIUM
    depth_asymmetry: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "bid_depth": round(self.bid_depth, 2),
            "ask_depth": round(self.ask_depth, 2),
            "depth_ratio": round(self.depth_ratio, 4),
            "depth_imbalance": round(self.depth_imbalance, 4),
            "bid_levels": self.bid_levels,
            "ask_levels": self.ask_levels,
            "spread": self.spread,
            "spread_bps": round(self.spread_bps, 2),
            "bid_walls": [w.to_dict() for w in self.bid_walls],
            "ask_walls": [w.to_dict() for w in self.ask_walls],
            "thin_zones": self.thin_zones,
            "liquidity_quality": self.liquidity_quality.value,
            "depth_asymmetry": round(self.depth_asymmetry, 4)
        }


@dataclass
class LiquidityZone:
    """Identified liquidity zone"""
    symbol: str
    zone_type: LiquidityZoneType
    
    # Price range
    price_low: float
    price_high: float
    mid_price: float
    
    # Zone characteristics
    liquidity_score: float      # 0-1
    attraction_strength: float  # How much price is drawn to it
    volume_concentration: float # Volume density
    
    # Sweep potential
    sweep_probability: float = 0.0
    sweep_direction: Optional[SweepDirection] = None
    
    # Timing
    detected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "zone_type": self.zone_type.value,
            "price_low": self.price_low,
            "price_high": self.price_high,
            "mid_price": self.mid_price,
            "liquidity_score": round(self.liquidity_score, 3),
            "attraction_strength": round(self.attraction_strength, 3),
            "volume_concentration": round(self.volume_concentration, 3),
            "sweep_probability": round(self.sweep_probability, 3),
            "sweep_direction": self.sweep_direction.value if self.sweep_direction else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class StopCluster:
    """Detected stop cluster"""
    symbol: str
    
    # Location
    price_level: float
    price_range_low: float
    price_range_high: float
    
    # Cluster properties
    side: StopClusterSide
    cluster_strength: float     # Estimated stop volume
    confidence: float           # Detection confidence
    
    # Context
    trigger_type: str          # "equal_highs", "swing_low", "range_break", etc.
    distance_from_current: float  # Distance from current price
    distance_pct: float
    
    # Risk
    cascade_risk: float = 0.0   # Risk of cascading liquidations
    
    detected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price_level": self.price_level,
            "price_range": {
                "low": self.price_range_low,
                "high": self.price_range_high
            },
            "side": self.side.value,
            "cluster_strength": round(self.cluster_strength, 3),
            "confidence": round(self.confidence, 3),
            "trigger_type": self.trigger_type,
            "distance_from_current": round(self.distance_from_current, 2),
            "distance_pct": round(self.distance_pct, 4),
            "cascade_risk": round(self.cascade_risk, 3),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class LiquidationZone:
    """Estimated liquidation zone"""
    symbol: str
    
    # Zone boundaries
    price_level: float
    price_range_low: float
    price_range_high: float
    
    # Position type
    position_type: str  # "LONG" or "SHORT"
    
    # Metrics
    estimated_volume: float      # Estimated liquidation volume
    cascade_risk: float          # Risk of cascade (0-1)
    leverage_density: float      # Concentration of leveraged positions
    
    # Distance
    distance_from_current: float
    distance_pct: float
    
    detected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price_level": self.price_level,
            "price_range": {
                "low": self.price_range_low,
                "high": self.price_range_high
            },
            "position_type": self.position_type,
            "estimated_volume": round(self.estimated_volume, 2),
            "cascade_risk": round(self.cascade_risk, 3),
            "leverage_density": round(self.leverage_density, 3),
            "distance_from_current": round(self.distance_from_current, 2),
            "distance_pct": round(self.distance_pct, 4),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class SweepSignal:
    """Sweep probability signal"""
    symbol: str
    
    # Sweep characteristics
    sweep_probability: float    # 0-1
    sweep_direction: SweepDirection
    target_level: float
    
    # Post-sweep expectation
    post_sweep_bias: PostSweepBias
    reclaim_probability: float  # Probability of reclaiming after sweep
    
    # Context
    trigger_zone: str           # What zone would be swept
    distance_to_target: float
    distance_pct: float
    
    # Confidence
    confidence: float = 0.5
    
    generated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "sweep_probability": round(self.sweep_probability, 3),
            "sweep_direction": self.sweep_direction.value,
            "target_level": self.target_level,
            "post_sweep_bias": self.post_sweep_bias.value,
            "reclaim_probability": round(self.reclaim_probability, 3),
            "trigger_zone": self.trigger_zone,
            "distance_to_target": round(self.distance_to_target, 2),
            "distance_pct": round(self.distance_pct, 4),
            "confidence": round(self.confidence, 3),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }


@dataclass
class LiquidityImbalance:
    """Liquidity imbalance analysis"""
    symbol: str
    
    # Imbalance metrics
    imbalance_score: float      # -1 to 1 (-1 = ask dominant, 1 = bid dominant)
    dominant_side: ImbalanceSide
    
    # Stability
    imbalance_stability: float  # How stable is the imbalance
    volatility_risk: float      # Risk of sudden moves
    
    # Components
    bid_pressure: float
    ask_pressure: float
    net_pressure: float
    
    # Time dynamics
    imbalance_trend: str        # INCREASING, DECREASING, STABLE
    
    computed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "imbalance_score": round(self.imbalance_score, 4),
            "dominant_side": self.dominant_side.value,
            "imbalance_stability": round(self.imbalance_stability, 3),
            "volatility_risk": round(self.volatility_risk, 3),
            "bid_pressure": round(self.bid_pressure, 3),
            "ask_pressure": round(self.ask_pressure, 3),
            "net_pressure": round(self.net_pressure, 3),
            "imbalance_trend": self.imbalance_trend,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }


@dataclass
class UnifiedLiquiditySnapshot:
    """Complete liquidity state for a symbol"""
    symbol: str
    current_price: float
    timestamp: datetime
    
    # Depth
    bid_depth: float
    ask_depth: float
    depth_imbalance: float
    
    # Nearest clusters
    nearest_stop_cluster_above: Optional[float] = None
    nearest_stop_cluster_below: Optional[float] = None
    
    # Nearest liquidation zones
    nearest_long_liquidation: Optional[float] = None
    nearest_short_liquidation: Optional[float] = None
    
    # Sweep analysis
    sweep_probability: float = 0.0
    sweep_direction: Optional[SweepDirection] = None
    post_sweep_bias: Optional[PostSweepBias] = None
    
    # Quality
    liquidity_quality: LiquidityQuality = LiquidityQuality.MEDIUM
    
    # Risk metrics
    cascade_risk: float = 0.0
    execution_risk: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "bid_depth": round(self.bid_depth, 2),
            "ask_depth": round(self.ask_depth, 2),
            "depth_imbalance": round(self.depth_imbalance, 4),
            "nearest_stop_cluster_above": self.nearest_stop_cluster_above,
            "nearest_stop_cluster_below": self.nearest_stop_cluster_below,
            "nearest_long_liquidation": self.nearest_long_liquidation,
            "nearest_short_liquidation": self.nearest_short_liquidation,
            "sweep_probability": round(self.sweep_probability, 3),
            "sweep_direction": self.sweep_direction.value if self.sweep_direction else None,
            "post_sweep_bias": self.post_sweep_bias.value if self.post_sweep_bias else None,
            "liquidity_quality": self.liquidity_quality.value,
            "cascade_risk": round(self.cascade_risk, 3),
            "execution_risk": round(self.execution_risk, 3)
        }


# Default configuration
DEFAULT_CONFIG = {
    "depth_levels": 50,          # Orderbook levels to analyze
    "wall_threshold": 2.0,       # Multiple of avg size to consider wall
    "thin_zone_threshold": 0.2,  # Fraction of avg for thin zone
    "stop_cluster_range": 0.005, # 0.5% range for clustering
    "liquidation_leverage_threshold": 10,  # High leverage threshold
}
