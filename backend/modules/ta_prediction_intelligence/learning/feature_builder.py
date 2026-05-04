"""
FeatureBuilder — Step 8 main orchestrator.

Takes the /live result dict (after Step 6+7) and produces a canonical
FeatureSnapshot:

    {
      'ts': int|None,
      'symbol': str,
      'tf': str,
      'features': {82 keys},
      'feature_hash': str,
      'feature_schema_hash': str,
      'feature_version': 'v1',
      'builder_version': '1.0.0',
      'states': {'trend': ..., 'momentum': ..., 'volatility': ...},
      'missing_engines': [list of engines that physically did NOT run
                            (absent from contributions[]); engines that ran
                            and honestly returned confidence=0 are NOT
                            considered missing — they are weak signals
                            and accounted for by downstream alignment math],
      'latency_ms': float,
    }

Read-only w.r.t. engines/scenarios/calibration. Missing engine data →
default values (per schema); missing_engines is returned as an auxiliary
observability field (NOT part of the hashed vector).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .feature_hash import build_feature_hash
from .feature_schema import (
    BUILDER_VERSION,
    DOMINANT_ENGINE_CODES,
    FEATURE_SCHEMA_HASH,
    FEATURE_VERSION,
    INTERACTION_TYPE_CODES,
    PATTERN_TYPE_CODES,
    TREND_PHASE_CODES,
    ZONE_ACTION_CODES,
    coerce_to_schema,
)
from .price_action import compute_price_action
from .state_machine import (
    classify_momentum_state,
    classify_trend_state,
    classify_volatility_state,
    detect_momentum_transition,
    detect_trend_transition,
    detect_volatility_transition,
)
from .temporal_buffer import HybridTemporalBuffer, get_temporal_buffer


def _f(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if v != v:
            return default
        return v
    except (TypeError, ValueError):
        return default


def _i(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(round(float(x)))
    except (TypeError, ValueError):
        return default


def _engine_raw(contributions: List[Dict[str, Any]], engine: str) -> Dict[str, Any]:
    for c in contributions or []:
        if str(c.get("engine") or "").lower() == engine:
            return c.get("raw") or {}
    return {}


def _engine_confidence(contributions: List[Dict[str, Any]], engine: str) -> float:
    for c in contributions or []:
        if str(c.get("engine") or "").lower() == engine:
            try:
                return float(c.get("confidence") or 0.0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _engine_bias_sign(contributions: List[Dict[str, Any]], engine: str) -> int:
    for c in contributions or []:
        if str(c.get("engine") or "").lower() == engine:
            b = (c.get("bias") or "").lower()
            if b == "bullish":
                return 1
            if b == "bearish":
                return -1
            return 0
    return 0


def _signal_entropy(contributions: List[Dict[str, Any]]) -> float:
    """Shannon entropy (0..1) over bullish/bearish/neutral distribution of 5 engines."""
    import math
    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for c in contributions or []:
        b = (c.get("bias") or "").lower()
        if b in counts:
            counts[b] += 1
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for v in counts.values():
        if v == 0:
            continue
        p = v / total
        h -= p * math.log2(p)
    # max entropy = log2(3) ≈ 1.585; normalise to [0, 1]
    return round(h / math.log2(3), 6)


class FeatureBuilder:
    """Deterministic builder from /live result → FeatureSnapshot."""

    VERSION = FEATURE_VERSION
    BUILDER = BUILDER_VERSION
    SCHEMA_HASH = FEATURE_SCHEMA_HASH

    def __init__(self, buffer: Optional[HybridTemporalBuffer] = None) -> None:
        self.buffer = buffer or get_temporal_buffer()

    # ------------------------------------------------------------------
    # MAIN BUILD
    # ------------------------------------------------------------------
    def build(self, result: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.time()
        symbol = str(result.get("symbol") or "").upper()
        tf = str(result.get("timeframe") or "").upper()
        live = result.get("_live") or {}
        candles: List[Dict[str, Any]] = (
            (result.get("_raw_data") or {}).get("candles")
            or live.get("candles")
            or []
        )
        contributions = result.get("contributions") or []

        # ── Raw per-engine payloads
        sraw = _engine_raw(contributions, "structure")
        mraw = _engine_raw(contributions, "momentum")
        lraw = _engine_raw(contributions, "level_zone")
        praw = _engine_raw(contributions, "pattern")
        vraw = _engine_raw(contributions, "volatility")

        # ── Confidences (for downstream alignment math; NOT the missing diagnostic)
        confs = {
            "structure": _engine_confidence(contributions, "structure"),
            "momentum": _engine_confidence(contributions, "momentum"),
            "level_zone": _engine_confidence(contributions, "level_zone"),
            "pattern": _engine_confidence(contributions, "pattern"),
            "volatility": _engine_confidence(contributions, "volatility"),
        }
        # ── feature_missing_engines = ONLY engines that physically did not run.
        # Previous logic flagged any engine with confidence<=0 as "missing", which
        # conflated a legitimate "no_signal" return (e.g. level_zone on a market
        # with no clear levels) with a real pipeline failure. Data Health Layer
        # caught the resulting 18% false-missing rate; this fix narrows the flag
        # to actual absence from contributions[]. Engines that ran and honestly
        # reported confidence=0 are NOT missing — they are weak signals, which
        # downstream alignment math (`confs`) already accounts for.
        _EXPECTED_ENGINES = ("structure", "momentum", "level_zone", "pattern", "volatility")
        _present_engines = {
            (c.get("engine") or "").strip().lower() for c in (contributions or [])
        }
        missing_engines = [e for e in _EXPECTED_ENGINES if e not in _present_engines]

        feats: Dict[str, Any] = {}

        # ── 1. STRUCTURE (12)
        feats["trend_strength"] = _f(sraw.get("trend_strength"))
        feats["trend_age_bars"] = _i(sraw.get("trend_age_bars") or sraw.get("trend_age"))
        feats["hh_count_20"] = _i(sraw.get("hh_count_20") or sraw.get("hh_count"))
        feats["hl_count_20"] = _i(sraw.get("hl_count_20") or sraw.get("hl_count"))
        feats["lh_count_20"] = _i(sraw.get("lh_count_20") or sraw.get("lh_count"))
        feats["ll_count_20"] = _i(sraw.get("ll_count_20") or sraw.get("ll_count"))
        feats["bos_count_20"] = _i(sraw.get("bos_count_20") or sraw.get("bos_count"))
        feats["choch_count_20"] = _i(sraw.get("choch_count_20") or sraw.get("choch_count"))
        feats["trend_phase"] = TREND_PHASE_CODES.get(
            str(sraw.get("trend_phase") or sraw.get("structure_state") or "range").lower(), 0
        )
        feats["trend_maturity"] = _f(sraw.get("trend_maturity") or sraw.get("maturity"))
        feats["structure_quality"] = _f(sraw.get("quality") or sraw.get("structure_quality"))
        feats["structure_consistency"] = _f(sraw.get("consistency"))

        # ── 2. MOMENTUM (13)
        feats["macd_hist"] = _f(mraw.get("macd_hist") or mraw.get("macd_hist_norm"))
        feats["macd_slope_5"] = _f(mraw.get("macd_slope_5") or mraw.get("macd_slope"))
        feats["macd_acceleration"] = _f(mraw.get("macd_acceleration") or mraw.get("macd_accel"))
        feats["macd_persistence"] = _i(mraw.get("macd_persistence"))
        # RSI may come in 0..100 or 0..1; normalise either way.
        rsi_raw = mraw.get("rsi")
        rsi_v = _f(rsi_raw, 0.0)
        if rsi_v > 1.5:
            rsi_v = rsi_v / 100.0
        feats["rsi"] = round(rsi_v, 6)
        feats["rsi_slope_5"] = _f(mraw.get("rsi_slope_5") or mraw.get("rsi_slope"))
        feats["rsi_div_bull"] = 1 if mraw.get("divergence_bull") or mraw.get("rsi_div_bull") else 0
        feats["rsi_div_bear"] = 1 if mraw.get("divergence_bear") or mraw.get("rsi_div_bear") else 0
        feats["divergence_age"] = _i(mraw.get("divergence_age"))
        feats["exhaustion_flag"] = 1 if mraw.get("exhaustion") or mraw.get("exhaustion_flag") else 0
        feats["momentum_quality"] = _f(mraw.get("quality") or mraw.get("momentum_quality"))
        # momentum_alignment: product of signs of macd_hist & (rsi-0.5)*2
        ma = feats["macd_hist"] * ((feats["rsi"] - 0.5) * 2)
        feats["momentum_alignment"] = round(max(-1.0, min(1.0, ma)), 6)
        # momentum_state will be set via classifier below (needs exhaustion_flag already set)
        mom_state = classify_momentum_state(
            rsi=feats["rsi"],
            macd_hist=feats["macd_hist"],
            exhaustion_flag=feats["exhaustion_flag"],
            momentum_alignment=feats["momentum_alignment"],
        )
        from .feature_schema import MOMENTUM_STATE_CODES
        feats["momentum_state"] = MOMENTUM_STATE_CODES.get(mom_state, 0)

        # ── 3. LEVEL/ZONE (12)
        feats["dist_to_support"] = abs(_f(lraw.get("dist_to_support") or lraw.get("support_dist_pct")))
        feats["dist_to_resistance"] = abs(_f(lraw.get("dist_to_resistance") or lraw.get("resistance_dist_pct")))
        feats["support_touches"] = _i(lraw.get("support_touches"))
        feats["resistance_touches"] = _i(lraw.get("resistance_touches"))
        feats["support_freshness"] = _i(lraw.get("support_freshness"))
        feats["resistance_freshness"] = _i(lraw.get("resistance_freshness"))
        feats["bounce_prob"] = _f(lraw.get("bounce_prob") or lraw.get("bounce_p"))
        feats["breakout_prob"] = _f(lraw.get("breakout_prob") or lraw.get("breakout_p"))
        feats["sweep_prob"] = _f(lraw.get("sweep_prob") or lraw.get("sweep_p"))
        feats["zone_action"] = ZONE_ACTION_CODES.get(
            str(lraw.get("zone_action") or lraw.get("action") or "none").lower(), 0
        )
        feats["level_strength"] = _f(lraw.get("level_strength") or lraw.get("strength"))
        feats["level_symmetry"] = _f(lraw.get("level_symmetry") or lraw.get("symmetry"))

        # ── 4. PATTERN (10)
        primary = praw.get("primary_pattern") or praw.get("pattern") or {}
        if isinstance(primary, dict):
            pname = str(primary.get("type") or primary.get("name") or "none").lower()
        else:
            pname = str(primary or "none").lower()
        feats["pattern_type"] = PATTERN_TYPE_CODES.get(pname, 0)
        feats["pattern_completion"] = _f(
            (primary or {}).get("completion") or praw.get("pattern_completion")
        )
        feats["pattern_symmetry"] = _f(
            (primary or {}).get("symmetry") or praw.get("pattern_symmetry")
        )
        feats["pattern_volume_confirm"] = (
            1 if (praw.get("volume_confirmation") or (primary or {}).get("volume_confirmation")) else 0
        )
        pdir_sign = _engine_bias_sign(contributions, "pattern")
        feats["pattern_direction"] = _i(
            (primary or {}).get("direction") or praw.get("pattern_direction") or pdir_sign
        )
        feats["pattern_conflict_flag"] = 1 if praw.get("alternative_conflict") or praw.get("conflict") else 0
        feats["pattern_age"] = _i((primary or {}).get("age_bars") or praw.get("pattern_age"))
        feats["pattern_quality"] = _f(praw.get("quality") or (primary or {}).get("quality"))
        feats["pattern_reliability"] = _f(praw.get("reliability") or (primary or {}).get("reliability"))
        feats["pattern_density"] = _f(praw.get("pattern_density"))

        # ── 5. VOLATILITY (10)
        feats["atr_pct"] = _f(vraw.get("atr_pct"))
        feats["atr_slope_5"] = _f(vraw.get("atr_slope_5") or vraw.get("atr_slope"))
        feats["compression_ratio"] = _f(vraw.get("compression_ratio"), 1.0)
        feats["expansion_flag"] = 1 if vraw.get("expansion") or vraw.get("expansion_flag") else 0
        feats["explosive_bar_flag"] = 1 if vraw.get("explosive_bar") or vraw.get("explosive_bar_flag") else 0
        feats["breakout_energy"] = _f(vraw.get("breakout_energy") or vraw.get("energy"))
        feats["volatility_regime_strength"] = _f(vraw.get("regime_strength"))
        feats["envelope_upper_dist"] = abs(_f(vraw.get("envelope_upper_dist") or vraw.get("upper_dist")))
        feats["envelope_lower_dist"] = abs(_f(vraw.get("envelope_lower_dist") or vraw.get("lower_dist")))
        vol_state = classify_volatility_state(
            atr_pct=feats["atr_pct"],
            compression_ratio=feats["compression_ratio"],
            expansion_flag=feats["expansion_flag"],
            explosive_bar_flag=feats["explosive_bar_flag"],
        )
        from .feature_schema import VOLATILITY_STATE_CODES
        feats["volatility_state"] = VOLATILITY_STATE_CODES.get(vol_state, 1)

        # ── 6. PRICE ACTION (10)
        feats.update(compute_price_action(candles))

        # ── Resolve anchor timestamp for THIS snapshot (FIX PIPELINE).
        # Single source of truth: live._live.last_candle_close_ts. We never
        # back-fill from a candle.timestamp because the chart-data layer ships
        # candle.timestamp as bar OPEN time (not close), which would produce
        # off-by-one alignment with outcome evaluation.
        ts_raw = live.get("last_candle_close_ts")
        try:
            ts: Optional[int] = int(ts_raw) if ts_raw is not None else None
        except (TypeError, ValueError):
            ts = None

        # ── 7. TRANSITIONS (7) — require previous BAR snapshot from buffer.
        # Use prev_bar(ts) so transitions are computed vs the actual prior
        # closed bar (not vs a same-bar snapshot from a previous /live call).
        prev_snap: Optional[Dict[str, Any]] = (
            self.buffer.prev_bar(symbol, tf, ts) if (symbol and tf) else None
        )
        prev_states = (prev_snap or {}).get("states") or {}
        curr_trend = classify_trend_state(
            trend_strength=feats["trend_strength"],
            trend_maturity=feats["trend_maturity"],
            exhaustion_flag=feats["exhaustion_flag"],
        )
        feats["trend_transition"] = detect_trend_transition(
            prev_states.get("trend"), curr_trend
        )
        feats["momentum_transition"] = detect_momentum_transition(
            prev_states.get("momentum"), mom_state
        )
        feats["volatility_transition"] = detect_volatility_transition(
            prev_states.get("volatility"), vol_state
        )
        # structure_break_flag: BOS or CHoCH within last 3 bars (if engine exposes list)
        recent_bos = _i(sraw.get("recent_bos_bars") or sraw.get("bos_bars_ago") or 999, 999)
        recent_choch = _i(sraw.get("recent_choch_bars") or sraw.get("choch_bars_ago") or 999, 999)
        feats["structure_break_flag"] = 1 if min(recent_bos, recent_choch) <= 3 else 0
        # interaction transition: type changed vs prev
        prev_inter = (prev_snap or {}).get("features", {}).get("interaction_type")
        curr_inter_name = str(
            (result.get("interaction") or {}).get("type") or "none"
        ).lower()
        curr_inter_code = INTERACTION_TYPE_CODES.get(curr_inter_name, 0)
        feats["interaction_transition_flag"] = (
            1 if (prev_inter is not None and prev_inter != curr_inter_code) else 0
        )
        # regime transition: from market_regime.label in meta (if present)
        prev_regime = (prev_snap or {}).get("regime")
        curr_regime = str(
            ((result.get("meta") or {}).get("market_regime") or {}).get("label")
            or (result.get("market_regime") or {}).get("label")
            or ""
        ).lower()
        if prev_regime and curr_regime and prev_regime != curr_regime:
            feats["regime_transition"] = 1
        else:
            feats["regime_transition"] = 0
        # transition_age: bars since last non-zero transition
        prev_age = _i((prev_snap or {}).get("features", {}).get("transition_age"))
        any_transition_now = int(
            feats["trend_transition"]
            or feats["momentum_transition"]
            or feats["volatility_transition"]
            or feats["structure_break_flag"]
            or feats["interaction_transition_flag"]
            or feats["regime_transition"]
        )
        feats["transition_age"] = 0 if any_transition_now else prev_age + 1

        # ── 8. META / CROSS (8)
        feats["conflict_ratio"] = _f(result.get("conflict_ratio"))
        feats["dominant_engine"] = DOMINANT_ENGINE_CODES.get(
            str(result.get("dominant_engine") or "none").lower(), 0
        )
        feats["interaction_type"] = curr_inter_code
        feats["interaction_confidence"] = _f((result.get("interaction") or {}).get("confidence"))
        # alignments = product of engine bias signs weighted by confidence
        s_sign = _engine_bias_sign(contributions, "structure")
        m_sign = _engine_bias_sign(contributions, "momentum")
        l_sign = _engine_bias_sign(contributions, "level_zone")
        feats["structure_momentum_alignment"] = round(
            max(-1.0, min(1.0, float(s_sign * m_sign) * min(confs["structure"], confs["momentum"]))),
            6,
        )
        feats["structure_level_alignment"] = round(
            max(-1.0, min(1.0, float(s_sign * l_sign) * min(confs["structure"], confs["level_zone"]))),
            6,
        )
        feats["expected_move"] = abs(_f(result.get("expected_move_pct")))
        feats["signal_entropy"] = _signal_entropy(contributions)

        # ── Coerce to schema (clip + order + types)
        coerced = coerce_to_schema(feats)

        # ── Hash (canonical, stable across platforms)
        fhash = build_feature_hash(coerced)

        snap = {
            "ts": ts,
            "symbol": symbol,
            "tf": tf,
            "features": coerced,
            "feature_hash": fhash,
            "feature_schema_hash": self.SCHEMA_HASH,
            "feature_version": self.VERSION,
            "builder_version": self.BUILDER,
            "states": {
                "trend": curr_trend,
                "momentum": mom_state,
                "volatility": vol_state,
            },
            "regime": curr_regime or None,
            "missing_engines": missing_engines,
            "latency_ms": round((time.time() - t0) * 1000.0, 3),
        }
        # Push to buffer AFTER build so transitions used the prior snapshot.
        if symbol and tf:
            try:
                self.buffer.push(symbol, tf, snap)
            except Exception:
                pass
        return snap

    def build_preview(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Build a snapshot WITHOUT pushing to the buffer (idempotent preview)."""
        real_buffer = self.buffer
        class _NoopBuf:
            def last(self, *a, **kw): return real_buffer.last(*a, **kw)
            def push(self, *a, **kw): return None
            def get(self, *a, **kw): return real_buffer.get(*a, **kw)
            def size(self, *a, **kw): return real_buffer.size(*a, **kw)
            def prev_bar(self, *a, **kw): return real_buffer.prev_bar(*a, **kw)
        self.buffer = _NoopBuf()
        try:
            return self.build(result)
        finally:
            self.buffer = real_buffer


_builder_singleton: Optional[FeatureBuilder] = None


def get_feature_builder() -> FeatureBuilder:
    global _builder_singleton
    if _builder_singleton is None:
        _builder_singleton = FeatureBuilder()
    return _builder_singleton
