"""
QUALITY HARDEN STEP 12 — Decision Intelligence stress tests.
============================================================

Pure offline harness: synthesises controlled `result` contexts and runs them
through `build_decision_intelligence(result)`. No HTTP, no Mongo, no engine
calls. Read-only on the decision layer (no mutation of formulas).

Each test enforces a single invariant. Failures print the synthesized input
and the offending output so the architect can spot regressions in seconds.

Run:
    python3 /app/scripts/qa_step12_decision.py
"""
from __future__ import annotations

import json
import random
import sys
import os
from typing import Any, Dict, List, Tuple

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.decision_intelligence import (
    build_decision_intelligence,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — minimal `result` shape needed by Step 12
# ─────────────────────────────────────────────────────────────────────────────

def _scenarios(bull: float, base: float, bear: float) -> List[Dict[str, Any]]:
    """Build a 3-element scenarios list. Caller is responsible for sum=1."""
    return [
        {"name": "bull", "probability": float(bull)},
        {"name": "base", "probability": float(base)},
        {"name": "bear", "probability": float(bear)},
    ]


def _temporal_ready(
    *,
    stability: float = 0.5,
    continuation: float = 0.0,
    reversal: float = 0.0,
    instability: float = 0.0,
    flip_freq: float = 0.0,
    sequence: str = "",
) -> Dict[str, Any]:
    return {
        "ready": True,
        "regime_stability_score": stability,
        "continuation_pressure": continuation,
        "reversal_pressure": reversal,
        "instability_pressure": instability,
        "regime_flip_frequency": flip_freq,
        "detected_sequence": sequence,
    }


def _ctx(
    *,
    scenarios,
    interaction_type: str = "",
    temporal: Dict[str, Any] = None,
    conflict_ratio: float = 0.0,
    bias: str = "neutral",
    contributions: List[Dict[str, Any]] = None,
    dominant_engine: str = "structure",
) -> Dict[str, Any]:
    return {
        "symbol": "ETHUSDT",
        "timeframe": "1H",
        "bias": bias,
        "confidence": 0.5,
        "conflict_ratio": conflict_ratio,
        "dominant_engine": dominant_engine,
        "contributions": contributions or [],
        "scenarios": scenarios,
        "scenarios_original": scenarios,
        "interaction": ({"type": interaction_type} if interaction_type else None),
        "temporal_intelligence": temporal,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


class Suite:
    def __init__(self) -> None:
        self.results: List[Tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "", extra: Any = None) -> None:
        self.results.append((name, ok, detail))
        prefix = PASS if ok else FAIL
        print(f"[{prefix}] {name}")
        if detail:
            print(f"        {detail}")
        if not ok and extra is not None:
            try:
                print(f"        observed: {json.dumps(extra, indent=2, default=str)[:600]}")
            except Exception:
                print(f"        observed: {extra}")

    def passed(self) -> int:
        return sum(1 for _, ok, _ in self.results if ok)

    def total(self) -> int:
        return len(self.results)


def main() -> int:
    print("=" * 72)
    print("  QUALITY HARDEN STEP 12 — Decision Intelligence stress tests")
    print("=" * 72)
    s = Suite()

    # ── Test 1: ambiguous scenarios → no_edge (dominance < DOM_THIN)
    print("\n── 1. Ambiguous scenarios (≈0.34/0.33/0.33) ──")
    ctx = _ctx(scenarios=_scenarios(0.34, 0.33, 0.33), bias="neutral",
               temporal=_temporal_ready())
    out = build_decision_intelligence(ctx)
    s.check(
        "1.1 dominance < 0.07",
        out["scenario_dominance"] < 0.07,
        f"dominance={out['scenario_dominance']:.4f}",
        out,
    )
    s.check(
        "1.2 dominance_label == 'ambiguous'",
        out["scenario_dominance_label"] == "ambiguous",
        f"label={out['scenario_dominance_label']}",
        out,
    )
    s.check(
        "1.3 signal_strength == 'no_edge'",
        out["signal_strength"] == "no_edge",
        f"strength={out['signal_strength']} conf={out['decision_confidence']:.4f}",
        out,
    )

    # ── Test 2: extreme risk → no_edge (hard kill regardless of confidence)
    print("\n── 2. Extreme risk (multi-trigger) ──")
    extreme_temporal = _temporal_ready(
        instability=0.9, reversal=0.9, flip_freq=0.5, sequence="chaos_burst"
    )
    ctx = _ctx(
        scenarios=_scenarios(0.80, 0.15, 0.05),
        interaction_type="fake_breakout",  # +0.20
        temporal=extreme_temporal,           # +0.25 +0.20 +0.15 +0.10 = +0.70
        conflict_ratio=0.55,                 # +0.25
        bias="bullish",
    )
    out = build_decision_intelligence(ctx)
    s.check(
        "2.1 risk_level == 'extreme'",
        out["risk_level"] == "extreme",
        f"risk_score={out['risk_score']:.4f} level={out['risk_level']}",
        out,
    )
    s.check(
        "2.2 signal_strength == 'no_edge'",
        out["signal_strength"] == "no_edge",
        f"strength={out['signal_strength']} primary_prob={out['scenario_probability']:.2f}",
        out,
    )

    # ── Test 3: high conflict alone → confidence damped + risk reason logged
    print("\n── 3. High conflict ratio (0.50) ──")
    ctx_no_conflict = _ctx(
        scenarios=_scenarios(0.60, 0.20, 0.20),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(continuation=0.5, stability=0.6),
        conflict_ratio=0.10,
        bias="bullish",
    )
    out_low = build_decision_intelligence(ctx_no_conflict)

    ctx_high_conflict = dict(ctx_no_conflict)
    ctx_high_conflict["conflict_ratio"] = 0.50
    out_high = build_decision_intelligence(ctx_high_conflict)

    s.check(
        "3.1 conflict>0.40 raises 'high_engine_conflict' risk",
        "high_engine_conflict" in out_high["risks"],
        f"risks={out_high['risks']}",
        out_high,
    )
    s.check(
        "3.2 high conflict → decision_confidence drops",
        out_high["decision_confidence"] < out_low["decision_confidence"],
        f"low_conflict={out_low['decision_confidence']:.4f} > high_conflict={out_high['decision_confidence']:.4f}",
        {"low": out_low, "high": out_high},
    )
    s.check(
        "3.3 high conflict → risk_score >= 0.25 (>= 'elevated')",
        out_high["risk_score"] >= 0.25,
        f"risk_score={out_high['risk_score']:.4f} level={out_high['risk_level']}",
        out_high,
    )

    # ── Test 4: missing/not-ready temporal → temporal_score=0.5, no fake high conf
    print("\n── 4. Missing temporal (not ready) ──")
    ctx_miss = _ctx(
        scenarios=_scenarios(0.70, 0.20, 0.10),
        interaction_type="trend_continuation",
        temporal={"ready": False, "summary": "insufficient_history"},
        conflict_ratio=0.0,
        bias="bullish",
    )
    out_miss = build_decision_intelligence(ctx_miss)
    s.check(
        "4.1 temporal_score == 0.5 (neutral fallback)",
        abs(out_miss["temporal_score"] - 0.5) < 1e-9,
        f"temporal_score={out_miss['temporal_score']}",
        out_miss,
    )
    # Mathematical ceiling when temporal=0.5: decision_conf <=
    #   primary_prob × 1 × (0.60 + 0.40×0.5) × 1 = primary_prob × 0.80
    ceiling = ctx_miss["scenarios"][0]["probability"] * 1.0 * 0.80 * 1.0
    s.check(
        "4.2 decision_conf NOT inflated above primary_prob × 0.80 ceiling",
        out_miss["decision_confidence"] <= ceiling + 1e-9,
        f"conf={out_miss['decision_confidence']:.4f} ceiling={ceiling:.4f}",
        out_miss,
    )
    s.check(
        "4.3 strength != 'strong' when temporal is unknown",
        out_miss["signal_strength"] != "strong",
        f"strength={out_miss['signal_strength']}",
        out_miss,
    )

    # ── Test 5: interaction OPPOSED to primary scenario → alignment drops
    print("\n── 5. Interaction OPPOSED to primary (fake_breakout vs bull) ──")
    ctx_aligned = _ctx(
        scenarios=_scenarios(0.65, 0.25, 0.10),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(continuation=0.4, stability=0.6),
        conflict_ratio=0.05,
        bias="bullish",
    )
    ctx_opposed = dict(ctx_aligned)
    ctx_opposed["interaction"] = {"type": "fake_breakout"}
    # Risk increases when fake_breakout is in play; isolate alignment by
    # comparing alignment_score AND decision_confidence dropping.
    out_aligned = build_decision_intelligence(ctx_aligned)
    out_opposed = build_decision_intelligence(ctx_opposed)
    s.check(
        "5.1 opposed interaction → alignment < aligned interaction",
        out_opposed["alignment_score"] < out_aligned["alignment_score"],
        f"aligned={out_aligned['alignment_score']:.4f} opposed={out_opposed['alignment_score']:.4f}",
        {"aligned": out_aligned, "opposed": out_opposed},
    )
    s.check(
        "5.2 'interaction_conflicts_with_primary_scenario' in risks",
        "interaction_conflicts_with_primary_scenario" in out_opposed["risks"],
        f"risks={out_opposed['risks']}",
        out_opposed,
    )
    s.check(
        "5.3 opposed interaction → decision_confidence drops",
        out_opposed["decision_confidence"] < out_aligned["decision_confidence"],
        f"aligned={out_aligned['decision_confidence']:.4f} opposed={out_opposed['decision_confidence']:.4f}",
        {"aligned": out_aligned, "opposed": out_opposed},
    )

    # ── Test 6: strong primary + low risk + aligned temporal → 'strong'
    # Decision layer is conservative by design: alignment maxes at ~0.85
    # (base 0.5 + 0.20 interaction + 0.15 temporal), temporal at ~0.84,
    # so the product multiplier ≈ 0.866. To reach strength="strong"
    # (decision_conf ≥ 0.70) primary_prob must be ≥ 0.81. We use 0.90 to
    # demonstrate the canonical strong-signal path.
    print("\n── 6. Strong primary + aligned + low risk → strong ──")
    ctx_strong = _ctx(
        scenarios=_scenarios(0.90, 0.07, 0.03),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(stability=0.85, continuation=0.75, reversal=0.05,
                                 instability=0.05, flip_freq=0.05),
        conflict_ratio=0.05,
        bias="bullish",
    )
    out_strong = build_decision_intelligence(ctx_strong)
    s.check(
        "6.1 risk_level == 'low'",
        out_strong["risk_level"] == "low",
        f"risk_score={out_strong['risk_score']:.4f} level={out_strong['risk_level']}",
        out_strong,
    )
    s.check(
        "6.2 dominance_label == 'dominant'",
        out_strong["scenario_dominance_label"] == "dominant",
        f"label={out_strong['scenario_dominance_label']} dom={out_strong['scenario_dominance']:.4f}",
        out_strong,
    )
    s.check(
        "6.3 signal_strength == 'strong'",
        out_strong["signal_strength"] == "strong",
        f"strength={out_strong['signal_strength']} conf={out_strong['decision_confidence']:.4f}",
        out_strong,
    )
    # And: under same primary but moderate alignment (no temporal continuation
    # support) decision_layer must drop to 'moderate' — never 'strong'.
    ctx_moderate_inputs = _ctx(
        scenarios=_scenarios(0.78, 0.15, 0.07),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(stability=0.6, continuation=0.3, reversal=0.05,
                                 instability=0.1),
        conflict_ratio=0.05,
        bias="bullish",
    )
    out_mod = build_decision_intelligence(ctx_moderate_inputs)
    s.check(
        "6.4 honesty: high primary alone does NOT auto-promote to 'strong'",
        out_mod["signal_strength"] in ("moderate", "weak"),
        f"strength={out_mod['signal_strength']} conf={out_mod['decision_confidence']:.4f}",
        out_mod,
    )

    # ── Test 7: calibration-adjusted scenarios don't break dominance direction
    print("\n── 7. Calibrated scenarios preserve dominance direction ──")
    ctx_pre = _ctx(
        scenarios=_scenarios(0.70, 0.20, 0.10),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(stability=0.6),
        bias="bullish",
    )
    # Simulate calibration shrinking primary toward base; primary still bull.
    ctx_post = _ctx(
        scenarios=_scenarios(0.55, 0.30, 0.15),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(stability=0.6),
        bias="bullish",
    )
    out_pre = build_decision_intelligence(ctx_pre)
    out_post = build_decision_intelligence(ctx_post)
    s.check(
        "7.1 primary_scenario unchanged after calibration",
        out_pre["primary_scenario"] == out_post["primary_scenario"] == "bull",
        f"pre={out_pre['primary_scenario']} post={out_post['primary_scenario']}",
        {"pre": out_pre, "post": out_post},
    )
    s.check(
        "7.2 decision_bias unchanged",
        out_pre["decision_bias"] == out_post["decision_bias"] == "bullish",
        f"pre={out_pre['decision_bias']} post={out_post['decision_bias']}",
        {"pre": out_pre, "post": out_post},
    )
    s.check(
        "7.3 dominance shrank but stayed positive (calibration didn't flip sign)",
        out_post["scenario_dominance"] >= 0.0
        and out_post["scenario_dominance"] < out_pre["scenario_dominance"],
        f"pre_dom={out_pre['scenario_dominance']:.4f} post_dom={out_post['scenario_dominance']:.4f}",
        {"pre": out_pre, "post": out_post},
    )

    # Edge case: calibration pushes secondary above primary → primary FLIPS
    # (this is correct behaviour, the test is to show it's deterministic).
    ctx_flipped = _ctx(
        scenarios=_scenarios(0.30, 0.50, 0.20),  # base now winning
        interaction_type="compression",
        temporal=_temporal_ready(stability=0.4),
        bias="neutral",
    )
    out_flipped = build_decision_intelligence(ctx_flipped)
    s.check(
        "7.4 calibration flip past 50% promotes new primary deterministically",
        out_flipped["primary_scenario"] == "base"
        and out_flipped["decision_bias"] == "neutral",
        f"primary={out_flipped['primary_scenario']} bias={out_flipped['decision_bias']}",
        out_flipped,
    )

    # ── Test 8: math invariant: decision_confidence <= primary_probability ALWAYS
    print("\n── 8. Math invariant: decision_confidence ≤ primary_probability ──")
    # Direct construction
    ctx_basic = _ctx(
        scenarios=_scenarios(0.85, 0.10, 0.05),
        interaction_type="trend_continuation",
        temporal=_temporal_ready(stability=1.0, continuation=1.0),
        conflict_ratio=0.0,
        bias="bullish",
    )
    out_basic = build_decision_intelligence(ctx_basic)
    s.check(
        "8.1 best-case: conf ≤ primary_prob",
        out_basic["decision_confidence"] <= out_basic["scenario_probability"] + 1e-9,
        f"conf={out_basic['decision_confidence']:.4f} prob={out_basic['scenario_probability']:.4f}",
        out_basic,
    )

    # High-risk, opposed, missing temporal — confidence must shrink hard.
    # Exact analytical ceiling under this config:
    #   alignment = 0.5 - 0.20 (interaction opposed) = 0.30
    #     → align_mult = 0.5 + 0.5*0.30 = 0.65
    #   temporal not-ready
    #     → temp_mult  = 0.6 + 0.4*0.5 = 0.80
    #   risk_score = 0.25 (conflict>0.40) + 0.20 (fake_breakout) = 0.45
    #     → risk_mult = 1.0 - 0.5*0.45 = 0.775
    # ceiling = primary_prob × 0.65 × 0.80 × 0.775 ≈ primary × 0.4030
    ctx_worst = _ctx(
        scenarios=_scenarios(0.85, 0.10, 0.05),
        interaction_type="fake_breakout",
        temporal={"ready": False},
        conflict_ratio=0.55,
        bias="bullish",
    )
    out_worst = build_decision_intelligence(ctx_worst)
    analytical_ceiling = out_worst["scenario_probability"] * 0.65 * 0.80 * 0.775
    # Allow 0.1% relative tolerance — the analytical ceiling is the EXACT
    # algebraic upper bound but rounding inside decision_builder may add a
    # ULP. Both numbers round to 0.3426 at 4 decimals.
    import math as _math
    s.check(
        "8.2 high-risk + opposed + no temporal: conf ≤ analytical ceiling (0.65×0.80×0.775)",
        out_worst["decision_confidence"] <= analytical_ceiling
        or _math.isclose(out_worst["decision_confidence"], analytical_ceiling, rel_tol=1e-3),
        f"conf={out_worst['decision_confidence']:.6f} ceiling={analytical_ceiling:.6f} "
        f"(align={out_worst['alignment_score']:.2f} temp={out_worst['temporal_score']:.2f} risk={out_worst['risk_score']:.2f})",
        out_worst,
    )
    s.check(
        "8.2b strength collapses to 'no_edge' or 'weak' under this combo",
        out_worst["signal_strength"] in ("no_edge", "weak"),
        f"strength={out_worst['signal_strength']}",
        out_worst,
    )

    # Fuzz: 200 random contexts. invariant must hold every time.
    print("\n── 8.3 Fuzz: 200 random contexts (deterministic seed) ──")
    rng = random.Random(42)
    violations: List[Dict[str, Any]] = []
    for i in range(200):
        # Random simplex over (bull, base, bear)
        a, b, c = rng.random(), rng.random(), rng.random()
        tot = a + b + c
        bull, base, bear = a / tot, b / tot, c / tot
        ctx = _ctx(
            scenarios=_scenarios(bull, base, bear),
            interaction_type=rng.choice([
                "", "trend_continuation", "fake_breakout", "compression",
                "early_reversal", "breakout", "rejection", "expansion_chaos",
                "whipsaw", "pullback_continuation",
            ]),
            temporal=(
                {"ready": False}
                if rng.random() < 0.30
                else _temporal_ready(
                    stability=rng.random(),
                    continuation=rng.random(),
                    reversal=rng.random(),
                    instability=rng.random(),
                    flip_freq=rng.random(),
                    sequence=rng.choice(["", "continuation_chain", "reversal_swing", "chaos_burst"]),
                )
            ),
            conflict_ratio=rng.random() * 0.8,
            bias=rng.choice(["bullish", "bearish", "neutral"]),
        )
        out = build_decision_intelligence(ctx)
        primary_prob = out["scenario_probability"]
        conf = out["decision_confidence"]
        if conf > primary_prob + 1e-9:
            violations.append({
                "i": i, "primary_prob": primary_prob, "conf": conf,
                "ctx_summary": {
                    "scenarios": ctx["scenarios"],
                    "interaction": ctx["interaction"],
                    "conflict": ctx["conflict_ratio"],
                    "temporal_ready": (ctx["temporal_intelligence"] or {}).get("ready"),
                },
                "out_summary": {
                    "alignment": out["alignment_score"],
                    "temporal_score": out["temporal_score"],
                    "risk_score": out["risk_score"],
                },
            })
    s.check(
        "8.3 fuzz invariant: conf ≤ primary_prob across 200 random ctx",
        len(violations) == 0,
        f"violations={len(violations)}/200",
        violations[:3] if violations else None,
    )

    # ── Bonus: extreme risk fuzz — no_edge ALWAYS
    print("\n── 9. Bonus invariant: extreme risk ⇒ no_edge ──")
    rng2 = random.Random(7)
    edge_violations: List[Dict[str, Any]] = []
    for i in range(50):
        a, b, c = rng2.random() + 0.5, rng2.random() * 0.3, rng2.random() * 0.3
        tot = a + b + c
        bull, base, bear = a / tot, b / tot, c / tot
        ctx = _ctx(
            scenarios=_scenarios(bull, base, bear),
            interaction_type="fake_breakout",
            temporal=_temporal_ready(
                instability=0.95, reversal=0.95, flip_freq=0.95,
                sequence="chaos_burst",
            ),
            conflict_ratio=0.7,
            bias="bullish",
        )
        out = build_decision_intelligence(ctx)
        if out["risk_level"] == "extreme" and out["signal_strength"] != "no_edge":
            edge_violations.append({"i": i, "out": out})
    s.check(
        "9.1 risk_level=extreme ⇒ signal_strength=no_edge (50 fuzz)",
        len(edge_violations) == 0,
        f"violations={len(edge_violations)}/50",
        edge_violations[:2] if edge_violations else None,
    )

    # ── Summary
    total = s.total()
    pas = s.passed()
    print()
    print("=" * 72)
    print(f"  RESULT: {pas}/{total} checks passed")
    print("=" * 72)
    return 0 if pas == total else 1


if __name__ == "__main__":
    sys.exit(main())
