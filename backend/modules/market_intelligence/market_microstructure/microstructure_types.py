"""
PHASE 9 - Market Microstructure Types
======================================
Core data types for microstructure analysis.

Provides understanding of:
- How price moves inside liquidity
- Who is driving the market (aggressor)
- Where micro-imbalances occur
- Optimal execution timing
- Short-term flow pressure
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class FlowState(str, Enum):
    """Order flow state"""
    BUYER_DOMINANT = "BUYER_DOMINANT"
    SELLER_DOMINANT = "SELLER_DOMINANT"
    BALANCED = "BALANCED"
    CHOPPY = "CHOPPY"
    BURST_BUY = "BURST_BUY"
    BURST_SELL = "BURST_SELL"


class AggressorSide(str, Enum):
    """Aggressor side detection"""
    BUYER = "BUYER"
    SELLER = "SELLER"
    NEUTRAL = "NEUTRAL"
    UNCLEAR = "UNCLEAR"


class TimingSignal(str, Enum):
    """Execution timing signal"""
    ENTER_NOW = "ENTER_NOW"
    WAIT_PULLBACK = "WAIT_PULLBACK"
    PARTIAL_ENTRY = "PARTIAL_ENTRY"
    REDUCE_ONLY = "REDUCE_ONLY"
    EXIT_NOW = "EXIT_NOW"
    HOLD = "HOLD"


class PressureState(str, Enum):
    """Flow pressure state"""
    BUILDING_BUY = "BUILDING_BUY"
    BUILDING_SELL = "BUILDING_SELL"
    EXHAUSTION_BUY = "EXHAUSTION_BUY"
    EXHAUSTION_SELL = "EXHAUSTION_SELL"
    ABSORPTION = "ABSORPTION"
    FAKE_PUSH = "FAKE_PUSH"
    NEUTRAL = "NEUTRAL"


class ImbalanceType(str, Enum):
    """Type of micro-imbalance"""
    BID_DOMINANT = "BID_DOMINANT"
    ASK_DOMINANT = "ASK_DOMINANT"
    VACUUM = "VACUUM"
    SKEW = "SKEW"
    BALANCED = "BALANCED"


@dataclass
class OrderFlowSnapshot:
    """Order flow analysis snapshot"""
    symbol: str
    timestamp: datetime
    
    # Flow metrics
    flow_state: FlowState
    buy_flow: float               # Buy side volume
    sell_flow: float              # Sell side volume
    net_flow: float               # buy - sell
    flow_ratio: float             # buy / (buy + sell)
    
    # Aggression metrics
    aggressive_buy: float         # Aggressive buy volume
    aggressive_sell: float        # Aggressive sell volume
    aggression_score: float       # -1 (sell) to 1 (buy)
    
    # Activity metrics
    burst_detected: bool = False
    burst_direction: Optional[str] = None
    flow_persistence: float = 0.0  # How consistent is the flow
    absorption_detected: bool = False
    
    # Pressure
    buy_pressure: float = 0.0
    sell_pressure: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "flow_state": self.flow_state.value,
            "buy_flow": round(self.buy_flow, 2),
            "sell_flow": round(self.sell_flow, 2),
            "net_flow": round(self.net_flow, 2),
            "flow_ratio": round(self.flow_ratio, 4),
            "aggressive_buy": round(self.aggressive_buy, 2),
            "aggressive_sell": round(self.aggressive_sell, 2),
            "aggression_score": round(self.aggression_score, 4),
            "burst_detected": self.burst_detected,
            "burst_direction": self.burst_direction,
            "flow_persistence": round(self.flow_persistence, 3),
            "absorption_detected": self.absorption_detected,
            "buy_pressure": round(self.buy_pressure, 3),
            "sell_pressure": round(self.sell_pressure, 3)
        }


@dataclass
class AggressorAnalysis:
    """Aggressor side detection result"""
    symbol: str
    timestamp: datetime
    
    # Primary determination
    aggressor_side: AggressorSide
    aggressor_confidence: float      # 0-1
    
    # Ratio metrics
    aggressor_ratio: float           # Ratio of aggressor trades
    buy_initiated_pct: float         # % trades near ask
    sell_initiated_pct: float        # % trades near bid
    
    # Shift detection
    aggressor_shift: bool = False    # Did aggressor change recently
    previous_aggressor: Optional[AggressorSide] = None
    shift_timestamp: Optional[datetime] = None
    
    # Context
    trade_count: int = 0
    analysis_window_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "aggressor_side": self.aggressor_side.value,
            "aggressor_confidence": round(self.aggressor_confidence, 3),
            "aggressor_ratio": round(self.aggressor_ratio, 4),
            "buy_initiated_pct": round(self.buy_initiated_pct, 4),
            "sell_initiated_pct": round(self.sell_initiated_pct, 4),
            "aggressor_shift": self.aggressor_shift,
            "previous_aggressor": self.previous_aggressor.value if self.previous_aggressor else None,
            "shift_timestamp": self.shift_timestamp.isoformat() if self.shift_timestamp else None,
            "trade_count": self.trade_count,
            "analysis_window_ms": self.analysis_window_ms
        }


@dataclass
class MicroImbalance:
    """Micro-imbalance analysis"""
    symbol: str
    timestamp: datetime
    
    # Imbalance metrics
    micro_imbalance_score: float    # -1 to 1
    imbalance_type: ImbalanceType
    dominant_micro_side: str        # BID or ASK
    
    # Characteristics
    vacuum_risk: float              # Risk of sudden move
    imbalance_duration_ms: int      # How long imbalance lasted
    imbalance_strength: float       # Strength of imbalance
    
    # Top of book analysis
    top_bid_size: float = 0.0
    top_ask_size: float = 0.0
    top_book_skew: float = 0.0      # (bid - ask) / (bid + ask)
    
    # Volatility
    short_term_volatility: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "micro_imbalance_score": round(self.micro_imbalance_score, 4),
            "imbalance_type": self.imbalance_type.value,
            "dominant_micro_side": self.dominant_micro_side,
            "vacuum_risk": round(self.vacuum_risk, 3),
            "imbalance_duration_ms": self.imbalance_duration_ms,
            "imbalance_strength": round(self.imbalance_strength, 3),
            "top_bid_size": round(self.top_bid_size, 2),
            "top_ask_size": round(self.top_ask_size, 2),
            "top_book_skew": round(self.top_book_skew, 4),
            "short_term_volatility": round(self.short_term_volatility, 6)
        }


@dataclass
class ExecutionTiming:
    """Execution timing recommendation"""
    symbol: str
    timestamp: datetime
    
    # Primary signal
    timing_signal: TimingSignal
    timing_quality: float           # 0-1 (how good is timing now)
    
    # Urgency
    urgency_score: float            # 0-1
    execution_readiness: float      # 0-1
    
    # Factors considered
    micro_flow_aligned: bool = True
    spread_favorable: bool = True
    liquidity_available: bool = True
    aggressor_aligned: bool = True
    
    # Recommendations
    entry_size_pct: float = 100.0   # Recommended entry size %
    delay_recommendation_ms: int = 0
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "timing_signal": self.timing_signal.value,
            "timing_quality": round(self.timing_quality, 3),
            "urgency_score": round(self.urgency_score, 3),
            "execution_readiness": round(self.execution_readiness, 3),
            "micro_flow_aligned": self.micro_flow_aligned,
            "spread_favorable": self.spread_favorable,
            "liquidity_available": self.liquidity_available,
            "aggressor_aligned": self.aggressor_aligned,
            "entry_size_pct": round(self.entry_size_pct, 1),
            "delay_recommendation_ms": self.delay_recommendation_ms,
            "notes": self.notes
        }


@dataclass
class FlowPressure:
    """Short-term flow pressure analysis"""
    symbol: str
    timestamp: datetime
    
    # Pressure state
    flow_pressure_state: PressureState
    pressure_direction: str         # UP, DOWN, NEUTRAL
    pressure_strength: float        # 0-1
    
    # Exhaustion detection
    exhaustion_probability: float   # 0-1
    exhaustion_type: Optional[str] = None  # BUY or SELL
    
    # Building pressure
    building_detected: bool = False
    building_direction: Optional[str] = None
    
    # Absorption & fake signals
    absorption_score: float = 0.0
    fake_push_probability: float = 0.0
    
    # Persistence
    pressure_persistence: float = 0.0  # How long pressure sustained
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "flow_pressure_state": self.flow_pressure_state.value,
            "pressure_direction": self.pressure_direction,
            "pressure_strength": round(self.pressure_strength, 3),
            "exhaustion_probability": round(self.exhaustion_probability, 3),
            "exhaustion_type": self.exhaustion_type,
            "building_detected": self.building_detected,
            "building_direction": self.building_direction,
            "absorption_score": round(self.absorption_score, 3),
            "fake_push_probability": round(self.fake_push_probability, 3),
            "pressure_persistence": round(self.pressure_persistence, 3)
        }


@dataclass
class UnifiedMicrostructureSnapshot:
    """Complete microstructure state for a symbol"""
    symbol: str
    timestamp: datetime
    
    # Flow state
    flow_state: FlowState
    aggressor_ratio: float
    
    # Imbalance
    micro_imbalance_score: float
    
    # Timing
    timing_signal: TimingSignal
    execution_readiness: float
    
    # Pressure
    pressure_direction: str
    pressure_strength: float
    exhaustion_probability: float
    
    # Additional context
    spread_bps: float = 0.0
    volatility: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "flowState": self.flow_state.value,
            "aggressorRatio": round(self.aggressor_ratio, 4),
            "microImbalanceScore": round(self.micro_imbalance_score, 4),
            "timingSignal": self.timing_signal.value,
            "executionReadiness": round(self.execution_readiness, 3),
            "pressureDirection": self.pressure_direction,
            "pressureStrength": round(self.pressure_strength, 3),
            "exhaustionProbability": round(self.exhaustion_probability, 3),
            "spreadBps": round(self.spread_bps, 2),
            "volatility": round(self.volatility, 6)
        }


# Default configuration
DEFAULT_MICROSTRUCTURE_CONFIG = {
    "flow_window_ms": 5000,           # 5 second window for flow
    "aggressor_threshold": 0.55,       # Threshold for aggressor determination
    "imbalance_threshold": 0.3,        # Min imbalance to flag
    "burst_threshold": 2.0,            # Multiple of avg for burst detection
    "exhaustion_threshold": 0.7,       # Threshold for exhaustion signal
    "vacuum_threshold": 0.2,           # Threshold for vacuum detection
    "persistence_window": 10,          # Number of periods for persistence
}
