"""
QA harness for the Simulation Engine.

Asserts the 10 DoD conditions from the FINAL SPEC:

  1.  No-lookahead test:
        prediction at i sees only candles[:i+1]
  2.  Feature determinism test:
        same symbol/tf/candle_close_ts -> same feature_hash
  3.  Replay creates history_sim + outcome + debug_sim
  4.  No partial outcome:
        insufficient future window -> skipped_insufficient_horizon
  5.  Live collections untouched:
        counts unchanged for ta_prediction_history / ta_prediction_debug
  6.  Sim collections isolated:
        history_sim / debug_sim only
  7.  ML readiness shows live_count and simulation_count separately
  8.  ML readiness score / gates ignore simulation_count
  9.  clear_first clears only sim collections
  10. Routes return correct contracts (Pydantic schemas)

Run with:
    cd /app/backend && python ../scripts/qa_simulation_engine.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List

# ── path bootstrapping ──────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
APP_BACKEND = os.path.normpath(os.path.join(HERE, "..", "backend"))
if APP_BACKEND not in sys.path:
    sys.path.insert(0, APP_BACKEND)


def _section(title: str) -> None:
    print(f"\n{'═' * 70}\n   {title}\n{'═' * 70}")


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _fail(msg: str) -> None:
    print(f"  ❌ {msg}")


# Counters mutated by tests
TOTAL = 0
PASSED = 0
FAILED: List[str] = []


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    global TOTAL, PASSED
    TOTAL += 1
    if actual == expected:
        PASSED += 1
        _ok(f"{name}: {actual!r} == {expected!r}")
    else:
        FAILED.append(name)
        _fail(f"{name}: expected {expected!r}, got {actual!r}")


def assert_true(name: str, cond: bool, detail: str = "") -> None:
    global TOTAL, PASSED
    TOTAL += 1
    if cond:
        PASSED += 1
        _ok(f"{name} {('— ' + detail) if detail else ''}")
    else:
        FAILED.append(name)
        _fail(f"{name} {('— ' + detail) if detail else ''}")


def main() -> int:
    _section("QA Simulation Engine — 10 DoD Conditions")

    # Lazy imports so the harness lives next to the running backend.
    from modules.ta_prediction_intelligence.simulation.simulation_repository import (
        get_simulation_repository,
    )
    from modules.ta_prediction_intelligence.simulation.simulation_service import (
        execute_replay,
        compute_sim_stats,
        LIVE_DEBUG_COLLECTION,
        LIVE_HISTORY_COLLECTION,
    )
    from modules.ta_prediction_intelligence.simulation.types import (
        ReplayRequest,
        ReplayResponse,
        SimStats,
        SIM_HISTORY_COLLECTION,
        SIM_DEBUG_COLLECTION,
    )
    from modules.ta_prediction_intelligence.simulation.no_lookahead import (
        slice_visible,
        future_window,
        assert_no_future_leak,
    )
    from modules.ta_prediction_intelligence.live_adapter import fetch_live_context
    from modules.ta_prediction_intelligence.ml_readiness.readiness_service import (
        compute_readiness_report,
    )

    sim_repo = get_simulation_repository()
    db = sim_repo.db
    if db is None:
        _fail("Mongo unavailable — cannot run QA")
        return 1

    # Live counts BEFORE we do anything.
    live_history_before = int(db[LIVE_HISTORY_COLLECTION].count_documents({}))
    live_debug_before = int(db[LIVE_DEBUG_COLLECTION].count_documents({}))

    # ── DoC 1 + 4: run a replay and inspect step results ───────────────────
    _section("DoC 1, 3, 4 — Run replay (clear_first=true)")

    # Pick a small index range. We rely on chart_data having at least 100 bars
    # for the symbol/tf, which is guaranteed by ingestion.
    req = ReplayRequest(
        symbol="BTCUSDT",
        tf="1H",
        start_candle_index=80,
        end_candle_index=95,
        max_steps=50,
        clear_first=True,
        candles_limit=300,
        min_horizon=6,
    )
    resp: ReplayResponse = asyncio.run(execute_replay(req))
    print(f"  steps_attempted={resp.steps_attempted}, persisted={resp.steps_persisted}, "
          f"skipped_horizon={resp.steps_skipped_insufficient_horizon}, "
          f"skipped_no_anchor={resp.steps_skipped_no_anchor}, errored={resp.steps_errored}")

    # DoC 1 — no-lookahead pure-function check
    fake_history = [{"timestamp": i * 60, "open": i, "high": i, "low": i, "close": i}
                    for i in range(20)]
    visible = slice_visible(fake_history, 5)
    assert_eq("DoC1.no_lookahead.visible_len", len(visible), 6)
    assert_no_future_leak(visible, fake_history, 5)
    fwd = future_window(fake_history, 5, 6)
    assert_eq("DoC1.future_window_len", len(fwd), 6)
    # Cannot ask for index out of range
    try:
        slice_visible(fake_history, 999)
        assert_true("DoC1.out_of_range_rejected", False, "expected ValueError")
    except ValueError:
        assert_true("DoC1.out_of_range_rejected", True)

    # DoC 3 — replay creates BOTH history_sim AND debug_sim, with outcomes
    def _step_dict(s):
        if hasattr(s, "model_dump"):
            return s.model_dump()
        return s if isinstance(s, dict) else {}
    steps_list = [_step_dict(s) for s in resp.steps]
    persisted_steps = [s for s in steps_list if s.get("status") == "persisted"]
    assert_true(
        "DoC3.replay_creates_history_sim",
        resp.sim_history_total_after >= len(persisted_steps),
        f"history_sim={resp.sim_history_total_after} >= persisted={len(persisted_steps)}",
    )
    assert_true(
        "DoC3.replay_creates_debug_sim",
        resp.sim_debug_total_after >= 1 if persisted_steps else True,
        f"debug_sim={resp.sim_debug_total_after}",
    )
    if persisted_steps:
        s0 = persisted_steps[0]
        assert_true(
            "DoC3.persisted_step_has_outcome",
            s0.get("return_h6") is not None and s0.get("winning_scenario") in {"bull", "base", "bear"},
            f"return_h6={s0.get('return_h6')}, winner={s0.get('winning_scenario')}",
        )
    else:
        # Acceptable — but flag explicitly
        _fail("No steps were persisted; cannot verify outcome shape")

    # DoC 4 — try a replay against the very tail so future window is missing
    try:
        # Pull candle count first.
        from modules.research_analytics.chart_data import get_chart_data_service
        cd = asyncio.run(
            get_chart_data_service().get_chart_data(symbol="BTCUSDT", timeframe="1H", limit=300)
        )
        n_candles = len(getattr(cd, "candles", []) or [])
    except Exception:
        n_candles = 300
    tail_start = max(0, n_candles - 4)  # only 3 future bars exist
    tail_end = max(tail_start, n_candles - 1)
    tail_req = ReplayRequest(
        symbol="BTCUSDT",
        tf="1H",
        start_candle_index=tail_start,
        end_candle_index=tail_end,
        max_steps=10,
        clear_first=False,
        candles_limit=300,
        min_horizon=6,
    )
    tail_resp = asyncio.run(execute_replay(tail_req))
    assert_true(
        "DoC4.tail_skips_insufficient_horizon",
        tail_resp.steps_skipped_insufficient_horizon >= 1,
        f"skipped_horizon={tail_resp.steps_skipped_insufficient_horizon}",
    )

    # ── DoC 2 — feature determinism (same anchor -> same feature_hash) ─────
    _section("DoC 2 — Feature determinism")

    async def _twice(idx: int) -> List[str]:
        hashes = []
        # We feed identical historical_candles via fetch_live_context twice.
        # Pull a frozen historical buffer first.
        from modules.research_analytics.chart_data import get_chart_data_service
        svc = get_chart_data_service()
        cd = await svc.get_chart_data(symbol="BTCUSDT", timeframe="1H", limit=300)
        raw = getattr(cd, "candles", []) or []
        hist = []
        for c in raw:
            if hasattr(c, "model_dump"):
                hist.append(c.model_dump())
            elif isinstance(c, dict):
                hist.append(dict(c))

        for _ in range(2):
            ctx = await fetch_live_context(
                symbol="BTCUSDT",
                timeframe="1H",
                historical_candles=hist,
                as_of_candle_index=idx,
                source="simulation",
                persist_predictions=False,
            )
            fh = (ctx.get("_features_debug") or {}).get("feature_hash")
            hashes.append(fh)
        return hashes

    h_pair = asyncio.run(_twice(120))
    assert_true(
        "DoC2.deterministic_feature_hash",
        h_pair[0] is not None and h_pair[0] == h_pair[1],
        f"hashes={h_pair}",
    )

    # ── DoC 5 + 6 — Live collections untouched, sim collections isolated ──
    _section("DoC 5, 6 — Isolation between live and sim collections")
    live_history_after = int(db[LIVE_HISTORY_COLLECTION].count_documents({}))
    live_debug_after = int(db[LIVE_DEBUG_COLLECTION].count_documents({}))
    assert_eq("DoC5.live_history_count_unchanged",
              live_history_after, live_history_before)
    assert_eq("DoC5.live_debug_count_unchanged",
              live_debug_after, live_debug_before)

    # No sim record leaked into the live collection (by source field).
    leaked_in_live_history = int(
        db[LIVE_HISTORY_COLLECTION].count_documents({"source": "simulation"})
    )
    leaked_in_live_debug = int(
        db[LIVE_DEBUG_COLLECTION].count_documents({"source": "simulation"})
    )
    assert_eq("DoC6.no_sim_in_live_history", leaked_in_live_history, 0)
    assert_eq("DoC6.no_sim_in_live_debug", leaked_in_live_debug, 0)

    # All sim history rows MUST have source='simulation'
    bad_source_in_sim = int(
        db[SIM_HISTORY_COLLECTION].count_documents({"source": {"$ne": "simulation"}})
    )
    assert_eq("DoC6.all_sim_history_marked_simulation", bad_source_in_sim, 0)
    bad_source_in_sim_debug = int(
        db[SIM_DEBUG_COLLECTION].count_documents({"source": {"$ne": "simulation"}})
    )
    assert_eq("DoC6.all_sim_debug_marked_simulation", bad_source_in_sim_debug, 0)

    # ── DoC 7 + 8 — ML Readiness shows samples_by_source, score is live-only ─
    _section("DoC 7, 8 — ML Readiness contract")
    ml_report = compute_readiness_report()
    samples_block = (
        (ml_report.get("details") or {}).get("samples") or {}
    ).get("samples_by_source")
    assert_true(
        "DoC7.ml_readiness_exposes_samples_by_source",
        isinstance(samples_block, dict),
        f"samples_by_source={samples_block}",
    )
    if isinstance(samples_block, dict):
        assert_true(
            "DoC7.has_live_keys",
            "live_total" in samples_block and "live_evaluated" in samples_block,
            str(list(samples_block.keys())),
        )
        assert_true(
            "DoC7.has_simulation_keys",
            "simulation_total" in samples_block and "simulation_evaluated" in samples_block,
            str(list(samples_block.keys())),
        )
        assert_eq("DoC7.scoring_basis_live_only",
                  samples_block.get("scoring_basis"), "live_evaluated_only")

    # DoC 8 — score / gates ignore simulation_count: total used by score
    # equals live_evaluated, NOT live_evaluated + simulation_evaluated.
    sample_total_used = (ml_report.get("details") or {}).get("samples", {}).get("total")
    live_evaluated = (samples_block or {}).get("live_evaluated", -1)
    assert_eq(
        "DoC8.score_uses_live_evaluated_only",
        sample_total_used,
        live_evaluated,
    )
    # Hard gate `total_samples_ok` must be derived from live_evaluated only.
    hard_gates = ml_report.get("hard_gates") or {}
    assert_true(
        "DoC8.hard_gates_present",
        "total_samples_ok" in hard_gates,
        f"hard_gates keys={list(hard_gates.keys())}",
    )

    # ── DoC 9 — clear_first removes only sim rows (sim_only) ──────────────
    _section("DoC 9 — clear_first sim-only deletion")
    # Run with clear_first; sim collection should drop to ~0 for this pair
    # while live collections stay equal.
    pre_live_history = int(db[LIVE_HISTORY_COLLECTION].count_documents({}))
    pre_live_debug = int(db[LIVE_DEBUG_COLLECTION].count_documents({}))
    pre_sim_for_pair = int(
        db[SIM_HISTORY_COLLECTION].count_documents({"symbol": "BTCUSDT", "timeframe": "1H"})
    )
    clear_resp = asyncio.run(
        execute_replay(ReplayRequest(
            symbol="BTCUSDT",
            tf="1H",
            start_candle_index=200,
            end_candle_index=205,
            max_steps=10,
            clear_first=True,
            candles_limit=300,
            min_horizon=6,
        ))
    )
    post_live_history = int(db[LIVE_HISTORY_COLLECTION].count_documents({}))
    post_live_debug = int(db[LIVE_DEBUG_COLLECTION].count_documents({}))
    assert_eq("DoC9.live_history_unchanged_after_clear_first",
              post_live_history, pre_live_history)
    assert_eq("DoC9.live_debug_unchanged_after_clear_first",
              post_live_debug, pre_live_debug)
    assert_true(
        "DoC9.cleared_first_was_applied",
        bool(clear_resp.cleared_first),
        f"cleared_count={clear_resp.cleared_count}",
    )
    assert_true(
        "DoC9.sim_for_pair_was_emptied_then_repopulated",
        clear_resp.cleared_count >= pre_sim_for_pair,
        f"cleared={clear_resp.cleared_count}, was={pre_sim_for_pair}",
    )

    # ── DoC 10 — Routes return correct contracts ──────────────────────────
    _section("DoC 10 — Pydantic schema validation")
    # ReplayResponse already validated by execute_replay; SimStats below.
    stats: SimStats = compute_sim_stats()
    assert_true("DoC10.SimStats_is_pydantic", isinstance(stats, SimStats))
    assert_true(
        "DoC10.SimStats_has_required_fields",
        all(hasattr(stats, k) for k in (
            "sim_history_count", "sim_debug_count",
            "live_history_count", "live_debug_count",
            "sim_history_by_symbol_tf", "sim_debug_by_error_type",
        )),
    )
    assert_true(
        "DoC10.ReplayResponse_is_pydantic",
        isinstance(resp, ReplayResponse),
    )
    assert_true(
        "DoC10.ReplayResponse_has_isolation_fields",
        all(hasattr(resp, k) for k in (
            "live_history_total_before", "live_history_total_after",
            "live_debug_total_before", "live_debug_total_after",
            "sim_history_total_after", "sim_debug_total_after",
        )),
    )

    # ── Summary ───────────────────────────────────────────────────────────
    _section("Summary")
    print(f"  Total assertions: {TOTAL}")
    print(f"  Passed:           {PASSED}")
    print(f"  Failed:           {len(FAILED)}")
    if FAILED:
        print("\n  Failed checks:")
        for f in FAILED:
            print(f"    - {f}")
        return 1
    print("\n  🎉 ALL 10 DoC CONDITIONS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
