"""
PHASE 14.5 — Position Sizing Rules
===================================
Rules and thresholds for position sizing adjustments.
"""

# ══════════════════════════════════════════════════════════════
# BASE RISK
# ══════════════════════════════════════════════════════════════

BASE_RISK_PCT = 1.0  # 1.0% base risk


# ══════════════════════════════════════════════════════════════
# RISK MULTIPLIER BY ACTION
# ══════════════════════════════════════════════════════════════

RISK_MULTIPLIER_RANGES = {
    "ALLOW_AGGRESSIVE": {"min": 1.15, "max": 1.30},
    "ALLOW": {"min": 0.85, "max": 1.05},
    "ALLOW_REDUCED": {"min": 0.35, "max": 0.65},
    "BLOCK": {"value": 0.0},
    "WAIT": {"value": 0.0},
    "REVERSE_CANDIDATE": {"value": 0.0},
}


# ══════════════════════════════════════════════════════════════
# VOLATILITY ADJUSTMENT
# ══════════════════════════════════════════════════════════════

VOLATILITY_ADJUSTMENTS = {
    "LOW": 1.05,
    "NORMAL": 1.00,
    "HIGH": 0.80,
    "EXPANDING": 0.65,
}


# ══════════════════════════════════════════════════════════════
# EXCHANGE ADJUSTMENT RULES
# ══════════════════════════════════════════════════════════════

EXCHANGE_ADJUSTMENT_RULES = {
    # Strong confirmation: high confidence + low conflict
    "strong_confirmation": {
        "confidence_min": 0.7,
        "conflict_max": 0.25,
        "adjustment_range": {"min": 1.05, "max": 1.15},
    },
    # Moderate confirmation
    "moderate_confirmation": {
        "confidence_min": 0.5,
        "conflict_max": 0.4,
        "adjustment_range": {"min": 0.95, "max": 1.05},
    },
    # Crowded / conflicted
    "crowded_conflicted": {
        "crowding_risk_min": 0.5,
        "conflict_min": 0.4,
        "adjustment_range": {"min": 0.70, "max": 0.90},
    },
    # Squeeze risk
    "squeeze_risk": {
        "squeeze_probability_min": 0.5,
        "adjustment_range": {"min": 0.60, "max": 0.85},
    },
}


# ══════════════════════════════════════════════════════════════
# MARKET STATE ADJUSTMENT
# ══════════════════════════════════════════════════════════════

HOSTILE_MARKET_STATES = [
    "CHOP_CONFLICTED",
    "UNDEFINED",
    "BEARISH_HIGH_VOL_SQUEEZE",
    "PANIC",
    "BEARISH_CAPITULATION",
]

SUPPORTIVE_MARKET_STATES = [
    "TRENDING_HIGH_VOL_BTC_DOM",
    "TRENDING_LOW_VOL_BULLISH",
    "TRENDING_EXPANSION_RISK_ON",
    "BREAKOUT_CONFIRMED",
    "SQUEEZE_SETUP_LONG",
    "SQUEEZE_SETUP_SHORT",
    "RANGE_ACCUMULATION",
]

MARKET_ADJUSTMENT_RANGES = {
    "supportive": {"min": 1.00, "max": 1.10},
    "neutral": {"min": 0.85, "max": 1.00},
    "mixed": {"min": 0.75, "max": 0.90},
    "hostile": {"min": 0.50, "max": 0.70},
}

RISK_STATE_ADJUSTMENTS = {
    "RISK_ON": 1.05,
    "NEUTRAL": 1.00,
    "RISK_OFF": 0.85,
}


# ══════════════════════════════════════════════════════════════
# SIZE BUCKET THRESHOLDS
# ══════════════════════════════════════════════════════════════

SIZE_BUCKET_THRESHOLDS = {
    "NONE": 0.00,
    "TINY": 0.35,
    "SMALL": 0.70,
    "NORMAL": 1.05,
    # LARGE is anything above NORMAL
}
