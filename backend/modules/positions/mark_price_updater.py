"""
Mark-Price Updater — background daemon that refreshes current_price / mark_price
and recomputes unrealized_pnl on every ACTIVE trading_case.

Phase closing-loop.MARK (2026-04-23):
  Architect directive: "Без live mark-price updater система торгует, но рынок
  в неё не поступает. PnL — единственный источник правды."

Responsibilities (and strict non-responsibilities):
  ✅ READ active trading_cases
  ✅ FETCH latest price per (unique symbol)
  ✅ COMPUTE unrealized_pnl = qty * (mark - entry) * (+1 LONG / -1 SHORT)
  ✅ UPDATE case.current_price, case.mark_price, case.unrealized_pnl,
     case.unrealized_pnl_pct, case.mark_updated_at
  ❌ does NOT open/close positions
  ❌ does NOT touch execution flow, decisions, router, guard, detector
  ❌ does NOT cache prices or overlay logic
  ❌ does NOT create new trading_cases

Running cadence: every 8 seconds (configurable). One price fetch per unique
symbol per tick — not per case — so a hundred BTC positions cost one HTTP
call per tick.

Safety:
  - Any exception in the inner loop is swallowed and logged; the outer
    loop never dies.
  - Uses asyncio.to_thread() to offload the synchronous BinanceProvider
    HTTP call so the FastAPI event loop is not blocked.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def _fetch_price(symbol: str) -> Optional[float]:
    """
    Single-symbol price fetch via BinanceProvider (sync call offloaded to
    a thread so we don't stall the event loop).

    Uses the ``/ticker/price`` endpoint — the canonical mark-price source
    (no interval, no cache, ~50 ms round-trip). Returns None on any
    error / missing data.
    """
    try:
        from modules.scanner.market_data.binance_provider import (
            get_market_data_provider,
        )
        provider = get_market_data_provider()
        price = await asyncio.to_thread(
            provider.get_ticker_price, symbol
        )
        if price is None:
            return None
        p = float(price)
        if p <= 0:
            return None
        return p
    except Exception as e:
        logger.debug(f"[MarkUpdater] price fetch failed for {symbol}: {e}")
        return None


def _compute_pnl(
    side: str, entry: float, mark: float, qty: float
) -> Dict[str, float]:
    """
    Pure computation — architect-specified formula.

        LONG:  pnl = (mark  - entry) * qty
        SHORT: pnl = (entry - mark)  * qty

    Returns dict with absolute $ PnL and percentage.
    """
    if entry <= 0 or qty <= 0:
        return {"pnl": 0.0, "pnl_pct": 0.0}

    sign = 1.0 if (side or "").upper() == "LONG" else -1.0
    pnl = (mark - entry) * qty * sign
    pnl_pct = ((mark - entry) / entry) * 100.0 * sign
    return {"pnl": round(pnl, 6), "pnl_pct": round(pnl_pct, 4)}


async def _tick(db) -> int:
    """
    Single updater tick:
      - fetch all ACTIVE trading_cases
      - group by unique symbol → one price fetch per symbol
      - update each case with fresh mark + recomputed PnL

    Returns the number of cases updated this tick.
    """
    # Read phase — collect ACTIVE cases only.
    try:
        cases: List[Dict[str, Any]] = await db.trading_cases.find(
            {"status": "ACTIVE"}
        ).to_list(length=500)
    except Exception as e:
        logger.error(f"[MarkUpdater] cannot load active cases: {e}")
        return 0

    if not cases:
        return 0

    # Price fetch phase — dedupe symbols.
    unique_symbols = sorted({
        c.get("symbol") for c in cases if c.get("symbol")
    })
    prices: Dict[str, float] = {}
    for sym in unique_symbols:
        p = await _fetch_price(sym)
        if p is not None:
            prices[sym] = p

    if not prices:
        logger.warning(
            f"[MarkUpdater] no prices resolved for {len(unique_symbols)} symbols"
        )
        return 0

    # Update phase — one update_one per case.
    now = datetime.now(timezone.utc)
    updated = 0
    for c in cases:
        sym = c.get("symbol")
        mark = prices.get(sym)
        if mark is None:
            continue
        entry = float(c.get("entry_price") or c.get("avg_entry_price") or 0.0)
        qty = float(c.get("qty") or 0.0)
        side = c.get("side") or "LONG"
        pnl_info = _compute_pnl(side, entry, mark, qty)
        try:
            await db.trading_cases.update_one(
                {"case_id": c["case_id"]},
                {
                    "$set": {
                        "current_price": mark,
                        "mark_price": mark,
                        "unrealized_pnl": pnl_info["pnl"],
                        "unrealized_pnl_pct": pnl_info["pnl_pct"],
                        "mark_updated_at": now,
                    }
                },
            )
            updated += 1
        except Exception as e:
            logger.warning(
                f"[MarkUpdater] update failed for {c.get('case_id')}: {e}"
            )
    return updated


async def mark_price_updater_loop(db, interval_sec: int = 8) -> None:
    """
    Forever-loop entrypoint.

    Scheduled from server.py lifespan as an asyncio.create_task. Never
    raises — any tick-level error is logged and the loop continues.
    """
    logger.info(
        f"[MarkUpdater] started — interval={interval_sec}s (closing-loop.MARK)"
    )
    # Small initial delay so we don't race the DB init on startup.
    await asyncio.sleep(3)
    ticks = 0
    while True:
        try:
            n = await _tick(db)
            ticks += 1
            # Log a heartbeat every ~10 ticks (≈80s) so we can see
            # the loop is alive without spamming.
            if ticks % 10 == 0 or n > 0:
                logger.info(
                    f"[MarkUpdater] tick={ticks} updated={n}"
                )
        except asyncio.CancelledError:
            logger.info("[MarkUpdater] cancelled")
            raise
        except Exception as e:
            # Never die from a transient error.
            logger.error(f"[MarkUpdater] tick error: {e}")
        await asyncio.sleep(interval_sec)
