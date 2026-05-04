"""
Feature Schema v1 — 82 canonical features for ta_prediction_intelligence.

All feature values live in [min, max] after coercion. Missing data is
represented by the default value (0.0 or 0); the builder may attach
engine-level missing flags via `_missing_*` metadata OUTSIDE the vector.

The schema + its hash are stable snapshots — any change REQUIRES bumping
FEATURE_VERSION to v2 and leaving v1 records intact. Dataset builder
splits predictions by `feature_version` to guarantee reproducibility.

Schema type keys:
  * "float" : bounded float
  * "int"   : bounded int (categorical enum OR small count)
  * "flag"  : 0/1 int
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .feature_hash import build_schema_hash

FEATURE_VERSION: str = "v1"
BUILDER_VERSION: str = "1.0.0"
DEFAULT_WINDOW: int = 50  # temporal buffer size

# ────────────────────────────────────────────────────────────────
# Enum codebooks. Keep STRICTLY APPEND-ONLY: new values get new ids, never
# reuse. If a dominant engine name changes, the v1 model sees the old id.
# ────────────────────────────────────────────────────────────────

TREND_PHASE_CODES: Dict[str, int] = {"range": 0, "correction": 1, "impulse": 2}
MOMENTUM_STATE_CODES: Dict[str, int] = {
    "flat": 0, "building": 1, "strong": 2, "exhaust": 3,
}
VOLATILITY_STATE_CODES: Dict[str, int] = {
    "compression": 0, "normal": 1, "expansion": 2, "chaos": 3,
}
ZONE_ACTION_CODES: Dict[str, int] = {
    "none": 0, "bounce": 1, "breakout": 2, "sweep": 3,
}
INTERACTION_TYPE_CODES: Dict[str, int] = {
    "none": 0,
    "pullback": 1,
    "rejection": 2,
    "breakout": 3,
    "fake_breakout": 4,
    "early_reversal": 5,
    "trend_continuation": 6,
    "compression": 7,
    "expansion_chaos": 8,
}
DOMINANT_ENGINE_CODES: Dict[str, int] = {
    "none": 0, "structure": 1, "momentum": 2, "level_zone": 3,
    "pattern": 4, "volatility": 5,
}
PATTERN_TYPE_CODES: Dict[str, int] = {
    "none": 0,
    "triangle": 1,
    "wedge": 2,
    "flag": 3,
    "pennant": 4,
    "head_shoulders": 5,
    "inverse_head_shoulders": 6,
    "double_top": 7,
    "double_bottom": 8,
    "rectangle": 9,
    "channel": 10,
    "cup_handle": 11,
    "rounding_bottom": 12,
    "rounding_top": 13,
    "diamond": 14,
    "broadening": 15,
}

# Transition codebooks: (from_state, to_state) → int. 0 reserved for
# "none / disallowed / noise". Allowed transitions are the only non-zero ids.
TREND_TRANSITIONS_CODED: Dict[tuple, int] = {
    ("range", "weak_trend"): 1,
    ("weak_trend", "strong_trend"): 2,
    ("weak_trend", "range"): 3,
    ("strong_trend", "exhaustion"): 4,
    ("strong_trend", "weak_trend"): 5,
    ("exhaustion", "range"): 6,
    ("exhaustion", "weak_trend"): 7,
}
MOMENTUM_TRANSITIONS_CODED: Dict[tuple, int] = {
    ("flat", "building"): 1,
    ("building", "strong"): 2,
    ("building", "flat"): 3,
    ("strong", "exhaust"): 4,
    ("exhaust", "flat"): 5,
}
VOLATILITY_TRANSITIONS_CODED: Dict[tuple, int] = {
    ("compression", "expansion"): 1,
    ("compression", "normal"): 2,
    ("expansion", "chaos"): 3,
    ("expansion", "normal"): 4,
    ("chaos", "normal"): 5,
    ("normal", "compression"): 6,
    ("normal", "expansion"): 7,
}


def _f(name: str, lo: float, hi: float, default: float = 0.0, block: str = "", doc: str = "") -> Dict[str, Any]:
    return {"name": name, "type": "float", "range": [lo, hi], "default": default, "block": block, "doc": doc}


def _i(name: str, lo: int, hi: int, default: int = 0, block: str = "", doc: str = "") -> Dict[str, Any]:
    return {"name": name, "type": "int", "range": [lo, hi], "default": default, "block": block, "doc": doc}


def _flag(name: str, block: str = "", doc: str = "") -> Dict[str, Any]:
    return {"name": name, "type": "flag", "range": [0, 1], "default": 0, "block": block, "doc": doc}


# Authoritative ordered list (82 entries).
_FEATURES: List[Dict[str, Any]] = [
    # ── 1. STRUCTURE (12) ──
    _f("trend_strength", -1.0, 1.0, 0.0, "structure"),
    _i("trend_age_bars", 0, 500, 0, "structure"),
    _i("hh_count_20", 0, 20, 0, "structure"),
    _i("hl_count_20", 0, 20, 0, "structure"),
    _i("lh_count_20", 0, 20, 0, "structure"),
    _i("ll_count_20", 0, 20, 0, "structure"),
    _i("bos_count_20", 0, 20, 0, "structure"),
    _i("choch_count_20", 0, 20, 0, "structure"),
    _i("trend_phase", 0, 2, 0, "structure", "enum: range=0 correction=1 impulse=2"),
    _f("trend_maturity", 0.0, 1.0, 0.0, "structure"),
    _f("structure_quality", 0.0, 1.0, 0.0, "structure"),
    _f("structure_consistency", 0.0, 1.0, 0.0, "structure"),
    # ── 2. MOMENTUM (13) ──
    _f("macd_hist", -1.0, 1.0, 0.0, "momentum", "ATR-normalised MACD histogram"),
    _f("macd_slope_5", -1.0, 1.0, 0.0, "momentum"),
    _f("macd_acceleration", -1.0, 1.0, 0.0, "momentum"),
    _i("macd_persistence", 0, 50, 0, "momentum", "bars in same sign"),
    _f("rsi", 0.0, 1.0, 0.0, "momentum", "raw RSI/100"),
    _f("rsi_slope_5", -1.0, 1.0, 0.0, "momentum"),
    _flag("rsi_div_bull", "momentum"),
    _flag("rsi_div_bear", "momentum"),
    _i("divergence_age", 0, 50, 0, "momentum"),
    _i("momentum_state", 0, 3, 0, "momentum", "enum flat=0 building=1 strong=2 exhaust=3"),
    _flag("exhaustion_flag", "momentum"),
    _f("momentum_quality", 0.0, 1.0, 0.0, "momentum"),
    _f("momentum_alignment", -1.0, 1.0, 0.0, "momentum", "macd×rsi agreement"),
    # ── 3. LEVEL/ZONE (12) ──
    _f("dist_to_support", 0.0, 0.2, 0.0, "level", "abs pct to nearest support"),
    _f("dist_to_resistance", 0.0, 0.2, 0.0, "level"),
    _i("support_touches", 0, 20, 0, "level"),
    _i("resistance_touches", 0, 20, 0, "level"),
    _i("support_freshness", 0, 500, 0, "level"),
    _i("resistance_freshness", 0, 500, 0, "level"),
    _f("bounce_prob", 0.0, 1.0, 0.0, "level"),
    _f("breakout_prob", 0.0, 1.0, 0.0, "level"),
    _f("sweep_prob", 0.0, 1.0, 0.0, "level"),
    _i("zone_action", 0, 3, 0, "level", "enum none=0 bounce=1 breakout=2 sweep=3"),
    _f("level_strength", 0.0, 1.0, 0.0, "level"),
    _f("level_symmetry", 0.0, 1.0, 0.0, "level"),
    # ── 4. PATTERN (10) ──
    _i("pattern_type", 0, 50, 0, "pattern"),
    _f("pattern_completion", 0.0, 1.0, 0.0, "pattern"),
    _f("pattern_symmetry", 0.0, 1.0, 0.0, "pattern"),
    _flag("pattern_volume_confirm", "pattern"),
    _i("pattern_direction", -1, 1, 0, "pattern"),
    _flag("pattern_conflict_flag", "pattern"),
    _i("pattern_age", 0, 200, 0, "pattern"),
    _f("pattern_quality", 0.0, 1.0, 0.0, "pattern"),
    _f("pattern_reliability", 0.0, 1.0, 0.0, "pattern"),
    _f("pattern_density", 0.0, 1.0, 0.0, "pattern"),
    # ── 5. VOLATILITY (10) ──
    _f("atr_pct", 0.0, 0.2, 0.0, "volatility"),
    _f("atr_slope_5", -1.0, 1.0, 0.0, "volatility"),
    _f("compression_ratio", 0.0, 3.0, 1.0, "volatility", "<1 compression"),
    _flag("expansion_flag", "volatility"),
    _flag("explosive_bar_flag", "volatility"),
    _f("breakout_energy", 0.0, 1.0, 0.0, "volatility"),
    _i("volatility_state", 0, 3, 0, "volatility", "enum compression=0 normal=1 expansion=2 chaos=3"),
    _f("volatility_regime_strength", 0.0, 1.0, 0.0, "volatility"),
    _f("envelope_upper_dist", 0.0, 0.2, 0.0, "volatility"),
    _f("envelope_lower_dist", 0.0, 0.2, 0.0, "volatility"),
    # ── 6. PRICE ACTION (10) ──
    _f("range_pct_10", 0.0, 0.3, 0.0, "price_action"),
    _f("body_ratio_mean_5", 0.0, 1.0, 0.0, "price_action"),
    _f("upper_wick_ratio", 0.0, 1.0, 0.0, "price_action"),
    _f("lower_wick_ratio", 0.0, 1.0, 0.0, "price_action"),
    _f("close_pos_in_range", 0.0, 1.0, 0.5, "price_action"),
    _i("consecutive_up", 0, 20, 0, "price_action"),
    _i("consecutive_down", 0, 20, 0, "price_action"),
    _flag("volatility_cluster_flag", "price_action"),
    _flag("gap_flag", "price_action"),
    _i("inside_bar_streak", 0, 20, 0, "price_action"),
    # ── 7. TRANSITIONS (7) ──
    _i("trend_transition", 0, 20, 0, "transition"),
    _i("momentum_transition", 0, 20, 0, "transition"),
    _i("volatility_transition", 0, 20, 0, "transition"),
    _flag("structure_break_flag", "transition", "BOS/CHoCH within last K bars"),
    _flag("interaction_transition_flag", "transition"),
    _i("regime_transition", 0, 20, 0, "transition"),
    _i("transition_age", 0, 500, 0, "transition"),
    # ── 8. META / CROSS (8) ──
    _f("conflict_ratio", 0.0, 1.0, 0.0, "meta"),
    _i("dominant_engine", 0, 5, 0, "meta", "enum dominant_engine"),
    _i("interaction_type", 0, 20, 0, "meta", "enum interaction_type"),
    _f("interaction_confidence", 0.0, 1.0, 0.0, "meta"),
    _f("structure_momentum_alignment", -1.0, 1.0, 0.0, "meta"),
    _f("structure_level_alignment", -1.0, 1.0, 0.0, "meta"),
    _f("expected_move", 0.0, 0.3, 0.0, "meta"),
    _f("signal_entropy", 0.0, 1.0, 0.0, "meta"),
]

assert len(_FEATURES) == 82, f"feature schema must have 82 entries, got {len(_FEATURES)}"

FEATURE_SCHEMA_V1: Dict[str, Any] = {
    "version": FEATURE_VERSION,
    "builder_version": BUILDER_VERSION,
    "count": len(_FEATURES),
    "features": _FEATURES,
    "enums": {
        "TREND_PHASE_CODES": TREND_PHASE_CODES,
        "MOMENTUM_STATE_CODES": MOMENTUM_STATE_CODES,
        "VOLATILITY_STATE_CODES": VOLATILITY_STATE_CODES,
        "ZONE_ACTION_CODES": ZONE_ACTION_CODES,
        "INTERACTION_TYPE_CODES": INTERACTION_TYPE_CODES,
        "DOMINANT_ENGINE_CODES": DOMINANT_ENGINE_CODES,
        "PATTERN_TYPE_CODES": PATTERN_TYPE_CODES,
        "TREND_TRANSITIONS_CODED": {"|".join(k): v for k, v in TREND_TRANSITIONS_CODED.items()},
        "MOMENTUM_TRANSITIONS_CODED": {"|".join(k): v for k, v in MOMENTUM_TRANSITIONS_CODED.items()},
        "VOLATILITY_TRANSITIONS_CODED": {"|".join(k): v for k, v in VOLATILITY_TRANSITIONS_CODED.items()},
    },
}

FEATURE_SCHEMA_HASH: str = build_schema_hash(FEATURE_SCHEMA_V1)


def get_feature_schema() -> Dict[str, Any]:
    return FEATURE_SCHEMA_V1


def list_feature_names() -> List[str]:
    return [f["name"] for f in _FEATURES]


def _clip(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _coerce_value(raw: Any, spec: Dict[str, Any]) -> Any:
    t = spec["type"]
    lo, hi = spec["range"]
    default = spec["default"]
    try:
        if raw is None:
            return default
        if t == "flag":
            return 1 if bool(raw) else 0
        if t == "int":
            v = int(round(float(raw)))
            if v < lo:
                v = int(lo)
            elif v > hi:
                v = int(hi)
            return v
        if t == "float":
            v = float(raw)
            if v != v:  # NaN
                return float(default)
            v = _clip(v, float(lo), float(hi))
            return round(v, 6)
    except (TypeError, ValueError):
        return default
    return default


def coerce_to_schema(
    raw_features: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return a NEW dict containing exactly the schema's 82 keys in schema order,
    each value clipped/cast to its declared type and range.

    Keys outside the schema are dropped. Missing keys are filled with defaults.
    """
    schema = schema or FEATURE_SCHEMA_V1
    out: Dict[str, Any] = {}
    for spec in schema["features"]:
        out[spec["name"]] = _coerce_value(raw_features.get(spec["name"]), spec)
    return out
