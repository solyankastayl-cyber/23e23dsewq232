"""
Phase C.3.5 — Regime Alerts
===========================

Automatic anomaly detection on the latest `regime_model_metrics` per lane.
Emits alert documents into the `regime_alerts` collection.

Alert catalogue:
  * SHORT_EDGE_COLLAPSE     — SHORT WR broken or avg pnl strongly negative
  * REGIME_DISAGREEMENT_HIGH — v1 vs v2 disagree on >30% of rows
  * V2_EXPLAINS_LOSSES      — >60% of SHORT losses sit in v1=DOWN/v2!=DOWN
  * LONG_EMERGENCE          — LONG side starting to show a real edge

Policy:
  * Idempotent per (lane, alert_type) within a tolerance window:
    - If the latest alert of the same (lane, type) is still valid for the
      same metrics snapshot, we don't duplicate — we update `last_seen_at`.
  * Never blocks, never raises.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, DESCENDING
from pymongo.database import Database

logger = logging.getLogger("regime_alerts")

# ---- thresholds ----
SHORT_EDGE_MIN_N = 8
SHORT_EDGE_WR_MAX = 0.05       # <=5% WR is collapse
SHORT_EDGE_AVG_PNL_MAX = -0.015  # avg pnl <= -1.5%
DISAGREEMENT_HIGH = 0.30
V2_EXPLAINS_THRESHOLD = 0.60
LONG_EDGE_MIN_N = 5
LONG_EDGE_WR_MIN = 0.60
LONG_EDGE_AVG_PNL_MIN = 0.0


def _latest_metric(db: Database, lane: str) -> Optional[Dict[str, Any]]:
    return db.regime_model_metrics.find_one(
        {"lane": lane},
        sort=[("generated_at", DESCENDING)],
    )


def _emit(db: Database, lane: str, alert_type: str, severity: str,
          message: str, evidence: Dict[str, Any], metric_generated_at: Any) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    # dedup — if latest alert for (lane, type) references the same metric snapshot,
    # just bump last_seen_at & count.
    existing = db.regime_alerts.find_one(
        {"lane": lane, "alert_type": alert_type, "metric_generated_at": metric_generated_at},
        sort=[("first_seen_at", DESCENDING)],
    )
    if existing:
        db.regime_alerts.update_one(
            {"_id": existing["_id"]},
            {"$set": {"last_seen_at": now, "severity": severity, "message": message, "evidence": evidence}},
        )
        existing.update({"last_seen_at": now, "severity": severity, "message": message, "evidence": evidence})
        existing.pop("_id", None)
        return existing

    doc = {
        "lane": lane,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "metric_generated_at": metric_generated_at,
        "first_seen_at": now,
        "last_seen_at": now,
        "version": 1,
    }
    try:
        db.regime_alerts.insert_one(dict(doc))
    except Exception as e:
        logger.exception("regime_alerts insert failed: %s", e)
    doc.pop("_id", None)
    return doc


def evaluate_lane(db: Database, lane: str) -> List[Dict[str, Any]]:
    doc = _latest_metric(db, lane)
    out: List[Dict[str, Any]] = []
    if not doc:
        return out

    metric_ts = doc.get("generated_at")
    short = doc.get("short") or {}
    long_ = doc.get("long") or {}
    cross = doc.get("cross") or {}

    # -------- SHORT_EDGE_COLLAPSE --------
    n = int(short.get("resolved", 0))
    wr = short.get("wr")
    avg_pnl = short.get("avg_pnl")
    if n >= SHORT_EDGE_MIN_N and (
        (wr is not None and wr <= SHORT_EDGE_WR_MAX)
        or (avg_pnl is not None and avg_pnl <= SHORT_EDGE_AVG_PNL_MAX)
    ):
        out.append(_emit(
            db, lane, "SHORT_EDGE_COLLAPSE", "critical",
            f"SHORT edge collapsed on lane={lane}: n={n} wr={wr} avg_pnl={avg_pnl}",
            {"n": n, "wr": wr, "avg_pnl": avg_pnl},
            metric_ts,
        ))

    # -------- REGIME_DISAGREEMENT_HIGH --------
    dr = cross.get("disagreement_rate")
    nwith_v2 = int(doc.get("n_with_v2", 0))
    if dr is not None and dr >= DISAGREEMENT_HIGH and nwith_v2 >= 10:
        out.append(_emit(
            db, lane, "REGIME_DISAGREEMENT_HIGH", "warning",
            f"v1 vs v2 disagreement={dr:.2f} on lane={lane} (n_with_v2={nwith_v2})",
            {"disagreement_rate": dr, "n_with_v2": nwith_v2},
            metric_ts,
        ))

    # -------- V2_EXPLAINS_LOSSES --------
    pct = short.get("loss_when_v1_down_v2_not_down_pct")
    n_losses = int(short.get("losses", 0))
    if pct is not None and pct >= V2_EXPLAINS_THRESHOLD and n_losses >= 8:
        out.append(_emit(
            db, lane, "V2_EXPLAINS_LOSSES", "critical",
            f"v2 explains SHORT losses on lane={lane}: {pct:.2f} of "
            f"{n_losses} losses occurred when v1=DOWNTREND but v2!=DOWNTREND",
            {"loss_when_v1_down_v2_not_down_pct": pct, "short_losses": n_losses},
            metric_ts,
        ))

    # -------- LONG_EMERGENCE --------
    long_n = int(long_.get("resolved", 0))
    long_wr = long_.get("wr")
    long_avg = long_.get("avg_pnl")
    if long_n >= LONG_EDGE_MIN_N and (
        long_wr is not None and long_wr >= LONG_EDGE_WR_MIN
        and long_avg is not None and long_avg > LONG_EDGE_AVG_PNL_MIN
    ):
        out.append(_emit(
            db, lane, "LONG_EMERGENCE", "info",
            f"LONG edge emerging on lane={lane}: n={long_n} wr={long_wr} avg_pnl={long_avg}",
            {"n": long_n, "wr": long_wr, "avg_pnl": long_avg},
            metric_ts,
        ))
    return out


def run(db: Optional[Database] = None, persist: bool = True) -> Dict[str, Any]:
    owns_client = False
    client: Optional[MongoClient] = None
    if db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("PHASE_B1_DB", "trading_os")
        client = MongoClient(mongo_url)
        db = client[db_name]
        owns_client = True
    try:
        out: Dict[str, Any] = {"lanes": {}}
        for lane in ("phase_c", "discovery"):
            alerts = evaluate_lane(db, lane)
            out["lanes"][lane] = alerts
        return out
    finally:
        if owns_client and client is not None:
            client.close()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), default=str, indent=2))
