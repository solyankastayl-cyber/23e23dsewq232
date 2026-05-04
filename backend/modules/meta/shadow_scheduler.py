"""
Shadow Scheduler (Pass 5) — forward-test loop.

ASYNCIO BACKGROUND TASK started on FastAPI startup. NEVER places orders.

Watchlist (per user spec):
    PRIMARY (edge candidate):
        ETHUSDT 1H  → policy: regime_selfref
    CONTROL  (baseline / null hypothesis):
        BTCUSDT 1H  → policy: baseline
        SOLUSDT 1H  → policy: baseline

Loop semantics:
    1. Every TICK_SECONDS, for each watchlist entry:
       a. Fetch candles, identify the LAST CLOSED candle (its close price + close ts).
       b. Build canonical decision_id = "{SYM}:{TF}:{candle_close_ts}".
       c. If a record with this decision_id already exists → skip (dedup).
       d. Run meta_pipeline.compute_decision().
       e. If `decision.should_trade == True` AND `final_bias != "neutral"`
          → write shadow record (with entry_price = candle close).
          Else → do nothing (no garbage in DB).

Strict rules:
    * NO order execution, NO position tracking, NO API key required.
    * Errors are logged but never propagate (loop must survive).
    * One signal per (symbol, tf, candle) MAX, enforced both at app level and
      via Mongo unique index on `decision_id`.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from modules.meta.meta_pipeline import (
    build_snapshot,
    compute_decision,
    fetch_system_health,
)
from modules.meta.shadow_logger import (
    DEFAULT_HORIZONS,
    _build_decision_id,
    has_signal,
    record_shadow_signal,
)
from modules.scanner.market_data.binance_provider import get_market_data_provider


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

# (symbol, timeframe). Policies are decided by policy_registry, NOT here.
WATCHLIST: List[Tuple[str, str]] = [
    ("ETHUSDT", "1H"),  # PRIMARY edge candidate
    ("BTCUSDT", "1H"),  # CONTROL — null hypothesis
    ("SOLUSDT", "1H"),  # CONTROL — null hypothesis
]

# Loop period. We don't need sub-minute precision for hourly TFs.
TICK_SECONDS: int = int(os.environ.get("SHADOW_SCHEDULER_TICK_S", "60"))

# Buffer past the candle close before we trust the close price.
# Avoids logging mid-candle values if the provider is slightly behind.
CLOSE_GRACE_SECONDS: int = int(os.environ.get("SHADOW_CLOSE_GRACE_S", "5"))

TF_SECONDS: Dict[str, int] = {
    "1M": 60, "3M": 180, "5M": 300, "15M": 900, "30M": 1800,
    "1H": 3600, "2H": 7200, "4H": 14400, "6H": 21600, "12H": 43200,
    "1D": 86400, "3D": 259200, "1W": 604800,
}

# Horizons → integer multiples of TF_SECONDS for h1/h3/h6.
HORIZON_MULT: Dict[str, int] = {"h1": 1, "h3": 3, "h6": 6}


# ════════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ════════════════════════════════════════════════════════════════════════════

class ShadowScheduler:
    """
    Asyncio task wrapper. Lifecycle is bound to FastAPI app.

    .start()  — call from app startup.
    .stop()   — call from app shutdown (graceful, awaits task cancel).
    """

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task[None]] = None
        self._running: bool = False
        self._stats: Dict[str, Any] = {
            "started_at": None,
            "last_tick_at": None,
            "ticks": 0,
            "logged": 0,
            "skipped_dup": 0,
            "skipped_not_actionable": 0,
            "errors": 0,
            "last_error": None,
            "watchlist": [{"symbol": s, "timeframe": tf} for s, tf in WATCHLIST],
            "tick_seconds": TICK_SECONDS,
        }

    # ------------------------------------------------------------------ public

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run(), name="shadow_scheduler")
        print("[ShadowScheduler] started")

    async def stop(self) -> None:
        self._running = False
        t = self._task
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[ShadowScheduler] stop error: {e}")
        self._task = None
        print("[ShadowScheduler] stopped")

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            **self._stats,
        }

    # ------------------------------------------------------------------- loop

    async def _run(self) -> None:
        # Slight initial delay so we don't race CoinbaseAutoInit on cold start.
        await asyncio.sleep(5)
        while self._running:
            try:
                await self._tick_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._stats["errors"] += 1
                self._stats["last_error"] = f"{type(e).__name__}: {e}"
                print(f"[ShadowScheduler] tick error: {e}")
            try:
                await asyncio.sleep(TICK_SECONDS)
            except asyncio.CancelledError:
                raise

    async def _tick_once(self) -> None:
        self._stats["ticks"] += 1
        self._stats["last_tick_at"] = datetime.now(timezone.utc).isoformat()

        # Fetch shared health once per tick (avoid 3× duplicate calls).
        health = await fetch_system_health()

        for symbol, tf in WATCHLIST:
            try:
                await self._process_pair(symbol, tf, health=health)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._stats["errors"] += 1
                self._stats["last_error"] = f"{symbol} {tf}: {type(e).__name__}: {e}"
                print(f"[ShadowScheduler] {symbol} {tf} failed: {e}")

    # --------------------------------------------------------------- per-pair

    async def _process_pair(
        self,
        symbol: str,
        timeframe: str,
        *,
        health: Dict[str, Any],
    ) -> None:
        tf_sec = TF_SECONDS.get(timeframe.upper())
        if tf_sec is None:
            return

        # Identify the last fully closed candle (with grace).
        last = await asyncio.to_thread(_last_closed_candle, symbol, timeframe, tf_sec)
        if last is None:
            return  # provider was empty / errored — nothing to log

        candle_close_ts = int(last["time"]) + tf_sec
        entry_price = float(last["close"])

        # Dedup pre-check (cheap).
        decision_id = _build_decision_id(symbol, timeframe, candle_close_ts)
        if has_signal(decision_id):
            self._stats["skipped_dup"] += 1
            return

        # Pipeline.
        decision, analysis, policy = await compute_decision(symbol, timeframe, health=health)

        # ❗ Garbage filter (per user spec).
        bias = (decision.get("final_bias") or "").lower()
        if not decision.get("should_trade") or bias == "neutral":
            self._stats["skipped_not_actionable"] += 1
            return

        # Compose horizon close timestamps.
        horizon_close_ts: Dict[str, int] = {
            h: candle_close_ts + HORIZON_MULT[h] * tf_sec for h in DEFAULT_HORIZONS
        }

        snapshot = build_snapshot(analysis, decision, current_price=entry_price)

        ins_id = record_shadow_signal(
            symbol=symbol,
            timeframe=timeframe,
            policy_name=policy.name,
            regime=decision.get("regime"),
            decision=decision,
            snapshot=snapshot,
            decision_id=decision_id,
            candle_close_ts=candle_close_ts,
            entry_price=entry_price,
            horizons=DEFAULT_HORIZONS,
            horizon_close_ts=horizon_close_ts,
            source="scheduler",
            # Phase 6 / P0
            market_regime=decision.get("market_regime"),
            score_regime=decision.get("score_regime") or decision.get("regime"),
        )

        if ins_id:
            self._stats["logged"] += 1
            mr = (decision.get("market_regime") or {}).get("label") if isinstance(decision.get("market_regime"), dict) else None
            print(
                f"[ShadowScheduler] LOGGED {symbol} {timeframe} "
                f"policy={policy.name} bias={bias} alloc={decision.get('allocation')} "
                f"score_regime={decision.get('score_regime')} market_regime={mr} "
                f"close_ts={candle_close_ts}"
            )
        else:
            # DuplicateKeyError raced us — this is expected and harmless.
            self._stats["skipped_dup"] += 1


# ════════════════════════════════════════════════════════════════════════════
# Helpers (sync — called via asyncio.to_thread)
# ════════════════════════════════════════════════════════════════════════════

def _last_closed_candle(
    symbol: str,
    timeframe: str,
    tf_sec: int,
) -> Optional[Dict[str, Any]]:
    """
    Find the last candle whose close time has already passed (with grace).
    Provider returns OHLCV dicts with `time` = candle OPEN unix seconds.
    """
    provider = get_market_data_provider()
    candles = provider.get_candles(symbol, timeframe, limit=5) or []
    if not candles:
        return None
    now_unix = int(time.time())
    cutoff = now_unix - CLOSE_GRACE_SECONDS
    closed = [c for c in candles if int(c["time"]) + tf_sec <= cutoff]
    if not closed:
        return None
    return closed[-1]


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

_scheduler: Optional[ShadowScheduler] = None


def get_shadow_scheduler() -> ShadowScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ShadowScheduler()
    return _scheduler
