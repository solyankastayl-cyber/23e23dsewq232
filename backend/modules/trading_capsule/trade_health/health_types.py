"""
Trade Health Types
==================

Core types for PHASE 3.2 Advanced Trade Health Engine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class HealthStatus(str, Enum):
    """Trade health status levels"""
    EXCELLENT = "EXCELLENT"   # 80-100: Trade performing well above expectations
    GOOD = "GOOD"             # 60-80: Trade progressing as expected
    STABLE = "STABLE"         # 40-60: Trade within acceptable parameters  
    WEAK = "WEAK"             # 20-40: Trade showing signs of deterioration
    CRITICAL = "CRITICAL"     # 10-20: Trade in danger zone
    TERMINAL = "TERMINAL"     # 0-10: Trade should be closed immediately


class EventType(str, Enum):
    """Health event types"""
    # Positive events
    TREND_CONFIRMED = "TREND_CONFIRMED"
    BREAKOUT_CONFIRMED = "BREAKOUT_CONFIRMED"
    MOMENTUM_SURGE = "MOMENTUM_SURGE"
    STRUCTURE_SUPPORT = "STRUCTURE_SUPPORT"
    VOLUME_CONFIRMATION = "VOLUME_CONFIRMATION"
    TARGET_APPROACH = "TARGET_APPROACH"
    
    # Negative events
    STRUCTURE_BREAK = "STRUCTURE_BREAK"
    MOMENTUM_LOSS = "MOMENTUM_LOSS"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    REGIME_SWITCH = "REGIME_SWITCH"
    VOLUME_DIVERGENCE = "VOLUME_DIVERGENCE"
    TIME_DECAY = "TIME_DECAY"
    STOP_APPROACH = "STOP_APPROACH"
    
    # Neutral events
    CONSOLIDATION = "CONSOLIDATION"
    RETEST = "RETEST"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "INFO"           # Informational only
    WARNING = "WARNING"     # Attention needed
    CRITICAL = "CRITICAL"   # Immediate action required
    EMERGENCY = "EMERGENCY" # Position at extreme risk


class DecayType(str, Enum):
    """Types of health decay"""
    TIME_DECAY = "TIME_DECAY"           # Natural decay over time
    VOLATILITY_DECAY = "VOLATILITY_DECAY"  # Decay from vol changes
    MOMENTUM_DECAY = "MOMENTUM_DECAY"   # Decay from momentum loss
    STRUCTURE_DECAY = "STRUCTURE_DECAY" # Decay from structure breaks
    EVENT_DECAY = "EVENT_DECAY"         # Decay from negative events


# ===========================================
# Health Event
# ===========================================

@dataclass
class HealthEvent:
    """Individual health event"""
    event_id: str = ""
    position_id: str = ""
    event_type: EventType = EventType.CONSOLIDATION
    
    # Event details
    description: str = ""
    impact: float = 0.0  # -100 to +100 impact on health
    confidence: float = 0.0  # 0-1 confidence in event detection
    
    # Context
    price_at_event: float = 0.0
    health_before: float = 0.0
    health_after: float = 0.0
    
    # Triggers
    trigger_indicators: List[str] = field(default_factory=list)
    trigger_values: Dict[str, float] = field(default_factory=dict)
    
    # Timestamps
    detected_at: int = 0
    expires_at: int = 0  # When event becomes stale
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "positionId": self.position_id,
            "type": self.event_type.value,
            "description": self.description,
            "impact": round(self.impact, 2),
            "confidence": round(self.confidence, 3),
            "priceAtEvent": self.price_at_event,
            "healthBefore": round(self.health_before, 1),
            "healthAfter": round(self.health_after, 1),
            "triggers": {
                "indicators": self.trigger_indicators,
                "values": self.trigger_values
            },
            "detectedAt": self.detected_at,
            "expiresAt": self.expires_at
        }


# ===========================================
# Health Decay Record
# ===========================================

@dataclass
class HealthDecayRecord:
    """Record of health decay"""
    position_id: str = ""
    decay_type: DecayType = DecayType.TIME_DECAY
    
    # Decay details
    decay_amount: float = 0.0
    decay_rate: float = 0.0  # Per-period decay rate
    cumulative_decay: float = 0.0
    
    # Source
    source_event_id: Optional[str] = None
    source_description: str = ""
    
    # State
    health_before: float = 0.0
    health_after: float = 0.0
    
    # Timestamps
    applied_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "decayType": self.decay_type.value,
            "decayAmount": round(self.decay_amount, 2),
            "decayRate": round(self.decay_rate, 4),
            "cumulativeDecay": round(self.cumulative_decay, 2),
            "source": {
                "eventId": self.source_event_id,
                "description": self.source_description
            },
            "healthBefore": round(self.health_before, 1),
            "healthAfter": round(self.health_after, 1),
            "appliedAt": self.applied_at
        }


# ===========================================
# Health Alert
# ===========================================

@dataclass
class HealthAlert:
    """Health alert for a position"""
    alert_id: str = ""
    position_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    
    # Alert content
    title: str = ""
    message: str = ""
    
    # Context
    current_health: float = 0.0
    health_trend: str = "STABLE"  # IMPROVING, STABLE, DETERIORATING
    trigger_event_id: Optional[str] = None
    
    # Actions
    recommended_action: str = "MONITOR"  # MONITOR, REDUCE, CLOSE, HEDGE
    action_urgency: str = "LOW"  # LOW, MEDIUM, HIGH, IMMEDIATE
    
    # Status
    acknowledged: bool = False
    acknowledged_at: Optional[int] = None
    resolved: bool = False
    resolved_at: Optional[int] = None
    
    # Timestamps
    created_at: int = 0
    expires_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alertId": self.alert_id,
            "positionId": self.position_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "context": {
                "currentHealth": round(self.current_health, 1),
                "healthTrend": self.health_trend,
                "triggerEventId": self.trigger_event_id
            },
            "action": {
                "recommended": self.recommended_action,
                "urgency": self.action_urgency
            },
            "status": {
                "acknowledged": self.acknowledged,
                "acknowledgedAt": self.acknowledged_at,
                "resolved": self.resolved,
                "resolvedAt": self.resolved_at
            },
            "createdAt": self.created_at,
            "expiresAt": self.expires_at
        }


# ===========================================
# Trade Stability Score
# ===========================================

@dataclass 
class TradeStabilityScore:
    """
    Trade Stability Score - shows how consistently the trade is developing
    """
    position_id: str = ""
    
    # Core stability metrics (0-100)
    stability_score: float = 50.0
    
    # Component scores
    price_stability: float = 50.0      # How steady price movement is
    momentum_stability: float = 50.0   # Consistency of momentum
    volume_stability: float = 50.0     # Volume consistency
    structure_stability: float = 50.0  # Support/resistance holding
    
    # Volatility analysis
    volatility_normalized: float = 1.0
    volatility_trend: str = "STABLE"  # INCREASING, STABLE, DECREASING
    
    # Event analysis
    positive_events: int = 0
    negative_events: int = 0
    net_event_impact: float = 0.0
    
    # Health trajectory
    health_changes: List[float] = field(default_factory=list)
    avg_health_change: float = 0.0
    health_volatility: float = 0.0
    
    # Prediction
    predicted_health_1h: float = 50.0
    predicted_health_4h: float = 50.0
    confidence: float = 0.5
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "stabilityScore": round(self.stability_score, 1),
            "components": {
                "priceStability": round(self.price_stability, 1),
                "momentumStability": round(self.momentum_stability, 1),
                "volumeStability": round(self.volume_stability, 1),
                "structureStability": round(self.structure_stability, 1)
            },
            "volatility": {
                "normalized": round(self.volatility_normalized, 3),
                "trend": self.volatility_trend
            },
            "events": {
                "positive": self.positive_events,
                "negative": self.negative_events,
                "netImpact": round(self.net_event_impact, 1)
            },
            "trajectory": {
                "avgHealthChange": round(self.avg_health_change, 2),
                "healthVolatility": round(self.health_volatility, 2)
            },
            "prediction": {
                "health1h": round(self.predicted_health_1h, 1),
                "health4h": round(self.predicted_health_4h, 1),
                "confidence": round(self.confidence, 2)
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Advanced Health Score
# ===========================================

@dataclass
class AdvancedTradeHealthScore:
    """
    Enhanced trade health score with advanced metrics
    """
    position_id: str = ""
    
    # Core health
    current_health: float = 100.0
    previous_health: float = 100.0
    health_change: float = 0.0
    status: HealthStatus = HealthStatus.GOOD
    
    # Component health scores (0-100)
    price_action_health: float = 0.0
    structure_health: float = 0.0
    momentum_health: float = 0.0
    time_health: float = 0.0
    pnl_health: float = 0.0
    volatility_health: float = 0.0
    
    # Health trends
    health_trend: str = "STABLE"  # IMPROVING, STABLE, DETERIORATING
    trend_strength: float = 0.0   # How strong is the trend
    bars_in_status: int = 0
    
    # Decay tracking
    total_decay: float = 0.0
    decay_rate: float = 0.0
    decay_sources: List[str] = field(default_factory=list)
    
    # Event tracking
    recent_events: List[HealthEvent] = field(default_factory=list)
    event_balance: float = 0.0  # Net positive - negative events
    
    # Stability
    stability: Optional[TradeStabilityScore] = None
    
    # Alerts
    active_alerts: List[HealthAlert] = field(default_factory=list)
    
    # Actions
    recommended_action: str = "HOLD"
    action_urgency: str = "LOW"
    action_reasons: List[str] = field(default_factory=list)
    
    # Recovery blocking
    recovery_blocked: bool = False
    recovery_block_reason: str = ""
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "health": {
                "current": round(self.current_health, 1),
                "previous": round(self.previous_health, 1),
                "change": round(self.health_change, 1),
                "status": self.status.value
            },
            "components": {
                "priceAction": round(self.price_action_health, 1),
                "structure": round(self.structure_health, 1),
                "momentum": round(self.momentum_health, 1),
                "time": round(self.time_health, 1),
                "pnl": round(self.pnl_health, 1),
                "volatility": round(self.volatility_health, 1)
            },
            "trend": {
                "direction": self.health_trend,
                "strength": round(self.trend_strength, 2),
                "barsInStatus": self.bars_in_status
            },
            "decay": {
                "total": round(self.total_decay, 1),
                "rate": round(self.decay_rate, 3),
                "sources": self.decay_sources
            },
            "events": {
                "recent": [e.to_dict() for e in self.recent_events[-5:]],
                "balance": round(self.event_balance, 1)
            },
            "stability": self.stability.to_dict() if self.stability else None,
            "alerts": [a.to_dict() for a in self.active_alerts],
            "action": {
                "recommended": self.recommended_action,
                "urgency": self.action_urgency,
                "reasons": self.action_reasons
            },
            "recovery": {
                "blocked": self.recovery_blocked,
                "reason": self.recovery_block_reason
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Health History Entry
# ===========================================

@dataclass
class HealthHistoryEntry:
    """Single entry in health history"""
    position_id: str = ""
    timestamp: int = 0
    health: float = 0.0
    status: HealthStatus = HealthStatus.GOOD
    price: float = 0.0
    pnl_pct: float = 0.0
    event_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "timestamp": self.timestamp,
            "health": round(self.health, 1),
            "status": self.status.value,
            "price": self.price,
            "pnlPct": round(self.pnl_pct, 3),
            "eventCount": self.event_count
        }
