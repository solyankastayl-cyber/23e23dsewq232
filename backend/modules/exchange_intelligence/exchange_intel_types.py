"""
PHASE 13.8 — Exchange Intelligence Types
==========================================
Output contracts for all exchange engines.
Each engine produces a typed signal that the aggregator consumes.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


# ── Enums ──────────────────────────────────────

class ExchangeBias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class FundingState(str, Enum):
    LONG_CROWDED = "LONG_CROWDED"
    SHORT_CROWDED = "SHORT_CROWDED"
    NEUTRAL = "NEUTRAL"
    EXTREME_LONG = "EXTREME_LONG"
    EXTREME_SHORT = "EXTREME_SHORT"


class OIPressureState(str, Enum):
    EXPANDING = "EXPANDING"
    CONTRACTING = "CONTRACTING"
    STABLE = "STABLE"
    DIVERGENT_BULLISH = "DIVERGENT_BULLISH"
    DIVERGENT_BEARISH = "DIVERGENT_BEARISH"


class DerivativesPressure(str, Enum):
    LONG_SQUEEZE = "LONG_SQUEEZE"
    SHORT_SQUEEZE = "SHORT_SQUEEZE"
    LEVERAGE_EXCESS = "LEVERAGE_EXCESS"
    BALANCED = "BALANCED"


class LiquidationRisk(str, Enum):
    CASCADE_IMMINENT = "CASCADE_IMMINENT"
    ELEVATED = "ELEVATED"
    NORMAL = "NORMAL"
    LOW = "LOW"


class FlowDirection(str, Enum):
    AGGRESSIVE_BUY = "AGGRESSIVE_BUY"
    AGGRESSIVE_SELL = "AGGRESSIVE_SELL"
    ABSORPTION_BUY = "ABSORPTION_BUY"
    ABSORPTION_SELL = "ABSORPTION_SELL"
    BALANCED = "BALANCED"


class VolumeState(str, Enum):
    BREAKOUT_CONFIRMED = "BREAKOUT_CONFIRMED"
    CLIMAX = "CLIMAX"
    EXHAUSTION = "EXHAUSTION"
    ABNORMAL_HIGH = "ABNORMAL_HIGH"
    ABNORMAL_LOW = "ABNORMAL_LOW"
    NORMAL = "NORMAL"


# ── Engine Outputs ──────────────────────────────

@dataclass
class FundingOISignal:
    """Output of funding_oi_engine"""
    symbol: str
    timestamp: datetime
    funding_rate: float
    funding_annualized: float
    funding_state: FundingState
    oi_value: float
    oi_change_pct: float
    oi_pressure: OIPressureState
    crowding_risk: float          # 0-1
    funding_oi_divergence: bool   # funding vs OI mismatch
    confidence: float             # 0-1
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "funding_rate": round(self.funding_rate, 6),
            "funding_annualized": round(self.funding_annualized, 4),
            "funding_state": self.funding_state.value,
            "oi_value": round(self.oi_value, 2),
            "oi_change_pct": round(self.oi_change_pct, 4),
            "oi_pressure": self.oi_pressure.value,
            "crowding_risk": round(self.crowding_risk, 3),
            "funding_oi_divergence": self.funding_oi_divergence,
            "confidence": round(self.confidence, 3),
            "drivers": self.drivers,
        }


@dataclass
class DerivativesPressureSignal:
    """Output of derivatives_pressure_engine"""
    symbol: str
    timestamp: datetime
    long_short_ratio: float
    leverage_index: float         # 0-1, 1 = extreme leverage
    squeeze_probability: float    # 0-1
    pressure_state: DerivativesPressure
    perp_premium: float           # perp vs spot premium %
    confidence: float
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "long_short_ratio": round(self.long_short_ratio, 4),
            "leverage_index": round(self.leverage_index, 3),
            "squeeze_probability": round(self.squeeze_probability, 3),
            "pressure_state": self.pressure_state.value,
            "perp_premium": round(self.perp_premium, 4),
            "confidence": round(self.confidence, 3),
            "drivers": self.drivers,
        }


@dataclass
class LiquidationSignal:
    """Output of exchange_liquidation_engine"""
    symbol: str
    timestamp: datetime
    long_liq_zone: float          # price level
    short_liq_zone: float         # price level
    cascade_probability: float    # 0-1
    trapped_longs_pct: float      # % of OI in danger
    trapped_shorts_pct: float
    liquidation_risk: LiquidationRisk
    net_liq_flow: float           # positive = more long liqs
    confidence: float
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "long_liq_zone": round(self.long_liq_zone, 2),
            "short_liq_zone": round(self.short_liq_zone, 2),
            "cascade_probability": round(self.cascade_probability, 3),
            "trapped_longs_pct": round(self.trapped_longs_pct, 3),
            "trapped_shorts_pct": round(self.trapped_shorts_pct, 3),
            "liquidation_risk": self.liquidation_risk.value,
            "net_liq_flow": round(self.net_liq_flow, 4),
            "confidence": round(self.confidence, 3),
            "drivers": self.drivers,
        }


@dataclass
class ExchangeFlowSignal:
    """Output of exchange_flow_engine"""
    symbol: str
    timestamp: datetime
    taker_buy_ratio: float        # 0-1, >0.5 = buyers dominate
    aggressive_flow: float        # -1 to 1
    absorption_detected: bool
    flow_direction: FlowDirection
    flow_intensity: float         # 0-1
    confidence: float
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "taker_buy_ratio": round(self.taker_buy_ratio, 4),
            "aggressive_flow": round(self.aggressive_flow, 4),
            "absorption_detected": self.absorption_detected,
            "flow_direction": self.flow_direction.value,
            "flow_intensity": round(self.flow_intensity, 3),
            "confidence": round(self.confidence, 3),
            "drivers": self.drivers,
        }


@dataclass
class VolumeContextSignal:
    """Output of exchange_volume_engine"""
    symbol: str
    timestamp: datetime
    volume_24h: float
    volume_ratio: float           # current / avg
    volume_state: VolumeState
    buy_volume_pct: float         # % of volume that is buy
    volume_trend: str             # INCREASING, DECREASING, FLAT
    anomaly_score: float          # 0-1
    confidence: float
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "volume_24h": round(self.volume_24h, 2),
            "volume_ratio": round(self.volume_ratio, 3),
            "volume_state": self.volume_state.value,
            "buy_volume_pct": round(self.buy_volume_pct, 4),
            "volume_trend": self.volume_trend,
            "anomaly_score": round(self.anomaly_score, 3),
            "confidence": round(self.confidence, 3),
            "drivers": self.drivers,
        }


# ── Aggregator Output ──────────────────────────

@dataclass
class ExchangeContext:
    """
    Unified Exchange Intelligence output.
    This is what the Trading Decision Layer consumes.
    """
    symbol: str
    timestamp: datetime

    # Overall
    exchange_bias: ExchangeBias
    confidence: float

    # Sub-signals
    funding_state: FundingState
    oi_pressure: OIPressureState
    derivatives_pressure: float   # -1 (bearish) to 1 (bullish)
    liquidation_risk: float       # 0-1
    flow_pressure: float          # -1 to 1
    volume_state: VolumeState

    # Risk
    crowding_risk: float
    squeeze_probability: float
    cascade_probability: float

    # Drivers
    drivers: List[str] = field(default_factory=list)

    # Sub-signal objects (optional full detail)
    funding_signal: Optional[FundingOISignal] = None
    derivatives_signal: Optional[DerivativesPressureSignal] = None
    liquidation_signal: Optional[LiquidationSignal] = None
    flow_signal: Optional[ExchangeFlowSignal] = None
    volume_signal: Optional[VolumeContextSignal] = None

    def to_dict(self) -> Dict:
        result = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "exchange_bias": self.exchange_bias.value,
            "confidence": round(self.confidence, 3),
            "funding_state": self.funding_state.value,
            "oi_pressure": self.oi_pressure.value,
            "derivatives_pressure": round(self.derivatives_pressure, 3),
            "liquidation_risk": round(self.liquidation_risk, 3),
            "flow_pressure": round(self.flow_pressure, 3),
            "volume_state": self.volume_state.value,
            "crowding_risk": round(self.crowding_risk, 3),
            "squeeze_probability": round(self.squeeze_probability, 3),
            "cascade_probability": round(self.cascade_probability, 3),
            "drivers": self.drivers,
        }
        if self.funding_signal:
            result["funding_detail"] = self.funding_signal.to_dict()
        if self.derivatives_signal:
            result["derivatives_detail"] = self.derivatives_signal.to_dict()
        if self.liquidation_signal:
            result["liquidation_detail"] = self.liquidation_signal.to_dict()
        if self.flow_signal:
            result["flow_detail"] = self.flow_signal.to_dict()
        if self.volume_signal:
            result["volume_detail"] = self.volume_signal.to_dict()
        return result
