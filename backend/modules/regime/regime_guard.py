"""
Phase C.3.3 — Regime Guard (feature-flagged, execution layer only)
==================================================================

Read-only helpers used by `scripts/phase_b1_regime_collection.py`
to decide whether a generated SHORT_TREND signal should be skipped.

Contract:
  * Does NOT modify any generator / strategy / regime logic.
  * OFF by default. Enabled only when
    `regime_controls.short_v2_guard_enabled.enabled == True`.
  * Per-cycle flag read (one round-trip), cached inside the caller.
  * Skips are logged into `regime_guard_events`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("regime_guard")

SHORT_V2_GUARD_CONTROL = "short_v2_guard_enabled"


def read_short_v2_guard_flag(db) -> Dict[str, Any]:
    """Return {'enabled': bool, 'updated_at': datetime|None}. Safe on any error."""
    try:
        doc = db.regime_controls.find_one({"control": SHORT_V2_GUARD_CONTROL})
        if doc is None:
            return {"enabled": False, "updated_at": None}
        return {
            "enabled": bool(doc.get("enabled", False)),
            "updated_at": doc.get("updated_at"),
        }
    except Exception as e:
        logger.warning("read_short_v2_guard_flag failed: %s", e)
        return {"enabled": False, "updated_at": None}


def should_skip_short(signal_strategy: str, regime_v1: Optional[str],
                     regime_v2: Optional[str]) -> bool:
    """True iff SHORT_TREND signal should be skipped under the v2 guard.

    Rule: if v1 says DOWNTREND but v2 disagrees (not DOWNTREND) — skip SHORT.
    """
    if (signal_strategy or "").upper() != "SHORT_TREND":
        return False
    v1 = (regime_v1 or "").upper()
    v2 = (regime_v2 or "").upper()
    # we only act when we have v2 and v2 disagrees with DOWNTREND call
    if not v2 or v2 == "UNKNOWN":
        return False
    if v1 == "DOWNTREND" and v2 != "DOWNTREND":
        return True
    # conservative default: also skip SHORT when v2 is UPTREND (loud disagreement)
    if v2 == "UPTREND":
        return True
    return False


def log_guard_skip(db, signal: Dict[str, Any], regime_info: Dict[str, Any],
                   regime_v2_debug: Dict[str, Any], experiment_id: str,
                   lane: Optional[str]) -> None:
    """Fire-and-forget insert into regime_guard_events. Must not raise."""
    try:
        db.regime_guard_events.insert_one({
            "type": "guard_skip",
            "strategy": regime_info.get("strategy"),
            "symbol": signal.get("symbol"),
            "timeframe": signal.get("timeframe"),
            "side": signal.get("side"),
            "lane": lane or "legacy",
            "experiment_id": experiment_id,
            "regime_v1": regime_info.get("regime") or (regime_v2_debug or {}).get("v1"),
            "regime_v2": (regime_v2_debug or {}).get("v2"),
            "v2_reason": (regime_v2_debug or {}).get("v2_reason"),
            "reason": "v2_guard_blocked_short",
            "created_at": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.warning("log_guard_skip insert failed: %s", e)
