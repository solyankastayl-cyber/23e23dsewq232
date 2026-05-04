"""
TA Hypothesis Rules
====================
Phase 14.2 — Configuration and scoring rules for hypothesis building.
"""

from typing import Dict

# ═══════════════════════════════════════════════════════════════
# Component Weights for Conviction Score
# ═══════════════════════════════════════════════════════════════

CONVICTION_WEIGHTS = {
    "setup_quality": 0.35,
    "trend_strength": 0.25,
    "entry_quality": 0.20,
    "regime_fit": 0.20,
}

# ═══════════════════════════════════════════════════════════════
# Driver Weights for Direction Score
# ═══════════════════════════════════════════════════════════════

DRIVER_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.25,
    "structure": 0.25,
    "breakout": 0.20,
}

# ═══════════════════════════════════════════════════════════════
# Trend Indicator Thresholds
# ═══════════════════════════════════════════════════════════════

TREND_THRESHOLDS = {
    "strong_trend": 0.7,
    "weak_trend": 0.3,
    "ma_alignment_bullish": 0.3,
    "ma_alignment_bearish": -0.3,
}

# ═══════════════════════════════════════════════════════════════
# Momentum Thresholds
# ═══════════════════════════════════════════════════════════════

MOMENTUM_THRESHOLDS = {
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "rsi_bullish": 55,
    "rsi_bearish": 45,
    "macd_bullish": 0.0,
    "strong_momentum": 0.6,
}

# ═══════════════════════════════════════════════════════════════
# Structure Thresholds
# ═══════════════════════════════════════════════════════════════

STRUCTURE_THRESHOLDS = {
    "bullish_structure": 0.3,
    "bearish_structure": -0.3,
    "strong_structure": 0.6,
}

# ═══════════════════════════════════════════════════════════════
# Entry Quality Thresholds
# ═══════════════════════════════════════════════════════════════

ENTRY_THRESHOLDS = {
    "volatility_low": 0.3,
    "volatility_high": 0.7,
    "distance_good": 0.02,  # 2% from key level
    "distance_bad": 0.05,   # 5% from key level
}

# ═══════════════════════════════════════════════════════════════
# Regime Fit Rules
# ═══════════════════════════════════════════════════════════════

REGIME_FIT_MATRIX: Dict[str, Dict[str, float]] = {
    # Setup type -> Regime -> Fit score
    "BREAKOUT": {
        "TREND_UP": 0.9,
        "TREND_DOWN": 0.9,
        "EXPANSION": 0.95,
        "RANGE": 0.4,
        "COMPRESSION": 0.7,
    },
    "PULLBACK": {
        "TREND_UP": 0.95,
        "TREND_DOWN": 0.95,
        "EXPANSION": 0.6,
        "RANGE": 0.3,
        "COMPRESSION": 0.4,
    },
    "REVERSAL": {
        "TREND_UP": 0.4,
        "TREND_DOWN": 0.4,
        "EXPANSION": 0.7,
        "RANGE": 0.8,
        "COMPRESSION": 0.6,
    },
    "CONTINUATION": {
        "TREND_UP": 0.9,
        "TREND_DOWN": 0.9,
        "EXPANSION": 0.8,
        "RANGE": 0.3,
        "COMPRESSION": 0.5,
    },
    "RANGE_TRADE": {
        "TREND_UP": 0.3,
        "TREND_DOWN": 0.3,
        "EXPANSION": 0.2,
        "RANGE": 0.95,
        "COMPRESSION": 0.7,
    },
    "NO_SETUP": {
        "TREND_UP": 0.5,
        "TREND_DOWN": 0.5,
        "EXPANSION": 0.5,
        "RANGE": 0.5,
        "COMPRESSION": 0.5,
    },
}

# ═══════════════════════════════════════════════════════════════
# Direction Threshold
# ═══════════════════════════════════════════════════════════════

DIRECTION_THRESHOLD = 0.20  # Score > 0.2 = LONG, < -0.2 = SHORT

# ═══════════════════════════════════════════════════════════════
# Quality Thresholds
# ═══════════════════════════════════════════════════════════════

SETUP_QUALITY_THRESHOLD = 0.5  # Below this = NO_SETUP
CONVICTION_THRESHOLD = 0.4     # Below this = low confidence
