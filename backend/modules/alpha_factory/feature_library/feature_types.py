"""
PHASE 13.2 - Feature Types
===========================
Core data types for Alpha Feature Library.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class FeatureCategory(str, Enum):
    """Feature category classification."""
    PRICE = "price"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    LIQUIDITY = "liquidity"
    STRUCTURE = "structure"
    MICROSTRUCTURE = "microstructure"
    CORRELATION = "correlation"
    CONTEXT = "context"


class FeatureTransform(str, Enum):
    """Available feature transformations."""
    RAW = "raw"
    LAG = "lag"
    ROLLING_MEAN = "rolling_mean"
    ROLLING_STD = "rolling_std"
    ZSCORE = "zscore"
    PERCENTILE_RANK = "percentile_rank"
    MINMAX_SCALE = "minmax_scale"
    LOG_TRANSFORM = "log_transform"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    BINARY_THRESHOLD = "binary_threshold"
    CLIP = "clip"
    RANK = "rank"
    EMA = "ema"
    SMA = "sma"


class FeatureStatus(str, Enum):
    """Feature lifecycle status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    DISABLED = "disabled"


@dataclass
class Feature:
    """
    Feature Definition for Alpha Factory.
    
    Features are the raw building blocks for factors.
    """
    
    # Identity
    feature_id: str
    category: FeatureCategory
    
    # Computation
    inputs: List[str] = field(default_factory=list)
    transform: FeatureTransform = FeatureTransform.RAW
    params: Dict = field(default_factory=dict)  # window, threshold, etc.
    
    # Output specification
    output_type: str = "numeric"  # numeric, binary, categorical
    value_range: Optional[List[float]] = None  # [min, max] or None for unbounded
    
    # Description
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Other features required
    
    # Regime applicability
    regime_dependency: List[str] = field(default_factory=list)
    
    # Quality metrics
    stability_score: float = 0.0  # How stable is this feature over time
    importance_score: float = 0.0  # How important for prediction
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: FeatureStatus = FeatureStatus.ACTIVE
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB."""
        return {
            "feature_id": self.feature_id,
            "category": self.category.value if isinstance(self.category, FeatureCategory) else self.category,
            "inputs": self.inputs,
            "transform": self.transform.value if isinstance(self.transform, FeatureTransform) else self.transform,
            "params": self.params,
            "output_type": self.output_type,
            "value_range": self.value_range,
            "description": self.description,
            "tags": self.tags,
            "depends_on": self.depends_on,
            "regime_dependency": self.regime_dependency,
            "stability_score": self.stability_score,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status.value if isinstance(self.status, FeatureStatus) else self.status,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Feature":
        """Create from dictionary."""
        return cls(
            feature_id=data["feature_id"],
            category=FeatureCategory(data["category"]) if data.get("category") else FeatureCategory.PRICE,
            inputs=data.get("inputs", []),
            transform=FeatureTransform(data["transform"]) if data.get("transform") else FeatureTransform.RAW,
            params=data.get("params", {}),
            output_type=data.get("output_type", "numeric"),
            value_range=data.get("value_range"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            depends_on=data.get("depends_on", []),
            regime_dependency=data.get("regime_dependency", []),
            stability_score=data.get("stability_score", 0.0),
            importance_score=data.get("importance_score", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            status=FeatureStatus(data["status"]) if data.get("status") else FeatureStatus.ACTIVE,
            version=data.get("version", "1.0.0")
        )


# =============================================================================
# DEFAULT FEATURES - 300+ features across 8 categories
# =============================================================================

DEFAULT_FEATURES: List[Feature] = []

# -----------------------------------------------------------------------------
# 1. PRICE FEATURES (~70)
# -----------------------------------------------------------------------------

# Returns at different timeframes
for tf, window in [("1m", 1), ("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60), ("4h", 240), ("1d", 1440)]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"returns_{tf}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": window},
        output_type="numeric",
        description=f"{tf} price returns",
        tags=["price", "returns", tf]
    ))
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"log_returns_{tf}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.LOG_TRANSFORM,
        params={"periods": window},
        output_type="numeric",
        description=f"{tf} log returns",
        tags=["price", "returns", "log", tf]
    ))

# Price momentum features
for period in [5, 10, 20, 50, 100, 200]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_momentum_{period}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": period},
        output_type="numeric",
        description=f"{period}-period price momentum",
        tags=["price", "momentum"]
    ))

# Price distance from MAs
for ma_period in [10, 20, 50, 100, 200]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_distance_sma_{ma_period}",
        category=FeatureCategory.PRICE,
        inputs=["close", f"sma_{ma_period}"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description=f"Price distance from {ma_period} SMA",
        tags=["price", "distance", "ma"]
    ))
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_distance_ema_{ma_period}",
        category=FeatureCategory.PRICE,
        inputs=["close", f"ema_{ma_period}"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description=f"Price distance from {ma_period} EMA",
        tags=["price", "distance", "ema"]
    ))

# Price Z-score
for window in [10, 20, 50, 100]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_zscore_{window}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.ZSCORE,
        params={"window": window},
        output_type="numeric",
        description=f"{window}-period price Z-score",
        tags=["price", "zscore"]
    ))

# Price percentile
for window in [50, 100, 252]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_percentile_{window}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": window},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description=f"{window}-period price percentile",
        tags=["price", "percentile"]
    ))

# Trend strength
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="price_trend_strength",
        category=FeatureCategory.PRICE,
        inputs=["close", "sma_20", "sma_50"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Overall price trend strength",
        tags=["price", "trend", "strength"]
    ),
    Feature(
        feature_id="price_acceleration",
        category=FeatureCategory.PRICE,
        inputs=["returns_1h"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 1},
        output_type="numeric",
        description="Price return acceleration",
        tags=["price", "acceleration"]
    ),
    Feature(
        feature_id="price_range_position",
        category=FeatureCategory.PRICE,
        inputs=["close", "high_20", "low_20"],
        transform=FeatureTransform.MINMAX_SCALE,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Price position within 20-day range",
        tags=["price", "range"]
    ),
    Feature(
        feature_id="price_gap",
        category=FeatureCategory.PRICE,
        inputs=["open", "prev_close"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Opening gap from previous close",
        tags=["price", "gap"]
    ),
    Feature(
        feature_id="higher_high",
        category=FeatureCategory.PRICE,
        inputs=["high"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Higher high formation",
        tags=["price", "structure"]
    ),
    Feature(
        feature_id="lower_low",
        category=FeatureCategory.PRICE,
        inputs=["low"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Lower low formation",
        tags=["price", "structure"]
    ),
])

# -----------------------------------------------------------------------------
# 2. VOLATILITY FEATURES (~60)
# -----------------------------------------------------------------------------

# ATR variations
for period in [7, 14, 21, 50]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"atr_{period}",
        category=FeatureCategory.VOLATILITY,
        inputs=["high", "low", "close"],
        transform=FeatureTransform.RAW,
        params={"period": period},
        output_type="numeric",
        description=f"{period}-period ATR",
        tags=["volatility", "atr"]
    ))

# Realized volatility
for window in [5, 10, 20, 30, 60, 90]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"realized_volatility_{window}",
        category=FeatureCategory.VOLATILITY,
        inputs=["returns_1d"],
        transform=FeatureTransform.ROLLING_STD,
        params={"window": window},
        output_type="numeric",
        description=f"{window}-day realized volatility",
        tags=["volatility", "realized"]
    ))

# Volatility percentile
for window in [50, 100, 252]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"volatility_percentile_{window}",
        category=FeatureCategory.VOLATILITY,
        inputs=["realized_volatility_20"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": window},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description=f"{window}-period volatility percentile",
        tags=["volatility", "percentile", "regime"]
    ))

# ATR percentile
for window in [50, 100, 252]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"atr_percentile_{window}",
        category=FeatureCategory.VOLATILITY,
        inputs=["atr_14"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": window},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description=f"{window}-period ATR percentile",
        tags=["volatility", "atr", "percentile"]
    ))

# Bollinger Bandwidth
for period in [10, 20, 50]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"bb_width_{period}",
        category=FeatureCategory.VOLATILITY,
        inputs=["close"],
        transform=FeatureTransform.RAW,
        params={"period": period, "std": 2},
        output_type="numeric",
        description=f"{period}-period Bollinger Bandwidth",
        tags=["volatility", "bollinger"]
    ))

# Special volatility features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="volatility_regime",
        category=FeatureCategory.VOLATILITY,
        inputs=["volatility_percentile_252"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": 0.7},
        output_type="categorical",
        description="Volatility regime (low/normal/high)",
        tags=["volatility", "regime"]
    ),
    Feature(
        feature_id="volatility_compression",
        category=FeatureCategory.VOLATILITY,
        inputs=["bb_width_20"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Volatility compression score",
        tags=["volatility", "compression", "breakout"]
    ),
    Feature(
        feature_id="volatility_expansion",
        category=FeatureCategory.VOLATILITY,
        inputs=["atr_14"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 5},
        output_type="numeric",
        description="Volatility expansion rate",
        tags=["volatility", "expansion"]
    ),
    Feature(
        feature_id="volatility_clustering",
        category=FeatureCategory.VOLATILITY,
        inputs=["realized_volatility_5", "realized_volatility_20"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Short vs long volatility ratio",
        tags=["volatility", "clustering"]
    ),
    Feature(
        feature_id="volatility_shock",
        category=FeatureCategory.VOLATILITY,
        inputs=["realized_volatility_5"],
        transform=FeatureTransform.ZSCORE,
        params={"window": 100},
        output_type="numeric",
        description="Volatility shock detector",
        tags=["volatility", "shock"]
    ),
    Feature(
        feature_id="intraday_volatility",
        category=FeatureCategory.VOLATILITY,
        inputs=["high", "low"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Intraday high-low range",
        tags=["volatility", "intraday"]
    ),
    Feature(
        feature_id="overnight_volatility",
        category=FeatureCategory.VOLATILITY,
        inputs=["open", "prev_close"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Overnight gap volatility",
        tags=["volatility", "overnight"]
    ),
    Feature(
        feature_id="parkinson_volatility",
        category=FeatureCategory.VOLATILITY,
        inputs=["high", "low"],
        transform=FeatureTransform.RAW,
        params={"window": 20},
        output_type="numeric",
        description="Parkinson volatility estimator",
        tags=["volatility", "parkinson"]
    ),
    Feature(
        feature_id="garman_klass_volatility",
        category=FeatureCategory.VOLATILITY,
        inputs=["open", "high", "low", "close"],
        transform=FeatureTransform.RAW,
        params={"window": 20},
        output_type="numeric",
        description="Garman-Klass volatility estimator",
        tags=["volatility", "garman_klass"]
    ),
    Feature(
        feature_id="vol_of_vol",
        category=FeatureCategory.VOLATILITY,
        inputs=["realized_volatility_20"],
        transform=FeatureTransform.ROLLING_STD,
        params={"window": 20},
        output_type="numeric",
        description="Volatility of volatility",
        tags=["volatility", "vol_of_vol"]
    ),
])

# -----------------------------------------------------------------------------
# 3. VOLUME FEATURES (~50)
# -----------------------------------------------------------------------------

# Volume SMAs
for period in [5, 10, 20, 50]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"volume_sma_{period}",
        category=FeatureCategory.VOLUME,
        inputs=["volume"],
        transform=FeatureTransform.SMA,
        params={"period": period},
        output_type="numeric",
        description=f"{period}-period volume SMA",
        tags=["volume", "sma"]
    ))

# Volume Z-score
for window in [10, 20, 50, 100]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"volume_zscore_{window}",
        category=FeatureCategory.VOLUME,
        inputs=["volume"],
        transform=FeatureTransform.ZSCORE,
        params={"window": window},
        output_type="numeric",
        description=f"{window}-period volume Z-score",
        tags=["volume", "zscore"]
    ))

# Volume percentile
for window in [50, 100, 252]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"volume_percentile_{window}",
        category=FeatureCategory.VOLUME,
        inputs=["volume"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": window},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description=f"{window}-period volume percentile",
        tags=["volume", "percentile"]
    ))

# Special volume features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="volume_spike",
        category=FeatureCategory.VOLUME,
        inputs=["volume", "volume_sma_20"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Volume spike (vs 20 SMA)",
        tags=["volume", "spike"]
    ),
    Feature(
        feature_id="volume_trend",
        category=FeatureCategory.VOLUME,
        inputs=["volume_sma_5", "volume_sma_20"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Volume trend (5 vs 20 SMA)",
        tags=["volume", "trend"]
    ),
    Feature(
        feature_id="volume_divergence",
        category=FeatureCategory.VOLUME,
        inputs=["price_momentum_10", "volume_momentum_10"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Price-volume divergence",
        tags=["volume", "divergence"]
    ),
    Feature(
        feature_id="buy_sell_ratio",
        category=FeatureCategory.VOLUME,
        inputs=["buy_volume", "sell_volume"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Buy/sell volume ratio",
        tags=["volume", "buy_sell"]
    ),
    Feature(
        feature_id="volume_pressure",
        category=FeatureCategory.VOLUME,
        inputs=["buy_volume", "sell_volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Net volume pressure",
        tags=["volume", "pressure"]
    ),
    Feature(
        feature_id="volume_profile_density",
        category=FeatureCategory.VOLUME,
        inputs=["volume", "price_levels"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Volume profile density at price",
        tags=["volume", "profile"]
    ),
    Feature(
        feature_id="obv",
        category=FeatureCategory.VOLUME,
        inputs=["close", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="On-Balance Volume",
        tags=["volume", "obv"]
    ),
    Feature(
        feature_id="obv_momentum",
        category=FeatureCategory.VOLUME,
        inputs=["obv"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 10},
        output_type="numeric",
        description="OBV momentum",
        tags=["volume", "obv", "momentum"]
    ),
    Feature(
        feature_id="vwap",
        category=FeatureCategory.VOLUME,
        inputs=["price", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Volume Weighted Average Price",
        tags=["volume", "vwap"]
    ),
    Feature(
        feature_id="vwap_distance",
        category=FeatureCategory.VOLUME,
        inputs=["close", "vwap"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Price distance from VWAP",
        tags=["volume", "vwap", "distance"]
    ),
    Feature(
        feature_id="volume_momentum_10",
        category=FeatureCategory.VOLUME,
        inputs=["volume"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 10},
        output_type="numeric",
        description="10-period volume momentum",
        tags=["volume", "momentum"]
    ),
    Feature(
        feature_id="relative_volume",
        category=FeatureCategory.VOLUME,
        inputs=["volume", "volume_sma_20"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Relative volume (RVOL)",
        tags=["volume", "rvol"]
    ),
    Feature(
        feature_id="volume_climax",
        category=FeatureCategory.VOLUME,
        inputs=["volume_percentile_100"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": 0.95},
        output_type="binary",
        description="Volume climax detection",
        tags=["volume", "climax"]
    ),
])

# -----------------------------------------------------------------------------
# 4. LIQUIDITY FEATURES (~50)
# -----------------------------------------------------------------------------

DEFAULT_FEATURES.extend([
    # Orderbook features
    Feature(
        feature_id="orderbook_depth_bid",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_bids"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Bid side orderbook depth",
        tags=["liquidity", "orderbook", "bid"]
    ),
    Feature(
        feature_id="orderbook_depth_ask",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_asks"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Ask side orderbook depth",
        tags=["liquidity", "orderbook", "ask"]
    ),
    Feature(
        feature_id="orderbook_imbalance",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_depth_bid", "orderbook_depth_ask"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Orderbook bid/ask imbalance",
        tags=["liquidity", "orderbook", "imbalance"]
    ),
    Feature(
        feature_id="bid_ask_spread",
        category=FeatureCategory.LIQUIDITY,
        inputs=["best_bid", "best_ask"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Bid-ask spread",
        tags=["liquidity", "spread"]
    ),
    Feature(
        feature_id="bid_ask_spread_percentile",
        category=FeatureCategory.LIQUIDITY,
        inputs=["bid_ask_spread"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Spread percentile",
        tags=["liquidity", "spread", "percentile"]
    ),
    
    # Liquidity zone features
    Feature(
        feature_id="liquidity_wall_distance_above",
        category=FeatureCategory.LIQUIDITY,
        inputs=["close", "resistance_levels"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to liquidity wall above",
        tags=["liquidity", "wall", "resistance"]
    ),
    Feature(
        feature_id="liquidity_wall_distance_below",
        category=FeatureCategory.LIQUIDITY,
        inputs=["close", "support_levels"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to liquidity wall below",
        tags=["liquidity", "wall", "support"]
    ),
    Feature(
        feature_id="thin_liquidity_above",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_asks"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Thin liquidity zone above",
        tags=["liquidity", "thin", "slippage"]
    ),
    Feature(
        feature_id="thin_liquidity_below",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_bids"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Thin liquidity zone below",
        tags=["liquidity", "thin", "slippage"]
    ),
    
    # Liquidation features
    Feature(
        feature_id="liquidation_density_long",
        category=FeatureCategory.LIQUIDITY,
        inputs=["open_interest_long", "price_levels"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Long liquidation density",
        tags=["liquidity", "liquidation", "long"]
    ),
    Feature(
        feature_id="liquidation_density_short",
        category=FeatureCategory.LIQUIDITY,
        inputs=["open_interest_short", "price_levels"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Short liquidation density",
        tags=["liquidity", "liquidation", "short"]
    ),
    Feature(
        feature_id="liquidation_imbalance",
        category=FeatureCategory.LIQUIDITY,
        inputs=["liquidation_density_long", "liquidation_density_short"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Long vs short liquidation imbalance",
        tags=["liquidity", "liquidation", "imbalance"]
    ),
    
    # Sweep probability
    Feature(
        feature_id="sweep_probability_high",
        category=FeatureCategory.LIQUIDITY,
        inputs=["stop_cluster_high", "momentum", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Probability of high sweep",
        tags=["liquidity", "sweep", "probability"]
    ),
    Feature(
        feature_id="sweep_probability_low",
        category=FeatureCategory.LIQUIDITY,
        inputs=["stop_cluster_low", "momentum", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Probability of low sweep",
        tags=["liquidity", "sweep", "probability"]
    ),
    
    # Stop clusters
    Feature(
        feature_id="stop_cluster_high",
        category=FeatureCategory.LIQUIDITY,
        inputs=["swing_highs", "orderbook"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Stop cluster above price",
        tags=["liquidity", "stops", "cluster"]
    ),
    Feature(
        feature_id="stop_cluster_low",
        category=FeatureCategory.LIQUIDITY,
        inputs=["swing_lows", "orderbook"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Stop cluster below price",
        tags=["liquidity", "stops", "cluster"]
    ),
    
    # Market depth score
    Feature(
        feature_id="market_depth_score",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_depth_bid", "orderbook_depth_ask"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Overall market depth score",
        tags=["liquidity", "depth"]
    ),
    Feature(
        feature_id="market_depth_percentile",
        category=FeatureCategory.LIQUIDITY,
        inputs=["market_depth_score"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Market depth percentile",
        tags=["liquidity", "depth", "percentile"]
    ),
    
    # Liquidity flow
    Feature(
        feature_id="liquidity_flow",
        category=FeatureCategory.LIQUIDITY,
        inputs=["orderbook_changes"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Direction of liquidity flow",
        tags=["liquidity", "flow"]
    ),
    Feature(
        feature_id="liquidity_absorption",
        category=FeatureCategory.LIQUIDITY,
        inputs=["volume", "orderbook_changes"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Liquidity absorption rate",
        tags=["liquidity", "absorption"]
    ),
    
    # Whale activity
    Feature(
        feature_id="whale_activity_score",
        category=FeatureCategory.LIQUIDITY,
        inputs=["large_orders", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Whale activity detection",
        tags=["liquidity", "whale", "smart_money"]
    ),
    Feature(
        feature_id="whale_buy_pressure",
        category=FeatureCategory.LIQUIDITY,
        inputs=["large_buy_orders"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Whale buying pressure",
        tags=["liquidity", "whale", "buy"]
    ),
    Feature(
        feature_id="whale_sell_pressure",
        category=FeatureCategory.LIQUIDITY,
        inputs=["large_sell_orders"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Whale selling pressure",
        tags=["liquidity", "whale", "sell"]
    ),
])

# -----------------------------------------------------------------------------
# 5. STRUCTURE FEATURES (~40)
# -----------------------------------------------------------------------------

DEFAULT_FEATURES.extend([
    # Distance to structure
    Feature(
        feature_id="distance_to_bos",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "bos_level"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to Break of Structure",
        tags=["structure", "bos", "distance"]
    ),
    Feature(
        feature_id="distance_to_choch",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "choch_level"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to Change of Character",
        tags=["structure", "choch", "distance"]
    ),
    Feature(
        feature_id="distance_to_swing_high",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "swing_high"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to recent swing high",
        tags=["structure", "swing", "high"]
    ),
    Feature(
        feature_id="distance_to_swing_low",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "swing_low"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to recent swing low",
        tags=["structure", "swing", "low"]
    ),
    
    # Range position
    Feature(
        feature_id="range_position",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "range_high", "range_low"],
        transform=FeatureTransform.MINMAX_SCALE,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Position within current range",
        tags=["structure", "range", "position"]
    ),
    Feature(
        feature_id="range_width",
        category=FeatureCategory.STRUCTURE,
        inputs=["range_high", "range_low"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Current range width",
        tags=["structure", "range", "width"]
    ),
    Feature(
        feature_id="range_width_percentile",
        category=FeatureCategory.STRUCTURE,
        inputs=["range_width"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Range width percentile",
        tags=["structure", "range", "percentile"]
    ),
    
    # Swing strength
    Feature(
        feature_id="swing_strength_high",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_high", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Swing high strength",
        tags=["structure", "swing", "strength"]
    ),
    Feature(
        feature_id="swing_strength_low",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_low", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Swing low strength",
        tags=["structure", "swing", "strength"]
    ),
    
    # Trend phase
    Feature(
        feature_id="trend_phase",
        category=FeatureCategory.STRUCTURE,
        inputs=["bos_count", "choch_count"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Current trend phase",
        tags=["structure", "trend", "phase"]
    ),
    Feature(
        feature_id="trend_persistence",
        category=FeatureCategory.STRUCTURE,
        inputs=["trend_duration"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 252},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Trend persistence score",
        tags=["structure", "trend", "persistence"]
    ),
    
    # Structure breaks
    Feature(
        feature_id="bos_bullish",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_highs", "close"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Bullish Break of Structure",
        tags=["structure", "bos", "bullish"]
    ),
    Feature(
        feature_id="bos_bearish",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_lows", "close"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Bearish Break of Structure",
        tags=["structure", "bos", "bearish"]
    ),
    Feature(
        feature_id="choch_bullish",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_lows", "close"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Bullish Change of Character",
        tags=["structure", "choch", "bullish"]
    ),
    Feature(
        feature_id="choch_bearish",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_highs", "close"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        output_type="binary",
        description="Bearish Change of Character",
        tags=["structure", "choch", "bearish"]
    ),
    
    # Fair Value Gaps
    Feature(
        feature_id="fvg_bullish_distance",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "fvg_bullish"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to bullish FVG",
        tags=["structure", "fvg", "bullish"]
    ),
    Feature(
        feature_id="fvg_bearish_distance",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "fvg_bearish"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to bearish FVG",
        tags=["structure", "fvg", "bearish"]
    ),
    
    # Order blocks
    Feature(
        feature_id="order_block_bullish",
        category=FeatureCategory.STRUCTURE,
        inputs=["price", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Bullish order block proximity",
        tags=["structure", "order_block", "bullish"]
    ),
    Feature(
        feature_id="order_block_bearish",
        category=FeatureCategory.STRUCTURE,
        inputs=["price", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Bearish order block proximity",
        tags=["structure", "order_block", "bearish"]
    ),
    
    # EQ levels
    Feature(
        feature_id="equal_highs_distance",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "eq_high"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to equal highs",
        tags=["structure", "eq", "high"]
    ),
    Feature(
        feature_id="equal_lows_distance",
        category=FeatureCategory.STRUCTURE,
        inputs=["close", "eq_low"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Distance to equal lows",
        tags=["structure", "eq", "low"]
    ),
])

# -----------------------------------------------------------------------------
# 6. MICROSTRUCTURE FEATURES (~50)
# -----------------------------------------------------------------------------

DEFAULT_FEATURES.extend([
    # Order flow imbalance
    Feature(
        feature_id="order_flow_imbalance",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["buy_volume", "sell_volume"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Order flow imbalance",
        tags=["microstructure", "flow", "imbalance"]
    ),
    Feature(
        feature_id="order_flow_imbalance_5m",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["buy_volume_5m", "sell_volume_5m"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="5-min order flow imbalance",
        tags=["microstructure", "flow", "5m"]
    ),
    Feature(
        feature_id="order_flow_imbalance_15m",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["buy_volume_15m", "sell_volume_15m"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="15-min order flow imbalance",
        tags=["microstructure", "flow", "15m"]
    ),
    
    # Aggressor ratio
    Feature(
        feature_id="aggressor_ratio",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["aggressive_buys", "aggressive_sells"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Aggressor buy/sell ratio",
        tags=["microstructure", "aggressor"]
    ),
    Feature(
        feature_id="buyer_aggression",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["aggressive_buys", "total_buys"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Buyer aggression level",
        tags=["microstructure", "aggression", "buy"]
    ),
    Feature(
        feature_id="seller_aggression",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["aggressive_sells", "total_sells"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Seller aggression level",
        tags=["microstructure", "aggression", "sell"]
    ),
    
    # Trade size distribution
    Feature(
        feature_id="trade_size_mean",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["trade_sizes"],
        transform=FeatureTransform.ROLLING_MEAN,
        params={"window": 100},
        output_type="numeric",
        description="Mean trade size",
        tags=["microstructure", "trade_size"]
    ),
    Feature(
        feature_id="trade_size_std",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["trade_sizes"],
        transform=FeatureTransform.ROLLING_STD,
        params={"window": 100},
        output_type="numeric",
        description="Trade size standard deviation",
        tags=["microstructure", "trade_size"]
    ),
    Feature(
        feature_id="large_trade_ratio",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["large_trades", "total_trades"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Large trade ratio",
        tags=["microstructure", "trade_size", "large"]
    ),
    
    # Execution pressure
    Feature(
        feature_id="execution_pressure",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["order_flow_imbalance", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Net execution pressure",
        tags=["microstructure", "execution"]
    ),
    Feature(
        feature_id="execution_pressure_zscore",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["execution_pressure"],
        transform=FeatureTransform.ZSCORE,
        params={"window": 100},
        output_type="numeric",
        description="Execution pressure Z-score",
        tags=["microstructure", "execution", "zscore"]
    ),
    
    # Flow dynamics
    Feature(
        feature_id="flow_acceleration",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["order_flow_imbalance"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 1},
        output_type="numeric",
        description="Flow acceleration",
        tags=["microstructure", "flow", "acceleration"]
    ),
    Feature(
        feature_id="flow_exhaustion",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["flow_acceleration", "volume"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Flow exhaustion signal",
        tags=["microstructure", "flow", "exhaustion"]
    ),
    Feature(
        feature_id="flow_persistence",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["order_flow_imbalance"],
        transform=FeatureTransform.ROLLING_MEAN,
        params={"window": 10},
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Flow persistence (smoothed)",
        tags=["microstructure", "flow", "persistence"]
    ),
    
    # Toxicity metrics
    Feature(
        feature_id="trade_toxicity",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["informed_flow_estimate"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Trade flow toxicity",
        tags=["microstructure", "toxicity"]
    ),
    Feature(
        feature_id="vpin",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["buy_volume", "sell_volume"],
        transform=FeatureTransform.RAW,
        params={"bucket_size": 50},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Volume-synchronized PIN",
        tags=["microstructure", "vpin", "toxicity"]
    ),
    
    # Spread dynamics
    Feature(
        feature_id="spread_zscore",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["bid_ask_spread"],
        transform=FeatureTransform.ZSCORE,
        params={"window": 100},
        output_type="numeric",
        description="Spread Z-score",
        tags=["microstructure", "spread"]
    ),
    Feature(
        feature_id="spread_volatility",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["bid_ask_spread"],
        transform=FeatureTransform.ROLLING_STD,
        params={"window": 20},
        output_type="numeric",
        description="Spread volatility",
        tags=["microstructure", "spread", "volatility"]
    ),
    
    # Market impact
    Feature(
        feature_id="market_impact_buy",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["buy_volume", "price_change"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Market impact of buys",
        tags=["microstructure", "impact", "buy"]
    ),
    Feature(
        feature_id="market_impact_sell",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["sell_volume", "price_change"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Market impact of sells",
        tags=["microstructure", "impact", "sell"]
    ),
    Feature(
        feature_id="price_impact_asymmetry",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["market_impact_buy", "market_impact_sell"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Buy vs sell price impact asymmetry",
        tags=["microstructure", "impact", "asymmetry"]
    ),
])

# -----------------------------------------------------------------------------
# 7. CORRELATION FEATURES (~40)
# -----------------------------------------------------------------------------

# Cross-asset correlations
corr_pairs = [
    ("btc", "spx"), ("btc", "dxy"), ("btc", "gold"), ("btc", "ndx"),
    ("eth", "btc"), ("eth", "spx"), ("sol", "btc"), ("sol", "eth")
]

for asset1, asset2 in corr_pairs:
    for window in [10, 30, 60, 90]:
        DEFAULT_FEATURES.append(Feature(
            feature_id=f"corr_{asset1}_{asset2}_{window}d",
            category=FeatureCategory.CORRELATION,
            inputs=[f"{asset1}_returns", f"{asset2}_returns"],
            transform=FeatureTransform.ROLLING_MEAN,
            params={"window": window},
            output_type="numeric",
            value_range=[-1.0, 1.0],
            description=f"{window}-day {asset1.upper()}-{asset2.upper()} correlation",
            tags=["correlation", asset1, asset2]
        ))

# Special correlation features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="corr_btc_spx_regime",
        category=FeatureCategory.CORRELATION,
        inputs=["corr_btc_spx_30d"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": 0.5},
        output_type="categorical",
        description="BTC-SPX correlation regime",
        tags=["correlation", "regime", "btc", "spx"]
    ),
    Feature(
        feature_id="corr_btc_dxy_regime",
        category=FeatureCategory.CORRELATION,
        inputs=["corr_btc_dxy_30d"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": -0.3},
        output_type="categorical",
        description="BTC-DXY inverse correlation regime",
        tags=["correlation", "regime", "btc", "dxy"]
    ),
    Feature(
        feature_id="eth_btc_lead_lag",
        category=FeatureCategory.CORRELATION,
        inputs=["eth_returns_lagged", "btc_returns"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="ETH leading/lagging BTC",
        tags=["correlation", "lead_lag", "eth", "btc"]
    ),
    Feature(
        feature_id="cross_asset_momentum_alignment",
        category=FeatureCategory.CORRELATION,
        inputs=["btc_momentum", "eth_momentum", "sol_momentum"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Cross-asset momentum alignment",
        tags=["correlation", "momentum", "cross_asset"]
    ),
    Feature(
        feature_id="cross_asset_vol_correlation",
        category=FeatureCategory.CORRELATION,
        inputs=["btc_vol", "eth_vol", "market_vol"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Cross-asset volatility correlation",
        tags=["correlation", "volatility", "cross_asset"]
    ),
    Feature(
        feature_id="risk_on_probability",
        category=FeatureCategory.CORRELATION,
        inputs=["spx_momentum", "vix_level", "dxy_strength"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Risk-on environment probability",
        tags=["correlation", "risk", "macro"]
    ),
    Feature(
        feature_id="risk_off_probability",
        category=FeatureCategory.CORRELATION,
        inputs=["spx_momentum", "vix_level", "gold_strength"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Risk-off environment probability",
        tags=["correlation", "risk", "macro"]
    ),
    Feature(
        feature_id="correlation_breakdown",
        category=FeatureCategory.CORRELATION,
        inputs=["corr_btc_spx_10d", "corr_btc_spx_60d"],
        transform=FeatureTransform.DIFFERENCE,
        output_type="numeric",
        description="Short vs long correlation breakdown",
        tags=["correlation", "breakdown"]
    ),
])

# -----------------------------------------------------------------------------
# 8. CONTEXT FEATURES (~40)
# -----------------------------------------------------------------------------

# Funding rate features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="funding_rate",
        category=FeatureCategory.CONTEXT,
        inputs=["funding_data"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Current funding rate",
        tags=["context", "funding"]
    ),
    Feature(
        feature_id="funding_rate_percentile",
        category=FeatureCategory.CONTEXT,
        inputs=["funding_rate"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 252},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Funding rate percentile",
        tags=["context", "funding", "percentile"]
    ),
    Feature(
        feature_id="funding_rate_zscore",
        category=FeatureCategory.CONTEXT,
        inputs=["funding_rate"],
        transform=FeatureTransform.ZSCORE,
        params={"window": 100},
        output_type="numeric",
        description="Funding rate Z-score",
        tags=["context", "funding", "zscore"]
    ),
    Feature(
        feature_id="funding_extreme",
        category=FeatureCategory.CONTEXT,
        inputs=["funding_rate_percentile"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": 0.9},
        output_type="binary",
        description="Extreme funding indicator",
        tags=["context", "funding", "extreme"]
    ),
    Feature(
        feature_id="funding_direction",
        category=FeatureCategory.CONTEXT,
        inputs=["funding_rate"],
        transform=FeatureTransform.BINARY_THRESHOLD,
        params={"threshold": 0},
        output_type="categorical",
        description="Funding direction (long/short bias)",
        tags=["context", "funding", "direction"]
    ),
])

# Open interest features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="open_interest",
        category=FeatureCategory.CONTEXT,
        inputs=["oi_data"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Current open interest",
        tags=["context", "open_interest"]
    ),
    Feature(
        feature_id="oi_change_rate",
        category=FeatureCategory.CONTEXT,
        inputs=["open_interest"],
        transform=FeatureTransform.DIFFERENCE,
        params={"periods": 1},
        output_type="numeric",
        description="OI change rate",
        tags=["context", "open_interest", "change"]
    ),
    Feature(
        feature_id="oi_percentile",
        category=FeatureCategory.CONTEXT,
        inputs=["open_interest"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Open interest percentile",
        tags=["context", "open_interest", "percentile"]
    ),
    Feature(
        feature_id="oi_price_divergence",
        category=FeatureCategory.CONTEXT,
        inputs=["oi_change_rate", "price_change"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="OI-price divergence",
        tags=["context", "open_interest", "divergence"]
    ),
])

# Macro context features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="macro_regime_score",
        category=FeatureCategory.CONTEXT,
        inputs=["spx_trend", "dxy_trend", "vix_level"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Macro regime score",
        tags=["context", "macro", "regime"]
    ),
    Feature(
        feature_id="risk_sentiment",
        category=FeatureCategory.CONTEXT,
        inputs=["vix_level", "credit_spread"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description="Risk sentiment indicator",
        tags=["context", "sentiment", "risk"]
    ),
    Feature(
        feature_id="market_stress_index",
        category=FeatureCategory.CONTEXT,
        inputs=["vix_percentile", "spread_percentile", "correlation_breakdown"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Market stress index",
        tags=["context", "stress", "risk"]
    ),
    Feature(
        feature_id="systemic_risk_score",
        category=FeatureCategory.CONTEXT,
        inputs=["correlation_spike", "volatility_spike", "liquidity_drop"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Systemic risk score",
        tags=["context", "systemic", "risk"]
    ),
])

# Session context
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="session_type",
        category=FeatureCategory.CONTEXT,
        inputs=["timestamp"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Trading session (Asia/London/NY)",
        tags=["context", "session"]
    ),
    Feature(
        feature_id="session_volatility_ratio",
        category=FeatureCategory.CONTEXT,
        inputs=["session_volatility", "avg_volatility"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Session vs average volatility",
        tags=["context", "session", "volatility"]
    ),
    Feature(
        feature_id="day_of_week",
        category=FeatureCategory.CONTEXT,
        inputs=["timestamp"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Day of week",
        tags=["context", "time", "day"]
    ),
    Feature(
        feature_id="hour_of_day",
        category=FeatureCategory.CONTEXT,
        inputs=["timestamp"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Hour of day",
        tags=["context", "time", "hour"]
    ),
    Feature(
        feature_id="month_of_year",
        category=FeatureCategory.CONTEXT,
        inputs=["timestamp"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Month of year",
        tags=["context", "time", "month"]
    ),
])

# Additional context
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="long_short_ratio",
        category=FeatureCategory.CONTEXT,
        inputs=["long_positions", "short_positions"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Long/short ratio",
        tags=["context", "positioning"]
    ),
    Feature(
        feature_id="long_short_percentile",
        category=FeatureCategory.CONTEXT,
        inputs=["long_short_ratio"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="L/S ratio percentile",
        tags=["context", "positioning", "percentile"]
    ),
    Feature(
        feature_id="leverage_ratio",
        category=FeatureCategory.CONTEXT,
        inputs=["open_interest", "spot_volume"],
        transform=FeatureTransform.RATIO,
        output_type="numeric",
        description="Market leverage ratio",
        tags=["context", "leverage"]
    ),
    Feature(
        feature_id="leverage_percentile",
        category=FeatureCategory.CONTEXT,
        inputs=["leverage_ratio"],
        transform=FeatureTransform.PERCENTILE_RANK,
        params={"window": 100},
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Leverage percentile",
        tags=["context", "leverage", "percentile"]
    ),
])

# -----------------------------------------------------------------------------
# ADDITIONAL FEATURES TO REACH 300+ (Extended Feature Set)
# -----------------------------------------------------------------------------

# Additional Price Features
for lag in [1, 2, 3, 5, 10]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_lag_{lag}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.LAG,
        params={"periods": lag},
        output_type="numeric",
        description=f"Price lagged by {lag} periods",
        tags=["price", "lag"]
    ))

# RSI variations
for period in [7, 14, 21, 28]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"rsi_{period}",
        category=FeatureCategory.PRICE,
        inputs=["close"],
        transform=FeatureTransform.RAW,
        params={"period": period},
        output_type="numeric",
        value_range=[0.0, 100.0],
        description=f"{period}-period RSI",
        tags=["price", "momentum", "rsi"]
    ))

# Additional Volatility Features
for window in [3, 5, 7, 10, 14, 21]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"price_volatility_{window}",
        category=FeatureCategory.VOLATILITY,
        inputs=["returns_1d"],
        transform=FeatureTransform.ROLLING_STD,
        params={"window": window},
        output_type="numeric",
        description=f"{window}-day price volatility",
        tags=["volatility", "short_term"]
    ))

# High-Low Range Features
for period in [5, 10, 20, 50]:
    DEFAULT_FEATURES.extend([
        Feature(
            feature_id=f"range_high_{period}",
            category=FeatureCategory.PRICE,
            inputs=["high"],
            transform=FeatureTransform.ROLLING_MEAN,
            params={"window": period},
            output_type="numeric",
            description=f"{period}-period rolling high",
            tags=["price", "range", "high"]
        ),
        Feature(
            feature_id=f"range_low_{period}",
            category=FeatureCategory.PRICE,
            inputs=["low"],
            transform=FeatureTransform.ROLLING_MEAN,
            params={"window": period},
            output_type="numeric",
            description=f"{period}-period rolling low",
            tags=["price", "range", "low"]
        ),
    ])

# Volume EMAs
for period in [5, 10, 20, 50, 100]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"volume_ema_{period}",
        category=FeatureCategory.VOLUME,
        inputs=["volume"],
        transform=FeatureTransform.EMA,
        params={"period": period},
        output_type="numeric",
        description=f"{period}-period volume EMA",
        tags=["volume", "ema"]
    ))

# Orderbook depth at different levels
for level in [1, 2, 3, 5, 10]:
    DEFAULT_FEATURES.extend([
        Feature(
            feature_id=f"bid_depth_level_{level}",
            category=FeatureCategory.LIQUIDITY,
            inputs=["orderbook_bids"],
            transform=FeatureTransform.RAW,
            params={"level": level},
            output_type="numeric",
            description=f"Bid depth at level {level}",
            tags=["liquidity", "orderbook", "bid"]
        ),
        Feature(
            feature_id=f"ask_depth_level_{level}",
            category=FeatureCategory.LIQUIDITY,
            inputs=["orderbook_asks"],
            transform=FeatureTransform.RAW,
            params={"level": level},
            output_type="numeric",
            description=f"Ask depth at level {level}",
            tags=["liquidity", "orderbook", "ask"]
        ),
    ])

# Flow momentum at different windows
for window in [3, 5, 10, 20, 30]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"flow_momentum_{window}",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["order_flow_imbalance"],
        transform=FeatureTransform.ROLLING_MEAN,
        params={"window": window},
        output_type="numeric",
        value_range=[-1.0, 1.0],
        description=f"{window}-period flow momentum",
        tags=["microstructure", "flow", "momentum"]
    ))

# Trade intensity features
for window in [5, 10, 20, 50]:
    DEFAULT_FEATURES.append(Feature(
        feature_id=f"trade_intensity_{window}",
        category=FeatureCategory.MICROSTRUCTURE,
        inputs=["trade_count"],
        transform=FeatureTransform.ROLLING_MEAN,
        params={"window": window},
        output_type="numeric",
        description=f"{window}-period trade intensity",
        tags=["microstructure", "intensity"]
    ))

# Additional Correlation Features
extra_corr_pairs = [
    ("btc", "vix"), ("eth", "dxy"), ("btc", "tnx"), ("btc", "oil"),
    ("eth", "gold"), ("sol", "spx"), ("btc", "usdt_dominance")
]
for asset1, asset2 in extra_corr_pairs:
    for window in [14, 30, 60]:
        DEFAULT_FEATURES.append(Feature(
            feature_id=f"corr_{asset1}_{asset2}_{window}d",
            category=FeatureCategory.CORRELATION,
            inputs=[f"{asset1}_returns", f"{asset2}_returns"],
            transform=FeatureTransform.ROLLING_MEAN,
            params={"window": window},
            output_type="numeric",
            value_range=[-1.0, 1.0],
            description=f"{window}-day {asset1.upper()}-{asset2.upper()} correlation",
            tags=["correlation", asset1, asset2]
        ))

# Structural confirmations
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="hh_hl_count",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_highs", "swing_lows"],
        transform=FeatureTransform.RAW,
        params={"lookback": 10},
        output_type="numeric",
        description="Higher high / higher low count",
        tags=["structure", "trend", "confirmation"]
    ),
    Feature(
        feature_id="ll_lh_count",
        category=FeatureCategory.STRUCTURE,
        inputs=["swing_highs", "swing_lows"],
        transform=FeatureTransform.RAW,
        params={"lookback": 10},
        output_type="numeric",
        description="Lower low / lower high count",
        tags=["structure", "trend", "confirmation"]
    ),
    Feature(
        feature_id="structure_strength",
        category=FeatureCategory.STRUCTURE,
        inputs=["bos_count", "choch_count"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        description="Overall structure strength",
        tags=["structure", "strength"]
    ),
    Feature(
        feature_id="consolidation_score",
        category=FeatureCategory.STRUCTURE,
        inputs=["range_width", "volatility"],
        transform=FeatureTransform.RAW,
        output_type="numeric",
        value_range=[0.0, 1.0],
        description="Consolidation detection score",
        tags=["structure", "consolidation"]
    ),
])

# Context momentum features
for period in [5, 10, 20]:
    DEFAULT_FEATURES.extend([
        Feature(
            feature_id=f"funding_momentum_{period}",
            category=FeatureCategory.CONTEXT,
            inputs=["funding_rate"],
            transform=FeatureTransform.DIFFERENCE,
            params={"periods": period},
            output_type="numeric",
            description=f"{period}-period funding rate momentum",
            tags=["context", "funding", "momentum"]
        ),
        Feature(
            feature_id=f"oi_momentum_{period}",
            category=FeatureCategory.CONTEXT,
            inputs=["open_interest"],
            transform=FeatureTransform.DIFFERENCE,
            params={"periods": period},
            output_type="numeric",
            description=f"{period}-period OI momentum",
            tags=["context", "open_interest", "momentum"]
        ),
    ])

# Indicator divergence features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="rsi_divergence",
        category=FeatureCategory.PRICE,
        inputs=["price", "rsi_14"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="RSI divergence detection",
        tags=["price", "divergence", "rsi"]
    ),
    Feature(
        feature_id="macd_divergence",
        category=FeatureCategory.PRICE,
        inputs=["price", "macd"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="MACD divergence detection",
        tags=["price", "divergence", "macd"]
    ),
    Feature(
        feature_id="obv_divergence",
        category=FeatureCategory.VOLUME,
        inputs=["price", "obv"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="OBV divergence detection",
        tags=["volume", "divergence", "obv"]
    ),
])

# Regime-specific features
DEFAULT_FEATURES.extend([
    Feature(
        feature_id="trend_regime",
        category=FeatureCategory.CONTEXT,
        inputs=["adx", "price_trend"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Current trend regime",
        tags=["context", "regime", "trend"]
    ),
    Feature(
        feature_id="range_regime",
        category=FeatureCategory.CONTEXT,
        inputs=["atr_percentile", "range_width"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Current range regime",
        tags=["context", "regime", "range"]
    ),
    Feature(
        feature_id="breakout_regime",
        category=FeatureCategory.CONTEXT,
        inputs=["volatility_compression", "volume_spike"],
        transform=FeatureTransform.RAW,
        output_type="categorical",
        description="Breakout regime detection",
        tags=["context", "regime", "breakout"]
    ),
])
