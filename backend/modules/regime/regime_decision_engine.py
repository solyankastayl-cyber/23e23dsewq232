"""
Phase C.3.2 — Regime Decision Engine
====================================

Reads the latest `regime_model_metrics` document for a lane and emits a
machine verdict about the v1 vs v2 regime detector hypothesis.

Verdict space (hard rules, no ML):
  * INSUFFICIENT_DATA       — not enough resolved trades yet to decide
  * STAY_V1                 — no evidence v2 helps; keep current detector
  * ENABLE_V2_GUARD         — SHORT losses concentrate in v1=DOWN/v2!=DOWN
                              state; turning on feature-flagged guard is
                              safe (skips SHORTs v2 doesn't confirm)
  * SWITCH_TO_V2_CANDIDATE  — v2 outperforms v1 in both lanes consistently
                              and disagreement is systematic

Output:
  * `regime_decisions` (one document per run, per lane)

Policy:
  * Never changes detectors, generators, routers.
  * Guardrail flipping is handled by a separate explicit admin action.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import MongoClient, DESCENDING
from pymongo.database import Database

logger = logging.getLogger("regime_decision_engine")

# ---------------------------------------------------------------------------
#  Thresholds (editable only via this file; no runtime tuning)
# ---------------------------------------------------------------------------
MIN_TRUTH_RESOLVED = 20           # need >=20 phase_c resolved trades
MIN_SHORT_RESOLVED = 10           # need >=10 SHORT resolved
MIN_SHORT_LOSSES_FOR_GUARD = 8    # need >=8 short losses to trust the pattern
LOSS_CONCENTRATION_THRESHOLD = 0.60  # >=60% of short losses in v1=DOWN/v2!=DOWN
DISAGREEMENT_SYSTEMATIC = 0.30    # disagreement >=30% counts as "systematic"
SWITCH_V2_MIN_WR_DELTA = 0.15     # v2-explained WR beats v1 WR by >=15 p.p.


def _latest_metric_doc(db: Database, lane: str) -> Optional[Dict[str, Any]]:
    return db.regime_model_metrics.find_one(
        {"lane": lane},
        sort=[("generated_at", DESCENDING)],
    )


def _v2_wr_for_short_in_downtrend(doc: Dict[str, Any]) -> Optional[float]:
    """Compute the WR for SHORTs where v2 ALSO says DOWNTREND.
    Proxy for 'if we had only fired SHORT when v2 confirmed'. Uses
    matrix_short['v1_DOWNTREND__v2_DOWNTREND'] if present.
    """
    m = (doc.get("matrix_short") or {}).get("v1_DOWNTREND__v2_DOWNTREND")
    if not m or not m.get("count"):
        return None
    wins = m.get("wins", 0)
    n = m.get("count", 0)
    if n <= 0:
        return None
    return round(wins / n, 4)


def evaluate(db: Database, lane: str = "phase_c") -> Dict[str, Any]:
    """Produce a verdict dict for the given lane."""
    doc = _latest_metric_doc(db, lane)
    now = datetime.now(timezone.utc)

    if not doc:
        return {
            "generated_at": now,
            "lane": lane,
            "verdict": "INSUFFICIENT_DATA",
            "confidence": 0.0,
            "reason": "no regime_model_metrics for this lane yet",
            "evidence": {},
            "version": 1,
        }

    n_resolved = int(doc.get("n_resolved", 0))
    short = doc.get("short") or {}
    long_ = doc.get("long") or {}
    cross = doc.get("cross") or {}

    short_resolved = int(short.get("resolved", 0))
    short_losses   = int(short.get("losses", 0))
    short_wr       = short.get("wr")
    short_avg_pnl  = short.get("avg_pnl")
    loss_conc      = short.get("loss_when_v1_down_v2_not_down_pct")
    loss_conc_n    = int(short.get("loss_when_v1_down_v2_not_down_n", 0))

    disagreement_rate = cross.get("disagreement_rate")

    # Cross-lane evidence for SWITCH_TO_V2_CANDIDATE: look at discovery too
    cross_lane_doc = None
    if lane == "phase_c":
        cross_lane_doc = _latest_metric_doc(db, "discovery")

    evidence: Dict[str, Any] = {
        "n_resolved": n_resolved,
        "short_resolved": short_resolved,
        "short_losses": short_losses,
        "short_wr": short_wr,
        "short_avg_pnl": short_avg_pnl,
        "loss_when_v1_down_v2_not_down_pct": loss_conc,
        "loss_when_v1_down_v2_not_down_n": loss_conc_n,
        "disagreement_rate": disagreement_rate,
        "v2_confirmed_short_wr": _v2_wr_for_short_in_downtrend(doc),
    }

    # ---------------- 1) INSUFFICIENT_DATA ----------------
    if n_resolved < MIN_TRUTH_RESOLVED or short_resolved < MIN_SHORT_RESOLVED:
        return {
            "generated_at": now,
            "lane": lane,
            "verdict": "INSUFFICIENT_DATA",
            "confidence": 0.0,
            "reason": (
                f"need n_resolved>={MIN_TRUTH_RESOLVED} "
                f"(got {n_resolved}) and short_resolved>={MIN_SHORT_RESOLVED} "
                f"(got {short_resolved})"
            ),
            "evidence": evidence,
            "version": 1,
        }

    # ---------------- 2) ENABLE_V2_GUARD ------------------
    # strong pattern: SHORT edge broken AND v2 explains the losses
    short_wr_broken = (short_wr is not None and short_wr <= 0.30)
    short_avg_negative = (short_avg_pnl is not None and short_avg_pnl < 0)
    loss_concentration_high = (loss_conc is not None and loss_conc >= LOSS_CONCENTRATION_THRESHOLD)
    enough_losses = short_losses >= MIN_SHORT_LOSSES_FOR_GUARD

    guard_ready = (
        (short_wr_broken or short_avg_negative)
        and loss_concentration_high
        and enough_losses
    )

    # ---------------- 3) SWITCH_TO_V2_CANDIDATE -----------
    # Consistency check across truth + discovery
    v2_confirmed_wr = _v2_wr_for_short_in_downtrend(doc)
    cross_v2_confirmed_wr = (
        _v2_wr_for_short_in_downtrend(cross_lane_doc) if cross_lane_doc else None
    )
    systematic_disagreement = (
        disagreement_rate is not None and disagreement_rate >= DISAGREEMENT_SYSTEMATIC
    )
    both_confirm_v2 = (
        v2_confirmed_wr is not None
        and short_wr is not None
        and (v2_confirmed_wr - (short_wr or 0.0)) >= SWITCH_V2_MIN_WR_DELTA
    )
    discovery_confirms_pattern = False
    if cross_lane_doc:
        cd_short = (cross_lane_doc.get("short") or {})
        cd_loss_conc = cd_short.get("loss_when_v1_down_v2_not_down_pct")
        cd_losses = int(cd_short.get("losses", 0))
        discovery_confirms_pattern = (
            cd_losses >= 5 and cd_loss_conc is not None
            and cd_loss_conc >= LOSS_CONCENTRATION_THRESHOLD
        )

    switch_ready = (
        guard_ready
        and systematic_disagreement
        and both_confirm_v2
        and discovery_confirms_pattern
    )

    if switch_ready:
        return {
            "generated_at": now,
            "lane": lane,
            "verdict": "SWITCH_TO_V2_CANDIDATE",
            "confidence": 0.9,
            "reason": (
                "v2 consistently beats v1 on SHORT, disagreement systematic, "
                "and discovery lane confirms the same pattern."
            ),
            "evidence": evidence,
            "cross_lane_evidence": (cross_lane_doc or {}).get("short") if cross_lane_doc else None,
            "version": 1,
        }

    if guard_ready:
        # confidence scales with loss_conc and n_losses
        conf_base = max(0.6, min(0.95, float(loss_conc or 0.6)))
        if short_losses >= 15:
            conf_base = min(0.95, conf_base + 0.05)
        return {
            "generated_at": now,
            "lane": lane,
            "verdict": "ENABLE_V2_GUARD",
            "confidence": round(conf_base, 2),
            "reason": (
                "SHORT edge broken and losses are highly concentrated in "
                "v1=DOWNTREND / v2!=DOWNTREND state. Enabling the v2 guard "
                "skips SHORTs v2 does not confirm; no other logic changes."
            ),
            "evidence": evidence,
            "version": 1,
        }

    # ---------------- 4) STAY_V1 --------------------------
    return {
        "generated_at": now,
        "lane": lane,
        "verdict": "STAY_V1",
        "confidence": 0.5,
        "reason": (
            "No strong evidence that v2 fixes v1; keep current detector. "
            "Either SHORT WR is not broken, or v2 doesn't concentrate the "
            "losses beyond the threshold, or data is still noisy."
        ),
        "evidence": evidence,
        "version": 1,
    }


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
        out = {"lanes": {}}
        for lane in ("phase_c", "discovery"):
            doc = evaluate(db, lane)
            if persist:
                try:
                    db.regime_decisions.insert_one(dict(doc))
                except Exception as e:
                    logger.exception("regime_decisions insert failed lane=%s: %s", lane, e)
            doc.pop("_id", None)
            out["lanes"][lane] = doc
        return out
    finally:
        if owns_client and client is not None:
            client.close()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), default=str, indent=2))
