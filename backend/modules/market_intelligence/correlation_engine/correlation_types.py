"""
PHASE 7 - Correlation Engine Types
====================================
Core data types for cross-asset correlation analysis.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime


class CorrelationMethod(str, Enum):
    """Correlation calculation methods"""
    PEARSON = "PEARSON"       # Linear correlation
    SPEARMAN = "SPEARMAN"     # Rank correlation
    KENDALL = "KENDALL"       # Ordinal correlation


class CorrelationStrength(str, Enum):
    """Correlation strength categories"""
    STRONG_POSITIVE = "STRONG_POSITIVE"    # > 0.7
    MODERATE_POSITIVE = "MODERATE_POSITIVE" # 0.3 to 0.7
    WEAK = "WEAK"                          # -0.3 to 0.3
    MODERATE_NEGATIVE = "MODERATE_NEGATIVE" # -0.7 to -0.3
    STRONG_NEGATIVE = "STRONG_NEGATIVE"    # < -0.7


class CorrelationRegime(str, Enum):
    """Market correlation regimes"""
    MACRO_DOMINANT = "MACRO_DOMINANT"     # High correlation with traditional assets
    CRYPTO_NATIVE = "CRYPTO_NATIVE"       # Crypto moves independently
    DECOUPLING = "DECOUPLING"             # Breaking from usual correlations
    RISK_OFF = "RISK_OFF"                 # High correlations, everything sells
    RISK_ON = "RISK_ON"                   # High correlations, everything buys
    TRANSITIONING = "TRANSITIONING"       # Regime changing


class AssetClass(str, Enum):
    """Asset classes"""
    CRYPTO_MAJOR = "CRYPTO_MAJOR"    # BTC, ETH
    CRYPTO_ALT = "CRYPTO_ALT"        # Altcoins
    EQUITY_INDEX = "EQUITY_INDEX"    # SPX, NASDAQ
    FOREX = "FOREX"                   # DXY, EUR/USD
    COMMODITY = "COMMODITY"           # Gold, Oil
    BOND = "BOND"                     # Treasury yields


@dataclass
class AssetPair:
    """Pair of assets for correlation analysis"""
    asset_a: str
    asset_b: str
    asset_a_class: AssetClass
    asset_b_class: AssetClass
    
    def to_dict(self) -> Dict:
        return {
            "asset_a": self.asset_a,
            "asset_b": self.asset_b,
            "asset_a_class": self.asset_a_class.value if isinstance(self.asset_a_class, Enum) else self.asset_a_class,
            "asset_b_class": self.asset_b_class.value if isinstance(self.asset_b_class, Enum) else self.asset_b_class
        }
    
    @property
    def pair_id(self) -> str:
        return f"{self.asset_a}_{self.asset_b}"


@dataclass
class CorrelationValue:
    """Single correlation measurement"""
    pair: AssetPair
    value: float
    method: CorrelationMethod
    window_size: int  # In candles
    timestamp: datetime
    
    # Statistical significance
    p_value: Optional[float] = None
    confidence: float = 0.0
    
    # Classification
    strength: CorrelationStrength = CorrelationStrength.WEAK
    
    def to_dict(self) -> Dict:
        return {
            "pair": self.pair.to_dict(),
            "value": round(self.value, 4),
            "method": self.method.value if isinstance(self.method, Enum) else self.method,
            "window_size": self.window_size,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "p_value": round(self.p_value, 4) if self.p_value else None,
            "confidence": round(self.confidence, 3),
            "strength": self.strength.value if isinstance(self.strength, Enum) else self.strength
        }


@dataclass
class RollingCorrelation:
    """Rolling correlation over time"""
    pair: AssetPair
    window_size: int
    method: CorrelationMethod
    
    # Time series
    timestamps: List[datetime] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    
    # Statistics
    current_value: float = 0.0
    mean_value: float = 0.0
    std_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    
    # Trend
    trend: str = "STABLE"  # INCREASING, DECREASING, STABLE
    
    def to_dict(self) -> Dict:
        return {
            "pair": self.pair.to_dict(),
            "window_size": self.window_size,
            "method": self.method.value if isinstance(self.method, Enum) else self.method,
            "data_points": len(self.values),
            "current_value": round(self.current_value, 4),
            "mean_value": round(self.mean_value, 4),
            "std_value": round(self.std_value, 4),
            "min_value": round(self.min_value, 4),
            "max_value": round(self.max_value, 4),
            "trend": self.trend
        }


@dataclass
class LeadLagResult:
    """Lead/lag relationship between assets"""
    pair: AssetPair
    
    # Lead/lag detection
    leader: str           # Which asset leads
    follower: str         # Which asset follows
    lag_candles: int      # Optimal lag
    lag_correlation: float # Correlation at optimal lag
    
    # Statistical measures
    confidence: float = 0.0
    p_value: Optional[float] = None
    
    # Cross-correlation at different lags
    lag_correlations: Dict[int, float] = field(default_factory=dict)
    
    computed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "pair": self.pair.to_dict(),
            "leader": self.leader,
            "follower": self.follower,
            "lag_candles": self.lag_candles,
            "lag_correlation": round(self.lag_correlation, 4),
            "confidence": round(self.confidence, 3),
            "p_value": round(self.p_value, 4) if self.p_value else None,
            "lag_correlations": {k: round(v, 4) for k, v in self.lag_correlations.items()},
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }


@dataclass
class RegimeState:
    """Current correlation regime state"""
    regime: CorrelationRegime
    confidence: float
    
    # Key indicators
    btc_spx_corr: float = 0.0
    btc_dxy_corr: float = 0.0
    btc_eth_corr: float = 0.0
    crypto_equity_avg: float = 0.0
    
    # Regime characteristics
    description: str = ""
    trading_implications: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    duration_candles: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "regime": self.regime.value if isinstance(self.regime, Enum) else self.regime,
            "confidence": round(self.confidence, 3),
            "btc_spx_corr": round(self.btc_spx_corr, 4),
            "btc_dxy_corr": round(self.btc_dxy_corr, 4),
            "btc_eth_corr": round(self.btc_eth_corr, 4),
            "crypto_equity_avg": round(self.crypto_equity_avg, 4),
            "description": self.description,
            "trading_implications": self.trading_implications,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_candles": self.duration_candles
        }


@dataclass
class CrossAssetSignal:
    """Signal generated from cross-asset analysis"""
    signal_id: str
    signal_type: str  # DIVERGENCE, CONVERGENCE, LEAD_SIGNAL, REGIME_SHIFT
    
    # Assets involved
    trigger_asset: str
    target_asset: str
    
    # Signal details
    direction: str  # BULLISH, BEARISH, NEUTRAL
    strength: float  # 0-1
    description: str
    
    # Basis
    correlation_basis: Optional[CorrelationValue] = None
    lead_lag_basis: Optional[LeadLagResult] = None
    regime_basis: Optional[RegimeState] = None
    
    # Timing
    generated_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "trigger_asset": self.trigger_asset,
            "target_asset": self.target_asset,
            "direction": self.direction,
            "strength": round(self.strength, 3),
            "description": self.description,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


# Default asset pairs for analysis
DEFAULT_PAIRS = [
    AssetPair("BTC", "ETH", AssetClass.CRYPTO_MAJOR, AssetClass.CRYPTO_MAJOR),
    AssetPair("BTC", "SPX", AssetClass.CRYPTO_MAJOR, AssetClass.EQUITY_INDEX),
    AssetPair("BTC", "DXY", AssetClass.CRYPTO_MAJOR, AssetClass.FOREX),
    AssetPair("BTC", "NASDAQ", AssetClass.CRYPTO_MAJOR, AssetClass.EQUITY_INDEX),
    AssetPair("BTC", "GOLD", AssetClass.CRYPTO_MAJOR, AssetClass.COMMODITY),
    AssetPair("ETH", "SOL", AssetClass.CRYPTO_MAJOR, AssetClass.CRYPTO_ALT),
    AssetPair("ETH", "SPX", AssetClass.CRYPTO_MAJOR, AssetClass.EQUITY_INDEX),
    AssetPair("SPX", "NASDAQ", AssetClass.EQUITY_INDEX, AssetClass.EQUITY_INDEX),
    AssetPair("DXY", "GOLD", AssetClass.FOREX, AssetClass.COMMODITY),
]


# Regime thresholds
REGIME_THRESHOLDS = {
    "MACRO_DOMINANT": {
        "min_btc_spx_corr": 0.5,
        "min_crypto_equity_avg": 0.4
    },
    "CRYPTO_NATIVE": {
        "max_btc_spx_corr": 0.3,
        "min_btc_eth_corr": 0.7
    },
    "RISK_OFF": {
        "min_correlation_avg": 0.6,
        "btc_trend": "DOWN"
    },
    "RISK_ON": {
        "min_correlation_avg": 0.6,
        "btc_trend": "UP"
    }
}
