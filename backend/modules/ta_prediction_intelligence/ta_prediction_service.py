"""
Service boundary. Takes already-built TA setupData and returns TA prediction context.
No I/O. No Mongo. Pure aggregator delegate.

Two entry points:
  * `build_from_setup(...)` accepts a flexible dict shape. Useful when
    upstream callers already have render_plan / structure_context / ta_context
    laid out (e.g. CombinedAnalysisService or admin tools).
  * `build_from_typed_setup(...)` accepts the canonical `TAPredictionSetup`
    dataclass (architect-defined contract). The service adapts it into the
    dict shape the engines understand. This is the recommended entry point
    for external API consumers - clean, flat, typed.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .ta_prediction_aggregator import TAPredictionAggregator
from .types import TAPredictionSetup
from .engine_interactions import build_interaction_from_context
from .scenarios.scenario_interaction_adjuster import apply_interaction_adjustment
from .step7_pipeline import apply_step7_postprocess


class TAPredictionService:
    def __init__(self):
        self.aggregator = TAPredictionAggregator()

    # ------------------------------------------------------------------
    # Entry point #1 - flexible dict shape (existing callers)
    # ------------------------------------------------------------------
    def build_from_setup(
        self,
        symbol: str,
        timeframe: str,
        setup: Dict[str, Any],
        market_regime: Optional[str] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        ctx = self.aggregator.build(
            symbol=symbol,
            timeframe=timeframe,
            setup=setup,
            market_regime=market_regime,
        )
        result = ctx.to_dict()
        interaction = build_interaction_from_context(result)
        result["interaction"] = interaction.to_dict() if interaction else None
        adjusted_scenarios, adj_meta = apply_interaction_adjustment(
            result.get("scenarios") or [], result.get("interaction")
        )
        result["scenarios_original"] = result.get("scenarios") or []
        result["scenarios"] = adjusted_scenarios
        result["scenarios_adjustment"] = adj_meta
        # Step 7: calibration on top of Step 6. Persist off by default for the
        # typed/dict entry points so synthetic test traffic does not pollute
        # the prediction history.
        apply_step7_postprocess(result, source="from-setup", persist=persist)
        return result

    # ------------------------------------------------------------------
    # Entry point #2 - canonical typed contract (architect-blessed)
    # ------------------------------------------------------------------
    def build_from_typed_setup(
        self,
        setup: TAPredictionSetup,
        market_regime: Optional[str] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        dict_setup = self._typed_to_dict(setup)
        ctx = self.aggregator.build(
            symbol=setup.symbol,
            timeframe=setup.timeframe,
            setup=dict_setup,
            market_regime=market_regime,
        )
        result = ctx.to_dict()
        interaction = build_interaction_from_context(result)
        result["interaction"] = interaction.to_dict() if interaction else None
        adjusted_scenarios, adj_meta = apply_interaction_adjustment(
            result.get("scenarios") or [], result.get("interaction")
        )
        result["scenarios_original"] = result.get("scenarios") or []
        result["scenarios"] = adjusted_scenarios
        result["scenarios_adjustment"] = adj_meta
        # Step 7: calibration on top of Step 6. Persist off by default.
        apply_step7_postprocess(result, source="from-typed", persist=persist)
        return result

    # ------------------------------------------------------------------
    # Internal: bridge typed setup -> dict shape used by engines.
    # Honest mapping. Where typed input has nothing, dict shape has nothing.
    # ------------------------------------------------------------------
    @staticmethod
    def _typed_to_dict(s: TAPredictionSetup) -> Dict[str, Any]:
        # Momentum signals derived from RSI / MACD_hist (only if data present).
        signals: List[Dict[str, Any]] = []
        if s.rsi is not None:
            if s.rsi > 60:
                signals.append({
                    "direction": "bullish",
                    "weight": min((s.rsi - 60) / 40, 1.0),
                })
            elif s.rsi < 40:
                signals.append({
                    "direction": "bearish",
                    "weight": min((40 - s.rsi) / 40, 1.0),
                })
        if s.macd_hist is not None:
            if s.macd_hist > 0:
                signals.append({
                    "direction": "bullish",
                    "weight": min(abs(s.macd_hist), 1.0),
                })
            elif s.macd_hist < 0:
                signals.append({
                    "direction": "bearish",
                    "weight": min(abs(s.macd_hist), 1.0),
                })

        # Structure scores from a single signed trend_strength (-1..1).
        ts = max(-1.0, min(1.0, float(s.trend_strength or 0.0)))
        bullish_score = round(max(0.0, ts) * 100, 4)
        bearish_score = round(max(0.0, -ts) * 100, 4)

        # Patterns: pick highest-confidence as primary, the rest as alternatives.
        primary: Dict[str, Any] = {}
        alternatives: List[Dict[str, Any]] = []
        if s.patterns:
            sorted_p = sorted(
                s.patterns,
                key=lambda p: float(p.get("confidence", 0) or 0),
                reverse=True,
            )
            primary = dict(sorted_p[0])
            if "name" not in primary and "type" in primary:
                primary["name"] = primary["type"]
            alternatives = [dict(p) for p in sorted_p[1:]]

        # Volatility flags: explicit fields > volatility_state mapping.
        compression = bool(s.compression or s.volatility_state == "low")
        expansion = bool(s.expansion or s.volatility_state == "high")

        # Levels - only include the side we actually have.
        levels: Dict[str, Any] = {}
        if s.support is not None:
            levels["support"] = {"price": float(s.support)}
        if s.resistance is not None:
            levels["resistance"] = {"price": float(s.resistance)}

        return {
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "price": float(s.price),
            "current_price": float(s.price),
            "decision": {
                "bias": str(s.direction or "neutral"),
                "confidence": float(s.confidence or 0.0),
                "indicator_bias": str(s.direction or "neutral"),
            },
            "structure_context": {
                "structure_bias": str(s.direction or "neutral"),
                "metadata": {
                    "bullish_score": bullish_score,
                    "bearish_score": bearish_score,
                    "bos_count": 0,
                    "choch_count": 0,
                    "trend_strength": ts,
                    "structure_state": s.structure_state,
                },
            },
            "render_plan": {
                "structure": {
                    "state": s.structure_state,
                    "trend_strength": ts,
                },
                "patterns": {
                    "primary": primary,
                    "alternatives": alternatives,
                },
                "levels": levels,
            },
            "ta_context": {
                "indicators": {
                    "bias": str(s.direction or "neutral"),
                    "signals": signals,
                },
                "volatility": {
                    "compression": compression,
                    "expansion": expansion,
                    "atr_pct": s.atr_pct,
                    "state": s.volatility_state,
                },
            },
            "volatility": {
                "compression": compression,
                "expansion": expansion,
                "atr_pct": s.atr_pct,
                "state": s.volatility_state,
            },
            "_typed_setup": asdict(s),
        }
