"""
OPS1 Position Types
===================

Data structures for deep position monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class PositionStatus(str, Enum):
    """Position lifecycle status"""
    OPEN = "OPEN"              # Normal open position
    SCALING = "SCALING"        # Being scaled up
    REDUCING = "REDUCING"      # Being reduced
    HEDGED = "HEDGED"          # Has hedge position
    CLOSING = "CLOSING"        # Being closed
    CLOSED = "CLOSED"          # Fully closed
    FORCED_CLOSE = "FORCED_CLOSE"  # Force closed (liquidation/stop)


class RiskLevel(str, Enum):
    """Position risk level"""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PositionOwnership:
    """
    Who owns this position.
    
    Links position to strategy/profile/config that created it.
    """
    position_id: str = ""
    
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    
    config_id: Optional[str] = None
    config_version: Optional[int] = None
    
    decision_trace_id: Optional[str] = None
    signal_id: Optional[str] = None
    
    # When ownership was assigned
    assigned_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "profileId": self.profile_id,
            "profileName": self.profile_name,
            "configId": self.config_id,
            "configVersion": self.config_version,
            "decisionTraceId": self.decision_trace_id,
            "signalId": self.signal_id,
            "assignedAt": self.assigned_at
        }


@dataclass
class PositionRiskView:
    """
    Risk metrics for a position.
    """
    position_id: str = ""
    
    # Exposure
    exposure_usd: float = 0.0
    exposure_pct: float = 0.0  # % of portfolio
    
    # Risk metrics
    risk_per_trade: Optional[float] = None
    max_loss_usd: Optional[float] = None
    
    # Distance metrics (as %)
    distance_to_stop_pct: Optional[float] = None
    distance_to_take_profit_pct: Optional[float] = None
    liquidation_price: Optional[float] = None
    liquidation_distance_pct: Optional[float] = None
    
    # Overall risk assessment
    risk_level: RiskLevel = RiskLevel.MODERATE
    risk_factors: List[str] = field(default_factory=list)
    
    # Volatility context
    current_atr: Optional[float] = None
    position_atr_ratio: Optional[float] = None
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "exposureUsd": round(self.exposure_usd, 2),
            "exposurePct": round(self.exposure_pct, 4),
            "riskPerTrade": self.risk_per_trade,
            "maxLossUsd": self.max_loss_usd,
            "distanceToStopPct": self.distance_to_stop_pct,
            "distanceToTakeProfitPct": self.distance_to_take_profit_pct,
            "liquidationPrice": self.liquidation_price,
            "liquidationDistancePct": self.liquidation_distance_pct,
            "riskLevel": self.risk_level.value,
            "riskFactors": self.risk_factors,
            "currentAtr": self.current_atr,
            "positionAtrRatio": self.position_atr_ratio,
            "computedAt": self.computed_at
        }


@dataclass
class DeepPositionState:
    """
    Complete position state with all metadata.
    
    This is the first-class operational entity.
    """
    
    # Identity
    position_id: str = ""
    exchange: str = ""
    symbol: str = ""
    side: str = ""  # LONG / SHORT
    
    # Size and price
    quantity: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    avg_price: float = 0.0
    
    # PnL
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Leverage and margin
    leverage: Optional[float] = None
    margin_mode: Optional[str] = None  # ISOLATED / CROSS
    margin_used: Optional[float] = None
    
    # Ownership
    ownership: Optional[PositionOwnership] = None
    
    # Lifecycle
    status: PositionStatus = PositionStatus.OPEN
    opened_at: int = 0
    updated_at: int = 0
    closed_at: Optional[int] = None
    age_minutes: float = 0.0
    
    # Modification tracking
    scale_count: int = 0
    reduce_count: int = 0
    last_scaled_at: Optional[int] = None
    last_reduced_at: Optional[int] = None
    
    # Risk
    risk_view: Optional[PositionRiskView] = None
    
    # Stop/Take profit
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Event ledger reference
    last_event_id: Optional[str] = None
    event_count: int = 0
    
    # Tags for filtering
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entryPrice": self.entry_price,
            "markPrice": self.mark_price,
            "avgPrice": self.avg_price,
            "unrealizedPnl": round(self.unrealized_pnl, 2),
            "realizedPnl": round(self.realized_pnl, 2),
            "totalPnl": round(self.total_pnl, 2),
            "pnlPct": round(self.pnl_pct, 4),
            "leverage": self.leverage,
            "marginMode": self.margin_mode,
            "marginUsed": self.margin_used,
            "ownership": self.ownership.to_dict() if self.ownership else None,
            "status": self.status.value,
            "openedAt": self.opened_at,
            "updatedAt": self.updated_at,
            "closedAt": self.closed_at,
            "ageMinutes": round(self.age_minutes, 1),
            "scaleCount": self.scale_count,
            "reduceCount": self.reduce_count,
            "lastScaledAt": self.last_scaled_at,
            "lastReducedAt": self.last_reduced_at,
            "riskView": self.risk_view.to_dict() if self.risk_view else None,
            "stopLoss": self.stop_loss,
            "takeProfit": self.take_profit,
            "lastEventId": self.last_event_id,
            "eventCount": self.event_count,
            "tags": self.tags
        }


@dataclass
class PositionSummary:
    """
    Aggregated summary of all positions.
    """
    open_positions: int = 0
    total_positions: int = 0
    
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_pnl: float = 0.0
    
    total_exposure_usd: float = 0.0
    
    largest_position_symbol: Optional[str] = None
    largest_position_exposure: float = 0.0
    
    highest_risk_position_id: Optional[str] = None
    highest_risk_level: Optional[str] = None
    
    positions_by_exchange: Dict[str, int] = field(default_factory=dict)
    positions_by_strategy: Dict[str, int] = field(default_factory=dict)
    positions_by_status: Dict[str, int] = field(default_factory=dict)
    
    winning_positions: int = 0
    losing_positions: int = 0
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "openPositions": self.open_positions,
            "totalPositions": self.total_positions,
            "totalUnrealizedPnl": round(self.total_unrealized_pnl, 2),
            "totalRealizedPnl": round(self.total_realized_pnl, 2),
            "totalPnl": round(self.total_pnl, 2),
            "totalExposureUsd": round(self.total_exposure_usd, 2),
            "largestPositionSymbol": self.largest_position_symbol,
            "largestPositionExposure": round(self.largest_position_exposure, 2),
            "highestRiskPositionId": self.highest_risk_position_id,
            "highestRiskLevel": self.highest_risk_level,
            "positionsByExchange": self.positions_by_exchange,
            "positionsByStrategy": self.positions_by_strategy,
            "positionsByStatus": self.positions_by_status,
            "winningPositions": self.winning_positions,
            "losingPositions": self.losing_positions,
            "computedAt": self.computed_at
        }
