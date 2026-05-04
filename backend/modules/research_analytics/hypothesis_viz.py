"""
Hypothesis Visualization API — PHASE TA-FINAL

Provides hypothesis data for visualization:
- 3-5 scenarios with DYNAMIC probabilities based on indicator signals
- Expected path
- Confidence corridor
- Invalidation level
- Target zones
- Timing window
- Feature vector integration
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, field_validator
import numpy as np

# Import feature vector services
from .market_feature_vector import (
    MarketFeatureVector,
    get_feature_vector_service,
    get_scenario_probability_engine,
)
from modules.ta_engine.utils.time_utils import normalize_timestamp


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class PricePathPoint(BaseModel):
    """Point on a price path."""
    timestamp: str
    price: float
    confidence: float = 1.0

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_ts(cls, v):
        dt = normalize_timestamp(v)
        return dt.isoformat() if dt is not None else (str(v) if v is not None else "")


class ScenarioVisualization(BaseModel):
    """Scenario for chart visualization."""
    scenario_id: str
    type: str  # base, bull, bear, extreme_bull, extreme_bear
    probability: float
    
    # Path
    expected_path: List[PricePathPoint] = Field(default_factory=list)
    upper_band: List[float] = Field(default_factory=list)
    lower_band: List[float] = Field(default_factory=list)
    
    # Targets
    target_price: float
    target_timestamp: Optional[str] = None
    
    # Invalidation
    invalidation_price: Optional[float] = None
    
    # Styling
    color: str = "#3B82F6"
    opacity: float = 0.5


class HypothesisVisualization(BaseModel):
    """Hypothesis visualization data."""
    hypothesis_id: str
    symbol: str
    timeframe: str
    
    # Direction and confidence
    direction: str  # bullish, bearish, neutral
    confidence: float
    strength: str  # weak, moderate, strong
    
    # Current state
    current_price: float
    
    # Scenarios (3-5)
    scenarios: List[ScenarioVisualization] = Field(default_factory=list)
    
    # Key levels
    entry_zone: tuple = (0.0, 0.0)  # (low, high)
    stop_loss: Optional[float] = None
    take_profit: List[float] = Field(default_factory=list)
    invalidation_level: Optional[float] = None
    
    # Timing
    expected_duration_hours: int = 24
    timing_window: tuple = (0, 0)  # (min_hours, max_hours)
    
    # Alpha sources
    alpha_contributors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # NEW: Feature vector for indicator intelligence
    feature_vector: Optional[Dict[str, Any]] = None
    
    # NEW: Indicator signal drivers
    indicator_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class HypothesisVisualizationService:
    """Service for hypothesis visualization with indicator intelligence."""
    
    def __init__(self):
        self.feature_service = get_feature_vector_service()
        self.probability_engine = get_scenario_probability_engine()
    
    def build_hypothesis_visualization(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        hypothesis_data: Optional[Dict[str, Any]] = None
    ) -> HypothesisVisualization:
        """Build visualization for a hypothesis with indicator intelligence."""
        
        if not candles:
            return HypothesisVisualization(
                hypothesis_id="empty",
                symbol=symbol,
                timeframe=timeframe,
                direction="neutral",
                confidence=0.0,
                strength="weak",
                current_price=0.0,
            )
        
        current_price = candles[-1]["close"]
        current_time = candles[-1]["timestamp"]
        
        # BUILD FEATURE VECTOR (new multi-factor model)
        feature_vector = self.feature_service.build_feature_vector(candles, symbol, timeframe)
        
        # Use feature vector for direction and confidence
        direction, confidence, strength = self._analyze_direction_with_features(feature_vector)
        
        # Get DYNAMIC scenario probabilities
        scenario_probs = self.probability_engine.calculate_scenario_probabilities(feature_vector)
        
        # Build scenarios with dynamic probabilities
        scenarios = self._build_scenarios_with_features(
            candles, current_price, current_time, direction, feature_vector, scenario_probs
        )
        
        # Calculate key levels
        entry_zone = self._calculate_entry_zone(candles, direction)
        stop_loss = self._calculate_stop_loss(candles, direction)
        take_profit = self._calculate_take_profit(candles, direction, current_price)
        invalidation = self._calculate_invalidation(candles, direction)
        
        # Determine timing
        duration, timing_window = self._estimate_timing(timeframe)
        
        # Build indicator drivers for explanation
        indicator_drivers = self._build_indicator_drivers(feature_vector)
        
        # Build alpha contributors from feature vector
        alpha_contributors = self._build_alpha_contributors(feature_vector)
        
        return HypothesisVisualization(
            hypothesis_id=f"hyp_{symbol}_{timeframe}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            confidence=confidence,
            strength=strength,
            current_price=current_price,
            scenarios=scenarios,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            take_profit=take_profit,
            invalidation_level=invalidation,
            expected_duration_hours=duration,
            timing_window=timing_window,
            alpha_contributors=alpha_contributors,
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "volatility_score": feature_vector.volatility_score,
                "breakout_score": feature_vector.breakout_score,
                "net_score": feature_vector.net_score,
                "confidence": feature_vector.confidence,
                "agreement_ratio": feature_vector.agreement_ratio,
            },
            indicator_drivers=indicator_drivers,
        )
    
    def _analyze_direction_with_features(
        self,
        feature_vector: MarketFeatureVector
    ) -> tuple:
        """Analyze direction using feature vector."""
        net = feature_vector.net_score
        conf = feature_vector.confidence
        
        if net > 0.3:
            direction = "bullish"
        elif net < -0.3:
            direction = "bearish"
        else:
            direction = "neutral"
        
        # Adjust confidence based on agreement
        adjusted_confidence = conf * feature_vector.agreement_ratio
        confidence = min(0.95, max(0.3, adjusted_confidence + 0.3))
        
        if confidence >= 0.75:
            strength = "strong"
        elif confidence >= 0.55:
            strength = "moderate"
        else:
            strength = "weak"
        
        return direction, round(confidence, 2), strength
    
    def _build_scenarios_with_features(
        self,
        candles: List[Dict[str, Any]],
        current_price: float,
        current_time: str,
        direction: str,
        feature_vector: MarketFeatureVector,
        scenario_probs: Dict[str, float]
    ) -> List[ScenarioVisualization]:
        """Build scenarios with dynamic probabilities from feature vector."""
        scenarios = []
        atr = self._calculate_atr(candles)
        
        tf_hours = {"1m": 0.5, "5m": 2, "15m": 6, "1h": 24, "4h": 96, "1d": 240}
        hours_ahead = tf_hours.get(self._guess_timeframe(candles), 24)
        
        # Target percentages adjusted by feature vector strength
        net = feature_vector.net_score
        base_mult = 1 + abs(net) * 0.5  # Stronger signals = larger targets
        
        if direction == "bullish":
            scenarios.append(self._create_scenario(
                "base", current_price, current_time, hours_ahead,
                target_pct=0.03 * base_mult, 
                probability=scenario_probs.get("base", 0.40), 
                color="#22C55E", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bull", current_price, current_time, hours_ahead,
                target_pct=0.06 * base_mult, 
                probability=scenario_probs.get("bull", 0.20), 
                color="#10B981", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bear", current_price, current_time, hours_ahead,
                target_pct=-0.02, 
                probability=scenario_probs.get("bear", 0.20), 
                color="#EF4444", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "extreme_bull", current_price, current_time, hours_ahead,
                target_pct=0.10 * base_mult, 
                probability=scenario_probs.get("extreme_bull", 0.10), 
                color="#059669", atr=atr
            ))
            
        elif direction == "bearish":
            scenarios.append(self._create_scenario(
                "base", current_price, current_time, hours_ahead,
                target_pct=-0.03 * base_mult, 
                probability=scenario_probs.get("base", 0.40), 
                color="#EF4444", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bear", current_price, current_time, hours_ahead,
                target_pct=-0.06 * base_mult, 
                probability=scenario_probs.get("bear", 0.20), 
                color="#DC2626", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bull", current_price, current_time, hours_ahead,
                target_pct=0.02, 
                probability=scenario_probs.get("bull", 0.20), 
                color="#22C55E", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "extreme_bear", current_price, current_time, hours_ahead,
                target_pct=-0.10 * base_mult, 
                probability=scenario_probs.get("extreme_bear", 0.10), 
                color="#991B1B", atr=atr
            ))
            
        else:  # neutral
            scenarios.append(self._create_scenario(
                "base", current_price, current_time, hours_ahead,
                target_pct=0.0, 
                probability=scenario_probs.get("base", 0.50), 
                color="#6B7280", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bull", current_price, current_time, hours_ahead,
                target_pct=0.02, 
                probability=scenario_probs.get("bull", 0.25), 
                color="#22C55E", atr=atr
            ))
            scenarios.append(self._create_scenario(
                "bear", current_price, current_time, hours_ahead,
                target_pct=-0.02, 
                probability=scenario_probs.get("bear", 0.25), 
                color="#EF4444", atr=atr
            ))
        
        return scenarios
    
    def _build_indicator_drivers(
        self,
        feature_vector: MarketFeatureVector
    ) -> List[Dict[str, Any]]:
        """Build indicator drivers for explanation."""
        drivers = []
        
        # Top contributing signals
        sorted_signals = sorted(
            feature_vector.indicator_signals,
            key=lambda s: abs(s.score) * s.strength,
            reverse=True
        )
        
        for signal in sorted_signals[:5]:  # Top 5
            drivers.append({
                "indicator": signal.indicator.upper(),
                "direction": signal.direction,
                "score": signal.score,
                "reason": signal.reason,
            })
        
        return drivers
    
    def _build_alpha_contributors(
        self,
        feature_vector: MarketFeatureVector
    ) -> List[Dict[str, Any]]:
        """Build alpha contributors from feature vector."""
        return [
            {
                "name": "Trend Indicators",
                "weight": 0.35,
                "score": feature_vector.trend_score,
                "signal": "bullish" if feature_vector.trend_score > 0.2 else "bearish" if feature_vector.trend_score < -0.2 else "neutral"
            },
            {
                "name": "Momentum Indicators",
                "weight": 0.25,
                "score": feature_vector.momentum_score,
                "signal": "bullish" if feature_vector.momentum_score > 0.2 else "bearish" if feature_vector.momentum_score < -0.2 else "neutral"
            },
            {
                "name": "Breakout Signals",
                "weight": 0.20,
                "score": feature_vector.breakout_score,
                "signal": "active" if abs(feature_vector.breakout_score) > 0.5 else "inactive"
            },
            {
                "name": "Volatility Context",
                "weight": 0.15,
                "score": feature_vector.volatility_score,
                "signal": "high" if feature_vector.volatility_score > 0.3 else "low" if feature_vector.volatility_score < -0.3 else "normal"
            },
            {
                "name": "Structure Analysis",
                "weight": 0.05,
                "score": feature_vector.structure_score,
                "signal": "bullish" if feature_vector.structure_score > 0.2 else "bearish" if feature_vector.structure_score < -0.2 else "neutral"
            },
        ]
    
    def _create_scenario(
        self,
        scenario_type: str,
        current_price: float,
        current_time: str,
        hours_ahead: int,
        target_pct: float,
        probability: float,
        color: str,
        atr: float
    ) -> ScenarioVisualization:
        """Create a single scenario."""
        # Generate price path
        target_price = current_price * (1 + target_pct)
        
        # Parse current time using unified normalizer
        base_time = normalize_timestamp(current_time) or datetime.now(timezone.utc)
        
        # Generate path points
        num_points = min(hours_ahead, 50)
        path = []
        upper_band = []
        lower_band = []
        
        for i in range(num_points + 1):
            progress = i / num_points
            
            # Non-linear path with some noise
            noise = np.random.normal(0, atr * 0.2) if i > 0 else 0
            price = current_price + (target_price - current_price) * progress + noise
            
            # Confidence decreases over time
            conf = 1.0 - (progress * 0.3)
            
            # Bands widen over time
            band_width = atr * (1 + progress * 2)
            
            point_time = base_time + timedelta(hours=hours_ahead * progress)
            
            path.append(PricePathPoint(
                timestamp=point_time.isoformat(),
                price=round(price, 2),
                confidence=round(conf, 2)
            ))
            
            upper_band.append(round(price + band_width, 2))
            lower_band.append(round(price - band_width, 2))
        
        return ScenarioVisualization(
            scenario_id=f"scenario_{scenario_type}",
            type=scenario_type,
            probability=probability,
            expected_path=path,
            upper_band=upper_band,
            lower_band=lower_band,
            target_price=round(target_price, 2),
            target_timestamp=(base_time + timedelta(hours=hours_ahead)).isoformat(),
            color=color,
            opacity=0.3 + probability * 0.4,
        )
    
    def _calculate_entry_zone(
        self,
        candles: List[Dict[str, Any]],
        direction: str
    ) -> tuple:
        """Calculate entry zone."""
        if not candles:
            return (0.0, 0.0)
        
        current = candles[-1]["close"]
        atr = self._calculate_atr(candles)
        
        if direction == "bullish":
            # Entry on pullback
            zone_low = current - atr * 0.5
            zone_high = current
        elif direction == "bearish":
            # Entry on rally
            zone_low = current
            zone_high = current + atr * 0.5
        else:
            zone_low = current - atr * 0.25
            zone_high = current + atr * 0.25
        
        return (round(zone_low, 2), round(zone_high, 2))
    
    def _calculate_stop_loss(
        self,
        candles: List[Dict[str, Any]],
        direction: str
    ) -> float:
        """Calculate stop loss level."""
        if len(candles) < 10:
            return candles[-1]["close"] if candles else 0.0
        
        current = candles[-1]["close"]
        atr = self._calculate_atr(candles)
        
        # Find recent swing
        if direction == "bullish":
            recent_low = min(c["low"] for c in candles[-10:])
            stop = min(recent_low - atr * 0.5, current - atr * 1.5)
        elif direction == "bearish":
            recent_high = max(c["high"] for c in candles[-10:])
            stop = max(recent_high + atr * 0.5, current + atr * 1.5)
        else:
            stop = current - atr if np.random.random() > 0.5 else current + atr
        
        return round(stop, 2)
    
    def _calculate_take_profit(
        self,
        candles: List[Dict[str, Any]],
        direction: str,
        current_price: float
    ) -> List[float]:
        """Calculate take profit levels."""
        atr = self._calculate_atr(candles)
        
        if direction == "bullish":
            return [
                round(current_price + atr * 1.5, 2),
                round(current_price + atr * 2.5, 2),
                round(current_price + atr * 4.0, 2),
            ]
        elif direction == "bearish":
            return [
                round(current_price - atr * 1.5, 2),
                round(current_price - atr * 2.5, 2),
                round(current_price - atr * 4.0, 2),
            ]
        else:
            return [
                round(current_price + atr * 1.0, 2),
                round(current_price - atr * 1.0, 2),
            ]
    
    def _calculate_invalidation(
        self,
        candles: List[Dict[str, Any]],
        direction: str
    ) -> float:
        """Calculate invalidation level."""
        if len(candles) < 20:
            return candles[-1]["close"] if candles else 0.0
        
        if direction == "bullish":
            return round(min(c["low"] for c in candles[-20:]), 2)
        elif direction == "bearish":
            return round(max(c["high"] for c in candles[-20:]), 2)
        else:
            return None
    
    def _estimate_timing(self, timeframe: str) -> tuple:
        """Estimate hypothesis timing."""
        timing_map = {
            "1m": (1, (0.5, 2)),
            "5m": (4, (2, 8)),
            "15m": (12, (6, 24)),
            "1h": (48, (24, 96)),
            "4h": (168, (72, 336)),
            "1d": (672, (336, 1008)),
        }
        
        return timing_map.get(timeframe, (48, (24, 96)))
    
    def _calculate_atr(self, candles: List[Dict[str, Any]], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < 2:
            return 0.0
        
        tr_values = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            tr_values.append(tr)
        
        return np.mean(tr_values) if tr_values else 0.0
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Calculate EMA."""
        if not data:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        
        for i in range(1, len(data)):
            ema.append(data[i] * multiplier + ema[-1] * (1 - multiplier))
        
        return ema
    
    def _guess_timeframe(self, candles: List[Dict[str, Any]]) -> str:
        """Guess timeframe from candle timestamps."""
        if len(candles) < 2:
            return "1h"
        
        # Try to determine from timestamp difference
        try:
            t1 = datetime.fromisoformat(candles[0]["timestamp"].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(candles[1]["timestamp"].replace('Z', '+00:00'))
            diff_minutes = (t2 - t1).total_seconds() / 60
            
            if diff_minutes <= 1:
                return "1m"
            elif diff_minutes <= 5:
                return "5m"
            elif diff_minutes <= 15:
                return "15m"
            elif diff_minutes <= 60:
                return "1h"
            elif diff_minutes <= 240:
                return "4h"
            else:
                return "1d"
        except:
            return "1h"


# Singleton
_hypothesis_viz_service: Optional[HypothesisVisualizationService] = None

def get_hypothesis_viz_service() -> HypothesisVisualizationService:
    global _hypothesis_viz_service
    if _hypothesis_viz_service is None:
        _hypothesis_viz_service = HypothesisVisualizationService()
    return _hypothesis_viz_service
