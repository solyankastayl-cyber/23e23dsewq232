"""
Phase C.3.4 — Research State Machine
====================================

Derives the current research state per lane from:
  * regime_model_metrics (did we collect enough?)
  * regime_decisions     (what does the engine say?)
  * regime_controls      (is the guard actually enabled?)
  * shadow_trades        (is there post-guard data yet?)

States:
  COLLECTING       — metrics thin, not enough resolved trades
  ANALYZING        — enough data, decision engine is computing, verdict pending / STAY_V1
  DECISION_READY   — verdict is ENABLE_V2_GUARD / SWITCH_TO_V2_CANDIDATE but control flag is OFF
  GUARD_ENABLED    — control flag is ON, waiting for post-switch trades
  VALIDATING       — guard enabled and we have enough post-switch trades to validate impact

Policy:
  * Purely observational; never flips flags, never creates trades.
  * Idempotent per run; stores one document per (lane, generated_at).
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import MongoClient, DESCENDING
from pymongo.database import Database

logger = logging.getLogger("research_state_machine")

MIN_RESOLVED_FOR_ANALYZING = 20
MIN_POST_GUARD_TRADES_FOR_VALIDATING = 10


def _latest(db: Database, collection: str, lane: str, ts_field: str = "generated_at") -> Optional[Dict[str, Any]]:
    return db[collection].find_one({"lane": lane}, sort=[(ts_field, DESCENDING)])


def _guard_flag(db: Database) -> Dict[str, Any]:
    doc = db.regime_controls.find_one({"control": "short_v2_guard_enabled"})
    if doc is None:
        return {"enabled": False, "updated_at": None}
    return {
        "enabled": bool(doc.get("enabled", False)),
        "updated_at": doc.get("updated_at"),
    }


def _post_guard_trades_count(db: Database, lane: str, since) -> int:
    if since is None:
        return 0
    from .regime_accuracy_service import LANE_EXPERIMENT_MAP
    exps = LANE_EXPERIMENT_MAP.get(lane, [])
    if not exps:
        return 0
    return db.shadow_trades.count_documents({
        "experiment_id": {"$in": exps},
        "horizons.resolved": True,
        "created_at": {"$gte": since},
    })


def evaluate_lane(db: Database, lane: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    metric = _latest(db, "regime_model_metrics", lane)
    decision = _latest(db, "regime_decisions", lane)
    guard = _guard_flag(db)

    n_resolved = int((metric or {}).get("n_resolved", 0))
    verdict = (decision or {}).get("verdict") or "UNKNOWN"

    state = "COLLECTING"
    reason = f"n_resolved={n_resolved}"

    # Manual-override detection: if guard is ENABLED, we are either
    # GUARD_ENABLED or VALIDATING regardless of the latest verdict
    # (architect override path — Phase C.3b).
    if guard["enabled"]:
        post_n = _post_guard_trades_count(db, lane, guard["updated_at"])
        if post_n >= MIN_POST_GUARD_TRADES_FOR_VALIDATING:
            state = "VALIDATING"
        else:
            state = "GUARD_ENABLED"
        reason = (
            f"guard ENABLED since {guard['updated_at']}; "
            f"post_guard_trades={post_n}; verdict={verdict}"
        )
    elif n_resolved < MIN_RESOLVED_FOR_ANALYZING:
        state = "COLLECTING"
        reason = f"need {MIN_RESOLVED_FOR_ANALYZING} resolved, have {n_resolved}"
    else:
        # enough data exists, guard OFF
        if verdict in ("ENABLE_V2_GUARD", "SWITCH_TO_V2_CANDIDATE"):
            state = "DECISION_READY"
            reason = f"verdict={verdict} but control flag is OFF"
        elif verdict == "INSUFFICIENT_DATA":
            state = "COLLECTING"
            reason = f"verdict=INSUFFICIENT_DATA n_resolved={n_resolved}"
        else:  # STAY_V1 or unknown
            state = "ANALYZING"
            reason = f"verdict={verdict}; no action required"

    doc = {
        "generated_at": now,
        "lane": lane,
        "state": state,
        "reason": reason,
        "n_resolved": n_resolved,
        "verdict": verdict,
        "guard_enabled": guard["enabled"],
        "guard_updated_at": guard["updated_at"],
        "version": 1,
    }
    return doc


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
            doc = evaluate_lane(db, lane)
            if persist:
                try:
                    db.research_states.insert_one(dict(doc))
                except Exception as e:
                    logger.exception("research_states insert failed: %s", e)
            doc.pop("_id", None)
            out["lanes"][lane] = doc
        return out
    finally:
        if owns_client and client is not None:
            client.close()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), default=str, indent=2))
