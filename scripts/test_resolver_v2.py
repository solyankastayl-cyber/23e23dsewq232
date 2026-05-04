#!/usr/bin/env python3
"""
test_resolver_v2.py — smoke tests for resolve_winning_scenario after
FIX-RESOLVER-1+2 (within-bar tie-break + invalidation state machine).

Self-contained: imports the function from the live module and exercises
six deterministic scenarios with hand-crafted candle highs/lows.

Pure read of the module. Does not touch Mongo.
Exit code 0 if all pass, 1 if any fail.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, "/app/backend")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "trading_os")

from modules.ta_prediction_intelligence.evaluation.ta_prediction_outcome_worker import (  # noqa: E402
    resolve_winning_scenario,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------
ENTRY = 1000.0


def scenarios(*, t_bull: float, inv_bull: float,
              t_bear: float, inv_bear: float) -> List[Dict[str, Any]]:
    return [
        {"name": "bull", "target_price": t_bull, "invalidation_price": inv_bull},
        {"name": "base"},
        {"name": "bear", "target_price": t_bear, "invalidation_price": inv_bear},
    ]


def candle(high: float, low: float, close: float = None) -> Dict[str, Any]:
    return {"high": high, "low": low, "close": close if close is not None else (high + low) / 2}


# Default scenario set used by most tests:
#   entry = 1000
#   bull target = 1010, bull invalidation = 995
#   bear target =  990, bear invalidation = 1005
DEFAULT_SCEN = scenarios(t_bull=1010, inv_bull=995, t_bear=990, inv_bear=1005)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def assert_eq(label: str, expected: str, actual: str) -> bool:
    ok = expected == actual
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}: expected={expected!r} got={actual!r}")
    return ok


def test_only_bull_target_hits() -> bool:
    """High goes up to t_bull cleanly; low never touches anything dangerous."""
    candles = [
        candle(high=1003, low=1001),  # nothing
        candle(high=1011, low=1002),  # bull target hit (1011 >= 1010)
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.001)
    return assert_eq("only bull target hits → bull", "bull", res)


def test_only_bear_target_hits() -> bool:
    """Low touches t_bear cleanly; high stays well below bear invalidation."""
    candles = [
        candle(high=1001, low=998),
        candle(high=1002, low=989),  # bear target hit (989 <= 990)
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=-0.001)
    return assert_eq("only bear target hits → bear", "bear", res)


def test_within_bar_both_targets_hit() -> bool:
    """One bar straddles BOTH targets in [low, high] — must resolve to base."""
    candles = [
        candle(high=1012, low=988),  # high>=1010 AND low<=990 in same bar
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.0)
    return assert_eq("within-bar bull+bear both hit → base", "base", res)


def test_both_invalidations_no_target() -> bool:
    """Bar 1: bull invalidates (low<=995). Bar 2: bear invalidates (high>=1005).
    Neither target ever hit. Must resolve to base."""
    candles = [
        candle(high=1003, low=994),   # bull_dead
        candle(high=1006, low=999),   # bear_dead → base
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.0)
    return assert_eq("both invalidations no target → base", "base", res)


def test_bull_invalidation_then_bear_target() -> bool:
    """Bull invalidates first, then bear target hit. Must resolve to bear
    (not base) because bear_dead never set and bear target is reached."""
    candles = [
        candle(high=1003, low=993),   # bull_dead (low<=995)
        candle(high=1004, low=988),   # bear target hit (988<=990)
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=-0.001)
    return assert_eq("bull invalidated, then bear target → bear", "bear", res)


def test_bear_invalidation_then_bull_target() -> bool:
    """Mirror: bear invalidates first, then bull target hit → bull."""
    candles = [
        candle(high=1006, low=997),   # bear_dead (high>=1005)
        candle(high=1011, low=998),   # bull target hit
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.001)
    return assert_eq("bear invalidated, then bull target → bull", "bull", res)


def test_no_resolution_falls_back_to_return_h6_above() -> bool:
    """No target, no double-invalidation, but return_h6 > +10% → bull (legacy
    fallback intentionally untouched in this commit)."""
    candles = [
        candle(high=1002, low=998),   # nothing happens
        candle(high=1003, low=999),
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.12)
    return assert_eq("no resolution, return_h6=0.12 → bull (fallback)", "bull", res)


def test_no_resolution_falls_back_to_base() -> bool:
    """No target, no double-invalidation, return_h6 within ±10% → base."""
    candles = [
        candle(high=1002, low=998),
        candle(high=1003, low=999),
    ]
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, candles, return_h6=0.001)
    return assert_eq("no resolution, return_h6=0.1% → base (fallback)", "base", res)


def test_old_bug_replication_within_bar_now_base() -> bool:
    """Replicate the exact pattern that produced 36/50 spurious bulls in
    historical data: a single 1H bar whose [low, high] straddles narrow
    targets centred near entry. Must now produce 'base', not 'bull'."""
    scen = scenarios(t_bull=1000.78, inv_bull=999.5,
                     t_bear=999.22, inv_bear=1000.5)
    candles = [candle(high=1001.2, low=998.8)]  # straddles everything
    res = resolve_winning_scenario(ENTRY, scen, candles, return_h6=0.0)
    return assert_eq("regression: narrow straddled targets → base (not bull)",
                     "base", res)


def test_empty_candles_returns_base() -> bool:
    res = resolve_winning_scenario(ENTRY, DEFAULT_SCEN, [], return_h6=0.0)
    return assert_eq("empty candles → base", "base", res)


def test_no_targets_no_invalidation_uses_fallback() -> bool:
    """Scenarios without any target/invalidation must fall through to the
    return_h6 path (cannot enter the candle loop)."""
    no_targets = [{"name": "bull"}, {"name": "base"}, {"name": "bear"}]
    candles = [candle(high=1100, low=900)]  # huge range, but no targets
    res_b = resolve_winning_scenario(ENTRY, no_targets, candles, return_h6=0.20)
    res_n = resolve_winning_scenario(ENTRY, no_targets, candles, return_h6=0.05)
    ok1 = assert_eq("no targets, return_h6=20% → bull", "bull", res_b)
    ok2 = assert_eq("no targets, return_h6=5% → base", "base", res_n)
    return ok1 and ok2


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
TESTS = [
    test_only_bull_target_hits,
    test_only_bear_target_hits,
    test_within_bar_both_targets_hit,
    test_both_invalidations_no_target,
    test_bull_invalidation_then_bear_target,
    test_bear_invalidation_then_bull_target,
    test_no_resolution_falls_back_to_return_h6_above,
    test_no_resolution_falls_back_to_base,
    test_old_bug_replication_within_bar_now_base,
    test_empty_candles_returns_base,
    test_no_targets_no_invalidation_uses_fallback,
]


def main() -> int:
    print("=" * 70)
    print("RESOLVER v2 SMOKE TESTS — FIX-RESOLVER-1+2")
    print("=" * 70)
    results = [t() for t in TESTS]
    passed = sum(1 for r in results if r)
    total = len(results)
    print()
    print(f"  PASSED {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
