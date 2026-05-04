"""
Live TA Adapter (Phase 6 / P2 — Step 2)
========================================

Pulls a current TA setup directly from the platform's existing services and
maps it into a `TAPredictionSetup`. Then runs it through the 5 engines via
`TAPredictionService.build_from_typed_setup`.

ARCHITECTURAL CONTRACT:
  * This adapter LIVES INSIDE the ta_prediction_intelligence module. It is
    the only piece allowed to TOUCH external services from this module.
  * It is READ-ONLY relative to those services. It must never mutate
    chart_data, context_engine output, indicators, or pattern detection.
  * If a data source is missing or fails, the corresponding TAPredictionSetup
    field stays at its honest default (None / 0 / empty list). Engines then
    naturally produce confidence=0 for that branch (Pass-2 honesty).
  * No interaction with combined_analysis, meta_pipeline, policy_registry,
    shadow_logger.

Data sources (live):
  candles                 ←  modules.research_analytics.chart_data
  context (trend / vol)   ←  modules.ta_engine.context_engine
  RSI(14), MACD(12,26,9)  ←  modules.research_analytics.indicators
  patterns                ←  modules.research_analytics.patterns (PatternService)
  support / resistance    ←  modules.research_analytics.patterns
                              .detect_support_resistance

Output: dict (TAPredictionContext.to_dict()).
"""

from __future__ import annotations

import asyncio
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .ta_prediction_service import TAPredictionService
from .types import TAPredictionSetup
from .engine_interactions import build_interaction_from_context
from .scenarios.scenario_interaction_adjuster import apply_interaction_adjustment
from .step7_pipeline import apply_step7_postprocess


# ════════════════════════════════════════════════════════════════════════════
# Pipeline-Integrity helpers (FIX PIPELINE)
# ────────────────────────────────────────────────────────────────────────────
# Single source of truth for "what is the last CLOSED candle" and "what is
# its close_time as a Unix-seconds integer". These two pieces of data anchor:
#   * entry_price                (used for outcome evaluation)
#   * candle_close_ts            (uniqueness key for ta_prediction_history)
#   * feature_hash                (must be stable for the same anchor)
#   * temporal buffer dedup
# ════════════════════════════════════════════════════════════════════════════

# Timeframe → minutes. Keep aligned with chart_data._generate_mock_candles map.
_TF_TO_MINUTES: Dict[str, int] = {
    "1M": 1, "5M": 5, "15M": 15, "30M": 30,
    "1H": 60, "2H": 120, "4H": 240, "6H": 360, "8H": 480, "12H": 720,
    "1D": 1440, "3D": 4320, "1W": 10080,
}


def _tf_minutes(tf: str) -> int:
    return _TF_TO_MINUTES.get((tf or "").upper().strip(), 60)


def _candle_open_ts_seconds(candle: Dict[str, Any]) -> Optional[int]:
    """Parse a candle's OPEN time into integer unix seconds (UTC).

    Accepts ISO string, datetime, ms-int, or sec-int. Returns None if unparseable.
    """
    if not candle:
        return None
    ts = candle.get("timestamp") or candle.get("open_time") or candle.get("time")
    if ts is None:
        return None
    try:
        if isinstance(ts, datetime):
            dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        if isinstance(ts, (int, float)):
            v = int(ts)
            # ms vs s heuristic
            return v // 1000 if v > 10**12 else v
        s = str(ts).strip()
        if not s:
            return None
        # numeric string?
        try:
            v = int(s)
            return v // 1000 if v > 10**12 else v
        except ValueError:
            pass
        # ISO string (allow trailing Z)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


def _candle_close_ts_seconds(candle: Dict[str, Any], tf: str) -> Optional[int]:
    """Compute candle CLOSE time = open_ts + tf_minutes*60. None on failure."""
    open_s = _candle_open_ts_seconds(candle)
    if open_s is None:
        return None
    return int(open_s + _tf_minutes(tf) * 60)


def _select_anchor_candles(
    candles: List[Dict[str, Any]], tf: str, *, now_seconds: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int]]:
    """
    Strip any trailing candle whose close_time has not yet occurred. Return:

        (closed_candles, anchor_candle, anchor_close_ts)

    `anchor_candle` is the LAST closed candle and is the single source of
    truth for entry_price / candle_close_ts. If everything is forming,
    returns ([], None, None).
    """
    if not candles:
        return [], None, None
    nows = int(now_seconds if now_seconds is not None else _time.time())
    out: List[Dict[str, Any]] = []
    for c in candles:
        cct = _candle_close_ts_seconds(c, tf)
        if cct is None:
            continue
        if cct > nows:
            # forming candle — exclude
            continue
        out.append(c)
    if not out:
        return [], None, None
    anchor = out[-1]
    return out, anchor, _candle_close_ts_seconds(anchor, tf)


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

# Map context_engine.regime → TAPredictionSetup.structure_state vocabulary.
_CTX_REGIME_TO_STATE: Dict[str, str] = {
    "trend": "trend",
    "range": "range",
    "compression": "compression",
    "volatile": "high_volatility",
}

# Map context_engine.volatility ("low"/"mid"/"high") → volatility_state vocab.
_CTX_VOL_TO_STATE: Dict[str, str] = {
    "low": "low",
    "mid": "normal",
    "high": "high",
}


def _last_close(candles: List[Dict[str, Any]]) -> Optional[float]:
    if not candles:
        return None
    last = candles[-1]
    try:
        return float(last.get("close"))
    except Exception:
        return None


def _fetch_indicator_last_value(
    indicator_name: str, candles: List[Dict[str, Any]], **params
) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (value, extra_field). Used to extract last RSI value and last
    MACD histogram value. Returns (None, None) on any failure.
    """
    try:
        from modules.research_analytics.indicators import get_indicator_service

        service = get_indicator_service()
        series = service.calculate_indicator(indicator_name, candles, **params)
        if not series or not series.values:
            return None, None
        last = series.values[-1]
        value = float(last.value) if last.value is not None else None
        extra = last.extra or {}
        # Normalise: for RSI we want the value; for MACD we want histogram.
        # MACD's IndicatorValue.value IS the histogram (see indicators.py:309).
        return value, extra.get("macd")
    except Exception:
        return None, None


def _fetch_indicator_full_series(
    indicator_name: str, candles: List[Dict[str, Any]], **params
) -> List[Dict[str, Any]]:
    """
    Returns the full indicator series as a list of {ts, value, extra} dicts.
    Returns [] on any failure. Used by production engines that need slope
    / divergence / persistence calculations.
    """
    try:
        from modules.research_analytics.indicators import get_indicator_service

        service = get_indicator_service()
        series = service.calculate_indicator(indicator_name, candles, **params)
        if not series or not series.values:
            return []
        return [
            {
                "ts": v.timestamp,
                "value": float(v.value) if v.value is not None else None,
                "extra": v.extra or {},
            }
            for v in series.values
        ]
    except Exception:
        return []


def _compute_pivots(
    candles: List[Dict[str, Any]], window: int = 5
) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Build (pivot_highs, pivot_lows) where each is a list of (index, price).
    Reuses pattern_service._find_pivots so we don't duplicate logic.
    """
    if len(candles) < 2 * window + 1:
        return [], []
    try:
        from modules.research_analytics.patterns import get_pattern_service

        ps = get_pattern_service()
        highs = [float(c.get("high")) for c in candles]
        lows = [float(c.get("low")) for c in candles]
        ph_flags = ps._find_pivots(highs, is_high=True, window=window)
        pl_flags = ps._find_pivots(lows, is_high=False, window=window)
        ph = [(i, highs[i]) for i, ok in enumerate(ph_flags) if ok]
        pl = [(i, lows[i]) for i, ok in enumerate(pl_flags) if ok]
        return ph, pl
    except Exception:
        return [], []


def _fetch_patterns_and_levels(
    candles: List[Dict[str, Any]], symbol: str, timeframe: str, current_price: float
) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float]]:
    """
    Returns (patterns_list, nearest_support, nearest_resistance).
    Each element fully nullable on failure.
    """
    patterns_out: List[Dict[str, Any]] = []
    support: Optional[float] = None
    resistance: Optional[float] = None
    try:
        from modules.research_analytics.patterns import get_pattern_service

        ps = get_pattern_service()

        # Patterns
        try:
            detected = ps.detect_patterns(candles, symbol, timeframe) or []
            for p in detected:
                # `p` is DetectedPattern (pydantic). Convert to dict the
                # ta_prediction engines expect.
                pname = getattr(p, "pattern_type", None) or getattr(p, "name", None)
                pconf = getattr(p, "confidence", None)
                pdir = getattr(p, "direction", None)
                plife = getattr(p, "lifecycle", None) or getattr(p, "status", None)
                if pname is None or pconf is None:
                    continue
                patterns_out.append({
                    "name": str(pname),
                    "type": str(pname),
                    "direction": str(pdir or "neutral"),
                    "confidence": float(pconf),
                    "lifecycle": str(plife or ""),
                })
        except Exception:
            patterns_out = []

        # Support / resistance — pick nearest on each side.
        try:
            levels = ps.detect_support_resistance(candles) or []
            sup_candidates: List[float] = []
            res_candidates: List[float] = []
            for lvl in levels:
                ltype = getattr(lvl, "type", None)
                lprice = getattr(lvl, "price", None)
                if ltype is None or lprice is None:
                    continue
                lprice = float(lprice)
                if ltype == "support" and lprice < current_price:
                    sup_candidates.append(lprice)
                elif ltype == "resistance" and lprice > current_price:
                    res_candidates.append(lprice)
            if sup_candidates:
                support = max(sup_candidates)  # nearest below
            if res_candidates:
                resistance = min(res_candidates)  # nearest above
        except Exception:
            pass
    except Exception:
        pass
    return patterns_out, support, resistance


def _build_context(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap context_engine; return {} on failure."""
    try:
        from modules.ta_engine.context_engine import build_market_context

        return build_market_context(candles) or {}
    except Exception:
        return {}


def _direction_from_trend(ts: float, threshold: float = 0.2) -> str:
    if ts >= threshold:
        return "bullish"
    if ts <= -threshold:
        return "bearish"
    return "neutral"


# ════════════════════════════════════════════════════════════════════════════
# Public entry point
# ════════════════════════════════════════════════════════════════════════════


async def fetch_live_context(
    symbol: str,
    timeframe: str,
    *,
    candles_limit: int = 200,
    market_regime: Optional[str] = None,
    historical_candles: Optional[List[Dict[str, Any]]] = None,
    as_of_candle_index: Optional[int] = None,
    source: str = "live",
    persist_predictions: bool = True,
) -> Dict[str, Any]:
    """
    Build a TAPredictionContext for (symbol, timeframe).

    LIVE PATH (default):
        Pulls the most recent candles from chart_data and anchors on the last
        CLOSED bar.

    SIMULATION PATH (when both historical_candles and as_of_candle_index
    are supplied):
        Uses ONLY historical_candles[: as_of_candle_index + 1]. No live tape,
        no now()-derived data, no chart_data call. The returned `_live.source`
        will be "simulation" and the result must be persisted via the
        simulation repository (NEVER the live one).

    The function NEVER raises. On any partial failure it produces a
    TAPredictionSetup with honest defaults so engines self-disable.

    Returns the same shape as TAPredictionContext.to_dict() plus a `_live`
    block with diagnostics including `source`.
    """
    sym_u = (symbol or "").upper().strip()
    tf_u = (timeframe or "").upper().strip()
    src = (source or "live").lower().strip()
    is_simulation = (
        src == "simulation"
        and historical_candles is not None
        and as_of_candle_index is not None
    )

    completeness: Dict[str, bool] = {
        "candles": False,
        "price": False,
        "trend_strength": False,
        "structure_state": False,
        "volatility_state": False,
        "rsi": False,
        "macd_hist": False,
        "support": False,
        "resistance": False,
        "patterns": False,
    }
    indicator_failures: List[str] = []

    # ── 1. Candles ──────────────────────────────────────────────────────────
    candles: List[Dict[str, Any]] = []
    if is_simulation:
        # SIMULATION PATH: use only historical_candles[: as_of_candle_index + 1].
        # No chart_data call. No now()-derived information leaks.
        try:
            idx = int(as_of_candle_index)
            if idx < 0 or idx >= len(historical_candles or []):
                raise ValueError(f"as_of_candle_index out of range: {idx}")
            for c in historical_candles[: idx + 1]:
                if hasattr(c, "model_dump"):
                    candles.append(c.model_dump())
                elif isinstance(c, dict):
                    candles.append(dict(c))
            completeness["candles"] = len(candles) >= 20
        except Exception as exc:
            indicator_failures.append(f"sim_candles:{type(exc).__name__}")
    else:
        try:
            from modules.research_analytics.chart_data import get_chart_data_service

            cd_service = get_chart_data_service()
            chart_data = await cd_service.get_chart_data(
                symbol=sym_u, timeframe=tf_u, limit=int(candles_limit)
            )
            raw_candles = getattr(chart_data, "candles", None) or []
            for c in raw_candles:
                if hasattr(c, "model_dump"):
                    candles.append(c.model_dump())
                elif isinstance(c, dict):
                    candles.append(c)
            completeness["candles"] = len(candles) >= 20
        except Exception as exc:
            indicator_failures.append(f"chart_data:{type(exc).__name__}")

    # ── 1b. Anchor on the last CLOSED candle (FIX PIPELINE bug #1+#2). ──────
    # Drop any forming candle so all downstream features hash deterministically
    # and entry_price / candle_close_ts come from a frozen bar.
    #
    # SIMULATION PATH: every candle in historical_candles[:idx+1] is treated
    # as fully closed. The anchor is the candle at as_of_candle_index. We
    # simulate "now" by passing a sentinel = last_close_ts + 1 so the anchor
    # selector keeps every bar.
    if is_simulation and candles:
        last_cct = _candle_close_ts_seconds(candles[-1], tf_u)
        sim_now = (int(last_cct) + 1) if last_cct is not None else None
        candles, anchor_candle, anchor_close_ts = _select_anchor_candles(
            candles, tf_u, now_seconds=sim_now
        )
    else:
        candles, anchor_candle, anchor_close_ts = _select_anchor_candles(
            candles, tf_u
        )
    completeness["candles"] = len(candles) >= 20

    price = float(anchor_candle["close"]) if anchor_candle is not None else None
    completeness["price"] = price is not None

    if not candles or price is None or anchor_candle is None:
        # Cannot do anything meaningful. Return empty context.
        empty_setup = TAPredictionSetup(
            symbol=sym_u, timeframe=tf_u, price=price or 0.0
        )
        # Run the typed path WITHOUT persisting (synthetic / empty result) —
        # step7 will be invoked manually below with `persist=True` so we still
        # log that a live call happened even though data was missing.
        result = TAPredictionService().build_from_typed_setup(
            empty_setup, market_regime=market_regime, persist=False
        )
        # Strip fields written by the inner step7 call so we can re-apply with
        # persist=True below. The interaction+interaction adjustment blocks
        # are cheap to recompute and harmless to keep.
        result.pop("scenarios_calibration", None)
        result.pop("scenarios_pre_calibration", None)
        result.pop("prediction_id", None)
        result["_live"] = {
            "candles_received": len(candles),
            "data_completeness": completeness,
            "context_regime_hint": None,
            "context_volatility_label": None,
            "indicator_failures": indicator_failures,
            "last_close": price,
            "last_candle_close_ts": anchor_close_ts,
            "anchor_candle_open_ts": _candle_open_ts_seconds(anchor_candle) if anchor_candle else None,
            "tf_minutes": _tf_minutes(tf_u),
            "source": src,
            "as_of_candle_index": int(as_of_candle_index) if is_simulation else None,
        }
        # Interaction layer (read-only on top of context). Empty branch -> None.
        interaction = build_interaction_from_context(result)
        result["interaction"] = interaction.to_dict() if interaction else None
        # Step 6: interaction-aware scenario adjustment (post-processing only).
        adjusted_scenarios, adj_meta = apply_interaction_adjustment(
            result.get("scenarios") or [], result.get("interaction")
        )
        result["scenarios_original"] = result.get("scenarios") or []
        result["scenarios"] = adjusted_scenarios
        result["scenarios_adjustment"] = adj_meta
        # Step 7: calibration on top of Step 6 + persist prediction (audit).
        apply_step7_postprocess(result, source=src, persist=bool(persist_predictions))
        return result

    # ── 2. Context (trend_strength / momentum / volatility / regime) ────────
    context = await asyncio.to_thread(_build_context, candles)
    raw_ctx = (context.get("_raw") or {}) if isinstance(context, dict) else {}
    trend_strength = float(raw_ctx.get("trend_strength") or 0.0)
    atr_pct = raw_ctx.get("atr_pct")
    ctx_regime = context.get("regime") if isinstance(context, dict) else None
    ctx_vol = context.get("volatility") if isinstance(context, dict) else None
    structure_state = _CTX_REGIME_TO_STATE.get(str(ctx_regime), "range")
    volatility_state = _CTX_VOL_TO_STATE.get(str(ctx_vol), "normal")
    completeness["trend_strength"] = bool(raw_ctx.get("trend_strength") is not None)
    completeness["structure_state"] = ctx_regime is not None
    completeness["volatility_state"] = ctx_vol is not None

    # ── 3. RSI(14), MACD(12,26,9) — last value AND full series ──────────────
    rsi_value, _ = await asyncio.to_thread(
        _fetch_indicator_last_value, "rsi", candles, period=14
    )
    if rsi_value is None:
        indicator_failures.append("rsi")
    else:
        completeness["rsi"] = True

    # MACD: indicators._calculate_macd stores histogram as IndicatorValue.value;
    # extra["macd"] is the MACD line. We want the histogram (momentum proxy).
    macd_hist, _ = await asyncio.to_thread(
        _fetch_indicator_last_value, "macd", candles
    )
    if macd_hist is None:
        indicator_failures.append("macd_hist")
    else:
        completeness["macd_hist"] = True

    # Production engines (Step 3) need full series + pivots.
    rsi_series = await asyncio.to_thread(
        _fetch_indicator_full_series, "rsi", candles, period=14
    )
    macd_series = await asyncio.to_thread(
        _fetch_indicator_full_series, "macd", candles
    )
    pivot_highs, pivot_lows = await asyncio.to_thread(_compute_pivots, candles, 5)

    # ── 4. Patterns + support / resistance ──────────────────────────────────
    patterns_list, support, resistance = await asyncio.to_thread(
        _fetch_patterns_and_levels, candles, sym_u, tf_u, price
    )
    completeness["patterns"] = len(patterns_list) > 0
    completeness["support"] = support is not None
    completeness["resistance"] = resistance is not None

    # ── 5. Compose typed setup ──────────────────────────────────────────────
    direction = _direction_from_trend(trend_strength)
    confidence = min(1.0, abs(trend_strength))  # honest: 0..|trend|
    setup = TAPredictionSetup(
        symbol=sym_u,
        timeframe=tf_u,
        price=float(price),
        direction=direction,
        confidence=confidence,
        strength=confidence,
        trend_strength=trend_strength,
        structure_state=structure_state,
        rsi=rsi_value,
        macd_hist=macd_hist,
        support=support,
        resistance=resistance,
        atr_pct=float(atr_pct) if atr_pct is not None else None,
        volatility_state=volatility_state,
        patterns=patterns_list,
        compression=(structure_state == "compression"),
        expansion=(volatility_state == "high"),
    )

    # ── 6. Run through engines / resolver / aggregator / scenarios ──────────
    # Instead of going via build_from_typed_setup() we manually build the dict
    # so we can inject `_raw_data` (production-grade engine inputs) alongside
    # the standard summary fields. The typed adapter is used to assemble the
    # base dict (back-compat), and then we enrich.
    service = TAPredictionService()
    base_dict = TAPredictionService._typed_to_dict(setup)
    base_dict["_raw_data"] = {
        "candles": candles,
        "rsi_series": rsi_series,
        "macd_series": macd_series,
        "pivot_highs": pivot_highs,
        "pivot_lows": pivot_lows,
        "current_price": float(price),
        "atr_pct": float(atr_pct) if atr_pct is not None else None,
        "context_regime_hint": ctx_regime,
        "context_volatility_label": ctx_vol,
    }
    ctx = service.aggregator.build(
        symbol=sym_u,
        timeframe=tf_u,
        setup=base_dict,
        market_regime=market_regime,
    )
    result = ctx.to_dict()
    # Anchor metadata is derived from the LAST CLOSED candle (FIX PIPELINE).
    last_ts = anchor_close_ts
    result["_live"] = {
        "candles_received": len(candles),
        "data_completeness": completeness,
        "context_regime_hint": ctx_regime,
        "context_volatility_label": ctx_vol,
        "indicator_failures": indicator_failures,
        "production_engines_armed": True,
        "last_close": float(price),
        "last_candle_close_ts": last_ts,
        "anchor_candle_open_ts": _candle_open_ts_seconds(anchor_candle),
        "tf_minutes": _tf_minutes(tf_u),
        "source": src,
        "as_of_candle_index": int(as_of_candle_index) if is_simulation else None,
    }
    # Interaction layer (read-only on top of context). May be None if no rule matches.
    interaction = build_interaction_from_context(result)
    result["interaction"] = interaction.to_dict() if interaction else None
    # Step 6: interaction-aware scenario adjustment (post-processing only).
    adjusted_scenarios, adj_meta = apply_interaction_adjustment(
        result.get("scenarios") or [], result.get("interaction")
    )
    result["scenarios_original"] = result.get("scenarios") or []
    result["scenarios"] = adjusted_scenarios
    result["scenarios_adjustment"] = adj_meta
    # Step 7: calibration on top of Step 6 + persist prediction (audit).
    apply_step7_postprocess(result, source=src, persist=bool(persist_predictions))
    return result
