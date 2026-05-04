"""
Prediction Engine V3

Advanced features:
- Drift adaptation (adjusts path based on actual price)
- Self-correction (learns from deviations)
- Version transitions (V1 → V2 → V3)
- Path smoothing with noise
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .types import (
    PredictionInput,
    PredictionOutput,
    Scenario,
    PathPoint,
    Direction,
    Confidence,
)
from .prediction_engine import PredictionEngine, build_prediction


# ══════════════════════════════════════════════════════════════
# V3 Types
# ══════════════════════════════════════════════════════════════

@dataclass
class PredictionVersion:
    """Single version of a prediction."""
    version_id: str  # v1, v2, v3...
    created_at: datetime
    prediction: PredictionOutput
    trigger: str  # "initial", "drift", "correction", "new_signal"
    deviation_from_prev: Optional[float] = None  # % deviation that triggered update


@dataclass
class PredictionHistory:
    """Full history of prediction versions."""
    symbol: str
    timeframe: str
    versions: List[PredictionVersion] = field(default_factory=list)
    current_version: Optional[PredictionVersion] = None
    accuracy_score: float = 0.0  # Historical accuracy
    total_corrections: int = 0


@dataclass
class DriftUpdate:
    """Drift update result."""
    needs_update: bool
    deviation: float
    reason: str
    new_target: Optional[float] = None


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Drift thresholds
DRIFT_MINOR_THRESHOLD = 0.02   # 2% deviation = minor adjustment
DRIFT_MAJOR_THRESHOLD = 0.05  # 5% deviation = major update
DRIFT_CRITICAL_THRESHOLD = 0.10  # 10% deviation = full recalculation

# Correction weights
CORRECTION_LEARNING_RATE = 0.1

# Path noise
PATH_NOISE_AMPLITUDE = 0.005  # 0.5% random noise


# ══════════════════════════════════════════════════════════════
# Prediction Engine V3
# ══════════════════════════════════════════════════════════════

class PredictionEngineV3:
    """
    Advanced Prediction Engine with:
    - Drift detection and adaptation
    - Self-correction from historical performance
    - Version history tracking
    - Realistic path generation with noise
    """
    
    def __init__(self):
        self._engine = PredictionEngine()
        self._histories: Dict[str, PredictionHistory] = {}
        self._correction_factors: Dict[str, float] = {}
    
    def predict(self, input: PredictionInput) -> PredictionOutput:
        """
        Generate prediction with V3 enhancements.
        """
        # Get base prediction from V2 engine
        base_prediction = self._engine.predict(input)
        
        # Apply self-correction based on historical accuracy
        corrected_prediction = self._apply_correction(input, base_prediction)
        
        # Add realistic noise to paths
        noisy_prediction = self._add_path_noise(corrected_prediction, input.indicators.volatility)
        
        # Track version
        self._track_version(input.symbol, input.timeframe, noisy_prediction, "initial")
        
        return noisy_prediction
    
    def update_with_drift(
        self,
        symbol: str,
        timeframe: str,
        current_price: float,
        input: Optional[PredictionInput] = None,
    ) -> Tuple[Optional[PredictionOutput], DriftUpdate]:
        """
        Check for drift and update prediction if needed.
        
        Drift = deviation between actual price and predicted path.
        """
        history = self._histories.get(f"{symbol}_{timeframe}")
        
        if history is None or history.current_version is None:
            return None, DriftUpdate(
                needs_update=False,
                deviation=0,
                reason="No existing prediction",
            )
        
        current = history.current_version.prediction
        
        # Calculate deviation from expected path
        deviation = self._calculate_deviation(current, current_price)
        
        # Determine if update needed
        if abs(deviation) >= DRIFT_CRITICAL_THRESHOLD:
            # Critical drift - full recalculation
            if input:
                new_prediction = self.predict(input)
                return new_prediction, DriftUpdate(
                    needs_update=True,
                    deviation=deviation,
                    reason="Critical drift - full recalculation",
                    new_target=new_prediction.scenarios["base"].target_price,
                )
            return None, DriftUpdate(
                needs_update=True,
                deviation=deviation,
                reason="Critical drift - input required for recalculation",
            )
        
        elif abs(deviation) >= DRIFT_MAJOR_THRESHOLD:
            # Major drift - adjust targets
            adjusted = self._adjust_for_drift(current, current_price, deviation)
            self._track_version(symbol, timeframe, adjusted, "drift")
            return adjusted, DriftUpdate(
                needs_update=True,
                deviation=deviation,
                reason="Major drift - targets adjusted",
                new_target=adjusted.scenarios["base"].target_price,
            )
        
        elif abs(deviation) >= DRIFT_MINOR_THRESHOLD:
            # Minor drift - path adjustment only
            adjusted = self._adjust_path_start(current, current_price)
            return adjusted, DriftUpdate(
                needs_update=False,
                deviation=deviation,
                reason="Minor drift - path adjusted",
            )
        
        return None, DriftUpdate(
            needs_update=False,
            deviation=deviation,
            reason="Within tolerance",
        )
    
    def record_outcome(
        self,
        symbol: str,
        timeframe: str,
        actual_price: float,
        at_horizon: bool = True,
    ):
        """
        Record actual outcome for learning.
        
        Updates correction factors based on prediction vs reality.
        """
        history = self._histories.get(f"{symbol}_{timeframe}")
        
        if history is None or history.current_version is None:
            return
        
        prediction = history.current_version.prediction
        predicted_price = prediction.scenarios["base"].target_price
        
        # Calculate error
        error = (actual_price - predicted_price) / predicted_price
        
        # Update correction factor (exponential moving average)
        key = f"{symbol}_{timeframe}"
        current_factor = self._correction_factors.get(key, 0.0)
        new_factor = current_factor + CORRECTION_LEARNING_RATE * (error - current_factor)
        self._correction_factors[key] = new_factor
        
        # Update accuracy score
        accuracy = 1.0 - min(abs(error), 1.0)
        history.accuracy_score = (
            history.accuracy_score * 0.9 + accuracy * 0.1
        )  # EMA of accuracy
        
        history.total_corrections += 1
    
    def get_history(self, symbol: str, timeframe: str) -> Optional[PredictionHistory]:
        """Get prediction history."""
        return self._histories.get(f"{symbol}_{timeframe}")
    
    def get_versions(self, symbol: str, timeframe: str) -> List[PredictionVersion]:
        """Get all prediction versions."""
        history = self._histories.get(f"{symbol}_{timeframe}")
        return history.versions if history else []
    
    # ─────────────────────────────────────────────────────────
    # Private methods
    # ─────────────────────────────────────────────────────────
    
    def _apply_correction(
        self,
        input: PredictionInput,
        prediction: PredictionOutput,
    ) -> PredictionOutput:
        """Apply self-correction based on historical performance."""
        key = f"{input.symbol}_{input.timeframe}"
        correction = self._correction_factors.get(key, 0.0)
        
        if abs(correction) < 0.005:  # Less than 0.5% - no correction needed
            return prediction
        
        # Adjust targets based on historical bias
        for name, scenario in prediction.scenarios.items():
            # Adjust target price
            adjustment = 1 + correction * 0.5  # Apply half of correction factor
            scenario.target_price *= adjustment
            scenario.expected_return = (scenario.target_price - prediction.current_price) / prediction.current_price
            
            # Rebuild path with adjusted target
            scenario.path = self._rebuild_path(
                prediction.current_price,
                scenario.target_price,
                prediction.horizon_days,
            )
        
        return prediction
    
    def _add_path_noise(
        self,
        prediction: PredictionOutput,
        volatility: float,
    ) -> PredictionOutput:
        """Add realistic noise to prediction paths."""
        noise_amplitude = PATH_NOISE_AMPLITUDE * (1 + volatility)
        
        for name, scenario in prediction.scenarios.items():
            # Add noise to path
            noisy_path = []
            for i, point in enumerate(scenario.path):
                if i == 0:
                    # First point is actual price - no noise
                    noisy_path.append(point)
                else:
                    # Add random walk noise
                    noise = point.price * noise_amplitude * random.gauss(0, 1)
                    noisy_path.append(PathPoint(
                        t=point.t,
                        price=point.price + noise,
                        timestamp=point.timestamp,
                    ))
            scenario.path = noisy_path
        
        return prediction
    
    def _calculate_deviation(
        self,
        prediction: PredictionOutput,
        current_price: float,
    ) -> float:
        """Calculate deviation from predicted path."""
        # Find expected price on path
        base_path = prediction.scenarios["base"].path
        
        if not base_path:
            return 0.0
        
        # Simple approach: compare to first path point
        expected_price = base_path[0].price
        
        deviation = (current_price - expected_price) / expected_price
        return deviation
    
    def _adjust_for_drift(
        self,
        prediction: PredictionOutput,
        current_price: float,
        deviation: float,
    ) -> PredictionOutput:
        """Adjust prediction for major drift."""
        # Calculate drift direction
        drift_direction = 1 if deviation > 0 else -1
        
        # Adjust scenarios
        for name, scenario in prediction.scenarios.items():
            # Adjust target based on drift
            drift_adjustment = 1 + deviation * 0.3  # Partial adjustment
            scenario.target_price *= drift_adjustment
            scenario.expected_return = (scenario.target_price - current_price) / current_price
            
            # Rebuild path from current price
            scenario.path = self._rebuild_path(
                current_price,
                scenario.target_price,
                prediction.horizon_days,
            )
            
            # Recalculate bands
            scenario.band_low, scenario.band_high = self._rebuild_bands(
                scenario.path,
                prediction.confidence.factors.get("volatility_adj", 0.3),
                name,
            )
        
        # Update current price in prediction
        prediction.current_price = current_price
        
        return prediction
    
    def _adjust_path_start(
        self,
        prediction: PredictionOutput,
        current_price: float,
    ) -> PredictionOutput:
        """Adjust path start for minor drift (keeps target)."""
        for name, scenario in prediction.scenarios.items():
            if scenario.path:
                # Shift path to start from current price
                shift = current_price - scenario.path[0].price
                for point in scenario.path:
                    point.price += shift * (1 - point.t / len(scenario.path))
        
        prediction.current_price = current_price
        return prediction
    
    def _rebuild_path(
        self,
        start_price: float,
        target_price: float,
        horizon_days: int,
    ) -> List[PathPoint]:
        """Rebuild path from start to target."""
        path = []
        start_time = datetime.utcnow()
        
        for i in range(horizon_days + 1):
            t = i / horizon_days if horizon_days > 0 else 1
            curve = 1 - (1 - t) ** 2  # Ease-out
            price = start_price + (target_price - start_price) * curve
            
            path.append(PathPoint(
                t=i,
                price=price,
                timestamp=start_time + timedelta(days=i),
            ))
        
        return path
    
    def _rebuild_bands(
        self,
        path: List[PathPoint],
        volatility: float,
        scenario_name: str,
    ) -> Tuple[List[PathPoint], List[PathPoint]]:
        """Rebuild confidence bands."""
        low = []
        high = []
        base_spread = volatility * 0.5
        
        if scenario_name == "bull":
            low_mult, high_mult = 0.7, 1.3
        elif scenario_name == "bear":
            low_mult, high_mult = 1.3, 0.7
        else:
            low_mult, high_mult = 1.0, 1.0
        
        for i, point in enumerate(path):
            time_factor = 1 + (i / len(path)) * 0.5
            spread = point.price * base_spread * time_factor
            
            low.append(PathPoint(
                t=point.t,
                price=point.price - spread * low_mult,
                timestamp=point.timestamp,
            ))
            high.append(PathPoint(
                t=point.t,
                price=point.price + spread * high_mult,
                timestamp=point.timestamp,
            ))
        
        return low, high
    
    def _track_version(
        self,
        symbol: str,
        timeframe: str,
        prediction: PredictionOutput,
        trigger: str,
    ):
        """Track prediction version."""
        key = f"{symbol}_{timeframe}"
        
        if key not in self._histories:
            self._histories[key] = PredictionHistory(
                symbol=symbol,
                timeframe=timeframe,
            )
        
        history = self._histories[key]
        
        # Calculate deviation from previous if exists
        deviation = None
        if history.current_version:
            prev_target = history.current_version.prediction.scenarios["base"].target_price
            new_target = prediction.scenarios["base"].target_price
            deviation = (new_target - prev_target) / prev_target
        
        # Create version
        version_num = len(history.versions) + 1
        version = PredictionVersion(
            version_id=f"v{version_num}",
            created_at=datetime.utcnow(),
            prediction=prediction,
            trigger=trigger,
            deviation_from_prev=deviation,
        )
        
        history.versions.append(version)
        history.current_version = version


# ══════════════════════════════════════════════════════════════
# Regime-Aware Prediction (NEW)
# ══════════════════════════════════════════════════════════════

def build_prediction_regime_aware(
    inp: Dict,
    prev_regime: Optional[str] = None
) -> Dict:
    """
    Build prediction using regime-aware routing.
    
    Args:
        inp: Prediction input containing:
            - symbol: str
            - timeframe: str
            - price: float
            - structure: dict
            - pattern: dict
            - indicators: dict
        prev_regime: Previous regime (for hysteresis)
    
    Returns:
        Full prediction payload dict
    """
    from .regime_detector import detect_regime, get_regime_confidence, regime_to_model_name
    from .regime_router import route_prediction, apply_bias_fixes
    from datetime import timezone
    
    symbol = inp.get("symbol", "UNKNOWN")
    timeframe = inp.get("timeframe", "1D")
    price = float(inp.get("price", 0))
    
    # 1. Detect regime with hysteresis
    regime = detect_regime(inp, prev_regime)
    regime_conf = get_regime_confidence(inp, regime)
    model = regime_to_model_name(regime)
    
    # 2. Route to appropriate model
    direction, target, confidence = route_prediction(inp, regime)
    
    # 3. Apply bias fixes
    direction, target, confidence = apply_bias_fixes(
        direction, target, confidence, inp
    )
    
    # 4. Sanity checks
    # Cap move at 20%
    expected_return = (target - price) / price if price > 0 else 0
    if abs(expected_return) > 0.20:
        target = price * (1.20 if expected_return > 0 else 0.80)
        expected_return = (target - price) / price
    
    # Cap confidence at 90%
    confidence = min(confidence, 0.90)
    
    # 5. Calculate direction score
    direction_score = confidence if direction == "bullish" else (
        -confidence if direction == "bearish" else 0
    )
    
    # 6. Build scenarios
    scenarios = _build_regime_scenarios(price, direction, expected_return, confidence)
    
    # 7. Build final payload
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        
        # Regime info (NEW)
        "regime": regime,
        "regime_confidence": round(regime_conf, 3),
        "model": model,
        
        # Direction
        "direction": {
            "label": direction,
            "score": round(direction_score, 3),
        },
        
        # Target
        "target": {
            "start_price": round(price, 2),
            "target_price": round(target, 2),
            "expected_return": round(expected_return, 4),
        },
        
        # Confidence
        "confidence": {
            "value": round(confidence, 3),
            "label": _regime_confidence_label(confidence),
        },
        
        # Scenarios
        "scenarios": scenarios,
        
        # Meta
        "_engine_version": "v3_regime",
        "_pattern_used": inp.get("pattern", {}).get("type", "none"),
        "_trend_state": inp.get("structure", {}).get("trend", "flat"),
    }


def _build_regime_scenarios(
    price: float,
    direction: str,
    base_return: float,
    confidence: float
) -> Dict:
    """Build optimistic/base/pessimistic scenarios."""
    
    if direction == "neutral":
        return {
            "base": {
                "target_price": price,
                "expected_return": 0,
            },
            "optimistic": {
                "target_price": round(price * 1.03, 2),
                "expected_return": 0.03,
            },
            "pessimistic": {
                "target_price": round(price * 0.97, 2),
                "expected_return": -0.03,
            },
        }
    
    # Scale scenarios based on base return
    opt_mult = 1.5 if direction == "bullish" else 0.5
    pess_mult = 0.5 if direction == "bullish" else 1.5
    
    opt_return = base_return * opt_mult
    pess_return = base_return * pess_mult
    
    return {
        "base": {
            "target_price": round(price * (1 + base_return), 2),
            "expected_return": round(base_return, 4),
        },
        "optimistic": {
            "target_price": round(price * (1 + opt_return), 2),
            "expected_return": round(opt_return, 4),
        },
        "pessimistic": {
            "target_price": round(price * (1 + pess_return), 2),
            "expected_return": round(pess_return, 4),
        },
    }


def _regime_confidence_label(conf: float) -> str:
    """Map confidence value to label."""
    if conf >= 0.75:
        return "HIGH"
    elif conf >= 0.55:
        return "MEDIUM"
    else:
        return "LOW"


# ══════════════════════════════════════════════════════════════
# Module-level singleton
# ══════════════════════════════════════════════════════════════

_engine_v3: Optional[PredictionEngineV3] = None


def get_prediction_engine_v3() -> PredictionEngineV3:
    """Get singleton V3 engine instance."""
    global _engine_v3
    if _engine_v3 is None:
        _engine_v3 = PredictionEngineV3()
    return _engine_v3
