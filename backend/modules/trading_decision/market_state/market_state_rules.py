"""
PHASE 14.3 — Market State Rules
================================
Rules and thresholds for state classification.
"""

# ══════════════════════════════════════════════════════════════
# TREND STATE RULES
# ══════════════════════════════════════════════════════════════

TREND_RULES = {
    # TA direction + strength thresholds
    "trend_up_threshold": 0.6,  # trend_strength > this for TREND_UP
    "trend_down_threshold": 0.6,
    "range_threshold": 0.3,  # trend_strength < this for RANGE
}


# ══════════════════════════════════════════════════════════════
# VOLATILITY STATE RULES
# ══════════════════════════════════════════════════════════════

VOLATILITY_RULES = {
    "low_percentile": 0.25,  # < 25th percentile = LOW
    "normal_low": 0.25,  # 25-75 = NORMAL
    "normal_high": 0.75,
    "high_percentile": 0.90,  # > 90th = HIGH
    "expanding_change": 0.3,  # 30% increase = EXPANDING
}


# ══════════════════════════════════════════════════════════════
# EXCHANGE STATE RULES
# ══════════════════════════════════════════════════════════════

EXCHANGE_RULES = {
    "bullish_threshold": 0.15,  # bias score > this = BULLISH
    "bearish_threshold": -0.15,
    "conflict_threshold": 0.5,  # conflict_ratio > this = CONFLICTED
}


# ══════════════════════════════════════════════════════════════
# DERIVATIVES STATE RULES
# ══════════════════════════════════════════════════════════════

DERIVATIVES_RULES = {
    "crowded_long_threshold": 0.6,  # crowding_risk > this + positive pressure
    "crowded_short_threshold": 0.6,
    "squeeze_threshold": 0.5,  # squeeze_probability > this = SQUEEZE
}


# ══════════════════════════════════════════════════════════════
# RISK STATE RULES
# ══════════════════════════════════════════════════════════════

RISK_RULES = {
    # Simple rule-based approximation
    # RISK_ON: trending up + low cascade risk + bullish exchange
    # RISK_OFF: trending down + high cascade risk + bearish exchange
    "risk_on_components": ["trend_up", "low_cascade", "bullish_bias"],
    "risk_off_components": ["trend_down", "high_cascade", "bearish_bias"],
}


# ══════════════════════════════════════════════════════════════
# CONFIDENCE WEIGHTS
# ══════════════════════════════════════════════════════════════

CONFIDENCE_WEIGHTS = {
    "ta_conviction": 0.35,
    "exchange_confidence": 0.35,
    "volatility_clarity": 0.15,
    "regime_clarity": 0.15,
}


# ══════════════════════════════════════════════════════════════
# COMBINED STATE MAPPING
# ══════════════════════════════════════════════════════════════

# Map of (trend, vol, exchange, derivatives) -> combined state
COMBINED_STATE_RULES = {
    # Trending bullish patterns
    ("TREND_UP", "HIGH", "BULLISH", "BALANCED"): "TRENDING_HIGH_VOL_BTC_DOM",
    ("TREND_UP", "LOW", "BULLISH", "BALANCED"): "TRENDING_LOW_VOL_BULLISH",
    ("TREND_UP", "EXPANDING", "BULLISH", "BALANCED"): "TRENDING_EXPANSION_RISK_ON",
    ("TREND_UP", "HIGH", "BULLISH", "CROWDED_LONG"): "EUPHORIA",
    
    # Bearish patterns
    ("TREND_DOWN", "EXPANDING", "BEARISH", "BALANCED"): "BEARISH_EXPANSION_RISK_OFF",
    ("TREND_DOWN", "HIGH", "BEARISH", "SQUEEZE"): "BEARISH_HIGH_VOL_SQUEEZE",
    ("TREND_DOWN", "HIGH", "BEARISH", "CROWDED_SHORT"): "BEARISH_CAPITULATION",
    ("TREND_DOWN", "HIGH", "BEARISH", "CROWDED_LONG"): "PANIC",
    
    # Range patterns
    ("RANGE", "LOW", "CONFLICTED", "BALANCED"): "CHOP_CONFLICTED",
    ("RANGE", "LOW", "NEUTRAL", "BALANCED"): "RANGE_LOW_VOL_NEUTRAL",
    ("RANGE", "LOW", "BULLISH", "BALANCED"): "RANGE_ACCUMULATION",
    ("MIXED", "NORMAL", "CONFLICTED", "BALANCED"): "CHOP_CONFLICTED",
    
    # Squeeze setups
    ("RANGE", "LOW", "BULLISH", "SQUEEZE"): "SQUEEZE_SETUP_LONG",
    ("RANGE", "LOW", "BEARISH", "SQUEEZE"): "SQUEEZE_SETUP_SHORT",
    ("TREND_UP", "EXPANDING", "BULLISH", "SQUEEZE"): "BREAKOUT_CONFIRMED",
    ("TREND_DOWN", "EXPANDING", "BEARISH", "SQUEEZE"): "BREAKDOWN_CONFIRMED",
    
    # Reversal potential
    ("TREND_DOWN", "HIGH", "BULLISH", "CROWDED_SHORT"): "REVERSAL_POTENTIAL",
    ("TREND_UP", "HIGH", "BEARISH", "CROWDED_LONG"): "REVERSAL_POTENTIAL",
}
