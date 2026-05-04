"""
Phase C.3.6 — Regime Decision Read API
=====================================

Endpoints:
  GET  /api/regime/accuracy              — latest regime_model_metrics (both lanes)
  GET  /api/regime/decision              — latest regime_decisions   (both lanes)
  GET  /api/regime/state                 — latest research_states    (both lanes)
  GET  /api/regime/alerts                — latest alerts per (lane, alert_type)
  GET  /api/regime/guard-events          — recent guard skip events (debug/observability)
  POST /api/regime/controls/short-v2-guard  — flip the feature flag

All GET endpoints are unauthenticated reads (same pattern as the rest of
the TA engine read surface). The POST is a deliberate admin action that
writes a single document to `regime_controls`; it requires an
`X-Admin-Token` header matching REGIME_ADMIN_TOKEN from env (if set).
If the env var is NOT set, the POST is accepted (local development mode).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pymongo import DESCENDING, MongoClient

router = APIRouter(prefix="/api/regime", tags=["regime"])

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")

_LANES = ("phase_c", "discovery")


def _db():
    client = MongoClient(MONGO_URL)
    return client, client[DB_NAME]


def _strip_id(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not d:
        return d
    d.pop("_id", None)
    return d


@router.get("/accuracy")
def get_accuracy():
    client, db = _db()
    try:
        out: Dict[str, Any] = {"lanes": {}}
        for lane in _LANES:
            doc = db.regime_model_metrics.find_one(
                {"lane": lane}, sort=[("generated_at", DESCENDING)],
            )
            out["lanes"][lane] = _strip_id(doc)
        return out
    finally:
        client.close()


@router.get("/decision")
def get_decision():
    client, db = _db()
    try:
        out: Dict[str, Any] = {"lanes": {}}
        for lane in _LANES:
            doc = db.regime_decisions.find_one(
                {"lane": lane}, sort=[("generated_at", DESCENDING)],
            )
            out["lanes"][lane] = _strip_id(doc)
        return out
    finally:
        client.close()


@router.get("/state")
def get_state():
    client, db = _db()
    try:
        out: Dict[str, Any] = {"lanes": {}}
        for lane in _LANES:
            doc = db.research_states.find_one(
                {"lane": lane}, sort=[("generated_at", DESCENDING)],
            )
            out["lanes"][lane] = _strip_id(doc)
        return out
    finally:
        client.close()


@router.get("/alerts")
def get_alerts(active_only: bool = True, limit: int = 50):
    """Latest alerts per (lane, alert_type). If active_only, returns the most
    recent alert per (lane, alert_type) pair. Otherwise returns the last
    `limit` alerts overall."""
    client, db = _db()
    try:
        if active_only:
            out: Dict[str, List[Dict[str, Any]]] = {l: [] for l in _LANES}
            for lane in _LANES:
                # latest per alert_type via aggregation
                pipeline = [
                    {"$match": {"lane": lane}},
                    {"$sort": {"last_seen_at": DESCENDING}},
                    {"$group": {
                        "_id": "$alert_type",
                        "doc": {"$first": "$$ROOT"},
                    }},
                ]
                for row in db.regime_alerts.aggregate(pipeline):
                    d = row["doc"]
                    d.pop("_id", None)
                    out[lane].append(d)
            return {"lanes": out}
        else:
            cursor = db.regime_alerts.find(
                {}, sort=[("last_seen_at", DESCENDING)],
            ).limit(int(limit))
            recent = [_strip_id(d) for d in cursor]
            return {"alerts": recent}
    finally:
        client.close()


@router.get("/guard-events")
def get_guard_events(lane: Optional[str] = None, limit: int = 50):
    client, db = _db()
    try:
        q: Dict[str, Any] = {}
        if lane:
            q["lane"] = lane
        cursor = db.regime_guard_events.find(q, sort=[("created_at", DESCENDING)]).limit(int(limit))
        items = [_strip_id(d) for d in cursor]
        count = db.regime_guard_events.count_documents(q)
        return {"total": count, "items": items}
    finally:
        client.close()


@router.get("/post-guard-report")
def get_post_guard_report():
    """Phase C.3c — 4-block POST-GUARD REPORT:
      A. phase_c (truth lane) post-guard stats
      B. discovery (exploratory) post-guard stats
      C. Guard Impact Delta (pre vs post, per-lane + combined)
      D. Regime evidence (accuracy + decision + state)
    Plus machine verdict: PASS / NEUTRAL / FAIL / INSUFFICIENT_POST_GUARD_DATA.

    Fully read-only — no strategy / detector / generator changes.
    """
    # Import lazily to avoid circular import at startup
    import sys
    sys.path.insert(0, "/app/backend")
    from modules.regime import regime_post_guard_report
    client, db = _db()
    try:
        return regime_post_guard_report.generate(db=db)
    finally:
        client.close()


@router.post("/controls/short-v2-guard")
def set_short_v2_guard(
    payload: Dict[str, Any] = Body(..., examples=[{"enabled": True}]),
    x_admin_token: Optional[str] = Header(default=None, convert_underscores=True),
):
    admin_token = os.environ.get("REGIME_ADMIN_TOKEN")
    if admin_token:
        if x_admin_token != admin_token:
            raise HTTPException(status_code=401, detail="invalid admin token")
    if "enabled" not in payload or not isinstance(payload["enabled"], bool):
        raise HTTPException(status_code=400, detail="body must contain {enabled: bool}")
    enabled = bool(payload["enabled"])
    now = datetime.now(timezone.utc)
    client, db = _db()
    try:
        db.regime_controls.update_one(
            {"control": "short_v2_guard_enabled"},
            {"$set": {
                "control": "short_v2_guard_enabled",
                "enabled": enabled,
                "updated_at": now,
                "updated_reason": payload.get("reason", "manual"),
            }},
            upsert=True,
        )
        doc = db.regime_controls.find_one({"control": "short_v2_guard_enabled"})
        return _strip_id(doc)
    finally:
        client.close()


@router.get("/controls/short-v2-guard")
def get_short_v2_guard():
    client, db = _db()
    try:
        doc = db.regime_controls.find_one({"control": "short_v2_guard_enabled"})
        if doc is None:
            return {"control": "short_v2_guard_enabled", "enabled": False, "updated_at": None}
        return _strip_id(doc)
    finally:
        client.close()
