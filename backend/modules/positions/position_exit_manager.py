"""
Position Exit Manager — background daemon that closes ACTIVE trading_cases
per Phase LIVE-2 minimal exit rules.

Architect directive (2026-04-23 Phase LIVE-2):
  "Без exit logic — это не trading system, это position accumulator.
   Минимальный exit, без усложнений."

Rules (applied in priority order, first match wins):
  1. TAKE_PROFIT — unrealized_pnl_pct >= +0.3%
  2. STOP_LOSS   — unrealized_pnl_pct <= -0.3%
  3. TIME_EXIT   — (now - opened_at) >= 30 minutes

On close:
  * status          = "CLOSED"
  * closed_at       = now (UTC)
  * close_reason    = "LIVE2_TP_030" | "LIVE2_SL_030" | "LIVE2_TIME_30M"
  * realized_pnl    = unrealized_pnl (snapshot at close)
  * realized_pnl_pct= unrealized_pnl_pct (snapshot at close)
  * exit_price      = mark_price (snapshot at close)
  * exit_mechanism  = "position_exit_manager"

Strict non-responsibilities:
  ❌ does not OPEN positions
  ❌ does not touch order queue / fills / execution handler
  ❌ does not cancel external orders (PAPER only for now)
  ❌ does not trail stops / move SL / move TP
  ❌ does not change strategy params
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Rule thresholds (architect-specified).
# Phase LIVE-2H (2026-04-25) — REGRESSION TO BASELINE.
# Forensic MFE/MAE diagnostic (48 trades) showed:
#   * LIVE-2  (±0.30%): WR 53.8%, +0.05%/trade, MFE/MAE = 1.26x
#   * LIVE-2D (±0.15%): WR 31.8%, -0.03%/trade, MFE/MAE = 0.73x
# Tightening to ±0.15% destroyed positive edge. Architect directive:
# revert to ±0.30%, keep TIME at 30m, and disable regime gating to
# isolate strategy edge from over-engineering. Close-reason labels
# carry a "LIVE2H_" prefix so baseline trades are cleanly separable
# from earlier phases in the next forensic pass.
TP_PCT = 0.30      # close if pnl_pct >=  +0.30
SL_PCT = -0.30     # close if pnl_pct <=  -0.30
TIME_EXIT_MIN = 30 # close if holding >= 30 minutes


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _evaluate_exit(case: Dict[str, Any], now: datetime) -> Optional[Tuple[str, str]]:
    """
    Decide whether a case should be closed.
    Returns (close_reason, rule_name) if the position must exit, else None.
    """
    pnl_pct = case.get("unrealized_pnl_pct")
    if pnl_pct is not None:
        try:
            p = float(pnl_pct)
            if p >= TP_PCT:
                return ("LIVE2D_TP_015", "TAKE_PROFIT")
            if p <= SL_PCT:
                return ("LIVE2D_SL_015", "STOP_LOSS")
        except Exception:
            pass

    opened_at = _as_utc(case.get("opened_at"))
    if opened_at is not None:
        if (now - opened_at) >= timedelta(minutes=TIME_EXIT_MIN):
            return ("LIVE2H_TIME_30M", "TIME_EXIT")

    return None


async def _tick(db) -> int:
    """
    One sweep over ACTIVE cases. Returns number of cases closed this tick.
    """
    try:
        cases: List[Dict[str, Any]] = await db.trading_cases.find(
            {"status": "ACTIVE"}
        ).to_list(length=500)
    except Exception as e:
        logger.error(f"[PositionExit] cannot load active cases: {e}")
        return 0

    if not cases:
        return 0

    now = datetime.now(timezone.utc)
    closed_count = 0

    for c in cases:
        verdict = _evaluate_exit(c, now)
        if verdict is None:
            continue

        close_reason, rule_name = verdict
        mark = c.get("mark_price") or c.get("current_price")
        realized_pnl = c.get("unrealized_pnl") or 0.0
        realized_pnl_pct = c.get("unrealized_pnl_pct") or 0.0
        case_id = c.get("case_id")

        # Idempotent close — if another process closes the same case
        # concurrently, only the first write wins (filter on status=ACTIVE).
        try:
            result = await db.trading_cases.update_one(
                {"case_id": case_id, "status": "ACTIVE"},
                {
                    "$set": {
                        "status": "CLOSED",
                        "closed_at": now,
                        "close_reason": close_reason,
                        "exit_rule": rule_name,
                        "exit_price": mark,
                        "exit_mechanism": "position_exit_manager",
                        "realized_pnl": round(float(realized_pnl), 6),
                        "realized_pnl_pct": round(float(realized_pnl_pct), 4),
                        # zero out unrealized so UI does not double-count
                        "unrealized_pnl": 0.0,
                        "unrealized_pnl_pct": 0.0,
                    }
                },
            )
            if result.modified_count > 0:
                closed_count += 1
                logger.info(
                    f"[PositionExit] CLOSED case_id={case_id} "
                    f"symbol={c.get('symbol')} side={c.get('side')} "
                    f"rule={rule_name} reason={close_reason} "
                    f"entry={c.get('entry_price')} exit={mark} "
                    f"realized_pnl={realized_pnl:+.4f} "
                    f"({realized_pnl_pct:+.4f}%)"
                )
                # Audit trail (best-effort)
                try:
                    await db.position_exit_events.insert_one(
                        {
                            "event": "POSITION_CLOSED",
                            "phase": "LIVE-2",
                            "case_id": case_id,
                            "symbol": c.get("symbol"),
                            "side": c.get("side"),
                            "strategy": c.get("strategy"),
                            "rule": rule_name,
                            "close_reason": close_reason,
                            "entry_price": c.get("entry_price"),
                            "exit_price": mark,
                            "qty": c.get("qty"),
                            "realized_pnl": round(float(realized_pnl), 6),
                            "realized_pnl_pct": round(float(realized_pnl_pct), 4),
                            "opened_at": c.get("opened_at"),
                            "closed_at": now,
                            "holding_seconds": (
                                (now - _as_utc(c.get("opened_at"))).total_seconds()
                                if c.get("opened_at") else None
                            ),
                        }
                    )
                except Exception as e:
                    logger.debug(
                        f"[PositionExit] audit insert failed for {case_id}: {e}"
                    )
        except Exception as e:
            logger.warning(
                f"[PositionExit] close failed for {case_id}: {e}"
            )

    return closed_count


async def position_exit_loop(db, interval_sec: int = 10) -> None:
    """
    Forever-loop. Scheduled from server.py lifespan.

    Never raises — any tick-level error is logged, the loop continues.
    """
    logger.info(
        f"[PositionExit] started — interval={interval_sec}s (Phase LIVE-2)  "
        f"rules: TP>={TP_PCT}%  SL<={SL_PCT}%  TIME>={TIME_EXIT_MIN}min"
    )
    # Small initial delay so we don't race mark-price updater first tick.
    await asyncio.sleep(4)
    ticks = 0
    while True:
        try:
            n = await _tick(db)
            ticks += 1
            # Heartbeat every 30 ticks (~5 minutes) or whenever we close anything.
            if n > 0 or ticks % 30 == 0:
                logger.info(f"[PositionExit] tick={ticks} closed={n}")
        except asyncio.CancelledError:
            logger.info("[PositionExit] cancelled")
            raise
        except Exception as e:
            logger.error(f"[PositionExit] tick error: {e}")
        await asyncio.sleep(interval_sec)
