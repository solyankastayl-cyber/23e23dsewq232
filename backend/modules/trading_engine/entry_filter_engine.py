"""
Trading Engine Integration — Feature Vector → Trading Decisions

Uses indicator intelligence (feature_vector) for:
1. Entry Filters - allow/block long/short based on indicator alignment
2. Position Sizing - scale size by indicator confidence
3. Stop Logic - ATR/Donchian/Keltner based stops
4. Scenario Validation - adjust probabilities based on indicator conflicts

This module transforms the research engine into a decision engine.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum
import numpy as np

# Import feature vector types
import sys
sys.path.insert(0, '/app/backend')
from modules.research_analytics.market_feature_vector import (
    MarketFeatureVector,
    get_feature_vector_service,
)


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class EntryDecision(BaseModel):
    """Entry filter decision."""
    allow_long: bool = False
    allow_short: bool = False
    preferred_direction: TradeDirection = TradeDirection.NEUTRAL
    confidence: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class PositionSizeDecision(BaseModel):
    """Position sizing decision."""
    base_multiplier: float = 1.0
    indicator_multiplier: float = 1.0
    final_multiplier: float = 1.0
    max_risk_pct: float = 0.02  # 2% default
    reasoning: str = ""


class StopLossDecision(BaseModel):
    """Stop loss calculation."""
    stop_price: float
    stop_distance: float
    stop_pct: float
    method: str  # "atr", "donchian", "keltner", "support"
    atr_multiplier: float = 1.5
    reasoning: str = ""


class TakeProfitDecision(BaseModel):
    """Take profit levels."""
    targets: List[Dict[str, float]] = Field(default_factory=list)  # [{price, pct, probability}]
    method: str  # "rr_ratio", "resistance", "fibonacci"
    reasoning: str = ""


class TradingDecision(BaseModel):
    """Complete trading decision based on indicator intelligence."""
    symbol: str
    timeframe: str
    timestamp: str
    
    # Entry
    entry: EntryDecision
    
    # Sizing
    position_size: PositionSizeDecision
    
    # Risk
    stop_loss: Optional[StopLossDecision] = None
    take_profit: Optional[TakeProfitDecision] = None
    
    # Underlying data
    feature_vector: Dict[str, Any] = Field(default_factory=dict)
    
    # Explanation
    explanation: str = ""
    indicator_summary: List[Dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

class TradingConfig(BaseModel):
    """Trading engine configuration."""
    
    # Entry thresholds
    long_trend_threshold: float = 0.25
    long_net_threshold: float = 0.15
    short_trend_threshold: float = -0.25
    short_net_threshold: float = -0.15
    
    # Breakout requirement
    require_breakout_for_trend: bool = False
    breakout_threshold: float = 0.3
    
    # Position sizing
    min_confidence_for_trade: float = 0.2
    position_size_scale: Dict[str, float] = Field(default_factory=lambda: {
        "very_low": 0.5,    # confidence < 0.2
        "low": 0.8,         # confidence < 0.4
        "medium": 1.0,      # confidence < 0.6
        "high": 1.2,        # confidence < 0.8
        "very_high": 1.5,   # confidence >= 0.8
    })
    
    # Stop loss
    default_atr_multiplier: float = 1.5
    max_stop_pct: float = 0.05  # 5% max
    
    # Take profit
    default_rr_ratio: float = 2.0  # Risk:Reward


DEFAULT_CONFIG = TradingConfig()


# ═══════════════════════════════════════════════════════════════
# Entry Filter Engine
# ═══════════════════════════════════════════════════════════════

class EntryFilterEngine:
    """
    Determines if a trade is allowed based on indicator intelligence.
    
    Logic:
    - LONG allowed if trend_score > threshold AND net_score > threshold
    - SHORT allowed if trend_score < -threshold AND net_score < -threshold
    - Breakout can override weak momentum
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or DEFAULT_CONFIG
    
    def evaluate(self, feature_vector: MarketFeatureVector) -> EntryDecision:
        """Evaluate entry conditions based on feature vector."""
        
        trend = feature_vector.trend_score
        momentum = feature_vector.momentum_score
        breakout = feature_vector.breakout_score
        net = feature_vector.net_score
        confidence = feature_vector.confidence
        agreement = feature_vector.agreement_ratio
        
        reasons = []
        blockers = []
        
        # ═══════════════════════════════════════════════════════
        # LONG CONDITIONS
        # ═══════════════════════════════════════════════════════
        
        long_trend_ok = trend >= self.config.long_trend_threshold
        long_net_ok = net >= self.config.long_net_threshold
        long_breakout = breakout >= self.config.breakout_threshold
        
        allow_long = False
        
        if long_trend_ok and long_net_ok:
            allow_long = True
            reasons.append(f"Trend aligned bullish (trend={trend:.2f}, net={net:.2f})")
            
            if long_breakout:
                reasons.append(f"Breakout confirmation (breakout={breakout:.2f})")
                
        elif long_breakout and net > 0:
            # Breakout can override weak trend
            allow_long = True
            reasons.append(f"Breakout signal overrides weak trend (breakout={breakout:.2f})")
            
        else:
            if not long_trend_ok:
                blockers.append(f"Trend too weak for LONG (trend={trend:.2f} < {self.config.long_trend_threshold})")
            if not long_net_ok:
                blockers.append(f"Net score too weak for LONG (net={net:.2f} < {self.config.long_net_threshold})")
        
        # Momentum divergence check
        if allow_long and momentum < -0.3:
            allow_long = False
            blockers.append(f"Momentum divergence blocks LONG (momentum={momentum:.2f})")
        
        # ═══════════════════════════════════════════════════════
        # SHORT CONDITIONS
        # ═══════════════════════════════════════════════════════
        
        short_trend_ok = trend <= self.config.short_trend_threshold
        short_net_ok = net <= self.config.short_net_threshold
        short_breakout = breakout <= -self.config.breakout_threshold
        
        allow_short = False
        
        if short_trend_ok and short_net_ok:
            allow_short = True
            reasons.append(f"Trend aligned bearish (trend={trend:.2f}, net={net:.2f})")
            
            if short_breakout:
                reasons.append(f"Breakdown confirmation (breakout={breakout:.2f})")
                
        elif short_breakout and net < 0:
            allow_short = True
            reasons.append(f"Breakdown signal overrides weak trend (breakout={breakout:.2f})")
            
        else:
            if not short_trend_ok:
                blockers.append(f"Trend too weak for SHORT (trend={trend:.2f} > {self.config.short_trend_threshold})")
            if not short_net_ok:
                blockers.append(f"Net score too weak for SHORT (net={net:.2f} > {self.config.short_net_threshold})")
        
        # Momentum divergence check
        if allow_short and momentum > 0.3:
            allow_short = False
            blockers.append(f"Momentum divergence blocks SHORT (momentum={momentum:.2f})")
        
        # ═══════════════════════════════════════════════════════
        # CONFIDENCE CHECK
        # ═══════════════════════════════════════════════════════
        
        if confidence < self.config.min_confidence_for_trade:
            if allow_long:
                blockers.append(f"Low confidence blocks LONG (confidence={confidence:.2f})")
            if allow_short:
                blockers.append(f"Low confidence blocks SHORT (confidence={confidence:.2f})")
            allow_long = False
            allow_short = False
        
        # Agreement ratio check
        if agreement < 0.5:
            reasons.append(f"Warning: low indicator agreement ({agreement:.0%})")
        
        # ═══════════════════════════════════════════════════════
        # DETERMINE PREFERRED DIRECTION
        # ═══════════════════════════════════════════════════════
        
        if allow_long and not allow_short:
            preferred = TradeDirection.LONG
        elif allow_short and not allow_long:
            preferred = TradeDirection.SHORT
        elif allow_long and allow_short:
            # Both allowed - use net score
            preferred = TradeDirection.LONG if net > 0 else TradeDirection.SHORT
        else:
            preferred = TradeDirection.NEUTRAL
        
        # Calculate confidence for the decision
        decision_confidence = abs(net) * agreement * confidence
        
        return EntryDecision(
            allow_long=allow_long,
            allow_short=allow_short,
            preferred_direction=preferred,
            confidence=round(decision_confidence, 3),
            reasons=reasons,
            blockers=blockers,
        )


# ═══════════════════════════════════════════════════════════════
# Position Size Engine
# ═══════════════════════════════════════════════════════════════

class PositionSizeEngine:
    """
    Calculates position size multiplier based on indicator confidence.
    
    Higher confidence → larger position
    Lower confidence → smaller position
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or DEFAULT_CONFIG
    
    def calculate(self, feature_vector: MarketFeatureVector) -> PositionSizeDecision:
        """Calculate position size multiplier."""
        
        # Calculate indicator confidence
        indicator_confidence = self._calculate_indicator_confidence(feature_vector)
        
        # Determine multiplier tier
        scale = self.config.position_size_scale
        
        if indicator_confidence < 0.2:
            multiplier = scale["very_low"]
            tier = "very_low"
        elif indicator_confidence < 0.4:
            multiplier = scale["low"]
            tier = "low"
        elif indicator_confidence < 0.6:
            multiplier = scale["medium"]
            tier = "medium"
        elif indicator_confidence < 0.8:
            multiplier = scale["high"]
            tier = "high"
        else:
            multiplier = scale["very_high"]
            tier = "very_high"
        
        # Agreement ratio adjustment
        agreement_adj = 0.8 + 0.4 * feature_vector.agreement_ratio
        
        final_multiplier = multiplier * agreement_adj
        
        return PositionSizeDecision(
            base_multiplier=1.0,
            indicator_multiplier=round(multiplier, 2),
            final_multiplier=round(final_multiplier, 2),
            max_risk_pct=self.config.max_stop_pct,
            reasoning=f"Confidence tier: {tier} ({indicator_confidence:.2f}), agreement adjustment: {agreement_adj:.2f}"
        )
    
    def _calculate_indicator_confidence(self, fv: MarketFeatureVector) -> float:
        """
        Calculate overall indicator confidence.
        
        Formula:
        confidence = 0.5 * |trend_score| + 0.3 * |momentum_score| + 0.2 * |breakout_score|
        """
        trend_contrib = 0.5 * abs(fv.trend_score)
        momentum_contrib = 0.3 * abs(fv.momentum_score)
        breakout_contrib = 0.2 * abs(fv.breakout_score)
        
        return min(1.0, trend_contrib + momentum_contrib + breakout_contrib)


# ═══════════════════════════════════════════════════════════════
# Stop Loss Engine
# ═══════════════════════════════════════════════════════════════

class StopLossEngine:
    """
    Calculates stop loss based on ATR, Donchian, or support levels.
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or DEFAULT_CONFIG
    
    def calculate(
        self,
        candles: List[Dict[str, Any]],
        direction: TradeDirection,
        entry_price: float,
        method: str = "atr"
    ) -> StopLossDecision:
        """Calculate stop loss level."""
        
        if direction == TradeDirection.NEUTRAL:
            return StopLossDecision(
                stop_price=entry_price,
                stop_distance=0,
                stop_pct=0,
                method="none",
                reasoning="No stop for neutral direction"
            )
        
        if method == "atr":
            return self._atr_stop(candles, direction, entry_price)
        elif method == "donchian":
            return self._donchian_stop(candles, direction, entry_price)
        elif method == "keltner":
            return self._keltner_stop(candles, direction, entry_price)
        else:
            return self._atr_stop(candles, direction, entry_price)
    
    def _atr_stop(
        self,
        candles: List[Dict[str, Any]],
        direction: TradeDirection,
        entry_price: float
    ) -> StopLossDecision:
        """ATR-based stop loss."""
        atr = self._calculate_atr(candles, 14)
        multiplier = self.config.default_atr_multiplier
        
        distance = atr * multiplier
        
        if direction == TradeDirection.LONG:
            stop_price = entry_price - distance
        else:
            stop_price = entry_price + distance
        
        stop_pct = distance / entry_price
        
        # Cap at max stop
        if stop_pct > self.config.max_stop_pct:
            stop_pct = self.config.max_stop_pct
            distance = entry_price * stop_pct
            if direction == TradeDirection.LONG:
                stop_price = entry_price - distance
            else:
                stop_price = entry_price + distance
        
        return StopLossDecision(
            stop_price=round(stop_price, 2),
            stop_distance=round(distance, 2),
            stop_pct=round(stop_pct, 4),
            method="atr",
            atr_multiplier=multiplier,
            reasoning=f"ATR({14})={atr:.2f} × {multiplier} = {distance:.2f}"
        )
    
    def _donchian_stop(
        self,
        candles: List[Dict[str, Any]],
        direction: TradeDirection,
        entry_price: float
    ) -> StopLossDecision:
        """Donchian channel stop."""
        period = 20
        lows = [c["low"] for c in candles[-period:]]
        highs = [c["high"] for c in candles[-period:]]
        
        if direction == TradeDirection.LONG:
            stop_price = min(lows)
        else:
            stop_price = max(highs)
        
        distance = abs(entry_price - stop_price)
        stop_pct = distance / entry_price
        
        return StopLossDecision(
            stop_price=round(stop_price, 2),
            stop_distance=round(distance, 2),
            stop_pct=round(stop_pct, 4),
            method="donchian",
            reasoning=f"Donchian({period}) {'low' if direction == TradeDirection.LONG else 'high'}"
        )
    
    def _keltner_stop(
        self,
        candles: List[Dict[str, Any]],
        direction: TradeDirection,
        entry_price: float
    ) -> StopLossDecision:
        """Keltner channel stop."""
        ema_period = 20
        atr_period = 10
        multiplier = 2.0
        
        closes = [c["close"] for c in candles]
        ema = self._ema(closes, ema_period)[-1]
        atr = self._calculate_atr(candles, atr_period)
        
        if direction == TradeDirection.LONG:
            stop_price = ema - multiplier * atr
        else:
            stop_price = ema + multiplier * atr
        
        distance = abs(entry_price - stop_price)
        stop_pct = distance / entry_price
        
        return StopLossDecision(
            stop_price=round(stop_price, 2),
            stop_distance=round(distance, 2),
            stop_pct=round(stop_pct, 4),
            method="keltner",
            reasoning=f"Keltner EMA({ema_period})={ema:.2f} ± {multiplier}×ATR({atr_period})"
        )
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < 2:
            return candles[0]["high"] - candles[0]["low"] if candles else 0
        
        tr_values = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            tr_values.append(tr)
        
        return np.mean(tr_values) if tr_values else 0
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Calculate EMA."""
        if not data:
            return []
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(data[i] * multiplier + ema[-1] * (1 - multiplier))
        return ema


# ═══════════════════════════════════════════════════════════════
# Take Profit Engine
# ═══════════════════════════════════════════════════════════════

class TakeProfitEngine:
    """
    Calculates take profit targets based on R:R ratio or resistance levels.
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or DEFAULT_CONFIG
    
    def calculate(
        self,
        entry_price: float,
        stop_loss: StopLossDecision,
        direction: TradeDirection,
        method: str = "rr_ratio"
    ) -> TakeProfitDecision:
        """Calculate take profit targets."""
        
        if direction == TradeDirection.NEUTRAL:
            return TakeProfitDecision(
                targets=[],
                method="none",
                reasoning="No targets for neutral direction"
            )
        
        risk = stop_loss.stop_distance
        rr = self.config.default_rr_ratio
        
        targets = []
        
        # TP1: 1:1 R:R (50% of position)
        tp1_distance = risk * 1.0
        if direction == TradeDirection.LONG:
            tp1_price = entry_price + tp1_distance
        else:
            tp1_price = entry_price - tp1_distance
        
        targets.append({
            "level": 1,
            "price": round(tp1_price, 2),
            "pct": round(tp1_distance / entry_price, 4),
            "rr_ratio": 1.0,
            "position_pct": 0.5,
        })
        
        # TP2: 2:1 R:R (30% of position)
        tp2_distance = risk * 2.0
        if direction == TradeDirection.LONG:
            tp2_price = entry_price + tp2_distance
        else:
            tp2_price = entry_price - tp2_distance
        
        targets.append({
            "level": 2,
            "price": round(tp2_price, 2),
            "pct": round(tp2_distance / entry_price, 4),
            "rr_ratio": 2.0,
            "position_pct": 0.3,
        })
        
        # TP3: 3:1 R:R (20% of position)
        tp3_distance = risk * 3.0
        if direction == TradeDirection.LONG:
            tp3_price = entry_price + tp3_distance
        else:
            tp3_price = entry_price - tp3_distance
        
        targets.append({
            "level": 3,
            "price": round(tp3_price, 2),
            "pct": round(tp3_distance / entry_price, 4),
            "rr_ratio": 3.0,
            "position_pct": 0.2,
        })
        
        return TakeProfitDecision(
            targets=targets,
            method="rr_ratio",
            reasoning=f"3-tier TP based on {rr}:1 R:R ratio with risk={risk:.2f}"
        )


# ═══════════════════════════════════════════════════════════════
# Scenario Validation Engine
# ═══════════════════════════════════════════════════════════════

class ScenarioValidationEngine:
    """
    Validates and adjusts scenario probabilities based on indicator conflicts.
    """
    
    def validate_scenario(
        self,
        scenario_type: str,  # "bullish", "bearish"
        probability: float,
        feature_vector: MarketFeatureVector
    ) -> tuple:  # (adjusted_prob, reasoning)
        """
        Adjust scenario probability based on indicator conflicts.
        
        Example:
        - Pattern says bullish but momentum is strongly bearish
        - → reduce bullish probability
        """
        
        momentum = feature_vector.momentum_score
        trend = feature_vector.trend_score
        
        adjustment = 0.0
        reasons = []
        
        if scenario_type == "bullish":
            # Check for conflicts
            if momentum < -0.3:
                adjustment -= 0.15
                reasons.append(f"Momentum divergence (momentum={momentum:.2f})")
            
            if trend < 0:
                adjustment -= 0.10
                reasons.append(f"Trend not aligned (trend={trend:.2f})")
            
            # Positive reinforcement
            if momentum > 0.3 and trend > 0.3:
                adjustment += 0.10
                reasons.append("Strong bullish confirmation")
                
        elif scenario_type == "bearish":
            if momentum > 0.3:
                adjustment -= 0.15
                reasons.append(f"Momentum divergence (momentum={momentum:.2f})")
            
            if trend > 0:
                adjustment -= 0.10
                reasons.append(f"Trend not aligned (trend={trend:.2f})")
            
            if momentum < -0.3 and trend < -0.3:
                adjustment += 0.10
                reasons.append("Strong bearish confirmation")
        
        adjusted_prob = max(0.05, min(0.80, probability + adjustment))
        reasoning = "; ".join(reasons) if reasons else "No conflicts detected"
        
        return round(adjusted_prob, 3), reasoning


# ═══════════════════════════════════════════════════════════════
# Main Trading Engine Service
# ═══════════════════════════════════════════════════════════════

class TradingEngineService:
    """
    Main service that integrates all trading components.
    
    Transforms feature_vector into complete trading decision.
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.feature_service = get_feature_vector_service()
        self.entry_filter = EntryFilterEngine(self.config)
        self.position_sizer = PositionSizeEngine(self.config)
        self.stop_engine = StopLossEngine(self.config)
        self.tp_engine = TakeProfitEngine(self.config)
        self.scenario_validator = ScenarioValidationEngine()
    
    def generate_decision(
        self,
        candles: List[Dict[str, Any]],
        symbol: str = "UNKNOWN",
        timeframe: str = "1H"
    ) -> TradingDecision:
        """
        Generate complete trading decision from candle data.
        """
        
        # Build feature vector
        feature_vector = self.feature_service.build_feature_vector(candles, symbol, timeframe)
        
        # Entry decision
        entry = self.entry_filter.evaluate(feature_vector)
        
        # Position sizing
        position_size = self.position_sizer.calculate(feature_vector)
        
        # Get current price
        entry_price = candles[-1]["close"] if candles else 0
        
        # Stop loss (if trade allowed)
        stop_loss = None
        take_profit = None
        
        if entry.allow_long or entry.allow_short:
            stop_loss = self.stop_engine.calculate(
                candles, 
                entry.preferred_direction, 
                entry_price
            )
            take_profit = self.tp_engine.calculate(
                entry_price,
                stop_loss,
                entry.preferred_direction
            )
        
        # Build explanation
        explanation = self._build_explanation(entry, feature_vector)
        
        # Build indicator summary
        indicator_summary = self._build_indicator_summary(feature_vector)
        
        return TradingDecision(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc).isoformat(),
            entry=entry,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "volatility_score": feature_vector.volatility_score,
                "breakout_score": feature_vector.breakout_score,
                "net_score": feature_vector.net_score,
                "confidence": feature_vector.confidence,
                "agreement_ratio": feature_vector.agreement_ratio,
            },
            explanation=explanation,
            indicator_summary=indicator_summary,
        )
    
    def _build_explanation(
        self,
        entry: EntryDecision,
        fv: MarketFeatureVector
    ) -> str:
        """Build human-readable explanation."""
        
        if entry.preferred_direction == TradeDirection.LONG:
            direction_str = "LONG"
        elif entry.preferred_direction == TradeDirection.SHORT:
            direction_str = "SHORT"
        else:
            direction_str = "NEUTRAL"
        
        if entry.allow_long or entry.allow_short:
            status = f"{direction_str} ALLOWED"
        else:
            status = "NO TRADE"
        
        summary = f"[{status}] "
        summary += f"Trend={fv.trend_score:+.2f}, Momentum={fv.momentum_score:+.2f}, "
        summary += f"Breakout={fv.breakout_score:+.2f}, Net={fv.net_score:+.2f}"
        
        if entry.blockers:
            summary += f" | Blocked: {entry.blockers[0]}"
        
        return summary
    
    def _build_indicator_summary(
        self,
        fv: MarketFeatureVector
    ) -> List[Dict[str, Any]]:
        """Build summary of indicator contributions."""
        
        summary = []
        
        # Top 5 indicator signals
        sorted_signals = sorted(
            fv.indicator_signals,
            key=lambda s: abs(s.score) * s.strength,
            reverse=True
        )
        
        for signal in sorted_signals[:5]:
            summary.append({
                "indicator": signal.indicator.upper(),
                "direction": signal.direction,
                "score": round(signal.score, 2),
                "strength": round(signal.strength, 2),
                "reason": signal.reason,
            })
        
        return summary


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_trading_engine: Optional[TradingEngineService] = None

def get_trading_engine() -> TradingEngineService:
    """Get singleton instance."""
    global _trading_engine
    if _trading_engine is None:
        _trading_engine = TradingEngineService()
    return _trading_engine
