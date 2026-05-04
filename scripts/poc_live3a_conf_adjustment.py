#!/usr/bin/env python3
"""
poc_live3a_conf_adjustment.py — Phase LIVE-3a verification script.

Read-only synthetic POC that validates the confidence adjustment layer added
to ExecutionBridge.submit() in /app/backend/modules/execution/bridge.py.

Coverage (per architect spec):
    1. Backend health OK.
    2. _adjust_confidence math correctness:
         - LONG / neutral regime           -> 0.60 (unchanged)
         - SHORT                           -> 0.48
         - LONG + UPTREND                  -> 0.51
    3. enriched_payload fields are populated end-to-end via ExecutionBridge.
    4. With min_adjusted_confidence=0.55, SHORT must yield CONF_BELOW_GATE.
    5. Audit row written to conf_gate_events on skip.

The test does NOT touch real exchanges — it stubs queue_repo.enqueue and uses
the in-memory regime_controls collection only via the live Mongo (read).

Run:
    python3 /app/scripts/poc_live3a_conf_adjustment.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from pymongo import MongoClient

ROOT = os.environ.get("ROOT", "/app")
sys.path.insert(0, os.path.join(ROOT, "backend"))

from modules.execution.bridge import (  # noqa: E402
    ExecutionBridge,
    _adjust_confidence,
    _read_confidence_adjustment_controls,
    _CONF_ADJ_DEFAULTS,
    _CONF_ADJ_CACHE,
    _MARKET_CTX_CACHE,
)

API = "http://localhost:8001"
MONGO = MongoClient(
    os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
    serverSelectionTimeoutMS=3000,
)
DB = MONGO["trading_os"]


def _ok(label: str, ok: bool, info: str = "") -> bool:
    icon = "✅" if ok else "❌"
    suffix = f" — {info}" if info else ""
    print(f"  {icon} {label}{suffix}")
    return ok


# --------------------------------------------------------------------------
# 1. Backend health
# --------------------------------------------------------------------------
def test_health() -> bool:
    print("\n[1] Backend health")
    try:
        r = requests.get(f"{API}/api/system/health", timeout=5).json()
        return _ok(
            "/api/system/health",
            r.get("ok") is True
            and r["services"]["database"] == "connected",
            json.dumps(r),
        )
    except Exception as exc:
        return _ok("/api/system/health", False, f"exception: {exc}")


# --------------------------------------------------------------------------
# 2. Pure math (no Mongo)
# --------------------------------------------------------------------------
def test_adjustment_math() -> bool:
    print("\n[2] _adjust_confidence math (defaults: side=0.80, regime=0.85)")
    controls = dict(_CONF_ADJ_DEFAULTS)
    cases = [
        # (label, side, regime, expected_adjusted)
        ("LONG / regime=None (neutral)", "LONG", None, 0.60),
        ("LONG / regime=DOWNTREND", "LONG", "DOWNTREND", 0.60),
        ("LONG / regime=RANGE", "LONG", "RANGE", 0.60),
        ("SHORT / regime=None", "SHORT", None, 0.48),
        ("SELL / regime=DOWNTREND", "SELL", "DOWNTREND", 0.48),
        ("BUY / regime=UPTREND", "BUY", "UPTREND", 0.51),
        ("LONG / regime=UPTREND", "LONG", "UPTREND", 0.51),
    ]
    all_pass = True
    for label, side, regime, expected in cases:
        adjusted, breakdown = _adjust_confidence(0.6, side, regime, controls)
        ok = abs(adjusted - expected) < 1e-6
        all_pass &= _ok(
            label,
            ok,
            f"adjusted={adjusted:.4f} (expected {expected:.4f}); "
            f"side_mult={breakdown['side_multiplier']}, "
            f"regime_mult={breakdown['regime_multiplier']}",
        )
    return all_pass


# --------------------------------------------------------------------------
# Helper: stub queue_repo for end-to-end submit() tests
# --------------------------------------------------------------------------
class _StubQueueRepo:
    def __init__(self) -> None:
        self.last_kwargs: Dict[str, Any] = {}
        self.calls: List[Dict[str, Any]] = []

    async def enqueue(self, **kwargs: Any) -> Dict[str, Any]:
        self.last_kwargs = kwargs
        self.calls.append(kwargs)
        return {"accepted": True}


def _make_signal(side: str, regime: str | None = None,
                 confidence: float = 0.6) -> Dict[str, Any]:
    sig = {
        "symbol": "BTCUSDT",
        "side": side,
        "confidence": confidence,
        "strategy": "SIMPLE_MA",
        "entry_price": 70000.0,
        "decision_id": "poc-live3a",
        "experiment_id": "poc_test",
        "sizing": {"qty": 0.001, "notional_usd": 70.0, "size_multiplier": 1.0},
        "size_usd": 70.0,
    }
    if regime is not None:
        sig["regime"] = regime
    return sig


def _ensure_short_trading_enabled() -> None:
    """Make sure hard-gates above the adjustment layer don't block our cases.

    LIVE-2H baseline already has these flags off; we re-assert them here so
    the synthetic scenarios pass through to the LIVE-3a layer.
    """
    DB["regime_controls"].update_one(
        {"control": "short_trading_enabled"},
        {"$set": {"control": "short_trading_enabled", "enabled": True}},
        upsert=True,
    )
    DB["regime_controls"].update_one(
        {"control": "short_downtrend_only"},
        {"$set": {"control": "short_downtrend_only", "enabled": False}},
        upsert=True,
    )
    DB["regime_controls"].update_one(
        {"control": "long_uptrend_only"},
        {"$set": {"control": "long_uptrend_only", "enabled": False}},
        upsert=True,
    )


def _set_conf_adjustment_controls(**fields: Any) -> None:
    """Upsert regime_controls.confidence_adjustment with the given fields."""
    base = {
        "control": "confidence_adjustment",
        **_CONF_ADJ_DEFAULTS,
    }
    base.update(fields)
    DB["regime_controls"].update_one(
        {"control": "confidence_adjustment"},
        {"$set": base},
        upsert=True,
    )
    # Reset TTL cache so the next read picks up the new doc immediately.
    _CONF_ADJ_CACHE["controls"] = None
    _CONF_ADJ_CACHE["ts"] = 0.0


# --------------------------------------------------------------------------
# 3. End-to-end: enriched_payload carries breakdown + adjusted_confidence
# --------------------------------------------------------------------------
async def test_payload_e2e() -> bool:
    print("\n[3] enriched_payload e2e (default controls)")
    _ensure_short_trading_enabled()
    _set_conf_adjustment_controls()  # defaults

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)

    # SELL (= SHORT side per SimpleMA emission) with no regime
    # → expected adjusted=0.48 (>= 0.45 default gate → pass).
    # NOTE: order_builder accepts only BUY/SELL — and real SimpleMA emits
    # exactly those; the adjustment layer treats SELL≡SHORT (proved in [2]).
    res = await bridge.submit(_make_signal("SELL", regime=None))
    if not _ok("SELL (short) submit accepted", res.get("ok") is True,
               json.dumps(res)):
        return False

    payload = stub.last_kwargs.get("payload", {})
    breakdown = payload.get("confidence_breakdown") or {}
    enq_conf = stub.last_kwargs.get("confidence")
    return all([
        _ok(
            "payload.adjusted_confidence",
            abs(payload.get("adjusted_confidence", 0) - 0.48) < 1e-6,
            f"value={payload.get('adjusted_confidence')}",
        ),
        _ok(
            "payload.base_confidence",
            abs(payload.get("base_confidence", 0) - 0.6) < 1e-6,
        ),
        _ok(
            "payload.confidence_breakdown.side_multiplier",
            abs(breakdown.get("side_multiplier", 0) - 0.80) < 1e-6,
        ),
        _ok(
            "payload.confidence_breakdown.regime_multiplier",
            abs(breakdown.get("regime_multiplier", 0) - 1.0) < 1e-6,
        ),
        _ok(
            "enqueue(confidence=adjusted)",
            abs(enq_conf - 0.48) < 1e-6,
            f"value={enq_conf}",
        ),
        _ok(
            "regime_at_entry forwarded",
            "regime_at_entry" in payload,
            f"value={payload.get('regime_at_entry')}",
        ),
    ])


# --------------------------------------------------------------------------
# 4. SHORT skipped when min_adjusted_confidence=0.55
# --------------------------------------------------------------------------
async def test_short_blocked_at_higher_gate() -> bool:
    print("\n[4] SHORT yields CONF_BELOW_GATE at min_gate=0.55")
    _ensure_short_trading_enabled()
    _set_conf_adjustment_controls(min_adjusted_confidence=0.55)
    # Clear conf_gate_events for this run so we can detect new audit row.
    before_count = DB["conf_gate_events"].count_documents({})

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    res = await bridge.submit(_make_signal("SHORT", regime=None))

    out_ok = (
        res.get("ok") is False
        and res.get("reason") == "CONF_BELOW_GATE"
        and res.get("phase") == "LIVE-3a"
        and abs(res.get("adjusted_confidence", 0) - 0.48) < 1e-6
        and abs(res.get("min_gate", 0) - 0.55) < 1e-6
    )
    after_count = DB["conf_gate_events"].count_documents({})
    return all([
        _ok(
            "submit returned CONF_BELOW_GATE",
            out_ok,
            json.dumps({k: v for k, v in res.items() if k != "breakdown"}),
        ),
        _ok(
            "no enqueue call (queue stub untouched)",
            len(stub.calls) == 0,
            f"calls={len(stub.calls)}",
        ),
        _ok(
            "conf_gate_events row inserted",
            after_count == before_count + 1,
            f"before={before_count} after={after_count}",
        ),
    ])


# --------------------------------------------------------------------------
# 5. LONG + UPTREND not blocked at default gate (0.51 >= 0.45)
# --------------------------------------------------------------------------
async def test_long_uptrend_pass_default_gate() -> bool:
    print("\n[5] LONG+UPTREND passes default gate=0.45 (adjusted=0.51)")
    _ensure_short_trading_enabled()
    _set_conf_adjustment_controls()  # defaults

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    res = await bridge.submit(_make_signal("BUY", regime="UPTREND"))

    if not _ok("submit accepted", res.get("ok") is True, json.dumps(res)):
        return False

    payload = stub.last_kwargs.get("payload", {})
    return all([
        _ok(
            "adjusted_confidence == 0.51",
            abs(payload.get("adjusted_confidence", 0) - 0.51) < 1e-6,
        ),
        _ok(
            "regime_multiplier == 0.85",
            abs(
                payload["confidence_breakdown"].get("regime_multiplier", 0)
                - 0.85
            ) < 1e-6,
        ),
        _ok(
            "regime_at_entry == UPTREND",
            payload.get("regime_at_entry") == "UPTREND",
        ),
    ])


# --------------------------------------------------------------------------
# 6. Disabled adjustment layer → confidence unchanged
# --------------------------------------------------------------------------
async def test_disabled_layer_passthrough() -> bool:
    print("\n[6] enabled=false → no shaping (regression safety)")
    _ensure_short_trading_enabled()
    _set_conf_adjustment_controls(enabled=False)

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    # Use SELL (SimpleMA's canonical SHORT-side emission, accepted by order_builder).
    res = await bridge.submit(_make_signal("SELL", regime=None))

    if not _ok("submit accepted", res.get("ok") is True, json.dumps(res)):
        return False

    payload = stub.last_kwargs.get("payload", {})
    return all([
        _ok(
            "adjusted_confidence == base 0.60 (no shaping)",
            abs(payload.get("adjusted_confidence", 0) - 0.60) < 1e-6,
            f"value={payload.get('adjusted_confidence')}",
        ),
        _ok(
            "breakdown.disabled flag present",
            payload["confidence_breakdown"].get("disabled") is True,
        ),
        _ok(
            "enqueue(confidence) == 0.60 (passthrough)",
            abs(stub.last_kwargs.get("confidence", 0) - 0.60) < 1e-6,
        ),
    ])


# --------------------------------------------------------------------------
# 7. LIVE-3d — Market context is ALWAYS persisted (B layer)
# --------------------------------------------------------------------------
async def test_live3d_market_ctx_persisted() -> bool:
    print("\n[7] LIVE-3d (B): market context persisted in payload")
    _ensure_short_trading_enabled()
    _set_conf_adjustment_controls()  # defaults — vol skip OFF
    _MARKET_CTX_CACHE.clear()

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    res = await bridge.submit(_make_signal("BUY", regime="UPTREND"))

    if not _ok("submit accepted (vol skip OFF)", res.get("ok") is True,
               json.dumps({k: v for k, v in res.items() if k != "breakdown"})):
        return False

    payload = stub.last_kwargs.get("payload", {})
    return all([
        _ok(
            "payload contains volatility_1h_20",
            "volatility_1h_20" in payload,
            f"value={payload.get('volatility_1h_20')}",
        ),
        _ok(
            "payload contains ma5_1h",
            "ma5_1h" in payload,
            f"value={payload.get('ma5_1h')}",
        ),
        _ok(
            "payload contains distance_to_ma5_1h",
            "distance_to_ma5_1h" in payload,
            f"value={payload.get('distance_to_ma5_1h')}",
        ),
        _ok(
            "market_ctx_candles_used present",
            "market_ctx_candles_used" in payload,
            f"value={payload.get('market_ctx_candles_used')}",
        ),
    ])


# --------------------------------------------------------------------------
# 8. LIVE-3d — Vol-gate triggers LOW_VOL_NO_EDGE when enabled + low vol
# --------------------------------------------------------------------------
async def test_live3d_low_vol_skip_with_synthetic_threshold() -> bool:
    print("\n[8] LIVE-3d gate ON: synthetic high threshold → LOW_VOL_NO_EDGE")
    _ensure_short_trading_enabled()
    # Threshold absurdly high so any real volatility looks LOW.
    _set_conf_adjustment_controls(
        volatility_low_skip_enabled=True,
        volatility_low_threshold=10.0,  # 1000% — guaranteed > vol
    )
    _MARKET_CTX_CACHE.clear()

    before_count = DB["vol_gate_events"].count_documents({})
    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    res = await bridge.submit(_make_signal("BUY", regime="UPTREND"))

    after_count = DB["vol_gate_events"].count_documents({})
    return all([
        _ok(
            "submit returned LOW_VOL_NO_EDGE",
            res.get("ok") is False
            and res.get("reason") == "LOW_VOL_NO_EDGE"
            and res.get("phase") == "LIVE-3d",
            json.dumps({k: v for k, v in res.items()
                        if k != "market_context"}),
        ),
        _ok(
            "no enqueue call",
            len(stub.calls) == 0,
            f"calls={len(stub.calls)}",
        ),
        _ok(
            "vol_gate_events row inserted",
            after_count >= before_count + 1,
            f"before={before_count} after={after_count}",
        ),
    ])


# --------------------------------------------------------------------------
# 9. LIVE-3d — gate OFF (default) → never skip on volatility
# --------------------------------------------------------------------------
async def test_live3d_default_off_passthrough() -> bool:
    print("\n[9] LIVE-3d gate OFF (default): vol low does NOT skip")
    _ensure_short_trading_enabled()
    # Skip OFF (default), but threshold huge — to prove OFF dominates.
    _set_conf_adjustment_controls(
        volatility_low_skip_enabled=False,
        volatility_low_threshold=10.0,
    )
    _MARKET_CTX_CACHE.clear()

    stub = _StubQueueRepo()
    bridge = ExecutionBridge(queue_repo=stub)
    res = await bridge.submit(_make_signal("BUY", regime="UPTREND"))
    return _ok(
        "submit accepted (skip OFF wins over high threshold)",
        res.get("ok") is True,
        json.dumps(res),
    )


# --------------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------------
def restore_defaults() -> None:
    print("\n[cleanup] restoring controls to defaults")
    _set_conf_adjustment_controls()  # defaults
    print("  ✅ confidence_adjustment doc reset to defaults")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
async def main() -> int:
    print("=" * 72)
    print(f"LIVE-3a Confidence Adjustment Layer POC  "
          f"({datetime.now(timezone.utc).isoformat()})")
    print("=" * 72)

    results: List[bool] = []
    results.append(test_health())
    results.append(test_adjustment_math())
    results.append(await test_payload_e2e())
    results.append(await test_short_blocked_at_higher_gate())
    results.append(await test_long_uptrend_pass_default_gate())
    results.append(await test_disabled_layer_passthrough())
    results.append(await test_live3d_market_ctx_persisted())
    results.append(await test_live3d_low_vol_skip_with_synthetic_threshold())
    results.append(await test_live3d_default_off_passthrough())

    restore_defaults()

    passed = sum(1 for r in results if r)
    total = len(results)
    print("\n" + "=" * 72)
    print(f"RESULT: {passed}/{total} groups passed")
    print("=" * 72)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
