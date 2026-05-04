"""
Signal Engine — Trading Signal Generation & Management

Transforms trading decisions into formalized signals:
- Signal generation with quality filtering
- Signal storage (MongoDB)
- Signal lifecycle tracking (pending → active → tp_hit/sl_hit/expired)
- Alert generation
- Performance tracking

This is the bridge between Trading Engine and UI/Alerts.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import uuid


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class SignalStrength(str, Enum):
    WEAK = "weak"           # confidence < 0.35
    MEDIUM = "medium"       # confidence < 0.6
    STRONG = "strong"       # confidence >= 0.6


class SignalStatus(str, Enum):
    PENDING = "pending"     # Generated, not yet active
    ACTIVE = "active"       # Entry price reached
    TP1_HIT = "tp1_hit"     # First target hit
    TP2_HIT = "tp2_hit"     # Second target hit
    TP3_HIT = "tp3_hit"     # Third target hit (full TP)
    SL_HIT = "sl_hit"       # Stop loss hit
    EXPIRED = "expired"     # Signal expired without entry
    CANCELLED = "cancelled" # Manually cancelled


class TakeProfitLevel(BaseModel):
    """Take profit level configuration."""
    level: int
    price: float
    rr_ratio: float
    position_pct: float = 0.0
    hit: bool = False
    hit_at: Optional[str] = None


class TradingSignal(BaseModel):
    """
    Complete trading signal with all necessary information.
    This is what gets stored and displayed to users.
    """
    # Identity
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    
    # Context
    symbol: str
    timeframe: str
    
    # Direction
    direction: SignalDirection
    strength: SignalStrength
    
    # Prices
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: List[TakeProfitLevel] = Field(default_factory=list)
    
    # Metrics
    stop_distance_pct: float = 0.0
    risk_reward_ratio: float = 0.0
    
    # Intelligence
    confidence: float
    market_state: str
    market_state_confidence: float = 0.0
    
    feature_vector: Dict[str, float] = Field(default_factory=dict)
    indicator_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Reasoning
    entry_reasons: List[str] = Field(default_factory=list)
    signal_explanation: str = ""
    
    # Lifecycle
    status: SignalStatus = SignalStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activated_at: Optional[str] = None
    closed_at: Optional[str] = None
    expires_at: Optional[str] = None
    
    # Performance (filled when closed)
    pnl_pct: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None


class SignalAlert(BaseModel):
    """Alert generated from signal events."""
    alert_id: str = Field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:8]}")
    alert_type: str  # "new_signal", "breakout", "regime_change", "tp_hit", "sl_hit"
    symbol: str
    timeframe: str
    message: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    signal_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read: bool = False


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

class SignalConfig(BaseModel):
    """Signal generation configuration."""
    
    # Minimum confidence to generate signal
    min_confidence: float = 0.05  # Lowered to allow signals with weaker confidence
    
    # Confidence thresholds for strength
    weak_threshold: float = 0.20
    medium_threshold: float = 0.45
    
    # Signal expiry (hours)
    expiry_hours: Dict[str, int] = Field(default_factory=lambda: {
        "1m": 1,
        "5m": 2,
        "15m": 4,
        "1h": 24,
        "4h": 72,
        "1d": 168,  # 1 week
    })
    
    # Maximum active signals per symbol
    max_active_per_symbol: int = 3
    
    # Alert thresholds
    alert_confidence_threshold: float = 0.50
    alert_breakout_threshold: float = 0.70


DEFAULT_SIGNAL_CONFIG = SignalConfig()


# ═══════════════════════════════════════════════════════════════
# Signal Engine
# ═══════════════════════════════════════════════════════════════

class SignalEngine:
    """
    Generates and manages trading signals.
    
    Pipeline:
    TradingDecision → Quality Filter → TradingSignal → Storage → Alerts
    """
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or DEFAULT_SIGNAL_CONFIG
        self._pending_alerts: List[SignalAlert] = []
    
    def generate_signal(
        self,
        trading_decision: Dict[str, Any],
        market_state: Dict[str, Any],
        feature_vector: Dict[str, Any],
        symbol: str,
        timeframe: str,
        current_price: float,
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal from decision if quality passes.
        
        Returns None if:
        - Neither long nor short allowed
        - Confidence below minimum threshold
        """
        
        entry = trading_decision.get("entry", {})
        allow_long = entry.get("allow_long", False)
        allow_short = entry.get("allow_short", False)
        confidence = entry.get("confidence", 0)
        
        # Check if any trade allowed
        if not allow_long and not allow_short:
            return None
        
        # Quality filter
        if confidence < self.config.min_confidence:
            return None
        
        # Determine direction
        if allow_long and not allow_short:
            direction = SignalDirection.LONG
        elif allow_short and not allow_long:
            direction = SignalDirection.SHORT
        else:
            # Both allowed - use net_score
            net_score = feature_vector.get("net_score", 0)
            direction = SignalDirection.LONG if net_score > 0 else SignalDirection.SHORT
        
        # Determine strength
        if confidence < self.config.weak_threshold:
            strength = SignalStrength.WEAK
        elif confidence < self.config.medium_threshold:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.STRONG
        
        # Get stop/TP from trading decision
        stop_loss_data = trading_decision.get("stop_loss", {})
        take_profit_data = trading_decision.get("take_profit", {})
        position_size = trading_decision.get("position_size", {})
        
        stop_loss = stop_loss_data.get("stop_price", current_price * 0.98)
        stop_pct = stop_loss_data.get("stop_pct", 0.02)
        
        # Build take profit levels
        tp_levels = []
        for tp in take_profit_data.get("targets", []):
            tp_levels.append(TakeProfitLevel(
                level=int(tp.get("level", 1)),
                price=tp.get("price", current_price),
                rr_ratio=tp.get("rr_ratio", 1.0),
                position_pct=tp.get("position_pct", 0.33),
            ))
        
        # Calculate R:R ratio
        if tp_levels:
            avg_tp_price = sum(tp.price for tp in tp_levels) / len(tp_levels)
            potential_reward = abs(avg_tp_price - current_price)
            potential_risk = abs(current_price - stop_loss)
            rr_ratio = potential_reward / potential_risk if potential_risk > 0 else 0
        else:
            rr_ratio = 0
        
        # Calculate expiry
        expiry_hours = self.config.expiry_hours.get(timeframe.lower(), 24)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
        
        # Build explanation
        explanation = self._build_explanation(
            direction, strength, market_state, feature_vector, entry.get("reasons", [])
        )
        
        # Get indicator drivers from decision
        indicator_drivers = trading_decision.get("indicator_summary", [])
        if not indicator_drivers:
            indicator_drivers = self._extract_drivers(feature_vector)
        
        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=strength,
            entry_price=current_price,
            current_price=current_price,
            stop_loss=round(stop_loss, 2),
            take_profit=tp_levels,
            stop_distance_pct=round(stop_pct, 4),
            risk_reward_ratio=round(rr_ratio, 2),
            confidence=round(confidence, 3),
            market_state=market_state.get("state", "unknown"),
            market_state_confidence=market_state.get("confidence", 0),
            feature_vector={
                k: round(v, 3) if isinstance(v, float) else v 
                for k, v in feature_vector.items()
            },
            indicator_drivers=indicator_drivers,
            entry_reasons=entry.get("reasons", []),
            signal_explanation=explanation,
            expires_at=expires_at,
        )
        
        # Generate alert if confidence is high enough
        if confidence >= self.config.alert_confidence_threshold:
            self._generate_signal_alert(signal)
        
        return signal
    
    def _build_explanation(
        self,
        direction: SignalDirection,
        strength: SignalStrength,
        market_state: Dict[str, Any],
        feature_vector: Dict[str, Any],
        reasons: List[str],
    ) -> str:
        """Build human-readable signal explanation."""
        
        parts = []
        
        # Direction and strength
        dir_str = "LONG" if direction == SignalDirection.LONG else "SHORT"
        parts.append(f"{strength.value.upper()} {dir_str} signal")
        
        # Market state context
        state = market_state.get("state", "unknown")
        state_conf = market_state.get("confidence", 0)
        parts.append(f"Market: {state} ({state_conf:.0%} confidence)")
        
        # Key metrics
        trend = feature_vector.get("trend_score", 0)
        momentum = feature_vector.get("momentum_score", 0)
        net = feature_vector.get("net_score", 0)
        parts.append(f"Trend={trend:+.2f}, Momentum={momentum:+.2f}, Net={net:+.2f}")
        
        # Reasons
        if reasons:
            parts.append(f"Entry: {reasons[0]}")
        
        return " | ".join(parts)
    
    def _extract_drivers(self, feature_vector: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract top indicator drivers from feature vector."""
        drivers = []
        
        # Build from feature vector scores
        scores = [
            ("Trend", feature_vector.get("trend_score", 0)),
            ("Momentum", feature_vector.get("momentum_score", 0)),
            ("Breakout", feature_vector.get("breakout_score", 0)),
            ("Volatility", feature_vector.get("volatility_score", 0)),
        ]
        
        for name, score in sorted(scores, key=lambda x: abs(x[1]), reverse=True):
            drivers.append({
                "indicator": name,
                "direction": "bullish" if score > 0 else "bearish" if score < 0 else "neutral",
                "score": round(score, 2),
            })
        
        return drivers[:5]
    
    def _generate_signal_alert(self, signal: TradingSignal):
        """Generate alert for new signal."""
        
        alert = SignalAlert(
            alert_type="new_signal",
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            message=f"{signal.strength.value.upper()} {signal.direction.value.upper()} signal on {signal.symbol} {signal.timeframe}",
            priority="high" if signal.strength == SignalStrength.STRONG else "normal",
            signal_id=signal.signal_id,
            data={
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "entry": signal.entry_price,
                "stop": signal.stop_loss,
                "market_state": signal.market_state,
            }
        )
        
        self._pending_alerts.append(alert)
    
    def get_pending_alerts(self) -> List[SignalAlert]:
        """Get and clear pending alerts."""
        alerts = self._pending_alerts.copy()
        self._pending_alerts.clear()
        return alerts
    
    # ═══════════════════════════════════════════════════════════════
    # Signal Updates
    # ═══════════════════════════════════════════════════════════════
    
    def update_signal_status(
        self,
        signal: TradingSignal,
        current_price: float,
    ) -> tuple:  # (updated_signal, alerts)
        """
        Update signal status based on current price.
        
        Checks:
        - Entry price reached (pending → active)
        - Take profit levels hit
        - Stop loss hit
        - Expiry
        """
        
        alerts = []
        signal.current_price = current_price
        
        # Check expiry
        if signal.expires_at:
            expiry = datetime.fromisoformat(signal.expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry and signal.status == SignalStatus.PENDING:
                signal.status = SignalStatus.EXPIRED
                signal.closed_at = datetime.now(timezone.utc).isoformat()
                return signal, alerts
        
        # Check stop loss
        if signal.direction == SignalDirection.LONG:
            if current_price <= signal.stop_loss:
                signal.status = SignalStatus.SL_HIT
                signal.exit_price = current_price
                signal.exit_reason = "Stop loss triggered"
                signal.closed_at = datetime.now(timezone.utc).isoformat()
                signal.pnl_pct = (current_price - signal.entry_price) / signal.entry_price
                
                alerts.append(SignalAlert(
                    alert_type="sl_hit",
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    message=f"Stop loss hit on {signal.symbol} {signal.direction.value.upper()}",
                    priority="high",
                    signal_id=signal.signal_id,
                    data={"exit_price": current_price, "pnl_pct": signal.pnl_pct}
                ))
                return signal, alerts
        else:
            if current_price >= signal.stop_loss:
                signal.status = SignalStatus.SL_HIT
                signal.exit_price = current_price
                signal.exit_reason = "Stop loss triggered"
                signal.closed_at = datetime.now(timezone.utc).isoformat()
                signal.pnl_pct = (signal.entry_price - current_price) / signal.entry_price
                
                alerts.append(SignalAlert(
                    alert_type="sl_hit",
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    message=f"Stop loss hit on {signal.symbol} {signal.direction.value.upper()}",
                    priority="high",
                    signal_id=signal.signal_id,
                    data={"exit_price": current_price, "pnl_pct": signal.pnl_pct}
                ))
                return signal, alerts
        
        # Check take profit levels
        for tp in signal.take_profit:
            if tp.hit:
                continue
            
            if signal.direction == SignalDirection.LONG:
                if current_price >= tp.price:
                    tp.hit = True
                    tp.hit_at = datetime.now(timezone.utc).isoformat()
                    
                    if tp.level == 1:
                        signal.status = SignalStatus.TP1_HIT
                    elif tp.level == 2:
                        signal.status = SignalStatus.TP2_HIT
                    elif tp.level >= 3:
                        signal.status = SignalStatus.TP3_HIT
                        signal.closed_at = datetime.now(timezone.utc).isoformat()
                        signal.exit_price = current_price
                        signal.exit_reason = f"TP{tp.level} hit"
                        signal.pnl_pct = (current_price - signal.entry_price) / signal.entry_price
                    
                    alerts.append(SignalAlert(
                        alert_type="tp_hit",
                        symbol=signal.symbol,
                        timeframe=signal.timeframe,
                        message=f"TP{tp.level} hit on {signal.symbol} ({tp.rr_ratio}:1 R:R)",
                        priority="normal",
                        signal_id=signal.signal_id,
                        data={"tp_level": tp.level, "price": current_price}
                    ))
            else:
                if current_price <= tp.price:
                    tp.hit = True
                    tp.hit_at = datetime.now(timezone.utc).isoformat()
                    
                    if tp.level == 1:
                        signal.status = SignalStatus.TP1_HIT
                    elif tp.level == 2:
                        signal.status = SignalStatus.TP2_HIT
                    elif tp.level >= 3:
                        signal.status = SignalStatus.TP3_HIT
                        signal.closed_at = datetime.now(timezone.utc).isoformat()
                        signal.exit_price = current_price
                        signal.exit_reason = f"TP{tp.level} hit"
                        signal.pnl_pct = (signal.entry_price - current_price) / signal.entry_price
                    
                    alerts.append(SignalAlert(
                        alert_type="tp_hit",
                        symbol=signal.symbol,
                        timeframe=signal.timeframe,
                        message=f"TP{tp.level} hit on {signal.symbol} ({tp.rr_ratio}:1 R:R)",
                        priority="normal",
                        signal_id=signal.signal_id,
                        data={"tp_level": tp.level, "price": current_price}
                    ))
        
        # Activate pending signal if price is at entry
        if signal.status == SignalStatus.PENDING:
            # For simplicity, activate immediately (in production would check entry zone)
            signal.status = SignalStatus.ACTIVE
            signal.activated_at = datetime.now(timezone.utc).isoformat()
        
        return signal, alerts
    
    # ═══════════════════════════════════════════════════════════════
    # Regime Change Alerts
    # ═══════════════════════════════════════════════════════════════
    
    def generate_regime_change_alert(
        self,
        symbol: str,
        timeframe: str,
        old_state: str,
        new_state: str,
        confidence: float,
    ) -> Optional[SignalAlert]:
        """Generate alert when market regime changes."""
        
        if old_state == new_state:
            return None
        
        # Determine priority
        priority = "normal"
        if new_state in ["breakout_up", "breakout_down"]:
            priority = "high"
        elif new_state == "volatile":
            priority = "high"
        
        return SignalAlert(
            alert_type="regime_change",
            symbol=symbol,
            timeframe=timeframe,
            message=f"Market regime changed: {old_state} → {new_state}",
            priority=priority,
            data={
                "old_state": old_state,
                "new_state": new_state,
                "confidence": confidence,
            }
        )
    
    def generate_breakout_alert(
        self,
        symbol: str,
        timeframe: str,
        direction: str,
        strength: float,
        feature_vector: Dict[str, Any],
    ) -> Optional[SignalAlert]:
        """Generate alert for breakout detection."""
        
        if strength < self.config.alert_breakout_threshold:
            return None
        
        return SignalAlert(
            alert_type="breakout",
            symbol=symbol,
            timeframe=timeframe,
            message=f"Breakout {direction.upper()} detected on {symbol} (strength: {strength:.0%})",
            priority="urgent" if strength > 0.85 else "high",
            data={
                "direction": direction,
                "strength": strength,
                "breakout_score": feature_vector.get("breakout_score", 0),
            }
        )


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_signal_engine: Optional[SignalEngine] = None

def get_signal_engine() -> SignalEngine:
    """Get singleton instance."""
    global _signal_engine
    if _signal_engine is None:
        _signal_engine = SignalEngine()
    return _signal_engine
