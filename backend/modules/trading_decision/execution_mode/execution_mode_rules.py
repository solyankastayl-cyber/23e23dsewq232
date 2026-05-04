"""
PHASE 14.6 — Execution Mode Rules
==================================
Rules and thresholds for execution mode decisions.
"""

# ══════════════════════════════════════════════════════════════
# BLOCKED ACTIONS (result in NONE)
# ══════════════════════════════════════════════════════════════

BLOCKED_ACTIONS = ["BLOCK", "WAIT", "REVERSE_CANDIDATE"]


# ══════════════════════════════════════════════════════════════
# AGGRESSIVE THRESHOLDS
# ══════════════════════════════════════════════════════════════

AGGRESSIVE_RULES = {
    "min_confidence": 0.7,
    "max_conflict_ratio": 0.25,
    "max_squeeze_probability": 0.35,
    "allowed_volatility": ["LOW", "NORMAL"],
    "min_size_buckets": ["NORMAL", "LARGE"],
}


# ══════════════════════════════════════════════════════════════
# NORMAL THRESHOLDS
# ══════════════════════════════════════════════════════════════

NORMAL_RULES = {
    "min_confidence": 0.5,
    "max_conflict_ratio": 0.4,
    "max_squeeze_probability": 0.45,
    "allowed_volatility": ["LOW", "NORMAL", "HIGH"],
}


# ══════════════════════════════════════════════════════════════
# PASSIVE THRESHOLDS
# ══════════════════════════════════════════════════════════════

PASSIVE_RULES = {
    "conflict_ratio_min": 0.3,
    "allowed_actions": ["ALLOW", "ALLOW_REDUCED"],
}


# ══════════════════════════════════════════════════════════════
# PARTIAL ENTRY THRESHOLDS
# ══════════════════════════════════════════════════════════════

PARTIAL_ENTRY_RULES = {
    "squeeze_probability_min": 0.5,
    "conflict_ratio_min": 0.4,
    "min_size_buckets": ["SMALL", "NORMAL", "LARGE"],
    "partial_ratio_range": {"min": 0.3, "max": 0.6},
}


# ══════════════════════════════════════════════════════════════
# DELAYED THRESHOLDS
# ══════════════════════════════════════════════════════════════

DELAYED_RULES = {
    "hostile_volatility": ["EXPANDING"],
    "hostile_states": [
        "CHOP_CONFLICTED",
        "UNDEFINED", 
        "BEARISH_HIGH_VOL_SQUEEZE",
        "PANIC",
        "BEARISH_CAPITULATION",
    ],
    "max_confidence": 0.55,
}


# ══════════════════════════════════════════════════════════════
# URGENCY WEIGHTS
# ══════════════════════════════════════════════════════════════

URGENCY_WEIGHTS = {
    "confidence": 0.35,
    "agreement": 0.25,  # TA + Exchange alignment
    "trend_strength": 0.20,
    "timing": 0.20,  # How good is current timing
}

URGENCY_PENALTIES = {
    "high_volatility": 0.15,
    "high_conflict": 0.12,
    "squeeze_risk": 0.10,
    "hostile_market": 0.08,
}

URGENCY_BONUSES = {
    "strong_agreement": 0.12,
    "low_volatility": 0.08,
    "breakout_state": 0.10,
}


# ══════════════════════════════════════════════════════════════
# SLIPPAGE TOLERANCE
# ══════════════════════════════════════════════════════════════

SLIPPAGE_TOLERANCE = {
    "AGGRESSIVE": {"min": 0.50, "max": 1.00},
    "NORMAL": {"min": 0.25, "max": 0.50},
    "PASSIVE": {"min": 0.10, "max": 0.25},
    "PARTIAL_ENTRY": {"min": 0.15, "max": 0.35},
    "DELAYED": {"value": 0.0},
    "NONE": {"value": 0.0},
}


# ══════════════════════════════════════════════════════════════
# ENTRY STYLE MAPPING
# ══════════════════════════════════════════════════════════════

ENTRY_STYLE_MAP = {
    "AGGRESSIVE": "MARKET",
    "NORMAL": "LIMIT",
    "PASSIVE": "LIMIT",
    "PARTIAL_ENTRY": "STAGED",
    "DELAYED": "WAIT",
    "NONE": "WAIT",
}
