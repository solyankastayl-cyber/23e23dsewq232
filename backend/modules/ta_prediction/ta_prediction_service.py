"""
TA Prediction Service — Adapter for the shared Prediction Core.

Pipeline:
    TA layer (signal_explanation, indicators, structure)
        ↓
    map_ta_to_prediction_input()  ← THIS MODULE
        ↓
    PredictionInput
        ↓
    prediction_core.build_forecast()  ← shared math
        ↓
    Same UI contract as Exchange Prediction

Pass 2 honesty rules (HARD):
    * No fabricated confidence (no "if missing → 0.5")
    * No fabricated volatility (no "0.02 default") — adapter passes 0
      and core falls back to baseline_vol_for_tf(tf)
    * No mixing with sentiment / capital flow inside this adapter
    * If TA layer has nothing to say → emit NEUTRAL with confidence 0.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from modules.prediction_core import (
    PredictionInput,
    build_forecast,
    build_targets,
    build_single_forecast,
    default_horizon_for_tf,
)


# ════════════════════════════════════════════════════════════════════════════
# ADAPTER: TA → PredictionInput
# ════════════════════════════════════════════════════════════════════════════

def map_ta_to_prediction_input(
    ta_explanation: Optional[Dict[str, Any]],
    indicators_payload: Optional[Dict[str, Any]] = None,
    structure_payload: Optional[Dict[str, Any]] = None,
    *,
    horizon_days: int = 0,
    timeframe: str = "",
    candles: Optional[List[Dict[str, Any]]] = None,
) -> PredictionInput:
    """
    Convert TA Engine signals → normalized PredictionInput.

    Inputs (any may be None — adapter is honest):
      ta_explanation     : output of /api/v1/signal/explanation/{symbol}/{tf}
      indicators_payload : output of /api/ta/indicators/{symbol}/{tf}
      structure_payload  : output of /api/ta/structure/{symbol}/{tf}
      candles            : raw OHLCV (used ONLY for vol estimation)
      timeframe          : canonical TF tag — pass-through to core for baseline math

    HONESTY:
      * If TA has no confidence → confidence = 0.0 (NOT 0.5)
      * If candles are missing → volatility = 0.0 (NOT 0.02)
        Core will substitute baseline_vol_for_tf(tf) when it sees 0.
      * Direction "neutral" is preserved as-is (no upgrading to LONG/SHORT
        on the basis of indicator counts / structure score).
    """
    e = ta_explanation or {}
    ind = indicators_payload or {}
    structure = structure_payload or {}

    # ─── DIRECTION (bullish/bearish/neutral → LONG/SHORT/NEUTRAL) ───────────
    # Single source of truth: the explanation. We do NOT override neutral
    # with indicators/structure bias — that would be exactly the kind of
    # silent fabrication Pass 2 forbids.
    direction_raw = e.get("direction")
    if not direction_raw:
        # No explanation → NEUTRAL (honest "I don't know")
        direction_raw = "neutral"
    direction = _to_canonical(direction_raw)

    # ─── CONFIDENCE (0..1, honest) ────────────────────────────────────────
    confidence_raw = e.get("confidence")
    confidence = _coerce_unit(confidence_raw) if confidence_raw is not None else 0.0
    # NO fallback synthesis from indicator counts — that's fabrication.

    # ─── STRENGTH (confluence_score from real explanation breakdown) ──────
    strength = 0.0
    cb = e.get("confidence_breakdown") or {}
    if cb:
        contribs = [v for k, v in cb.items() if k.endswith("_contribution") and isinstance(v, (int, float))]
        if contribs:
            # Average × 2 because individual contributions are typically 0..0.5
            strength = _coerce_unit(sum(contribs) / len(contribs) * 2.0)
    # If breakdown is empty → strength stays 0.0 (honest "no confluence info")

    # ─── VOLATILITY (real σ from candles, or 0 to let core use TF baseline) ─
    volatility = _estimate_volatility(candles) if candles else 0.0

    # ─── DRIVERS (top contributors for transparency) ──────────────────────
    drivers: Dict[str, float] = {}
    for key, val in (cb or {}).items():
        if key.endswith("_contribution") and isinstance(val, (int, float)) and val:
            drivers[key.replace("_contribution", "")] = round(float(val), 4)

    # If horizon_days not provided → derive from tf via core helper
    h_days = int(horizon_days) if horizon_days and horizon_days > 0 else (
        default_horizon_for_tf(timeframe) if timeframe else 7
    )

    return PredictionInput(
        direction=direction,
        confidence=confidence,
        strength=strength,
        volatility=volatility,
        horizon_days=h_days,
        timeframe=(timeframe or "").upper(),
        drivers=drivers,
    )


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════════════════

async def build_ta_prediction(
    symbol: str,
    timeframe: str,
    horizon: str = "7D",
    *,
    asset: str = "BTC",
) -> Dict[str, Any]:
    """
    End-to-end TA prediction (graph4 contract).

    1. Fetch TA signal explanation
    2. Fetch indicators
    3. Fetch structure
    4. Fetch candles (current price + history)
    5. Adapter → PredictionInput
    6. Core → forecast
    """
    horizon_days = _horizon_to_days(horizon)
    explanation = await _safe_get_explanation(symbol, timeframe)
    indicators = await _safe_get_indicators(symbol, timeframe)
    structure = await _safe_get_structure(symbol, timeframe)
    candles = _safe_get_candles(symbol, timeframe, limit=180 + horizon_days * 6)

    current_price = _extract_current_price(candles)

    inp = map_ta_to_prediction_input(
        ta_explanation=explanation,
        indicators_payload=indicators,
        structure_payload=structure,
        horizon_days=horizon_days,
        timeframe=timeframe,
        candles=candles,
    )

    result = build_forecast(
        inp,
        current_price=current_price,
        history=candles,
        asset=asset,
        horizon_label=horizon,
        timeframe=timeframe,
    )
    # Attach raw TA telemetry under _ta for transparency / debugging
    result["_ta"] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "explanation_summary": (explanation or {}).get("summary"),
        "explanation_strength": (explanation or {}).get("strength"),
        "indicator_bias": (indicators or {}).get("indicator_bias"),
        "structure_bias": (structure or {}).get("structure_bias"),
        "has_explanation": explanation is not None,
        "has_indicators": indicators is not None,
        "has_structure": structure is not None,
    }
    return result


async def build_ta_targets(
    symbol: str,
    timeframe: str,
    *,
    asset: str = "BTC",
) -> Dict[str, Any]:
    """Multi-horizon targets (24H / 7D / 30D)."""
    explanation = await _safe_get_explanation(symbol, timeframe)
    indicators = await _safe_get_indicators(symbol, timeframe)
    structure = await _safe_get_structure(symbol, timeframe)
    candles = _safe_get_candles(symbol, timeframe, limit=180)
    current_price = _extract_current_price(candles)

    inp = map_ta_to_prediction_input(
        ta_explanation=explanation,
        indicators_payload=indicators,
        structure_payload=structure,
        timeframe=timeframe,
        candles=candles,
    )
    return build_targets(inp, current_price=current_price, asset=asset, timeframe=timeframe)


async def build_ta_single_forecast(
    symbol: str,
    timeframe: str,
) -> Dict[str, Any]:
    """
    Pass 2 spec-compliant single-TF forecast.

    Returns:
      {
        "symbol": "BTCUSDT",
        "timeframe": "4H",
        "direction": "bullish"|"bearish"|"neutral",
        "confidence": 0..1,
        "forecast": [{"ts": ms, "price": ...}, ...],
        "targets": {"expected_move_pct", "target_price", "max_upside", "max_drawdown"},
        "timestamp": ISO-8601 UTC,
        "_meta": {direction, confidence, volatility, drift_d, weak, ...},
        "_ta": {summary, strength, has_*}    # adapter telemetry
      }

    Honest properties:
      * No fabricated confidence / volatility.
      * NEUTRAL or weak signal → flat-with-noise forecast.
      * targets.target_price == forecast[-1].price (consistency).
      * Same input ⇒ same output, every render.
    """
    explanation = await _safe_get_explanation(symbol, timeframe)
    indicators = await _safe_get_indicators(symbol, timeframe)
    structure = await _safe_get_structure(symbol, timeframe)
    candles = _safe_get_candles(symbol, timeframe, limit=240)
    current_price = _extract_current_price(candles)

    inp = map_ta_to_prediction_input(
        ta_explanation=explanation,
        indicators_payload=indicators,
        structure_payload=structure,
        timeframe=timeframe,
        candles=candles,
    )

    result = build_single_forecast(
        inp,
        current_price=current_price,
        history=candles,
        symbol=symbol,
        timeframe=timeframe,
    )
    result["_ta"] = {
        "summary": (explanation or {}).get("summary"),
        "strength": (explanation or {}).get("strength"),
        "indicator_bias": (indicators or {}).get("indicator_bias"),
        "structure_bias": (structure or {}).get("structure_bias"),
        "has_explanation": explanation is not None,
        "has_indicators": indicators is not None,
        "has_structure": structure is not None,
    }
    return result


def get_live_price(symbol: str, timeframe: str = "1H") -> Dict[str, Any]:
    """Latest price helper for the live-price polling endpoint."""
    candles = _safe_get_candles(symbol, timeframe, limit=2)
    price = _extract_current_price(candles)
    return {"ok": price > 0, "asset": symbol.replace("USDT", "").upper(), "price": price}


# ════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _to_canonical(direction_raw: str) -> str:
    d = (direction_raw or "").lower()
    if d in ("long", "up", "bullish", "bull"):
        return "LONG"
    if d in ("short", "down", "bearish", "bear"):
        return "SHORT"
    return "NEUTRAL"


def _coerce_unit(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, x))


def _horizon_to_days(h: str) -> int:
    s = (h or "").upper()
    return {"1D": 1, "24H": 1, "7D": 7, "30D": 30}.get(s, 7)


def _extract_current_price(candles: Optional[List[Dict[str, Any]]]) -> float:
    if not candles:
        return 0.0
    last = candles[-1]
    for k in ("close", "price", "c"):
        if k in last and last[k] is not None:
            try:
                return float(last[k])
            except (TypeError, ValueError):
                pass
    return 0.0


def _estimate_volatility(candles: List[Dict[str, Any]], window: int = 30) -> float:
    """
    Real σ of % returns from candles (daily-ish volatility estimate).

    Returns 0.0 if not enough data — core treats 0 as "use TF baseline".
    No magic 0.02 default leaks through.
    """
    if not candles or len(candles) < 5:
        return 0.0
    sub = candles[-window:] if len(candles) > window else candles
    closes = [c.get("close") for c in sub if c.get("close")]
    if len(closes) < 3:
        return 0.0
    rets = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)) if closes[i-1]]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
    sd = var ** 0.5
    # clamp to reasonable bounds (lower bound 0 → no fabrication)
    return max(0.0, min(0.15, sd))


# ─── network/data fetchers (kept lazy and resilient) ────────────────────

async def _safe_get_explanation(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Build a TA hypothesis from real chart_data + pattern + fractal services and
    feed it into the signal explainer. NO fabricated alpha/regime scores.

    If the explainer would otherwise need numeric breakdown fields and we don't
    have real ones, we pass 0.0 — never 0.5/0.6 placeholders. The downstream
    adapter treats 0.0 as "no info" (honest).
    """
    try:
        from modules.signal_explanation.explainer import get_signal_explainer
        from modules.research_analytics.chart_data import get_chart_data_service
        from modules.research_analytics.patterns import get_pattern_service
        from modules.research_analytics.hypothesis_viz import get_hypothesis_viz_service
        from modules.research_analytics.fractal_viz import get_fractal_viz_service

        chart_data = await get_chart_data_service().get_chart_data(symbol=symbol.upper(), timeframe=timeframe, limit=300)
        hyp = get_hypothesis_viz_service().build_hypothesis_visualization(chart_data.candles, symbol, timeframe)
        patterns = get_pattern_service().detect_patterns(chart_data.candles, symbol, timeframe)
        fractal_result = get_fractal_viz_service().find_fractal_matches(chart_data.candles, symbol, timeframe)

        # HONEST hyp_dict: only fields that come from real services.
        # alpha/regime/microstructure/capital_flow scores are NOT computed by
        # the TA layer — leave them at 0 so the explainer cannot synthesize
        # fake confluence out of placeholders.
        hyp_dict = {
            "hypothesis_id": hyp.hypothesis_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": hyp.direction,
            "confidence": hyp.confidence,           # real, from hypothesis_viz
            "alpha_score": 0.0,
            "regime_score": 0.0,
            "microstructure_score": 0.0,
            "capital_flow_score": 0.0,
            "fractal_similarity_score": (
                fractal_result.matches[0].similarity if fractal_result.matches else 0.0
            ),
            "alpha_sources": [],
        }
        explanation = get_signal_explainer().explain_hypothesis(
            hypothesis=hyp_dict,
            patterns=[p.model_dump() for p in patterns],
            fractal_matches=[m.model_dump() for m in fractal_result.matches],
        )
        return explanation.model_dump()
    except Exception as exc:
        print(f"[TAPrediction] explanation fetch failed: {exc}")
        return None


async def _safe_get_indicators(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    try:
        from modules.ta_engine.setup.indicator_engine import get_indicator_engine
        engine = get_indicator_engine()
        candles = _safe_get_candles(symbol, timeframe, limit=200)
        if not candles or len(candles) < 50:
            return None
        result = engine.analyze_all(candles)
        # Normalize: analyze_all may return a list of indicator signals.
        # Convert to {bullish_signals, bearish_signals, indicator_bias} shape.
        if isinstance(result, list):
            bull = [s for s in result if _direction_str(s) == "bullish"]
            bear = [s for s in result if _direction_str(s) == "bearish"]
            bias = "bullish" if len(bull) > len(bear) else "bearish" if len(bear) > len(bull) else "neutral"
            return {
                "indicator_bias": bias,
                "bullish_signals": [_signal_to_dict(s) for s in bull],
                "bearish_signals": [_signal_to_dict(s) for s in bear],
            }
        if isinstance(result, dict):
            return result
        return None
    except Exception as exc:
        print(f"[TAPrediction] indicators fetch failed: {exc}")
        return None


def _direction_str(sig) -> str:
    """Extract direction string from a signal object/dict."""
    if isinstance(sig, dict):
        d = sig.get("direction") or sig.get("bias") or ""
    else:
        d = getattr(sig, "direction", None)
        d = getattr(d, "value", d) if d is not None else ""
    return str(d).lower() if d else ""


def _signal_to_dict(sig) -> Dict[str, Any]:
    if isinstance(sig, dict):
        return sig
    out = {}
    for attr in ("name", "direction", "strength", "value"):
        v = getattr(sig, attr, None)
        if v is not None:
            out[attr] = getattr(v, "value", v)
    return out


async def _safe_get_structure(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    try:
        from modules.ta_engine.setup.structure_engine import get_structure_engine
        engine = get_structure_engine()
        candles = _safe_get_candles(symbol, timeframe, limit=200)
        if not candles or len(candles) < 20:
            return None
        out = engine.analyze_all(candles)
        # analyze_all signature differs across versions — normalize.
        if isinstance(out, dict):
            return out
        if isinstance(out, tuple):
            structure_points, bias, metadata = out[0], out[1], (out[2] if len(out) > 2 else {})
            return {
                "structure_bias": getattr(bias, "value", str(bias)),
                "metadata": metadata or {},
                "all_points": [_safe_dict(p) for p in (structure_points or [])],
            }
        return None
    except Exception as exc:
        print(f"[TAPrediction] structure fetch failed: {exc}")
        return None


def _safe_dict(p) -> Dict[str, Any]:
    if isinstance(p, dict):
        return p
    if hasattr(p, "to_dict"):
        try:
            return p.to_dict()
        except Exception:
            pass
    if hasattr(p, "model_dump"):
        try:
            return p.model_dump()
        except Exception:
            pass
    return {"_repr": str(p)}


def _safe_get_candles(symbol: str, timeframe: str, limit: int = 200) -> List[Dict[str, Any]]:
    try:
        from modules.ta_engine.setup.market_data_service import get_market_data_service
        service = get_market_data_service()
        return service.get_candles(symbol, timeframe, limit=limit) or []
    except Exception as exc:
        print(f"[TAPrediction] candles fetch failed: {exc}")
        return []
