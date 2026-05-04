"""
Conflict resolver — analogous to exchange_intelligence's resolver.
Computes weighted bullish / bearish strength, conflict ratio, dominant engine.
Weights are regime-aware via REGIME_MODIFIERS.
"""

from typing import Any, Dict, List, Optional

from .types import EngineContribution, PredictionBias


class TAPredictionConflictResolver:
    BASE_WEIGHTS: Dict[str, float] = {
        "structure": 1.20,
        "pattern": 1.10,
        "momentum": 1.00,
        "level_zone": 0.85,
        "volatility": 0.60,
    }

    REGIME_MODIFIERS: Dict[str, Dict[str, float]] = {
        "trend": {
            "structure": 1.25,
            "momentum": 1.20,
            "pattern": 1.05,
            "level_zone": 0.85,
            "volatility": 0.80,
        },
        "range": {
            "level_zone": 1.30,
            "momentum": 0.85,
            "structure": 0.90,
            "pattern": 1.00,
            "volatility": 0.75,
        },
        "compression": {
            "volatility": 1.40,
            "pattern": 1.25,
            "structure": 1.00,
            "momentum": 0.80,
            "level_zone": 0.80,
        },
        "high_volatility": {
            "volatility": 1.25,
            "level_zone": 1.10,
            "momentum": 0.80,
            "structure": 0.95,
            "pattern": 0.90,
        },
    }

    def resolve(
        self,
        contributions: List[EngineContribution],
        market_regime: Optional[str] = None,
    ) -> Dict[str, Any]:
        bullish_strength = 0.0
        bearish_strength = 0.0
        neutral_strength = 0.0
        weighted_contributions: Dict[str, float] = {}
        drivers: List[str] = []
        risks: List[str] = []

        for c in contributions:
            weight = self._weight_for(c.engine, market_regime)
            strength = float(c.confidence) * weight
            weighted_contributions[c.engine] = round(strength, 6)
            if c.bias == PredictionBias.BULLISH:
                bullish_strength += strength
            elif c.bias == PredictionBias.BEARISH:
                bearish_strength += strength
            else:
                neutral_strength += strength * 0.5
            drivers.extend(c.drivers)
            risks.extend(c.risks)

        directional_total = bullish_strength + bearish_strength
        if directional_total <= 0:
            return {
                "bias": PredictionBias.NEUTRAL,
                "confidence": 0.0,
                "conflict_ratio": 0.0,
                "dominant_engine": None,
                "contributions": weighted_contributions,
                "drivers": sorted(set(drivers)),
                "risks": sorted(set(risks)),
            }

        conflict_ratio = min(bullish_strength, bearish_strength) / directional_total

        if bullish_strength > bearish_strength:
            bias = PredictionBias.BULLISH
            raw_confidence = bullish_strength / directional_total
        elif bearish_strength > bullish_strength:
            bias = PredictionBias.BEARISH
            raw_confidence = bearish_strength / directional_total
        else:
            bias = PredictionBias.NEUTRAL
            raw_confidence = 0.0

        confidence = max(0.0, min(1.0, raw_confidence * (1.0 - conflict_ratio * 0.35)))
        dominant_engine = self._dominant(weighted_contributions)

        return {
            "bias": bias,
            "confidence": round(confidence, 4),
            "conflict_ratio": round(conflict_ratio, 4),
            "dominant_engine": dominant_engine,
            "contributions": weighted_contributions,
            "drivers": sorted(set(drivers)),
            "risks": sorted(set(risks)),
        }

    def _weight_for(self, engine: str, regime: Optional[str]) -> float:
        base = self.BASE_WEIGHTS.get(engine, 1.0)
        modifier = self.REGIME_MODIFIERS.get(
            str(regime or "").lower(), {}
        ).get(engine, 1.0)
        return base * modifier

    def _dominant(self, weighted: Dict[str, float]) -> Optional[str]:
        if not weighted:
            return None
        items = sorted(weighted.items(), key=lambda x: x[1], reverse=True)
        if not items or items[0][1] <= 0:
            return None
        if len(items) == 1:
            return items[0][0]
        if items[0][1] >= items[1][1] * 1.2:
            return items[0][0]
        return None
