"""
PHASE 13.1 - Alpha Node Types
==============================
Core data types for Alpha Node Registry.

Node types designed for:
- Alpha Graph (logical relationships)
- Alpha DAG (computational dependencies)
- Feature Library (base features)
- Factor Generator (factor combinations)
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class NodeType(str, Enum):
    """Alpha node type classification."""
    ALPHA = "alpha"                     # Trading signals (trend_strength, breakout_pressure)
    STRUCTURE = "structure"             # Market structure (bos, choch, swing_high)
    LIQUIDITY = "liquidity"             # Liquidity analysis (stop_cluster, sweep)
    MICROSTRUCTURE = "microstructure"   # Order flow (aggression, imbalance)
    CONTEXT = "context"                 # Market context (funding, OI, macro)
    CORRELATION = "correlation"         # Cross-asset correlations
    PORTFOLIO = "portfolio"             # Portfolio state (drawdown, risk_budget)
    FEATURE = "feature"                 # Base features for DAG (price, volume, volatility)
    FACTOR = "factor"                   # Computed factors (combinations of features)


class NodeCategory(str, Enum):
    """Node category for grouping."""
    PRICE = "price"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    TREND = "trend"
    MOMENTUM = "momentum"
    ORDERBOOK = "orderbook"
    FUNDING = "funding"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    TECHNICAL = "technical"


class NodeStatus(str, Enum):
    """Node lifecycle status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    DISABLED = "disabled"


@dataclass
class AlphaNode:
    """
    Alpha Node Definition.
    
    Designed for both:
    - Alpha Graph (logical relationships)
    - Alpha DAG (computational dependencies)
    """
    
    # Identity
    node_id: str
    node_type: NodeType
    
    # Source
    source_module: str                  # e.g., "alpha_engine", "market_structure"
    
    # DAG compatibility (inputs/outputs)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    
    # Computation (for DAG)
    compute_function: Optional[str] = None   # Function name for DAG executor
    compute_params: Dict = field(default_factory=dict)
    
    # Description
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    # Regime dependency (for Alpha Graph)
    regime_dependency: List[str] = field(default_factory=list)
    
    # Value characteristics
    value_type: str = "float"           # float, int, bool, categorical
    value_range: Optional[List[float]] = None
    confidence_range: List[float] = field(default_factory=lambda: [0.0, 1.0])
    
    # Relationships (for Alpha Graph)
    supports: List[str] = field(default_factory=list)
    contradicts: List[str] = field(default_factory=list)
    amplifies: List[str] = field(default_factory=list)
    conditional_on: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: str = "1.0.0"
    status: NodeStatus = NodeStatus.ACTIVE
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, NodeType) else self.node_type,
            "source_module": self.source_module,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "compute_function": self.compute_function,
            "compute_params": self.compute_params,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "regime_dependency": self.regime_dependency,
            "value_type": self.value_type,
            "value_range": self.value_range,
            "confidence_range": self.confidence_range,
            "supports": self.supports,
            "contradicts": self.contradicts,
            "amplifies": self.amplifies,
            "conditional_on": self.conditional_on,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "status": self.status.value if isinstance(self.status, NodeStatus) else self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AlphaNode":
        """Create from dictionary."""
        return cls(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]) if data.get("node_type") else NodeType.ALPHA,
            source_module=data.get("source_module", "unknown"),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            compute_function=data.get("compute_function"),
            compute_params=data.get("compute_params", {}),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category"),
            regime_dependency=data.get("regime_dependency", []),
            value_type=data.get("value_type", "float"),
            value_range=data.get("value_range"),
            confidence_range=data.get("confidence_range", [0.0, 1.0]),
            supports=data.get("supports", []),
            contradicts=data.get("contradicts", []),
            amplifies=data.get("amplifies", []),
            conditional_on=data.get("conditional_on", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            version=data.get("version", "1.0.0"),
            status=NodeStatus(data["status"]) if data.get("status") else NodeStatus.ACTIVE
        )


@dataclass
class NodeUsageRecord:
    """Track node usage in signals/factors."""
    node_id: str
    used_in: str                        # signal_id or factor_id
    used_at: datetime
    context: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "used_in": self.used_in,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "context": self.context
        }


@dataclass
class NodePerformanceRecord:
    """Track node performance metrics."""
    node_id: str
    timestamp: datetime
    
    # Performance metrics
    hit_rate: float = 0.0
    information_coefficient: float = 0.0
    sharpe_contribution: float = 0.0
    decay_rate: float = 0.0
    
    # Usage stats
    usage_count: int = 0
    active_factors: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "hit_rate": self.hit_rate,
            "information_coefficient": self.information_coefficient,
            "sharpe_contribution": self.sharpe_contribution,
            "decay_rate": self.decay_rate,
            "usage_count": self.usage_count,
            "active_factors": self.active_factors
        }


# Default nodes configuration
DEFAULT_ALPHA_NODES = [
    # ===== ALPHA NODES =====
    AlphaNode(
        node_id="trend_strength",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["price", "sma_20", "sma_50"],
        outputs=["trend_strength_signal"],
        description="Measures overall trend strength using multiple timeframes",
        tags=["trend", "momentum", "core"],
        category="trend",
        regime_dependency=["TRENDING"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="trend_acceleration",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["trend_strength", "momentum"],
        outputs=["trend_acceleration_signal"],
        description="Detects acceleration or deceleration in trend",
        tags=["trend", "momentum"],
        category="trend",
        regime_dependency=["TRENDING"],
        supports=["trend_strength"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="trend_exhaustion",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["trend_strength", "rsi", "volume"],
        outputs=["trend_exhaustion_signal"],
        description="Detects potential trend exhaustion",
        tags=["trend", "reversal", "divergence"],
        category="trend",
        regime_dependency=["TRENDING"],
        contradicts=["trend_strength", "breakout_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="breakout_pressure",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["volatility_compression", "volume", "range"],
        outputs=["breakout_pressure_signal"],
        description="Measures pressure building for breakout",
        tags=["breakout", "volatility", "compression"],
        category="volatility",
        regime_dependency=["LOW_VOL", "PRE_BREAKOUT"],
        supports=["volatility_compression"],
        confidence_range=[0.2, 0.9]
    ),
    AlphaNode(
        node_id="volatility_compression",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["atr_percentile", "bb_width", "range_compression"],
        outputs=["volatility_compression_signal"],
        description="Detects volatility compression before expansion",
        tags=["volatility", "breakout", "compression"],
        category="volatility",
        regime_dependency=["LOW_VOL"],
        supports=["breakout_pressure"],
        confidence_range=[0.3, 0.95]
    ),
    AlphaNode(
        node_id="volatility_expansion",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["atr", "bb_width", "range"],
        outputs=["volatility_expansion_signal"],
        description="Detects volatility expansion",
        tags=["volatility", "breakout"],
        category="volatility",
        regime_dependency=["HIGH_VOL"],
        contradicts=["volatility_compression"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="reversal_pressure",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["trend_exhaustion", "divergence", "structure"],
        outputs=["reversal_pressure_signal"],
        description="Measures reversal probability",
        tags=["reversal", "divergence"],
        category="trend",
        regime_dependency=["TRENDING", "EXHAUSTION"],
        supports=["trend_exhaustion"],
        contradicts=["trend_strength", "breakout_pressure"],
        confidence_range=[0.2, 0.85]
    ),
    AlphaNode(
        node_id="volume_confirmation",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["volume", "volume_sma", "price_direction"],
        outputs=["volume_confirmation_signal"],
        description="Confirms price moves with volume",
        tags=["volume", "confirmation"],
        category="volume",
        amplifies=["trend_strength", "breakout_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="volume_anomaly",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["volume", "volume_percentile"],
        outputs=["volume_anomaly_signal"],
        description="Detects unusual volume spikes",
        tags=["volume", "anomaly"],
        category="volume",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="liquidity_sweep_alpha",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["liquidity_zones", "price", "volume"],
        outputs=["liquidity_sweep_signal"],
        description="Detects liquidity sweep setups",
        tags=["liquidity", "sweep", "reversal"],
        category="liquidity",
        regime_dependency=["HIGH_LIQUIDITY_CLUSTER"],
        supports=["reversal_pressure"],
        confidence_range=[0.3, 0.9]
    ),
    
    # ===== STRUCTURE NODES =====
    AlphaNode(
        node_id="bos",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["swing_high", "swing_low", "price"],
        outputs=["bos_signal", "bos_direction"],
        description="Break of Structure detection",
        tags=["structure", "trend", "continuation"],
        category="technical",
        supports=["trend_strength"],
        confidence_range=[0.5, 1.0]
    ),
    AlphaNode(
        node_id="choch",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["swing_high", "swing_low", "price"],
        outputs=["choch_signal", "choch_direction"],
        description="Change of Character detection",
        tags=["structure", "reversal"],
        category="technical",
        supports=["reversal_pressure"],
        contradicts=["trend_strength"],
        confidence_range=[0.5, 1.0]
    ),
    AlphaNode(
        node_id="swing_high",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["price", "lookback"],
        outputs=["swing_high_price", "swing_high_index"],
        description="Swing high identification",
        tags=["structure", "swing"],
        category="technical",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="swing_low",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["price", "lookback"],
        outputs=["swing_low_price", "swing_low_index"],
        description="Swing low identification",
        tags=["structure", "swing"],
        category="technical",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="range_high",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["price", "range_period"],
        outputs=["range_high_price"],
        description="Range high boundary",
        tags=["structure", "range"],
        category="technical"
    ),
    AlphaNode(
        node_id="range_low",
        node_type=NodeType.STRUCTURE,
        source_module="market_structure",
        inputs=["price", "range_period"],
        outputs=["range_low_price"],
        description="Range low boundary",
        tags=["structure", "range"],
        category="technical"
    ),
    
    # ===== LIQUIDITY NODES =====
    AlphaNode(
        node_id="stop_cluster",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["orderbook", "swing_highs", "swing_lows"],
        outputs=["stop_cluster_price", "stop_cluster_size"],
        description="Stop loss cluster detection",
        tags=["liquidity", "stops", "target"],
        category="orderbook",
        confidence_range=[0.3, 0.95]
    ),
    AlphaNode(
        node_id="liquidation_zone",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["open_interest", "funding", "price_levels"],
        outputs=["liquidation_price", "liquidation_size"],
        description="Liquidation zone detection",
        tags=["liquidity", "liquidation", "leverage"],
        category="funding",
        confidence_range=[0.4, 0.9]
    ),
    AlphaNode(
        node_id="liquidity_wall",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["orderbook_depth"],
        outputs=["wall_price", "wall_size", "wall_side"],
        description="Large orderbook wall detection",
        tags=["liquidity", "orderbook", "resistance"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="thin_liquidity",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["orderbook_depth", "spread"],
        outputs=["thin_liquidity_zones"],
        description="Thin liquidity zone detection",
        tags=["liquidity", "slippage", "risk"],
        category="orderbook",
        supports=["breakout_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="sweep_probability",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["stop_cluster", "momentum", "volume"],
        outputs=["sweep_probability_signal"],
        description="Probability of liquidity sweep",
        tags=["liquidity", "sweep", "probability"],
        category="orderbook",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="liquidity_imbalance",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["bid_depth", "ask_depth"],
        outputs=["liquidity_imbalance_ratio"],
        description="Bid/ask liquidity imbalance",
        tags=["liquidity", "orderbook", "imbalance"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="liquidity_depth_score",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["orderbook_depth"],
        outputs=["depth_score"],
        description="Overall market depth score",
        tags=["liquidity", "depth"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="liquidity_flow",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["orderbook_changes"],
        outputs=["liquidity_flow_direction"],
        description="Direction of liquidity flow",
        tags=["liquidity", "flow"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="whale_activity",
        node_type=NodeType.LIQUIDITY,
        source_module="liquidity_intelligence",
        inputs=["large_orders", "volume"],
        outputs=["whale_activity_signal"],
        description="Large player activity detection",
        tags=["liquidity", "whale", "smart_money"],
        category="orderbook"
    ),
    
    # ===== MICROSTRUCTURE NODES =====
    AlphaNode(
        node_id="buyer_aggression",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["trades", "orderbook"],
        outputs=["buyer_aggression_score"],
        description="Buyer aggression level",
        tags=["microstructure", "aggressor", "buying"],
        category="orderbook",
        supports=["trend_strength"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="seller_aggression",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["trades", "orderbook"],
        outputs=["seller_aggression_score"],
        description="Seller aggression level",
        tags=["microstructure", "aggressor", "selling"],
        category="orderbook",
        contradicts=["buyer_aggression"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="flow_pressure",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["buyer_aggression", "seller_aggression"],
        outputs=["flow_pressure_direction", "flow_pressure_strength"],
        description="Net order flow pressure",
        tags=["microstructure", "flow", "pressure"],
        category="orderbook",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="orderbook_imbalance",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["bid_volume", "ask_volume"],
        outputs=["imbalance_ratio", "imbalance_direction"],
        description="Orderbook bid/ask imbalance",
        tags=["microstructure", "orderbook", "imbalance"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="execution_timing",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["volatility", "spread", "depth"],
        outputs=["optimal_execution_score"],
        description="Optimal execution timing signal",
        tags=["microstructure", "execution", "timing"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="trade_flow_toxicity",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["trades", "informed_flow"],
        outputs=["toxicity_score"],
        description="Trade flow toxicity (informed vs noise)",
        tags=["microstructure", "toxicity", "informed"],
        category="orderbook"
    ),
    AlphaNode(
        node_id="spread_dynamics",
        node_type=NodeType.MICROSTRUCTURE,
        source_module="market_microstructure",
        inputs=["bid", "ask"],
        outputs=["spread", "spread_percentile"],
        description="Bid-ask spread analysis",
        tags=["microstructure", "spread"],
        category="orderbook"
    ),
    
    # ===== CONTEXT NODES =====
    AlphaNode(
        node_id="funding_extreme",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["funding_rate", "funding_history"],
        outputs=["funding_extreme_signal", "funding_direction"],
        description="Extreme funding rate detection",
        tags=["context", "funding", "leverage"],
        category="funding",
        contradicts=["breakout_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="oi_expansion",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["open_interest", "oi_history"],
        outputs=["oi_expansion_signal"],
        description="Open interest expansion",
        tags=["context", "open_interest", "leverage"],
        category="funding",
        supports=["trend_strength"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="oi_divergence",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["open_interest", "price"],
        outputs=["oi_divergence_signal"],
        description="OI/price divergence",
        tags=["context", "open_interest", "divergence"],
        category="funding",
        supports=["reversal_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="macro_risk_on",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["spx", "dxy", "vix"],
        outputs=["risk_on_signal"],
        description="Macro risk-on environment",
        tags=["context", "macro", "risk"],
        category="macro",
        supports=["trend_strength"],
        contradicts=["macro_risk_off"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="macro_risk_off",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["spx", "dxy", "vix"],
        outputs=["risk_off_signal"],
        description="Macro risk-off environment",
        tags=["context", "macro", "risk"],
        category="macro",
        contradicts=["macro_risk_on", "trend_strength"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="volatility_regime",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["realized_volatility", "implied_volatility"],
        outputs=["volatility_regime_state"],
        description="Current volatility regime",
        tags=["context", "volatility", "regime"],
        category="volatility"
    ),
    AlphaNode(
        node_id="session_context",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["timestamp"],
        outputs=["session_type", "session_liquidity"],
        description="Trading session context",
        tags=["context", "session", "time"],
        category="technical"
    ),
    AlphaNode(
        node_id="news_sentiment",
        node_type=NodeType.CONTEXT,
        source_module="market_context",
        inputs=["news_feed"],
        outputs=["sentiment_score"],
        description="News sentiment analysis",
        tags=["context", "sentiment", "news"],
        category="sentiment"
    ),
    
    # ===== CORRELATION NODES =====
    AlphaNode(
        node_id="btc_spx_correlation",
        node_type=NodeType.CORRELATION,
        source_module="correlation_engine",
        inputs=["btc_returns", "spx_returns"],
        outputs=["correlation_coefficient", "correlation_regime"],
        description="BTC-SPX correlation",
        tags=["correlation", "btc", "spx", "macro"],
        category="macro",
        confidence_range=[-1.0, 1.0]
    ),
    AlphaNode(
        node_id="btc_dxy_inverse",
        node_type=NodeType.CORRELATION,
        source_module="correlation_engine",
        inputs=["btc_returns", "dxy_returns"],
        outputs=["inverse_correlation"],
        description="BTC-DXY inverse correlation",
        tags=["correlation", "btc", "dxy", "macro"],
        category="macro",
        confidence_range=[-1.0, 1.0]
    ),
    AlphaNode(
        node_id="eth_btc_lead",
        node_type=NodeType.CORRELATION,
        source_module="correlation_engine",
        inputs=["eth_returns", "btc_returns"],
        outputs=["lead_lag_signal"],
        description="ETH leading/lagging BTC",
        tags=["correlation", "eth", "btc", "lead_lag"],
        category="technical"
    ),
    AlphaNode(
        node_id="gold_btc_divergence",
        node_type=NodeType.CORRELATION,
        source_module="correlation_engine",
        inputs=["gold_returns", "btc_returns"],
        outputs=["divergence_signal"],
        description="Gold-BTC divergence",
        tags=["correlation", "gold", "btc", "macro"],
        category="macro"
    ),
    AlphaNode(
        node_id="cross_asset_momentum",
        node_type=NodeType.CORRELATION,
        source_module="correlation_engine",
        inputs=["asset_returns"],
        outputs=["momentum_alignment"],
        description="Cross-asset momentum alignment",
        tags=["correlation", "momentum", "cross_asset"],
        category="momentum"
    ),
    
    # ===== PORTFOLIO NODES =====
    AlphaNode(
        node_id="drawdown_state",
        node_type=NodeType.PORTFOLIO,
        source_module="portfolio_construction",
        inputs=["equity_curve"],
        outputs=["drawdown_pct", "drawdown_duration"],
        description="Current drawdown state",
        tags=["portfolio", "risk", "drawdown"],
        category="portfolio"
    ),
    AlphaNode(
        node_id="risk_budget",
        node_type=NodeType.PORTFOLIO,
        source_module="portfolio_construction",
        inputs=["positions", "volatility"],
        outputs=["risk_budget_used", "risk_budget_remaining"],
        description="Risk budget utilization",
        tags=["portfolio", "risk", "budget"],
        category="portfolio"
    ),
    AlphaNode(
        node_id="portfolio_health",
        node_type=NodeType.PORTFOLIO,
        source_module="portfolio_construction",
        inputs=["positions", "pnl", "risk"],
        outputs=["health_score"],
        description="Overall portfolio health",
        tags=["portfolio", "health"],
        category="portfolio"
    ),
    AlphaNode(
        node_id="allocation_shift",
        node_type=NodeType.PORTFOLIO,
        source_module="portfolio_construction",
        inputs=["current_allocation", "target_allocation"],
        outputs=["shift_required", "rebalance_urgency"],
        description="Required allocation shift",
        tags=["portfolio", "allocation", "rebalance"],
        category="portfolio"
    ),
    
    # ===== FEATURE NODES (for DAG) =====
    AlphaNode(
        node_id="price_returns",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["returns"],
        compute_function="calculate_returns",
        description="Price returns calculation",
        tags=["feature", "price", "returns"],
        category="price"
    ),
    AlphaNode(
        node_id="realized_volatility",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["returns"],
        outputs=["realized_vol"],
        compute_function="calculate_realized_volatility",
        compute_params={"window": 20},
        description="Realized volatility",
        tags=["feature", "volatility"],
        category="volatility"
    ),
    AlphaNode(
        node_id="volatility_percentile",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["realized_volatility"],
        outputs=["vol_percentile"],
        compute_function="percentile_rank",
        compute_params={"window": 252},
        description="Volatility percentile rank",
        tags=["feature", "volatility", "percentile"],
        category="volatility"
    ),
    AlphaNode(
        node_id="atr",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["high", "low", "close"],
        outputs=["atr_value"],
        compute_function="calculate_atr",
        compute_params={"period": 14},
        description="Average True Range",
        tags=["feature", "volatility", "atr"],
        category="volatility"
    ),
    AlphaNode(
        node_id="rsi",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["rsi_value"],
        compute_function="calculate_rsi",
        compute_params={"period": 14},
        description="Relative Strength Index",
        tags=["feature", "momentum", "rsi"],
        category="momentum"
    ),
    AlphaNode(
        node_id="volume_sma",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["volume"],
        outputs=["volume_sma_value"],
        compute_function="simple_moving_average",
        compute_params={"period": 20},
        description="Volume Simple Moving Average",
        tags=["feature", "volume", "sma"],
        category="volume"
    ),
    AlphaNode(
        node_id="volume_percentile",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["volume"],
        outputs=["vol_percentile"],
        compute_function="percentile_rank",
        compute_params={"window": 100},
        description="Volume percentile rank",
        tags=["feature", "volume", "percentile"],
        category="volume"
    ),
    AlphaNode(
        node_id="bb_width",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["bb_width_value"],
        compute_function="bollinger_bandwidth",
        compute_params={"period": 20, "std": 2},
        description="Bollinger Band Width",
        tags=["feature", "volatility", "bollinger"],
        category="volatility"
    ),
    AlphaNode(
        node_id="range_compression",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["high", "low"],
        outputs=["compression_ratio"],
        compute_function="calculate_range_compression",
        compute_params={"short_period": 5, "long_period": 20},
        description="Price range compression ratio",
        tags=["feature", "volatility", "compression"],
        category="volatility"
    ),
    AlphaNode(
        node_id="momentum_score",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["momentum_value"],
        compute_function="calculate_momentum",
        compute_params={"period": 10},
        description="Price momentum score",
        tags=["feature", "momentum"],
        category="momentum"
    ),
    AlphaNode(
        node_id="sma_20",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["sma_20_value"],
        compute_function="simple_moving_average",
        compute_params={"period": 20},
        description="20-period SMA",
        tags=["feature", "trend", "sma"],
        category="trend"
    ),
    AlphaNode(
        node_id="sma_50",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["sma_50_value"],
        compute_function="simple_moving_average",
        compute_params={"period": 50},
        description="50-period SMA",
        tags=["feature", "trend", "sma"],
        category="trend"
    ),
    AlphaNode(
        node_id="sma_200",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["sma_200_value"],
        compute_function="simple_moving_average",
        compute_params={"period": 200},
        description="200-period SMA",
        tags=["feature", "trend", "sma"],
        category="trend"
    ),
    AlphaNode(
        node_id="ema_12",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["ema_12_value"],
        compute_function="exponential_moving_average",
        compute_params={"period": 12},
        description="12-period EMA",
        tags=["feature", "trend", "ema"],
        category="trend"
    ),
    AlphaNode(
        node_id="ema_26",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price"],
        outputs=["ema_26_value"],
        compute_function="exponential_moving_average",
        compute_params={"period": 26},
        description="26-period EMA",
        tags=["feature", "trend", "ema"],
        category="trend"
    ),
    AlphaNode(
        node_id="macd",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["ema_12", "ema_26"],
        outputs=["macd_line", "macd_signal", "macd_histogram"],
        compute_function="calculate_macd",
        compute_params={"signal_period": 9},
        description="MACD indicator",
        tags=["feature", "momentum", "macd"],
        category="momentum"
    ),
    AlphaNode(
        node_id="stochastic",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["high", "low", "close"],
        outputs=["stoch_k", "stoch_d"],
        compute_function="calculate_stochastic",
        compute_params={"k_period": 14, "d_period": 3},
        description="Stochastic oscillator",
        tags=["feature", "momentum", "stochastic"],
        category="momentum"
    ),
    AlphaNode(
        node_id="vwap",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price", "volume"],
        outputs=["vwap_value"],
        compute_function="calculate_vwap",
        description="Volume Weighted Average Price",
        tags=["feature", "volume", "vwap"],
        category="volume"
    ),
    AlphaNode(
        node_id="obv",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["price", "volume"],
        outputs=["obv_value"],
        compute_function="calculate_obv",
        description="On-Balance Volume",
        tags=["feature", "volume", "obv"],
        category="volume"
    ),
    AlphaNode(
        node_id="adx",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["high", "low", "close"],
        outputs=["adx_value", "plus_di", "minus_di"],
        compute_function="calculate_adx",
        compute_params={"period": 14},
        description="Average Directional Index",
        tags=["feature", "trend", "adx"],
        category="trend"
    ),
    AlphaNode(
        node_id="keltner_channels",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["high", "low", "close"],
        outputs=["kc_upper", "kc_middle", "kc_lower"],
        compute_function="calculate_keltner",
        compute_params={"period": 20, "multiplier": 2},
        description="Keltner Channels",
        tags=["feature", "volatility", "keltner"],
        category="volatility"
    ),
    AlphaNode(
        node_id="atr_percentile",
        node_type=NodeType.FEATURE,
        source_module="feature_library",
        inputs=["atr"],
        outputs=["atr_percentile_value"],
        compute_function="percentile_rank",
        compute_params={"window": 100},
        description="ATR percentile rank",
        tags=["feature", "volatility", "percentile"],
        category="volatility"
    ),
    
    # ===== FACTOR NODES (computed combinations) =====
    AlphaNode(
        node_id="trend_momentum_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["trend_strength", "momentum_score", "adx"],
        outputs=["trend_momentum_score"],
        compute_function="combine_trend_momentum",
        description="Combined trend and momentum factor",
        tags=["factor", "trend", "momentum"],
        category="factor",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="volatility_regime_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["volatility_percentile", "atr_percentile", "bb_width"],
        outputs=["vol_regime_score"],
        compute_function="combine_volatility_regime",
        description="Volatility regime factor",
        tags=["factor", "volatility", "regime"],
        category="factor"
    ),
    AlphaNode(
        node_id="liquidity_quality_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["liquidity_depth_score", "spread_dynamics", "volume_percentile"],
        outputs=["liquidity_quality_score"],
        compute_function="combine_liquidity_quality",
        description="Liquidity quality factor",
        tags=["factor", "liquidity", "quality"],
        category="factor"
    ),
    AlphaNode(
        node_id="flow_conviction_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["buyer_aggression", "seller_aggression", "flow_pressure", "volume_confirmation"],
        outputs=["flow_conviction_score"],
        compute_function="combine_flow_conviction",
        description="Order flow conviction factor",
        tags=["factor", "flow", "conviction"],
        category="factor"
    ),
    AlphaNode(
        node_id="risk_adjusted_momentum_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["momentum_score", "realized_volatility", "drawdown_state"],
        outputs=["risk_adj_momentum_score"],
        compute_function="calculate_risk_adjusted_momentum",
        description="Risk-adjusted momentum factor",
        tags=["factor", "momentum", "risk"],
        category="factor"
    ),
    AlphaNode(
        node_id="reversal_probability_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["trend_exhaustion", "reversal_pressure", "rsi", "volume_divergence"],
        outputs=["reversal_prob_score"],
        compute_function="calculate_reversal_probability",
        description="Reversal probability factor",
        tags=["factor", "reversal", "probability"],
        category="factor"
    ),
    AlphaNode(
        node_id="breakout_quality_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["volatility_compression", "breakout_pressure", "volume_confirmation", "thin_liquidity"],
        outputs=["breakout_quality_score"],
        compute_function="calculate_breakout_quality",
        description="Breakout quality factor",
        tags=["factor", "breakout", "quality"],
        category="factor"
    ),
    AlphaNode(
        node_id="market_health_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["macro_risk_on", "volatility_regime", "correlation_regime"],
        outputs=["market_health_score"],
        compute_function="calculate_market_health",
        description="Overall market health factor",
        tags=["factor", "market", "health"],
        category="factor"
    ),
    AlphaNode(
        node_id="entry_quality_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["trend_momentum_factor", "flow_conviction_factor", "liquidity_quality_factor"],
        outputs=["entry_quality_score"],
        compute_function="calculate_entry_quality",
        description="Combined entry quality factor",
        tags=["factor", "entry", "quality"],
        category="factor"
    ),
    AlphaNode(
        node_id="regime_alignment_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["volatility_regime", "trend_regime", "correlation_regime"],
        outputs=["regime_alignment_score"],
        compute_function="calculate_regime_alignment",
        description="Multi-regime alignment factor",
        tags=["factor", "regime", "alignment"],
        category="factor"
    ),
    AlphaNode(
        node_id="smart_money_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["whale_activity", "flow_pressure", "liquidity_sweep_alpha"],
        outputs=["smart_money_score"],
        compute_function="calculate_smart_money",
        description="Smart money activity factor",
        tags=["factor", "smart_money", "whale"],
        category="factor"
    ),
    AlphaNode(
        node_id="divergence_factor",
        node_type=NodeType.FACTOR,
        source_module="factor_generator",
        inputs=["oi_divergence", "volume_divergence", "price_rsi_divergence"],
        outputs=["divergence_score"],
        compute_function="calculate_divergence",
        description="Multi-indicator divergence factor",
        tags=["factor", "divergence"],
        category="factor"
    ),
    
    # ===== Additional Alpha Nodes =====
    AlphaNode(
        node_id="accumulation_distribution",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["price", "volume", "range"],
        outputs=["acc_dist_signal"],
        description="Accumulation/Distribution phase detection",
        tags=["alpha", "accumulation", "distribution"],
        category="volume",
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="momentum_divergence",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["price", "rsi", "macd"],
        outputs=["momentum_divergence_signal"],
        description="Price/momentum divergence detection",
        tags=["alpha", "momentum", "divergence"],
        category="momentum",
        supports=["reversal_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="volume_divergence",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["price", "volume"],
        outputs=["volume_divergence_signal"],
        description="Price/volume divergence",
        tags=["alpha", "volume", "divergence"],
        category="volume",
        supports=["reversal_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="range_bound_signal",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["range_high", "range_low", "atr"],
        outputs=["range_bound_signal"],
        description="Range-bound market detection",
        tags=["alpha", "range", "consolidation"],
        category="technical",
        contradicts=["trend_strength", "breakout_pressure"],
        confidence_range=[0.0, 1.0]
    ),
    AlphaNode(
        node_id="price_rsi_divergence",
        node_type=NodeType.ALPHA,
        source_module="alpha_engine",
        inputs=["price", "rsi"],
        outputs=["rsi_divergence_signal"],
        description="Price vs RSI divergence",
        tags=["alpha", "rsi", "divergence"],
        category="momentum",
        supports=["reversal_pressure"],
        confidence_range=[0.0, 1.0]
    ),
]
