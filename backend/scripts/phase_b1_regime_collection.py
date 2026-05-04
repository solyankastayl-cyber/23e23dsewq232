#!/usr/bin/env python3
"""
Phase B.1.3: Regime-Aware Stateful Shadow Collection
=====================================================

Integration loop: Market Data → Regime → Router → StateManager → Generator → Validator(Observer) → Shadow

Key properties (F-TRADE v2):
  1. One generator per (strategy, symbol, tf) — owned by GeneratorStateManager.
  2. warmup runs ONCE (on cold start or process restart via Mongo checkpoint).
  3. On each cycle: update(latest_candle) → dedup → maybe_generate() → observe.
  4. Validator is observer-only: logs + metrics, never drops signals.
  5. State survives process restart via MongoDB `generator_state` collection.

CLI:
  --max-cycles N      : stop after N cycles (for smoke-tests). 0 = unlimited.
  --sleep-seconds S   : sleep between cycles (default: --interval * 60).
  --interval M        : legacy — minutes between cycles.
  --experiment ID     : experiment tag for shadow_trades.
  --target T          : stop after T resolved trades (0 = ignore).
  --horizon H         : shadow trade horizon in hours.
"""

import asyncio
import sys
import os
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, '/app/backend')

# Load /app/backend/.env so subprocess sees MONGO_URL / DB_NAME
try:
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
except Exception:
    pass

# Route INFO logs to stdout so downstream smoke tests can grep them
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    stream=sys.stdout,
)
# Silence very chatty universe scanner unless DEBUG
logging.getLogger("modules.market_intelligence").setLevel(logging.WARNING)

# ------------------------------------------------------------------ #
#  Process lifecycle observability (execution-layer only)
#
#  Goal: turn silent `kill -9` from sandbox into a diagnosable event.
#  We register SIGTERM / SIGINT / SIGHUP handlers that log the signal
#  before the process goes down, plus an atexit hook that records the
#  exit reason. If the process just vanishes with no atexit / no
#  signal log — that is itself a diagnostic: sandbox OOM / cgroup
#  kill with SIGKILL (uncatchable).
# ------------------------------------------------------------------ #
import signal as _signal_mod
import atexit as _atexit_mod
import time as _time_mod

_PROCESS_START_MONO = _time_mod.monotonic()

def _emit_banner() -> None:
    logger = logging.getLogger("phase_c.lifecycle")
    try:
        ppid = os.getppid()
    except Exception:
        ppid = -1
    logger.info(
        "[PROCESS] STARTED pid=%d ppid=%d cwd=%s python=%s argv=%s",
        os.getpid(), ppid, os.getcwd(), sys.executable, " ".join(sys.argv),
    )

def _install_signal_handlers() -> None:
    logger = logging.getLogger("phase_c.lifecycle")

    def _make_handler(name: str):
        def _handler(signum, frame):
            uptime = _time_mod.monotonic() - _PROCESS_START_MONO
            logger.warning(
                "[PROCESS] %s received (signum=%s) after uptime=%.1fs — shutting down",
                name, signum, uptime,
            )
            # Re-raise as KeyboardInterrupt so the asyncio loop unwinds cleanly
            raise KeyboardInterrupt(f"{name} received")
        return _handler

    for sig_name in ("SIGTERM", "SIGINT", "SIGHUP"):
        try:
            sig = getattr(_signal_mod, sig_name)
            _signal_mod.signal(sig, _make_handler(sig_name))
        except (AttributeError, ValueError, OSError):
            # Some signals not available on all platforms / contexts
            pass

def _on_exit() -> None:
    logger = logging.getLogger("phase_c.lifecycle")
    uptime = _time_mod.monotonic() - _PROCESS_START_MONO
    logger.info("[PROCESS] EXIT via atexit after uptime=%.1fs", uptime)

_emit_banner()
_install_signal_handlers()
_atexit_mod.register(_on_exit)

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from modules.market_intelligence.universe_scanner import scan_market_universe
from modules.scanner.market_data.binance_provider import get_market_data_provider

from modules.regime.market_regime import (
    get_regime_detector,
    get_strategy_router,
    get_signal_validator,
    RegimeType,
)
# Shadow-only V2 detector (Phase C.2). Observability only — no routing/execution impact.
from modules.regime.regime_guard import (
    read_short_v2_guard_flag,
    should_skip_short,
    log_guard_skip,
)
from modules.regime.market_regime_v2 import (
    detect_regime_v2,
    rolling_mean_series,
    calc_slope,
)
from modules.state.generator_state_manager import get_state_manager
from modules.signal_generator.multi_asset_generator import MultiAssetGenerator
from modules.signal_generator.trend_pullback_long_generator import TrendPullbackLongGenerator
from modules.signal_generator.breakout_long_generator import BreakoutLongGenerator


# ------------------------------------------------------------------ #
#  Generator factories (one per strategy)
# ------------------------------------------------------------------ #
def _short_trend_factory(symbol: str, timeframe: str) -> MultiAssetGenerator:
    """Factory for SHORT_TREND strategy (MA3/MA5/MA20 SHORT-only)."""
    return MultiAssetGenerator(symbol=symbol, timeframe=timeframe)


def _long_pullback_factory(symbol: str, timeframe: str) -> TrendPullbackLongGenerator:
    """
    Factory for LONG_PULLBACK strategy (UPTREND → pullback to MA20 → bullish candle).

    Strategy parameters are FROZEN by Phase B.2 contract:
      - pullback_threshold = 0.4% from MA20
      - min_body_pct       = 0.1%
      - trend_period       = MA50
    """
    return TrendPullbackLongGenerator(symbol=symbol, timeframe=timeframe)


def _long_breakout_factory(symbol: str, timeframe: str) -> BreakoutLongGenerator:
    """
    Factory for LONG_BREAKOUT strategy (breakout + volume + strength + distance).

    Strategy parameters are FROZEN by Phase B.3 contract:
      - lookback_period       = 20
      - volume_multiplier     = 1.5x
      - min_close_strength    = 0.7
      - max_breakout_distance = 0.3%
    """
    return BreakoutLongGenerator(symbol=symbol, timeframe=timeframe)


STRATEGY_FACTORIES = {
    "SHORT_TREND": _short_trend_factory,
    "LONG_PULLBACK": _long_pullback_factory,
    "LONG_BREAKOUT": _long_breakout_factory,
}


# ------------------------------------------------------------------ #
#  Shadow trade persistence (async — trades, features)
# ------------------------------------------------------------------ #
async def create_shadow_trade(
    db,
    signal: Dict[str, Any],
    regime_info: Dict[str, Any],
    horizon_hours: int,
    experiment_id: str,
    regime_v2_debug: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=horizon_hours)

    trade = {
        "experiment_id": experiment_id,
        "symbol": signal["symbol"],
        "timeframe": signal.get("timeframe"),
        "side": signal["side"],
        "entry_price": signal["price"],
        "entry_time": now,
        "features": {
            **signal.get("features", {}),
            # SHORT_TREND flat fields (None for LONG_PULLBACK — harmless)
            "short_ma": signal.get("short_ma"),
            "long_ma": signal.get("long_ma"),
            "trend_ma": signal.get("trend_ma"),
            "spread_pct": signal.get("spread_pct"),
            # Shared
            "confidence": signal.get("confidence"),
            "source": signal.get("source"),
            "regime": regime_info["regime"],
            "regime_confidence": regime_info["confidence"],
            "allowed_strategies": regime_info["allowed_strategies"],
            "strategy": regime_info.get("strategy"),
            "last_candle_ts": signal.get("last_candle_ts"),
            "validator_warn": regime_info.get("validator_warn", False),
            "validator_warn_reason": regime_info.get("validator_warn_reason"),
        },
        # Shadow v2 debug — Phase C.2 observability. Zero impact on routing.
        "regime_debug": regime_v2_debug,
        "horizons": [{
            "name": f"{horizon_hours}h",
            "target_exit_time": exit_time,
            "resolved": False,
            "exit_price": None,
            "pnl": None,
        }],
        "created_at": now,
        "source": "regime_aware_v2_stateful",
    }
    result = await db.shadow_trades.insert_one(trade)
    return str(result.inserted_id)


async def resolve_expired_trades(db, market_data) -> int:
    now = datetime.now(timezone.utc)
    cursor = db.shadow_trades.find({
        "horizons.resolved": False,
        "horizons.target_exit_time": {"$lte": now},
    })
    resolved = 0
    async for trade in cursor:
        try:
            symbol = trade["symbol"]
            timeframe = trade.get("timeframe", "1H")
            entry_price = trade["entry_price"]
            side = trade["side"]

            exit_price = market_data.get_last_price(symbol, timeframe)
            if exit_price is None:
                continue
            if side in ("SELL", "SHORT"):
                pnl = (entry_price - exit_price) / entry_price
            else:
                pnl = (exit_price - entry_price) / entry_price
            await db.shadow_trades.update_one(
                {"_id": trade["_id"]},
                {"$set": {
                    "horizons.0.resolved": True,
                    "horizons.0.exit_price": exit_price,
                    "horizons.0.pnl": pnl,
                    "horizons.0.resolved_at": now,
                }},
            )
            resolved += 1
        except Exception as e:
            print(f"    [resolve] error: {e}")
    return resolved


# ------------------------------------------------------------------ #
#  Core stateful generation
# ------------------------------------------------------------------ #
def _detect_regime_for_asset(
    candles: List[Dict[str, Any]],
    regime_detector,
) -> Tuple[Optional[object], Optional[float], Optional[Dict[str, Any]]]:
    """
    Compute MAs + V1 regime (canonical) + V2 shadow regime (observability only).

    Returns:
        (regime_v1, price, regime_v2_debug)

    regime_v2_debug is a plain dict safe to persist into Mongo; it includes the
    v2 verdict and all inputs (price, ma20, ma50, ma200, slopes). It is NEVER
    used to gate routing/execution — only logged and stored on the shadow trade.
    """
    if not candles or len(candles) < 50:
        return None, None, None
    closes = [c["close"] for c in candles]
    price = closes[-1]
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else ma50
    if ma50 is None:
        return None, None, None

    # ---- V1 (CANONICAL — drives the router) -------------------------------
    regime = regime_detector.detect(price, ma20, ma50, ma200)

    # ---- V2 (SHADOW — never routes anything) -----------------------------
    # slopes: last ~6 MA points, current − point 5 bars ago
    ma50_series = rolling_mean_series(closes, window=50, n=6)
    ma200_series = rolling_mean_series(closes, window=200, n=6) if len(closes) >= 205 else []
    ma50_slope = calc_slope(ma50_series, window=5) if ma50_series else 0.0
    ma200_slope = calc_slope(ma200_series, window=5) if ma200_series else 0.0

    v2 = detect_regime_v2(
        price=price,
        ma20=ma20,
        ma50=ma50,
        ma200=ma200,
        ma50_slope=ma50_slope,
        ma200_slope=ma200_slope,
    )
    v2_debug = {
        "v1": regime.regime.value,
        "v1_confidence": regime.confidence,
        "v2": v2.regime,
        "v2_reason": v2.reason,
        "price": price,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "ma50_slope": ma50_slope,
        "ma200_slope": ma200_slope,
        "disagree": regime.regime.value != v2.regime,
    }
    return regime, price, v2_debug


def generate_regime_aware_signals_stateful(
    eligible: List[Dict[str, Any]],
    market_data,
    state_manager,
    regime_detector,
    strategy_router,
    signal_validator,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Stateful signal generation pipeline.

    For each eligible (symbol, timeframe):
      1. Fetch candles.
      2. Detect regime.
      3. Route strategies (Router = primary gate).
      4. For each allowed strategy:
         a. state_manager.get_or_create(strategy, symbol, tf, factory, warmup_candles)
         b. gen.update(latest_candle) — dedup by candle['time']
         c. if new candle: gen.maybe_generate()
         d. validator.observe(signal, regime)  → observer-only
         e. state_manager.save_checkpoint(..., regime=...)
    """
    stats = {
        "total_assets": len(eligible),
        "regime_detections": {},
        "regime_v2_detections": {},   # SHADOW — does not affect routing
        "regime_disagreements": 0,    # SHADOW — how often v1 != v2
        "allowed_strategies": {},
        "signals_by_strategy": {},
        "duplicate_skips": 0,
        "cold_skips": 0,
        "fresh_warmups": 0,
        "checkpoints_saved": 0,
        "validator_warns": 0,
        "signals_generated": 0,
    }
    signals: List[Dict[str, Any]] = []

    # Phase R.1.1: boundary audit — per (symbol, tf) once per cycle.
    # Observability only; no logic change.
    _boundary_logged = set()
    _TF_SECONDS = {"15M": 900, "1H": 3600, "4H": 14400, "1D": 86400}
    from datetime import datetime as _dt, timezone as _tz
    _now_utc = _dt.now(_tz.utc)
    for asset in eligible:
        try:
            symbol = asset["symbol"]
            timeframe = asset["timeframe"]

            # Phase R.2.1: FRESHNESS_CHAIN — peek cache state BEFORE fetch
            #   This tells us whether the provider call hit cache (age>0) or
            #   forced a fresh HTTP fetch (entry absent or age_reset after
            #   the call). Read-only peek, does not mutate cache.
            _rc_cache_hit_before = False
            _rc_cache_age_before = None
            try:
                from modules.scanner.market_data import binance_provider as _bp
                _rc_ck = f"{symbol.upper()}:{timeframe.upper()}"
                _rc_entry = getattr(_bp, "_cache", {}).get(_rc_ck)
                if _rc_entry and isinstance(_rc_entry, tuple) and len(_rc_entry) >= 1:
                    import time as _tmod_rc
                    _rc_cache_age_before = int(_tmod_rc.time() - _rc_entry[0])
                    _rc_cache_hit_before = True
            except Exception:
                pass

            candles = market_data.get_candles(symbol, timeframe, limit=200)
            regime, price, regime_v2_debug = _detect_regime_for_asset(candles, regime_detector)
            if regime is None:
                continue

            regime_type = regime.regime.value
            stats["regime_detections"][regime_type] = \
                stats["regime_detections"].get(regime_type, 0) + 1

            # Shadow v2 aggregates (observability only)
            if regime_v2_debug is not None:
                v2_type = regime_v2_debug["v2"]
                stats["regime_v2_detections"][v2_type] = \
                    stats["regime_v2_detections"].get(v2_type, 0) + 1
                if regime_v2_debug["disagree"]:
                    stats["regime_disagreements"] += 1

            allowed = strategy_router.route(regime)
            for strategy in allowed:
                stats["allowed_strategies"][strategy] = \
                    stats["allowed_strategies"].get(strategy, 0) + 1

            if not allowed:
                continue

            for strategy_name in allowed:
                factory = STRATEGY_FACTORIES.get(strategy_name)
                if factory is None:
                    # Known but not yet wired (LONG_PULLBACK / LONG_BREAKOUT in B.1)
                    continue

                # Detect cold start BEFORE get_or_create
                key = state_manager._make_key(strategy_name, symbol, timeframe)
                was_cold = key not in state_manager.cache and \
                    state_manager.db.generator_state.find_one({"key": key}, {"_id": 1}) is None

                gen = state_manager.get_or_create(
                    strategy=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    factory=factory,
                    # Phase C.3d: warmup must exclude the still-forming candle
                    # at candles[-1] (its open_time stays constant for the
                    # whole TF period and its OHLCV is partial/mutating).
                    warmup_candles=candles[:-1] if len(candles) >= 2 else candles,
                )
                if was_cold:
                    stats["fresh_warmups"] += 1

                # Phase C.3d: Feed the latest CLOSED candle only.
                # Binance klines returns the currently-forming candle as the
                # last element; using candles[-1] breaks dedup semantics
                # (open_time stable for the whole TF period) and feeds partial
                # data to strategy conditions. candles[-2] is the last fully-
                # closed candle with final OHLCV. No detector/strategy/router
                # logic is changed; only the data-contract is restored.
                latest = candles[-2] if len(candles) >= 2 else candles[-1]
                is_new = gen.update(latest)

                # Phase R.1.1: boundary audit log (one line per (symbol, tf) per cycle)
                _pair_key = f"{symbol}:{timeframe}"
                if _pair_key not in _boundary_logged:
                    _boundary_logged.add(_pair_key)
                    _tf_sec = _TF_SECONDS.get(timeframe, 0)
                    _latest_ts = latest.get("time", 0) if isinstance(latest, dict) else 0
                    try:
                        _lts_int = int(_latest_ts)
                    except Exception:
                        _lts_int = 0
                    # cache age peek (best effort — does not affect logic)
                    # Phase R.2.1: fixed cache key — was "SYM:TF:500", real key is "SYM:TF"
                    _cache_age_sec = "na"
                    try:
                        from modules.scanner.market_data import binance_provider as _bp
                        _ck = f"{symbol.upper()}:{timeframe.upper()}"
                        _cache_tuple = getattr(_bp, "_cache", {}).get(_ck)
                        if _cache_tuple and isinstance(_cache_tuple, tuple) and len(_cache_tuple) >= 1:
                            import time as _tmod
                            _cache_age_sec = int(_tmod.time() - _cache_tuple[0])
                    except Exception:
                        pass
                    if _tf_sec > 0 and _lts_int > 0:
                        _close_ts = _lts_int + _tf_sec
                        _now_ts = int(_now_utc.timestamp())
                        _sec_since_close = _now_ts - _close_ts
                        _stored_ts = getattr(gen, "last_candle_ts", None)
                        _lane_tag = getattr(state_manager, "lane", None) or "legacy"
                        print(
                            f"[BOUNDARY] lane={_lane_tag} symbol={symbol} tf={timeframe} "
                            f"now={_now_utc.strftime('%H:%M:%SZ')} "
                            f"latest_closed_ts={_lts_int} "
                            f"sec_since_close={_sec_since_close} "
                            f"is_new={is_new} "
                            f"stored_last_ts={_stored_ts} "
                            f"cache_age_sec={_cache_age_sec}"
                        )

                        # Phase R.2.1: FRESHNESS_CHAIN — deeper audit of the
                        # data-freshness layer. Observability only, no logic
                        # change. One grep-friendly line per (symbol, tf) per
                        # cycle. Fields:
                        #   provider_latest_ts   — time of provider's newest
                        #                          (possibly still-forming)
                        #                          candle; candles[-1].time
                        #   provider_prev_ts     — time of provider's second-
                        #                          newest candle (the last
                        #                          closed one the provider has)
                        #                          = candles[-2].time
                        #   provider_cache_hit   — was this get_candles() call
                        #                          served from _cache?
                        #                          (true = age>0 before call)
                        #   provider_cache_age_sec — age of cache entry just
                        #                          BEFORE get_candles(); na if
                        #                          cache miss / entry absent.
                        #   selected_closed_ts   — consumer's chosen closed
                        #                          candle = candles[-2].time
                        #                          (== latest.time here)
                        #   stored_last_candle_ts — generator's remembered
                        #                          last candle ts from state
                        try:
                            _prov_latest_ts = None
                            _prov_prev_ts = None
                            if isinstance(candles, list) and len(candles) >= 1:
                                _c_last = candles[-1]
                                if isinstance(_c_last, dict):
                                    _prov_latest_ts = int(_c_last.get("time", 0)) or None
                            if isinstance(candles, list) and len(candles) >= 2:
                                _c_prev = candles[-2]
                                if isinstance(_c_prev, dict):
                                    _prov_prev_ts = int(_c_prev.get("time", 0)) or None
                            _selected_closed_ts = _lts_int  # latest.time
                            _cache_hit_val = "true" if _rc_cache_hit_before else "false"
                            _cache_age_val = (
                                _rc_cache_age_before
                                if _rc_cache_age_before is not None
                                else "na"
                            )
                            print(
                                f"[FRESHNESS_CHAIN] lane={_lane_tag} "
                                f"symbol={symbol} tf={timeframe} "
                                f"now={_now_utc.strftime('%H:%M:%SZ')} "
                                f"provider_latest_ts={_prov_latest_ts} "
                                f"provider_prev_ts={_prov_prev_ts} "
                                f"provider_cache_hit={_cache_hit_val} "
                                f"provider_cache_age_sec={_cache_age_val} "
                                f"selected_closed_ts={_selected_closed_ts} "
                                f"stored_last_candle_ts={_stored_ts} "
                                f"is_new={is_new}"
                            )
                        except Exception as _rc_err:
                            # Safe-first: observability must never break the
                            # live loop. Swallow and continue.
                            print(f"[FRESHNESS_CHAIN] lane={_lane_tag} symbol={symbol} tf={timeframe} error={_rc_err}")
                if not is_new:
                    stats["duplicate_skips"] += 1
                    # Still checkpoint — updated_at / regime info evolves
                    if state_manager.save_checkpoint(
                        strategy_name, symbol, timeframe, gen, regime=regime_type
                    ):
                        stats["checkpoints_saved"] += 1
                    continue

                if not getattr(gen, "is_warm", False):
                    stats["cold_skips"] += 1
                    if state_manager.save_checkpoint(
                        strategy_name, symbol, timeframe, gen, regime=regime_type
                    ):
                        stats["checkpoints_saved"] += 1
                    continue

                signal = gen.maybe_generate()

                # Always checkpoint state after update (price/ts changed)
                if state_manager.save_checkpoint(
                    strategy_name, symbol, timeframe, gen, regime=regime_type
                ):
                    stats["checkpoints_saved"] += 1

                if not signal:
                    continue

                # Observer-only validator (never drops)
                report = signal_validator.observe(signal, regime, strategy=strategy_name)
                if report.get("warn"):
                    stats["validator_warns"] += 1

                enriched = dict(signal)
                enriched["regime_info"] = {
                    "regime": regime_type,
                    "confidence": regime.confidence,
                    "allowed_strategies": allowed,
                    "strategy": strategy_name,
                    "validator_warn": report.get("warn", False),
                    "validator_warn_reason": report.get("warn_reason"),
                }
                # Attach v2 shadow debug (observability only). Safe if None.
                if regime_v2_debug is not None:
                    enriched["regime_v2_debug"] = regime_v2_debug
                    # Per-signal structured line — easy to grep after the run.
                    try:
                        print(
                            f"[REGIME_SHADOW] symbol={symbol} tf={timeframe} "
                            f"strategy={strategy_name} side={signal.get('side')} "
                            f"v1={regime_v2_debug['v1']} v2={regime_v2_debug['v2']} "
                            f"disagree={regime_v2_debug['disagree']} "
                            f"price={regime_v2_debug['price']:.6f} "
                            f"ma50={regime_v2_debug['ma50']:.6f} "
                            f"ma200={regime_v2_debug['ma200']:.6f} "
                            f"slope50={regime_v2_debug['ma50_slope']:.6f} "
                            f"slope200={regime_v2_debug['ma200_slope']:.6f} "
                            f"v2_reason={regime_v2_debug['v2_reason']}"
                        )
                    except Exception:
                        pass
                signals.append(enriched)
                stats["signals_generated"] += 1
                stats["signals_by_strategy"][strategy_name] = \
                    stats["signals_by_strategy"].get(strategy_name, 0) + 1
        except Exception as e:
            print(f"      [gen] error on {asset.get('symbol')} {asset.get('timeframe')}: {e}")
    return signals, stats


# ------------------------------------------------------------------ #
#  Main loop
# ------------------------------------------------------------------ #
async def phase_b1_collection_loop(
    target_trades: int = 0,
    horizon_hours: int = 4,
    cycle_sleep_seconds: float = 900.0,
    experiment_id: str = "phase_b1_regime_aware",
    max_cycles: int = 0,
    lane: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    lane_tag: str = "[PHASE_C]",
):
    print("=" * 70)
    print(" PHASE B.1.3: REGIME-AWARE STATEFUL COLLECTION")
    print("=" * 70)
    print(f"experiment : {experiment_id}")
    print(f"lane       : {lane!r}")
    print(f"symbols    : {len(symbols) if symbols else 'default'}")
    print(f"timeframes : {timeframes if timeframes else 'default'}")
    print(f"horizon_h  : {horizon_hours}")
    print(f"sleep_s    : {cycle_sleep_seconds}")
    print(f"target     : {target_trades if target_trades > 0 else 'unlimited'}")
    print(f"max_cycles : {max_cycles if max_cycles > 0 else 'unlimited'}")
    print("=" * 70)

    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('PHASE_B1_DB', 'trading_os')

    async_client = AsyncIOMotorClient(mongo_url)
    db_async = async_client[db_name]

    sync_client = MongoClient(mongo_url)
    db_sync = sync_client[db_name]

    market_data = get_market_data_provider()
    regime_detector = get_regime_detector()
    strategy_router = get_strategy_router()
    signal_validator = get_signal_validator(db=db_sync)  # persists validator metrics
    # Lane-isolated state manager \u2014 prevents race on shared generator_state keys
    # when phase_c and discovery_matrix_live run concurrently.
    state_manager = get_state_manager(db_sync, lane=lane)

    cycle = 0
    total_created = 0
    total_resolved = 0
    # Phase F1: pod suspension detector (runtime integrity observability).
    # We track the wall-clock timestamp at the end of each cycle sleep; if the
    # next cycle starts more than `suspension_threshold_sec` AFTER the expected
    # wakeup, the pod was frozen by the sandbox. Emit a [POD_SUSPENSION_DETECTED]
    # line and force-reload generator state from the DB checkpoint so we don't
    # carry stale in-memory state through the gap. Read + log + reload; no change
    # to detector / router / guard / generator semantics.
    _last_cycle_end_ts = None
    _suspension_threshold_sec = max(cycle_sleep_seconds * 2, 60)
    cumulative = {
        "downtrend_cycles": 0,
        "uptrend_cycles": 0,
        "range_cycles": 0,
        "short_allowed": 0,
        "long_pullback_allowed": 0,
        "long_breakout_allowed": 0,
        "short_fired": 0,
        "long_pullback_fired": 0,
        "long_breakout_fired": 0,
        "short_trades": 0,
        "long_pullback_trades": 0,
        "long_breakout_trades": 0,
        "validator_warns": 0,
        "duplicate_skips": 0,
        "cold_skips": 0,
        "checkpoints_saved": 0,
        "fresh_warmups": 0,
        "pod_suspension_events": 0,
        "pod_suspension_total_gap_sec": 0,
    }

    try:
        while True:
            cycle += 1
            cycle_started = datetime.now(timezone.utc)

            # Phase F1: pod suspension detector.
            # If more than `_suspension_threshold_sec` wall-clock seconds passed
            # between the END of the previous cycle's sleep and NOW, the sandbox
            # kernel froze the process. This is not a cycle-took-too-long
            # problem — this is a runtime-didn't-exist problem. All downstream
            # analysis (guard, edge, boundary-aware validation) is invalid until
            # the gap is acknowledged.
            if _last_cycle_end_ts is not None:
                _gap_sec = (cycle_started - _last_cycle_end_ts).total_seconds()
                # Expected gap between cycle_end and next cycle_start is near 0.
                # (we sleep INSIDE the cycle body, then loop — so at this point
                # _last_cycle_end_ts is AFTER that sleep). A real suspension is
                # anything beyond threshold.
                if _gap_sec > _suspension_threshold_sec:
                    _lane_tag = getattr(state_manager, "lane", None) or "legacy"
                    _gap_int = int(_gap_sec)
                    _missed_boundaries_1h = _gap_int // 3600
                    _missed_boundaries_4h = _gap_int // 14400
                    cumulative["pod_suspension_events"] += 1
                    cumulative["pod_suspension_total_gap_sec"] += _gap_int
                    print(
                        f"[POD_SUSPENSION_DETECTED] lane={_lane_tag} "
                        f"cycle={cycle} "
                        f"gap_sec={_gap_int} "
                        f"threshold_sec={int(_suspension_threshold_sec)} "
                        f"last_cycle_end={_last_cycle_end_ts.strftime('%Y-%m-%dT%H:%M:%SZ')} "
                        f"resumed_at={cycle_started.strftime('%Y-%m-%dT%H:%M:%SZ')} "
                        f"missed_1h_boundaries={_missed_boundaries_1h} "
                        f"missed_4h_boundaries={_missed_boundaries_4h}"
                    )
                    # Force-reload generator state from MongoDB checkpoint — the
                    # in-memory cache is stale by definition after a gap this
                    # large. The next cycle's get_or_create() calls will then
                    # restore generators from persisted `generator_state` docs,
                    # re-triggering warmup only if a checkpoint is missing.
                    # This is idempotent: reload only reads from the DB.
                    try:
                        if hasattr(state_manager, "clear_cache"):
                            state_manager.clear_cache()
                            print(
                                f"[POD_SUSPENSION_DETECTED] lane={_lane_tag} "
                                f"state_reload=ok method=clear_cache "
                                f"next_cycle_will_reload_from_db=true"
                            )
                        else:
                            print(
                                f"[POD_SUSPENSION_DETECTED] lane={_lane_tag} "
                                f"state_reload=skipped reason=no_reload_api"
                            )
                    except Exception as _re_exc:
                        print(
                            f"[POD_SUSPENSION_DETECTED] lane={_lane_tag} "
                            f"state_reload=error err={_re_exc}"
                        )

            print("─" * 70)
            print(f"Cycle {cycle} @ {cycle_started.strftime('%H:%M:%S')}")
            print("─" * 70)

            try:
                print("[1/5] Resolving expired trades...")
                resolved = await resolve_expired_trades(db_async, market_data)
                if resolved:
                    print(f"      resolved={resolved}")
                    total_resolved += resolved

                print("[2/5] Scanning universe...")
                universe = await scan_market_universe(symbols=symbols, timeframes=timeframes)
                eligible = [a for a in universe if a.get("eligible", False)]
                print(f"      eligible={len(eligible)}")
                if not eligible:
                    await asyncio.sleep(cycle_sleep_seconds)
                    # Phase F1: record end-of-sleep wall-clock even on early
                    # continue; otherwise suspension detector misses gaps that
                    # happen when universe is empty.
                    _last_cycle_end_ts = datetime.now(timezone.utc)
                    continue

                print("[3/5] Stateful signal generation...")
                signals, stats = generate_regime_aware_signals_stateful(
                    eligible,
                    market_data,
                    state_manager,
                    regime_detector,
                    strategy_router,
                    signal_validator,
                )
                print(f"      regime_detections: {stats['regime_detections']}")
                print(f"      allowed_strategies: {stats['allowed_strategies']}")
                print(
                    f"      fresh_warmups={stats['fresh_warmups']} "
                    f"dup_skips={stats['duplicate_skips']} "
                    f"cold_skips={stats['cold_skips']} "
                    f"checkpoints={stats['checkpoints_saved']} "
                    f"validator_warns={stats['validator_warns']} "
                    f"signals={stats['signals_generated']}"
                )

                # update cumulative
                if "DOWNTREND" in stats["regime_detections"]:
                    cumulative["downtrend_cycles"] += 1
                if "UPTREND" in stats["regime_detections"]:
                    cumulative["uptrend_cycles"] += 1
                if "RANGE" in stats["regime_detections"]:
                    cumulative["range_cycles"] += 1
                cumulative["short_allowed"] += stats["allowed_strategies"].get("SHORT_TREND", 0)
                cumulative["long_pullback_allowed"] += stats["allowed_strategies"].get("LONG_PULLBACK", 0)
                cumulative["long_breakout_allowed"] += stats["allowed_strategies"].get("LONG_BREAKOUT", 0)
                cumulative["short_fired"] += stats["signals_by_strategy"].get("SHORT_TREND", 0)
                cumulative["long_pullback_fired"] += stats["signals_by_strategy"].get("LONG_PULLBACK", 0)
                cumulative["long_breakout_fired"] += stats["signals_by_strategy"].get("LONG_BREAKOUT", 0)
                cumulative["validator_warns"] += stats["validator_warns"]
                cumulative["duplicate_skips"] += stats["duplicate_skips"]
                cumulative["cold_skips"] += stats["cold_skips"]
                cumulative["checkpoints_saved"] += stats["checkpoints_saved"]
                cumulative["fresh_warmups"] += stats["fresh_warmups"]

                cycle_trades_by_strategy: Dict[str, int] = {
                    "SHORT_TREND": 0,
                    "LONG_PULLBACK": 0,
                    "LONG_BREAKOUT": 0,
                }

                if not signals:
                    print("      (no signals this cycle)")
                else:
                    # --- Phase C.3 SHORT v2 Guardrail (feature-flagged) -----
                    # OFF by default. When enabled via `regime_controls`,
                    # skips SHORT_TREND signals that v2 does not confirm as
                    # DOWNTREND (or actively calls UPTREND). Pure execution-
                    # layer filter; never touches detectors/generators.
                    guard_flag = read_short_v2_guard_flag(db_sync)
                    if guard_flag["enabled"]:
                        kept = []
                        skipped = 0
                        for _s in signals:
                            ri = _s.get("regime_info", {}) or {}
                            v2dbg = _s.get("regime_v2_debug") or {}
                            strat = ri.get("strategy")
                            v1 = ri.get("regime") or v2dbg.get("v1")
                            v2 = v2dbg.get("v2") if isinstance(v2dbg, dict) else None
                            if strat == "SHORT_TREND" and should_skip_short(strat, v1, v2):
                                skipped += 1
                                log_guard_skip(
                                    db_sync, _s, ri, v2dbg if isinstance(v2dbg, dict) else {},
                                    experiment_id, lane,
                                )
                            else:
                                kept.append(_s)
                        if skipped:
                            print(
                                f"      [GUARD] short_v2_guard ENABLED: "
                                f"skipped={skipped}/{len(signals)} "
                                f"(updated_at={guard_flag.get('updated_at')})"
                            )
                        signals = kept

                    if not signals:
                        print("      (all signals filtered by guard; nothing to create)")
                    else:
                        # Sample + dedup by symbol for shadow trade creation
                        print("[4/5] Sampling signals...")
                        max_per_cycle = min(7, max(5, len(signals) // 3))
                        sample = random.sample(signals, k=max_per_cycle) \
                            if len(signals) > max_per_cycle else signals

                        seen = set()
                        deduped = []
                        for s in sample:
                            if s["symbol"] in seen:
                                continue
                            seen.add(s["symbol"])
                            deduped.append(s)

                        print(f"[5/5] Creating shadow trades ({len(deduped)})...")
                        created = 0
                        for s in deduped:
                            regime_info = s.pop("regime_info")
                            v2_dbg = s.pop("regime_v2_debug", None)
                            strat = regime_info.get("strategy", "UNKNOWN")
                            await create_shadow_trade(
                                db_async, s, regime_info, horizon_hours, experiment_id,
                                regime_v2_debug=v2_dbg,
                            )
                            created += 1
                            total_created += 1
                            cycle_trades_by_strategy[strat] = cycle_trades_by_strategy.get(strat, 0) + 1
                        print(f"      created={created}  by_strategy={cycle_trades_by_strategy}")

                # Update cumulative trade counters
                cumulative["short_trades"] += cycle_trades_by_strategy.get("SHORT_TREND", 0)
                cumulative["long_pullback_trades"] += cycle_trades_by_strategy.get("LONG_PULLBACK", 0)
                cumulative["long_breakout_trades"] += cycle_trades_by_strategy.get("LONG_BREAKOUT", 0)

                # ───── Structured observability line (lane-tagged) ─────
                rd = stats["regime_detections"]
                rd_v2 = stats.get("regime_v2_detections", {})
                rd_dis = stats.get("regime_disagreements", 0)
                al = stats["allowed_strategies"]
                sg = stats["signals_by_strategy"]
                trades_this_cycle = sum(cycle_trades_by_strategy.values())
                print(
                    f"{lane_tag} cycle={cycle} "
                    f"regimes: DOWNTREND={rd.get('DOWNTREND', 0)} "
                    f"UPTREND={rd.get('UPTREND', 0)} RANGE={rd.get('RANGE', 0)} "
                    f"| v2: DOWNTREND={rd_v2.get('DOWNTREND', 0)} "
                    f"UPTREND={rd_v2.get('UPTREND', 0)} RANGE={rd_v2.get('RANGE', 0)} "
                    f"disagree={rd_dis} "
                    f"| allowed: SHORT={al.get('SHORT_TREND', 0)} "
                    f"PULLBACK={al.get('LONG_PULLBACK', 0)} BREAKOUT={al.get('LONG_BREAKOUT', 0)} "
                    f"| generated: SHORT={sg.get('SHORT_TREND', 0)} "
                    f"PULLBACK={sg.get('LONG_PULLBACK', 0)} BREAKOUT={sg.get('LONG_BREAKOUT', 0)} "
                    f"| validated_warns={stats['validator_warns']} "
                    f"created_trades={trades_this_cycle} "
                    f"duplicates_skipped={stats['duplicate_skips']}"
                )
                cum_tag = lane_tag.replace("]", "_CUMULATIVE]")
                print(
                    f"{cum_tag} "
                    f"short_allowed={cumulative['short_allowed']}/short_fired={cumulative['short_fired']}/short_trades={cumulative['short_trades']} "
                    f"| pullback_allowed={cumulative['long_pullback_allowed']}/pullback_fired={cumulative['long_pullback_fired']}/pullback_trades={cumulative['long_pullback_trades']} "
                    f"| breakout_allowed={cumulative['long_breakout_allowed']}/breakout_fired={cumulative['long_breakout_fired']}/breakout_trades={cumulative['long_breakout_trades']}"
                )

                # status
                current_total = await db_async.shadow_trades.count_documents(
                    {"experiment_id": experiment_id}
                )
                resolved_total = await db_async.shadow_trades.count_documents(
                    {"experiment_id": experiment_id, "horizons.resolved": True}
                )
                print(f"\n Summary: total={current_total} resolved={resolved_total}")
                print(
                    f" Cumulative: DT={cumulative['downtrend_cycles']} "
                    f"UT={cumulative['uptrend_cycles']} RG={cumulative['range_cycles']} "
                    f"SHORT_allowed={cumulative['short_allowed']} "
                    f"LONG_PULLBACK_allowed={cumulative['long_pullback_allowed']} "
                    f"LONG_BREAKOUT_allowed={cumulative['long_breakout_allowed']} "
                    f"dup_skips={cumulative['duplicate_skips']} "
                    f"cold_skips={cumulative['cold_skips']} "
                    f"warmups={cumulative['fresh_warmups']} "
                    f"checkpoints={cumulative['checkpoints_saved']} "
                    f"warns={cumulative['validator_warns']}"
                )
                # state manager introspection (key observability)
                sm_stats = state_manager.get_stats()
                print(
                    f" StateManager: cached={sm_stats['cache_size']} "
                    f"checkpoints_in_db={sm_stats['checkpoint_count']}"
                )

                # exit conditions
                if target_trades > 0 and resolved_total >= target_trades:
                    print("\n target reached — stopping.")
                    break
                if max_cycles > 0 and cycle >= max_cycles:
                    print(f"\n max_cycles={max_cycles} reached — stopping.")
                    break
            except Exception as e:
                print(f" cycle {cycle} error: {e}")
                import traceback
                traceback.print_exc()

            elapsed = (datetime.now(timezone.utc) - cycle_started).total_seconds()
            sleep_for = max(1.0, cycle_sleep_seconds - elapsed)
            print(f"\n sleeping {sleep_for:.1f}s...")
            await asyncio.sleep(sleep_for)
            # Phase F1: record wall-clock timestamp at the END of this cycle's
            # sleep. The next loop iteration compares this to datetime.now() to
            # detect sandbox pod suspension (gap >> sleep_for means the process
            # was frozen by the kernel, not executing our sleep). Purely
            # observability — no behavior change on the happy path.
            _last_cycle_end_ts = datetime.now(timezone.utc)
    finally:
        print("\n" + "=" * 70)
        print(" PHASE B.1.3 COLLECTION FINISHED")
        print("=" * 70)
        sm_stats = state_manager.get_stats()
        print(f" total_cycles          : {cycle}")
        print(f" total_trades_created  : {total_created}")
        print(f" total_trades_resolved : {total_resolved}")
        print(f" generator_state docs  : {sm_stats['checkpoint_count']}")
        print(f" validator warnings    : {signal_validator.get_counters()}")
        async_client.close()
        sync_client.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Phase B.1.3: stateful regime-aware collection")
    p.add_argument("--target", type=int, default=0, help="stop after N resolved trades (0=ignore)")
    p.add_argument("--horizon", type=int, default=4, help="horizon in hours")
    p.add_argument("--interval", type=int, default=15, help="minutes between cycles (legacy)")
    p.add_argument("--sleep-seconds", type=float, default=None, help="override sleep between cycles (sec)")
    p.add_argument("--max-cycles", type=int, default=0, help="stop after N cycles (0=unlimited)")
    p.add_argument("--experiment", type=str, default="phase_b1_regime_aware")
    p.add_argument("--lane", type=str, default=None,
                   help="State isolation lane: 'phase_c', 'discovery', or None (legacy)")
    p.add_argument("--symbols", type=str, default=None,
                   help="Comma-separated override for UNIVERSE_SYMBOLS (discovery matrix)")
    p.add_argument("--timeframes", type=str, default=None,
                   help="Comma-separated override for TIMEFRAMES (e.g. '1H,4H')")
    p.add_argument("--log-tag", type=str, default="[PHASE_C]",
                   help="Structured log prefix (e.g. '[DISCOVERY]' for matrix_live)")
    args = p.parse_args()

    sleep_s = args.sleep_seconds if args.sleep_seconds is not None else args.interval * 60
    symbols_list = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    tfs_list = [t.strip() for t in args.timeframes.split(",")] if args.timeframes else None
    asyncio.run(phase_b1_collection_loop(
        target_trades=args.target,
        horizon_hours=args.horizon,
        cycle_sleep_seconds=sleep_s,
        experiment_id=args.experiment,
        max_cycles=args.max_cycles,
        lane=args.lane,
        symbols=symbols_list,
        timeframes=tfs_list,
        lane_tag=args.log_tag,
    ))
