"""
Frozen Constants — Market Intelligence OS V1

PHASE 32.5 — Intelligence Layer Freeze

This file contains all frozen constants for the core system.
DO NOT MODIFY these values after freeze.

Version: MARKET_INTELLIGENCE_OS_V1_FROZEN
Date: 2026-03-14
"""

# ══════════════════════════════════════════════════════════════
# VERSION TAG
# ══════════════════════════════════════════════════════════════

SYSTEM_VERSION = "MARKET_INTELLIGENCE_OS_V1_FROZEN"
SYSTEM_VERSION_NUMBER = "1.0.0"
FREEZE_DATE = "2026-03-14"
STATUS = "PRODUCTION_CORE_FROZEN"


# ══════════════════════════════════════════════════════════════
# HYPOTHESIS SCORE WEIGHTS (FROZEN)
# ══════════════════════════════════════════════════════════════
# Total = 1.00

HYPOTHESIS_WEIGHT_ALPHA = 0.33
HYPOTHESIS_WEIGHT_REGIME = 0.23
HYPOTHESIS_WEIGHT_MICROSTRUCTURE = 0.18
HYPOTHESIS_WEIGHT_MACRO = 0.10
HYPOTHESIS_WEIGHT_FRACTAL_MARKET = 0.05
HYPOTHESIS_WEIGHT_FRACTAL_SIMILARITY = 0.05
HYPOTHESIS_WEIGHT_CROSS_ASSET = 0.06


# ══════════════════════════════════════════════════════════════
# SCENARIO PROBABILITY WEIGHTS (FROZEN)
# ══════════════════════════════════════════════════════════════
# Total = 1.00

SCENARIO_WEIGHT_HYPOTHESIS = 0.35
SCENARIO_WEIGHT_REGIME = 0.20
SCENARIO_WEIGHT_MICROSTRUCTURE = 0.15
SCENARIO_WEIGHT_FRACTAL_SIMILARITY = 0.15
SCENARIO_WEIGHT_META_ALPHA = 0.15


# ══════════════════════════════════════════════════════════════
# SIMILARITY CONFIDENCE WEIGHTS (FROZEN)
# ══════════════════════════════════════════════════════════════
# Total = 1.00

CONFIDENCE_WEIGHT_SIMILARITY = 0.50
CONFIDENCE_WEIGHT_HISTORICAL_SUCCESS = 0.30
CONFIDENCE_WEIGHT_CROSS_ASSET = 0.20


# ══════════════════════════════════════════════════════════════
# MODIFIERS (FROZEN)
# ══════════════════════════════════════════════════════════════

# Fractal Similarity Modifier
FRACTAL_SIMILARITY_ALIGNED = 1.12
FRACTAL_SIMILARITY_CONFLICT = 0.90
FRACTAL_SIMILARITY_NEUTRAL = 1.00

# Cross-Asset Similarity Modifier
CROSS_ASSET_ALIGNED = 1.10
CROSS_ASSET_CONFLICT = 0.92
CROSS_ASSET_NEUTRAL = 1.00


# ══════════════════════════════════════════════════════════════
# THRESHOLDS (FROZEN)
# ══════════════════════════════════════════════════════════════

FRACTAL_SIMILARITY_THRESHOLD = 0.75
CROSS_ASSET_SIMILARITY_THRESHOLD = 0.78


# ══════════════════════════════════════════════════════════════
# ASSET UNIVERSE (FROZEN)
# ══════════════════════════════════════════════════════════════

ASSET_UNIVERSE = ["BTC", "ETH", "SOL", "SPX", "NDX", "DXY"]
CRYPTO_ASSETS = ["BTC", "ETH", "SOL"]
TRADITIONAL_ASSETS = ["SPX", "NDX", "DXY"]


# ══════════════════════════════════════════════════════════════
# SCENARIO TYPES (FROZEN)
# ══════════════════════════════════════════════════════════════

SCENARIO_TYPES = [
    "BREAKOUT_CONTINUATION",
    "MEAN_REVERSION",
    "TREND_ACCELERATION",
    "VOLATILITY_EXPANSION",
    "LIQUIDATION_EVENT",
]


# ══════════════════════════════════════════════════════════════
# SIMULATION HORIZONS (FROZEN)
# ══════════════════════════════════════════════════════════════

SIMULATION_HORIZONS = [15, 60, 240]


# ══════════════════════════════════════════════════════════════
# WINDOW SIZES (FROZEN)
# ══════════════════════════════════════════════════════════════

WINDOW_SIZES = [50, 100, 200]


# ══════════════════════════════════════════════════════════════
# LAYER DEFINITIONS (FROZEN)
# ══════════════════════════════════════════════════════════════

INTELLIGENCE_LAYERS = {
    1: "Alpha Intelligence",
    2: "Regime Intelligence",
    3: "Microstructure Intelligence",
    4: "Fractal Intelligence",
    5: "Similarity Intelligence",
    6: "Cross-Asset Intelligence",
    7: "Simulation Intelligence",
}


# ══════════════════════════════════════════════════════════════
# VERIFICATION
# ══════════════════════════════════════════════════════════════

def verify_hypothesis_weights() -> bool:
    """Verify hypothesis weights sum to 1.0."""
    total = (
        HYPOTHESIS_WEIGHT_ALPHA
        + HYPOTHESIS_WEIGHT_REGIME
        + HYPOTHESIS_WEIGHT_MICROSTRUCTURE
        + HYPOTHESIS_WEIGHT_MACRO
        + HYPOTHESIS_WEIGHT_FRACTAL_MARKET
        + HYPOTHESIS_WEIGHT_FRACTAL_SIMILARITY
        + HYPOTHESIS_WEIGHT_CROSS_ASSET
    )
    return abs(total - 1.0) < 0.01


def verify_scenario_weights() -> bool:
    """Verify scenario weights sum to 1.0."""
    total = (
        SCENARIO_WEIGHT_HYPOTHESIS
        + SCENARIO_WEIGHT_REGIME
        + SCENARIO_WEIGHT_MICROSTRUCTURE
        + SCENARIO_WEIGHT_FRACTAL_SIMILARITY
        + SCENARIO_WEIGHT_META_ALPHA
    )
    return abs(total - 1.0) < 0.01


def verify_confidence_weights() -> bool:
    """Verify confidence weights sum to 1.0."""
    total = (
        CONFIDENCE_WEIGHT_SIMILARITY
        + CONFIDENCE_WEIGHT_HISTORICAL_SUCCESS
        + CONFIDENCE_WEIGHT_CROSS_ASSET
    )
    return abs(total - 1.0) < 0.01


def verify_freeze_integrity() -> dict:
    """Verify all frozen constants are valid."""
    return {
        "version": SYSTEM_VERSION,
        "status": STATUS,
        "hypothesis_weights_valid": verify_hypothesis_weights(),
        "scenario_weights_valid": verify_scenario_weights(),
        "confidence_weights_valid": verify_confidence_weights(),
        "layers_count": len(INTELLIGENCE_LAYERS),
        "assets_count": len(ASSET_UNIVERSE),
        "scenarios_count": len(SCENARIO_TYPES),
        "integrity": "VERIFIED" if all([
            verify_hypothesis_weights(),
            verify_scenario_weights(),
            verify_confidence_weights(),
        ]) else "FAILED",
    }
