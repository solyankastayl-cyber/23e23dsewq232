"""
Shadow Outcome Evaluator (Pass 5)

Background task that closes open shadow signals after their horizon has
elapsed by reading the close price of the corresponding candle and
computing pnl_pct.

Inputs (per shadow record):
    entry_price                       — close of the signal candle
    decision.final_bias               — "bullish" | "bearish"  (neutral is filtered out at write-time)
    outcomes.{h}.horizon_close_ts     — when this horizon's candle closed
    outcomes.{h}.evaluated == False   — only unfinished work

Math:
    pnl_pct(bullish) = (exit - entry) / entry
    pnl_pct(bearish) = (entry - exit) / entry
    pnl_pct(neutral) = NEVER LOGGED — should_trade==True && bias!=neutral filter

Strict rules:
    * Read-only against the market data provider.
    * Idempotent — re-running on the same horizon is a no-op (evaluated flag).
    * Loop continues forever; per-record errors don't kill the loop.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.meta.shadow_logger import (
    DEFAULT_HORIZONS,
    find_unevaluated,
    update_outcome,
)
from modules.scanner.market_data.binance_provider import get_market_data_provider


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

TICK_SECONDS: int = int(os.environ.get("SHADOW_OUTCOME_TICK_S", "60"))
EVAL_GRACE_SECONDS: int = int(os.environ.get("SHADOW_OUTCOME_GRACE_S", "5"))

TF_SECONDS: Dict[str, int] = {
    "1M": 60, "3M": 180, "5M": 300, "15M": 900, "30M": 1800,
    "1H": 3600, "2H": 7200, "4H": 14400, "6H": 21600, "12H": 43200,
    "1D": 86400, "3D": 259200, "1W": 604800,
}


def _pnl_pct(bias: str, entry: float, exit_p: float) -> Optional[float]:
    if entry is None or exit_p is None or entry == 0:
        return None
    b = (bias or "").lower()
    if b == "bullish":
        return (exit_p - entry) / entry
    if b == "bearish":
        return (entry - exit_p) / entry
    return None  # neutral / unknown — should not happen for actionable records


# ════════════════════════════════════════════════════════════════════════════
# EVALUATOR
# ════════════════════════════════════════════════════════════════════════════

class ShadowOutcomeEvaluator:
    def __init__(self, horizons: Optional[List[str]] = None) -> None:
        self._horizons = horizons or DEFAULT_HORIZONS
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._stats: Dict[str, Any] = {
            "started_at": None,
            "last_tick_at": None,
            "ticks": 0,
            "evaluated": 0,
            "errors": 0,
            "last_error": None,
            "horizons": self._horizons,
            "tick_seconds": TICK_SECONDS,
        }

    # ----------------------------------------------------------------- public

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run(), name="shadow_outcome_evaluator")
        print("[ShadowOutcomeEvaluator] started")

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
                print(f"[ShadowOutcomeEvaluator] stop error: {e}")
        self._task = None
        print("[ShadowOutcomeEvaluator] stopped")

    def status(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

    # ------------------------------------------------------------------- loop

    async def _run(self) -> None:
        await asyncio.sleep(7)  # offset from scheduler tick
        while self._running:
            try:
                await self._tick_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._stats["errors"] += 1
                self._stats["last_error"] = f"{type(e).__name__}: {e}"
                print(f"[ShadowOutcomeEvaluator] tick error: {e}")
            try:
                await asyncio.sleep(TICK_SECONDS)
            except asyncio.CancelledError:
                raise

    async def _tick_once(self) -> None:
        self._stats["ticks"] += 1
        self._stats["last_tick_at"] = datetime.now(timezone.utc).isoformat()
        now_unix = int(time.time()) - EVAL_GRACE_SECONDS

        for h in self._horizons:
            await self._evaluate_horizon(h, now_unix)

    async def _evaluate_horizon(self, horizon: str, now_unix: int) -> None:
        records = await asyncio.to_thread(find_unevaluated, horizon, now_unix, limit=200)
        if not records:
            return
        for rec in records:
            try:
                await self._evaluate_record(rec, horizon)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._stats["errors"] += 1
                self._stats["last_error"] = f"eval {horizon}: {type(e).__name__}: {e}"
                print(f"[ShadowOutcomeEvaluator] eval failed: {e}")

    async def _evaluate_record(self, rec: Dict[str, Any], horizon: str) -> None:
        symbol = rec.get("symbol")
        timeframe = rec.get("timeframe")
        decision_id = rec.get("decision_id")
        entry_price = rec.get("entry_price")
        bias = (rec.get("decision") or {}).get("final_bias")
        horizon_close_ts = ((rec.get("outcomes") or {}).get(horizon) or {}).get("horizon_close_ts")

        if not (symbol and timeframe and decision_id and entry_price and horizon_close_ts):
            return

        tf_sec = TF_SECONDS.get(str(timeframe).upper())
        if not tf_sec:
            return

        # Find a candle with open_ts == horizon_close_ts - tf_sec.
        # Fetch a small window and pick the right one.
        target_open_ts = int(horizon_close_ts) - tf_sec
        exit_price = await asyncio.to_thread(
            _close_at_open_ts, symbol, timeframe, target_open_ts, tf_sec
        )
        if exit_price is None:
            return  # provider hadn't caught up yet — try again next tick

        pnl = _pnl_pct(bias, float(entry_price), float(exit_price))
        ok = await asyncio.to_thread(
            update_outcome, decision_id, horizon,
            exit_price=exit_price, pnl_pct=pnl,
        )
        if ok:
            self._stats["evaluated"] += 1
            print(
                f"[ShadowOutcomeEvaluator] {decision_id} {horizon} "
                f"entry={entry_price} exit={exit_price} pnl_pct={pnl}"
            )


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _close_at_open_ts(
    symbol: str,
    timeframe: str,
    target_open_ts: int,
    tf_sec: int,
) -> Optional[float]:
    """
    Return close price of the candle whose OPEN timestamp matches target_open_ts.

    Strategy: pull a small recent window (limit=20) and locate the exact
    candle. If not present (target is older than window), pull bigger.
    """
    provider = get_market_data_provider()

    # Quick attempt with a small window.
    for limit in (20, 100, 300):
        candles = provider.get_candles(symbol, timeframe, limit=limit) or []
        if not candles:
            return None
        # Provider sorts ascending by `time`.
        for c in reversed(candles):
            t = int(c.get("time") or 0)
            if t == target_open_ts:
                try:
                    return float(c.get("close"))
                except (TypeError, ValueError):
                    return None
            if t < target_open_ts:
                break  # gone past — won't find by going further back
        # If oldest fetched candle is still newer than target → expand window.
        oldest = int(candles[0].get("time") or 0)
        if oldest > target_open_ts:
            continue
        else:
            break
    return None


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

_evaluator: Optional[ShadowOutcomeEvaluator] = None


def get_outcome_evaluator() -> ShadowOutcomeEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = ShadowOutcomeEvaluator()
    return _evaluator
