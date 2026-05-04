#!/usr/bin/env python3
"""
F-TRADE v2 — Phase C.1 Watchdog
===============================

Autonomous process that runs INDEPENDENT of the collection loops.
Its job:
  1. Every WATCHDOG_INTERVAL seconds:
     a. Hit backend health endpoint (observability of API layer)
     b. Force-resolve matured shadow_trades (even if backend resolver is down)
     c. Snapshot dataset every SNAPSHOT_INTERVAL seconds (survive pod kill)
  2. Log structured metrics in [WATCHDOG] format for post-hoc review.

This is execution-layer only — zero changes to strategy logic.
"""
from __future__ import annotations
import asyncio
import logging
import os
import sys
import time
import signal
import atexit
from datetime import datetime, timezone
from typing import Optional

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, '/app/backend')
try:
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("watchdog")

# ------------------------------------------------------------------ #
#  Process lifecycle observability (same contract as phase_c)
# ------------------------------------------------------------------ #
_START_MONO = time.monotonic()


def _emit_banner() -> None:
    logger.info(
        "[PROCESS] STARTED pid=%d ppid=%d cwd=%s python=%s argv=%s",
        os.getpid(), os.getppid(), os.getcwd(), sys.executable, " ".join(sys.argv),
    )


def _install_signal_handlers() -> None:
    def _make(name):
        def _h(signum, frame):
            up = time.monotonic() - _START_MONO
            logger.warning("[PROCESS] %s received (signum=%s) after uptime=%.1fs", name, signum, up)
            raise KeyboardInterrupt(name)
        return _h
    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        try:
            signal.signal(getattr(signal, name), _make(name))
        except (AttributeError, ValueError, OSError):
            pass


def _on_exit() -> None:
    up = time.monotonic() - _START_MONO
    logger.info("[PROCESS] EXIT via atexit after uptime=%.1fs", up)


_emit_banner()
_install_signal_handlers()
atexit.register(_on_exit)

# ------------------------------------------------------------------ #
#  Config
# ------------------------------------------------------------------ #
WATCHDOG_INTERVAL = float(os.environ.get("WATCHDOG_INTERVAL", "60"))
SNAPSHOT_INTERVAL = float(os.environ.get("WATCHDOG_SNAPSHOT_INTERVAL", "900"))  # 15min
HEALTH_URL = os.environ.get("WATCHDOG_HEALTH_URL", "http://localhost:8001/api/health")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")

SNAPSHOT_DIR = "/app/data_snapshots/latest"
SNAPSHOT_SCRIPT = "/app/backend/scripts/export_snapshot.py"


# ------------------------------------------------------------------ #
#  Health probe
# ------------------------------------------------------------------ #
async def check_health() -> dict:
    """Hit backend health endpoint. Return dict of results."""
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(HEALTH_URL)
            latency_ms = (time.monotonic() - started) * 1000
            return {
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "latency_ms": round(latency_ms, 1),
                "err": None,
            }
    except Exception as e:
        return {
            "ok": False,
            "status_code": 0,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "err": str(e)[:120],
        }


# ------------------------------------------------------------------ #
#  Force-resolve matured trades
#  Direct Mongo access — no dependency on backend being up.
# ------------------------------------------------------------------ #
async def force_resolve(db) -> dict:
    """
    Find matured (resolve_at <= now) shadow_trades that are NOT yet resolved,
    and resolve them using the same algorithm as OutcomeResolver.

    Returns dict with metrics.
    """
    from modules.scanner.market_data.binance_provider import get_market_data_provider

    now = datetime.now(timezone.utc)
    started = time.monotonic()

    # Count matured unresolved BEFORE we act
    matured_before = await db.shadow_trades.count_documents({
        "horizons": {
            "$elemMatch": {"resolved": False, "resolve_at": {"$lte": now}},
        },
    })

    # Fetch candidates (cap at 200 per watchdog cycle)
    cursor = db.shadow_trades.find({
        "horizons": {
            "$elemMatch": {"resolved": False, "resolve_at": {"$lte": now}},
        },
    }).limit(200)

    provider = get_market_data_provider()
    resolved_count = 0
    oldest_matured_lag_sec = 0.0

    trades = await cursor.to_list(length=200)
    for trade in trades:
        try:
            # Fetch current price (1m candle, last close)
            symbol = trade["symbol"]
            candles = await asyncio.to_thread(provider.get_candles, symbol, "1H", 1)
            if not candles:
                continue
            current_price = float(candles[-1]["close"])

            horizons = trade.get("horizons") or []
            any_resolved = False
            for h in horizons:
                if h.get("resolved"):
                    continue
                resolve_at = h.get("resolve_at")
                if not resolve_at or resolve_at > now:
                    continue

                # Lag tracking
                lag = (now - resolve_at).total_seconds()
                if lag > oldest_matured_lag_sec:
                    oldest_matured_lag_sec = lag

                # PnL based on side
                entry = float(trade["entry_price"])
                if trade["side"] == "BUY":
                    pnl = (current_price - entry) / entry
                else:
                    pnl = (entry - current_price) / entry

                h["resolved"] = True
                h["resolved_at"] = now
                h["exit_price"] = current_price
                h["pnl"] = pnl
                any_resolved = True

            if any_resolved:
                await db.shadow_trades.update_one(
                    {"_id": trade["_id"]},
                    {"$set": {"horizons": horizons}},
                )
                resolved_count += 1
        except Exception as e:
            logger.warning("[WATCHDOG] resolve error for trade %s: %s", trade.get("_id"), e)

    # Matured-after = matured-before - resolved (approx)
    matured_after = await db.shadow_trades.count_documents({
        "horizons": {
            "$elemMatch": {"resolved": False, "resolve_at": {"$lte": now}},
        },
    })

    elapsed = time.monotonic() - started
    return {
        "matured_before": matured_before,
        "matured_after": matured_after,
        "resolved": resolved_count,
        "build_lag_sec": round(oldest_matured_lag_sec, 1),
        "duration_ms": round(elapsed * 1000, 1),
    }


# ------------------------------------------------------------------ #
#  Snapshot
# ------------------------------------------------------------------ #
async def take_snapshot() -> dict:
    """Invoke export_snapshot.py in subprocess. Returns rows_built metric."""
    started = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, SNAPSHOT_SCRIPT, SNAPSHOT_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "rc": proc.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
            "stderr_tail": (stderr.decode(errors="replace")[-200:] if stderr else ""),
        }
    except Exception as e:
        return {
            "ok": False,
            "rc": -1,
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
            "stderr_tail": str(e)[:200],
        }


# ------------------------------------------------------------------ #
#  Main loop
# ------------------------------------------------------------------ #
async def watchdog_loop() -> None:
    logger.info(
        "[WATCHDOG] config: interval=%.0fs snapshot_interval=%.0fs health_url=%s db=%s",
        WATCHDOG_INTERVAL, SNAPSHOT_INTERVAL, HEALTH_URL, DB_NAME,
    )

    async_client = AsyncIOMotorClient(MONGO_URL)
    db = async_client[DB_NAME]

    last_snapshot_mono = 0.0
    tick = 0
    try:
        while True:
            tick += 1
            tick_start = datetime.now(timezone.utc)

            # 1) Health
            h = await check_health()

            # 2) Force-resolve matured (only if health OK OR no matter — direct Mongo works anyway)
            r = await force_resolve(db)

            # 3) Snapshot (if interval elapsed)
            snap_info = None
            if (time.monotonic() - last_snapshot_mono) >= SNAPSHOT_INTERVAL:
                snap_info = await take_snapshot()
                last_snapshot_mono = time.monotonic()

            # 4) Structured log
            logger.info(
                "[WATCHDOG] tick=%d health_ok=%s health_code=%s health_ms=%.1f "
                "| matured_before=%d resolved_now=%d matured_after=%d build_lag_sec=%.1f resolve_ms=%.1f "
                "| snapshot=%s",
                tick,
                h["ok"], h["status_code"], h["latency_ms"],
                r["matured_before"], r["resolved"], r["matured_after"], r["build_lag_sec"], r["duration_ms"],
                ("ok=%s rc=%s ms=%.1f" % (snap_info["ok"], snap_info["rc"], snap_info["duration_ms"])) if snap_info else "skipped",
            )
            if snap_info and not snap_info["ok"]:
                logger.warning("[WATCHDOG] snapshot FAILED stderr=%s", snap_info["stderr_tail"])
            if not h["ok"]:
                logger.warning("[WATCHDOG] health FAILED err=%s code=%s", h["err"], h["status_code"])

            # 5) Sleep remainder of interval
            elapsed = (datetime.now(timezone.utc) - tick_start).total_seconds()
            sleep_for = max(1.0, WATCHDOG_INTERVAL - elapsed)
            await asyncio.sleep(sleep_for)
    finally:
        async_client.close()
        logger.info("[WATCHDOG] loop finished")


if __name__ == "__main__":
    try:
        asyncio.run(watchdog_loop())
    except KeyboardInterrupt:
        logger.info("[WATCHDOG] KeyboardInterrupt — clean exit")
