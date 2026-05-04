"""
Meta Policy Registry (Pass 4.3)
================================

Per-(symbol, timeframe) policy resolution + universal balanced-regime skip.

Architectural decision (from OOS validation, Pass 4.2 → 4.3):
    Meta is NOT a universal predictor.
    Meta is a SELECTOR / ROUTER between per-asset, per-TF policies.

Two production-validated truths drive this module:

  1. UNIVERSAL FILTER (validated on 9/9 cells in OOS):
        regime == "balanced"  →  SKIP (allocation = 0)
     `balanced` is toxic across every asset/TF tested.

  2. SINGLE OOS-VALIDATED ALPHA:
        ETHUSDT 1H + regime_selfref policy
        PF 1.22, Sharpe 1.35, DD 4.9%, corr +0.072, n=431, overheated n=34/PF 2.57
     Everything else falls back to baseline (no fancy overrides).

This file is the single source of truth for "which policy applies to which
market, and how much to cap exposure". No fabricated edges, no universal
overrides, no hidden defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
# POLICY DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MetaPolicy:
    """
    A policy describes: which allocation map to use, whether to flip direction
    in overheated regime, whether to apply self-reference penalty, and a
    hard exposure cap.

    All fields are explicit — no implicit defaults that could leak.
    """
    name: str
    allocation_map: str           # "baseline" | "calibrated" | "regime_aware"
    flip_overheated: bool         # True ⇒ overheated regime trades INVERTED direction
    self_reference_penalty: float # 0.0 = none, 0.85 = 15% honest downgrade
    max_allocation: float         # hard cap (0..1) — cannot be exceeded
    notes: str = ""


# Validated policies (OOS-tested or honest baseline only)
POLICIES: Dict[str, MetaPolicy] = {
    # Default — same as Meta Pass 4 vanilla.
    "baseline": MetaPolicy(
        name="baseline",
        allocation_map="baseline",
        flip_overheated=False,
        self_reference_penalty=0.0,
        max_allocation=1.0,
        notes="Pass 4 vanilla. No regime overrides. Default for any (sym, tf) "
              "without OOS-validated edge.",
    ),
    # ETH 1H — only OOS-validated configuration. Capped at 0.25 per user spec.
    "regime_selfref": MetaPolicy(
        name="regime_selfref",
        allocation_map="regime_aware",
        flip_overheated=True,
        self_reference_penalty=0.85,
        max_allocation=0.25,
        notes="OOS-validated ONLY for (ETHUSDT, 1H). PF 1.22 / Sharpe 1.35 / "
              "DD 4.9% / corr +0.072 on 1500c. Overheated n=34 / PF 2.57.",
    ),
    # Reserved name for future per-asset extensions; same as baseline now.
    "calibrated": MetaPolicy(
        name="calibrated",
        allocation_map="calibrated",
        flip_overheated=False,
        self_reference_penalty=0.0,
        max_allocation=0.5,
        notes="Pass 4.1 bucket-based filter. Used as backup option; not "
              "production-blessed without per-asset validation.",
    ),
}


# ════════════════════════════════════════════════════════════════════════════
# PER-(symbol, tf[, market_regime]) MAPPING
# ════════════════════════════════════════════════════════════════════════════
#
# Phase 6 / P0 extension:
# The registry now supports an OPTIONAL third dimension `market_regime`
# (one of the regime_detector labels: trend / range / compression /
# high_volatility). It lets us route the SAME (sym, tf) to different
# policies depending on the live market regime.
#
# Lookup ladder used by `resolve_policy()`:
#   1. (SYMBOL, TF, MARKET_REGIME)         — most specific
#   2. (SYMBOL, TF, "*")                   — explicit catch-all per pair
#   3. (SYMBOL, TF)                        — legacy 2-tuple (back-compat)
#   4. "baseline"                          — global default
#
# By default (Phase 6 / P0) we DO NOT add any (sym, tf, regime) overrides:
# the user spec says "сначала можно просто логировать market_regime, не менять
# policy". This module is wired to support overrides the moment we're ready.

# Legacy 2-tuple registry (keeps perfect parity with Pass 4.3 behaviour).
_REGISTRY_2: Dict[Tuple[str, str], str] = {
    # Only one OOS-validated entry. Everything else = baseline.
    ("ETHUSDT", "1H"): "regime_selfref",
}

# Optional per-(sym, tf, market_regime) overrides. Empty in P0 by design.
_REGISTRY_3: Dict[Tuple[str, str, str], str] = {}


def resolve_policy(
    symbol: str,
    timeframe: str,
    market_regime: Optional[str] = None,
) -> MetaPolicy:
    """
    Look up the policy for (symbol, timeframe[, market_regime]).

    Falls back gracefully through the ladder. Returns the baseline policy
    when no match is found. Honest default: NO silent universal override.

    `market_regime` is OPTIONAL. None / "" / "unknown" are treated as missing
    and the function behaves exactly like the Pass 4.3 2-tuple lookup.
    """
    sym = (symbol or "").upper().strip()
    tf = (timeframe or "").upper().strip()
    mr = (market_regime or "").lower().strip()

    # 1. Most specific: (sym, tf, market_regime)
    if mr and mr not in ("unknown", "none"):
        name = _REGISTRY_3.get((sym, tf, mr))
        if name is not None:
            return POLICIES[name]
        # 2. Explicit catch-all per pair
        name = _REGISTRY_3.get((sym, tf, "*"))
        if name is not None:
            return POLICIES[name]

    # 3. Legacy 2-tuple
    name = _REGISTRY_2.get((sym, tf), "baseline")
    return POLICIES[name]


def list_policies() -> Dict[str, Any]:
    """
    Snapshot of registry for transparency / API exposure.
    """
    return {
        "registry": [
            {"symbol": k[0], "timeframe": k[1], "policy": v}
            for k, v in _REGISTRY_2.items()
        ],
        "registry_with_regime": [
            {"symbol": k[0], "timeframe": k[1], "market_regime": k[2], "policy": v}
            for k, v in _REGISTRY_3.items()
        ],
        "default": "baseline",
        "available_policies": {
            name: {
                "allocation_map": p.allocation_map,
                "flip_overheated": p.flip_overheated,
                "self_reference_penalty": p.self_reference_penalty,
                "max_allocation": p.max_allocation,
                "notes": p.notes,
            }
            for name, p in POLICIES.items()
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# REGIME DERIVATION  (score-band → market regime label)
# ════════════════════════════════════════════════════════════════════════════
#
# OOS-validated bands (Pass 4.2 / 1500c × 9 cells):
#     score < 0.50          → "uncertain"   (low edge, stay light)
#     0.50 ≤ score < 0.70   → "balanced"    (TOXIC — universal SKIP)
#     score ≥ 0.70          → "overheated"  (mean-reversion edge possible)
#
# This is the SINGLE place that turns a numeric score into a regime label.
# Everything downstream (apply_policy / should_skip / shadow logger) reads
# the same regime — no duplicated definitions, no silent disagreements.

def derive_regime(score: Optional[float]) -> str:
    if score is None:
        return "uncertain"
    s = max(0.0, min(1.0, float(score)))
    if s < 0.50:
        return "uncertain"
    if s < 0.70:
        return "balanced"
    return "overheated"


def is_balanced_regime(score: Optional[float]) -> bool:
    """Back-compat helper. True iff `score` falls in the toxic balanced band."""
    return derive_regime(score) == "balanced"


# ════════════════════════════════════════════════════════════════════════════
# UNIVERSAL FILTER (validated on 9/9 OOS cells)
# ════════════════════════════════════════════════════════════════════════════
#
# Returns (skip: bool, reason: str). Reason is empty when not skipping.
# Order of checks is intentional and ladder-shaped (LOW > no-score > balanced)
# so the produced reason is the FIRST honest cause, not a generic message.

def should_skip(
    regime: Optional[str],
    score: Optional[float],
    quality: Optional[str],
) -> Tuple[bool, str]:
    q = (quality or "").upper()
    if q == "LOW":
        return True, "quality=LOW"
    if score is None or float(score) <= 0.0:
        return True, "strategy_score=0 (no edge)"
    if (regime or "").lower() == "balanced":
        return True, "regime=balanced (universal toxic filter)"
    return False, ""


# ════════════════════════════════════════════════════════════════════════════
# POLICY APPLICATION  (pure, side-effect free, never mutates input)
# ════════════════════════════════════════════════════════════════════════════
#
# IMPORTANT: this layer SITS ON TOP of build_meta_decision().
# It MUST NOT be inlined into the core engine — Meta = pure math, Policy = overlay.
# The function returns a new dict (input is not mutated).

def _flip_bias(bias: Optional[str]) -> Optional[str]:
    if bias == "bullish":
        return "bearish"
    if bias == "bearish":
        return "bullish"
    return bias  # neutral / None / unknown — leave as-is


def apply_policy(
    decision: Dict[str, Any],
    policy: MetaPolicy,
) -> Dict[str, Any]:
    """
    Transform a base meta decision according to the resolved policy.

    Effects (in order):
      1. Ensure `regime` is set (derived from strategy_score if missing).
      2. If policy.flip_overheated AND regime=="overheated" → invert final_bias.
      3. If policy.self_reference_penalty AND regime=="overheated"
         → allocation *= self_reference_penalty   (honest down-weight, not zero).
      4. Hard cap: allocation = min(allocation, policy.max_allocation).
      5. Re-derive should_trade after the transformation.
      6. Stamp `policy`, `policy_max_allocation`, `regime` for transparency.

    Notes:
      * `should_skip` is NOT called here — that universal filter is
        applied AFTER apply_policy by the caller (see meta_routes).
      * No mutation of the input `decision`.
    """
    out = dict(decision)  # shallow copy is enough — fields are scalars/dicts
    score = float(out.get("strategy_score") or 0.0)
    alloc = float(out.get("allocation") or 0.0)
    bias = out.get("final_bias")
    regime = out.get("regime") or derive_regime(score)
    out["regime"] = regime

    # 2. Direction flip (regime_selfref policy on overheated state)
    if policy.flip_overheated and regime == "overheated":
        bias = _flip_bias(bias)

    # 3. Self-reference penalty (honest down-weight in overheated regime)
    if policy.self_reference_penalty and regime == "overheated":
        alloc *= float(policy.self_reference_penalty)

    # 4. Hard cap
    alloc = min(max(0.0, alloc), float(policy.max_allocation))

    out["final_bias"] = bias
    out["allocation"] = round(alloc, 4)
    out["should_trade"] = alloc > 0.0
    out["policy"] = policy.name
    out["policy_max_allocation"] = policy.max_allocation
    out["policy_flip_overheated"] = policy.flip_overheated
    out["policy_self_reference_penalty"] = policy.self_reference_penalty
    return out
