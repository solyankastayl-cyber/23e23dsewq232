"""
Execution Bridge
================
Sprint A2.3: Единственная точка входа для execution из Runtime/Strategy.

КРИТИЧНО:
- НЕ исполняет напрямую
- ВСЁ через ExecutionQueueV2
- Изолирует Runtime от execution деталей

Phase LIVE-1 (2026-04-23): SHORT-side gate.
  Reads `short_trading_enabled` flag from `regime_controls` collection (TTL-
  cached 5s). When disabled — signals whose side is SELL/SHORT are *not*
  enqueued; we log `[STRATEGY_DISABLED] SHORT_TREND skipped because
  short_trading_enabled=false` and persist an audit event to
  `regime_guard_events`. This is reversible: flip the doc to
  `enabled: true` and the next signal is accepted. No SHORT generator
  code touched.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from modules.exchange.order_builder import build_order_request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase LIVE-1 — SHORT-trading feature flag (TTL-cached reader)
# ---------------------------------------------------------------------------
_SHORT_FLAG_CACHE: Dict[str, Any] = {"enabled": None, "ts": 0.0}
_SHORT_FLAG_TTL_SEC = 5.0


def _pymongo_controls_collection():
    """Open a short-lived sync pymongo handle to regime_controls.
    Kept out of the hot path via cache; called only on cache miss.
    """
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = MongoClient(url, serverSelectionTimeoutMS=3000)
        return client["trading_os"]["regime_controls"]
    except Exception as exc:  # pragma: no cover — environment-specific
        logger.debug("[LIVE-1] regime_controls unavailable: %s", exc)
        return None


def _is_short_trading_enabled(default: bool = True) -> bool:
    """Return True when SHORT submissions are allowed.
    Default is True (safe backward-compat) when the flag doc is absent.
    """
    now = time.time()
    if _SHORT_FLAG_CACHE["enabled"] is not None and (
        now - _SHORT_FLAG_CACHE["ts"] < _SHORT_FLAG_TTL_SEC
    ):
        return bool(_SHORT_FLAG_CACHE["enabled"])
    col = _pymongo_controls_collection()
    enabled = default
    if col is not None:
        try:
            doc = col.find_one({"control": "short_trading_enabled"})
            if doc is not None and "enabled" in doc:
                enabled = bool(doc["enabled"])
        except Exception as exc:  # pragma: no cover
            logger.debug("[LIVE-1] read short_trading_enabled failed: %s", exc)
    _SHORT_FLAG_CACHE["enabled"] = enabled
    _SHORT_FLAG_CACHE["ts"] = now
    return enabled


def _record_short_skip(signal: Dict[str, Any], reason: str) -> None:
    """Persist one audit row to regime_guard_events (best-effort)."""
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db = MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        db["regime_guard_events"].insert_one(
            {
                "event": "SHORT_SKIPPED",
                "gate": "short_trading_enabled",
                "phase": "LIVE-1",
                "symbol": signal.get("symbol"),
                "side": signal.get("side"),
                "strategy": signal.get("strategy"),
                "decision_id": signal.get("decision_id"),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("[LIVE-1] record skip audit failed: %s", exc)


# Phase LIVE-2f — SHORT-regime alignment flag.
# When `short_downtrend_only=true`, SHORT orders require regime==DOWNTREND.
_SHORT_DOWNTREND_FLAG_CACHE: Dict[str, Any] = {"enabled": None, "ts": 0.0}


def _is_short_downtrend_only_enabled(default: bool = True) -> bool:
    """Read regime_controls.short_downtrend_only (TTL 5s). Default True."""
    now = time.time()
    if _SHORT_DOWNTREND_FLAG_CACHE["enabled"] is not None and (
        now - _SHORT_DOWNTREND_FLAG_CACHE["ts"] < _SHORT_FLAG_TTL_SEC
    ):
        return bool(_SHORT_DOWNTREND_FLAG_CACHE["enabled"])
    col = _pymongo_controls_collection()
    enabled = default
    if col is not None:
        try:
            doc = col.find_one({"control": "short_downtrend_only"})
            if doc is not None and "enabled" in doc:
                enabled = bool(doc["enabled"])
        except Exception:
            pass
    _SHORT_DOWNTREND_FLAG_CACHE["enabled"] = enabled
    _SHORT_DOWNTREND_FLAG_CACHE["ts"] = now
    return enabled


def _record_short_regime_skip(signal: Dict[str, Any], regime: Optional[str]) -> None:
    """Persist one audit row to regime_guard_events (best-effort)."""
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db = MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        db["regime_guard_events"].insert_one(
            {
                "event": "SHORT_SKIPPED_REGIME",
                "gate": "short_downtrend_only",
                "phase": "LIVE-2f",
                "symbol": signal.get("symbol"),
                "side": signal.get("side"),
                "strategy": signal.get("strategy"),
                "decision_id": signal.get("decision_id"),
                "detected_regime": regime,
                "required_regime": "DOWNTREND",
                "reason": (
                    f"[STRATEGY_FILTERED] SHORT blocked: regime={regime} != DOWNTREND"
                ),
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:
        logger.debug("[LIVE-2f] record short regime skip failed: %s", exc)


# ---------------------------------------------------------------------------
# Phase FIX-ENTRY (Phase LIVE-2e) — LONG regime alignment
# ---------------------------------------------------------------------------
# Architect directive (2026-04-24 post LIVE-2d):
#   "LIVE-2d показал win-rate 30% для LONG при симметричных ±0.15% TP/SL —
#    это отрицательный edge. Причина — MA-cross entries на downtrend'ах.
#    Минимальный фикс: НЕ открывать LONG если regime != UPTREND."
#
# Implementation:
#   * TTL-cached (60s) regime computed via the existing RegimeDetector from
#     200x 1h BTC candles (ma50 + ma200 against current close).
#   * Per-symbol cache so multi-asset works later; for BTCUSDT only today.
#   * Regime filter is TOGGLEABLE via regime_controls.long_uptrend_only
#     doc — default is ENABLED (we are entering LIVE-2e with the filter on).
# ---------------------------------------------------------------------------
_LONG_REGIME_CACHE: Dict[str, Dict[str, Any]] = {}
_LONG_REGIME_TTL_SEC = 60.0
_LONG_FLAG_CACHE: Dict[str, Any] = {"enabled": None, "ts": 0.0}


def _is_long_uptrend_filter_enabled(default: bool = True) -> bool:
    """Read regime_controls.long_uptrend_only (TTL 5s). Default True."""
    now = time.time()
    if _LONG_FLAG_CACHE["enabled"] is not None and (
        now - _LONG_FLAG_CACHE["ts"] < _SHORT_FLAG_TTL_SEC
    ):
        return bool(_LONG_FLAG_CACHE["enabled"])
    col = _pymongo_controls_collection()
    enabled = default
    if col is not None:
        try:
            doc = col.find_one({"control": "long_uptrend_only"})
            if doc is not None and "enabled" in doc:
                enabled = bool(doc["enabled"])
        except Exception:
            pass
    _LONG_FLAG_CACHE["enabled"] = enabled
    _LONG_FLAG_CACHE["ts"] = now
    return enabled


def _compute_current_regime(symbol: str) -> Optional[str]:
    """Compute current market regime for a symbol.

    Phase FIX-DETECTOR (LIVE-2g, 2026-04-24): EMA-based, faster detector.

    Old (LIVE-2e/2f, deprecated):
        UPTREND   = price > SMA50 > SMA200
        DOWNTREND = price < SMA50 < SMA200
        else RANGE
        — required ~$300–500 BTC impulse to flip → too late, system silent.

    New (this implementation):
        UPTREND   = EMA20 > EMA50 AND price > EMA20
        DOWNTREND = EMA20 < EMA50 AND price < EMA20
        else RANGE
        — EMA20/50 react faster, catch trends earlier, but stay disciplined
          enough to avoid the LIVE-2d noise trap.

    Implementation:
      * Pull 200x 1h candles from BinanceProvider (cheap, cached at provider).
      * Seed EMA with SMA of the first `period` closes, then iterate the
        standard EMA recurrence (mult = 2 / (period + 1)).
      * Return 'UPTREND' / 'DOWNTREND' / 'RANGE' / None on data shortage.
    """
    try:
        from modules.scanner.market_data.binance_provider import (
            get_market_data_provider,
        )

        provider = get_market_data_provider()
        candles = provider.get_candles(symbol, "1h", limit=200)
        if not candles or len(candles) < 60:
            return None
        closes = [float(c.get("close")) for c in candles if c.get("close")]
        if len(closes) < 60:
            return None

        def _ema(values, period):
            if len(values) < period:
                return None
            ema = sum(values[:period]) / period
            mult = 2.0 / (period + 1)
            for v in values[period:]:
                ema = (v - ema) * mult + ema
            return ema

        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        if ema20 is None or ema50 is None:
            return None

        last_close = closes[-1]
        if ema20 > ema50 and last_close > ema20:
            return "UPTREND"
        if ema20 < ema50 and last_close < ema20:
            return "DOWNTREND"
        return "RANGE"
    except Exception as exc:
        logger.debug("[FIX-DETECTOR] regime compute failed %s: %s", symbol, exc)
        return None


def _get_cached_regime(symbol: str) -> Optional[str]:
    now = time.time()
    entry = _LONG_REGIME_CACHE.get(symbol)
    if entry and (now - entry["ts"] < _LONG_REGIME_TTL_SEC):
        return entry["regime"]
    regime = _compute_current_regime(symbol)
    _LONG_REGIME_CACHE[symbol] = {"regime": regime, "ts": now}
    return regime


def _record_long_skip(signal: Dict[str, Any], regime: Optional[str]) -> None:
    """Persist one audit row to regime_guard_events (best-effort)."""
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db = MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        db["regime_guard_events"].insert_one(
            {
                "event": "LONG_SKIPPED_REGIME",
                "gate": "long_uptrend_only",
                "phase": "LIVE-2e",
                "symbol": signal.get("symbol"),
                "side": signal.get("side"),
                "strategy": signal.get("strategy"),
                "decision_id": signal.get("decision_id"),
                "detected_regime": regime,
                "required_regime": "UPTREND",
                "reason": (
                    f"[STRATEGY_FILTERED] LONG blocked: regime={regime} != UPTREND"
                ),
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:
        logger.debug("[FIX-ENTRY] record long skip failed: %s", exc)


# ---------------------------------------------------------------------------
# Phase LIVE-3a — Confidence Adjustment Layer (soft, multiplicative)
# ---------------------------------------------------------------------------
# Forensic basis (EDGE_AUDIT, LIVE-2H subset):
#   * SHORT side: N=45, WR=37.8%, avg_pnl=-0.063%  → side penalty 0.80
#   * LONG side in UPTREND: WR=31% (vs 50% in DOWN/RANGE)  → regime penalty 0.85
#
# Architectural choice: this is NOT a hard skip rule. We *shape* the confidence
# distribution (it is currently flat 0.60 from SimpleMA) using forensic-derived
# multipliers, then apply a soft, configurable threshold gate. SimpleMA entry
# logic and decision_intelligence are NOT touched.
#
# Controls (regime_controls collection, single document):
#   { "control": "confidence_adjustment",
#     "enabled":               true|false,   # if false → no shaping at all
#     "gate_enabled":          true|false,   # if false → never skip on conf
#     "min_adjusted_confidence": 0.45,
#     "short_side_multiplier":   0.80,
#     "long_uptrend_multiplier": 0.85 }
# Defaults below are used when the doc / field is absent (safe backward-compat).
# ---------------------------------------------------------------------------
_CONF_ADJ_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "gate_enabled": True,
    "min_adjusted_confidence": 0.45,
    "short_side_multiplier": 0.80,
    "long_uptrend_multiplier": 0.85,
    # ----- Phase LIVE-3d additions (default OFF; architect must enable) -----
    # Gathered from LIVE-3c forensic: in LOW-volatility windows
    # (1h × 20-bar stdev of returns < 0.15%) SimpleMA WR=30% / avg PnL=-0.09%
    # versus MID-vol WR=80% / avg=+0.05%. Hard skip when vol < threshold.
    # Defaults are inert (skip disabled) so deployment of LIVE-3d cannot
    # change runtime behaviour without an explicit mongo update.
    "volatility_low_skip_enabled": False,
    "volatility_low_threshold": 0.0015,
}
_CONF_ADJ_CACHE: Dict[str, Any] = {"controls": None, "ts": 0.0}
_CONF_ADJ_TTL_SEC = 5.0


def _read_confidence_adjustment_controls() -> Dict[str, Any]:
    """Read regime_controls.confidence_adjustment with TTL cache.

    Falls back to _CONF_ADJ_DEFAULTS when the doc is missing or any field is
    absent. Read errors are non-fatal and fall through to defaults.
    """
    now = time.time()
    cached = _CONF_ADJ_CACHE.get("controls")
    if cached is not None and (now - _CONF_ADJ_CACHE["ts"] < _CONF_ADJ_TTL_SEC):
        return cached

    controls = dict(_CONF_ADJ_DEFAULTS)
    col = _pymongo_controls_collection()
    if col is not None:
        try:
            doc = col.find_one({"control": "confidence_adjustment"}) or {}
            for key in _CONF_ADJ_DEFAULTS.keys():
                if key in doc and doc[key] is not None:
                    controls[key] = doc[key]
        except Exception as exc:  # pragma: no cover
            logger.debug("[LIVE-3a] read confidence_adjustment failed: %s", exc)

    # Sanitize numeric fields.
    for k in ("min_adjusted_confidence", "short_side_multiplier",
              "long_uptrend_multiplier"):
        try:
            controls[k] = float(controls[k])
        except (TypeError, ValueError):
            controls[k] = float(_CONF_ADJ_DEFAULTS[k])
    controls["enabled"] = bool(controls["enabled"])
    controls["gate_enabled"] = bool(controls["gate_enabled"])

    _CONF_ADJ_CACHE["controls"] = controls
    _CONF_ADJ_CACHE["ts"] = now
    return controls


def _resolve_regime_for_adjustment(
    signal: Dict[str, Any], symbol: str
) -> Optional[str]:
    """Canonical regime resolution order for the adjustment layer.

    1. signal["regime"]  (or signal["regime_at_entry"])
    2. cached regime via _get_cached_regime(symbol) (EMA20/50 detector)
    3. None  → caller treats this as 'unknown' and applies regime_multiplier=1.0

    NEVER blocks. Unknown regime is benign — only side penalty will apply.
    """
    raw = signal.get("regime") or signal.get("regime_at_entry")
    if isinstance(raw, str) and raw:
        return raw.upper()
    try:
        return _get_cached_regime(symbol)
    except Exception as exc:  # pragma: no cover
        logger.debug("[LIVE-3a] regime cache lookup failed: %s", exc)
        return None


def _adjust_confidence(
    base_conf: float,
    side: str,
    regime: Optional[str],
    controls: Dict[str, Any],
) -> tuple:
    """Apply multiplicative adjustment chain to a flat upstream confidence.

    Returns (adjusted_conf, breakdown).

    Math (per architect spec):
        side_mult   = short_side_multiplier   if side in (SELL,SHORT) else 1.0
        regime_mult = long_uptrend_multiplier if side in (BUY,LONG)
                                               and regime == 'UPTREND' else 1.0
        adjusted = clamp(base * side_mult * regime_mult, 0.05, 0.95)

    `breakdown` is JSON-safe and meant to be persisted / logged for forensic.
    """
    try:
        conf = float(base_conf) if base_conf is not None else 0.0
    except (TypeError, ValueError):
        conf = 0.0

    breakdown: Dict[str, Any] = {"base": round(conf, 4)}

    side_u = (side or "").upper()
    is_short = side_u in ("SELL", "SHORT")
    is_long = side_u in ("BUY", "LONG")
    regime_u = (regime or "").upper() if regime else None

    if controls.get("enabled", True):
        side_mult = (
            float(controls["short_side_multiplier"]) if is_short else 1.0
        )
        conf = conf * side_mult
        breakdown["side_multiplier"] = round(side_mult, 4)
        breakdown["after_side"] = round(conf, 4)

        regime_mult = 1.0
        if is_long and regime_u == "UPTREND":
            regime_mult = float(controls["long_uptrend_multiplier"])
        conf = conf * regime_mult
        breakdown["regime_multiplier"] = round(regime_mult, 4)
        breakdown["after_regime"] = round(conf, 4)
    else:
        breakdown["side_multiplier"] = 1.0
        breakdown["after_side"] = round(conf, 4)
        breakdown["regime_multiplier"] = 1.0
        breakdown["after_regime"] = round(conf, 4)
        breakdown["disabled"] = True

    # Clamp to safe range.
    adjusted = max(0.05, min(conf, 0.95))
    breakdown["adjusted"] = round(adjusted, 4)
    breakdown["min_gate"] = float(controls["min_adjusted_confidence"])
    breakdown["regime_observed"] = regime_u
    return adjusted, breakdown


def _record_conf_gate_skip(
    signal: Dict[str, Any],
    breakdown: Dict[str, Any],
    regime: Optional[str],
) -> None:
    """Persist one audit row to conf_gate_events (best-effort, non-blocking)."""
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db = MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        db["conf_gate_events"].insert_one(
            {
                "event": "CONF_BELOW_GATE",
                "phase": "LIVE-3a",
                "symbol": signal.get("symbol"),
                "side": signal.get("side"),
                "strategy": signal.get("strategy"),
                "decision_id": signal.get("decision_id"),
                "detected_regime": regime,
                "base_confidence": breakdown.get("base"),
                "adjusted_confidence": breakdown.get("adjusted"),
                "min_gate": breakdown.get("min_gate"),
                "breakdown": breakdown,
                "reason": (
                    f"[CONF_GATE] adjusted={breakdown.get('adjusted')} "
                    f"< min_gate={breakdown.get('min_gate')}"
                ),
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("[LIVE-3a] record conf gate skip failed: %s", exc)


# ---------------------------------------------------------------------------
# Phase LIVE-3d — Market-context capture + optional LOW-volatility gate
# ---------------------------------------------------------------------------
# Goal: persist 1h × 20-bar volatility, MA(5,1h), and distance-to-MA on every
# accepted signal so the next forensic iteration has native ground-truth
# without re-deriving from candles. Optional hard skip when volatility is
# pathologically low (forensic showed WR=30% / avg=-0.09% in that band).
#
# Defaults: skip is OFF. Persistence is unconditional (just data audit).
# Reversible via regime_controls.confidence_adjustment.volatility_low_skip_*.
# ---------------------------------------------------------------------------
_MARKET_CTX_CACHE: Dict[str, Dict[str, Any]] = {}
_MARKET_CTX_TTL_SEC = 60.0


def _fetch_candles_with_fallback(symbol: str) -> tuple:
    """Try Binance first, then Coinbase via MarketDataService. Returns
    (closes_list, source_name). closes_list is empty on total failure."""
    closes: List[float] = []
    source = "none"

    # --- Primary: Binance ---
    try:
        from modules.scanner.market_data.binance_provider import (
            get_market_data_provider,
        )
        provider = get_market_data_provider()
        candles = provider.get_candles(symbol, "1h", limit=30)
        if candles and len(candles) >= 6:
            closes = [
                float(c.get("close")) for c in candles
                if c.get("close") is not None
            ]
            if len(closes) >= 6:
                source = "binance"
                return closes, source
        logger.warning(
            "[LIVE-3d] binance returned insufficient candles for %s "
            "(got %d, need >=6); falling back to coinbase",
            symbol, len(candles) if candles else 0,
        )
    except Exception as exc:
        logger.warning(
            "[LIVE-3d] binance provider failed for %s: %s; "
            "falling back to coinbase", symbol, exc,
        )

    # --- Fallback: Coinbase via MarketDataService ---
    try:
        from modules.ta_engine.setup.market_data_service import (
            MarketDataService,
        )
        # NOTE: cheap to instantiate; service has its own internal cache.
        svc = MarketDataService()
        cb_candles = svc.get_candles(symbol, "1h", limit=30)
        if cb_candles and len(cb_candles) >= 6:
            cb_closes = [
                float(c.get("close")) for c in cb_candles
                if c.get("close") is not None
            ]
            if len(cb_closes) >= 6:
                source = "coinbase"
                return cb_closes, source
        logger.warning(
            "[LIVE-3d] coinbase fallback also returned insufficient "
            "candles for %s (got %d)",
            symbol, len(cb_candles) if cb_candles else 0,
        )
    except Exception as exc:
        logger.warning(
            "[LIVE-3d] coinbase fallback failed for %s: %s", symbol, exc,
        )

    return closes, source


def _compute_market_context(
    symbol: str, entry_price: Optional[float]
) -> Dict[str, Any]:
    """Derive 1h × 20-bar volatility + MA(5) with provider fallback.

    All fields can be None when both Binance and Coinbase return short data.
    Never raises. Now emits warning-level logs so silent failures are visible.
    """
    out: Dict[str, Any] = {
        "volatility_1h_20": None,
        "ma5_1h": None,
        "distance_to_ma5_1h": None,
        "candles_used": 0,
        "source": "none",
    }
    try:
        closes, source = _fetch_candles_with_fallback(symbol)
        if len(closes) < 6:
            logger.warning(
                "[LIVE-3d] no usable candles for %s — market ctx will be null",
                symbol,
            )
            return out

        out["candles_used"] = len(closes)
        out["source"] = source

        window = closes[-20:]
        if len(window) >= 6:
            rets = [
                (window[i] - window[i - 1]) / window[i - 1]
                for i in range(1, len(window))
                if window[i - 1]
            ]
            if rets:
                mean = sum(rets) / len(rets)
                var = sum((r - mean) ** 2 for r in rets) / len(rets)
                out["volatility_1h_20"] = var ** 0.5

        if len(closes) >= 5:
            ma5 = sum(closes[-5:]) / 5.0
            out["ma5_1h"] = ma5
            if entry_price is not None and ma5:
                try:
                    out["distance_to_ma5_1h"] = (
                        abs(float(entry_price) - ma5) / ma5
                    )
                except (TypeError, ValueError):
                    pass
    except Exception as exc:
        logger.warning(
            "[LIVE-3d] market ctx compute crashed for %s: %s", symbol, exc,
        )
    return out


def _get_cached_market_context(
    symbol: str, entry_price: Optional[float]
) -> Dict[str, Any]:
    """TTL-cached market context. Distance is recomputed on every call (entry
    price is signal-specific). Volatility/MA cached for 60s — but **failed**
    computes (volatility_1h_20 is None) are NOT cached, so a transient
    provider outage cannot poison the cache for a full minute."""
    now = time.time()
    cached = _MARKET_CTX_CACHE.get(symbol)
    if cached and (now - cached["ts"] < _MARKET_CTX_TTL_SEC):
        ctx = dict(cached["ctx"])
        ma5 = ctx.get("ma5_1h")
        if entry_price is not None and ma5:
            try:
                ctx["distance_to_ma5_1h"] = abs(float(entry_price) - ma5) / ma5
            except (TypeError, ValueError):
                pass
        return ctx
    ctx = _compute_market_context(symbol, entry_price)
    # Phase LIVE-3d-fix: only cache successful computes. Otherwise we'd be
    # locked into stale `None`s for 60s after every transient provider hiccup.
    if ctx.get("volatility_1h_20") is not None:
        _MARKET_CTX_CACHE[symbol] = {"ctx": ctx, "ts": now}
    return ctx


def _record_vol_gate_skip(
    signal: Dict[str, Any], ctx: Dict[str, Any], threshold: float
) -> None:
    """Persist one audit row to vol_gate_events (best-effort, non-blocking)."""
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db = MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        db["vol_gate_events"].insert_one(
            {
                "event": "LOW_VOL_NO_EDGE",
                "phase": "LIVE-3d",
                "symbol": signal.get("symbol"),
                "side": signal.get("side"),
                "strategy": signal.get("strategy"),
                "decision_id": signal.get("decision_id"),
                "volatility_1h_20": ctx.get("volatility_1h_20"),
                "threshold": threshold,
                "ma5_1h": ctx.get("ma5_1h"),
                "distance_to_ma5_1h": ctx.get("distance_to_ma5_1h"),
                "candles_used": ctx.get("candles_used"),
                "reason": (
                    f"[LOW_VOL_NO_EDGE] vol={ctx.get('volatility_1h_20')} "
                    f"< threshold={threshold}"
                ),
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("[LIVE-3d] record vol gate skip failed: %s", exc)


class ExecutionBridge:
    """
    Execution facade для Runtime.
    
    Принимает trading signals → преобразует в execution jobs → enqueue.
    Runtime НЕ знает про OrderManager, Exchange, Workers.
    """

    def __init__(self, queue_repo=None):
        self.queue_repo = queue_repo
        if self.queue_repo is None:
            logger.warning("ExecutionBridge initialized without queue_repo - will fail on submit")

    async def submit(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit signal for execution.
        
        Args:
            signal: {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "confidence": 0.75,
                "strategy": "CONTINUATION",
                "entry_price": 70000,
                "stop_price": 68000,
                "target_price": 73000
            }
        
        Returns:
            {"ok": bool, "job_id": str}
        """
        if self.queue_repo is None:
            return {
                "ok": False,
                "error": "ExecutionBridge queue_repo not initialized"
            }

        # Phase LIVE-1 → LIVE-2f SHORT gate ladder:
        #   short_trading_enabled=false              → block all SHORT
        #   short_trading_enabled=true AND
        #     short_downtrend_only=true              → block SHORT if regime != DOWNTREND
        #   short_trading_enabled=true AND
        #     short_downtrend_only=false             → allow SHORT (legacy)
        raw_side = str(signal.get("side") or "").upper()
        is_short_side = raw_side in ("SELL", "SHORT")
        is_long_side = raw_side in ("BUY", "LONG")

        if is_short_side:
            if not _is_short_trading_enabled(default=True):
                msg = (
                    "[STRATEGY_DISABLED] SHORT_TREND skipped because "
                    "short_trading_enabled=false"
                )
                logger.warning(
                    "%s symbol=%s strategy=%s decision_id=%s",
                    msg,
                    signal.get("symbol"),
                    signal.get("strategy"),
                    signal.get("decision_id"),
                )
                _record_short_skip(signal, reason=msg)
                return {
                    "ok": False,
                    "reason": "SHORT_TRADING_DISABLED",
                    "phase": "LIVE-1",
                }
            # SHORT trading is globally on — apply regime-alignment gate.
            if _is_short_downtrend_only_enabled(default=True):
                sym = signal.get("symbol") or "BTCUSDT"
                regime = _get_cached_regime(sym)
                if regime != "DOWNTREND":
                    msg = (
                        f"[STRATEGY_FILTERED] SHORT skipped: regime={regime} != DOWNTREND"
                    )
                    logger.info(
                        "%s symbol=%s strategy=%s decision_id=%s",
                        msg,
                        sym,
                        signal.get("strategy"),
                        signal.get("decision_id"),
                    )
                    _record_short_regime_skip(signal, regime=regime)
                    return {
                        "ok": False,
                        "reason": "SHORT_REGIME_MISMATCH",
                        "detected_regime": regime,
                        "required_regime": "DOWNTREND",
                        "phase": "LIVE-2f",
                    }

        # Phase FIX-ENTRY (LIVE-2e) gate — block LONG submissions unless
        # current market regime is UPTREND. Default-on; flip
        # regime_controls.long_uptrend_only=false to disable quickly.
        if is_long_side and _is_long_uptrend_filter_enabled(default=True):
            sym = signal.get("symbol") or "BTCUSDT"
            regime = _get_cached_regime(sym)
            if regime != "UPTREND":
                msg = (
                    f"[STRATEGY_FILTERED] LONG skipped: regime={regime} != UPTREND"
                )
                logger.info(
                    "%s symbol=%s strategy=%s decision_id=%s",
                    msg,
                    sym,
                    signal.get("strategy"),
                    signal.get("decision_id"),
                )
                _record_long_skip(signal, regime=regime)
                return {
                    "ok": False,
                    "reason": "LONG_REGIME_MISMATCH",
                    "detected_regime": regime,
                    "required_regime": "UPTREND",
                    "phase": "LIVE-2e",
                }

        # ---------------------------------------------------------------
        # Phase LIVE-3a — Confidence Adjustment Layer (soft, non-blocking)
        # ---------------------------------------------------------------
        # Runs AFTER the hard-gate ladder above and BEFORE order build/enqueue.
        # Shapes the (currently flat 0.60) upstream confidence using forensic-
        # derived side & regime multipliers, then applies a soft, configurable
        # threshold gate. Does NOT touch SimpleMA or decision_intelligence.
        conf_controls = _read_confidence_adjustment_controls()
        adj_symbol = signal.get("symbol") or "BTCUSDT"
        adj_regime = _resolve_regime_for_adjustment(signal, adj_symbol)
        base_conf = signal.get("confidence", 0.5)
        adjusted_conf, conf_breakdown = _adjust_confidence(
            base_conf=base_conf,
            side=raw_side,
            regime=adj_regime,
            controls=conf_controls,
        )
        if (
            conf_controls.get("gate_enabled", True)
            and adjusted_conf < conf_breakdown["min_gate"]
        ):
            logger.info(
                "[CONF_GATE] skipped: symbol=%s side=%s base=%.4f adjusted=%.4f "
                "min=%.2f regime=%s",
                adj_symbol,
                raw_side,
                conf_breakdown.get("base", 0.0),
                adjusted_conf,
                conf_breakdown["min_gate"],
                adj_regime,
            )
            _record_conf_gate_skip(signal, conf_breakdown, adj_regime)
            return {
                "ok": False,
                "reason": "CONF_BELOW_GATE",
                "phase": "LIVE-3a",
                "adjusted_confidence": adjusted_conf,
                "min_gate": conf_breakdown["min_gate"],
                "detected_regime": adj_regime,
                "breakdown": conf_breakdown,
            }

        # ---------------------------------------------------------------
        # Phase LIVE-3d — Market-context capture + optional LOW-vol gate
        # ---------------------------------------------------------------
        # Always compute & persist (B). Optional skip behind feature flag.
        market_ctx = _get_cached_market_context(
            adj_symbol, signal.get("entry_price")
        )
        vol_low_skip = bool(
            conf_controls.get("volatility_low_skip_enabled", False)
        )
        try:
            vol_threshold = float(
                conf_controls.get("volatility_low_threshold", 0.0015)
            )
        except (TypeError, ValueError):
            vol_threshold = 0.0015
        vol_value = market_ctx.get("volatility_1h_20")
        if (
            vol_low_skip
            and vol_value is not None
            and vol_value < vol_threshold
        ):
            logger.info(
                "[LOW_VOL_NO_EDGE] skipped: symbol=%s side=%s vol=%.6f "
                "< threshold=%.6f ma5=%s dist=%s",
                adj_symbol, raw_side, vol_value, vol_threshold,
                market_ctx.get("ma5_1h"),
                market_ctx.get("distance_to_ma5_1h"),
            )
            _record_vol_gate_skip(signal, market_ctx, vol_threshold)
            return {
                "ok": False,
                "reason": "LOW_VOL_NO_EDGE",
                "phase": "LIVE-3d",
                "volatility_1h_20": vol_value,
                "threshold": vol_threshold,
                "market_context": market_ctx,
            }

        try:
            # Build order request
            qty_from_sizing = self._resolve_size(signal)
            
            # DEBUG: Log qty resolution
            logger.warning(f"[ExecutionBridge] Resolved qty={qty_from_sizing} from signal sizing (symbol={signal['symbol']})")
            
            order_request = build_order_request(
                symbol=signal["symbol"],
                side=signal["side"],
                qty=qty_from_sizing,
                order_type="MARKET",
            )
            
            # Sprint R1: Add sizing metadata to order payload for audit trail
            sizing = signal.get("sizing", {})
            if sizing:
                order_request["sizing_meta"] = {
                    "qty": sizing.get("qty"),
                    "notional_usd": sizing.get("notional_usd"),
                    "size_multiplier": sizing.get("size_multiplier"),
                    "debug": sizing.get("debug", {}),
                }
                order_request["sizing_applied"] = True
            else:
                order_request["sizing_applied"] = False
            
            # DEBUG: Confirm qty match
            logger.warning(f"[ExecutionBridge] ORDER qty={order_request['quantity']}, sizing.qty={sizing.get('qty')}, match={order_request['quantity'] == sizing.get('qty')}")
            
            # Create execution job
            job_id = str(uuid4())
            trace_id = str(uuid4())
            idempotency_key = f"runtime-{job_id}"
            
            # Paper Trading: Add decision metadata to payload
            # Phase closing-loop.B (2026-04-23): fill field-name aliases so the
            # OrderSimulator / Worker fill pipeline can read entry_price and
            # final_size. Historically OrderSimulator read payload.get(
            # "entry_price") and payload.get("final_size") — those keys did
            # not exist in this payload (we only had "signal_price" and
            # "quantity"), causing every paper-trade's fill_price and
            # filled_qty to fall back to 0.0, which cascaded into
            # trading_cases with entry_price=0 / qty=0 and disabled PnL.
            # Fix: publish the SAME value under both names — no arithmetic
            # change, pure key-name compatibility.
            signal_entry_price = signal.get("entry_price", 0) or 0
            enriched_payload = {
                **order_request,
                "decision_id": signal.get("decision_id"),
                "strategy": signal.get("strategy"),
                "timeframe": signal.get("timeframe"),
                "size_usd": signal.get("size_usd", 0),
                # Price aliases: producer wrote signal_price; simulator reads entry_price.
                "signal_price": signal_entry_price,
                "entry_price": signal_entry_price,
                # Size aliases: producer wrote quantity (in order_request); simulator reads final_size.
                "final_size": order_request.get("quantity", qty_from_sizing),
                # STEP 1.5.2: Pass experiment_id to execution pipeline
                "experiment_id": signal.get("experiment_id", "baseline_btc"),  # Safe fallback
                # Phase LIVE-3a: confidence shaping audit trail.
                "base_confidence": conf_breakdown.get("base"),
                "adjusted_confidence": adjusted_conf,
                "confidence_breakdown": conf_breakdown,
                "regime_at_entry": adj_regime,
                # Phase LIVE-3d: market-context audit (no logic, just data).
                "volatility_1h_20": market_ctx.get("volatility_1h_20"),
                "ma5_1h": market_ctx.get("ma5_1h"),
                "distance_to_ma5_1h": market_ctx.get("distance_to_ma5_1h"),
                "market_ctx_candles_used": market_ctx.get("candles_used"),
                # Phase LIVE-3d-fix: which provider produced the ctx (binance/
                # coinbase/none). Lets forensics tell apart legit nulls
                # (provider outage) from real low-vol signals.
                "market_ctx_source": market_ctx.get("source", "unknown"),
            }
            
            # Enqueue напрямую через ExecutionQueueRepository
            enqueue_result = await self.queue_repo.enqueue(
                job_id=job_id,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
                symbol=signal["symbol"],
                exchange="binance",
                action="EXECUTE_ORDER",
                priority=80,  # ENTRY priority
                payload=enriched_payload,
                # Phase LIVE-3a: enqueue with shaped confidence (was flat 0.60).
                confidence=adjusted_conf
            )
            
            if enqueue_result.get("accepted"):
                logger.info(
                    "EXECUTION_QUEUED symbol=%s side=%s job_id=%s",
                    signal["symbol"],
                    signal["side"],
                    job_id
                )
                return {
                    "ok": True,
                    "job_id": job_id
                }
            else:
                reason = enqueue_result.get("reason", "unknown")
                logger.warning(
                    "EXECUTION_REJECTED symbol=%s reason=%s",
                    signal["symbol"],
                    reason
                )
                return {
                    "ok": False,
                    "reason": reason,
                    "job_id": job_id
                }

        except Exception as e:
            logger.exception("ExecutionBridge.submit failed: %s", e)
            return {
                "ok": False,
                "error": str(e)
            }

    def _resolve_size(self, signal: Dict[str, Any]) -> float:
        """
        Resolve position size for signal.
        
        Sprint R1: Read qty from DynamicRiskEngine sizing
        Fallback: 0.001 if sizing not present (safety)
        """
        sizing = signal.get("sizing", {})
        qty = sizing.get("qty")
        
        if qty is None or qty <= 0:
            logger.warning(
                "ExecutionBridge._resolve_size: signal missing sizing.qty, using fallback 0.001"
            )
            return 0.001
        
        return float(qty)


# Singleton
_execution_bridge_instance: Optional[ExecutionBridge] = None


def init_execution_bridge(queue_repo) -> ExecutionBridge:
    """Initialize ExecutionBridge with queue_repo."""
    global _execution_bridge_instance
    _execution_bridge_instance = ExecutionBridge(queue_repo=queue_repo)
    return _execution_bridge_instance


def get_execution_bridge() -> ExecutionBridge:
    """Get ExecutionBridge singleton."""
    if _execution_bridge_instance is None:
        raise RuntimeError("ExecutionBridge not initialized - call init_execution_bridge() first")
    return _execution_bridge_instance
