"""
Prediction Engine V2

TA-first prediction system.

Core principle:
    Prediction = f(TA Engine output)

Pipeline:
    1. TA Input → Direction
    2. Direction → Confidence
    3. Input + Direction → Scenarios (bull/base/bear)
    4. Scenarios → Paths + Bands
    5. Output

NO external dependencies on Exchange/Sentiment/Fractal as core.
Those can be used as optional modifiers only.
"""

from typing import Dict, Optional, Any
from datetime import datetime

from .types import (
    PredictionInput,
    PredictionOutput,
    Direction,
    Confidence,
    Scenario,
)
from .direction import build_direction
from .confidence import build_confidence
from .scenarios import build_scenarios
from .path_builder import (
    resolve_horizon,
    build_paths_for_scenarios,
)
from .ta_interpreter import (
    interpret_ta_output,
    build_input_from_raw,
)


class PredictionEngine:
    """
    TA-based Prediction Engine V2.
    
    Usage:
        engine = PredictionEngine()
        prediction = engine.predict(ta_input)
    """
    
    def __init__(self):
        self._cache: Dict[str, PredictionOutput] = {}
    
    def predict(self, input: PredictionInput) -> PredictionOutput:
        """
        Generate prediction from TA input.
        
        Args:
            input: PredictionInput built from TA Engine output
        
        Returns:
            PredictionOutput with direction, scenarios, confidence, and paths
        """
        # ─────────────────────────────────────────────────────────
        # 1. Calculate direction
        # ─────────────────────────────────────────────────────────
        direction = build_direction(input)
        
        # ─────────────────────────────────────────────────────────
        # 2. Calculate confidence
        # ─────────────────────────────────────────────────────────
        confidence = build_confidence(input, direction)
        
        # ─────────────────────────────────────────────────────────
        # 3. Resolve horizon
        # ─────────────────────────────────────────────────────────
        horizon_days = resolve_horizon(input.timeframe)
        
        # ─────────────────────────────────────────────────────────
        # 4. Build scenarios (bull/base/bear)
        # ─────────────────────────────────────────────────────────
        scenarios = build_scenarios(input, direction)
        
        # ─────────────────────────────────────────────────────────
        # 5. Build paths and bands for each scenario
        # ─────────────────────────────────────────────────────────
        scenarios = build_paths_for_scenarios(
            scenarios=scenarios,
            price=input.price,
            horizon_days=horizon_days,
            volatility=input.indicators.volatility,
            start_time=input.timestamp,
        )
        
        # ─────────────────────────────────────────────────────────
        # 6. Assemble output
        # ─────────────────────────────────────────────────────────
        output = PredictionOutput(
            symbol=input.symbol,
            timeframe=input.timeframe,
            current_price=input.price,
            direction=direction,
            confidence=confidence,
            scenarios=scenarios,
            horizon_days=horizon_days,
            version="v2",
            created_at=datetime.utcnow(),
        )
        
        # Cache result
        cache_key = f"{input.symbol}_{input.timeframe}"
        self._cache[cache_key] = output
        
        return output
    
    def predict_from_ta(
        self,
        ta_output: Dict[str, Any],
        symbol: str,
        timeframe: str,
    ) -> PredictionOutput:
        """
        Generate prediction directly from TA Engine output.
        
        Convenience method that handles TA interpretation.
        """
        input = interpret_ta_output(ta_output, symbol, timeframe)
        return self.predict(input)
    
    def predict_quick(
        self,
        symbol: str,
        timeframe: str,
        price: float,
        pattern_type: str = "none",
        pattern_direction: str = "neutral",
        pattern_confidence: float = 0.0,
        pattern_target: Optional[float] = None,
        structure_state: str = "range",
        structure_trend: str = "flat",
        trend_strength: float = 0.5,
        momentum: float = 0.0,
        volatility: float = 0.3,
    ) -> PredictionOutput:
        """
        Quick prediction with raw parameters.
        
        Useful for API endpoints or simple use cases.
        """
        input = build_input_from_raw(
            symbol=symbol,
            timeframe=timeframe,
            price=price,
            pattern_type=pattern_type,
            pattern_direction=pattern_direction,
            pattern_confidence=pattern_confidence,
            pattern_target=pattern_target,
            structure_state=structure_state,
            structure_trend=structure_trend,
            trend_strength=trend_strength,
            momentum=momentum,
            volatility=volatility,
        )
        return self.predict(input)
    
    def get_cached(self, symbol: str, timeframe: str) -> Optional[PredictionOutput]:
        """Get cached prediction if available."""
        cache_key = f"{symbol}_{timeframe}"
        return self._cache.get(cache_key)
    
    def clear_cache(self):
        """Clear prediction cache."""
        self._cache.clear()


# ══════════════════════════════════════════════════════════════
# Module-level convenience functions
# ══════════════════════════════════════════════════════════════

_engine: Optional[PredictionEngine] = None


def get_prediction_engine() -> PredictionEngine:
    """Get singleton prediction engine instance."""
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
    return _engine


def build_prediction(input: PredictionInput) -> PredictionOutput:
    """
    Build prediction from TA input.
    
    Module-level convenience function.
    """
    return get_prediction_engine().predict(input)


def build_prediction_from_ta(
    ta_output: Dict[str, Any],
    symbol: str,
    timeframe: str,
) -> PredictionOutput:
    """
    Build prediction directly from TA Engine output.
    
    Module-level convenience function.
    """
    return get_prediction_engine().predict_from_ta(ta_output, symbol, timeframe)


def build_prediction_quick(
    symbol: str,
    timeframe: str,
    price: float,
    **kwargs,
) -> PredictionOutput:
    """
    Quick prediction with parameters.
    
    Module-level convenience function.
    """
    return get_prediction_engine().predict_quick(
        symbol=symbol,
        timeframe=timeframe,
        price=price,
        **kwargs,
    )
