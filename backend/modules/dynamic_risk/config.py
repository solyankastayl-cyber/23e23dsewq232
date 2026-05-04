"""
Dynamic Risk Engine Configuration
Sprint R1: Confidence-aware sizing + exposure management
"""

DYNAMIC_RISK_DEFAULTS = {
    "enabled": True,

    # Base sizing
    "base_notional_usd": 100.0,
    
    # Confidence thresholds
    "min_confidence": 0.55,
    "max_confidence": 0.95,

    # Size multipliers (based on confidence)
    "min_size_multiplier": 0.5,   # At min_confidence
    "max_size_multiplier": 1.5,   # At max_confidence

    # Exposure caps — TEMPORARILY DISABLED FOR QTY MATCH TEST
    "max_symbol_notional_usd": 100000.0,     # Effectively unlimited for test
    "max_portfolio_exposure_pct": 1.0,       # 100% - no portfolio blocking

    # Regime multipliers (optional)
    "regime_multipliers": {
        "TREND_UP": 1.1,
        "TREND_DOWN": 1.1,
        "RANGE": 0.8,
        "UNKNOWN": 0.6,
    },
}
