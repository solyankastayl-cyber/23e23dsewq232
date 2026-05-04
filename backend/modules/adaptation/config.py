"""
Sprint 7.1: Adaptation Configuration
=====================================

Defines safe boundaries for adaptation recommendations.
"""

# Adaptation constraints
ADAPTATION_DEFAULTS = {
    # Confidence weight bounds
    "min_confidence_weight": 0.7,      # Never reduce below 70% of original
    "max_confidence_weight": 1.1,      # Never boost above 110% of original
    
    # Safety limits
    "max_single_adjustment_step_pct": 0.15,  # Max 15% change per step
    "min_sample_size": 5,              # Minimum decisions to make recommendation (lowered for demo)
    
    # R2 tuning (future)
    "min_r2_multiplier": 0.5,
    "max_r2_multiplier": 1.0,
}

# Expected win rate floors by confidence bucket
CONFIDENCE_EXPECTED_FLOORS = {
    "0.8-1.0": 0.70,   # High confidence should win at least 70%
    "0.7-0.8": 0.60,   # 
    "0.6-0.7": 0.50,
    "0.5-0.6": 0.45,
    "0.0-0.5": 0.35,
}

# Change types
CHANGE_TYPE_CONFIDENCE_BUCKET = "CONFIDENCE_BUCKET_ADJUSTMENT"
CHANGE_TYPE_R2_DRAWDOWN = "R2_DRAWDOWN_TUNING"

# Change statuses
STATUS_PROPOSED = "PROPOSED"
STATUS_APPLIED = "APPLIED"
STATUS_REJECTED = "REJECTED"
