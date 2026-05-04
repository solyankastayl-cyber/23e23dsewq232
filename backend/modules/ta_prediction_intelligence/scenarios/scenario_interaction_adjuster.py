"""
Scenario × Interaction Adjuster (Step 6)
=========================================

Pure post-processing layer that takes:

    1) the scenarios list ALREADY produced by ScenarioBuilder
       (output of aggregator -> {bull, base, bear} dicts with .probability)

    2) the InteractionSignal ALREADY produced by engine_interactions.py

…and returns a NEW scenarios list with probabilities **adjusted** to reflect
the interaction's market interpretation.

ARCHITECTURAL CONTRACT (locked):
--------------------------------
* DOES NOT touch ScenarioBuilder, types.py, aggregator, conflict resolver,
  engines, or InteractionSignal.
* DOES NOT mutate the input scenarios list. Returns NEW dicts.
* Always re-normalises probabilities to sum=1.0.
* Bounded: each delta is scaled by interaction confidence and capped, so
  the adjuster CANNOT flip a strong scenario into a weak one or invent
  probability mass out of nowhere.
* If interaction is None / no rule for type / scenarios empty -> returns
  scenarios unchanged + adjustment=None.
* No randomness. No ML. Deterministic, table-driven.

Adjustment semantics (per interaction type):
-------------------------------------------
    pullback             counter-side short-term ↑, main intact (smaller cut)
    rejection            reject-side ↑ (towards interaction.direction)
    breakout             break-side ↑ strongly
    fake_breakout        opposite of break-side ↑ strongly (trap reversal)
    trend_continuation   trend-side ↑
    early_reversal       new-bias side ↑ (modest, still early)
    compression          base ↑, bull/bear both ↓ (uncertainty + coil)
    expansion_chaos      base ↑ slightly, others slightly down (noise)

NOTE: Author calls "main" the side aligned with `interaction.direction`,
and "opposite" the inverse. For pullback this is intentionally inverted
because pullback main bias = structure (trend), but short-term pressure
goes against it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# Maximum total absolute delta we are allowed to inject before renorm.
# Keeps adjuster honest — it shapes, doesn't invent.
_MAX_TOTAL_DELTA = 0.40

# Bounds applied to each scenario probability before renorm.
_PROB_FLOOR = 0.02
_PROB_CEIL = 0.92


def _clip01(x: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def _direction_to_main_opposite(direction: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if direction == "bullish":
        return "bull", "bear"
    if direction == "bearish":
        return "bear", "bull"
    return None, None


def _build_deltas(
    interaction_type: str,
    direction: Optional[str],
    scale: float,
) -> Optional[Dict[str, float]]:
    """
    Returns delta map {bull, base, bear} -> additive change to apply BEFORE
    renorm. `scale` already contains interaction.confidence. Returns None
    when the rule cannot apply (no direction where required).
    """
    main, opp = _direction_to_main_opposite(direction)
    deltas = {"bull": 0.0, "base": 0.0, "bear": 0.0}

    t = interaction_type

    if t == "trend_continuation":
        if not main:
            return None
        deltas[main] += 0.15 * scale
        deltas[opp] += -0.10 * scale
        deltas["base"] += -0.05 * scale

    elif t == "breakout":
        if not main:
            return None
        deltas[main] += 0.20 * scale
        deltas[opp] += -0.15 * scale
        deltas["base"] += -0.05 * scale

    elif t == "rejection":
        if not main:
            return None
        deltas[main] += 0.12 * scale
        deltas[opp] += -0.08 * scale
        deltas["base"] += -0.04 * scale

    elif t == "fake_breakout":
        # interaction.direction here ALREADY denotes the trap-resolution side
        # (e.g. "bearish" for failed bull breakout). So main = trap side.
        if not main:
            return None
        deltas[main] += 0.18 * scale
        deltas[opp] += -0.13 * scale
        deltas["base"] += -0.05 * scale

    elif t == "early_reversal":
        if not main:
            return None
        # Modest tilt — reversal is still a hypothesis, not a confirmation.
        deltas[main] += 0.10 * scale
        deltas[opp] += -0.07 * scale
        deltas["base"] += -0.03 * scale

    elif t == "pullback":
        # Pullback semantics: structure says `main`, but short-term pressure
        # is against it. We bump the SHORT-TERM-PRESSURE side (= opposite of
        # interaction.direction) and the base scenario, while only mildly
        # cutting `main` (because trend integrity is intact).
        if not main:
            return None
        deltas[main] += -0.05 * scale
        deltas[opp] += 0.10 * scale
        deltas["base"] += 0.05 * scale

    elif t == "compression":
        # No directional bias — base wins, bull/bear both shrink slightly.
        deltas["base"] += 0.10 * scale
        deltas["bull"] += -0.05 * scale
        deltas["bear"] += -0.05 * scale

    elif t == "expansion_chaos":
        # Pure noise → spread out a bit toward base.
        deltas["base"] += 0.06 * scale
        deltas["bull"] += -0.03 * scale
        deltas["bear"] += -0.03 * scale

    else:
        # Unknown type — no-op.
        return None

    return deltas


def _cap_total_delta(deltas: Dict[str, float]) -> Dict[str, float]:
    total_abs = sum(abs(v) for v in deltas.values())
    if total_abs <= _MAX_TOTAL_DELTA or total_abs <= 0:
        return deltas
    factor = _MAX_TOTAL_DELTA / total_abs
    return {k: v * factor for k, v in deltas.items()}


def apply_interaction_adjustment(
    scenarios: List[Dict[str, Any]],
    interaction: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Returns (new_scenarios, adjustment_meta).

    * `new_scenarios` is always a fresh list of fresh dicts (deep enough copy).
    * `adjustment_meta` is None when no adjustment was applied.
    * Each adjusted scenario dict carries:
        - `probability`        : final, renormalised probability (0..1)
        - `original_probability`: the value before adjustment
        - `delta`              : final - original
        - `adjusted`           : True
    * Probability sum stays 1.0 (within float epsilon).
    """
    if not scenarios:
        return [], None

    # Always work on copies — never mutate caller's data.
    base_list: List[Dict[str, Any]] = [dict(s) for s in scenarios]

    # No interaction OR no type -> return originals, but still tag them as
    # not-adjusted so the UI contract is uniform.
    if not interaction or not interaction.get("type"):
        for s in base_list:
            s.setdefault("original_probability", s.get("probability"))
            s.setdefault("delta", 0.0)
            s.setdefault("adjusted", False)
        return base_list, None

    direction = interaction.get("direction")
    conf = _clip01(interaction.get("confidence") or 0.0)
    if conf <= 0.0:
        for s in base_list:
            s.setdefault("original_probability", s.get("probability"))
            s.setdefault("delta", 0.0)
            s.setdefault("adjusted", False)
        return base_list, None

    deltas = _build_deltas(interaction["type"], direction, conf)
    if deltas is None:
        for s in base_list:
            s.setdefault("original_probability", s.get("probability"))
            s.setdefault("delta", 0.0)
            s.setdefault("adjusted", False)
        return base_list, None

    deltas = _cap_total_delta(deltas)

    # Capture originals (by name).
    originals: Dict[str, float] = {}
    for s in base_list:
        name = s.get("name")
        if not name:
            continue
        try:
            originals[name] = float(s.get("probability") or 0.0)
        except (TypeError, ValueError):
            originals[name] = 0.0

    # Apply additive deltas + clamp per-scenario.
    adjusted_raw: Dict[str, float] = {}
    for name, p in originals.items():
        d = deltas.get(name, 0.0)
        v = p + d
        if v < _PROB_FLOOR:
            v = _PROB_FLOOR
        elif v > _PROB_CEIL:
            v = _PROB_CEIL
        adjusted_raw[name] = v

    total = sum(adjusted_raw.values())
    if total <= 0:
        # Defensive — should never happen given _PROB_FLOOR.
        return base_list, None
    adjusted_norm: Dict[str, float] = {k: v / total for k, v in adjusted_raw.items()}

    # Write back into copies + decoration.
    for s in base_list:
        name = s.get("name")
        if name not in originals:
            s.setdefault("original_probability", s.get("probability"))
            s.setdefault("delta", 0.0)
            s.setdefault("adjusted", False)
            continue
        original = originals[name]
        new_p = adjusted_norm.get(name, original)
        s["original_probability"] = round(original, 6)
        s["probability"] = round(new_p, 6)
        s["delta"] = round(new_p - original, 6)
        s["adjusted"] = True

    meta = {
        "applied": True,
        "interaction_type": interaction.get("type"),
        "interaction_direction": direction,
        "interaction_confidence": conf,
        "scale_used": conf,
        "raw_deltas": {k: round(v, 6) for k, v in deltas.items()},
        "max_total_delta": _MAX_TOTAL_DELTA,
        "prob_floor": _PROB_FLOOR,
        "prob_ceil": _PROB_CEIL,
        "explanation": _explain(interaction.get("type"), direction),
    }
    return base_list, meta


def _explain(interaction_type: Optional[str], direction: Optional[str]) -> str:
    side = direction or "neutral"
    table = {
        "trend_continuation": f"Trend-aligned scenario ({side}) reinforced; opposite reduced.",
        "breakout": f"Breakout direction ({side}) reinforced; opposite reduced.",
        "rejection": f"Rejection side ({side}) reinforced; opposite reduced.",
        "fake_breakout": f"Trap reversal ({side}) reinforced; failed-breakout side reduced.",
        "early_reversal": f"Reversal hypothesis ({side}) modestly tilted; main bias still considered.",
        "pullback": "Counter-trend short-term pressure boosted; trend side mildly reduced (intact).",
        "compression": "Base scenario boosted; bull and bear both reduced (coil → uncertainty).",
        "expansion_chaos": "Slight tilt towards base scenario (no clean directional context).",
    }
    return table.get(interaction_type or "", "")
