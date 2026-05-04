"""
Phase C.3.1 — Automatic Regime Accuracy Matrix
==============================================

READ-ONLY analysis service. Computes v1 x v2 x outcome matrix from
`shadow_trades` and persists a structured metric document into
`regime_model_metrics`. Per-lane (phase_c + discovery).

Contract:
  * Input : shadow_trades with horizons.resolved==True
  * v1    : features.regime (what the router actually used at entry)
  * v2    : regime_debug.v2 (Phase C.2 shadow detector output)
  * outcome: sign of first resolved horizon.pnl
  * Output: ONE dict per lane, also inserted into regime_model_metrics

Policy (hard):
  * Never touches market_regime, routers, generators, thresholds.
  * Never alters shadow_trades.
  * Skips legacy trades that have no regime_debug (v2) — they are counted
    separately as `n_without_v2`, not mixed into ratios.

Lane mapping (experiment_id -> lane):
    phase_c_real_regime_run  -> phase_c
    discovery_matrix_live    -> discovery
"""
from __future__ import annotations

import os
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient
from pymongo.database import Database

logger = logging.getLogger("regime_accuracy_service")

# ---------------------------------------------------------------------------
#  Lane registry
# ---------------------------------------------------------------------------
LANE_EXPERIMENT_MAP: Dict[str, List[str]] = {
    "phase_c":   ["phase_c_real_regime_run"],
    "discovery": ["discovery_matrix_live"],
}


def _outcome(pnl: Optional[float]) -> str:
    if pnl is None:
        return "unresolved"
    if pnl > 0:
        return "win"
    if pnl < 0:
        return "loss"
    return "flat"


def _side_bucket(side: Optional[str]) -> str:
    s = (side or "").upper()
    if s in ("SELL", "SHORT"):
        return "SHORT"
    if s in ("BUY", "LONG"):
        return "LONG"
    return "OTHER"


def _first_resolved_pnl(trade: Dict[str, Any]) -> Optional[float]:
    for h in (trade.get("horizons") or []):
        if h.get("resolved"):
            return h.get("pnl")
    return None


def _v1_from_trade(trade: Dict[str, Any]) -> str:
    features = trade.get("features") or {}
    return (features.get("regime") or "UNKNOWN").upper()


def _v2_from_trade(trade: Dict[str, Any]) -> Optional[str]:
    rdbg = trade.get("regime_debug")
    if not isinstance(rdbg, dict):
        return None
    v2 = rdbg.get("v2")
    if v2 is None:
        return None
    return str(v2).upper()


# ---------------------------------------------------------------------------
#  Core matrix build for a single lane
# ---------------------------------------------------------------------------
def build_matrix_for_lane(db: Database, lane: str) -> Dict[str, Any]:
    experiments = LANE_EXPERIMENT_MAP.get(lane, [])
    if not experiments:
        return {
            "lane": lane,
            "n_resolved": 0,
            "error": "unknown_lane",
        }

    cursor = db.shadow_trades.find({
        "experiment_id": {"$in": experiments},
        "horizons.resolved": True,
    })

    # aggregation containers
    short_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    long_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    short_pnl_sum: Dict[Tuple[str, str], float] = defaultdict(float)
    short_pnl_n:   Dict[Tuple[str, str], int] = defaultdict(int)
    long_pnl_sum:  Dict[Tuple[str, str], float] = defaultdict(float)
    long_pnl_n:    Dict[Tuple[str, str], int] = defaultdict(int)

    total = 0
    n_without_v2 = 0

    # raw side summaries
    short_win = short_loss = short_flat = 0
    long_win = long_loss = long_flat = 0
    short_pnl_total = 0.0
    long_pnl_total = 0.0

    # disagreement trackers (only rows with v2 present)
    disagree_total = 0
    disagree_on_win = 0
    disagree_on_loss = 0
    rows_with_v2 = 0

    # primary edge questions
    short_loss_v1_down_v2_not_down = 0     # the classic "v2 explains SHORT losses"
    short_win_v1_down_v2_down = 0          # SHORT win where v2 confirms downtrend
    long_win_v1_up_v2_up = 0               # LONG win both up

    for t in cursor:
        side = _side_bucket(t.get("side"))
        if side == "OTHER":
            continue
        pnl = _first_resolved_pnl(t)
        outcome = _outcome(pnl)
        if outcome == "unresolved":
            continue

        v1 = _v1_from_trade(t)
        v2 = _v2_from_trade(t)

        total += 1

        if v2 is None:
            n_without_v2 += 1
            # still count in per-side totals (for raw WR reporting)
            if side == "SHORT":
                short_win  += outcome == "win"
                short_loss += outcome == "loss"
                short_flat += outcome == "flat"
                short_pnl_total += (pnl or 0.0)
            else:
                long_win  += outcome == "win"
                long_loss += outcome == "loss"
                long_flat += outcome == "flat"
                long_pnl_total += (pnl or 0.0)
            continue

        rows_with_v2 += 1
        key_c = (v1, v2, outcome)
        key_m = (v1, v2)

        if side == "SHORT":
            short_counts[key_c] += 1
            short_pnl_sum[key_m] += (pnl or 0.0)
            short_pnl_n[key_m]   += 1
            short_win  += outcome == "win"
            short_loss += outcome == "loss"
            short_flat += outcome == "flat"
            short_pnl_total += (pnl or 0.0)
            if v1 == "DOWNTREND" and v2 != "DOWNTREND" and outcome == "loss":
                short_loss_v1_down_v2_not_down += 1
            if v1 == "DOWNTREND" and v2 == "DOWNTREND" and outcome == "win":
                short_win_v1_down_v2_down += 1
        else:  # LONG
            long_counts[key_c] += 1
            long_pnl_sum[key_m] += (pnl or 0.0)
            long_pnl_n[key_m]   += 1
            long_win  += outcome == "win"
            long_loss += outcome == "loss"
            long_flat += outcome == "flat"
            long_pnl_total += (pnl or 0.0)
            if v1 == "UPTREND" and v2 == "UPTREND" and outcome == "win":
                long_win_v1_up_v2_up += 1

        if v1 != v2:
            disagree_total += 1
            if outcome == "win":
                disagree_on_win += 1
            elif outcome == "loss":
                disagree_on_loss += 1

    # ------- ratios / wr --------------------------------------------------
    def _wr(w: int, n: int) -> Optional[float]:
        return round(w / n, 4) if n > 0 else None

    def _avg(s: float, n: int) -> Optional[float]:
        return round(s / n, 6) if n > 0 else None

    short_resolved = short_win + short_loss + short_flat
    long_resolved  = long_win + long_loss + long_flat

    short_wr = _wr(short_win, short_resolved)
    long_wr  = _wr(long_win,  long_resolved)

    # key percentages (use only trades with v2 for these)
    pct_short_loss_v1_down_v2_not_down = (
        round(short_loss_v1_down_v2_not_down / short_loss, 4)
        if short_loss > 0 else None
    )
    pct_long_win_v1_up_v2_up = (
        round(long_win_v1_up_v2_up / long_win, 4)
        if long_win > 0 else None
    )
    disagreement_rate = (
        round(disagree_total / rows_with_v2, 4) if rows_with_v2 > 0 else None
    )
    disagreement_on_losers = (
        round(disagree_on_loss / max(1, short_loss + long_loss), 4)
        if rows_with_v2 > 0 else None
    )
    disagreement_on_winners = (
        round(disagree_on_win / max(1, short_win + long_win), 4)
        if rows_with_v2 > 0 else None
    )

    # ------- flat matrix for persistence ----------------------------------
    def _flat(counts: Dict[Tuple[str, str, str], int],
              pnl_s: Dict[Tuple[str, str], float],
              pnl_n: Dict[Tuple[str, str], int]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        pairs = set((k[0], k[1]) for k in counts.keys())
        for pair in pairs:
            v1, v2 = pair
            w = counts.get((v1, v2, "win"), 0)
            l = counts.get((v1, v2, "loss"), 0)
            f = counts.get((v1, v2, "flat"), 0)
            n = w + l + f
            key = f"v1_{v1}__v2_{v2}"
            out[key] = {
                "count": n,
                "wins":  w,
                "losses": l,
                "flats": f,
                "avg_pnl": _avg(pnl_s.get(pair, 0.0), pnl_n.get(pair, 0)),
                "wr": _wr(w, n),
            }
        return out

    doc: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc),
        "lane": lane,
        "experiments": experiments,
        "n_resolved": total,
        "n_with_v2": rows_with_v2,
        "n_without_v2": n_without_v2,
        "short": {
            "resolved": short_resolved,
            "wins": short_win,
            "losses": short_loss,
            "flats": short_flat,
            "wr": short_wr,
            "avg_pnl": _avg(short_pnl_total, short_resolved),
            # v1 x v2 x outcome summaries (only v2-covered rows)
            "loss_when_v1_down_v2_not_down_pct": pct_short_loss_v1_down_v2_not_down,
            "loss_when_v1_down_v2_not_down_n": short_loss_v1_down_v2_not_down,
            "win_when_v1_down_v2_down_n": short_win_v1_down_v2_down,
        },
        "long": {
            "resolved": long_resolved,
            "wins": long_win,
            "losses": long_loss,
            "flats": long_flat,
            "wr": long_wr,
            "avg_pnl": _avg(long_pnl_total, long_resolved),
            "win_when_v1_up_v2_up_pct": pct_long_win_v1_up_v2_up,
            "win_when_v1_up_v2_up_n": long_win_v1_up_v2_up,
        },
        "cross": {
            "disagreement_rate": disagreement_rate,
            "disagreement_on_winners": disagreement_on_winners,
            "disagreement_on_losers": disagreement_on_losers,
        },
        "matrix_short": _flat(short_counts, short_pnl_sum, short_pnl_n),
        "matrix_long":  _flat(long_counts,  long_pnl_sum,  long_pnl_n),
        "version": 1,
    }
    return doc


def run(db: Optional[Database] = None, persist: bool = True) -> Dict[str, Any]:
    """Compute matrix for every known lane, optionally write to Mongo.

    Returns: {"lanes": {lane: doc, ...}, "persisted": bool}
    """
    owns_client = False
    client: Optional[MongoClient] = None
    if db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("PHASE_B1_DB", "trading_os")
        client = MongoClient(mongo_url)
        db = client[db_name]
        owns_client = True

    try:
        out: Dict[str, Any] = {"lanes": {}, "persisted": False}
        for lane in LANE_EXPERIMENT_MAP.keys():
            doc = build_matrix_for_lane(db, lane)
            if persist:
                try:
                    db.regime_model_metrics.insert_one(dict(doc))
                    out["persisted"] = True
                except Exception as e:
                    logger.exception("regime_model_metrics insert failed for lane=%s: %s", lane, e)
            # pop Mongo-only _id if any
            doc.pop("_id", None)
            out["lanes"][lane] = doc
        return out
    finally:
        if owns_client and client is not None:
            client.close()


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, default=str, indent=2))
