#!/usr/bin/env python3
"""
Phase C.3.7 — Regime Decision Pipeline Scheduler
================================================

Standalone supervisor-managed process that runs the analyze -> decide ->
alert -> state-machine pipeline on a fixed interval.

NO runtime logic changes. Pure read/analyze + writes to dedicated
collections (regime_model_metrics, regime_decisions, regime_alerts,
research_states).

Environment:
  REGIME_DECISION_INTERVAL   seconds (default 900 = 15 min)
  PHASE_B1_DB                target DB (default trading_os)
  MONGO_URL                  mongo connection
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

sys.path.insert(0, "/app/backend")
try:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
except Exception:
    pass

from pymongo import MongoClient

from modules.regime import (
    regime_accuracy_service,
    regime_decision_engine,
    regime_alerts,
    research_state_machine,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("regime_decision_scheduler")

INTERVAL = float(os.environ.get("REGIME_DECISION_INTERVAL", "900"))
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")

_START = time.monotonic()


def _banner() -> None:
    logger.info(
        "[PROCESS] STARTED pid=%d ppid=%d python=%s argv=%s",
        os.getpid(), os.getppid(), sys.executable, " ".join(sys.argv),
    )


def _install_signals() -> None:
    def _handler(name):
        def _h(signum, frame):
            up = time.monotonic() - _START
            logger.warning("[PROCESS] %s received (signum=%s) after %.1fs", name, signum, up)
            raise KeyboardInterrupt(name)
        return _h
    for s in ("SIGTERM", "SIGINT", "SIGHUP"):
        try:
            signal.signal(getattr(signal, s), _handler(s))
        except (AttributeError, ValueError, OSError):
            pass


def _on_exit() -> None:
    up = time.monotonic() - _START
    logger.info("[PROCESS] EXIT via atexit after uptime=%.1fs", up)


_banner()
_install_signals()
atexit.register(_on_exit)


def run_once(db) -> dict:
    t0 = time.monotonic()
    r_acc = regime_accuracy_service.run(db=db, persist=True)
    r_dec = regime_decision_engine.run(db=db, persist=True)
    r_alert = regime_alerts.run(db=db, persist=True)
    r_state = research_state_machine.run(db=db, persist=True)
    elapsed = (time.monotonic() - t0) * 1000.0

    # Compact structured log line
    for lane in ("phase_c", "discovery"):
        acc = r_acc["lanes"].get(lane, {})
        dec = r_dec["lanes"].get(lane, {})
        st = r_state["lanes"].get(lane, {})
        al = r_alert["lanes"].get(lane, [])
        al_types = [a["alert_type"] for a in al] if al else []
        logger.info(
            "[DECISION] lane=%s n_resolved=%s n_with_v2=%s verdict=%s conf=%s state=%s alerts=%s",
            lane,
            acc.get("n_resolved"),
            acc.get("n_with_v2"),
            dec.get("verdict"),
            dec.get("confidence"),
            st.get("state"),
            al_types,
        )
    logger.info("[DECISION] pipeline run complete in %.1fms", elapsed)
    return {"accuracy": r_acc, "decision": r_dec, "alerts": r_alert, "state": r_state}


async def loop() -> None:
    logger.info("[DECISION] config interval=%.0fs db=%s mongo=%s", INTERVAL, DB_NAME, MONGO_URL)
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    tick = 0
    try:
        while True:
            tick += 1
            started = datetime.now(timezone.utc)
            try:
                run_once(db)
            except Exception as e:
                logger.exception("[DECISION] tick=%d failed: %s", tick, e)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            sleep_for = max(5.0, INTERVAL - elapsed)
            logger.info("[DECISION] tick=%d done, sleeping %.1fs", tick, sleep_for)
            await asyncio.sleep(sleep_for)
    finally:
        client.close()
        logger.info("[DECISION] loop finished")


if __name__ == "__main__":
    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        logger.info("[DECISION] KeyboardInterrupt — clean exit")
