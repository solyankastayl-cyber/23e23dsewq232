"""
Engine Interaction Layer
========================

A pure interpretation layer that sits **on top of** the 5 engines
(structure / pattern / momentum / level_zone / volatility) and reads
their already-produced biases & raw flags to extract higher-order
market interpretation:

    pullback / trend_continuation / early_reversal / rejection /
    breakout / fake_breakout / compression

Strict architectural rules (locked):
-----------------------------------
* This module DOES NOT touch:
    - engines (structure/pattern/momentum/level_zone/volatility)
    - aggregator
    - conflict resolver
    - scenarios
    - typed contracts
* This module DOES NOT add weights to aggregator confidence.
* This module DOES NOT mutate any engine output.
* This module is invoked AFTER aggregator builds the context. It only
  READS the produced TAPredictionContext.
* No randomness. No ML. Deterministic, rule-based.
* If no rule matches -> return None. No fake fallback.

Author: Step 5 (TA Prediction Intelligence v1)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Public output contract
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class InteractionSignal:
    """Higher-order interpretation of how engines interact."""
    type: str                                    # canonical interaction id
    confidence: float                            # 0..1
    description: str                             # human-readable summary
    implications: List[str] = field(default_factory=list)
    dominant_factors: List[str] = field(default_factory=list)
    direction: Optional[str] = None              # bullish | bearish | neutral | None
    raw_inputs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Internal input contract (decoupled from engines)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class InteractionInput:
    structure_bias: Optional[str] = None     # bullish | bearish | neutral | None
    momentum_bias: Optional[str] = None
    pattern_bias: Optional[str] = None
    level_context: Optional[str] = None      # support | resistance | None
    volatility_state: Optional[str] = None   # compression | expansion | normal | None
    momentum_divergence: Optional[str] = None  # bullish | bearish | None
    structure_phase: Optional[str] = None    # impulse | correction | range | None
    # numeric assists (for confidence shaping, never required)
    structure_confidence: float = 0.0
    momentum_confidence: float = 0.0
    pattern_confidence: float = 0.0
    level_confidence: float = 0.0
    volatility_confidence: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _norm_bias(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("bullish", "long", "up"):
        return "bullish"
    if s in ("bearish", "short", "down"):
        return "bearish"
    if s in ("neutral", "flat", "none", ""):
        return "neutral"
    return None


def _clip01(x: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def _avg(*xs: float) -> float:
    vals = [v for v in xs if v is not None]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


# ─────────────────────────────────────────────────────────────────────────────
# Core ruleset
# ─────────────────────────────────────────────────────────────────────────────
#
# Order matters — the most specific / highest-information rules first.
# Every rule is monotonic (always returns the same answer for the same input).
#
# Confidence is built from a small fixed prior (rule strength) + a modest
# bonus from the underlying engines' own confidences. Capped at 0.95.
# ─────────────────────────────────────────────────────────────────────────────


def _bonus_from(*engine_confs: float) -> float:
    """Modest data-quality bonus: up to +0.15."""
    return 0.15 * _clip01(_avg(*engine_confs))


def resolve_interaction(inp: InteractionInput) -> Optional[InteractionSignal]:
    sb = _norm_bias(inp.structure_bias)
    mb = _norm_bias(inp.momentum_bias)
    pb = _norm_bias(inp.pattern_bias)
    lc = (inp.level_context or "").lower() or None
    vs = (inp.volatility_state or "").lower() or None
    div = _norm_bias(inp.momentum_divergence)
    raw_inputs = {
        "structure_bias": sb,
        "momentum_bias": mb,
        "pattern_bias": pb,
        "level_context": lc,
        "volatility_state": vs,
        "momentum_divergence": div,
        "structure_phase": inp.structure_phase,
    }

    # ── 1. EARLY REVERSAL (divergence inside opposing structure) ──
    # Place BEFORE pullback so divergence-driven warnings win.
    if div == "bullish" and sb == "bearish":
        return InteractionSignal(
            type="early_reversal",
            direction="bullish",
            confidence=min(0.95, 0.55 + _bonus_from(inp.momentum_confidence, inp.structure_confidence)),
            description="Bullish momentum divergence inside bearish structure",
            implications=[
                "downtrend may be exhausting",
                "possible reversal setup forming",
                "wait for structure shift confirmation (BOS / CHoCH)",
            ],
            dominant_factors=["momentum", "structure"],
            raw_inputs=raw_inputs,
        )
    if div == "bearish" and sb == "bullish":
        return InteractionSignal(
            type="early_reversal",
            direction="bearish",
            confidence=min(0.95, 0.55 + _bonus_from(inp.momentum_confidence, inp.structure_confidence)),
            description="Bearish momentum divergence inside bullish structure",
            implications=[
                "uptrend exhaustion risk",
                "possible top formation",
                "watch for lower-high break",
            ],
            dominant_factors=["momentum", "structure"],
            raw_inputs=raw_inputs,
        )

    # ── 2. FAKE BREAKOUT / TRAP ──
    # Breakout context (level + expansion) but momentum disagrees.
    if (
        lc == "resistance"
        and vs == "expansion"
        and (mb == "bearish" or div == "bearish")
    ):
        return InteractionSignal(
            type="fake_breakout",
            direction="bearish",
            confidence=min(0.95, 0.6 + _bonus_from(inp.level_confidence, inp.volatility_confidence, inp.momentum_confidence)),
            description="Resistance breakout attempt with bearish momentum / divergence — likely trap",
            implications=[
                "breakout lacks momentum confirmation",
                "stop-hunt above resistance possible",
                "expect reversion back into range",
            ],
            dominant_factors=["level_zone", "volatility", "momentum"],
            raw_inputs=raw_inputs,
        )
    if (
        lc == "support"
        and vs == "expansion"
        and (mb == "bullish" or div == "bullish")
    ):
        return InteractionSignal(
            type="fake_breakout",
            direction="bullish",
            confidence=min(0.95, 0.6 + _bonus_from(inp.level_confidence, inp.volatility_confidence, inp.momentum_confidence)),
            description="Support breakdown attempt with bullish momentum / divergence — likely trap",
            implications=[
                "breakdown lacks momentum confirmation",
                "liquidity grab below support possible",
                "expect bounce back into range",
            ],
            dominant_factors=["level_zone", "volatility", "momentum"],
            raw_inputs=raw_inputs,
        )

    # ── 3. BREAKOUT (level + aligned momentum + expansion) ──
    if lc == "resistance" and mb == "bullish" and vs == "expansion":
        return InteractionSignal(
            type="breakout",
            direction="bullish",
            confidence=min(0.95, 0.7 + _bonus_from(inp.level_confidence, inp.momentum_confidence, inp.volatility_confidence)),
            description="Bullish momentum + volatility expansion at resistance",
            implications=[
                "breakout in progress",
                "trend acceleration likely",
                "liquidity above resistance gets swept",
            ],
            dominant_factors=["level_zone", "momentum", "volatility"],
            raw_inputs=raw_inputs,
        )
    if lc == "support" and mb == "bearish" and vs == "expansion":
        return InteractionSignal(
            type="breakout",
            direction="bearish",
            confidence=min(0.95, 0.7 + _bonus_from(inp.level_confidence, inp.momentum_confidence, inp.volatility_confidence)),
            description="Breakdown of support with bearish momentum and volatility expansion",
            implications=[
                "support breakdown confirmed",
                "accelerated downside likely",
                "stop cascade risk",
            ],
            dominant_factors=["level_zone", "momentum", "volatility"],
            raw_inputs=raw_inputs,
        )

    # ── 4. LEVEL REJECTION (level + opposing momentum, no expansion) ──
    if lc == "resistance" and mb == "bearish":
        return InteractionSignal(
            type="rejection",
            direction="bearish",
            confidence=min(0.95, 0.6 + _bonus_from(inp.level_confidence, inp.momentum_confidence)),
            description="Bearish reaction at resistance",
            implications=[
                "rejection forming at supply",
                "downside move into range likely",
                "watch for lower-high confirmation",
            ],
            dominant_factors=["level_zone", "momentum"],
            raw_inputs=raw_inputs,
        )
    if lc == "support" and mb == "bullish":
        return InteractionSignal(
            type="rejection",
            direction="bullish",
            confidence=min(0.95, 0.6 + _bonus_from(inp.level_confidence, inp.momentum_confidence)),
            description="Bullish reaction at support",
            implications=[
                "support holding",
                "buyers stepping in",
                "upside bounce setup",
            ],
            dominant_factors=["level_zone", "momentum"],
            raw_inputs=raw_inputs,
        )

    # ── 5. TREND CONTINUATION (structure + momentum aligned, pattern not opposing) ──
    if sb == "bullish" and mb == "bullish" and pb != "bearish":
        return InteractionSignal(
            type="trend_continuation",
            direction="bullish",
            confidence=min(0.95, 0.75 + _bonus_from(inp.structure_confidence, inp.momentum_confidence)),
            description="Aligned bullish structure and momentum",
            implications=[
                "trend continuation likely",
                "pullbacks tend to be shallow",
                "momentum-driven leg in progress",
            ],
            dominant_factors=["structure", "momentum"],
            raw_inputs=raw_inputs,
        )
    if sb == "bearish" and mb == "bearish" and pb != "bullish":
        return InteractionSignal(
            type="trend_continuation",
            direction="bearish",
            confidence=min(0.95, 0.75 + _bonus_from(inp.structure_confidence, inp.momentum_confidence)),
            description="Aligned bearish structure and momentum",
            implications=[
                "downtrend continuation likely",
                "weak bounces expected",
                "sell pressure dominant",
            ],
            dominant_factors=["structure", "momentum"],
            raw_inputs=raw_inputs,
        )

    # ── 6. PULLBACK (structure vs momentum disagreement, NOT divergence) ──
    if sb == "bullish" and mb == "bearish":
        return InteractionSignal(
            type="pullback",
            direction="bullish",
            confidence=min(0.95, 0.65 + _bonus_from(inp.structure_confidence, inp.momentum_confidence)),
            description="Bullish structure with bearish momentum — pullback within uptrend",
            implications=[
                "uptrend intact",
                "short-term downside likely",
                "potential buy-the-dip zone forming",
            ],
            dominant_factors=["structure", "momentum"],
            raw_inputs=raw_inputs,
        )
    if sb == "bearish" and mb == "bullish":
        return InteractionSignal(
            type="pullback",
            direction="bearish",
            confidence=min(0.95, 0.65 + _bonus_from(inp.structure_confidence, inp.momentum_confidence)),
            description="Bearish structure with bullish momentum — pullback within downtrend",
            implications=[
                "downtrend intact",
                "short-term upside likely",
                "potential short re-entry zone",
            ],
            dominant_factors=["structure", "momentum"],
            raw_inputs=raw_inputs,
        )

    # ── 7. PRE-BREAKOUT COMPRESSION (range + low volatility) ──
    if vs == "compression" and (sb == "neutral" or inp.structure_phase == "range"):
        return InteractionSignal(
            type="compression",
            direction=None,
            confidence=min(0.95, 0.55 + _bonus_from(inp.volatility_confidence)),
            description="Volatility compression inside range — pre-breakout coil",
            implications=[
                "range tightening",
                "energy building up",
                "directional breakout pending",
            ],
            dominant_factors=["volatility", "structure"],
            raw_inputs=raw_inputs,
        )

    # ── 8. EXPANSION WITHOUT DIRECTIONAL CONTEXT ──
    if vs == "expansion" and lc is None and sb in (None, "neutral"):
        return InteractionSignal(
            type="expansion_chaos",
            direction=None,
            confidence=0.45,
            description="Volatility expansion without clear structure or level context",
            implications=[
                "directional bias unclear",
                "wait for structure to develop",
                "elevated noise / risk",
            ],
            dominant_factors=["volatility"],
            raw_inputs=raw_inputs,
        )

    # No rule matched — honest None.
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Adapter: TAPredictionContext (or its dict form) -> InteractionInput
# Reads only what the aggregator already produced.
# ─────────────────────────────────────────────────────────────────────────────


def _engine(contributions: List[Any], name: str) -> Optional[Dict[str, Any]]:
    """Find an engine contribution by name. Works on dicts or dataclasses."""
    for c in contributions or []:
        if isinstance(c, dict):
            if str(c.get("engine", "")).lower() == name:
                return c
        else:
            if getattr(c, "engine", None) == name:
                # dataclass case
                try:
                    return c.to_dict()  # EngineContribution.to_dict
                except AttributeError:
                    try:
                        return asdict(c)
                    except TypeError:
                        return {
                            "engine": name,
                            "bias": getattr(c, "bias", None),
                            "confidence": getattr(c, "confidence", 0.0),
                            "raw": getattr(c, "raw", {}) or {},
                        }
    return None


def _bias_of(engine_dict: Optional[Dict[str, Any]]) -> Optional[str]:
    if not engine_dict:
        return None
    return _norm_bias(engine_dict.get("bias"))


def _conf_of(engine_dict: Optional[Dict[str, Any]]) -> float:
    if not engine_dict:
        return 0.0
    return _clip01(engine_dict.get("confidence") or 0.0)


def build_interaction_from_context(ctx_or_dict: Any) -> Optional[InteractionSignal]:
    """
    Read-only consumer of aggregator output.

    Accepts either:
      * a `TAPredictionContext` instance (dataclass with .contributions), or
      * a plain dict (the .to_dict() form, which is what live_adapter uses).

    Returns InteractionSignal or None. Never raises on bad shape — returns None.
    """
    if ctx_or_dict is None:
        return None

    # Normalise to dict-shape access.
    if isinstance(ctx_or_dict, dict):
        contributions = ctx_or_dict.get("contributions") or []
    else:
        contributions = getattr(ctx_or_dict, "contributions", None) or []

    structure = _engine(contributions, "structure")
    momentum = _engine(contributions, "momentum")
    pattern = _engine(contributions, "pattern")
    level_zone = _engine(contributions, "level_zone")
    volatility = _engine(contributions, "volatility")

    # level_context: "support"/"resistance" comes from level_zone.raw.side
    level_context: Optional[str] = None
    if level_zone:
        raw_lz = level_zone.get("raw") or {}
        side = raw_lz.get("side")
        if isinstance(side, str) and side.lower() in ("support", "resistance"):
            level_context = side.lower()

    # volatility_state: prefer raw.state ("compression"/"expansion"/"normal"),
    # fall back to compression/expansion booleans.
    vol_state: Optional[str] = None
    if volatility:
        raw_v = volatility.get("raw") or {}
        s = raw_v.get("state")
        if isinstance(s, str) and s.lower() in ("compression", "expansion", "normal"):
            vol_state = s.lower()
        elif raw_v.get("compression"):
            vol_state = "compression"
        elif raw_v.get("expansion"):
            vol_state = "expansion"

    # momentum divergence
    div: Optional[str] = None
    structure_phase: Optional[str] = None
    if momentum:
        raw_m = momentum.get("raw") or {}
        if raw_m.get("bullish_divergence"):
            div = "bullish"
        elif raw_m.get("bearish_divergence"):
            div = "bearish"
    if structure:
        raw_s = structure.get("raw") or {}
        ph = raw_s.get("phase")
        if isinstance(ph, str):
            structure_phase = ph.lower()

    inp = InteractionInput(
        structure_bias=_bias_of(structure),
        momentum_bias=_bias_of(momentum),
        pattern_bias=_bias_of(pattern),
        level_context=level_context,
        volatility_state=vol_state,
        momentum_divergence=div,
        structure_phase=structure_phase,
        structure_confidence=_conf_of(structure),
        momentum_confidence=_conf_of(momentum),
        pattern_confidence=_conf_of(pattern),
        level_confidence=_conf_of(level_zone),
        volatility_confidence=_conf_of(volatility),
    )

    return resolve_interaction(inp)
