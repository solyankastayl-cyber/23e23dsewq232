"""
TA Prediction Outcome Worker (Step 7)
=====================================

Async background task that walks pending prediction records and computes
their outcome once N subsequent closed candles exist on the timeframe.

Pipeline per record:
  1. Pull current candles for (symbol, tf) from chart_data_service.
  2. Identify the index corresponding to record.candle_close_ts.
  3. If at least min_horizon (h6 = 6) future closed candles exist, compute:
         return_h1, return_h3, return_h6   (signed pct from entry_price)
         max_favourable_move_pct, max_adverse_move_pct (within h6 window)
  4. Determine winning scenario using target/invalidation if present
     (scenarios_interaction_adjusted), else deterministic return threshold.
  5. Persist outcome via repository.update_prediction_outcome.

All operations are wrapped in try/except per record (error isolation).
No ML, no randomness. Pure candle arithmetic.
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

TICK_SECONDS = 60.0
MIN_HORIZON_CANDLES = 6   # h6
DIR_THRESHOLD_PCT = 0.10  # used when scenario target/invalidation absent
MAX_PENDING_PER_TICK = 50


def _utcnow():
    return datetime.now(timezone.utc)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _locate_entry_idx(
    candles: List[Dict[str, Any]],
    ts_seconds: int,
    *,
    timeframe: Optional[str] = None,
) -> int:
    """
    Return the index of the candle whose CLOSE time matches ts_seconds.

    Single source of truth for "what is the close time of a candle":
        close_ts = open_ts + tf_minutes * 60       (FIX PIPELINE bug #1)

    This mirrors `live_adapter._candle_close_ts_seconds`. We never trust a
    field named `close_time` on candle dicts because chart_data ships only
    `timestamp` (= bar OPEN time as ISO string), which would silently double
    the offset.

    On exact match returns that index. On miss, returns the nearest candle
    whose close_ts <= ts_seconds (entry candle just closed before ts).
    Returns -1 if not locatable.
    """
    if not candles or ts_seconds is None:
        return -1
    try:
        from modules.ta_prediction_intelligence.live_adapter import (
            _candle_close_ts_seconds,
            _tf_minutes,  # noqa: F401  (touched to keep import explicit)
        )
    except Exception:
        return -1
    target = int(ts_seconds)
    last_le = -1
    for i, c in enumerate(candles):
        cct = _candle_close_ts_seconds(c, timeframe or "")
        if cct is None:
            continue
        if cct == target:
            return i
        if cct < target:
            last_le = i
        else:
            # cct > target → went past, stop
            break
    return last_le


def _candle_field(c: Dict[str, Any], key: str) -> Optional[float]:
    v = c.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _compute_returns_and_extremes(
    entry_price: float,
    future_candles: List[Dict[str, Any]],
    horizons: Tuple[int, int, int] = (1, 3, 6),
) -> Dict[str, Any]:
    h1, h3, h6 = horizons
    out: Dict[str, Any] = {
        "return_h1": None,
        "return_h3": None,
        "return_h6": None,
        "max_favourable_move_pct": None,
        "max_adverse_move_pct": None,
        "volatility_future_h6": None,
    }
    if entry_price is None or entry_price <= 0 or not future_candles:
        return out
    def pct(p: float) -> float:
        return (p - entry_price) / entry_price

    if len(future_candles) >= h1:
        c = future_candles[h1 - 1]
        cl = _candle_field(c, "close")
        if cl is not None:
            out["return_h1"] = round(pct(cl), 6)
    if len(future_candles) >= h3:
        c = future_candles[h3 - 1]
        cl = _candle_field(c, "close")
        if cl is not None:
            out["return_h3"] = round(pct(cl), 6)
    if len(future_candles) >= h6:
        c = future_candles[h6 - 1]
        cl = _candle_field(c, "close")
        if cl is not None:
            out["return_h6"] = round(pct(cl), 6)

    window = future_candles[:h6]
    best = None
    worst = None
    log_returns = []
    prev_close = entry_price
    for c in window:
        hi = _candle_field(c, "high")
        lo = _candle_field(c, "low")
        cl = _candle_field(c, "close")
        if hi is not None:
            fav = pct(hi)
            if best is None or fav > best:
                best = fav
        if lo is not None:
            adv = pct(lo)
            if worst is None or adv < worst:
                worst = adv
        if cl is not None and prev_close is not None and prev_close > 0:
            try:
                log_returns.append(math.log(cl / prev_close))
            except (ValueError, ZeroDivisionError):
                pass
            prev_close = cl
    out["max_favourable_move_pct"] = round(best, 6) if best is not None else None
    out["max_adverse_move_pct"] = round(worst, 6) if worst is not None else None
    # Realized volatility over the h6 window — population stdev of log returns.
    # This is a real forward measurement; not synthetic.
    if len(log_returns) >= 2:
        mu = sum(log_returns) / len(log_returns)
        var = sum((r - mu) ** 2 for r in log_returns) / len(log_returns)
        out["volatility_future_h6"] = round(var ** 0.5, 8)
    else:
        out["volatility_future_h6"] = None
    return out


def resolve_winning_scenario(
    entry_price: float,
    scenarios_interaction_adjusted: List[Dict[str, Any]],
    future_candles: List[Dict[str, Any]],
    return_h6: Optional[float],
    *,
    dir_threshold_pct: float = DIR_THRESHOLD_PCT,
) -> str:
    """
    Deterministic rule to pick winning scenario from {bull, base, bear}.

    Resolver v2 (FIX-RESOLVER-1+2, 2026-05-04):

    Walks candles in order, with strict tie-break and an invalidation
    state-machine. The two bugs fixed by this version:

        Bug #1 — within-bar ambiguity always biased to bull
            Old: if hi>=t_bull -> 'bull' immediately (skipped t_bear check
            in the same bar). Inside a single 1H candle whose [low, high]
            range straddles BOTH narrow targets, the result was always
            'bull', regardless of which level was actually touched first.
            Fix: when both bull_target AND bear_target are crossed in the
            SAME bar, the bar is ambiguous → return 'base'.

        Bug #2 — invalidation_price was a no-op
            Old: invalidation hits were two `pass` statements. They never
            led to any decision, only target hits did. So a market that
            invalidated both directions but never hit either target fell
            through to the return_h6 fallback (with a 10% threshold).
            Fix: track `bull_dead`/`bear_dead` flags. If both die before
            either target is hit → return 'base'.

    Resolution priority (per bar, top to bottom):
        1. bull_target_hit AND bear_target_hit  -> 'base'  (within-bar tie)
        2. bull_target_hit                      -> 'bull'
        3. bear_target_hit                      -> 'bear'
        4. update bull_dead / bear_dead flags
        5. if bull_dead AND bear_dead           -> 'base'

    If the entire future_candles window is exhausted without resolution,
    fall back to the return_h6 directional threshold (UNCHANGED in this
    commit by deliberate scope — see DIR_THRESHOLD_PCT).
    """
    if entry_price is None or entry_price <= 0 or not future_candles:
        return "base"

    scen_by_name = {
        str(s.get("name") or "").lower(): s for s in (scenarios_interaction_adjusted or [])
    }
    bull = scen_by_name.get("bull") or {}
    _ = scen_by_name.get("base") or {}  # base has no target/invalidation by design
    bear = scen_by_name.get("bear") or {}

    t_bull = _safe_float(bull.get("target_price"), 0.0) or None
    inv_bull = _safe_float(bull.get("invalidation_price"), 0.0) or None
    t_bear = _safe_float(bear.get("target_price"), 0.0) or None
    inv_bear = _safe_float(bear.get("invalidation_price"), 0.0) or None

    if any(v is not None for v in (t_bull, t_bear, inv_bull, inv_bear)):
        bull_dead = False
        bear_dead = False
        for c in future_candles:
            hi = _candle_field(c, "high")
            lo = _candle_field(c, "low")

            bull_target_hit = (
                t_bull is not None and hi is not None and hi >= t_bull
            )
            bear_target_hit = (
                t_bear is not None and lo is not None and lo <= t_bear
            )

            # FIX #1 — within-bar ambiguity: both targets crossed in the
            # same bar means we cannot tell from candle data which was hit
            # first; that bar is structurally indeterminate → 'base'.
            if bull_target_hit and bear_target_hit:
                return "base"
            if bull_target_hit:
                return "bull"
            if bear_target_hit:
                return "bear"

            # FIX #2 — invalidation state machine: track which sides have
            # been killed off by their own invalidation level. The flags
            # are sticky: once a side dies, it stays dead for the rest of
            # the window.
            if (not bull_dead and inv_bull is not None
                    and lo is not None and lo <= inv_bull):
                bull_dead = True
            if (not bear_dead and inv_bear is not None
                    and hi is not None and hi >= inv_bear):
                bear_dead = True
            if bull_dead and bear_dead:
                return "base"

    # Fallback: no target/invalidation resolution within horizon — defer
    # to the directional return_h6 threshold (intentionally unchanged in
    # this commit; see DIR_THRESHOLD_PCT).
    if return_h6 is None:
        return "base"
    thr = abs(dir_threshold_pct)
    if return_h6 > thr:
        return "bull"
    if return_h6 < -thr:
        return "bear"
    return "base"


def evaluate_prediction_with_candles(
    record: Dict[str, Any],
    candles: List[Dict[str, Any]],
    *,
    min_horizon: int = MIN_HORIZON_CANDLES,
) -> Optional[Dict[str, Any]]:
    """
    Pure evaluation helper — used by worker AND by unit tests.

    Returns outcome dict, or None if not enough forward candles yet.
    Outcome shape:
        {
          return_h1, return_h3, return_h6,
          max_favourable_move_pct, max_adverse_move_pct,
          winning_scenario: 'bull'|'base'|'bear',
          evaluated_at: iso,
          candles_used: int,
        }
    """
    entry = _safe_float(record.get("entry_price"))
    if entry <= 0:
        return None
    ts = record.get("candle_close_ts")
    if not ts:
        return None

    timeframe = (record.get("timeframe") or "").upper()
    idx = _locate_entry_idx(candles, int(ts), timeframe=timeframe)
    if idx < 0:
        return None
    future = candles[idx + 1 : idx + 1 + min_horizon]
    if len(future) < min_horizon:
        return None  # not ready yet

    base = _compute_returns_and_extremes(entry, future)
    winner = resolve_winning_scenario(
        entry_price=entry,
        scenarios_interaction_adjusted=(
            record.get("scenarios_interaction_adjusted")
            or record.get("scenarios_original")
            or []
        ),
        future_candles=future,
        return_h6=base.get("return_h6"),
    )
    outcome = {
        **base,
        "winning_scenario": winner,
        "candles_used": len(future),
        "evaluated_at": _utcnow().isoformat(),
    }
    return outcome


class TAPredictionOutcomeWorker:
    def __init__(self, repository_provider=None, candles_provider=None):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._last_tick_at: Optional[datetime] = None
        self._ticks = 0
        self._evaluated = 0
        self._errors = 0
        self._last_error: Optional[str] = None
        self._repository_provider = repository_provider
        self._candles_provider = candles_provider

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "last_tick_at": self._last_tick_at.isoformat() if self._last_tick_at else None,
            "ticks": self._ticks,
            "evaluated": self._evaluated,
            "errors": self._errors,
            "last_error": self._last_error,
            "min_horizon_candles": MIN_HORIZON_CANDLES,
            "tick_seconds": TICK_SECONDS,
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._started_at = _utcnow()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def _loop(self):
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                self._errors += 1
                self._last_error = f"{type(e).__name__}: {e}"
            try:
                await asyncio.sleep(TICK_SECONDS)
            except asyncio.CancelledError:
                break

    def _get_repo(self):
        if self._repository_provider is not None:
            return self._repository_provider()
        try:
            from modules.ta_prediction_intelligence.repository import get_repository
            return get_repository()
        except Exception:
            return None

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 300):
        if self._candles_provider is not None:
            return await self._candles_provider(symbol, timeframe, limit)
        try:
            from modules.research_analytics.chart_data import get_chart_data_service
            svc = get_chart_data_service()
            chart_data = await svc.get_chart_data(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
            raw = getattr(chart_data, "candles", None) or []
            out = []
            for c in raw:
                if hasattr(c, "model_dump"):
                    out.append(c.model_dump())
                elif isinstance(c, dict):
                    out.append(c)
            return out
        except Exception:
            return []

    async def _tick(self):
        self._ticks += 1
        self._last_tick_at = _utcnow()
        repo = self._get_repo()
        if not repo:
            return
        pending = repo.get_pending_predictions(limit=MAX_PENDING_PER_TICK)
        if not pending:
            return

        # Group by (symbol, tf) to reduce candle fetches.
        by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for rec in pending:
            sym = rec.get("symbol")
            tf = rec.get("timeframe")
            if not sym or not tf:
                continue
            by_pair.setdefault((sym.upper(), tf.upper()), []).append(rec)

        for (sym, tf), records in by_pair.items():
            try:
                candles = await self._fetch_candles(sym, tf, limit=300)
            except Exception as e:
                self._errors += 1
                self._last_error = f"candles_fetch:{type(e).__name__}"
                continue
            if not candles:
                continue
            for rec in records:
                try:
                    outcome = evaluate_prediction_with_candles(rec, candles)
                    if outcome is None:
                        continue
                    ok = repo.update_prediction_outcome(
                        rec.get("prediction_id"),
                        outcome=outcome,
                        state="evaluated",
                    )
                    if ok:
                        self._evaluated += 1
                except Exception as e:
                    self._errors += 1
                    self._last_error = f"evaluate:{type(e).__name__}"
                    try:
                        repo.mark_prediction_error(rec.get("prediction_id"), str(e))
                    except Exception:
                        pass


_worker_singleton: Optional[TAPredictionOutcomeWorker] = None


def get_outcome_worker() -> TAPredictionOutcomeWorker:
    global _worker_singleton
    if _worker_singleton is None:
        _worker_singleton = TAPredictionOutcomeWorker()
    return _worker_singleton
