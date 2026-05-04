"""
Phase C.3c — Post-Guard Validation Report
=========================================

READ-ONLY analysis. Generates the 4-block post-guard report on demand.

Does NOT touch detectors, generators, routers, validators, thresholds.

Blocks:
  A. phase_c post-guard:    per-strategy create/resolved/WR/avg_pnl,
                             guard_skip_count, top skipped symbols/tfs,
                             total system pnl post-guard.
  B. discovery post-guard:  same, marked exploratory_only.
  C. Guard Impact Delta:    pre-guard vs post-guard WR/avg_pnl for
                             SHORT/LONG, trade count delta, skip rate,
                             system pnl before/after.
  D. Regime Evidence:       latest accuracy key numbers + decision +
                             state for both lanes.

Verdict (machine):
  PASS    — SHORT edge improves AND LONG flow is preserved AND system pnl
            improves OR at least stops degrading (post-guard avg_pnl
            >= pre-guard avg_pnl for SHORT, and LONG avg_pnl not worse
            by more than 20% relative).
  NEUTRAL — guard barely fires (skip_count low, SHORT post count low).
  FAIL    — guard fires a lot BUT SHORT still broken OR LONG degrades
            OR total pnl gets worse.

Caveats:
  * If post-guard resolved trades are insufficient (<5 per lane), the
    verdict is `INSUFFICIENT_POST_GUARD_DATA` regardless of other checks.
"""
from __future__ import annotations

import os
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, DESCENDING
from pymongo.database import Database

from .regime_accuracy_service import LANE_EXPERIMENT_MAP

logger = logging.getLogger("regime_post_guard_report")

MIN_POST_GUARD_RESOLVED_FOR_VERDICT = 5
MIN_POST_GUARD_SHORT_FOR_PASS = 3      # architect rule: PASS impossible without SHORT activity
SHORT_EDGE_MIN_IMPROVEMENT = 0.0       # post >= pre (any non-negative delta is good)
LONG_REGRESSION_TOLERANCE = 0.20       # post avg must not drop >20% relative to pre


def _guard_flag(db: Database) -> Dict[str, Any]:
    doc = db.regime_controls.find_one({"control": "short_v2_guard_enabled"})
    if doc is None:
        return {"enabled": False, "updated_at": None, "reason": None}
    return {
        "enabled": bool(doc.get("enabled", False)),
        "updated_at": doc.get("updated_at"),
        "reason": doc.get("updated_reason"),
    }


def _first_resolved_pnl(trade: Dict[str, Any]) -> Optional[float]:
    for h in (trade.get("horizons") or []):
        if h.get("resolved"):
            return h.get("pnl")
    return None


def _side_bucket(side: Optional[str]) -> str:
    s = (side or "").upper()
    if s in ("SELL", "SHORT"):
        return "SHORT"
    if s in ("BUY", "LONG"):
        return "LONG"
    return "OTHER"


def _aggregate_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute per-strategy and per-side stats over a list of trades."""
    by_strategy: Dict[str, Dict[str, Any]] = {}
    by_side: Dict[str, Dict[str, Any]] = {"SHORT": _empty_stat(), "LONG": _empty_stat()}
    total_pnl = 0.0
    total_resolved = 0
    total_created = len(trades)

    for t in trades:
        feat = t.get("features") or {}
        strat = (feat.get("strategy") or "UNKNOWN").upper()
        side = _side_bucket(t.get("side"))
        pnl = _first_resolved_pnl(t)

        s_entry = by_strategy.setdefault(strat, _empty_stat())
        s_entry["created"] += 1
        if side in by_side:
            by_side[side]["created"] += 1

        if pnl is None:
            continue  # unresolved

        s_entry["resolved"] += 1
        s_entry["pnl_sum"] += pnl
        total_pnl += pnl
        total_resolved += 1
        if pnl > 0:
            s_entry["wins"] += 1
        elif pnl < 0:
            s_entry["losses"] += 1
        else:
            s_entry["flats"] += 1

        if side in by_side:
            b = by_side[side]
            b["resolved"] += 1
            b["pnl_sum"] += pnl
            if pnl > 0:
                b["wins"] += 1
            elif pnl < 0:
                b["losses"] += 1
            else:
                b["flats"] += 1

    # finalize
    for d in list(by_strategy.values()) + list(by_side.values()):
        _finalize_stat(d)

    return {
        "total_created": total_created,
        "total_resolved": total_resolved,
        "total_pnl_sum": round(total_pnl, 6),
        "avg_pnl_per_resolved": round(total_pnl / total_resolved, 6) if total_resolved else None,
        "by_strategy": by_strategy,
        "by_side": by_side,
    }


def _empty_stat() -> Dict[str, Any]:
    return {"created": 0, "resolved": 0, "wins": 0, "losses": 0, "flats": 0, "pnl_sum": 0.0}


def _finalize_stat(d: Dict[str, Any]) -> None:
    n = d.get("resolved", 0)
    d["wr"] = round(d["wins"] / n, 4) if n > 0 else None
    d["avg_pnl"] = round(d["pnl_sum"] / n, 6) if n > 0 else None


def _lane_block(db: Database, lane: str, since: Optional[datetime]) -> Dict[str, Any]:
    experiments = LANE_EXPERIMENT_MAP.get(lane, [])

    # pre-guard: trades created BEFORE `since`
    pre_q = {"experiment_id": {"$in": experiments}}
    if since is not None:
        pre_q["created_at"] = {"$lt": since}
    pre_trades = list(db.shadow_trades.find(pre_q))

    # post-guard: trades created AT/AFTER `since`
    if since is None:
        post_trades: List[Dict[str, Any]] = []
    else:
        post_trades = list(db.shadow_trades.find({
            "experiment_id": {"$in": experiments},
            "created_at": {"$gte": since},
        }))

    pre_agg = _aggregate_trades(pre_trades)
    post_agg = _aggregate_trades(post_trades)

    # guard_skip_count for this lane
    guard_skip_q: Dict[str, Any] = {"lane": lane}
    if since is not None:
        guard_skip_q["created_at"] = {"$gte": since}
    skip_count = db.regime_guard_events.count_documents(guard_skip_q)

    # top skipped symbols/timeframes
    skips = list(db.regime_guard_events.find(guard_skip_q))
    sym_counter = Counter((e.get("symbol") or "UNKNOWN") for e in skips)
    tf_counter = Counter((e.get("timeframe") or "UNKNOWN") for e in skips)
    pair_counter = Counter(
        (f"{e.get('symbol','UNKNOWN')}@{e.get('timeframe','UNKNOWN')}") for e in skips
    )

    # --- guard_metrics: architect rule ---
    # skip_rate = skipped / (skipped + executed_SHORT_created_post_guard)
    # Interprets how hard the guard is filtering. NOT about wins/losses,
    # purely about throughput.
    #   <30%  : normal filter
    #   30-70%: strong filter — watch
    #   >70%  : capacity collapse — guard kills the flow
    executed_short_post = int(
        (post_agg.get("by_side") or {}).get("SHORT", {}).get("created", 0) or 0
    )
    denom = skip_count + executed_short_post
    skip_rate = round(skip_count / denom, 4) if denom > 0 else None
    if skip_rate is None:
        skip_rate_level = "no_short_activity"
    elif skip_rate < 0.30:
        skip_rate_level = "normal"
    elif skip_rate <= 0.70:
        skip_rate_level = "strong_filter"
    else:
        skip_rate_level = "capacity_collapse"

    guard_metrics = {
        "skip_count": skip_count,
        "executed_short": executed_short_post,
        "skip_rate": skip_rate,
        "skip_rate_level": skip_rate_level,
    }

    return {
        "lane": lane,
        "experiments": experiments,
        "since": since,
        "pre_guard": pre_agg,
        "post_guard": post_agg,
        "guard_skip_count": skip_count,
        "guard_metrics": guard_metrics,
        "top_skipped_symbols": sym_counter.most_common(10),
        "top_skipped_timeframes": tf_counter.most_common(10),
        "top_skipped_pairs": pair_counter.most_common(10),
    }


def _delta_block(lane_blocks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Compute pre/post delta aggregated across lanes (and per-lane)."""
    out: Dict[str, Any] = {"per_lane": {}, "combined": {}}

    combined_pre = {"SHORT": _empty_stat(), "LONG": _empty_stat()}
    combined_post = {"SHORT": _empty_stat(), "LONG": _empty_stat()}
    combined_pre_total_pnl = 0.0
    combined_pre_total_n = 0
    combined_post_total_pnl = 0.0
    combined_post_total_n = 0
    combined_pre_created = 0
    combined_post_created = 0
    combined_skip = 0

    for lane, blk in lane_blocks.items():
        pre = blk["pre_guard"]
        post = blk["post_guard"]
        per_lane_delta = {}
        for side in ("SHORT", "LONG"):
            p = pre["by_side"].get(side) or _empty_stat()
            q = post["by_side"].get(side) or _empty_stat()
            per_lane_delta[side] = {
                "pre_wr": p.get("wr"),
                "post_wr": q.get("wr"),
                "pre_avg_pnl": p.get("avg_pnl"),
                "post_avg_pnl": q.get("avg_pnl"),
                "pre_resolved": p.get("resolved"),
                "post_resolved": q.get("resolved"),
                "delta_avg_pnl": (
                    round((q.get("avg_pnl") or 0.0) - (p.get("avg_pnl") or 0.0), 6)
                    if p.get("avg_pnl") is not None and q.get("avg_pnl") is not None
                    else None
                ),
            }
            # combined
            for k in ("created", "resolved", "wins", "losses", "flats"):
                combined_pre[side][k] += p.get(k, 0) or 0
                combined_post[side][k] += q.get(k, 0) or 0
            combined_pre[side]["pnl_sum"] += p.get("pnl_sum", 0.0) or 0.0
            combined_post[side]["pnl_sum"] += q.get("pnl_sum", 0.0) or 0.0

        per_lane_delta["system"] = {
            "pre_total_created": pre.get("total_created"),
            "post_total_created": post.get("total_created"),
            "pre_total_resolved": pre.get("total_resolved"),
            "post_total_resolved": post.get("total_resolved"),
            "pre_total_pnl_sum": pre.get("total_pnl_sum"),
            "post_total_pnl_sum": post.get("total_pnl_sum"),
            "pre_avg_pnl": pre.get("avg_pnl_per_resolved"),
            "post_avg_pnl": post.get("avg_pnl_per_resolved"),
            "guard_skip_count": blk.get("guard_skip_count", 0),
            "skip_rate": (
                round(blk["guard_skip_count"] / (blk["guard_skip_count"] + post.get("total_created", 0)), 4)
                if (blk["guard_skip_count"] + post.get("total_created", 0)) > 0 else None
            ),
        }
        out["per_lane"][lane] = per_lane_delta

        # combined running totals
        combined_pre_total_pnl += pre.get("total_pnl_sum") or 0.0
        combined_pre_total_n += pre.get("total_resolved") or 0
        combined_post_total_pnl += post.get("total_pnl_sum") or 0.0
        combined_post_total_n += post.get("total_resolved") or 0
        combined_pre_created += pre.get("total_created") or 0
        combined_post_created += post.get("total_created") or 0
        combined_skip += blk.get("guard_skip_count", 0) or 0

    # finalize combined by_side
    for d in list(combined_pre.values()) + list(combined_post.values()):
        _finalize_stat(d)

    out["combined"] = {
        "pre_by_side": combined_pre,
        "post_by_side": combined_post,
        "pre_total_pnl_sum": round(combined_pre_total_pnl, 6),
        "post_total_pnl_sum": round(combined_post_total_pnl, 6),
        "pre_total_resolved": combined_pre_total_n,
        "post_total_resolved": combined_post_total_n,
        "pre_total_created": combined_pre_created,
        "post_total_created": combined_post_created,
        "guard_skip_count_total": combined_skip,
    }

    # --- combined guard_metrics (architect rule) ---
    executed_short_combined = int(combined_post["SHORT"].get("created", 0) or 0)
    denom = combined_skip + executed_short_combined
    skip_rate = round(combined_skip / denom, 4) if denom > 0 else None
    if skip_rate is None:
        level = "no_short_activity"
    elif skip_rate < 0.30:
        level = "normal"
    elif skip_rate <= 0.70:
        level = "strong_filter"
    else:
        level = "capacity_collapse"
    out["combined"]["guard_metrics"] = {
        "skip_count": combined_skip,
        "executed_short": executed_short_combined,
        "skip_rate": skip_rate,
        "skip_rate_level": level,
    }
    return out


def _evidence_block(db: Database) -> Dict[str, Any]:
    out: Dict[str, Any] = {"lanes": {}}
    for lane in ("phase_c", "discovery"):
        metric = db.regime_model_metrics.find_one({"lane": lane}, sort=[("generated_at", DESCENDING)])
        decision = db.regime_decisions.find_one({"lane": lane}, sort=[("generated_at", DESCENDING)])
        state = db.research_states.find_one({"lane": lane}, sort=[("generated_at", DESCENDING)])
        row: Dict[str, Any] = {
            "n_with_v2": (metric or {}).get("n_with_v2"),
            "n_resolved": (metric or {}).get("n_resolved"),
            "disagreement_rate": ((metric or {}).get("cross") or {}).get("disagreement_rate"),
            "loss_when_v1_down_v2_not_down_pct":
                ((metric or {}).get("short") or {}).get("loss_when_v1_down_v2_not_down_pct"),
            "loss_when_v1_down_v2_not_down_n":
                ((metric or {}).get("short") or {}).get("loss_when_v1_down_v2_not_down_n"),
            "short_wr": ((metric or {}).get("short") or {}).get("wr"),
            "long_wr": ((metric or {}).get("long") or {}).get("wr"),
            "verdict": (decision or {}).get("verdict"),
            "verdict_confidence": (decision or {}).get("confidence"),
            "state": (state or {}).get("state"),
            "state_reason": (state or {}).get("reason"),
        }
        out["lanes"][lane] = row
    return out


def _compute_verdict(delta: Dict[str, Any]) -> Dict[str, Any]:
    """Compute PASS/NEUTRAL/FAIL based on combined post-guard evidence."""
    combined = delta["combined"]
    post_n = combined["post_total_resolved"]

    if post_n < MIN_POST_GUARD_RESOLVED_FOR_VERDICT:
        return {
            "verdict": "INSUFFICIENT_POST_GUARD_DATA",
            "reason": (
                f"need >={MIN_POST_GUARD_RESOLVED_FOR_VERDICT} post-guard resolved "
                f"trades, have {post_n}"
            ),
            "post_total_resolved": post_n,
            "short_post_resolved": int(combined["post_by_side"]["SHORT"].get("resolved", 0) or 0),
            "min_short_post_for_pass": MIN_POST_GUARD_SHORT_FOR_PASS,
            "guard_metrics": combined.get("guard_metrics"),
            "short_delta_avg_pnl": None,
            "long_delta_avg_pnl": None,
            "short_pre_wr": combined["pre_by_side"]["SHORT"].get("wr"),
            "short_post_wr": combined["post_by_side"]["SHORT"].get("wr"),
            "long_pre_wr": combined["pre_by_side"]["LONG"].get("wr"),
            "long_post_wr": combined["post_by_side"]["LONG"].get("wr"),
            "guard_skip_count": combined["guard_skip_count_total"],
        }

    short_pre = combined["pre_by_side"]["SHORT"]
    short_post = combined["post_by_side"]["SHORT"]
    long_pre = combined["pre_by_side"]["LONG"]
    long_post = combined["post_by_side"]["LONG"]

    short_delta = (
        (short_post["avg_pnl"] or 0.0) - (short_pre["avg_pnl"] or 0.0)
        if short_pre["avg_pnl"] is not None and short_post["avg_pnl"] is not None else None
    )
    long_delta = (
        (long_post["avg_pnl"] or 0.0) - (long_pre["avg_pnl"] or 0.0)
        if long_pre["avg_pnl"] is not None and long_post["avg_pnl"] is not None else None
    )

    skip_count = combined["guard_skip_count_total"]
    short_post_n = int(short_post.get("resolved", 0) or 0)

    # low-activity branch: guard barely fired AND very few post-guard shorts
    if skip_count <= 2 and short_post_n < 3:
        verdict = "NEUTRAL"
        reason = (
            f"guard barely fires (skip_count={skip_count}, "
            f"post-guard SHORT resolved={short_post_n}). "
            "v2 disagreement operationally low in current market."
        )
    else:
        # --- ARCHITECT RULE: MIN_ACTIVITY_CONSTRAINT ---
        # PASS is impossible without enough post-guard SHORT resolved trades.
        # This prevents a false PASS where guard kills all SHORTs and SHORT
        # stats trivially "improve" because there is nothing to measure.
        if short_post_n < MIN_POST_GUARD_SHORT_FOR_PASS:
            verdict = "NEUTRAL"
            reason = (
                f"post-guard SHORT resolved={short_post_n} < "
                f"{MIN_POST_GUARD_SHORT_FOR_PASS}; PASS impossible without "
                "measurable SHORT activity (guard may have blocked all SHORTs, "
                "which is not proof the edge improves — only that signals were "
                "filtered). skip_count={sk}".format(sk=skip_count)
            )
        else:
            # check SHORT edge: must not get worse
            short_ok = short_delta is None or short_delta >= SHORT_EDGE_MIN_IMPROVEMENT

            # check LONG didn't regress beyond tolerance
            long_ok = True
            if long_pre["avg_pnl"] is not None and long_post["avg_pnl"] is not None:
                if long_pre["avg_pnl"] > 0:
                    long_ok = long_post["avg_pnl"] >= long_pre["avg_pnl"] * (1 - LONG_REGRESSION_TOLERANCE)
                else:
                    long_ok = long_post["avg_pnl"] >= long_pre["avg_pnl"]

            total_pnl_change = combined["post_total_pnl_sum"] / max(1, post_n) - \
                               (combined["pre_total_pnl_sum"] / max(1, combined["pre_total_resolved"]))

            if short_ok and long_ok and total_pnl_change >= 0:
                # --- architect rule: capacity_collapse blocks PASS ---
                guard_metrics = combined.get("guard_metrics") or {}
                skip_rate_level = guard_metrics.get("skip_rate_level")
                skip_rate = guard_metrics.get("skip_rate")
                if skip_rate_level == "capacity_collapse":
                    verdict = "FAIL"
                    reason = (
                        "capacity collapse: skip_rate=%.2f (>70%%) — guard kills "
                        "the SHORT flow. Not an edge improvement, just a filter."
                        % (skip_rate if skip_rate is not None else 0.0)
                    )
                else:
                    verdict = "PASS"
                    reason = (
                        "SHORT post-guard activity=%d (>= %d); SHORT avg_pnl non-negative delta; "
                        "LONG preserved within ±%.0f%%; system pnl non-negative delta; "
                        "guard skip_rate=%s (%s)."
                        % (
                            short_post_n, MIN_POST_GUARD_SHORT_FOR_PASS,
                            LONG_REGRESSION_TOLERANCE * 100,
                            ("%.2f" % skip_rate) if skip_rate is not None else "n/a",
                            skip_rate_level or "unknown",
                        )
                    )
            else:
                verdict = "FAIL"
                reason = (
                    f"short_post_n={short_post_n} short_ok={short_ok} long_ok={long_ok} "
                    f"system_pnl_delta={round(total_pnl_change, 6)}"
                )

    return {
        "verdict": verdict,
        "reason": reason,
        "post_total_resolved": post_n,
        "short_post_resolved": short_post_n,
        "min_short_post_for_pass": MIN_POST_GUARD_SHORT_FOR_PASS,
        "guard_metrics": combined.get("guard_metrics"),
        "short_pre_wr": short_pre.get("wr"),
        "short_post_wr": short_post.get("wr"),
        "short_pre_avg_pnl": short_pre.get("avg_pnl"),
        "short_post_avg_pnl": short_post.get("avg_pnl"),
        "short_delta_avg_pnl": short_delta,
        "long_pre_wr": long_pre.get("wr"),
        "long_post_wr": long_post.get("wr"),
        "long_pre_avg_pnl": long_pre.get("avg_pnl"),
        "long_post_avg_pnl": long_post.get("avg_pnl"),
        "long_delta_avg_pnl": long_delta,
        "guard_skip_count": skip_count,
    }


def generate(db: Optional[Database] = None) -> Dict[str, Any]:
    owns_client = False
    client: Optional[MongoClient] = None
    if db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("PHASE_B1_DB", "trading_os")
        client = MongoClient(mongo_url)
        db = client[db_name]
        owns_client = True

    try:
        guard = _guard_flag(db)
        since = guard.get("updated_at") if guard.get("enabled") else None
        # Mongo BSON datetimes are naive UTC — make timezone-aware so we can
        # subtract from `now` (which is tz-aware). This does not change the
        # value, just the tzinfo tag.
        if since is not None and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        lane_blocks: Dict[str, Dict[str, Any]] = {}
        for lane in ("phase_c", "discovery"):
            lane_blocks[lane] = _lane_block(db, lane, since)

        delta = _delta_block(lane_blocks)
        evidence = _evidence_block(db)
        verdict = _compute_verdict(delta)

        hours_since_guard = (
            (now - since).total_seconds() / 3600.0 if since is not None else None
        )

        return {
            "generated_at": now,
            "guard": {
                "enabled": guard["enabled"],
                "updated_at": guard.get("updated_at"),
                "reason": guard.get("reason"),
                "hours_since_enabled": round(hours_since_guard, 2) if hours_since_guard is not None else None,
            },
            "A_phase_c": lane_blocks.get("phase_c"),
            "B_discovery": {**(lane_blocks.get("discovery") or {}), "exploratory_only": True},
            "C_delta": delta,
            "D_regime_evidence": evidence,
            "verdict": verdict,
            "version": 1,
        }
    finally:
        if owns_client and client is not None:
            client.close()


if __name__ == "__main__":
    import json
    print(json.dumps(generate(), default=str, indent=2))
