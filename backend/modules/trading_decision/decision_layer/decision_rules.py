"""
PHASE 14.4 — Trading Decision Rules
=====================================
Hierarchical decision rules and thresholds.
"""

# ══════════════════════════════════════════════════════════════
# SETUP THRESHOLDS
# ══════════════════════════════════════════════════════════════

SETUP_THRESHOLDS = {
    "min_setup_quality": 0.3,  # Below this = no valid setup
    "min_conviction": 0.25,  # Below this = WAIT
    "high_conviction": 0.7,  # Above this = can be aggressive
    "strong_trend": 0.6,  # Above this = strong trend
}

# ══════════════════════════════════════════════════════════════
# AGREEMENT THRESHOLDS
# ══════════════════════════════════════════════════════════════

AGREEMENT_THRESHOLDS = {
    # Strong agreement: TA + Exchange aligned + high conviction
    "strong_agreement_min_conviction": 0.65,
    "strong_agreement_min_exchange_conf": 0.6,
    
    # Mild agreement: TA valid + Exchange neutral
    "mild_agreement_min_conviction": 0.4,
}

# ══════════════════════════════════════════════════════════════
# CONFLICT THRESHOLDS
# ══════════════════════════════════════════════════════════════

CONFLICT_THRESHOLDS = {
    "weak_conflict_max": 0.5,  # conflict_ratio <= this = weak
    "strong_conflict_min": 0.5,  # conflict_ratio > this = strong
    "extreme_conflict_min": 0.7,  # Very high conflict
    "squeeze_extreme": 0.6,  # squeeze_probability threshold
    "cascade_extreme": 0.5,  # cascade_probability threshold
}

# ══════════════════════════════════════════════════════════════
# POSITION MULTIPLIER RANGES
# ══════════════════════════════════════════════════════════════

POSITION_MULTIPLIERS = {
    "ALLOW_AGGRESSIVE": {"min": 1.10, "max": 1.25},
    "ALLOW": {"min": 0.80, "max": 1.00},
    "ALLOW_REDUCED": {"min": 0.35, "max": 0.65},
    "WAIT": {"value": 0.0},
    "BLOCK": {"value": 0.0},
    "REVERSE_CANDIDATE": {"value": 0.0},
}

# ══════════════════════════════════════════════════════════════
# CONFIDENCE WEIGHTS
# ══════════════════════════════════════════════════════════════

CONFIDENCE_WEIGHTS = {
    "ta_conviction": 0.40,
    "exchange_confidence": 0.30,
    "market_state_confidence": 0.30,
}

# Penalties
CONFIDENCE_PENALTIES = {
    "high_conflict": 0.15,  # Subtract when conflict_ratio high
    "hostile_regime": 0.10,  # Subtract when market state hostile
    "squeeze_risk": 0.08,  # Subtract when squeeze probability high
}

# Bonuses
CONFIDENCE_BONUSES = {
    "strong_alignment": 0.10,  # Add when all aligned
    "supportive_market": 0.05,  # Add when market state supportive
}

# ══════════════════════════════════════════════════════════════
# HOSTILE MARKET STATES
# ══════════════════════════════════════════════════════════════

HOSTILE_MARKET_STATES = [
    "CHOP_CONFLICTED",
    "UNDEFINED",
    "BEARISH_HIGH_VOL_SQUEEZE",
    "PANIC",
    "BEARISH_CAPITULATION",
]

SUPPORTIVE_LONG_STATES = [
    "TRENDING_HIGH_VOL_BTC_DOM",
    "TRENDING_LOW_VOL_BULLISH",
    "TRENDING_EXPANSION_RISK_ON",
    "BREAKOUT_CONFIRMED",
    "SQUEEZE_SETUP_LONG",
    "RANGE_ACCUMULATION",
]

SUPPORTIVE_SHORT_STATES = [
    "BEARISH_EXPANSION_RISK_OFF",
    "BREAKDOWN_CONFIRMED",
    "SQUEEZE_SETUP_SHORT",
]

# ══════════════════════════════════════════════════════════════
# EXECUTION MODE MAPPING
# ══════════════════════════════════════════════════════════════

EXECUTION_MODE_RULES = {
    "ALLOW_AGGRESSIVE": "AGGRESSIVE",
    "ALLOW": "NORMAL",
    "ALLOW_REDUCED": "PASSIVE",
    "BLOCK": "NONE",
    "WAIT": "WAIT",
    "REVERSE_CANDIDATE": "WAIT",
}

# ══════════════════════════════════════════════════════════════
# DIRECTION MAPPING
# ══════════════════════════════════════════════════════════════

BIAS_TO_DIRECTION = {
    "BULLISH": "LONG",
    "BEARISH": "SHORT",
    "NEUTRAL": "NEUTRAL",
}

TA_DIRECTION_TO_TRADE = {
    "LONG": "LONG",
    "SHORT": "SHORT",
    "NEUTRAL": "NEUTRAL",
}
