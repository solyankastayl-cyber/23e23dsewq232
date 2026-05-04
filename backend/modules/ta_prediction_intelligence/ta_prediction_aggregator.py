"""
Aggregator — runs all engines, resolves conflicts, builds scenarios,
and returns a typed TAPredictionContext.

No external I/O. Pure function of the supplied `setup` dict.
"""

from typing import Any, Dict, Optional

from .engines.level_zone_prediction_engine import LevelZonePredictionEngine
from .engines.momentum_prediction_engine import MomentumPredictionEngine
from .engines.pattern_prediction_engine import PatternPredictionEngine
from .engines.structure_prediction_engine import StructurePredictionEngine
from .engines.volatility_prediction_engine import VolatilityPredictionEngine
from .scenarios.scenario_builder import ScenarioBuilder
from .ta_prediction_conflict_resolver import TAPredictionConflictResolver
from .types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAPredictionContext,
)


class TAPredictionAggregator:
    def __init__(self):
        self.engines = [
            StructurePredictionEngine(),
            PatternPredictionEngine(),
            MomentumPredictionEngine(),
            LevelZonePredictionEngine(),
            VolatilityPredictionEngine(),
        ]
        self.resolver = TAPredictionConflictResolver()
        self.scenarios = ScenarioBuilder()

    def build(
        self,
        symbol: str,
        timeframe: str,
        setup: Dict[str, Any],
        market_regime: Optional[str] = None,
    ) -> TAPredictionContext:
        contributions = []
        for engine in self.engines:
            try:
                contributions.append(engine.analyze(setup))
            except Exception as exc:  # pragma: no cover — engines must self-heal
                contributions.append(
                    self._error_contribution(engine.__class__.__name__, exc)
                )

        resolved = self.resolver.resolve(contributions, market_regime=market_regime)
        bias = resolved["bias"]
        confidence = resolved["confidence"]
        expected_move_pct = self._aggregate_expected_move(contributions, bias)

        current_price = self._get_price(setup)
        scenarios = self.scenarios.build(
            bias=bias,
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            current_price=current_price,
            drivers=resolved["drivers"],
        )

        return TAPredictionContext(
            symbol=symbol,
            timeframe=timeframe,
            bias=bias,
            confidence=confidence,
            expected_move_pct=round(expected_move_pct, 6),
            conflict_ratio=resolved["conflict_ratio"],
            dominant_engine=resolved["dominant_engine"],
            contributions=contributions,
            scenarios=scenarios,
            drivers=resolved["drivers"],
            risks=resolved["risks"],
            meta={
                "market_regime": market_regime,
                "contribution_count": len(contributions),
            },
        )

    def _aggregate_expected_move(self, contributions, final_bias: PredictionBias) -> float:
        total = 0.0
        weight = 0.0
        for c in contributions:
            if c.confidence <= 0:
                continue
            if c.bias == PredictionBias.BULLISH:
                sign = 1
            elif c.bias == PredictionBias.BEARISH:
                sign = -1
            else:
                # neutral contributes magnitude in the direction of the final bias only
                if final_bias == PredictionBias.NEUTRAL:
                    continue
                sign = 1 if final_bias == PredictionBias.BULLISH else -1
            total += sign * abs(c.expected_move_pct) * c.confidence
            weight += c.confidence
        if weight <= 0:
            return 0.0
        return total / weight

    def _get_price(self, setup: Dict[str, Any]):
        for key in ("price", "current_price"):
            if key in setup:
                try:
                    return float(setup[key])
                except Exception:
                    pass
        # nested fallbacks
        for path in (("market", "price"), ("summary", "price")):
            cur = setup
            ok = True
            for k in path:
                if not isinstance(cur, dict) or k not in cur:
                    ok = False
                    break
                cur = cur[k]
            if ok:
                try:
                    return float(cur)
                except Exception:
                    pass
        return None

    def _error_contribution(self, engine_name: str, exc: Exception) -> EngineContribution:
        return EngineContribution(
            engine=engine_name,
            bias=PredictionBias.NEUTRAL,
            score=0.0,
            confidence=0.0,
            expected_move_pct=0.0,
            horizon=PredictionHorizon.H1.value,
            drivers=[],
            risks=[f"engine_error:{type(exc).__name__}"],
            raw={"error": str(exc)},
        )
