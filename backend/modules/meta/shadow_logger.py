"""
Shadow Logger (Pass 4.3 + Pass 5) — paper execution layer.

Records EVERY actionable meta decision (live or evaluated) into MongoDB,
BUT NEVER sends an order. Production-safe live observation.

Pass 5 additions:
  * `decision_id` — canonical dedup key:  f"{symbol}:{tf}:{candle_close_ts}"
    (NO policy in the key — same candle = same decision regardless of policy.)
  * `candle_close_ts` — int unix seconds, the close time of the candle that
    drove the decision (used by outcome evaluator).
  * `entry_price` — close of the candle that drove the decision.
  * `outcomes` — dict of horizon → outcome record:
        {
          "h1": {evaluated, exit_price, pnl_pct, evaluated_at, horizon_close_ts},
          "h3": {...},
          "h6": {...},
        }
  * `source` — "scheduler" (forward-test) | "manual" (ad-hoc /score call).

Hard rules:
  * WRITE-ONLY for the request handler — no I/O on hot path beyond insert.
  * No order emission of any kind.
  * Every record is timestamped server-side (no client clock trust).
  * Scheduler logs only when decision.should_trade==True AND final_bias!=neutral
    (caller's responsibility — keeps stats clean of garbage).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError


_COLLECTION_NAME = "meta_shadow_signals"
_client: Optional[MongoClient] = None

# Default forward-test horizons (in candles, NOT minutes).
DEFAULT_HORIZONS: List[str] = ["h1", "h3", "h6"]


def _build_decision_id(symbol: str, timeframe: str, candle_close_ts: int) -> str:
    return f"{(symbol or '').upper()}:{(timeframe or '').upper()}:{int(candle_close_ts)}"


def _empty_outcome(horizon_close_ts: Optional[int]) -> Dict[str, Any]:
    return {
        "evaluated": False,
        "exit_price": None,
        "pnl_pct": None,
        "evaluated_at": None,
        "horizon_close_ts": int(horizon_close_ts) if horizon_close_ts is not None else None,
    }


def _get_collection() -> Collection:
    global _client
    if _client is None:
        _client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = _client[os.environ.get("DB_NAME", "trading_os")]
    coll = db[_COLLECTION_NAME]
    # Idempotent index setup.
    try:
        coll.create_index([("symbol", 1), ("timeframe", 1), ("ts", DESCENDING)])
        coll.create_index([("ts", DESCENDING)])
        # Sparse unique guarantees no duplicates per (symbol, tf, candle_close_ts)
        # while remaining backward-compatible with legacy records that lack the field.
        coll.create_index(
            [("decision_id", ASCENDING)],
            unique=True,
            sparse=True,
            name="uniq_decision_id",
        )
        # Handy compound index for the outcome evaluator: scan by horizon flag fast.
        coll.create_index([("outcomes.h1.evaluated", 1)])
        coll.create_index([("outcomes.h3.evaluated", 1)])
        coll.create_index([("outcomes.h6.evaluated", 1)])
        # Phase 6 / P0: cheap aggregations by market regime label.
        coll.create_index([("market_regime_label", 1)])
    except Exception:
        pass
    return coll


# ════════════════════════════════════════════════════════════════════════════
# WRITE
# ════════════════════════════════════════════════════════════════════════════

def record_shadow_signal(
    *,
    symbol: str,
    timeframe: str,
    policy_name: str,
    regime: str,
    decision: Dict[str, Any],
    snapshot: Dict[str, Any],
    # Pass 5 additions (all optional for backward-compat with /api/meta/score)
    decision_id: Optional[str] = None,
    candle_close_ts: Optional[int] = None,
    entry_price: Optional[float] = None,
    horizons: Optional[List[str]] = None,
    horizon_close_ts: Optional[Dict[str, int]] = None,
    source: str = "manual",
    # Phase 6 / P0 additions:
    market_regime: Optional[Dict[str, Any]] = None,
    score_regime: Optional[str] = None,
) -> str:
    """
    Append one shadow record. Returns inserted id (string), or "" on failure.

    NEVER raises into the caller — failures only log. DuplicateKeyError on
    decision_id is treated as a success-equivalent skip and returns "".
    """
    try:
        # Compose canonical decision_id when caller provided candle_close_ts but
        # not the explicit id (cheap defence against drift).
        if not decision_id and candle_close_ts is not None:
            decision_id = _build_decision_id(symbol, timeframe, candle_close_ts)

        outcomes: Dict[str, Any] = {}
        for h in (horizons or DEFAULT_HORIZONS):
            ts_close = (horizon_close_ts or {}).get(h)
            outcomes[h] = _empty_outcome(ts_close)

        # Phase 6 / P0: extract market_regime label as a top-level scalar
        # for cheap filtering (Mongo $eq) without touching the full dict.
        market_regime_label: Optional[str] = None
        if isinstance(market_regime, dict):
            v = market_regime.get("label")
            if v is not None:
                market_regime_label = str(v)

        doc: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": (symbol or "").upper(),
            "timeframe": (timeframe or "").upper(),
            "policy": policy_name,
            "regime": regime,                          # back-compat (==score_regime)
            "score_regime": score_regime or regime,    # explicit alias (P0)
            "market_regime": market_regime,            # full dict {label, confidence, model_name, raw}
            "market_regime_label": market_regime_label,  # scalar for fast filtering
            "decision": {
                "final_bias":   decision.get("final_bias"),
                "score":        decision.get("strategy_score"),
                "allocation":   decision.get("allocation"),
                "should_trade": decision.get("should_trade"),
                "skip_reason":  decision.get("skip_reason"),
                "reason":       decision.get("reason"),
            },
            "snapshot": snapshot,
            "entry_price": float(entry_price) if entry_price is not None else None,
            "candle_close_ts": int(candle_close_ts) if candle_close_ts is not None else None,
            "source": source,
            "outcomes": outcomes,
        }
        # IMPORTANT: only include `decision_id` when we have a real id.
        # Mongo's sparse-unique index treats explicit null as a value, which
        # would collide across all manual /score writes. By OMITTING the
        # field for those, the sparse index correctly skips them.
        if decision_id:
            doc["decision_id"] = decision_id
        try:
            res = _get_collection().insert_one(doc)
            return str(res.inserted_id)
        except DuplicateKeyError:
            # Same candle, same decision — already logged. Not an error.
            return ""
    except Exception as exc:
        print(f"[ShadowLogger] insert failed: {exc}")
        return ""


# ════════════════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════════════════

def has_signal(decision_id: str) -> bool:
    """Cheap dedup pre-check used by the scheduler before doing real work."""
    if not decision_id:
        return False
    return _get_collection().count_documents({"decision_id": decision_id}, limit=1) > 0


def get_recent_signals(
    *,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if symbol:
        q["symbol"] = symbol.upper()
    if timeframe:
        q["timeframe"] = timeframe.upper()
    cur = _get_collection().find(q, {"_id": 0}).sort("ts", DESCENDING).limit(int(limit))
    return list(cur)


def get_stats(symbol: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
    coll = _get_collection()
    match: Dict[str, Any] = {}
    if symbol:
        match["symbol"] = symbol.upper()
    if timeframe:
        match["timeframe"] = timeframe.upper()

    total = coll.count_documents(match)
    by_regime: Dict[str, int] = {}            # back-compat: == by score_regime
    by_score_regime: Dict[str, int] = {}
    by_market_regime: Dict[str, int] = {}     # P0
    by_should_trade: Dict[str, int] = {"true": 0, "false": 0}
    by_source: Dict[str, int] = {}
    by_policy: Dict[str, int] = {}
    for r in coll.find(
        match,
        {
            "regime": 1,
            "score_regime": 1,
            "market_regime_label": 1,
            "decision.should_trade": 1,
            "source": 1,
            "policy": 1,
            "_id": 0,
        },
    ):
        rr = r.get("regime") or "unknown"
        by_regime[rr] = by_regime.get(rr, 0) + 1
        sr = r.get("score_regime") or rr
        by_score_regime[sr] = by_score_regime.get(sr, 0) + 1
        mr = r.get("market_regime_label") or "unknown"
        by_market_regime[mr] = by_market_regime.get(mr, 0) + 1
        st = (r.get("decision") or {}).get("should_trade")
        by_should_trade["true" if st else "false"] += 1
        src = r.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
        pol = r.get("policy") or "unknown"
        by_policy[pol] = by_policy.get(pol, 0) + 1
    return {
        "total": total,
        "by_regime": by_regime,                 # back-compat alias for score_regime
        "by_score_regime": by_score_regime,
        "by_market_regime": by_market_regime,   # P0
        "by_should_trade": by_should_trade,
        "by_source": by_source,
        "by_policy": by_policy,
    }


# ════════════════════════════════════════════════════════════════════════════
# OUTCOME EVALUATOR API
# ════════════════════════════════════════════════════════════════════════════

def find_unevaluated(
    horizon: str,
    now_unix: int,
    *,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Return shadow signals whose `horizon` outcome is unevaluated AND whose
    horizon_close_ts has already passed (so a real close price exists).

    Only `should_trade == true` records are returned — non-actionable
    decisions are not part of forward-test PnL.
    """
    flag_path = f"outcomes.{horizon}.evaluated"
    ts_path = f"outcomes.{horizon}.horizon_close_ts"
    q = {
        flag_path: False,
        ts_path: {"$ne": None, "$lte": int(now_unix)},
        "decision.should_trade": True,
        "entry_price": {"$ne": None},
    }
    cur = _get_collection().find(q).limit(int(limit))
    return list(cur)


def update_outcome(
    decision_id: str,
    horizon: str,
    *,
    exit_price: Optional[float],
    pnl_pct: Optional[float],
) -> bool:
    """Mark a horizon as evaluated. Returns True if a doc was updated."""
    if not decision_id:
        return False
    set_doc = {
        f"outcomes.{horizon}.evaluated": True,
        f"outcomes.{horizon}.exit_price": float(exit_price) if exit_price is not None else None,
        f"outcomes.{horizon}.pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
        f"outcomes.{horizon}.evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    res = _get_collection().update_one({"decision_id": decision_id}, {"$set": set_doc})
    return res.modified_count > 0


# ════════════════════════════════════════════════════════════════════════════
# PERFORMANCE AGGREGATOR
# ════════════════════════════════════════════════════════════════════════════

def aggregate_performance(
    *,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    policy: Optional[str] = None,
    regime: Optional[str] = None,           # alias for score_regime (back-compat)
    score_regime: Optional[str] = None,
    market_regime: Optional[str] = None,    # P0: filter by market regime label
    horizons: Optional[List[str]] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Live-shadow performance aggregator.

    Returns one bucket per horizon:
      {
        "h1": {
            "n": int,                # evaluated trades
            "win_rate": float,       # in [0,1]
            "avg_pnl": float,        # arithmetic mean of pnl_pct
            "expectancy": float,     # same as avg_pnl, named for clarity
            "profit_factor": float,  # sum_wins / |sum_losses|, inf if no losses
            "max_drawdown": float,   # of cumulative pnl path
            "sharpe_like": float,    # mean / std (no annualisation, raw)
            "best": float,
            "worst": float,
        },
        ...
      }

    NOTE: Sharpe-like is intentionally NOT annualised — annualisation requires
    a clean trade-cadence assumption that we DO NOT have yet at this scale.
    Reporting raw mean/std keeps the signal honest.
    """
    horizons = horizons or DEFAULT_HORIZONS
    coll = _get_collection()

    base_match: Dict[str, Any] = {"decision.should_trade": True}
    if symbol:
        base_match["symbol"] = symbol.upper()
    if timeframe:
        base_match["timeframe"] = timeframe.upper()
    if policy:
        base_match["policy"] = policy
    # `regime` is the legacy name for score_regime — accept either, prefer
    # the explicit one when both are passed.
    sr = score_regime or regime
    if sr:
        base_match["regime"] = sr
    if market_regime:
        base_match["market_regime_label"] = market_regime
    if source:
        base_match["source"] = source

    out: Dict[str, Any] = {}
    for h in horizons:
        flag_path = f"outcomes.{h}.evaluated"
        pnl_path = f"outcomes.{h}.pnl_pct"
        match = dict(base_match)
        match[flag_path] = True
        match[pnl_path] = {"$ne": None}

        pnls: List[float] = []
        for r in coll.find(match, {pnl_path: 1, "_id": 0}):
            v = (r.get("outcomes") or {}).get(h, {}).get("pnl_pct")
            if v is not None:
                try:
                    pnls.append(float(v))
                except (TypeError, ValueError):
                    pass

        out[h] = _summarise_pnls(pnls)
    return out


def _summarise_pnls(pnls: List[float]) -> Dict[str, Any]:
    n = len(pnls)
    if n == 0:
        return {
            "n": 0,
            "win_rate": None,
            "avg_pnl": None,
            "expectancy": None,
            "profit_factor": None,
            "max_drawdown": None,
            "sharpe_like": None,
            "best": None,
            "worst": None,
        }
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    sum_wins = sum(wins)
    sum_losses = sum(losses)  # negative
    avg = sum(pnls) / n
    # std (population)
    var = sum((p - avg) ** 2 for p in pnls) / n
    std = var ** 0.5
    sharpe_like = (avg / std) if std > 0 else None
    pf: Optional[float]
    if losses:
        denom = abs(sum_losses)
        pf = (sum_wins / denom) if denom > 0 else None
    else:
        # No losses: profit_factor is undefined (∞). Return None for JSON safety;
        # callers should treat "all wins, no losses" via the win_rate field.
        pf = None

    # max drawdown of cumulative pnl path (in pnl-points, not %).
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    return {
        "n": n,
        "win_rate": round(len(wins) / n, 4),
        "avg_pnl": round(avg, 6),
        "expectancy": round(avg, 6),
        "profit_factor": (round(pf, 4) if pf is not None else None),
        "max_drawdown": round(max_dd, 6),
        "sharpe_like": (round(sharpe_like, 4) if sharpe_like is not None else None),
        "best": round(max(pnls), 6),
        "worst": round(min(pnls), 6),
    }
