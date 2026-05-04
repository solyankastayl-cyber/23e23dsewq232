"""
Market Regime Service (Phase 6 / P0)
====================================

Compute the market regime for a (symbol, timeframe) as an INDEPENDENT context
that sits beside `score_regime` (the band derived from meta strategy_score).

Architectural rules (locked by user spec):

  1. This service is READ-ONLY relative to TA / Prediction / Agreement.
     It MUST NOT modify:
        * ta.confidence
        * prediction.confidence
        * agreement.score
     It can only PRODUCE its own field:
        market_regime = {"label": ..., "confidence": ..., "model_name": ..., "raw": {...}}

  2. score_regime stays the universal TOXIC filter (band 0.50..0.70 → SKIP).
     market_regime ONLY routes policy. Adding it MUST NOT relax the
     existing `should_skip` ladder (LOW > score=0 > balanced).

  3. Detection is delegated to the ALREADY EXISTING, well-tested
     `modules/prediction/regime_detector.detect_regime()` so we do not
     duplicate logic. We feed it a clean TA shape derived from:
        * `modules/research_analytics/chart_data` (candles)
        * `modules/ta_engine/context_engine.build_market_context`
          (trend_strength / momentum / volatility / regime hint / structure)
        * `modules/research_analytics/patterns.PatternDetectionService`
          (best pattern type + confidence)

  4. Hysteresis: previous regime per (symbol, tf) is remembered IN-PROCESS
     so detect_regime's hysteresis branch is meaningful. Cache is a simple
     dict; no Mongo persistence — the regime is a derived view.

Output contract (stable):

    {
      "label":       "trend" | "range" | "compression" | "high_volatility",
      "confidence":  float in [0, 1],
      "model_name":  str,        # e.g. "trend_momentum_v1"
      "raw":         { "trend_strength": ..., "volatility_score": ...,
                        "momentum": ..., "structure_state": ...,
                        "structure_trend": ..., "pattern_type": ...,
                        "pattern_confidence": ..., "atr_pct": ... },
      "reason":      None | str  # set ONLY when label is None due to bad input
    }

If candles cannot be fetched or are too short, label is None and reason
explains why. In that case the meta pipeline should treat market_regime
as MISSING (not as "range") to avoid false attribution.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple


# In-process hysteresis cache.  Key: (SYMBOL, TIMEFRAME).  Value: last label.
_PREV_REGIME: Dict[Tuple[str, str], str] = {}


# ════════════════════════════════════════════════════════════════════════════
# Shape adapter — turn (context, pattern) into the TA dict regime_detector
# expects.  No magic, no mutation of source data.
# ════════════════════════════════════════════════════════════════════════════

# Discrete "low/mid/high" volatility from context_engine -> 0..1 scalar.
_VOL_TO_SCORE: Dict[str, float] = {"low": 0.20, "mid": 0.50, "high": 0.80}


def _structure_state_from_context(ctx: Dict[str, Any]) -> str:
    """
    Map context_engine.regime ∈ {trend, range, compression, volatile} +
    the sign of trend_strength → state expected by regime_detector
    ({trend_up, trend_down, trend, range, compression, accumulation, distribution}).
    """
    raw = ctx.get("_raw") or {}
    trend_strength = float(raw.get("trend_strength") or 0.0)
    regime_hint = ctx.get("regime")
    if regime_hint == "trend":
        if trend_strength > 0:
            return "trend_up"
        if trend_strength < 0:
            return "trend_down"
        return "trend"
    if regime_hint in ("range", "compression"):
        return regime_hint
    # context's "volatile" doesn't map to a structure state; default to range.
    return "range"


def _structure_trend_from_context(ctx: Dict[str, Any]) -> str:
    """
    Reduce context.structure ∈ {bullish, bearish, neutral} → trend hint
    expected by regime_detector ({up, down, flat}).
    """
    s = ctx.get("structure")
    if s == "bullish":
        return "up"
    if s == "bearish":
        return "down"
    return "flat"


def _best_pattern(patterns: Any) -> Tuple[Optional[str], float]:
    """
    Pick the pattern with the highest .confidence. Tolerates a list of
    DetectedPattern (pydantic) or dicts. Returns (type, confidence).
    """
    best_type: Optional[str] = None
    best_conf: float = 0.0
    if not patterns:
        return None, 0.0
    for p in patterns:
        try:
            t = getattr(p, "pattern_type", None)
            c = getattr(p, "confidence", None)
            if t is None and isinstance(p, dict):
                t = p.get("pattern_type")
                c = p.get("confidence")
            if t is None or c is None:
                continue
            cf = float(c)
            if cf > best_conf:
                best_conf = cf
                best_type = str(t)
        except Exception:
            continue
    return best_type, best_conf


def _build_detector_input(
    context: Dict[str, Any],
    pattern_type: Optional[str],
    pattern_conf: float,
) -> Dict[str, Any]:
    """
    Compose the dict shape that regime_detector.detect_regime() reads:
      ta = {
        "indicators": {trend_strength, volatility_score, momentum},
        "structure":  {state, trend},
        "pattern":    {type, confidence},
      }
    """
    raw = context.get("_raw") or {}
    vol_label = context.get("volatility")  # "low"|"mid"|"high"
    return {
        "indicators": {
            "trend_strength": float(raw.get("trend_strength") or 0.0),
            "volatility_score": _VOL_TO_SCORE.get(str(vol_label), 0.5),
            "momentum": float(raw.get("momentum") or 0.0),
        },
        "structure": {
            "state": _structure_state_from_context(context),
            "trend": _structure_trend_from_context(context),
        },
        "pattern": {
            "type": pattern_type or "none",
            "confidence": float(pattern_conf or 0.0),
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# Main entry point
# ════════════════════════════════════════════════════════════════════════════

async def compute_market_regime(
    symbol: str,
    timeframe: str,
    *,
    candles_limit: int = 200,
) -> Dict[str, Any]:
    """
    Compute the market regime for (symbol, timeframe).

    Steps (all best-effort; failure → label=None with `reason`):
      1. Fetch candles.
      2. Build market context (context_engine).
      3. Detect best pattern (pattern_service).
      4. Adapt → regime_detector input.
      5. detect_regime + get_regime_confidence (with hysteresis).

    Always returns a dict. Never raises.
    """
    sym_u = (symbol or "").upper().strip()
    tf_u = (timeframe or "").upper().strip()
    cache_key = (sym_u, tf_u)

    raw_payload: Dict[str, Any] = {}
    try:
        from modules.research_analytics.chart_data import get_chart_data_service
        from modules.research_analytics.patterns import get_pattern_service
        from modules.ta_engine.context_engine import build_market_context
        from modules.prediction.regime_detector import (
            detect_regime,
            get_regime_confidence,
            regime_to_model_name,
        )

        cd_service = get_chart_data_service()
        chart_data = await cd_service.get_chart_data(
            symbol=sym_u, timeframe=tf_u, limit=int(candles_limit)
        )
        candles = []
        if chart_data is not None:
            # `chart_data.candles` may be a list of pydantic candle objects
            # or already plain dicts depending on provider.
            raw_candles = getattr(chart_data, "candles", None) or []
            for c in raw_candles:
                if hasattr(c, "model_dump"):
                    candles.append(c.model_dump())
                elif isinstance(c, dict):
                    candles.append(c)
        if len(candles) < 20:
            return {
                "label": None,
                "confidence": 0.0,
                "model_name": None,
                "raw": {"candles_received": len(candles)},
                "reason": f"insufficient_candles ({len(candles)}<20)",
            }

        # Off-load CPU-bound build_market_context to a thread.
        context = await asyncio.to_thread(build_market_context, candles)
        # Pattern detection is also CPU-only.
        patterns = await asyncio.to_thread(
            get_pattern_service().detect_patterns, candles, sym_u, tf_u
        )
        pattern_type, pattern_conf = _best_pattern(patterns)

        ta_shape = _build_detector_input(context, pattern_type, pattern_conf)

        prev = _PREV_REGIME.get(cache_key)
        label = detect_regime(ta_shape, prev_regime=prev)
        confidence = float(get_regime_confidence(ta_shape, label))

        # Update hysteresis state ONLY on a successful detection.
        _PREV_REGIME[cache_key] = label

        raw_payload = {
            "trend_strength": ta_shape["indicators"]["trend_strength"],
            "volatility_score": ta_shape["indicators"]["volatility_score"],
            "momentum": ta_shape["indicators"]["momentum"],
            "structure_state": ta_shape["structure"]["state"],
            "structure_trend": ta_shape["structure"]["trend"],
            "pattern_type": ta_shape["pattern"]["type"],
            "pattern_confidence": ta_shape["pattern"]["confidence"],
            "atr_pct": (context.get("_raw") or {}).get("atr_pct"),
            "context_regime_hint": context.get("regime"),
            "context_volatility_label": context.get("volatility"),
            "prev_regime": prev,
        }

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "model_name": regime_to_model_name(label),
            "raw": raw_payload,
            "reason": None,
        }

    except Exception as exc:
        return {
            "label": None,
            "confidence": 0.0,
            "model_name": None,
            "raw": raw_payload,
            "reason": f"{type(exc).__name__}: {exc}",
        }


# ════════════════════════════════════════════════════════════════════════════
# Test helpers (kept tiny on purpose)
# ════════════════════════════════════════════════════════════════════════════

def _reset_hysteresis_for_tests() -> None:
    """Drop the in-process previous-regime cache."""
    _PREV_REGIME.clear()


def get_cached_prev_regimes() -> Dict[str, str]:
    """Read-only snapshot of the hysteresis cache for diagnostics."""
    return {f"{k[0]}:{k[1]}": v for k, v in _PREV_REGIME.items()}
