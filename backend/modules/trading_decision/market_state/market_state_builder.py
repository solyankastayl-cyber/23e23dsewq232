"""
PHASE 14.3 — Market State Builder
==================================
Builds multi-dimensional market state from TA and Exchange inputs.

Architecture:
    TA Hypothesis ────┐
                       ├── Market State Matrix ── Trading Decision Layer
    Exchange Context ──┘

Input sources:
- TA Hypothesis: direction, regime, setup_quality, trend_strength, conviction
- Exchange Context: bias, dominant_signal, confidence, conflict_ratio
- Volatility: from existing context/regime data
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.market_state.market_state_types import (
    MarketStateMatrix,
    TrendState,
    VolatilityState,
    ExchangeState,
    DerivativesState,
    BreadthState,
    RiskState,
    CombinedState,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    VolatilityInputSnapshot,
)
from modules.trading_decision.market_state.market_state_rules import (
    TREND_RULES,
    VOLATILITY_RULES,
    EXCHANGE_RULES,
    DERIVATIVES_RULES,
    RISK_RULES,
    CONFIDENCE_WEIGHTS,
    COMBINED_STATE_RULES,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class MarketStateBuilder:
    """
    Builds MarketStateMatrix from TA Hypothesis and Exchange Context.
    
    This is the bridge between:
    - TA Module (technical analysis)
    - Exchange Intelligence Module (derivatives/flow data)
    
    Output goes to Trading Decision Layer.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load hypothesis builder and exchange aggregator
        self._ta_builder = None
        self._exchange_aggregator = None
    
    @property
    def ta_builder(self):
        """Lazy load TA Hypothesis Builder."""
        if self._ta_builder is None:
            from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_hypothesis_builder
            self._ta_builder = get_hypothesis_builder()
        return self._ta_builder
    
    @property
    def exchange_aggregator(self):
        """Lazy load Exchange Context Aggregator."""
        if self._exchange_aggregator is None:
            from modules.exchange_intelligence.exchange_context_aggregator import ExchangeContextAggregator
            self._exchange_aggregator = ExchangeContextAggregator()
        return self._exchange_aggregator
    
    def build(self, symbol: str) -> MarketStateMatrix:
        """
        Build full market state matrix for symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            MarketStateMatrix with all dimensions
        """
        now = datetime.now(timezone.utc)
        
        # Get inputs from both modules
        ta_input = self._get_ta_input(symbol)
        exchange_input = self._get_exchange_input(symbol)
        volatility_input = self._get_volatility_input(symbol)
        
        # Compute individual states
        trend_state = self._compute_trend_state(ta_input)
        volatility_state = self._compute_volatility_state(volatility_input)
        exchange_state = self._compute_exchange_state(exchange_input)
        derivatives_state = self._compute_derivatives_state(exchange_input)
        breadth_state = self._compute_breadth_state(symbol)
        risk_state = self._compute_risk_state(ta_input, exchange_input)
        
        # Compute combined state
        combined_state = self._compute_combined_state(
            trend_state, volatility_state, exchange_state, derivatives_state
        )
        
        # Compute confidence
        confidence = self._compute_confidence(ta_input, exchange_input, volatility_input)
        
        # Build drivers dict
        drivers = self._build_drivers(ta_input, exchange_input, volatility_input)
        
        # Build raw scores for debugging
        raw_scores = {
            "ta_conviction": ta_input.conviction,
            "ta_trend_strength": ta_input.trend_strength,
            "exchange_confidence": exchange_input.confidence,
            "exchange_conflict": exchange_input.conflict_ratio,
            "crowding_risk": exchange_input.crowding_risk,
            "squeeze_prob": exchange_input.squeeze_probability,
            "volatility_percentile": volatility_input.volatility_percentile,
        }
        
        return MarketStateMatrix(
            symbol=symbol,
            timestamp=now,
            trend_state=trend_state,
            volatility_state=volatility_state,
            exchange_state=exchange_state,
            derivatives_state=derivatives_state,
            breadth_state=breadth_state,
            risk_state=risk_state,
            combined_state=combined_state,
            confidence=confidence,
            drivers=drivers,
            raw_scores=raw_scores,
        )
    
    def build_batch(self, symbols: List[str]) -> List[MarketStateMatrix]:
        """Build market state for multiple symbols."""
        return [self.build(symbol) for symbol in symbols]
    
    # ═══════════════════════════════════════════════════════════════
    # INPUT GETTERS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_ta_input(self, symbol: str) -> TAInputSnapshot:
        """Get TA Hypothesis as input snapshot."""
        try:
            hypothesis = self.ta_builder.build(symbol)
            return TAInputSnapshot(
                direction=hypothesis.direction.value,
                regime=hypothesis.regime.value,
                setup_quality=hypothesis.setup_quality,
                trend_strength=hypothesis.trend_strength,
                conviction=hypothesis.conviction,
                entry_quality=hypothesis.entry_quality,
                regime_fit=hypothesis.regime_fit,
            )
        except Exception as e:
            # Return neutral defaults on error
            return TAInputSnapshot(
                direction="NEUTRAL",
                regime="UNKNOWN",
                setup_quality=0.0,
                trend_strength=0.0,
                conviction=0.0,
                entry_quality=0.5,
                regime_fit=0.5,
            )
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        """Get Exchange Context as input snapshot."""
        try:
            context = self.exchange_aggregator.compute(symbol)
            
            # Determine dominant signal
            driver_scores = {
                "funding": abs(context.funding_signal.funding_rate) if context.funding_signal else 0,
                "flow": abs(context.flow_pressure),
                "derivatives": abs(context.derivatives_pressure),
                "liquidation": context.cascade_probability,
                "volume": context.volume_signal.anomaly_score if context.volume_signal else 0,
            }
            dominant = max(driver_scores, key=driver_scores.get)
            
            # Compute conflict ratio
            signals = []
            if context.funding_signal:
                signals.append(1 if context.funding_signal.funding_rate > 0 else -1)
            signals.append(1 if context.flow_pressure > 0 else -1)
            signals.append(1 if context.derivatives_pressure > 0 else -1)
            
            # Conflict = variance of signals
            if signals:
                avg = sum(signals) / len(signals)
                conflict = sum((s - avg) ** 2 for s in signals) / len(signals)
            else:
                conflict = 0
            
            return ExchangeInputSnapshot(
                bias=context.exchange_bias.value,
                dominant_signal=dominant,
                confidence=context.confidence,
                conflict_ratio=min(conflict, 1.0),
                crowding_risk=context.crowding_risk,
                squeeze_probability=context.squeeze_probability,
                cascade_probability=context.cascade_probability,
                derivatives_pressure=context.derivatives_pressure,
                flow_pressure=context.flow_pressure,
            )
        except Exception as e:
            return ExchangeInputSnapshot(
                bias="NEUTRAL",
                dominant_signal="none",
                confidence=0.5,
                conflict_ratio=0.5,
                crowding_risk=0.0,
                squeeze_probability=0.0,
                cascade_probability=0.0,
                derivatives_pressure=0.0,
                flow_pressure=0.0,
            )
    
    def _get_volatility_input(self, symbol: str) -> VolatilityInputSnapshot:
        """Get volatility context from candles."""
        try:
            candles = list(self.db.candles.find(
                {"symbol": symbol, "timeframe": "1d"},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(100))
            
            if len(candles) < 20:
                return self._default_volatility()
            
            candles = list(reversed(candles))
            
            # Compute ATR
            atrs = []
            for i in range(1, len(candles)):
                high = candles[i]["high"]
                low = candles[i]["low"]
                prev_close = candles[i-1]["close"]
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                atrs.append(tr)
            
            atr_14 = sum(atrs[-14:]) / 14 if len(atrs) >= 14 else sum(atrs) / len(atrs)
            current_price = candles[-1]["close"]
            atr_normalized = atr_14 / current_price if current_price else 0
            
            # Compute percentile of current ATR vs historical
            sorted_atrs = sorted(atrs)
            percentile = sorted_atrs.index(min(sorted_atrs, key=lambda x: abs(x - atrs[-1]))) / len(sorted_atrs)
            
            # Recent range
            recent_high = max(c["high"] for c in candles[-14:])
            recent_low = min(c["low"] for c in candles[-14:])
            recent_range = (recent_high - recent_low) / current_price if current_price else 0
            
            # Determine volatility regime
            if percentile < VOLATILITY_RULES["low_percentile"]:
                regime = "LOW"
            elif percentile > VOLATILITY_RULES["high_percentile"]:
                regime = "HIGH"
            elif len(atrs) > 5 and atrs[-1] > atrs[-5] * (1 + VOLATILITY_RULES["expanding_change"]):
                regime = "EXPANDING"
            else:
                regime = "NORMAL"
            
            return VolatilityInputSnapshot(
                atr_normalized=atr_normalized,
                volatility_percentile=percentile,
                volatility_regime=regime,
                recent_range=recent_range,
            )
        except Exception:
            return self._default_volatility()
    
    def _default_volatility(self) -> VolatilityInputSnapshot:
        """Default volatility snapshot."""
        return VolatilityInputSnapshot(
            atr_normalized=0.02,
            volatility_percentile=0.5,
            volatility_regime="NORMAL",
            recent_range=0.05,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # STATE COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_trend_state(self, ta: TAInputSnapshot) -> TrendState:
        """Compute trend state from TA input."""
        direction = ta.direction
        strength = ta.trend_strength
        
        if direction == "LONG" and strength >= TREND_RULES["trend_up_threshold"]:
            return TrendState.TREND_UP
        elif direction == "SHORT" and strength >= TREND_RULES["trend_down_threshold"]:
            return TrendState.TREND_DOWN
        elif strength < TREND_RULES["range_threshold"]:
            return TrendState.RANGE
        else:
            return TrendState.MIXED
    
    def _compute_volatility_state(self, vol: VolatilityInputSnapshot) -> VolatilityState:
        """Compute volatility state."""
        regime = vol.volatility_regime
        return VolatilityState(regime)
    
    def _compute_exchange_state(self, exchange: ExchangeInputSnapshot) -> ExchangeState:
        """Compute exchange state from bias and conflict."""
        if exchange.conflict_ratio > EXCHANGE_RULES["conflict_threshold"]:
            return ExchangeState.CONFLICTED
        
        if exchange.bias == "BULLISH":
            return ExchangeState.BULLISH
        elif exchange.bias == "BEARISH":
            return ExchangeState.BEARISH
        else:
            return ExchangeState.NEUTRAL
    
    def _compute_derivatives_state(self, exchange: ExchangeInputSnapshot) -> DerivativesState:
        """Compute derivatives state."""
        # Check for squeeze
        if exchange.squeeze_probability > DERIVATIVES_RULES["squeeze_threshold"]:
            return DerivativesState.SQUEEZE
        
        # Check for crowding
        if exchange.crowding_risk > DERIVATIVES_RULES["crowded_long_threshold"]:
            if exchange.derivatives_pressure > 0:
                return DerivativesState.CROWDED_LONG
            else:
                return DerivativesState.CROWDED_SHORT
        
        return DerivativesState.BALANCED
    
    def _compute_breadth_state(self, symbol: str) -> BreadthState:
        """Compute market breadth state."""
        # Placeholder: would need cross-asset data
        # For now, return based on symbol
        if symbol == "BTC":
            return BreadthState.BTC_DOM
        elif symbol in ["ETH", "SOL"]:
            return BreadthState.ALT_DOM
        return BreadthState.UNKNOWN
    
    def _compute_risk_state(
        self, ta: TAInputSnapshot, exchange: ExchangeInputSnapshot
    ) -> RiskState:
        """Compute risk sentiment state."""
        risk_on_score = 0
        risk_off_score = 0
        
        # Trend component
        if ta.direction == "LONG" and ta.trend_strength > 0.5:
            risk_on_score += 1
        elif ta.direction == "SHORT" and ta.trend_strength > 0.5:
            risk_off_score += 1
        
        # Exchange bias
        if exchange.bias == "BULLISH":
            risk_on_score += 1
        elif exchange.bias == "BEARISH":
            risk_off_score += 1
        
        # Cascade risk
        if exchange.cascade_probability < 0.3:
            risk_on_score += 1
        elif exchange.cascade_probability > 0.6:
            risk_off_score += 1
        
        # Determine state
        if risk_on_score >= 2 and risk_off_score == 0:
            return RiskState.RISK_ON
        elif risk_off_score >= 2 and risk_on_score == 0:
            return RiskState.RISK_OFF
        return RiskState.NEUTRAL
    
    def _compute_combined_state(
        self,
        trend: TrendState,
        vol: VolatilityState,
        exchange: ExchangeState,
        derivatives: DerivativesState,
    ) -> CombinedState:
        """Compute combined state label."""
        key = (trend.value, vol.value, exchange.value, derivatives.value)
        
        # Direct match
        if key in COMBINED_STATE_RULES:
            return CombinedState(COMBINED_STATE_RULES[key])
        
        # Fallback: find closest match
        # Try with wildcards
        for rule_key, state in COMBINED_STATE_RULES.items():
            matches = sum(1 for a, b in zip(key, rule_key) if a == b)
            if matches >= 3:  # 3 out of 4 match
                return CombinedState(state)
        
        # Default fallback based on trend
        if trend == TrendState.TREND_UP:
            return CombinedState.TRENDING_LOW_VOL_BULLISH
        elif trend == TrendState.TREND_DOWN:
            return CombinedState.BEARISH_EXPANSION_RISK_OFF
        elif trend == TrendState.RANGE:
            return CombinedState.RANGE_LOW_VOL_NEUTRAL
        
        return CombinedState.UNDEFINED
    
    def _compute_confidence(
        self,
        ta: TAInputSnapshot,
        exchange: ExchangeInputSnapshot,
        vol: VolatilityInputSnapshot,
    ) -> float:
        """Compute overall confidence."""
        # Volatility clarity: clearer at extremes
        vol_clarity = abs(vol.volatility_percentile - 0.5) * 2
        
        # Regime clarity: higher when trend is clear
        regime_clarity = ta.trend_strength
        
        confidence = (
            CONFIDENCE_WEIGHTS["ta_conviction"] * ta.conviction
            + CONFIDENCE_WEIGHTS["exchange_confidence"] * exchange.confidence
            + CONFIDENCE_WEIGHTS["volatility_clarity"] * vol_clarity
            + CONFIDENCE_WEIGHTS["regime_clarity"] * regime_clarity
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _build_drivers(
        self,
        ta: TAInputSnapshot,
        exchange: ExchangeInputSnapshot,
        vol: VolatilityInputSnapshot,
    ) -> Dict[str, str]:
        """Build explainability drivers."""
        return {
            "ta_direction": ta.direction,
            "ta_regime": ta.regime,
            "exchange_bias": exchange.bias,
            "exchange_dominant_signal": exchange.dominant_signal,
            "volatility_state": vol.volatility_regime,
            "breadth_state": "computed",
            "risk_state": "computed",
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_builder: Optional[MarketStateBuilder] = None


def get_market_state_builder() -> MarketStateBuilder:
    """Get singleton builder instance."""
    global _builder
    if _builder is None:
        _builder = MarketStateBuilder()
    return _builder
